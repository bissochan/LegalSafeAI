from flask import Blueprint, request, jsonify
from agents.web_search_agent import WebSearchAgent
import logging

web_search_bp = Blueprint('web_search', __name__)
web_search_agent = WebSearchAgent()
logger = logging.getLogger(__name__)

@web_search_bp.route('/focused-search', methods=['POST'])
def focused_search():
    """Perform a focused web search with keyword filtering"""
    try:
        data = request.get_json()
        if not data or 'query' not in data or 'keywords' not in data:
            return jsonify({
                'status': 'error',
                'error': 'Missing required fields: query and keywords'
            }), 400
            
        results = web_search_agent.focused_search(
            query=data['query'],
            keywords=data['keywords'],
            min_matches=data.get('min_matches', 2),
            max_results=data.get('max_results', 10)
        )
        
        return jsonify(results)

    except Exception as e:
        logger.error(f"Focused search error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500