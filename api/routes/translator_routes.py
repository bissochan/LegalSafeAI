from flask import Blueprint, request, jsonify
from agents.translator_agent import TranslatorAgent
import logging

translator_bp = Blueprint('translator', __name__)
translator_agent = TranslatorAgent()
logger = logging.getLogger(__name__)

@translator_bp.route('/translate', methods=['POST'])
def translate_analysis():
    """Translate JSON content to target language"""
    try:
        data = request.get_json()
        if not data or 'content' not in data or 'language' not in data:
            logger.error("Missing fields in translation request")
            return jsonify({
                'status': 'error',
                'error': 'Missing content or language',
                'translated_content': data.get('content', {})
            }), 400

        target_language = data['language']
        logger.debug(f"Translating to {target_language}")
        result = translator_agent.translate(
            content=data['content'],
            target_language=target_language
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Translation route error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'translated_content': data.get('content', {})
        }), 500