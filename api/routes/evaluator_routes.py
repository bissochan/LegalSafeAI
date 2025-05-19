from flask import Blueprint, request, jsonify
from agents.evaluator_agent import EvaluatorAgent
import logging

evaluator_bp = Blueprint('evaluator', __name__)
evaluator_agent = EvaluatorAgent()
logger = logging.getLogger(__name__)

@evaluator_bp.route('/evaluate', methods=['POST'])
def evaluate_analysis():
    """Evaluate contract analysis results"""
    try:
        data = request.get_json()
        required_fields = ['text', 'shadow_analysis', 'summary']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'error': 'Missing required fields'
            }), 400

        language = data.get('language', 'en')
        evaluation = evaluator_agent.evaluate(
            analysis_data=data,
            language=language
        )

        return jsonify({
            'status': 'success',
            'evaluation': evaluation
        })

    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500