# api/legalApp.py
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
    SESSION_COOKIE_SAME_SITE='Lax',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size
)

# Ensure session directory exists
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])

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
    logger.debug("Rendering index.html")
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}")
        raise

@app.route('/analyze', methods=['POST'])
def analyze_contract():
    """Perform contract analysis in English and translate to selected language"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            logger.error("No text provided in analyze request")
            return jsonify({'status': 'error', 'error': 'No text provided'}), 400

        user_language = data.get('language', 'en')
        contract_text = data['text']
        focal_points = data.get('focal_points', None)
        logger.debug(f"Analyzing contract with language: {user_language}")

        # Perform shadow analysis in English
        logger.debug("Starting shadow analysis")
        shadow_response = requests.post(
            f"{request.host_url}api/shadow/analyze",
            json={
                'text': contract_text,
                'focal_points': focal_points,
                'language': 'en'
            }
        )
        if shadow_response.status_code != 200:
            logger.error(f"Shadow analysis failed: {shadow_response.status_code}")
            return jsonify({'status': 'error', 'error': 'Shadow analysis failed'}), shadow_response.status_code
        shadow_analysis = shadow_response.json()['analysis']

        # Perform summary analysis in English
        logger.debug("Starting summary analysis")
        summary_response = requests.post(
            f"{request.host_url}api/summary/analyze",
            json={
                'text': contract_text,
                'focal_points': focal_points,
                'language': 'en'
            }
        )
        if summary_response.status_code != 200:
            logger.error(f"Summary analysis failed: {summary_response.status_code}")
            return jsonify({'status': 'error', 'error': 'Summary analysis failed'}), summary_response.status_code
        summary = summary_response.json()['summary']

        # Perform evaluation in English
        logger.debug("Starting evaluation")
        eval_response = requests.post(
            f"{request.host_url}api/evaluator/evaluate",
            json={
                'text': contract_text,
                'shadow_analysis': shadow_analysis,
                'summary': summary,
                'focal_points': focal_points
            }
        )
        if eval_response.status_code != 200:
            logger.error(f"Evaluation failed: {eval_response.status_code}")
            return jsonify({'status': 'error', 'error': 'Evaluation failed'}), eval_response.status_code
        evaluation = eval_response.json().get('evaluation', {})

        # Store English results in session
        analysis_results = {
            'status': 'success',
            'document_text': contract_text,
            'shadow_analysis': shadow_analysis,
            'summary': summary,
            'evaluation': evaluation,
            'original_language': 'en'
        }
        session['english_analysis_results'] = analysis_results
        session['contract_text'] = contract_text
        session['chat_language'] = user_language
        session.modified = True
        logger.debug(f"Stored English analysis results in session")

        # Translate if not English
        if user_language != 'en':
            logger.debug(f"Translating results to {user_language}")
            translation_response = requests.post(
                f"{request.host_url}api/translator/translate",
                json={
                    'content': analysis_results,
                    'language': user_language
                }
            )
            if translation_response.status_code == 200 and translation_response.json().get('status') == 'success':
                analysis_results = translation_response.json()['translated_content']
                analysis_results['translated_to'] = user_language
                logger.debug(f"Translated results to {user_language}")
            else:
                error_msg = translation_response.json().get('error', 'Unknown error')
                logger.error(f"Translation failed: {error_msg}")
                return jsonify({
                    'status': 'error',
                    'error': f"Translation to {user_language} failed: {error_msg}",
                    'analysis_results': analysis_results,
                    'translated_to': 'en'
                }), 400

        return jsonify(analysis_results), 200

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/retranslate', methods=['POST'])
def retranslate_analysis():
    """Retranslate cached English analysis results to the selected language"""
    try:
        data = request.get_json()
        if not data or 'language' not in data:
            logger.error("No language provided in retranslate request")
            return jsonify({'status': 'error', 'error': 'No language provided'}), 400

        user_language = data['language']
        logger.debug(f"Retranslating to language: {user_language}")

        if 'english_analysis_results' not in session:
            logger.error("No cached analysis results in session")
            return jsonify({
                'status': 'error',
                'error': 'No analysis results available. Please analyze a contract first.'
            }), 400

        analysis_results = session['english_analysis_results']
        logger.debug(f"Retrieved English analysis results")

        if user_language == 'en':
            analysis_results['translated_to'] = 'en'
            session['chat_language'] = user_language
            session.modified = True
            return jsonify(analysis_results), 200

        translation_response = requests.post(
            f"{request.host_url}api/translator/translate",
            json={
                'content': analysis_results,
                'language': user_language
            }
        )
        if translation_response.status_code == 200 and translation_response.json().get('status') == 'success':
            analysis_results = translation_response.json()['translated_content']
            analysis_results['translated_to'] = user_language
            session['chat_language'] = user_language
            session.modified = True
            logger.debug(f"Translated results to {user_language}")
            return jsonify(analysis_results), 200
        else:
            error_msg = translation_response.json().get('error', 'Translation failed')
            logger.error(f"Translation request failed: {error_msg}")
            return jsonify({
                'status': 'error',
                'error': f"Translation to {user_language} failed: {error_msg}",
                'translated_to': 'en',
                'analysis_results': analysis_results
            }), 400

    except Exception as e:
        logger.error(f"Retranslation error: {str(e)}")
        return jsonify({'status': 'error', 'error': f"Retranslation failed: {str(e)}"}), 500

@app.route('/api/chat/update_language', methods=['POST'])
def update_chat_language():
    """Update the chat session language"""
    try:
        data = request.get_json()
        if not data or 'language' not in data:
            logger.error("No language provided in chat language update")
            return jsonify({'status': 'error', 'error': 'No language provided'}), 400

        language = data['language']
        session['chat_language'] = language
        session.modified = True
        logger.debug(f"Updated chat language to {language}")
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.error(f"Chat language update error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)