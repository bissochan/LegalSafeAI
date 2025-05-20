from flask import Blueprint, request, jsonify, session
from agents.chat_agent import ChatAgent
import logging

chat_bp = Blueprint('chat', __name__)
chat_agent = ChatAgent()
logger = logging.getLogger(__name__)

@chat_bp.route('/start', methods=['POST'])
def start_chat():
    """Initialize chat session with contract context"""
    try:
        data = request.get_json()
        if not data or 'contract_text' not in data:
            return jsonify({'error': 'No contract text provided'}), 400
            
        session_id = chat_agent.initialize_session(
            contract_text=data['contract_text'],
            language=data.get('language', 'en')
        )
        
        session['chat_session_id'] = session_id
        return jsonify({
            'status': 'success',
            'session_id': session_id
        })

    except Exception as e:
        logger.error(f"Chat initialization error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Send message to chat agent"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
            
        session_id = session.get('chat_session_id')
        if not session_id:
            return jsonify({'error': 'No active chat session'}), 400
            
        response = chat_agent.process_message(
            session_id=session_id,
            message=data['message'],
            language=data.get('language', 'en')
        )
        
        return jsonify({
            'status': 'success',
            'response': response
        })

    except Exception as e:
        logger.error(f"Message processing error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@chat_bp.route('/end', methods=['POST'])
def end_chat():
    """End chat session"""
    try:
        session_id = session.get('chat_session_id')
        if session_id:
            chat_agent.end_session(session_id)
            session.pop('chat_session_id', None)
            
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.error(f"Chat end error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500