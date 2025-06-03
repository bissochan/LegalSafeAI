# api/routes/summary_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from agents.summary_agent import SummaryAgent
import logging

summary_bp = Blueprint('summary', __name__)
summary_agent = SummaryAgent()
logger = logging.getLogger(__name__)

@summary_bp.route('/analyze', methods=['POST'])
@login_required
def summarize_contract():
    """Generate contract summary"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            logger.error("No text provided")
            return jsonify({'status': 'error', 'error': 'No text provided'}), 400
            
        language = data.get('language', 'en')
        summary = summary_agent.analyze(
            contract_text=data['text'],
            user_id=current_user.id,
            language=language
        )
        
        return jsonify({
            'status': 'success',
            'summary': summary
        })

    except Exception as e:
        logger.error(f"Error during summary generation: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
