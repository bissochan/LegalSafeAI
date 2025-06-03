# api/agents/shadow_agent.py
import os
import json
import requests
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from agents.question_analyzer_agent import QuestionAnalyzerAgent
from time import sleep

logger = logging.getLogger(__name__)

class TopicAnalysis(BaseModel):
    topic: str = Field(description="Main topic or clause analyzed")
    problems: str = Field(description="Identified problems or ambiguities")
    implications: str = Field(description="Potential implications of the problems")
    solutions: str = Field(description="Suggested solutions or improvements")
    score: Optional[int] = Field(default=None, nullable=True, description="Clarity and fairness score (1-10)")

class ShadowAnalysisResult(BaseModel):
    overall_score: Optional[int] = Field(default=None, nullable=True, description="Overall contract score (1-10)")
    topics: List[TopicAnalysis] = Field(description="List of analyzed topics")
    summary: str = Field(description="Concise summary of critical points")

class ShadowAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.question_analyzer = QuestionAnalyzerAgent()
        self.output_dir = "shadow_analyses"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def analyze(self, contract_text: str, user_id: int, language: str = 'en') -> Dict:
        """Analyze the contract and return structured results."""
        if not contract_text:
            raise ValueError("Contract text cannot be empty")

        choices = self.question_analyzer.get_choices(user_id)
        system_prompt = (
            f"You are an expert legal consultant analyzing employment contracts in {language}. "
            f"Your goal is to identify ambiguities, unfavorable clauses, and potential risks, focusing on: {', '.join(choices)}. "
            "Pay close attention to unclear definitions, broad liability exclusions, ambiguous termination clauses, "
            "payment terms, penalties, intellectual property, governing law, jurisdiction, and discrepancies. "
            "Return the response wrapped in ```json\n...\n``` code blocks as a valid JSON object with the following structure:\n"
            "```json\n"
            "{\n"
            "  \"overall_score\": integer|null,\n"
            "  \"topics\": [\n"
            "    {\n"
            "      \"topic\": \"string\",\n"
            "      \"problems\": \"string\",\n"
            "      \"implications\": \"string\",\n"
            "      \"solutions\": \"string\",\n"
            "      \"score\": integer|null\n"
            "    }\n"
            "  ],\n"
            "  \"summary\": \"string\"\n"
            "}\n"
            "```\n"
            "For each topic:\n"
            "- Identify the main clause or term.\n"
            "- Explain problems or ambiguities.\n"
            "- Describe potential implications.\n"
            "- Suggest solutions or improvements.\n"
            "- Assign a clarity and fairness score (1-10).\n"
            "Provide a concise summary of critical points. Respond in {language}, be polite, and ensure the JSON is valid."
        )

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-001",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Contract: {contract_text}"}
                        ],
                        "max_tokens": 2000,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=60
                )

                logger.debug(f"Raw API response: {response.text}")

                if response.status_code in (500, 429) and attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} due to status {response.status_code}")
                    sleep(retry_delay)
                    continue

                if response.status_code != 200:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    raise requests.RequestException(f"API returned status {response.status_code}")

                result = response.json()
                if not result.get('choices'):
                    logger.error(f"No valid choices in API response: {response.text}")
                    raise ValueError("No valid response from API")

                content = result['choices'][0]['message']['content'].strip()

                try:
                    if content.startswith('```json') and content.endswith('```'):
                        content = content[7:-3].strip()
                    parsed_data = json.loads(content)
                except json.JSONDecodeError:
                    try:
                        parsed_data = json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse API response as JSON: {content}")
                        raise ValueError(f"Invalid JSON response: {str(e)}")

                analysis_result = ShadowAnalysisResult(
                    overall_score=parsed_data.get('overall_score'),
                    topics=[
                        TopicAnalysis(
                            topic=topic.get('topic', ''),
                            problems=topic.get('problems', ''),
                            implications=topic.get('implications', ''),
                            solutions=topic.get('solutions', ''),
                            score=topic.get('score')
                        ) for topic in parsed_data.get('topics', [])
                    ],
                    summary=parsed_data.get('summary', '')
                )

                self.save_analysis(analysis_result, contract_name="shadow_analysis")
                return analysis_result.dict()

            except (requests.RequestException, ValueError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} due to error: {str(e)}")
                    sleep(retry_delay)
                    continue
                logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                default_analysis = ShadowAnalysisResult(
                    overall_score=None,
                    topics=[],
                    summary="Unable to generate shadow analysis due to API error. Please try again later."
                )
                self.save_analysis(default_analysis, contract_name="shadow_analysis_fallback")
                return default_analysis.dict()

    def save_analysis(self, analysis_result: ShadowAnalysisResult, contract_name: str):
        """Save the analysis to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = ''.join(c for c in contract_name if c.isalnum() or c in ('_', '-'))
        filename = f"analysis_{safe_name}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        analysis_data = analysis_result.dict()
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis saved to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save analysis to {filepath}: {str(e)}")
            raise