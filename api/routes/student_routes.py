from flask import Blueprint, request, jsonify
from agents.student_agent import StudentAgent
import logging
import asyncio

student_bp = Blueprint('student', __name__)
student_agent = StudentAgent()
logger = logging.getLogger(__name__)

@student_bp.route('/search', methods=['POST'])
async def student_search():
    """Search for university-specific student information"""
    try:
        data = request.get_json()
        if not data or 'university' not in data:
            return jsonify({
                'status': 'error',
                'error': 'University name is required'
            }), 400

        university = data['university']
        category = data.get('category', 'working_student')
        custom_keywords = data.get('keywords', None)
        target_language = data.get('language', 'en')

        logger.debug(f"Received student search request for {university}, category: {category}, language: {target_language}")
        results = await student_agent.search_university_info(
            university=university,
            category=category,
            custom_keywords=custom_keywords
        )

        if results['status'] != 'success':
            logger.error(f"Student search failed: {results.get('error')}")
            return jsonify(results), 500

        # Translate results if target_language is not English
        if target_language != 'en':
            translated_results = await translate_results(results, target_language)
            return jsonify(translated_results)
        
        logger.info(f"Student search for {university} successful")
        return jsonify(results)

    except Exception as e:
        logger.error(f"Student search error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

async def translate_results(results: dict, target_language: str) -> dict:
    """Translate search results to the target language"""
    try:
        from ..routes.translator_routes import translate_content
        translated_results = results.copy()
        translated_results['summary']['recommendation'] = await translate_content(
            results['summary']['recommendation'], target_language
        )
        for result in translated_results['results']:
            result['title'] = await translate_content(result['title'], target_language)
            result['content_summary'] = await translate_content(result['content_summary'], target_language)
            result['key_points'] = [await translate_content(point, target_language) for point in result['key_points']]
        return translated_results
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return results