from flask import Blueprint, request, jsonify
from agents.summary_agent import SummaryAgent
import logging

summary_bp = Blueprint('summary', __name__)
summary_agent = SummaryAgent()
logger = logging.getLogger(__name__)

@summary_bp.route('/analyze', methods=['POST'])
def summarize_contract():
    """Generate contract summary"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
            
        language = data.get('language', 'en')
        summary = summary_agent.analyze(data['text'], language=language)
        
        return jsonify({
            'status': 'success',
            'summary': summary.dict()  # Convert Pydantic model to dictionary
        })

    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500