from flask import Blueprint, request, jsonify
from agents.translator_agent import TranslatorAgent
import logging

translator_bp = Blueprint('translator', __name__)
translator_agent = TranslatorAgent()
logger = logging.getLogger(__name__)

@translator_bp.route('/translate', methods=['POST'])
def translate_analysis():
    """Translate analysis results to target language"""
    try:
        data = request.get_json()
        if not data or 'content' not in data or 'language' not in data:
            return jsonify({'status': 'error', 'error': 'Missing required fields'}), 400

        target_language = data['language']
        logger.debug(f"Received translation request for language: {target_language}")
        result = translator_agent.translate(
            content=data['content'],
            target_language=target_language
        )

        # Ensure consistent response format
        if result['status'] == 'success':
            logger.info(f"Translation to {target_language} successful")
            return jsonify({
                'status': 'success',
                'translated_content': result['translated_content']
            })
        else:
            logger.error(f"Translation failed: {result['error']}")
            return jsonify({
                'status': 'error',
                'error': result['error'],
                'translated_content': result['translated_content']
            }), 500

    except Exception as e:
        logger.error(f"Translation route error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'translated_content': data.get('content', {})
        }), 500