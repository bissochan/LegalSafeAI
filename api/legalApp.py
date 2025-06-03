# api/legalApp.py
import os
import logging
from flask import Flask, redirect, request, jsonify, session, render_template, url_for
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import secrets
import requests
from routes.document_routes import document_bp
from routes.shadow_routes import shadow_bp
from routes.summary_routes import summary_bp
from routes.evaluator_routes import evaluator_bp
from routes.chat_routes import chat_bp
from routes.translator_routes import translator_bp
from routes.student_routes import student_bp
from routes.web_search_routes import web_search_bp
from routes.auth_routes import auth_bp
from models import db, User, Preference

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__,
    template_folder="../templates",
    static_folder="../static",
)

# Ensure instance folder exists
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Configure app
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32)),
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR='flask_session',
    PERMANENT_SESSION_LIFETIME=3600,
    SESSION_COOKIE_SECURE=False,  # Set to True if using HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAME_SITE='Lax',
    SESSION_COOKIE_NAME='legal_safe_ai_session',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    SQLALCHEMY_DATABASE_URI=f'sqlite:///{os.path.join(instance_path, "legal_safe_ai.db")}',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Ensure session directory exists
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])

# Initialize Flask-Session
Session(app)

# Initialize SQLAlchemy
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables and initialize preferences
with app.app_context():
    db.create_all()
    areas = [
        'sick_leave', 'vacation', 'overtime', 'termination', 'confidentiality',
        'non_compete', 'intellectual_property', 'governing_law', 'jurisdiction',
        'dispute_resolution', 'liability', 'salary', 'benefits', 'work_hours',
        'performance_evaluation', 'duties', 'responsibilities'
    ]
    for user in User.query.all():
        existing_areas = {p.area for p in Preference.query.filter_by(user_id=user.id).all()}
        for area in areas:
            if area not in existing_areas:
                db.session.add(Preference(user_id=user.id, area=area, weight=1.0))
    db.session.commit()

# Register blueprints
app.register_blueprint(document_bp, url_prefix='/api/document')
app.register_blueprint(shadow_bp, url_prefix='/api/shadow')
app.register_blueprint(summary_bp, url_prefix='/api/summary')
app.register_blueprint(evaluator_bp, url_prefix='/api/evaluator')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(translator_bp, url_prefix='/api/translator')
app.register_blueprint(student_bp, url_prefix='/api/student')
app.register_blueprint(web_search_bp, url_prefix='/api/web_search')
app.register_blueprint(auth_bp, url_prefix='/auth')

@app.route('/')
def index():
    """Serve the main application page"""
    logger.debug("Rendering index.html")
    try:
        if current_user.is_authenticated:
            return render_template('index.html')
        return redirect(url_for('auth.login'))
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}")
        raise

@app.route('/analyze', methods=['POST'])
@login_required
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
        logger.debug(f"Analyzing contract with language: {user_language} for user: {current_user.username}")

        # Prepare session cookies
        session_cookies = {app.config['SESSION_COOKIE_NAME']: request.cookies.get(app.config['SESSION_COOKIE_NAME'])}

        # Perform shadow analysis in English
        logger.debug("Starting shadow analysis")
        shadow_response = requests.post(
            f"{request.host_url}api/shadow/analyze",
            json={
                'text': contract_text,
                'focal_points': focal_points,
                'language': 'en'
            },
            cookies=session_cookies
        )
        if shadow_response.status_code == 401 or shadow_response.status_code == 403:
            logger.error("Shadow analysis unauthorized")
            return jsonify({'status': 'error', 'error': 'Unauthorized access to shadow analysis'}), 401
        if shadow_response.status_code != 200:
            logger.error(f"Shadow analysis failed: {shadow_response.status_code} - {shadow_response.text}")
            return jsonify({'status': 'error', 'error': 'Shadow analysis failed'}), shadow_response.status_code
        shadow_result = shadow_response.json()
        if shadow_result.get('status') != 'success':
            logger.error(f"Shadow analysis error: {shadow_result.get('error')}")
            return jsonify({'status': 'error', 'error': shadow_result.get('error')}), 500
        shadow_analysis = shadow_result.get('shadow_analysis')
        if not shadow_analysis:
            logger.error("Shadow analysis missing in response")
            return jsonify({'status': 'error', 'error': 'Shadow analysis missing'}), 500

        # Perform summary analysis in English
        logger.debug("Starting summary analysis")
        summary_response = requests.post(
            f"{request.host_url}api/summary/analyze",
            json={
                'text': contract_text,
                'focal_points': focal_points,
                'language': 'en'
            },
            cookies=session_cookies
        )
        if summary_response.status_code == 401 or summary_response.status_code == 403:
            logger.error("Summary analysis unauthorized")
            return jsonify({'status': 'error', 'error': 'Unauthorized access to summary analysis'}), 401
        if summary_response.status_code != 200:
            logger.error(f"Summary analysis failed: {summary_response.status_code} - {summary_response.text}")
            return jsonify({'status': 'error', 'error': 'Summary analysis failed'}), summary_response.status_code
        summary_result = summary_response.json()
        if summary_result.get('status') != 'success':
            logger.error(f"Summary analysis error: {summary_result.get('error')}")
            return jsonify({'status': 'error', 'error': summary_result.get('error')}), 500
        summary = summary_result.get('summary')
        if not summary:
            logger.error("Summary missing in response")
            return jsonify({'status': 'error', 'error': 'Summary missing'}), 500

        # Perform evaluation in English
        logger.debug("Starting evaluation")
        eval_response = requests.post(
            f"{request.host_url}api/evaluator/evaluate",
            json={
                'text': contract_text,
                'shadow_analysis': shadow_analysis,
                'summary': summary,
                'focal_points': focal_points
            },
            cookies=session_cookies
        )
        if eval_response.status_code == 401 or eval_response.status_code == 403:
            logger.error("Evaluation unauthorized")
            return jsonify({'status': 'error', 'error': 'Unauthorized access to evaluation'}), 401
        if eval_response.status_code != 200:
            logger.error(f"Evaluation failed: {eval_response.status_code} - {eval_response.text}")
            return jsonify({'status': 'error', 'error': 'Evaluation failed'}), eval_response.status_code
        eval_result = eval_response.json()
        if eval_result.get('status') != 'success':
            logger.error(f"Evaluation error: {eval_result.get('error')}")
            return jsonify({'status': 'error', 'error': eval_result.get('error')}), 500
        evaluation = eval_result.get('evaluation', {})
        if not evaluation:
            logger.error("Evaluation missing in response")
            return jsonify({'status': 'error', 'error': 'Evaluation missing'}), 500

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
        session['analysis_complete'] = True
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
                },
                cookies=session_cookies
            )
            if translation_response.status_code == 401 or translation_response.status_code == 403:
                logger.error("Translation unauthorized")
                return jsonify({'status': 'error', 'error': 'Unauthorized access to translation'}), 401
            if translation_response.status_code == 200:
                translation_data = translation_response.json()
                if translation_data.get('status') == 'success':
                    analysis_results = translation_data['translated_content']
                    analysis_results['translated_to'] = user_language
                    logger.debug(f"Translated results to {user_language}")
                else:
                    error_msg = translation_data.get('error', 'Unknown error')
                    logger.error(f"Translation failed: {error_msg}")
                    return jsonify({
                        'status': 'error',
                        'error': f"Translation to {user_language} failed: {error_msg}",
                        'analysis_results': analysis_results,
                        'translated_to': 'en'
                    }), 400
            else:
                logger.error(f"Translation failed: {translation_response.status_code} - {translation_response.text}")
                return jsonify({
                    'status': 'error',
                    'error': f"Translation failed: {translation_response.text}",
                    'analysis_results': analysis_results,
                    'translated_to': 'en'
                }), translation_response.status_code

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

if __name__ == '__main__':
    app.run(debug=True)