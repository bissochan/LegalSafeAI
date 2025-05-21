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
    """Agent for translating string values in JSON to the target language"""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found")
        self.output_dir = "contract_analyses"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _clean_response(self, response_text: str) -> str:
        """Clean AI response to ensure valid JSON"""
        # Remove code fences
        response_text = re.sub(r'^```json\s*\n|\n```$', '', response_text, flags=re.MULTILINE)
        # Strip non-JSON content
        response_text = response_text.strip()
        # Extract JSON
        json_match = re.search(r'(\{.*\}|\[.*\])', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        # Fix trailing commas
        response_text = re.sub(r',\s*([}\]])', r'\1', response_text)
        logger.debug(f"Cleaned response: {response_text[:100]}...")
        return response_text

    def translate(self, content: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """Translate string values in JSON to target language"""
        try:
            logger.info(f"Translating to {target_language}")
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

            system_prompt = (
                f"Translate string values in the provided JSON to {language_name}, preserving the JSON structure. "
                f"Do not translate keys, non-string values, or 'status'/'error' values. "
                f"Return valid JSON without code fences, preamble, or extra text."
            )

            # Save prompt for debugging
            debug_file = os.path.join(self.output_dir, f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"Prompt:\n{system_prompt}\n\nInput:\n{json_string}")

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
                            "max_tokens": 15000
                        }
                    )
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        logger.error(f"API failed after {max_retries} attempts: {e}")
                        return {'status': 'error', 'error': str(e), 'translated_content': content}
                    logger.warning(f"API failed: {e}. Retrying...")
                    time.sleep(2 ** attempt)

            translated_json_string = response.json()['choices'][0]['message']['content'].strip()

            # Save response for debugging
            debug_response_file = os.path.join(self.output_dir, f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(debug_response_file, 'w', encoding='utf-8') as f:
                f.write(translated_json_string)

            # Parse response
            translated_json_string = self._clean_response(translated_json_string)
            try:
                translated_content = json.loads(translated_json_string)
                return {'status': 'success', 'translated_content': translated_content}
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}\nRaw: {translated_json_string}")
                debug_error_file = os.path.join(self.output_dir, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                with open(debug_error_file, 'w', encoding='utf-8') as f:
                    f.write(f"Error: {e}\nRaw: {translated_json_string}")
                return {'status': 'error', 'error': f"Invalid JSON: {e}", 'translated_content': content}

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {'status': 'error', 'error': str(e), 'translated_content': content}