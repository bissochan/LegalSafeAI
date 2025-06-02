# api/agents/translator_agent.py
import os
import logging
import json
import requests
import time
import re
from typing import Dict, Any, Union
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class TranslatorAgent:
    """Agent for translating string values in JSON to the target language"""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.default_model = "google/gemini-2.0-flash-001"
        self.fallback_model = "anthropic/claude-3.5-sonnet"
        self.output_dir = "contract_analyses"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _clean_response(self, response_text: str) -> str:
        """Clean AI response to ensure valid JSON"""
        response_text = re.sub(r'^```json\s*\n|\n```$', '', response_text, flags=re.MULTILINE)
        response_text = response_text.strip()
        json_match = re.search(r'(\{.*\}|\[.*\])', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        response_text = re.sub(r',\s*([}\]])', r'\1', response_text)
        response_text = re.sub(r'(?<!\\)"', r'\"', response_text)
        logger.debug(f"Cleaned response: {response_text[:100]}...")
        return response_text

    def _translate_chunk(self, text: str, target_language: str, model: str = None) -> str:
        """Translate a single text chunk."""
        if not text.strip():
            logger.debug("Empty text chunk, skipping translation")
            return text

        language_map = {
            'en': 'English',
            'it': 'Italian',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German'
        }
        language_name = language_map.get(target_language, target_language)
        model = model or self.default_model

        prompt = (
            f"Translate the following text to {language_name}. "
            f"Return the translated text as plain text, without JSON or code markers. "
            f"Do not modify the meaning or add explanations.\n\n"
            f"Text:\n{text}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "Return plain text translation."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 4000,
                        "temperature": 0.3
                    },
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                logger.debug(f"Raw API response for model {model}: {json.dumps(result, indent=2)}")
                if "choices" in result and result["choices"]:
                    translated_text = result["choices"][0]["message"]["content"].strip()
                    # Save debug output
                    debug_file = os.path.join(self.output_dir, f"chunk_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(f"Model: {model}\nPrompt: {prompt}\nResponse: {translated_text}")
                    return translated_text
                logger.error(f"No choices in API response for model {model}")
                break
            except requests.exceptions.RequestException as e:
                logger.warning(f"Chunk translation failed with model {model}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"Chunk translation failed after {max_retries} attempts")
                    if model != self.fallback_model:
                        logger.info(f"Trying fallback model: {self.fallback_model}")
                        return self._translate_chunk(text, target_language, self.fallback_model)
                    return text
                time.sleep(2 ** attempt)

        return text

    def _translate_dict(self, data: Union[str, dict, list], target_language: str) -> Union[str, dict, list]:
        """Recursively translate string values in a dictionary or list."""
        if isinstance(data, str):
            return self._translate_chunk(data, target_language)
        elif isinstance(data, dict):
            translated = {}
            for key, value in data.items():
                translated[key] = self._translate_dict(value, target_language)
            return translated
        elif isinstance(data, list):
            return [self._translate_dict(item, target_language) for item in data]
        else:
            return data

    def translate(self, content: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """Translate string values in JSON to target language"""
        try:
            logger.info(f"Translating to {target_language}")
            logger.debug(f"Input JSON structure: {json.dumps(content, ensure_ascii=False, indent=2)[:500]}...")
            translated_content = content.copy()

            # Translate document_text and shadow_analysis
            for key in ["document_text", "shadow_analysis"]:
                if key in content and isinstance(content[key], str):
                    logger.debug(f"Translating {key}, length: {len(content[key])}")
                    translated_content[key] = self._translate_chunk(content[key], target_language)

            # Translate summary recursively
            if "summary" in content:
                logger.debug(f"Translating summary, structure: {json.dumps(content['summary'], ensure_ascii=False)[:200]}...")
                translated_content["summary"] = self._translate_dict(content["summary"], target_language)

            # Save translated output
            debug_file = os.path.join(self.output_dir, f"translation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(translated_content, f, ensure_ascii=False, indent=2)

            logger.info(f"Successfully translated to {target_language}")
            return {"status": "success", "translated_content": translated_content}

        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            debug_error_file = os.path.join(self.output_dir, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(debug_error_file, 'w', encoding='utf-8') as f:
                f.write(f"Error: {str(e)}\nInput:\n{json.dumps(content, ensure_ascii=False, indent=2)}")
            return {
                "status": "error",
                "error": f"Translation failed: {str(e)}",
                "translated_content": translated_content
            }