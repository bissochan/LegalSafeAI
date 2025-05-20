import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict
import requests
import json
import re
from datetime import datetime
from time import sleep

class ContractField(BaseModel):
    content: str = Field(description="The content of the field")
    score: Optional[int] = Field(default=None, description="Score from 1-10")

class ContractAnalysis(BaseModel):
    """
    Analisi di un contratto di lavoro con punteggi.
    """
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
    overall_score: Optional[int] = Field(default=None, description="Overall contract score (1-10)")

class ContractSummary(BaseModel):
    """Riassunto testuale del contratto"""
    executive_summary: str = Field(description="Riassunto generale del contratto")
    key_points: str = Field(description="Punti chiave del contratto")
    potential_issues: str = Field(description="Potenziali problemi o aree di attenzione")
    recommendations: str = Field(description="Raccomandazioni per miglioramenti")

class ContractAnalysisResult(BaseModel):
    """Risultato completo dell'analisi del contratto"""
    structured_analysis: ContractAnalysis
    summary: ContractSummary

class SummaryAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found in .env file")
        self.output_dir = "contract_analyses"
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
    def analyze(self, contract_text: str, language: str = 'en') -> Dict:
        system_prompt = f"""Analyze this contract and provide a structured analysis in {language}.
        Return the response as a pure JSON object without any Markdown code block markers (e.g., ```json or ```).
        Ensure the JSON is syntactically correct, with proper commas between fields and no trailing commas.
        Maintain this exact JSON structure, even if responding in a language different from English. The structure's field names must remain in English, but the content should be in the specified language ({language}).
        """
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Analyze this employment contract. You must respond using EXACTLY this format:

        GENERAL_SUMMARY:
        [Write a comprehensive overview here]
        END_SUMMARY

        FIELD_ANALYSIS:
        sick_leave:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        vacation:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        overtime:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        termination:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        confidentiality:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        non_compete:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        intellectual_property:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        governing_law:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        jurisdiction:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        dispute_resolution:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        liability:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        salary:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        benefits:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        work_hours:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        performance_evaluation:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        duties:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        responsibilities:
        CONTENT: [detailed explanation]
        SCORE: [number 1-10]
        END_FIELD

        OVERALL_ASSESSMENT:
        SCORE: [number 1-10]
        EXECUTIVE_SUMMARY: [final summary]
        KEY_POINTS: [bullet points separated by |]
        POTENTIAL_ISSUES: [bullet points separated by |]
        RECOMMENDATIONS: [bullet points separated by |]
        END_ASSESSMENT

        Contract to analyze:
        {contract_text}
        """
        
        data = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    if not content:
                        raise ValueError("Empty response content from API")
                    analysis_result = self._parse_response(content)
                    return analysis_result
                else:
                    raise ValueError("No valid response from API")
                    
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    print(f"Error calling API after {max_retries} attempts: {e}")
                    raise
                print(f"API request failed: {e}. Retrying in {2 ** attempt} seconds...")
                sleep(2 ** attempt)
            except Exception as e:
                print(f"Error processing API response: {e}")
                raise

    def _parse_response(self, content: str) -> ContractAnalysisResult:
        """Parse the API response into a ContractAnalysisResult, handling various response formats."""
        # Save raw content for debugging
        debug_file = os.path.join(self.output_dir, f"raw_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Warning: Could not save raw response to {debug_file}: {e}")

        # Clean the response: remove Markdown code block markers and extra whitespace
        cleaned_content = content.strip()
        cleaned_content = re.sub(r'^```json\s*|\s*```$', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = cleaned_content.strip()

        # Fix common JSON syntax errors
        # 1. Add colon to END_SUMMARY if missing
        cleaned_content = re.sub(r'("END_SUMMARY")\s*([,\}])', r'\1: ""\2', cleaned_content)
        # 2. Add colon to END_ASSESSMENT if missing
        cleaned_content = re.sub(r'("END_ASSESSMENT")\s*([,\}])', r'\1: ""\2', cleaned_content)
        # 3. Replace END_ASSESSMENT: null with END_ASSESSMENT: ""
        cleaned_content = re.sub(r'("END_ASSESSMENT":\s*)null', r'\1""', cleaned_content)
        # 4. Add comma before END_FIELD if missing
        cleaned_content = re.sub(r'("SCORE":\s*\d+)\s+("END_FIELD")', r'\1,\2', cleaned_content)
        # 5. Ensure END_FIELD is properly formatted as key-value pair
        cleaned_content = re.sub(r'("END_FIELD")\s*([,\}])', r'\1: ""\2', cleaned_content)
        # 6. Replace END_FIELD: null with END_FIELD: ""
        cleaned_content = re.sub(r'("END_FIELD":\s*)null', r'\1""', cleaned_content)
        # 7. Add comma before END_ASSESSMENT if missing
        cleaned_content = re.sub(r'("RECOMMENDATIONS":\s*".*?")\s+("END_ASSESSMENT")', r'\1,\2', cleaned_content, flags=re.DOTALL)
        # 8. Add comma after SCORE in OVERALL_ASSESSMENT if missing
        cleaned_content = re.sub(r'("SCORE":\s*\d+)\s+("EXECUTIVE_SUMMARY")', r'\1,\2', cleaned_content)
        # 9. Add commas between other OVERALL_ASSESSMENT fields if missing
        cleaned_content = re.sub(r'("EXECUTIVE_SUMMARY":\s*".*?")\s+("KEY_POINTS")', r'\1,\2', cleaned_content, flags=re.DOTALL)
        cleaned_content = re.sub(r'("KEY_POINTS":\s*".*?")\s+("POTENTIAL_ISSUES")', r'\1,\2', cleaned_content, flags=re.DOTALL)
        cleaned_content = re.sub(r'("POTENTIAL_ISSUES":\s*".*?")\s+("RECOMMENDATIONS")', r'\1,\2', cleaned_content, flags=re.DOTALL)

        # Attempt to parse the cleaned JSON
        try:
            data = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print("Cleaned content:")
            print(cleaned_content)
            # Save cleaned content for further debugging
            cleaned_debug_file = os.path.join(self.output_dir, f"cleaned_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            try:
                with open(cleaned_debug_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                print(f"Cleaned content saved to: {cleaned_debug_file}")
            except Exception as ex:
                print(f"Warning: Could not save cleaned content to {cleaned_debug_file}: {ex}")
            raise ValueError("Invalid JSON format in response after cleaning")

        # Validate the response structure
        if not isinstance(data, dict):
            raise ValueError("Response is not a valid JSON object")

        # Initialize default fields
        default_fields = {
            'sick_leave': ContractField(content="", score=None),
            'vacation': ContractField(content="", score=None),
            'overtime': ContractField(content="", score=None),
            'termination': ContractField(content="", score=None),
            'confidentiality': ContractField(content="", score=None),
            'non_compete': ContractField(content="", score=None),
            'intellectual_property': ContractField(content="", score=None),
            'governing_law': ContractField(content="", score=None),
            'jurisdiction': ContractField(content="", score=None),
            'dispute_resolution': ContractField(content="", score=None),
            'liability': ContractField(content="", score=None),
            'salary': ContractField(content="", score=None),
            'benefits': ContractField(content="", score=None),
            'work_hours': ContractField(content="", score=None),
            'performance_evaluation': ContractField(content="", score=None),
            'duties': ContractField(content="", score=None),
            'responsibilities': ContractField(content="", score=None),
        }

        # Parse field analysis
        field_analysis = data.get('FIELD_ANALYSIS', {})
        if not isinstance(field_analysis, dict):
            print("Warning: FIELD_ANALYSIS is missing or invalid. Using default empty fields.")
            field_analysis = {}

        for field_name, field_data in field_analysis.items():
            if field_name.lower() in default_fields:
                if not isinstance(field_data, dict):
                    print(f"Warning: Invalid data for field {field_name}. Skipping.")
                    continue
                content = field_data.get('CONTENT', '')
                score = field_data.get('SCORE')
                # Validate score
                if score is not None:
                    try:
                        score = int(score)
                        if not 1 <= score <= 10:
                            print(f"Warning: Invalid score {score} for {field_name}. Setting to None.")
                            score = None
                    except (TypeError, ValueError):
                        print(f"Warning: Invalid score format for {field_name}. Setting to None.")
                        score = None
                default_fields[field_name.lower()] = ContractField(
                    content=str(content),
                    score=score
                )

        # Parse overall assessment
        overall = data.get('OVERALL_ASSESSMENT', {})
        if not isinstance(overall, dict):
            print("Warning: OVERALL_ASSESSMENT is missing or invalid. Using defaults.")
            overall = {}

        overall_score = overall.get('SCORE')
        try:
            overall_score = int(overall_score) if overall_score is not None else None
            if overall_score is not None and not 1 <= overall_score <= 10:
                print(f"Warning: Invalid overall score {overall_score}. Setting to None.")
                overall_score = None
        except (TypeError, ValueError):
            print("Warning: Invalid overall score format. Setting to None.")
            overall_score = None

        exec_summary = str(overall.get('EXECUTIVE_SUMMARY', ''))
        key_points = str(overall.get('KEY_POINTS', '')).split('|')
        potential_issues = str(overall.get('POTENTIAL_ISSUES', '')).split('|')
        recommendations = str(overall.get('RECOMMENDATIONS', '')).split('|')

        return ContractAnalysisResult(
            structured_analysis=ContractAnalysis(
                **default_fields,
                overall_score=overall_score
            ),
            summary=ContractSummary(
                executive_summary=exec_summary,
                key_points='\n'.join(p.strip() for p in key_points if p.strip()),
                potential_issues='\n'.join(p.strip() for p in potential_issues if p.strip()),
                recommendations='\n'.join(r.strip() for r in recommendations if r.strip())
            )
        )

    def save_analysis(self, analysis_result: ContractAnalysisResult, contract_name: str = None):
        """Save the complete analysis results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{timestamp}.json"
        if contract_name:
            safe_name = "".join(c for c in contract_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name}_{timestamp}.json"

        # Convert the analysis result to a dictionary
        analysis_data = {
            "metadata": {
                "timestamp": timestamp,
                "contract_name": contract_name or "unnamed_contract",
                "overall_score": analysis_result.structured_analysis.overall_score
            },
            "structured_analysis": {},
            "summary": {
                "executive_summary": analysis_result.summary.executive_summary,
                "key_points": [kp.strip() for kp in analysis_result.summary.key_points.split("\n") if kp.strip()],
                "potential_issues": [pi.strip() for pi in analysis_result.summary.potential_issues.split("\n") if pi.strip()],
                "recommendations": [r.strip() for r in analysis_result.summary.recommendations.split("\n") if r.strip()]
            }
        }

        # Process each field in the structured analysis
        for field_name in [
            'sick_leave', 'vacation', 'overtime', 'termination', 'confidentiality',
            'non_compete', 'intellectual_property', 'governing_law', 'jurisdiction',
            'dispute_resolution', 'liability', 'salary', 'benefits', 'work_hours',
            'performance_evaluation', 'duties', 'responsibilities'
        ]:
            field = getattr(analysis_result.structured_analysis, field_name)
            if field:
                analysis_data["structured_analysis"][field_name] = {
                    "content": field.content,
                    "score": field.score
                }
            else:
                analysis_data["structured_analysis"][field_name] = {
                    "content": "",
                    "score": None
                }

        # Ensure the output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Save to JSON file
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            print(f"Analysis saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving analysis to JSON: {e}")
            raise

    def _extract_score(self, text: str) -> Optional[int]:
        """Extract score from text if present (format: "... (Punteggio: X)")"""
        if not text:
            return None
        try:
            if "(Punteggio:" in text:
                score_part = text.split("(Punteggio:")[-1]
                return int(score_part.strip(" )"))
        except:
            pass
        return None