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
        
        # Modelli per la valutazione
        self.models = [
            "google/gemini-2.0-flash-001",
            "openai/gpt-4o",
            "meta-llama/llama-3.1-70b-instruct"
        ]
        
        # Threshold per considerare la risposta corretta
        self.accuracy_threshold = 80
        # Timeout per le richieste API
        self.timeout = 30

    def clean_json_response(self, response_text: str) -> str:
        """Tenta di estrarre un JSON valido da una risposta potenzialmente malformata."""
        if not response_text or response_text.isspace():
            logger.warning("Response text is empty or contains only whitespace")
            return "{}"  # Restituisci un JSON vuoto come fallback

        # Rimuove eventuali blocchi di codice markdown (es. ```json ... ```)
        response_text = re.sub(r'^```json\n|\n```$', '', response_text, flags=re.MULTILINE)
        
        # Rimuove spazi o caratteri non validi iniziali/finali
        response_text = response_text.strip()
        
        # Sostituisce caratteri di controllo non validi (es. \n, \t) all'interno delle stringhe
        def escape_control_chars(match):
            text = match.group(0)
            return text.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
        
        # Applica la sostituzione solo alle stringhe tra virgolette
        response_text = re.sub(r'"[^"]*"', escape_control_chars, response_text)
        
        # Cerca un oggetto JSON valido
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, response_text, re.DOTALL)
        if match:
            return match.group(0)
        
        # Se non trova un JSON, restituisci un JSON vuoto
        logger.warning(f"Could not extract valid JSON from response: {response_text}")
        return "{}"

    def evaluate(self, contract: str, response_to_evaluate: str, response_type: str) -> dict:
        """Evaluate a response using multiple models."""
        results = {}
        scores = []

        # Define evaluation criteria
        evaluation_prompt = {
            "role": "system",
            "content": f"""You are a legal contract evaluator. Analyze the {'shadow analysis' if response_type == 'shadow' else 'contract summary'} for accuracy and completeness.
            YOU MUST RESPOND WITH A VALID JSON OBJECT IN THIS EXACT FORMAT:
            {{
                "explanation": "<your detailed evaluation explanation>",
                "accuracy_score": <integer between 0 and 100>
            }}
            DO NOT include any text outside the JSON. Ensure the response is valid JSON."""
        }

        user_prompt = {
            "role": "user",
            "content": f"""Contract: {contract}
                        Response to evaluate: {response_to_evaluate}
                        
                        Evaluate this response and provide your assessment in the required JSON format."""
        }

        # Evaluate with each model
        for model in self.models:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [evaluation_prompt, user_prompt]
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()

                # Log dello status e del contenuto grezzo
                raw_content = response.content.decode('utf-8', errors='replace')
                #logger.info(f"Response status for {model}: {response.status_code}")
                #logger.info(f"Raw response content for {model}: {raw_content}")

                try:
                    # Parsa la risposta JSON
                    response_data = response.json()

                    # Estrai la risposta del modello
                    choices = response_data.get('choices', [])
                    if not choices:
                        raise ValueError("No choices in API response")
                    
                    model_response = choices[0].get('message', {}).get('content', '').strip()
                    if not model_response:
                        raise ValueError("Empty response from model")

                    # Tenta di ripulire la risposta
                    cleaned_response = self.clean_json_response(model_response)
                    
                    # Parse JSON
                    evaluation = json.loads(cleaned_response)

                    # Validate JSON structure
                    if not isinstance(evaluation, dict):
                        raise ValueError("Response is not a JSON object")
                    if not all(key in evaluation for key in ["explanation", "accuracy_score"]):
                        raise ValueError("Missing required fields in JSON")
                    if not isinstance(evaluation["accuracy_score"], (int, float)):
                        raise ValueError("accuracy_score must be a number")
                    if not 0 <= evaluation["accuracy_score"] <= 100:
                        raise ValueError("accuracy_score must be between 0 and 100")

                    scores.append(evaluation["accuracy_score"])
                    results[model] = evaluation
                    logger.info(f"Successfully evaluated with {model}")

                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Invalid response from {model}: {str(e)}")
                    logger.error(f"Raw model response: {model_response}")
                    results[model] = {"error": f"Invalid response format: {str(e)}"}

            except requests.exceptions.RequestException as e:
                logger.error(f"API error with {model}: {str(e)}")
                logger.error(f"Response content: {response.content.decode('utf-8', errors='replace') if 'response' in locals() else 'No response'}")
                results[model] = {"error": f"API error: {str(e)}"}

        # Calculate average score from valid responses
        valid_scores = [score for score in scores if isinstance(score, (int, float))]
        average_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        is_correct = average_score >= self.accuracy_threshold

        return {
            "response_type": response_type,
            "model_results": results,
            "average_score": round(average_score, 2),
            "is_correct": is_correct,
            "threshold": self.accuracy_threshold
        }