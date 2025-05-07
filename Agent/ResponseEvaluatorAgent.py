import requests
import json
from dotenv import load_dotenv
import os
import logging
import re

# Configura il logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseEvaluator:
    def __init__(self):
        # Carica variabili d'ambiente
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found in .env file.")
        
        # Modelli per la valutazione (sostituisci con i tuoi)
        self.models = [
            "google/gemini-2.0-flash-001",
            "openai/gpt-4o",
            "meta-llama/llama-3.1-70b-instruct"
        ]
        
        # Threshold per considerare la risposta corretta
        self.accuracy_threshold = 80

    def evaluate(self, contract, response_to_evaluate, response_type):
        """
        Evaluate the correctness of a provided response against a contract using three models.

        Args:
            contract (str): The contract text for context.
            response_to_evaluate (str): The response to evaluate for correctness.
            response_type (str): Type of response, either "shadow" or "summary".

        Returns:
            dict: Contains individual scores, average score, and verdict.
        """
        # Validazione input
        if not isinstance(contract, str) or not contract.strip():
            logger.error("No valid contract provided")
            return {"error": "A valid contract is required."}
        if not isinstance(response_to_evaluate, str) or not response_to_evaluate.strip():
            logger.error("No valid response provided for evaluation")
            return {"error": "A valid response to evaluate is required."}
        if response_type not in ["shadow", "summary"]:
            logger.error("Invalid response_type. Must be 'shadow' or 'summary'.")
            return {"error": "response_type must be 'shadow' or 'summary'."}

        # Prompt specifici per tipo di risposta
        if response_type == "shadow":
            system_prompt = """You are an expert legal evaluator tasked with assessing the correctness of a provided response 
            regarding a contract analysis. The response is a general analysis of a contract, identifying ambiguities, risks, or 
            unfavorable clauses. Your goal is to evaluate whether the response accurately identifies issues and provides appropriate 
            suggestions.

            Instructions:
            - Compare the provided response with the contract.
            - Assess the response for factual accuracy, completeness, and relevance in identifying key issues (e.g., unclear terms, 
              liability, termination, payments, IP, jurisdiction).
            - Provide a brief explanation of your evaluation.
            - Assign an accuracy score between 0 and 100, where:
              - 0: Completely incorrect or irrelevant.
              - 100: Perfectly accurate and comprehensive.
            - Return your response in the following JSON format:
              {
                "explanation": "Your explanation here",
                "accuracy_score": <integer between 0 and 100>
              }
            """
        else:  # summary
            system_prompt = """You are an expert legal evaluator tasked with assessing the correctness of a provided response 
            regarding a contract analysis. The response is a detailed summary of an employment contract, covering specific fields 
            (e.g., sick leave, vacation, termination). Your goal is to evaluate whether the content of the summary and field analyses 
            is factually accurate and relevant to the contract, ignoring the response's format or structure.

            Instructions:
            - Compare the provided response with the contract.
            - Assess the response for factual accuracy, completeness, and relevance in describing the contract's terms and identifying 
              issues in fields like sick leave, vacation, termination, etc.
            - Provide a brief explanation of your evaluation, focusing on the content's correctness.
            - Assign an accuracy score between 0 and 100, where:
              - 0: Completely incorrect or irrelevant.
              - 100: Perfectly accurate and comprehensive.
            - Return your response in the following JSON format:
              {
                "explanation": "Your explanation here",
                "accuracy_score": <integer between 0 and 100>
              }
            """

        results = {}
        scores = []

        # Chiama ogni modello
        for model in self.models:
            try:
                logger.info(f"Evaluating response with model: {model}")
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    data=json.dumps({
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": f"Contract: {contract}\n\nResponse to evaluate: {response_to_evaluate}"
                            }
                        ]
                    }),
                    timeout=10
                )
                response.raise_for_status()

                # Estrai il contenuto della risposta
                response_data = response.json()
                if 'choices' not in response_data or not response_data['choices']:
                    logger.warning(f"Empty response from model {model}")
                    results[model] = {"error": "Empty or invalid response"}
                    continue

                model_response = response_data['choices'][0]['message']['content']
                
                # Prova a parsare il JSON dalla risposta
                try:
                    evaluation = json.loads(model_response)
                    if "accuracy_score" in evaluation and "explanation" in evaluation:
                        score = int(evaluation["accuracy_score"])
                        if 0 <= score <= 100:
                            scores.append(score)
                            results[model] = evaluation
                        else:
                            results[model] = {"error": "Invalid accuracy score"}
                    else:
                        results[model] = {"error": "Missing required fields in response"}
                except json.JSONDecodeError:
                    # Fallback con regex per estrarre lo score
                    score_match = re.search(r"accuracy_score\":\s*(\d+)", model_response)
                    if score_match:
                        score = int(score_match.group(1))
                        if 0 <= score <= 100:
                            scores.append(score)
                            results[model] = {
                                "explanation": "Extracted from non-JSON response",
                                "accuracy_score": score
                            }
                        else:
                            results[model] = {"error": "Invalid accuracy score"}
                    else:
                        results[model] = {"error": "Failed to parse response as JSON"}

            except requests.exceptions.RequestException as e:
                logger.error(f"Network error with model {model}: {str(e)}")
                results[model] = {"error": f"Network error: {str(e)}"}
            except Exception as e:
                logger.error(f"Unexpected error with model {model}: {str(e)}")
                results[model] = {"error": f"Unexpected error: {str(e)}"}

        # Calcola la media degli score validi
        average_score = sum(scores) / len(scores) if scores else 0
        is_correct = average_score >= self.accuracy_threshold if scores else False

        # Risultato finale
        final_result = {
            "response_type": response_type,
            "model_results": results,
            "average_score": round(average_score, 2),
            "is_correct": is_correct,
            "threshold": self.accuracy_threshold
        }

        logger.info(f"Evaluation complete. Response type: {response_type}, Average score: {average_score}, Correct: {is_correct}")
        return final_result