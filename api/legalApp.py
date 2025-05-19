from flask import Flask, request, jsonify, session, render_template, url_for
from flask_session import Session
import os
import secrets
import requests
import logging
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Import routes
from routes.document_routes import document_bp
from routes.shadow_routes import shadow_bp
from routes.summary_routes import summary_bp
from routes.evaluator_routes import evaluator_bp
from routes.chat_routes import chat_bp

app = Flask(__name__, 
    template_folder='../templates',
    static_folder='../static'
)

# Add debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure app
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32)),
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR='flask_session',
    PERMANENT_SESSION_LIFETIME=3600,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size
)

# Initialize Flask-Session
Session(app)

# Register blueprints
app.register_blueprint(document_bp, url_prefix='/api/document')
app.register_blueprint(shadow_bp, url_prefix='/api/shadow')
app.register_blueprint(summary_bp, url_prefix='/api/summary')
app.register_blueprint(evaluator_bp, url_prefix='/api/evaluator')
app.register_blueprint(chat_bp, url_prefix='/api/chat')

# Add root route to serve the index.html template
@app.route('/')
def index():
    """Serve the main application page"""
    logger.debug(f"Template folder: {app.template_folder}")
    logger.debug(f"Current working directory: {os.getcwd()}")
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_contract():
    """Main endpoint that orchestrates the analysis pipeline"""
    try:
        # Get data from JSON request
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400

        language = data.get('language', 'en')
        contract_text = data['text']
        
        # Step 1: Shadow analysis
        shadow_response = requests.post(
            f"{request.host_url}api/shadow/analyze",
            json={'text': contract_text, 'language': language}
        )
        if shadow_response.status_code != 200:
            return jsonify({'error': 'Shadow analysis failed'}), shadow_response.status_code
            
        shadow_analysis = shadow_response.json()['analysis']
        
        # Step 2: Contract summary
        summary_response = requests.post(
            f"{request.host_url}api/summary/analyze",
            json={'text': contract_text, 'language': language}
        )
        if summary_response.status_code != 200:
            return jsonify({'error': 'Summary analysis failed'}), summary_response.status_code
            
        summary = summary_response.json()['summary']
        
        # Step 3: Evaluation
        eval_response = requests.post(
            f"{request.host_url}api/evaluator/evaluate",
            json={
                'text': contract_text,
                'shadow_analysis': shadow_analysis,
                'summary': summary,
                'language': language
            }
        )
        if eval_response.status_code != 200:
            return jsonify({'error': 'Evaluation failed'}), eval_response.status_code
        
        # Return combined results
        return jsonify({
            'status': 'success',
            'document_text': contract_text,
            'shadow_analysis': shadow_analysis,
            'summary': summary,
            'evaluation': eval_response.json().get('evaluation', {})
        })

    except Exception as e:
        logger.error(f"Analysis pipeline error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)