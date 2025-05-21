import os
from dotenv import load_dotenv
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
from dataclasses import dataclass
from urllib.parse import quote_plus
import json
import re

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for storing filtered search results"""
    title: str
    url: str
    content: str
    relevance_score: float
    matched_keywords: List[str]

class WebSearchAgent:
    """Agent for performing focused web searches with keyword filtering"""
    
    def __init__(self):
        load_dotenv()
        self.serp_api_key = os.getenv("SERPAPI_KEY")
        if not self.serp_api_key:
            raise ValueError("SERPAPI_KEY not found in environment variables")
        
        # Configure output directory for cached results
        self.cache_dir = "search_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def focused_search(
        self, 
        query: str, 
        keywords: List[str], 
        min_matches: int = 2,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform a focused web search with keyword filtering
        
        Args:
            query: Search query string
            keywords: List of keywords to filter results
            min_matches: Minimum number of keywords that must match
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing filtered search results and metadata
        """
        try:
            # Perform initial search
            search_results = self._perform_search(query, max_results * 2)  # Get more results for filtering
            
            if search_results['status'] != 'success':
                return search_results
            
            # Process and filter results
            filtered_results = []
            
            for result in search_results['raw_results']:
                # Fetch and parse page content
                content = self._fetch_page_content(result['url'])
                if not content:
                    continue
                
                # Calculate relevance score and check keyword matches
                score, matched_kw = self._calculate_relevance(
                    content=content,
                    title=result['title'],
                    keywords=keywords
                )
                
                if len(matched_kw) >= min_matches:
                    filtered_results.append(SearchResult(
                        title=result['title'],
                        url=result['url'],
                        content=self._extract_relevant_sections(content, matched_kw),
                        relevance_score=score,
                        matched_keywords=matched_kw
                    ))
            
            # Sort by relevance and limit results
            filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)
            filtered_results = filtered_results[:max_results]
            
            return {
                'status': 'success',
                'query': query,
                'keywords': keywords,
                'total_results': len(filtered_results),
                'results': [vars(r) for r in filtered_results]
            }

        except Exception as e:
            logger.error(f"Focused search error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'query': query,
                'keywords': keywords,
                'results': []
            }

    def _perform_search(self, query: str, num_results: int) -> Dict[str, Any]:
        """Perform the initial web search"""
        try:
            response = requests.get(
                "https://serpapi.com/search",
                params={
                    "api_key": self.serp_api_key,
                    "q": quote_plus(query),
                    "num": num_results,
                    "engine": "google"
                }
            )
            
            if response.status_code != 200:
                return {
                    'status': 'error',
                    'error': f'Search API error: {response.status_code}',
                    'raw_results': []
                }

            data = response.json()
            return {
                'status': 'success',
                'raw_results': data.get('organic_results', [])
            }

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'raw_results': []
            }

    def _fetch_page_content(self, url: str) -> str:
        """Fetch and parse webpage content"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            return soup.get_text(separator=' ', strip=True)

        except Exception as e:
            logger.warning(f"Failed to fetch content from {url}: {e}")
            return ""

    def _calculate_relevance(
        self, 
        content: str, 
        title: str, 
        keywords: List[str]
    ) -> tuple[float, List[str]]:
        """Calculate relevance score and find matched keywords"""
        content_lower = content.lower()
        title_lower = title.lower()
        matched_keywords = []
        score = 0.0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title_lower:
                score += 2.0
                matched_keywords.append(keyword)
            if keyword_lower in content_lower:
                score += 1.0
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
                
        return score, matched_keywords

    def _extract_relevant_sections(self, content: str, keywords: List[str], context_chars: int = 200) -> str:
        """Extract relevant sections of content containing keywords"""
        relevant_sections = []
        
        for keyword in keywords:
            pattern = re.compile(f".{{0,{context_chars}}}{re.escape(keyword)}.{{0,{context_chars}}}", 
                               re.IGNORECASE)
            matches = pattern.finditer(content)
            
            for match in matches:
                relevant_sections.append(match.group())
        
        return "\n...\n".join(relevant_sections)