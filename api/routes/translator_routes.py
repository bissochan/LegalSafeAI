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
            return jsonify({'error': 'Missing required fields'}), 400

        translated_content = translator_agent.translate(
            content=data['content'],
            target_language=data['language']
        )

        return jsonify({
            'status': 'success',
            'translated_content': translated_content
        })

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500