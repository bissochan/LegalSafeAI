# api/routes/evaluator_routes.py
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
            return jsonify({'status': 'error', 'error': 'No text provided'}), 400

        contract_text = data['text']
        shadow_analysis = data.get('shadow_analysis', {})
        summary = data.get('summary', {})
        focal_points = data.get('focal_points', None)

        evaluation_results = evaluator_agent.evaluate(
            contract_text=contract_text,
            shadow_analysis=shadow_analysis,
            summary=summary,
            focal_points=focal_points
        )

        if 'error' in evaluation_results:
            return jsonify({
                'status': 'error',
                'error': evaluation_results['error']
            }), 500

        return jsonify({
            'status': 'success',
            'evaluation': evaluation_results['evaluation']
        })

    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500