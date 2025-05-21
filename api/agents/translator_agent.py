import os
from dotenv import load_dotenv
import logging
import json
import requests
import time
from typing import Dict, Any
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class TranslatorAgent:
    """Agent for translating 'value' in JSON 'name:value' pairs to the target language"""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        self.output_dir = "contract_analyses"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _clean_response(self, response_text: str) -> str:
        """
        Clean the AI response to ensure it contains only valid JSON.
        Removes code fences, preamble, or trailing text.
        """
        # Remove code fences (```json, ```)
        response_text = re.sub(r'^```json\s*\n|\n```$', '', response_text, flags=re.MULTILINE)
        # Remove any leading/trailing non-JSON text
        response_text = response_text.strip()
        # Ensure it starts and ends with JSON delimiters
        if not (response_text.startswith('{') or response_text.startswith('[')):
            logger.warning("Response does not start with JSON delimiter, attempting to extract JSON")
            json_match = re.search(r'(\{.*\}|\[.*\])', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                logger.error("No valid JSON found in response")
                return response_text
        return response_text

    def translate(self, content: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """
        Translate string values in JSON key-value pairs to the target language by sending the entire JSON to the AI.
        
        Args:
            content: The JSON dictionary
            target_language: Target language code (e.g., 'it', 'es')
            
        Returns:
            Dict with status and translated content
        """
        try:
            logger.info(f"Starting translation to {target_language}")

            # Convert JSON to string for the prompt
            json_string = json.dumps(content, ensure_ascii=False, indent=2)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            language_map = {
                'en': 'English',
                'it': 'Italian',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German'
            }
            language_name = language_map.get(target_language, target_language)
            if target_language not in language_map:
                logger.warning(f"Unsupported target language: {target_language}. Using {language_name}")

            # Strict system prompt to enforce valid JSON and precise translation
            system_prompt = (
                f"You are a professional translator. You will receive a JSON object as a string. "
                f"Your task is to translate ONLY the string values in key-value pairs to {language_name}, "
                f"preserving the entire JSON structure, including all keys, non-string values (e.g., numbers, booleans, null), "
                f"and nested objects/arrays. "
                f"Do NOT translate keys, non-string values, or values of 'status' or 'error' keys. "
                f"If a string value is already in {language_name}, leave it unchanged. "
                f"Return the modified JSON object as a string, maintaining the original structure and formatting. "
                f"The output MUST be valid JSON, parseable by a JSON parser, with no preamble, explanations, code fences (e.g., ```json), "
                f"or any additional text before or after the JSON. "
                f"Ensure proper JSON syntax, including correct delimiters (e.g., commas, brackets). "
                f"Double-check that the output matches the input structure exactly, with only the specified values translated."
            )

            # Save input prompt for debugging
            debug_prompt_file = os.path.join(self.output_dir, f"translation_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            try:
                with open(debug_prompt_file, 'w', encoding='utf-8') as f:
                    f.write(f"System Prompt:\n{system_prompt}\n\nUser Prompt:\n{json_string}")
                logger.debug(f"Saved translation prompt to: {debug_prompt_file}")
            except Exception as e:
                logger.warning(f"Could not save translation prompt to {debug_prompt_file}: {e}")

            # Make API request with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json={
                            "model": "google/gemini-2.0-flash-001",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": json_string}
                            ],
                            "max_tokens": 10000  # Increased to handle large JSON and ensure complete output
                        }
                    )
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        logger.error(f"API error after {max_retries} attempts: {e}")
                        return {
                            'status': 'error',
                            'error': f"API error after {max_retries} attempts: {e}",
                            'translated_content': content
                        }
                    logger.warning(f"API request failed: {e}. Retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)

            if response.status_code == 200:
                translated_json_string = response.json()['choices'][0]['message']['content'].strip()

                # Clean the response to ensure valid JSON
                translated_json_string = self._clean_response(translated_json_string)

                # Save raw response for debugging
                debug_response_file = os.path.join(self.output_dir, f"translation_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                try:
                    with open(debug_response_file, 'w', encoding='utf-8') as f:
                        f.write(translated_json_string)
                    logger.debug(f"Saved translation response to: {debug_response_file}")
                except Exception as e:
                    logger.warning(f"Could not save translation response to {debug_response_file}: {e}")

                # Parse the returned JSON string
                try:
                    translated_content = json.loads(translated_json_string)
                    return {
                        'status': 'success',
                        'translated_content': translated_content
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response: {e}")
                    # Log the problematic response for debugging
                    debug_error_file = os.path.join(self.output_dir, f"translation_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                    try:
                        with open(debug_error_file, 'w', encoding='utf-8') as f:
                            f.write(f"Error: {e}\nResponse:\n{translated_json_string}")
                        logger.debug(f"Saved error response to: {debug_error_file}")
                    except Exception as ex:
                        logger.warning(f"Could not save error response to {debug_error_file}: {ex}")
                    return {
                        'status': 'error',
                        'error': f"Invalid JSON response: {e}",
                        'translated_content': content
                    }
            else:
                logger.error(f"Translation API error: {response.status_code} - {response.text}")
                return {
                    'status': 'error',
                    'error': f"API error: {response.status_code} - {response.text}",
                    'translated_content': content
                }

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'translated_content': content
            }