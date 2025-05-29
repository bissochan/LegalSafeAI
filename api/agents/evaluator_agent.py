import requests
import json
from dotenv import load_dotenv
import os
import logging
import re
from typing import Dict, Any, List, Optional

# Configura il logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvaluatorAgent:
    def __init__(self):
        # Carica variabili d'ambiente
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

    def clean_json_response(self, response_text: str) -> str:
        """Tenta di estrarre un JSON valido da una risposta potenzialmente malformata."""
        if not response_text or response_text.isspace():
            logger.warning("Response text is empty or contains only whitespace")
            return "{}"  # Restituisci un JSON vuoto come fallback

        # Rimuove eventuali blocchi di codice markdown (es. ```json ... ```)
        response_text = re.sub(r'^```json\n|\n```$', '', response_text, flags=re.MULTILINE)
        
        # Rimuove spazi o caratteri non validi iniziali/finali
        response_text = response_text.strip()
        
        # Sostituisce caratteri di controllo non validi (es. \n, \t) all'interno delle stringhe
        def escape_control_chars(match):
            text = match.group(0)
            return text.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
        
        # Applica la sostituzione solo alle stringhe tra virgolette
        response_text = re.sub(r'"[^"]*"', escape_control_chars, response_text)
        
        # Cerca un oggetto JSON valido
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, response_text, re.DOTALL)
        if match:
            return match.group(0)
        
        # Se non trova un JSON, restituisci un JSON vuoto
        logger.warning(f"Could not extract valid JSON from response: {response_text}")
        return "{}"

    def evaluate(
        self,
        contract_text: str,
        shadow_analysis: Dict[str, Any],
        summary: Dict[str, Any],
        focal_points: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate contract with analysis data and optional focal points
        
        Args:
            contract_text: Raw contract text
            shadow_analysis: Deep analysis results
            summary: Contract summary
            focal_points: Optional list of areas to focus on
        """
        try:
            # Default evaluation areas
            evaluation_areas = {
                'liability': 0,
                'work_hours': 0,
                'compensation': 0,
                'termination': 0,
                'confidentiality': 0,
                'non_compete': 0,
                'benefits': 0,
                'intellectual_property': 0,
                'dispute_resolution': 0
            }

            # Prioritize focal points if provided
            if focal_points:
                for point in focal_points:
                    if point not in evaluation_areas:
                        evaluation_areas[point] = 0

            # For now, return a placeholder evaluation
            return {
                'evaluation': {
                    'overall_score': 8.5,
                    'scores': {
                        'clarity': 8.0,
                        'completeness': 9.0,
                        'risk_level': 7.5,
                        'fairness': 8.5
                    },
                    'recommendations': [
                        'Consider clarifying section 3.2',
                        'Add more specific terms in section 5'
                    ]
                }
            }

        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            return {'error': str(e)}