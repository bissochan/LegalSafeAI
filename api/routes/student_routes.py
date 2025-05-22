from flask import Blueprint, request, jsonify
from agents.student_agent import StudentAgent
import logging
from typing import Dict, Any

student_bp = Blueprint('student', __name__)
student_agent = StudentAgent()
logger = logging.getLogger(__name__)

CATEGORY_MAPPING = {
    'working': 'working_student',
    'jobs': 'job_offers',
    'housing': 'housing',
    'research': 'research',
    'internship': 'internship',
    'scholarships': 'scholarships',  # Added from frontend
    'visas': 'visas',  # Added from frontend
    'custom': 'custom'
}

@student_bp.route('/search', methods=['POST'])
def student_search():
    """Search for university-specific student information and government regulations"""
    try:
        data = request.get_json()
        if not data or 'university' not in data:
            return jsonify({
                'status': 'error',
                'error': 'University name is required'
            }), 400

        university = data['university']
        category = data.get('category', 'working_student')
        category = CATEGORY_MAPPING.get(category, category)
        custom_keywords = data.get('keywords', None)
        target_language = data.get('language', 'en')

        logger.debug(f"Received student search request: university={university}, category={category}, keywords={custom_keywords}, language={target_language}")

        # Get university country (using Hipolabs API or similar)
        country = student_agent.get_university_country(university)
        results = student_agent.search_university_info(
            university=university,
            category=category,
            custom_keywords=custom_keywords,
            country=country
        )

        if results['status'] != 'success':
            logger.error(f"Student search failed: {results.get('error')} for university={university}, category={category}")
            return jsonify(results), 500

        if target_language != 'en':
            results = translate_results(results, target_language)

        logger.info(f"Student search for {university} successful")
        return jsonify(results)

    except Exception as e:
        logger.error(f"Student search error: {str(e)}, request={data}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

def translate_results(results: Dict, target_language: str) -> Dict:
    """Translate search results to the target language"""
    try:
        from ..routes.translator_routes import translate_content
        translated_results = results.copy()
        translated_results['summary']['recommendation'] = translate_content(
            results['summary']['recommendation'], target_language
        )
        for result in translated_results['results']:
            result['title'] = translate_content(result['title'], target_language)
            result['content_summary'] = translate_content(result['content_summary'], target_language)
            result['key_points'] = [translate_content(point, target_language) for point in result.get('key_points', [])]
        return translated_results
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return results