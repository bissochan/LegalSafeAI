from flask import Blueprint, request, jsonify
from agents.evaluator_agent import EvaluatorAgent
import logging

evaluator_bp = Blueprint('evaluator', __name__)
evaluator_agent = EvaluatorAgent()
logger = logging.getLogger(__name__)

@evaluator_bp.route('/evaluate', methods=['POST'])
def evaluate_contract():
    """Evaluate contract analysis results"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400

        # Extract required data
        contract_text = data['text']
        shadow_analysis = data.get('shadow_analysis', {})
        summary = data.get('summary', {})
        focal_points = data.get('focal_points', None)

        # Call evaluator with correct parameters
        evaluation_results = evaluator_agent.evaluate(
            contract_text=contract_text,
            shadow_analysis=shadow_analysis,
            summary=summary,
            focal_points=focal_points
        )

        return jsonify({
            'status': 'success',
            'evaluation': evaluation_results
        })

    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500