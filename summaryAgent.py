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
        
        prompt = f"""
        Analyze this contract and provide a complete analysis. For each section, include a score (1-10) in parentheses at the end of the analysis.

        Format each section as follows:
        field_name: <detailed analysis> (Punteggio: X)

        Include analysis for:
        - sick_leave
        - vacation
        - overtime
        - termination
        - confidentiality
        - non_compete
        - intellectual_property
        - governing_law
        - jurisdiction
        - dispute_resolution
        - liability
        - salary
        - benefits
        - work_hours
        - performance_evaluation
        - duties
        - responsibilities

        End with an overall score:
        overall_score: X

        Then provide:
        EXECUTIVE SUMMARY:
        ...

        Contract to analyze:
        {contract}
        """
        
        data = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "system", "content": "You are a legal expert analyzing employment contracts."},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                analysis_result = self._parse_response(content)
                self.save_analysis(analysis_result, contract_name)
                return analysis_result
            else:
                raise ValueError("No valid response from API")
                
        except Exception as e:
            print(f"Error calling API: {e}")
            raise

    def _parse_response(self, content: str) -> ContractAnalysisResult:
        """Parse the API response into a ContractAnalysisResult object."""
        structured_data = {}
        
        # Split the content into structured and narrative parts
        parts = content.split("EXECUTIVE SUMMARY:")
        
        # Parse structured analysis
        for line in parts[0].strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if key == 'overall_score':
                    try:
                        structured_data[key] = int(value)
                    except ValueError:
                        structured_data[key] = None
                    continue
                
                # Extract score if present (format: "... (Punteggio: X)")
                score = None
                content_value = value
                if "(Punteggio:" in value:
                    content_part, score_part = value.rsplit("(Punteggio:", 1)
                    try:
                        score = int(score_part.strip(" )"))
                        content_value = content_part.strip()
                    except ValueError:
                        pass
                
                if key in ContractAnalysis.model_fields and key != 'overall_score':
                    structured_data[key] = ContractField(
                        content=content_value,
                        score=score
                    )

        # Initialize summary parts with empty strings
        summary_parts = {
            "executive_summary": "",
            "key_points": "",
            "potential_issues": "",
            "recommendations": ""
        }
        
        # Parse narrative summary if it exists
        if len(parts) > 1:
            summary_text = parts[1]
            current_section = "executive_summary"
            
            for line in summary_text.split('\n'):
                if "KEY POINTS:" in line:
                    current_section = "key_points"
                    continue
                elif "POTENTIAL ISSUES:" in line:
                    current_section = "potential_issues"
                    continue
                elif "RECOMMENDATIONS:" in line:
                    current_section = "recommendations"
                    continue
                
                if current_section in summary_parts:
                    summary_parts[current_section] += line + "\n"
        
        # Clean up the summary parts
        for key in summary_parts:
            summary_parts[key] = summary_parts[key].strip()
        
        # Create the final result with proper ContractField instances
        analysis_data = {}
        for field in ContractAnalysis.model_fields:
            if field == 'overall_score':
                analysis_data[field] = structured_data.get(field)
            else:
                field_data = structured_data.get(field, {})
                analysis_data[field] = ContractField(
                    content=field_data.get('content', ''),
                    score=field_data.get('score')
                )
        
        return ContractAnalysisResult(
            structured_analysis=ContractAnalysis(**analysis_data),
            summary=ContractSummary(**summary_parts)
        )

    def save_analysis(self, analysis_result: ContractAnalysisResult, contract_name: str = None):
        """
        Save the complete analysis results to a JSON file with scores.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{timestamp}.json"
        if contract_name:
            safe_name = "".join(c for c in contract_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name}_{timestamp}.json"

        # Create detailed analysis with scores
        detailed_fields = {}
        structured = analysis_result.structured_analysis
        
        for field_name, field in structured.model_fields.items():
            value = getattr(structured, field_name)
            if value is not None:
                if field_name == 'overall_score':
                    detailed_fields[field_name] = {
                        "score": value,
                        "content": f"Overall contract score: {value}/10"
                    }
                else:
                    detailed_fields[field_name] = {
                        "score": value.score if hasattr(value, 'score') else None,
                        "content": value.content if hasattr(value, 'content') else str(value)
                    }

        analysis_data = {
            "metadata": {
                "timestamp": timestamp,
                "contract_name": contract_name or "unnamed_contract",
                "overall_score": structured.overall_score
            },
            "detailed_analysis": detailed_fields,
            "narrative_summary": {
                "executive_summary": analysis_result.summary.executive_summary,
                "key_points": analysis_result.summary.key_points,
                "potential_issues": analysis_result.summary.potential_issues,
                "recommendations": analysis_result.summary.recommendations
            }
        }

        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        print(f"Analysis saved to: {filepath}")
        return filepath

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
        
        for field_name, field in structured.model_fields.items():
            value = getattr(structured, field_name)
            if value is not None:
                field_display = field_name.replace('_', ' ').title()
                
                if field_name == 'overall_score':
                    print(f"\n{field_display}: {value}/10")
                else:
                    print(f"\n{field_display} (Score: {value.score}/10):")
                    print(f"{value.content}")

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
