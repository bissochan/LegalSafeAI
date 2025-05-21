import requests
import json
from dotenv import load_dotenv
import os
import logging
from typing import Dict, Any
import uuid
from agents.translator_agent import TranslatorAgent

logger = logging.getLogger(__name__)

class ChatAgent:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set OPENROUTER_API_KEY in your .env file.")

        # Initialize translator
        self.translator = TranslatorAgent()
        
        # Store chat sessions
        self.sessions: Dict[str, dict] = {}

    def initialize_session(self, contract_text: str, language: str = 'en') -> str:
        """Initialize a new chat session with contract context"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'contract_text': contract_text,
            'language': language,
            'messages': []
        }
        logger.debug(f"Initialized chat session {session_id} with language {language}")
        return session_id

    def update_session_language(self, session_id: str, language: str) -> None:
        """Update the language of an existing chat session"""
        if session_id not in self.sessions:
            raise ValueError("Invalid session ID")
        self.sessions[session_id]['language'] = language
        logger.debug(f"Updated chat session {session_id} to language {language}")

    def process_message(self, session_id: str, message: str, language: str = 'en') -> str:
        """Process a chat message in the context of the contract"""
        if session_id not in self.sessions:
            raise ValueError("Invalid session ID")

        session = self.sessions[session_id]
        contract_text = session['contract_text']
        session_language = session.get('language', language)
        
        # Translate user message to English if not in English
        if session_language != 'en':
            translation_response = self.translator.translate(
                content={'message': message},
                target_language='en'
            )
            if translation_response['status'] == 'success':
                message = translation_response['translated_content']['message']
            else:
                logger.error(f"Failed to translate message to English: {translation_response.get('error')}")
                return "Sorry, I couldn't process your message due to a translation error."

        system_prompt = f"""You are an expert legal assistant specialized in employment contracts.
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
                            {contract_text}
                            
                            User Question:
                            {message}"""
                        }
                    ],
                    "max_tokens": 2000
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                answer = result["choices"][0]["message"]["content"]
                # Clean up any remaining markdown or special characters
                answer = answer.replace("**", "").replace("*", "").replace("`", "").replace("#", "").replace(">", "")
                
                # Translate response back to session language if not English
                if session_language != 'en':
                    translation_response = self.translator.translate(
                        content={'answer': answer},
                        target_language=session_language
                    )
                    if translation_response['status'] == 'success':
                        answer = translation_response['translated_content']['answer']
                    else:
                        logger.error(f"Failed to translate response to {session_language}: {translation_response.get('error')}")
                        return "Sorry, I couldn't process the response due to a translation error."
                
                # Store message history
                session['messages'].append({
                    'user': message,
                    'assistant': answer
                })
                return answer
            else:
                return "I couldn't generate a response. Please try rephrasing your question."
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return f"Error communicating with the API: {str(e)}"
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from API")
            return "Error processing the response from the API"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"

    def end_session(self, session_id: str) -> None:
        """End a chat session and cleanup"""
        self.sessions.pop(session_id, None)
        logger.debug(f"Ended chat session {session_id}")

    def get_explanation(self, session_id: str, aspect: str) -> str:
        """Get a detailed explanation of a specific aspect of the contract analysis"""
        if session_id not in self.sessions:
            raise ValueError("Invalid session ID")

        session = self.sessions[session_id]
        contract_text = session['contract_text']
        language = session['language']
        
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
                            "content": f"""You are an expert legal assistant specialized in employment contracts.
                            Respond in {language}.
                            Explain the '{aspect}' aspect of the contract in detail.
                            
                            IMPORTANT FORMATTING RULES:
                            1. Use plain text only - no Markdown, no asterisks, no special formatting
                            2. Use simple punctuation and natural language
                            3. Structure your response like a chat message
                            4. Use clear paragraphs with line breaks for readability
                            5. Use simple bullet points with dashes (-)
                            6. Avoid technical formatting or symbols
                            
                            Focus on:
                            - What the contract says about this aspect
                            - Any potential issues or concerns identified
                            - Common questions users might have about this aspect"""
                        },
                        {
                            "role": "user",
                            "content": f"""Based on:
                            Contract Text: {contract_text}
                            
                            Please provide a detailed explanation of the '{aspect}' aspect."""
                        }
                    ],
                    "max_tokens": 2000
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                answer = result["choices"][0]["message"]["content"]
                # Clean up any remaining markdown or special characters
                answer = answer.replace("**", "").replace("*", "").replace("`", "").replace("#", "").replace(">", "")
                return answer
            else:
                return f"I couldn't generate an explanation for the {aspect} aspect."
                
        except Exception as e:
            logger.error(f"Error generating explanation for {aspect}: {str(e)}")
            return f"Error generating explanation: {str(e)}"

if __name__ == "__main__":
    chat_agent = ChatAgent()
    contract = "Sample contract text..."
    language = 'en'
    session_id = chat_agent.initialize_session(contract, language)
    response = chat_agent.process_message(session_id, "Can you explain the termination clause?")
    print(response)
    explanation = chat_agent.get_explanation(session_id, "termination")
    print(explanation)
    chat_agent.end_session(session_id)