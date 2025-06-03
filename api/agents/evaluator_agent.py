# api/agents/evaluator_agent.py
import logging
import re
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EvaluatorAgent:
    def __init__(self):
        pass  # No API key needed for aggregation

    def evaluate(
        self,
        contract_text: str,
        shadow_analysis: Dict[str, Any],
        summary: Dict[str, Any],
        focal_points: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Evaluate contract with analysis data and optional focal points."""
        try:
            evaluation_areas = {
                'liability': {'score': 0, 'issues': [], 'recommendations': []},
                'work_hours': {'score': 0, 'issues': [], 'recommendations': []},
                'compensation': {'score': 0, 'issues': [], 'recommendations': []},
                'termination': {'score': 0, 'issues': [], 'recommendations': []},
                'confidentiality': {'score': 0, 'issues': [], 'recommendations': []},
                'non_compete': {'score': 0, 'issues': [], 'recommendations': []},
                'benefits': {'score': 0, 'issues': [], 'recommendations': []},
                'intellectual_property': {'score': 0, 'issues': [], 'recommendations': []},
                'dispute_resolution': {'score': 0, 'issues': [], 'recommendations': []}
            }

            if focal_points:
                for point in focal_points:
                    if point not in evaluation_areas:
                        evaluation_areas[point] = {'score': 0, 'issues': [], 'recommendations': []}

            # Process shadow analysis
            if shadow_analysis.get('topics'):
                for topic_data in shadow_analysis['topics']:
                    topic = topic_data.get('topic', '').lower()
                    score = topic_data.get('score', 0) or 0
                    problems = topic_data.get('problems', '')
                    solutions = topic_data.get('solutions', '')

                    for area in evaluation_areas:
                        if area in topic or topic in area:
                            evaluation_areas[area]['score'] = max(evaluation_areas[area]['score'], score)
                            if problems:
                                evaluation_areas[area]['issues'].append(problems)
                            if solutions:
                                evaluation_areas[area]['recommendations'].append(solutions)

            # Process summary
            if summary.get('structured_analysis'):
                for key, value in summary['structured_analysis'].items():
                    if key != 'overall_score' and key in evaluation_areas:
                        score = value.get('score', 0) or 0
                        content = value.get('content', '')
                        evaluation_areas[key]['score'] = max(evaluation_areas[key]['score'], score)
                        if 'issue' in content.lower() or 'concern' in content.lower():
                            evaluation_areas[key]['issues'].append(content)
                        if 'recommend' in content.lower() or 'suggest' in content.lower():
                            evaluation_areas[key]['recommendations'].append(content)

            # Calculate overall scores
            total_score = sum(area['score'] for area in evaluation_areas.values() if area['score'] > 0)
            score_count = sum(1 for area in evaluation_areas.values() if area['score'] > 0)
            overall_score = total_score / score_count if score_count > 0 else 5.0

            clarity = sum(1 for area in evaluation_areas.values() if area['score'] >= 8) / len(evaluation_areas) * 10
            completeness = sum(1 for area in evaluation_areas.values() if area['score'] > 0) / len(evaluation_areas) * 10
            risk_level = sum(len(area['issues']) for area in evaluation_areas.values()) / len(evaluation_areas) * 10
            fairness = overall_score

            return {
                'evaluation': {
                    'overall_score': round(overall_score, 1),
                    'scores': {
                        'clarity': round(clarity, 1),
                        'completeness': round(completeness, 1),
                        'risk_level': round(risk_level, 1),
                        'fairness': round(fairness, 1)
                    },
                    'areas': {
                        key: {
                            'score': area['score'],
                            'issues': area['issues'],
                            'recommendations': area['recommendations']
                        } for key, area in evaluation_areas.items() if area['score'] > 0 or area['issues']
                    },
                    'recommendations': [
                        rec for area in evaluation_areas.values() for rec in area['recommendations']
                    ][:5]
                }
            }

        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            return {'error': str(e)}