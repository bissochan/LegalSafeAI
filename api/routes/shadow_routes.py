# api/routes/shadow_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from agents.shadow_agent import ShadowAgent
import logging

shadow_bp = Blueprint('shadow', __name__)
shadow_agent = ShadowAgent()
logger = logging.getLogger(__name__)

@shadow_bp.route('/analyze', methods=['POST'])
@login_required
def analyze_contract():
    """Perform shadow analysis on contract text"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            logger.error("No contract text provided")
            return jsonify({'status': 'error', 'error': 'No text provided'}), 400

        analysis_result = shadow_agent.analyze(
            contract_text=data['text'],
            user_id=current_user.id,
            language=data.get('language', 'en')
        )

        return jsonify({
            'status': 'success',
            'shadow_analysis': analysis_result
        })

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500