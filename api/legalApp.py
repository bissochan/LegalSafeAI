from flask import Flask, render_template, request, jsonify, session
import os
import json
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging
from dotenv import load_dotenv

# Lazy loading of agents
def get_shadow_agent():
    from Agent.shadowAgent import ShadowAgent
    return ShadowAgent()

def get_summary_agent():
    from Agent.summaryAgent import ContractAnalyzerAgent
    return ContractAnalyzerAgent()

def get_chat_agent():
    from Agent.legalChatAgent import LegalChatAgent
    return LegalChatAgent()

def get_pdf_extractor():
    from utils.pdfExtractor import PdfTextExtractor
    return PdfTextExtractor()

# Initialize Flask app
app = Flask(__name__, template_folder='../templates')
load_dotenv()

# Basic config
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', os.urandom(24)),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024
)

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_contract():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['file']
        if not file or not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Invalid file'}), 400

        # Lazy load agents only when needed
        pdf_extractor = get_pdf_extractor()
        shadow_agent = get_shadow_agent()
        summary_agent = get_summary_agent()

        # Process file
        text = pdf_extractor.extract_text_from_pdf(file)
        shadow_analysis = shadow_agent.analyze(text)
        summary_analysis = summary_agent.analyze(text)

        return jsonify({
            'status': 'success',
            'data': {
                'shadow': shadow_analysis,
                'summary': summary_analysis
            }
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'No message provided'}), 400

        chat_agent = get_chat_agent()
        response = chat_agent.chat(message)

        return jsonify({
            'status': 'success',
            'response': response
        })

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Remove session cleanup and scheduler for Vercel