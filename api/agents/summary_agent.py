# api/agents/summary_agent.py
import os
import json
import requests
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from agents.question_analyzer_agent import QuestionAnalyzerAgent
from time import sleep

logger = logging.getLogger(__name__)

class ContractField(BaseModel):
    content: str = Field(description="The content of the field")
    score: Optional[int] = Field(default=None, nullable=True, description="Score from 1-10")

class ContractAnalysis(BaseModel):
    sick_leave: ContractField
    vacation: ContractField
    overtime: ContractField
    termination: ContractField
    confidentiality: ContractField
    non_compete: ContractField
    intellectual_property: ContractField
    governing_law: ContractField
    jurisdiction: ContractField
    dispute_resolution: ContractField
    liability: ContractField
    salary: ContractField
    benefits: ContractField
    work_hours: ContractField
    performance_evaluation: ContractField
    duties: ContractField
    responsibilities: ContractField
    overall_score: Optional[int] = Field(default=None, nullable=True, description="Overall contract score (1-10)")

class ContractSummary(BaseModel):
    executive_summary: str = Field(description="General overview of the contract")
    key_points: str = Field(description="Key points of the contract")
    potential_issues: str = Field(description="Potential problems or areas of concern")
    recommendations: str = Field(description="Recommendations for improvements")

class ContractAnalysisResult(BaseModel):
    structured_analysis: ContractAnalysis
    summary: ContractSummary

class SummaryAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.question_analyzer = QuestionAnalyzerAgent()
        self.output_dir = "contract_analyses"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def analyze(self, contract_text: str, user_id: int, language: str = 'en') -> Dict:
        """Analyze the contract and return structured results."""
        if not contract_text:
            raise ValueError("Contract text cannot be empty")

        choices = self.question_analyzer.get_choices(user_id)
        system_prompt = (
            f"You are an expert in employment contract analysis. Analyze the provided contract in {language}. "
            f"Focus particularly on these areas: {', '.join(choices)}. "
            "Return the response wrapped in ```json\n...\n``` code blocks as a valid JSON object with the following structure:\n"
            "```json\n"
            "{\n"
            "  \"structured_analysis\": {\n"
            "    \"sick_leave\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"vacation\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"overtime\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"termination\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"confidentiality\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"non_compete\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"intellectual_property\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"governing_law\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"jurisdiction\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"dispute_resolution\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"liability\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"salary\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"benefits\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"work_hours\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"performance_evaluation\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"duties\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"responsibilities\": {\"content\": \"string\", \"score\": integer|null},\n"
            "    \"overall_score\": integer|null\n"
            "  },\n"
            "  \"summary\": {\n"
            "    \"executive_summary\": \"string\",\n"
            "    \"key_points\": \"string\",\n"
            "    \"potential_issues\": \"string\",\n"
            "    \"recommendations\": \"string\"\n"
            "  }\n"
            "}\n"
            "```\n"
            "Ensure the response is valid JSON and contains all required fields, even if empty."
        )

        max_retries = 3
        retry_delay = 2  # seconds

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

                # Try parsing as JSON, handling code blocks
                try:
                    if content.startswith('```json') and content.endswith('```'):
                        content = content[7:-3].strip()  # Strip ```json and ```
                    parsed_data = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: try parsing raw content
                    try:
                        parsed_data = json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse API response as JSON: {content}")
                        raise ValueError(f"Invalid JSON response from API: {str(e)}")

                # Validate and structure the response
                structured_analysis = parsed_data.get('structured_analysis', {})
                summary_data = parsed_data.get('summary', {})

                default_field = ContractField(content="", score=None)
                analysis_fields = {
                    field: ContractField(
                        content=structured_analysis.get(field, {}).get('content', ''),
                        score=structured_analysis.get(field, {}).get('score')
                    ) if structured_analysis.get(field) else default_field
                    for field in [
                        'sick_leave', 'vacation', 'overtime', 'termination', 'confidentiality',
                        'non_compete', 'intellectual_property', 'governing_law', 'jurisdiction',
                        'dispute_resolution', 'liability', 'salary', 'benefits', 'work_hours',
                        'performance_evaluation', 'duties', 'responsibilities'
                    ]
                }

                analysis_result = ContractAnalysisResult(
                    structured_analysis=ContractAnalysis(
                        **analysis_fields,
                        overall_score=structured_analysis.get('overall_score')
                    ),
                    summary=ContractSummary(
                        executive_summary=summary_data.get('executive_summary', ''),
                        key_points=summary_data.get('key_points', ''),
                        potential_issues=summary_data.get('potential_issues', ''),
                        recommendations=summary_data.get('recommendations', '')
                    )
                )

                # Save analysis
                self.save_analysis(analysis_result, contract_name="analysis")
                return analysis_result.dict()

            except (requests.RequestException, ValueError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries} due to error: {str(e)}")
                    sleep(retry_delay)
                    continue
                logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                # Fallback response
                default_field = ContractField(content="", score=None)
                default_analysis = ContractAnalysis(
                    **{field: default_field for field in [
                        'sick_leave', 'vacation', 'overtime', 'termination', 'confidentiality',
                        'non_compete', 'intellectual_property', 'governing_law', 'jurisdiction',
                        'dispute_resolution', 'liability', 'salary', 'benefits', 'work_hours',
                        'performance_evaluation', 'duties', 'responsibilities'
                    ]},
                    overall_score=None
                )
                default_summary = ContractSummary(
                    executive_summary="Unable to generate summary due to API error.",
                    key_points="No key points available.",
                    potential_issues="No issues identified due to API error.",
                    recommendations="Please try again later or contact support."
                )
                analysis_result = ContractAnalysisResult(
                    structured_analysis=default_analysis,
                    summary=default_summary
                )
                self.save_analysis(analysis_result, contract_name="analysis_fallback")
                return analysis_result.dict()

    def save_analysis(self, analysis_result: ContractAnalysisResult, contract_name: str):
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