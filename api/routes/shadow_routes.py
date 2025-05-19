from flask import Blueprint, request, jsonify
from agents.shadow_agent import ShadowAgent
import logging

shadow_bp = Blueprint('shadow', __name__)
shadow_agent = ShadowAgent()
logger = logging.getLogger(__name__)

@shadow_bp.route('/analyze', methods=['POST'])
def analyze_contract():
    """Perform shadow analysis on contract text"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
            
        language = data.get('language', 'en')
        analysis = shadow_agent.analyze(data['text'], language=language)
        
        return jsonify({
            'status': 'success',
            'analysis': analysis
        })

    except Exception as e:
        logger.error(f"Shadow analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500