import requests
import json
from dotenv import load_dotenv
import os
from typing import Dict, Any

class LegalChatAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set OPENROUTER_API_KEY in your .env file.")

        # Store context of the analysis
        self.contract_text = None
        self.shadow_analysis = None
        self.summary_analysis = None
        self.language = 'en'

    def initialize_context(self, contract_text: str, shadow_analysis: str, 
                            summary_analysis: Dict[str, Any], language: str = 'en'):
        """
        Initialize the chat context with the contract and its analyses.
        
        Args:
            contract_text (str): The original contract text
            shadow_analysis (str): The shadow analysis results
            summary_analysis (dict): The structured summary analysis
            language (str): The language for responses (default is 'en')
        """
        self.contract_text = contract_text
        self.shadow_analysis = shadow_analysis
        self.summary_analysis = summary_analysis
        self.language = language

    def chat(self, user_query: str) -> str:
        """
        Process user queries about the contract and its analyses.
        
        Args:
            user_query (str): The user's question or concern
            
        Returns:
            str: The agent's response
        """
        if not all([self.contract_text, self.shadow_analysis, self.summary_analysis]):
            return "Please initialize the context first with initialize_context()"

        system_prompt = f"""You are an expert legal assistant specialized in employment contracts.
        Respond in {self.language}.
        Your role is to help users understand the contract analysis provided and answer their questions.
        
        IMPORTANT FORMATTING RULES:
        1. Use plain text only - no Markdown, no asterisks, no special formatting
        2. Use simple punctuation and natural language
        3. Structure your response like a chat message
        4. Use clear paragraphs with line breaks for readability
        5. Use simple bullet points with dashes (-)
        6. Avoid technical formatting or symbols
        
        When responding:
        - Be clear and direct
        - Use everyday language
        - Break complex ideas into simple points
        - Structure information in an easy-to-read way
        - If emphasizing something, use natural language like "Note:" or "Important:"
        
        If asked about legal advice, remind users that you can only explain the analyses 
        and cannot provide legal advice."""

        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": f"""Context:
                            Original Contract:
                            {self.contract_text}
                            
                            Shadow Analysis:
                            {self.shadow_analysis}
                            
                            Structured Analysis:
                            {json.dumps(self.summary_analysis, indent=2)}
                            
                            User Question:
                            {user_query}"""
                        }
                    ]
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                # Clean up any remaining markdown or special characters
                answer = result["choices"][0]["message"]["content"]
                answer = answer.replace("**", "")
                answer = answer.replace("*", "")
                answer = answer.replace("`", "")
                answer = answer.replace("#", "")
                answer = answer.replace(">", "")
                return answer
            else:
                return "I couldn't generate a response. Please try rephrasing your question."
                
        except requests.exceptions.RequestException as e:
            return f"Error communicating with the API: {str(e)}"
        except json.JSONDecodeError:
            return "Error processing the response from the API"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

    def get_explanation(self, aspect: str) -> str:
        """
        Get a detailed explanation of a specific aspect of the contract analysis.
        
        Args:
            aspect (str): The aspect to explain (e.g., "sick_leave", "termination", etc.)
            
        Returns:
            str: Detailed explanation of the aspect
        """
        if not all([self.contract_text, self.shadow_analysis, self.summary_analysis]):
            return "Please initialize the context first with initialize_context()"

        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""Respond in {self.language}. Explain the '{aspect}' aspect of the contract in detail.
                            Reference both the structured analysis and any relevant points from the shadow analysis.
                            Focus on:
                            1. What the contract says about this aspect
                            2. How it was scored and why
                            3. Any potential issues or concerns identified
                            4. Common questions users might have about this aspect"""
                        },
                        {
                            "role": "user",
                            "content": f"""Based on:
                            Contract Text: {self.contract_text}
                            Shadow Analysis: {self.shadow_analysis}
                            Structured Analysis: {json.dumps(self.summary_analysis.get('structured_analysis', {}).get(aspect, {}), indent=2)}
                            
                            Please provide a detailed explanation of the '{aspect}' aspect in {self.language}."""
                        }
                    ]
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return f"I couldn't generate an explanation for the {aspect} aspect."
                
        except Exception as e:
            return f"Error generating explanation: {str(e)}"

# Example usage
if __name__ == "__main__":
    chat_agent = LegalChatAgent()
    
    # Sample data
    contract = "Sample contract text..."
    shadow_analysis = "Sample shadow analysis..."
    summary_analysis = {"structured_analysis": {}}
    
    # Initialize the agent
    chat_agent.initialize_context(contract, shadow_analysis, summary_analysis, language='en')
    
    # Example chat interaction
    response = chat_agent.chat("Can you explain the termination clause?")
    print(response)
    
    # Example aspect explanation
    explanation = chat_agent.get_explanation("termination")
    print(explanation)