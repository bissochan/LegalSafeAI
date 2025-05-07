from api.Agent.shadowAgent import ShadowAgent
from api.Agent.pdfExtractor import PdfTextExtractor
from api.Agent.summaryAgent import ContractAnalyzerAgent
from api.Agent.ResponseEvaluatorAgent import ResponseEvaluator
from api.jsonHandler import add_agent_response_and_scores
import json

if __name__ == "__main__":
    # Initialize agents
    ShadAgent = ShadowAgent()
    SummAgent = ContractAnalyzerAgent()
    EvalAgent = ResponseEvaluator()

    # Set up PDF extractor
    extractor = PdfTextExtractor()
    pdf_file = "esempio_contratto_2.pdf"
    language = 'eng'

    try:
        # Extract text from PDF
        contract = extractor.extract_text_from_pdf(pdf_file, lang=language)
        
        # Shadow Analysis
        print("\n" + "="*80)
        print("SHADOW ANALYSIS (Potential Issues and Risks):")
        print("="*80)
        shadow_analysis = ShadAgent.analyze(contract)
        print(shadow_analysis)
        
        # Evaluate Shadow Analysis
        print("\n" + "="*80)
        print("SHADOW ANALYSIS EVALUATION:")
        print("="*80)
        shadow_eval = EvalAgent.evaluate(contract, str(shadow_analysis), "shadow")
        print(f"Average accuracy score: {shadow_eval['average_score']}%")
        print(f"Analysis is {'correct' if shadow_eval['is_correct'] else 'potentially inaccurate'}")
        print("\nModel evaluations:")
        for model, result in shadow_eval['model_results'].items():
            if 'error' in result:
                print(f"{model}: Error - {result['error']}")
            else:
                print(f"{model}: Score {result['accuracy_score']}% - {result['explanation']}")
        
        # Summary Analysis
        print("\n" + "="*80)
        print("DETAILED CONTRACT ANALYSIS:")
        print("="*80)
        summary_analysis = SummAgent.analyze(contract)
        SummAgent.print_analysis(summary_analysis)
        
        # Evaluate Summary Analysis
        print("\n" + "="*80)
        print("SUMMARY ANALYSIS EVALUATION:")
        print("="*80)
        summary_eval = EvalAgent.evaluate(contract, str(summary_analysis), "summary")
        print(f"Average accuracy score: {summary_eval['average_score']}%")
        print(f"Analysis is {'correct' if summary_eval['is_correct'] else 'potentially inaccurate'}")
        print("\nModel evaluations:")
        for model, result in summary_eval['model_results'].items():
            if 'error' in result:
                print(f"{model}: Score {result['accuracy_score']}% - {result['explanation']}")
        
        # Save initial summary analysis to JSON
        json_path = SummAgent.save_analysis(summary_analysis, "Contract Analysis")
        
        # Read the saved JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            initial_json = f.read()
        
        # Extract scores from evaluations
        shadow_scores = {
            model: result.get('accuracy_score', 0) 
            for model, result in shadow_eval['model_results'].items()
            if 'accuracy_score' in result
        }
        
        summary_scores = {
            model: result.get('accuracy_score', 0) 
            for model, result in summary_eval['model_results'].items()
            if 'accuracy_score' in result
        }
        
        # Add shadow analysis and evaluation scores to JSON
        modified_json = add_agent_response_and_scores(
            initial_json,
            str(shadow_analysis),
            shadow_scores,
            summary_scores
        )
        
        # Save the modified JSON
        modified_path = json_path.replace('.json', '_with_eval.json')
        with open(modified_path, 'w', encoding='utf-8') as f:
            f.write(modified_json)
            
        print(f"\nFull analysis with evaluations saved to: {modified_path}")
        
    except Exception as e:
        print(f"Error processing contract: {e}")