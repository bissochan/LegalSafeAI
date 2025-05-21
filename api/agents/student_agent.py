from typing import Dict, List, Any
import logging
from .web_search_agent import WebSearchAgent

logger = logging.getLogger(__name__)

class StudentAgent:
    """Agent for handling student-related searches and analysis"""
    
    SEARCH_CATEGORIES = {
        'working_student': {
            'keywords': ['working student', 'student job', 'part-time study', 'work-study', 'student employment'],
            'min_matches': 2
        },
        'housing': {
            'keywords': ['student housing', 'accommodation', 'rental agreement', 'student apartment', 'dormitory'],
            'min_matches': 2
        },
        'research': {
            'keywords': ['research position', 'research grant', 'PhD', 'fellowship', 'scholarship'],
            'min_matches': 2
        },
        'internship': {
            'keywords': ['internship', 'apprenticeship', 'traineeship', 'placement', 'work experience'],
            'min_matches': 2
        },
        'job_offers': {
            'keywords': ['graduate job', 'entry level', 'student position', 'career', 'recruitment'],
            'min_matches': 2
        }
    }

    def __init__(self):
        self.web_search = WebSearchAgent()

    async def search_university_info(
        self, 
        university: str,
        category: str = 'working_student',
        custom_keywords: List[str] = None
    ) -> Dict[str, Any]:
        """
        Search and analyze university-specific information
        
        Args:
            university: Name of the university
            category: Search category (working_student, housing, research, etc.)
            custom_keywords: Optional additional keywords
        """
        try:
            # Validate category
            if category not in self.SEARCH_CATEGORIES and category != 'custom':
                return {
                    'status': 'error',
                    'error': f'Invalid category. Must be one of: {", ".join(self.SEARCH_CATEGORIES.keys())} or custom'
                }

            # Build search query and keywords
            if category == 'custom' and not custom_keywords:
                return {
                    'status': 'error',
                    'error': 'Custom search requires keywords'
                }

            # Prepare search parameters
            if category == 'custom':
                keywords = custom_keywords
                min_matches = 1
            else:
                category_config = self.SEARCH_CATEGORIES[category]
                keywords = category_config['keywords']
                min_matches = category_config['min_matches']

            # Build university-specific query
            query = f"site:{self._get_university_domain(university)} {category.replace('_', ' ')}"
            
            # Perform focused search
            search_results = self.web_search.focused_search(
                query=query,
                keywords=keywords,
                min_matches=min_matches,
                max_results=5
            )

            if search_results['status'] != 'success':
                return search_results

            # Analyze and structure results
            analyzed_results = self._analyze_results(search_results['results'], category)

            return {
                'status': 'success',
                'university': university,
                'category': category,
                'summary': self._generate_summary(analyzed_results),
                'results': analyzed_results
            }

        except Exception as e:
            logger.error(f"Student agent error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _get_university_domain(self, university: str) -> str:
        """Extract or construct university domain"""
        # Remove common words and spaces
        domain = university.lower()
        for word in ['university', 'of', 'the']:
            domain = domain.replace(word, '')
        domain = domain.strip().replace(' ', '')
        
        return f"{domain}.edu"

    def _analyze_results(self, results: List[Dict], category: str) -> List[Dict]:
        """Analyze and structure search results"""
        analyzed = []
        
        for result in results:
            analyzed.append({
                'title': result['title'],
                'url': result['url'],
                'content_summary': self._summarize_content(result['content']),
                'relevance': result['relevance_score'],
                'key_points': self._extract_key_points(result['content'], category),
                'matched_keywords': result['matched_keywords']
            })
            
        return analyzed

    def _summarize_content(self, content: str, max_length: int = 200) -> str:
        """Create a brief summary of the content"""
        # For now, return truncated content
        # TODO: Implement proper summarization using LLM
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def _extract_key_points(self, content: str, category: str) -> List[str]:
        """Extract key points based on category"""
        # TODO: Implement proper key points extraction using LLM
        # For now, return basic extraction
        key_points = []
        sentences = content.split('.')
        
        for sentence in sentences:
            if any(kw.lower() in sentence.lower() for kw in self.SEARCH_CATEGORIES[category]['keywords']):
                key_points.append(sentence.strip())
                
        return key_points[:3]  # Return top 3 key points

    def _generate_summary(self, analyzed_results: List[Dict]) -> Dict[str, Any]:
        """Generate overall summary of findings"""
        return {
            'total_results': len(analyzed_results),
            'avg_relevance': sum(r['relevance'] for r in analyzed_results) / len(analyzed_results),
            'top_keywords': self._get_top_keywords(analyzed_results),
            'recommendation': self._generate_recommendation(analyzed_results)
        }

    def _get_top_keywords(self, results: List[Dict], limit: int = 5) -> List[str]:
        """Get most frequently matched keywords"""
        keyword_count = {}
        for result in results:
            for kw in result['matched_keywords']:
                keyword_count[kw] = keyword_count.get(kw, 0) + 1
        
        return sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)[:limit]

    def _generate_recommendation(self, results: List[Dict]) -> str:
        """Generate a recommendation based on analysis"""
        if not results:
            return "No relevant information found"
        
        top_result = max(results, key=lambda x: x['relevance'])
        return f"Recommended resource: {top_result['title']} ({top_result['url']})"