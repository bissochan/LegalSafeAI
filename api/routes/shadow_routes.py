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

        # Get optional focal points
        focal_points = data.get('focal_points', None)
        contract_text = data['text']
        
        # Validate focal points if provided
        if focal_points and (not isinstance(focal_points, list) or len(focal_points) > 5):
            return jsonify({
                'error': 'Focal points must be a list of 5 or fewer items'
            }), 400

        analysis_results = shadow_agent.analyze(
            contract_text=contract_text,  # Changed from text to contract_text
            focal_points=focal_points
        )

        return jsonify({
            'status': 'success',
            'analysis': analysis_results
        })

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500