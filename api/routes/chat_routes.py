# api/routes/chat_routes.py
from flask import Blueprint, request, jsonify
import logging
import uuid
from datetime import datetime
import requests
from requests.exceptions import RequestException
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

# In-memory session storage (replace with database/Redis in production)
chat_sessions = {}

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

@chat_bp.route('/start', methods=['POST'])
def start_chat():
    logger.info("Starting new chat session")
    try:
        data = request.get_json(silent=True)
        if not data or 'contract_text' not in data:
            logger.error("No contract text provided")
            return jsonify({'status': 'error', 'error': 'No contract text provided'}), 400

        language = data.get('language', 'en')
        session_id = str(uuid.uuid4())
        chat_sessions[session_id] = {
            'contract_text': data['contract_text'],
            'language': language,
            'created_at': datetime.now(),
            'messages': []
        }
        logger.info(f"Created chat session: {session_id}")
        return jsonify({'status': 'success', 'session_id': session_id})
    except Exception as e:
        logger.error(f"Failed to start chat session: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@chat_bp.route('/message', methods=['POST'])
def send_message():
    logger.info("Processing chat message")
    try:
        data = request.get_json(silent=True)
        if not data or 'message' not in data or 'session_id' not in data:
            logger.error("Missing session_id or message")
            return jsonify({'status': 'error', 'error': 'Missing session_id or message'}), 400

        session_id = data['session_id']
        if not session_id or session_id not in chat_sessions:
            logger.error(f"No active chat session for session_id: {session_id}")
            return jsonify({'status': 'error', 'error': 'No active chat session'}), 400

        question = data['message']
        contract_text = chat_sessions[session_id]['contract_text']
        language = chat_sessions[session_id].get('language', 'en')

        prompt = (
            "You are an expert in analyzing employment contracts under Italian law. "
            "Based on the following contract text, answer the user's question clearly and concisely. "
            "Provide specific references to the contract where applicable.\n\n"
            f"Contract Text:\n{contract_text}\n\n"
            f"Question: {question}"
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
                    'max_tokens': 500
                },
                timeout=15
            )
            response.raise_for_status()
            chat_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No response generated')
        except RequestException as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            return jsonify({'status': 'error', 'error': 'Unable to process question due to API error'}), 500

        chat_sessions[session_id]['messages'].append({
            'question': question,
            'response': chat_response,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"Processed message for session: {session_id}")
        return jsonify({'status': 'success', 'response': chat_response})
    except Exception as e:
        logger.error(f"Failed to process chat message: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@chat_bp.route('/end', methods=['POST'])
def end_chat():
    logger.info("Ending chat session")
    try:
        data = request.get_json(silent=True)
        if not data or 'session_id' not in data:
            logger.error("Missing or invalid session_id")
            return jsonify({'status': 'error', 'error': 'Missing or invalid session_id'}), 400

        session_id = data['session_id']
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            logger.info(f"Ended chat session: {session_id}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Failed to end chat session: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500