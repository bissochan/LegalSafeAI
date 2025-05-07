from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import secrets
from Agent.shadowAgent import ShadowAgent
from Agent.summaryAgent import ContractAnalyzerAgent
from Agent.ResponseEvaluatorAgent import ResponseEvaluator
from Agent.pdfExtractor import PdfTextExtractor
from Agent.legalChatAgent import LegalChatAgent
from jsonHandler import add_agent_response_and_scores
from dotenv import load_dotenv
import json
import os
import time
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Session configuration
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32)),
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR='flask_session',
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Initialize Flask-Session
Session(app)

# Ensure session directory exists
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])

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
chat_agent = LegalChatAgent()

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    return jsonify({'error': 'File is too large (max 16MB)'}), 413

@app.errorhandler(500)
def handle_server_error(e):
    return jsonify({'error': 'Internal server error occurred'}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_contract():
    try:
        # Generate unique session ID
        session.clear()
        session['id'] = secrets.token_hex(16)
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        # Save and process file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Step 1: Extract text
            logger.info("Extracting text from PDF...")
            contract_text = pdf_extractor.extract_text_from_pdf(filepath, lang='eng')
            
            # Store session data
            session['contract_text'] = contract_text
            session['creation_time'] = time.time()

            # Step 2: Shadow analysis
            logger.info("Performing shadow analysis...")
            shadow_analysis = shadow_agent.analyze(contract_text)
            session['shadow_analysis'] = str(shadow_analysis)
            
            # Step 3: Contract analysis
            logger.info("Analyzing contract structure...")
            summary_analysis = summary_agent.analyze(contract_text)
            session['summary_analysis'] = summary_analysis.model_dump()

            # Step 4: Evaluation
            logger.info("Evaluating analyses...")
            shadow_eval = eval_agent.evaluate(contract_text, str(shadow_analysis), "shadow")
            summary_eval = eval_agent.evaluate(contract_text, str(summary_analysis), "summary")
            
            # Step 5: Generate final report
            logger.info("Generating final report...")
            
            # Extract scores and prepare response
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

            # Generate and modify JSON
            json_path = summary_agent.save_analysis(summary_analysis, "Contract Analysis")
            with open(json_path, 'r', encoding='utf-8') as f:
                initial_json = f.read()
            
            final_json = add_agent_response_and_scores(
                initial_json,
                str(shadow_analysis),
                shadow_scores,
                summary_scores
            )

            return jsonify({
                'status': 'success',
                'data': json.loads(final_json),
                'session_id': session['id']
            })

        except Exception as e:
            session.clear()
            logger.error(f"Analysis error: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'Error analyzing contract',
                'details': str(e)
            }), 500

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    except Exception as e:
        session.clear()
        logger.error(f"Request error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error processing request',
            'details': str(e)
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Validate session
        if 'id' not in session:
            return jsonify({'error': 'No active session'}), 401
            
        # Check session age
        creation_time = session.get('creation_time', 0)
        if time.time() - creation_time > app.config['PERMANENT_SESSION_LIFETIME']:
            session.clear()
            return jsonify({'error': 'Session expired'}), 401

        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Initialize chat agent with stored context
        chat_agent.initialize_context(
            session.get('contract_text'),
            session.get('shadow_analysis'),
            session.get('summary_analysis')
        )

        # Get response
        response = chat_agent.chat(user_message)
        
        return jsonify({
            'status': 'success',
            'response': response,
            'session_id': session['id']
        })

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Error processing chat message',
            'details': str(e)
        }), 500

def cleanup_old_sessions():
    """Clean up expired session files"""
    try:
        session_dir = app.config['SESSION_FILE_DIR']
        expiry = time.time() - app.config['PERMANENT_SESSION_LIFETIME']
        
        for file in os.listdir(session_dir):
            if not file.endswith('.session'):
                continue
                
            file_path = os.path.join(session_dir, file)
            if os.path.getmtime(file_path) < expiry:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed expired session file: {file}")
                except OSError as e:
                    logger.error(f"Error removing session file {file}: {e}")
    except Exception as e:
        logger.error(f"Session cleanup error: {e}")

if __name__ == '__main__':
    # Schedule session cleanup
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_old_sessions, 'interval', hours=1)
    scheduler.start()
    
    try:
        app.run(debug=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()