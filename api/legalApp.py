from flask import Flask, request, jsonify, session, render_template, url_for
from flask_session import Session
import os
import secrets
import requests
import logging
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Import routes from routes/
from routes.document_routes import document_bp
from routes.shadow_routes import shadow_bp
from routes.summary_routes import summary_bp
from routes.evaluator_routes import evaluator_bp
from routes.chat_routes import chat_bp
from routes.translator_routes import translator_bp
from routes.student_routes import student_bp
from routes.web_search_routes import web_search_bp

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


app = Flask(__name__, 
    template_folder="../templates",
    static_folder="../static",
)

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
app.register_blueprint(translator_bp, url_prefix='/api/translator')
app.register_blueprint(student_bp, url_prefix='/api/student')
app.register_blueprint(web_search_bp, url_prefix='/api/web_search')

@app.route('/')
def index():
    """Serve the main application page"""
    logger.debug("Attempting to render index.html")
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}")
        raise

@app.route('/analyze', methods=['POST'])
def analyze_contract():
    """Main endpoint that orchestrates the analysis pipeline"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            logger.error("No text provided in analyze request")
            return jsonify({'error': 'No text provided'}), 400

        user_language = data.get('language', 'en')
        contract_text = data['text']
        
        logger.debug("Starting shadow analysis")
        shadow_response = requests.post(
            f"{request.host_url}api/shadow/analyze",
            json={'text': contract_text, 'language': 'en'}
        )
        if shadow_response.status_code != 200:
            logger.error(f"Shadow analysis failed with status {shadow_response.status_code}")
            return jsonify({'error': 'Shadow analysis failed'}), shadow_response.status_code

        shadow_analysis = shadow_response.json()['analysis']
        
        logger.debug("Starting summary analysis")
        summary_response = requests.post(
            f"{request.host_url}api/summary/analyze",
            json={'text': contract_text, 'language': 'en'}
        )
        if summary_response.status_code != 200:
            logger.error(f"Summary analysis failed with status {summary_response.status_code}")
            return jsonify({'error': 'Summary analysis failed'}), summary_response.status_code
            
        summary = summary_response.json()['summary']
        
        logger.debug("Starting evaluation")
        eval_response = requests.post(
            f"{request.host_url}api/evaluator/evaluate",
            json={
                'text': contract_text,
                'shadow_analysis': shadow_analysis,
                'summary': summary,
                'language': 'en'
            }
        )
        if eval_response.status_code != 200:
            logger.error(f"Evaluation failed with status {eval_response.status_code}")
            return jsonify({'error': 'Evaluation failed'}), eval_response.status_code
        
        analysis_results = {
            'status': 'success',
            'document_text': contract_text,
            'shadow_analysis': shadow_analysis,
            'summary': summary,
            'evaluation': eval_response.json().get('evaluation', {}),
            'original_language': 'en'
        }

        session['english_analysis_results'] = analysis_results
        session['contract_text'] = contract_text
        session['chat_language'] = user_language
        logger.debug(f"Stored English analysis results and chat language ({user_language}) in session")

        if user_language != 'en':
            logger.debug(f"Translating analysis results to {user_language}")
            translation_response = requests.post(
                f"{request.host_url}api/translator/translate",
                json={
                    'content': analysis_results,
                    'language': user_language
                }
            )
            
            if translation_response.status_code == 200:
                translated_data = translation_response.json()
                if translated_data['status'] == 'success':
                    analysis_results = translated_data['translated_content']
                    analysis_results['original_language'] = 'en'
                    analysis_results['translated_to'] = user_language
                    logger.debug(f"Translated results to {user_language}")
                else:
                    logger.error(f"Translation failed: {translated_data.get('error')}")
            else:
                logger.error(f"Translation request failed with status {translation_response.status_code}")

        return jsonify(analysis_results)

    except Exception as e:
        logger.error(f"Analysis pipeline error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/retranslate', methods=['POST'])
def retranslate_analysis():
    """Endpoint to retranslate cached analysis results"""
    try:
        data = request.get_json()
        if not data or 'language' not in data:
            logger.error("No language provided in retranslate request")
            return jsonify({'error': 'No language provided'}), 400

        user_language = data['language']
        logger.debug(f"Retranslating to language: {user_language}")

        if user_language == 'en':
            if 'english_analysis_results' in session:
                logger.debug("Returning cached English results")
                return jsonify(session['english_analysis_results'])
            logger.error("No cached analysis results for English")
            return jsonify({'error': 'No cached analysis results'}), 400

        if 'english_analysis_results' not in session:
            logger.error("No analysis results to translate")
            return jsonify({'error': 'No analysis results to translate'}), 400

        logger.debug(f"Sending translation request for {user_language}")
        translation_response = requests.post(
            f"{request.host_url}api/translator/translate",
            json={
                'content': session['english_analysis_results'],
                'language': user_language
            }
        )

        if translation_response.status_code != 200:
            logger.error(f"Translation failed with status {translation_response.status_code}")
            return jsonify({'error': 'Translation failed'}), translation_response.status_code

        translated_data = translation_response.json()
        if translated_data['status'] == 'success':
            translated_results = translated_data['translated_content']
            translated_results['original_language'] = 'en'
            translated_results['translated_to'] = user_language
            logger.debug(f"Translated results: {translated_results}")
            return jsonify(translated_results)

        logger.error(f"Translation failed: {translated_data.get('error')}")
        return jsonify({'error': 'Translation failed'}), 500

    except Exception as e:
        logger.error(f"Retranslation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/chat/update_language', methods=['POST'])
def update_chat_language():
    """Update the language of the current chat session"""
    try:
        data = request.get_json()
        if not data or 'language' not in data:
            logger.error("No language provided in chat language update request")
            return jsonify({'error': 'No language provided'}), 400

        language = data['language']
        session['chat_language'] = language
        logger.debug(f"Updated chat session language to {language}")
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.error(f"Chat language update error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)