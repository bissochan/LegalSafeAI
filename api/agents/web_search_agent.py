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
import pdfplumber

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Data class for storing filtered search results"""
    title: str
    url: str
    content: str
    content_summary: str
    relevance_score: float
    matched_keywords: List[str]
    key_points: List[str]

class WebSearchAgent:
    """Agent for performing focused web searches with keyword filtering"""
    
    def __init__(self):
        load_dotenv()
        self.serp_api_key = os.getenv("SERPAPI_KEY")
        if not self.serp_api_key:
            raise ValueError("SERPAPI_KEY not found in environment variables")
        
        self.cache_dir = "search_cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def focused_search(
        self, 
        query: str, 
        keywords: List[str], 
        min_matches: int = 1,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform a focused web search with keyword filtering
        """
        try:
            # Check cache
            cache_key = f"{query}_{'_'.join(keywords)}".replace(' ', '_')
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    logger.debug(f"Returning cached results for query: {query}")
                    return json.load(f)

            search_results = self._perform_search(query, max_results * 2)
            if search_results['status'] != 'success':
                return search_results
            
            filtered_results = []
            for result in search_results['raw_results']:
                if not isinstance(result, dict):
                    logger.warning(f"Skipping invalid search result: {result}")
                    continue
                
                url = result.get('link') or result.get('url')
                title = result.get('title')
                if not url or not title:
                    logger.warning(f"Skipping result missing url or title: {result}")
                    continue
                
                content = self._fetch_page_content(url)
                if not content:
                    logger.debug(f"No content fetched for URL: {url}")
                    continue
                
                score, matched_kw = self._calculate_relevance(
                    content=content,
                    title=title,
                    keywords=keywords
                )
                
                if len(matched_kw) >= min_matches:
                    content_summary, key_points = self._summarize_content(content, matched_kw)
                    filtered_results.append(SearchResult(
                        title=title,
                        url=url,
                        content=content[:1000],  # Limit content size
                        content_summary=content_summary,
                        relevance_score=score,
                        matched_keywords=matched_kw,
                        key_points=key_points
                    ))
            
            filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)
            filtered_results = filtered_results[:max_results]
            
            if not filtered_results:
                logger.warning(f"No valid results found for query: {query}")
                result = {
                    'status': 'success',
                    'query': query,
                    'keywords': keywords,
                    'total_results': 0,
                    'results': []
                }
            else:
                result = {
                    'status': 'success',
                    'query': query,
                    'keywords': keywords,
                    'total_results': len(filtered_results),
                    'results': [vars(r) for r in filtered_results]
                }
            
            # Cache results
            with open(cache_path, 'w') as f:
                json.dump(result, f)
            
            return result

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
                logger.error(f"Search API error: {response.status_code} - {response.text}")
                return {
                    'status': 'error',
                    'error': f'Search API error: {response.status_code}',
                    'raw_results': []
                }

            data = response.json()
            logger.debug(f"SerpAPI response: {json.dumps(data, indent=2)}")
            raw_results = data.get('organic_results', [])
            if not raw_results:
                logger.warning(f"No organic results for query: {query}")
            
            return {
                'status': 'success',
                'raw_results': raw_results
            }

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'raw_results': []
            }

    def _fetch_page_content(self, url: str) -> str:
        """Fetch and parse webpage content, including PDFs"""
        try:
            if url.lower().endswith('.pdf'):
                response = requests.get(url, timeout=15)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch PDF {url}: HTTP {response.status_code}")
                    return ""
                with open('temp.pdf', 'wb') as f:
                    f.write(response.content)
                with pdfplumber.open('temp.pdf') as pdf:
                    content = " ".join(page.extract_text() or "" for page in pdf.pages)
                os.remove('temp.pdf')
                return content.strip()

            response = requests.get(
                url,
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            if response.status_code != 200:
                logger.warning(f"Failed to fetch URL {url}: HTTP {response.status_code}")
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
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
            if keyword_lower in ['regulation', 'regulations', 'regolamenti', 'policy', 'policies']:
                score += 1.5
        
        # Boost for policy-related terms in content
        policy_terms = ['policy', 'policies', 'regulation', 'regulations', 'guidelines', 'rules', 'regolamenti']
        for term in policy_terms:
            if term in content_lower:
                score += 0.5
        
        return score, matched_keywords

    def _summarize_content(self, content: str, keywords: List[str]) -> tuple[str, List[str]]:
        """Generate a summary and key points from content"""
        content_lower = content.lower()
        sentences = content.split('. ')
        relevant_sentences = []
        key_points = []
        
        for sentence in sentences:
            if any(keyword.lower() in sentence.lower() for keyword in keywords):
                relevant_sentences.append(sentence.strip())
                if len(key_points) < 3:  # Limit to 3 key points
                    key_points.append(sentence.strip())
        
        summary = " ".join(relevant_sentences[:3]) or content[:200]
        return summary, key_points