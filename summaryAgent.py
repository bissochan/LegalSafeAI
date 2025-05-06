import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict
import requests
import json
from datetime import datetime

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

class ContractAnalyzerAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found in .env file")
        self.output_dir = "contract_analyses"
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
    def analyze(self, contract: str, contract_name: str = None) -> ContractAnalysisResult:
        """
        Analyze the contract and provide both structured and narrative analysis.
        
        Args:
            contract: The contract text to analyze
            contract_name: Optional name for the contract
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
        {contract}
        """
        
        data = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "system", "content": "You are an expert legal analyst specialized in employment contracts. Provide detailed, structured analysis."},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # Add debug print to see raw API response
                print("Raw API response:", content)
                analysis_result = self._parse_response(content)
                return analysis_result
            else:
                raise ValueError("No valid response from API")
                
        except Exception as e:
            print(f"Error calling API: {e}")
            raise

    def _parse_response(self, content: str) -> ContractAnalysisResult:
        """Parse the API response using regex for more reliable extraction."""
        import re
        
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

        try:
            # Parse overall assessment
            overall_pattern = r'OVERALL_ASSESSMENT:\s*SCORE:\s*(\d+)\s*EXECUTIVE_SUMMARY:\s*(.*?)\s*KEY_POINTS:\s*(.*?)\s*POTENTIAL_ISSUES:\s*(.*?)\s*RECOMMENDATIONS:\s*(.*?)\s*END_ASSESSMENT'
            overall_match = re.search(overall_pattern, content, re.DOTALL)
            
            if not overall_match:
                raise ValueError("Failed to parse OVERALL_ASSESSMENT section")
                
            overall_score = int(overall_match.group(1))
            exec_summary = overall_match.group(2).strip()
            key_points = overall_match.group(3).strip()
            potential_issues = overall_match.group(4).strip()
            recommendations = overall_match.group(5).strip()

            # Parse field analysis
            field_pattern = r'(\w+):\s*CONTENT:\s*(.*?)\s*SCORE:\s*(\d+)\s*END_FIELD'
            field_matches = re.finditer(field_pattern, content, re.DOTALL)
            
            fields_found = 0
            for match in field_matches:
                field_name = match.group(1).lower().strip()
                content_text = match.group(2).strip()
                score = int(match.group(3))
                
                if field_name in default_fields:
                    default_fields[field_name] = ContractField(
                        content=content_text,
                        score=score
                    )
                    fields_found += 1
            
            if fields_found == 0:
                print("Warning: No fields found in FIELD_ANALYSIS")

            return ContractAnalysisResult(
                structured_analysis=ContractAnalysis(
                    **default_fields,
                    overall_score=overall_score
                ),
                summary=ContractSummary(
                    executive_summary=exec_summary,
                    key_points=key_points.replace("|", "\n"),
                    potential_issues=potential_issues.replace("|", "\n"),
                    recommendations=recommendations.replace("|", "\n")
                )
            )
        except Exception as e:
            print(f"Error parsing response: {e}")
            print("Raw content:")
            print(content)
            raise

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

    def print_analysis(self, analysis_result: ContractAnalysisResult):
        """
        Print the analysis results in a clean and formatted way.
        
        Args:
            analysis_result: The ContractAnalysisResult to print
        """
        print("\n" + "="*50)
        print("CONTRACT ANALYSIS REPORT")
        print("="*50 + "\n")

        # Print Structured Analysis
        print("STRUCTURED ANALYSIS")
        print("-"*30)
        structured = analysis_result.structured_analysis
        
        for field_name, field in structured.__class__.model_fields.items():
            value = getattr(structured, field_name)
            if value is not None:
                field_display = field_name.replace('_', ' ').title()
                
                if field_name == 'overall_score':
                    print(f"\n{field_display}: {value}/10")
                else:
                    print(f"\n{field_display}:")
                    print(f"Score: {value.score if value.score else 'N/A'}/10")
                    print(f"Analysis: {value.content}")
                    print("-" * 30)

        # Print Narrative Summary
        print("\n" + "="*50)
        print("NARRATIVE SUMMARY")
        print("="*50)
        
        summary = analysis_result.summary
        
        print("\nEXECUTIVE SUMMARY:")
        print("-"*30)
        print(summary.executive_summary)
        
        print("\nKEY POINTS:")
        print("-"*30)
        print(summary.key_points)
        
        print("\nPOTENTIAL ISSUES:")
        print("-"*30)
        print(summary.potential_issues)
        
        print("\nRECOMMENDATIONS:")
        print("-"*30)
        print(summary.recommendations)
        
        print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    analyzer = ContractAnalyzerAgent()

    sample_contract = """
    Articolo 1: Assunzione
    Il Sig. Rossi (Dipendente) è assunto da Bianchi S.p.A. (Datore di Lavoro) con un contratto a tempo indeterminato a partire dal 01/06/2025.

    Articolo 2: Mansioni e Responsabilità
    Il Dipendente svolgerà le mansioni di Project Manager, come specificato nell'allegato A. Sarà responsabile della gestione dei progetti assegnati, del coordinamento dei team e del rispetto delle scadenze. (Punteggio: 8)

    Articolo 3: Orario di Lavoro
    L'orario di lavoro è fissato in 40 ore settimanali, dal lunedì al venerdì, dalle 9:00 alle 18:00 con un'ora di pausa pranzo. Eventuali ore straordinarie dovranno essere preventivamente autorizzate e saranno retribuite come previsto dalla legge. (Punteggio: 9)

    Articolo 4: Retribuzione
    La retribuzione lorda annua è di €50.000, pagata in 13 mensilità. (Punteggio: 10)

    Articolo 5: Ferie
    Il Dipendente ha diritto a 4 settimane di ferie retribuite all'anno, da concordarsi con il Datore di Lavoro tenendo conto delle esigenze aziendali. (Punteggio: 7)

    Articolo 6: Congedo per Malattia
    In caso di malattia, il Dipendente dovrà avvisare tempestivamente il Datore di Lavoro e presentare il certificato medico entro 48 ore. Il trattamento economico sarà quello previsto dalla legge e dal CCNL applicato. (Punteggio: 7)

    Articolo 7: Cessazione del Contratto
    Il presente contratto può essere risolto da ciascuna delle parti con un preavviso di 3 mesi, salvo giusta causa. (Punteggio: 8)

    Articolo 8: Riservatezza
    Il Dipendente si impegna a mantenere la massima riservatezza su tutte le informazioni aziendali di cui verrà a conoscenza durante il rapporto di lavoro e anche dopo la sua cessazione. (Punteggio: 9)

    Articolo 9: Legge Applicabile e Foro Competente
    Il presente contratto è regolato dalla legge italiana. Per qualsiasi controversia derivante dal presente contratto, sarà competente il Foro di Verona. (Punteggio: 10)

    Punteggio Complessivo del Contratto: 8
    """

    try:
        result = analyzer.analyze(sample_contract, contract_name="Sample Contract")
        analyzer.print_analysis(result)
        
        # Save to JSON file
        json_path = analyzer.save_analysis(result, "Sample Contract")
        print(f"\nFull analysis saved to: {json_path}")
    except Exception as e:
        print(f"Error analyzing contract: {e}")
