import json

def add_agent_response_and_scores(json_str, agent_response, scores_set1, scores_set2):
    """
    Aggiunge una risposta dell'agente e due set di punteggi di evaluation al JSON.
    
    Args:
        json_str (str): Stringa JSON del contratto.
        agent_response (str): Risposta dell'agente che analizza le zone problematiche.
        scores_set1 (dict): Primo set di punteggi {'model1': int, 'model2': int, 'model3': int}.
        scores_set2 (dict): Secondo set di punteggi {'model1': int, 'model2': int, 'model3': int}.
    
    Returns:
        str: JSON modificato come stringa.
    """
    try:
        # Parsa il JSON
        data = json.loads(json_str)
        
        # Aggiungi la risposta dell'agente e i punteggi nella sezione summary
        data['summary']['agent_response'] = agent_response
        data['summary']['evaluation_scores'] = {
            'set1': scores_set1,
            'set2': scores_set2
        }
        
        # Ritorna il JSON modificato come stringa
        return json.dumps(data, indent=2)
    
    except json.JSONDecodeError as e:
        return f"Errore nel parsing del JSON: {str(e)}"
    except Exception as e:
        return f"Errore generico: {str(e)}"

# Esempio di utilizzo
if __name__ == "__main__":
    # JSON di esempio (tratto dal tuo input)
    sample_json = '''
    {
      "metadata": {
        "timestamp": "20250506_224833",
        "contract_name": "Sample Contract",
        "overall_score": 5
      },
      "structured_analysis": {},
      "summary": {
        "executive_summary": "This employment contract is a basic agreement...",
        "key_points": [],
        "potential_issues": [],
        "recommendations": []
      }
    }
    '''
    
    # Esempio di risposta dell'agente
    agent_response = ("L'analisi evidenzia lacune significative nella protezione dell'azienda, "
                     "specialmente per l'assenza di clausole di non concorrenza e proprietà intellettuale. "
                     "Si consiglia un'immediata revisione per includere tali clausole e chiarire i benefici.")
    
    # Esempio di punteggi
    scores_set1 = {"model1": 8, "model2": 7, "model3": 9}
    scores_set2 = {"model1": 6, "model2": 8, "model3": 7}
    
    # Chiama la funzione
    modified_json = add_agent_response_and_scores(sample_json, agent_response, scores_set1, scores_set2)
    
    # Stampa il risultato
    print(modified_json)