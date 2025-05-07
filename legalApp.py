from flask import Flask, render_template, request, jsonify
from Agent.shadowAgent import ShadowAgent
from Agent.summaryAgent import ContractAnalyzerAgent
from Agent.ResponseEvaluatorAgent import ResponseEvaluator
from Agent.pdfExtractor import PdfTextExtractor
from jsonHandler import add_agent_response_and_scores
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize agents
shadow_agent = ShadowAgent()
summary_agent = ContractAnalyzerAgent()
eval_agent = ResponseEvaluator()
pdf_extractor = PdfTextExtractor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_contract():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    try:
        # Save and process the file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract text from PDF
        contract_text = pdf_extractor.extract_text_from_pdf(filepath, lang='eng')

        # Get analyses
        shadow_analysis = shadow_agent.analyze(contract_text)
        summary_analysis = summary_agent.analyze(contract_text)

        # Get evaluations
        shadow_eval = eval_agent.evaluate(contract_text, str(shadow_analysis), "shadow")
        summary_eval = eval_agent.evaluate(contract_text, str(summary_analysis), "summary")

        # Extract scores
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

        # Generate initial JSON
        json_path = summary_agent.save_analysis(summary_analysis, "Contract Analysis")
        
        # Read and modify JSON with evaluations
        with open(json_path, 'r', encoding='utf-8') as f:
            initial_json = f.read()
        
        final_json = add_agent_response_and_scores(
            initial_json,
            str(shadow_analysis),
            shadow_scores,
            summary_scores
        )

        # Clean up
        os.remove(filepath)
        
        return jsonify({
            'status': 'success',
            'data': json.loads(final_json)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)