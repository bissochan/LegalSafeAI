import os
from dotenv import load_dotenv
import logging
import json
import requests
from typing import Any, Dict, Union, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class TranslatorAgent:
    """Agent for translating analysis results while preserving JSON structure"""
    
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        self.max_tokens_per_request = 10000  # Adjust based on API limits
        self.output_dir = "contract_analyses"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _collect_strings(self, data: Any, path: List[str] = [], strings: List[Tuple[List[str], str]] = []) -> List[Tuple[List[str], str]]:
        """
        Recursively collect all strings to translate with their JSON paths.
        Returns a list of (path, string) tuples.
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['status', 'error']:  # Skip technical fields
                    continue
                self._collect_strings(value, path + [key], strings)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._collect_strings(item, path + [str(i)], strings)
        elif isinstance(data, str) and data.strip():
            strings.append((path, data))
        return strings

    def _batch_strings(self, strings: List[Tuple[List[str], str]]) -> List[List[Tuple[List[str], str]]]:
        """
        Batch strings into groups based on estimated token count.
        Returns a list of batches, each containing (path, string) tuples.
        """
        batches = []
        current_batch = []
        current_token_count = 0
        
        for path, string in strings:
            token_count = len(string) // 4 + 1
            if current_token_count + token_count > self.max_tokens_per_request and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_token_count = 0
            current_batch.append((path, string))
            current_token_count += token_count
        
        if current_batch:
            batches.append(current_batch)
        
        return batches

    def _translate_batch(self, batch: List[Tuple[List[str], str]], target_language: str) -> List[Tuple[List[str], str]]:
        """
        Translate a batch of strings in a single API request.
        Returns a list of (path, translated_string) tuples.
        """
        try:
            # Format strings with indices for reference
            prompt = "\n".join(f"{i}:{text}" for i, (_, text) in enumerate(batch))
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Map language codes to full names for clarity in prompt
            language_map = {
                'en': 'English',
                'it': 'Italian',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German'
            }
            language_name = language_map.get(target_language, target_language)

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model": "anthropic/claude-3-opus",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are a professional translator. Translate the following numbered texts to {language_name}. Return only the translations, each on a new line, prefixed with the original number (e.g., '0:translated text'). Do not include any preamble, explanations, or additional text. If a text is already in {language_name}, return it unchanged."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            )

            if response.status_code == 200:
                translated_text = response.json()['choices'][0]['message']['content'].strip()
                
                # Save raw response for debugging
                debug_file = os.path.join(self.output_dir, f"translation_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                try:
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(translated_text)
                    logger.debug(f"Saved translation response to: {debug_file}")
                except Exception as e:
                    logger.warning(f"Could not save translation response to {debug_file}: {e}")

                translated_lines = translated_text.split('\n')
                translated_results = []
                for line in translated_lines:
                    line = line.strip()
                    if not line or ':' not in line:
                        logger.warning(f"Skipping invalid translation line: {line}")
                        continue
                    try:
                        idx, translated_text = line.split(':', 1)
                        idx = int(idx.strip())
                        if 0 <= idx < len(batch):
                            translated_results.append((batch[idx][0], translated_text.strip()))
                        else:
                            logger.warning(f"Invalid index {idx} in translation response, skipping")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing translation line '{line}': {e}")
                        continue
                
                # Ensure all batch items are returned, using original text if translation failed
                result_map = {tuple(path): text for path, text in translated_results}
                return [(path, result_map.get(tuple(path), text)) for path, text in batch]
            else:
                logger.error(f"Translation API error: {response.status_code} - {response.text}")
                return [(path, text) for path, text in batch]

        except Exception as e:
            logger.error(f"Batch translation error: {e}")
            return [(path, text) for path, text in batch]

    def _rebuild_dict(self, original: Dict[str, Any], translations: Dict[tuple, str], path: List[str] = []) -> Dict[str, Any]:
        """
        Rebuild the dictionary with translated values using the JSON paths.
        """
        translated = {}
        for key, value in original.items():
            current_path = path + [key]
            if key in ['status', 'error']:
                translated[key] = value
            elif isinstance(value, dict):
                translated[key] = self._rebuild_dict(value, translations, current_path)
            elif isinstance(value, list):
                translated[key] = [
                    self._rebuild_dict(item, translations, current_path + [str(i)]) if isinstance(item, dict)
                    else translations.get(tuple(current_path + [str(i)]), item)
                    for i, item in enumerate(value)
                ]
            elif isinstance(value, str):
                translated[key] = translations.get(tuple(current_path), value)
            else:
                translated[key] = value
        return translated

    def translate(self, content: Dict[str, Any], target_language: str) -> Dict[str, Any]:
        """
        Translate the analysis results while preserving the exact JSON structure.
        
        Args:
            content: The analysis results dictionary
            target_language: Target language code (e.g., 'es', 'fr', 'de')
            
        Returns:
            Dict with status and translated content
        """
        try:
            logger.info(f"Starting translation to {target_language}")
            strings = self._collect_strings(content)
            translation_map = {tuple(path): text for path, text in strings}
            batches = self._batch_strings(strings)
            translated_map = {}
            for batch in batches:
                translated_batch = self._translate_batch(batch, target_language)
                translated_map.update({tuple(path): text for path, text in translated_batch})
            translated_content = self._rebuild_dict(content, translated_map)
            return {
                'status': 'success',
                'translated_content': translated_content
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'translated_content': content
            }