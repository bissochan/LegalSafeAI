import logging
from typing import Dict, List, Any
from agents.web_search_agent import WebSearchAgent
from urllib.parse import urlparse
import requests
from fuzzywuzzy import fuzz, process

logger = logging.getLogger(__name__)

class StudentAgent:
    """Agent for searching university-specific student information and government regulations"""
    
    def __init__(self):
        self.web_search_agent = WebSearchAgent()
        self.university_domains = {
            "università degli studi di trento": "unitn.it",
            "universita degli stui di trento": "unitn.it",
            "university of oxford": "ox.ac.uk",
            "harvard university": "harvard.edu",
            # Add more as needed
        }
        self.government_domains = {
            "italy": ["miur.gov.it", "istruzione.it"],
            "united kingdom": ["gov.uk"],
            "united states": ["ed.gov"],
            # Add more country-specific domains
        }
        self.country_mapping = {}  # Cache for university-country mapping

    def get_university_country(self, university: str) -> str:
        """Fetch the country of the university using Hipolabs API"""
        try:
            university_lower = university.lower().strip()
            if university_lower in self.country_mapping:
                return self.country_mapping[university_lower]

            response = requests.get(f"http://universities.hipolabs.com/search?name={university}")
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    country = data[0].get('country', 'unknown').lower()
                    self.country_mapping[university_lower] = country
                    return country
            logger.warning(f"No country found for university: {university}")
            return "unknown"
        except Exception as e:
            logger.error(f"Error fetching university country: {str(e)}")
            return "unknown"

    def search_university_info(
        self, 
        university: str, 
        category: str, 
        custom_keywords: List[str] = None,
        country: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Search for university-specific information and government regulations in the given category
        """
        try:
            # Get university domain
            domain = self._get_university_domain(university)
            if not domain:
                logger.warning(f"Could not determine domain for university: {university}")
                # Proceed with broader search if domain not found

            # Define category-specific keywords with synonyms
            category_keywords = {
                'working_student': ['working student', 'student job', 'part-time work', 'lavoro studente', 'student employment', 'work study'],
                'housing': ['student housing', 'dormitory', 'accommodation', 'alloggi studenti', 'residence', 'on-campus living'],
                'research': ['research opportunities', 'undergraduate research', 'research assistant', 'ricerca', 'research programs', 'thesis'],
                'internship': ['internship', 'stage', 'tirocinio', 'practicum', 'work placement'],
                'job_offers': ['job offers', 'career services', 'student employment', 'offerte di lavoro', 'job postings', 'career opportunities'],
                'scholarships': ['scholarships', 'financial aid', 'grants', 'bursaries', 'funding', 'stipends'],
                'visas': ['student visa', 'residence permit', 'immigration', 'visa regulations', 'international student'],
                'custom': custom_keywords or ['student regulations', 'regolamenti', 'policies']
            }

            keywords = category_keywords.get(category, ['student regulations', 'policies'])
            if custom_keywords:
                keywords.extend(custom_keywords)

            results = []
            total_results = 0

            # Search university website
            if domain:
                query = f"site:{domain} {' '.join(keywords)}"
                logger.debug(f"University query: {query}")
                uni_results = self.web_search_agent.focused_search(
                    query=query,
                    keywords=keywords,
                    min_matches=1,
                    max_results=5
                )
                if uni_results['status'] == 'success':
                    results.extend(uni_results['results'])
                    total_results += uni_results['total_results']

            # Search government regulations if country is known
            if country != "unknown" and category in self.government_domains.get(country, []):
                gov_domains = self.government_domains.get(country, [])
                for gov_domain in gov_domains:
                    query = f"site:{gov_domain} {category} student regulations"
                    logger.debug(f"Government query: {query}")
                    gov_results = self.web_search_agent.focused_search(
                        query=query,
                        keywords=keywords,
                        min_matches=1,
                        max_results=3
                    )
                    if gov_results['status'] == 'success':
                        results.extend(gov_results['results'])
                        total_results += gov_results['total_results']

            # Fallback search if no results
            if not results:
                query = f"{university} {category} regulations"
                logger.debug(f"Fallback query: {query}")
                fallback_results = self.web_search_agent.focused_search(
                    query=query,
                    keywords=keywords,
                    min_matches=1,
                    max_results=5
                )
                if fallback_results['status'] == 'success':
                    results.extend(fallback_results['results'])
                    total_results += fallback_results['total_results']

            # Deduplicate results by URL
            seen_urls = set()
            unique_results = []
            for result in results:
                if result['url'] not in seen_urls:
                    seen_urls.add(result['url'])
                    unique_results.append(result)
            results = unique_results[:5]
            total_results = min(total_results, len(results))

            # Summarize results
            summary = self._summarize_results(results, category, university, country)
            return {
                'status': 'success',
                'university': university,
                'category': category,
                'summary': summary,
                'results': results,
                'total_results': total_results
            }

        except Exception as e:
            logger.error(f"Student agent error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'results': []
            }

    def _get_university_domain(self, university: str) -> str:
        """Determine the domain for the given university"""
        university_lower = university.lower().strip()
        # Fuzzy matching for university names
        best_match, score = process.extractOne(
            university_lower, self.university_domains.keys(), scorer=fuzz.token_sort_ratio
        )
        if score > 80:  # Threshold for fuzzy match
            return self.university_domains[best_match]

        # Try Hipolabs API
        try:
            response = requests.get(f"http://universities.hipolabs.com/search?name={university}")
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    domains = data[0].get('domains', [])
                    if domains:
                        return domains[0]
        except Exception as e:
            logger.warning(f"Failed to fetch domain from API for {university}: {str(e)}")

        # Fallback: guess domain based on country
        country = self.get_university_country(university)
        tld = {
            'italy': '.it',
            'united kingdom': '.ac.uk',
            'united states': '.edu',
            # Add more country-specific TLDs
        }.get(country, '.edu')
        cleaned_name = university_lower.replace('university', '').replace('of', '').replace('the', '').strip().replace(' ', '')
        return f"{cleaned_name}{tld}"

    def _summarize_results(self, results: List[Dict], category: str, university: str, country: str) -> Dict:
        """Summarize search results"""
        if not results:
            recommendation = (
                f"No {category} regulations found for {university}. "
                f"Visit the university website or contact the administration. "
                f"Check government resources for {country} if applicable."
            )
            return {
                'recommendation': recommendation,
                'confidence': 0.0
            }

        titles = [r['title'] for r in results]
        recommendation = (
            f"Found {len(results)} relevant resources for {category} at {university}. "
            f"Explore the links for detailed policies and regulations."
        )
        if country != "unknown":
            recommendation += f" Also check {country} government websites for national regulations."
        return {
            'recommendation': recommendation,
            'confidence': min(1.0, len(results) / 5)
        }