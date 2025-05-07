import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

# Configura il logging
logging.basicConfig(level=logging.DEBUG)  # Impostato su DEBUG per maggiore visibilità
logger = logging.getLogger(__name__)

def create_evaluation_json(agent_response: str, scores_set1: Dict[str, float], scores_set2: Dict[str, float]) -> dict:
    """Creates a JSON structure for evaluation results"""
    logger.info("Creating evaluation JSON structure...")
    logger.debug(f"Agent response: {agent_response[:100]}...")
    logger.debug(f"Shadow scores: {scores_set1}")
    logger.debug(f"Summary scores: {scores_set2}")

    # Calcola la media dei punteggi
    def calculate_average(scores: Dict[str, float]) -> float:
        valid_scores = [score for score in scores.values() if isinstance(score, (int, float))]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0

    return {
        "evaluation": {  # Nodo evaluation direttamente, senza evaluation_data
            "shadow_analysis": {
                "content": agent_response,
                "evaluation": {
                    "scores": scores_set1,
                    "average": calculate_average(scores_set1),
                    "model_results": {
                        model: {
                            "score": score,
                            "evaluation": {}  # Vuoto, poiché le explanation sono in agent_response
                        }
                        for model, score in scores_set1.items()
                    }
                }
            },
            "summary_evaluation": {
                "scores": scores_set2,
                "average": calculate_average(scores_set2),
                "model_results": {
                    model: {
                        "score": score,
                        "evaluation": {}  # Vuoto, poiché le explanation sono in agent_response
                    }
                    for model, score in scores_set2.items()
                }
            }
        }
    }

def merge_json_data(summary_json: str, evaluation_data: dict) -> str:
    """Merges the summary JSON with evaluation data"""
    try:
        logger.info("Starting JSON merge process...")
        
        # Parse summary JSON
        summary_data = json.loads(summary_json)
        logger.info("Successfully parsed summary JSON")
        logger.debug(f"Summary JSON structure: {json.dumps(summary_data, indent=2)}")
        
        # Crea una nuova struttura combinata
        merged_data = {
            "metadata": summary_data.get("metadata", {}),
            "structured_analysis": summary_data.get("structured_analysis", {}),
            "summary": summary_data.get("summary", {}),
            "evaluation": evaluation_data.get("evaluation", {})  # Prende direttamente evaluation
        }
        
        logger.info("Successfully merged JSON structures")
        logger.debug(f"Merged JSON structure: {json.dumps(merged_data, indent=2)}")
        
        # Serializza in JSON con formattazione
        merged_json = json.dumps(merged_data, indent=2, ensure_ascii=False)
        logger.info("Successfully serialized merged data to JSON")
        
        return merged_json
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        raise ValueError(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise Exception(f"Error merging JSON: {str(e)}")

def save_json_to_file(json_str: str, filename: str = None) -> str:
    """Saves the JSON string to a file in the contract_analysis_complete directory"""
    try:
        output_dir = "contract_analysis_complete"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"contract_analysis_{timestamp}.json"
        
        # Ensure filename has .json extension
        if not filename.endswith('.json'):
            filename += '.json'
        
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        
        logger.info(f"JSON saved successfully to {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving JSON to file: {str(e)}")
        raise

def add_agent_response_and_scores(json_str: str, agent_response: str, 
                                 scores_set1: Dict[str, float], scores_set2: Dict[str, float],
                                 output_filename: str = "merged_contract_analysis.json") -> str:
    """Main function to handle the JSON processing and save to file"""
    try:
        logger.info(f"Processing JSON with agent_response: {agent_response[:100]}...")
        logger.debug(f"scores_set1: {scores_set1}")
        logger.debug(f"scores_set2: {scores_set2}")
        
        # Crea evaluation JSON
        evaluation_json = create_evaluation_json(agent_response, scores_set1, scores_set2)
        logger.debug(f"Evaluation JSON: {json.dumps(evaluation_json, indent=2)}")
        
        # Merge JSONs
        final_json = merge_json_data(json_str, evaluation_json)
        
        # Salva il JSON nella cartella contract_analysis_complete
        saved_path = save_json_to_file(final_json, output_filename)
        
        return final_json
        
    except Exception as e:
        logger.error(f"Error in JSON processing: {str(e)}")
        raise

# Esempio di utilizzo
if __name__ == "__main__":
    # JSON iniziale (esempio, sostituisci con il tuo)
    initial_json = '''{
      "metadata": {
        "timestamp": "20250507_134113",
        "contract_name": "Contract Analysis",
        "overall_score": 5
      },
      "structured_analysis": {...},
      "summary": {...}
    }'''

    # Dati di esempio
    agent_response = "This is the shadow analysis of the contract, highlighting key issues..."
    shadow_scores = {
        "google/gemini-2.0-flash-001": 95,
        "openai/gpt-4o": 90,
        "meta-llama/llama-3.1-70b-instruct": 95
    }
    summary_scores = {
        "google/gemini-2.0-flash-001": 95,
        "openai/gpt-4o": 92,
        "meta-llama/llama-3.1-70b-instruct": 80
    }

    # Esegui il merge e salva
    final_json = add_agent_response_and_scores(
        initial_json,
        agent_response,
        shadow_scores,
        summary_scores,
        output_filename="merged_contract_analysis_20250507_134113.json"
    )
    print(final_json)