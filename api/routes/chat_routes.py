# api/routes/chat_routes.py
from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
import logging
import uuid
from datetime import datetime
import requests
from requests.exceptions import RequestException
from models import db, ChatHistory, ChatSession
from agents.question_analyzer_agent import QuestionAnalyzerAgent
import os
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    logger.error("OPENROUTER_API_KEY not found in environment")
    raise ValueError("OPENROUTER_API_KEY not found in .env file")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Initialize QuestionAnalyzerAgent
question_analyzer = QuestionAnalyzerAgent()

@chat_bp.route('/start', methods=['POST'])
@login_required
def start_chat():
    """Start a new chat session with contract text."""
    logger.info(f"Starting new chat session for user: {current_user.username}")
    try:
        data = request.get_json(silent=True)
        if not data or 'contract_text' not in data:
            logger.error("No contract text provided")
            return jsonify({'status': 'error', 'error': 'No contract text provided'}), 400

        language = data.get('language', 'en')
        session_id = str(uuid.uuid4())

        # Store session in database
        chat_session = ChatSession(
            id=session_id,
            user_id=current_user.id,
            contract_text=data['contract_text'],
            language=language
        )
        db.session.add(chat_session)
        db.session.commit()

        # Update Flask session for language
        session['chat_language'] = language
        session.modified = True

        logger.info(f"Created chat session: {session_id} for user_id: {current_user.id}")
        return jsonify({'status': 'success', 'session_id': session_id})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error starting chat session: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to start chat session: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@chat_bp.route('/message', methods=['POST'])
@login_required
def send_message():
    """Process a user message and return AI response."""
    logger.info(f"Processing message for user: {current_user.username}")
    try:
        data = request.get_json(silent=True)
        if not data or 'message' not in data or 'session_id' not in data:
            logger.error("Missing session_id or message")
            return jsonify({'status': 'error', 'error': 'Missing session_id or message'}), 400

        session_id = data['session_id']
        chat_session = ChatSession.query.get(session_id)
        if not chat_session or chat_session.user_id != current_user.id:
            logger.error(f"No active chat session for session_id: {session_id}")
            return jsonify({'status': 'error', 'error': 'No active chat session or unauthorized access'}), 400

        question = data['message']
        contract_text = chat_session.contract_text
        language = chat_session.language

        # Save question to database
        chat_history = ChatHistory(
            user_id=current_user.id,
            session_id=session_id,
            question=question
        )
        db.session.add(chat_history)
        db.session.commit()

        # Update preferences
        question_analyzer.analyze(user_id=current_user.id, question=question)

        # Include analysis results if available
        analysis_context = ''
        if 'english_analysis_results' in session:
            analysis = session['english_analysis_results']
            analysis_context = (
                f"\n\nPrevious Analysis Results:\n"
                f"Summary: {analysis.get('summary', '')}\n"
                f"Shadow Analysis: {analysis.get('shadow_analysis', '')}\n"
                f"Evaluation: {str(analysis.get('evaluation', ''))}"
            )

        # Prepare prompt
        prompt = (
            "You are an expert in analyzing employment contracts under Italian law. "
            "Based on the following contract text and any provided analysis results, answer the user's question clearly and concisely in the requested language. "
            "Provide specific references to the contract where applicable, and ensure the response complies with Italian legal standards.\n\n"
            f"Contract Text:\n{contract_text}\n"
            f"{analysis_context}\n\n"
            f"Question: {question}\n"
            f"Language: {language}"
        )

        try:
            response = requests.post(
                OPENROUTER_API_URL,
                headers={
                    'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'google/gemini-2.0-flash-001',
                    'messages': [
                        {'role': 'system', 'content': prompt},
                        {'role': 'user', 'content': question}
                    ],
                    'max_tokens': 1000,  # Increased for detailed responses
                    'temperature': 0.7  # Balanced creativity
                },
                timeout=15
            )
            response.raise_for_status()
            choices = response.json().get('choices', [])
            if not choices or not choices[0].get('message', {}).get('content'):
                logger.error("Invalid OpenRouter API response structure")
                return jsonify({'status': 'error', 'error': 'Invalid API response'}), 500
            chat_response = choices[0]['message']['content'].strip()
        except RequestException as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            return jsonify({'status': 'error', 'error': 'Unable to process question due to API error'}), 500

        # Save response
        chat_history.response = chat_response
        db.session.commit()

        logger.info(f"Processed message for session: {session_id}")
        return jsonify({'status': 'success', 'response': chat_response})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error processing message: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to process chat message: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@chat_bp.route('/update_language', methods=['POST'])
@login_required
def update_language():
    """Update the chat session language."""
    logger.info(f"Updating chat language for user: {current_user.username}")
    try:
        data = request.get_json(silent=True)
        if not data or 'language' not in data:
            logger.error("No language provided")
            return jsonify({'status': 'error', 'error': 'No language provided'}), 400

        language = data['language']
        session['chat_language'] = language
        session.modified = True

        # Update active chat sessions
        session_id = data.get('session_id')
        if session_id:
            chat_session = ChatSession.query.get(session_id)
            if chat_session and chat_session.user_id == current_user.id:
                chat_session.language = language
                db.session.commit()
                logger.debug(f"Updated language for session: {session_id} to {language}")

        logger.info(f"Updated chat language to: {language}")
        return jsonify({'status': 'success'})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating language: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update chat language: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@chat_bp.route('/frequent_questions', methods=['GET'])
@login_required
def get_frequent_questions():
    """Get frequently asked questions for the current user."""
    logger.info(f"Fetching frequent questions for user: {current_user.username}")
    try:
        questions = question_analyzer.get_frequent_questions(user_id=current_user.id)
        return jsonify({'status': 'success', 'questions': questions})
    except Exception as e:
        logger.error(f"Error fetching frequent questions: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@chat_bp.route('/end', methods=['POST'])
@login_required
def end_chat():
    """End a chat session."""
    logger.info(f"Ending chat session for user: {current_user.username}")
    try:
        data = request.get_json(silent=True)
        if not data or 'session_id' not in data:
            logger.error("Missing session_id")
            return jsonify({'status': 'error', 'error': 'Missing or invalid session_id'}), 400

        session_id = data['session_id']
        chat_session = ChatSession.query.get(session_id)
        if not chat_session or chat_session.user_id != current_user.id:
            logger.error(f"No active chat session for session_id: {session_id}")
            return jsonify({'status': 'error', 'error': 'No active chat session or unauthorized access'}), 400

        db.session.delete(chat_session)
        db.session.commit()
        logger.info(f"Ended chat session: {session_id}")
        return jsonify({'status': 'success'})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error ending chat session: {str(e)}")
        return jsonify({'status': 'error', 'error': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to end chat session: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500