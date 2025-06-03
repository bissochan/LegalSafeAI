# api/agents/question_analyzer_agent.py
import requests
import re
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os
from flask import Flask
from models import db, Preference, ChatHistory
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class QuestionAnalyzerAgent:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.areas = [
            'sick_leave', 'vacation', 'overtime', 'termination', 'confidentiality',
            'non_compete', 'intellectual_property', 'governing_law', 'jurisdiction',
            'dispute_resolution', 'liability', 'salary', 'benefits', 'work_hours',
            'performance_evaluation', 'duties', 'responsibilities'
        ]
        self._frequent_questions_cache = None
        self._cache_timestamp = None
        self._cache_duration = 3600  # Cache for 1 hour

    def analyze(self, user_id: int, question: str) -> List[str]:
        """Analyze a question to identify relevant contract areas and update preferences."""
        logger.info(f"Analyzing {user_id}: {question[:50]}...")
        system_prompt = """
        You are an expert in employment contracts. Given a user's question about a contract,
        identify which of the following areas are most relevant to the question:
        - sick_leave
        - vacation
        - overtime
        - termination
        - confidentiality
        - non_compete
        - intellectual_property
        - governing_law
        - jurisdiction
        - dispute_resolution
        - liability
        - salary
        - benefits
        - work_hours
        - performance_evaluation
        - duties
        - responsibilities

        Return a list of up to 3 areas in order of relevance as a comma-separated string
        (e.g., "salary,benefits,work_hours"). If no areas are relevant, return an empty string.
        Only include areas from the provided list.
        """
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Question: {question}"}
                    ],
                    "max_tokens": 100
                },
                timeout=15
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            
            # Parse response with regex to handle varied formats
            pattern = r'\b(' + '|'.join(self.areas) + r')\b'
            areas = [area for area in re.findall(pattern, content, re.IGNORECASE) if area in self.areas]
            valid_areas = list(dict.fromkeys(areas))[:3]  # Remove duplicates, keep order
            
            # Initialize preferences if not exist
            existing_prefs = {p.area: p for p in Preference.query.filter_by(user_id=user_id).all()}
            for area in self.areas:
                if area not in existing_prefs:
                    pref = Preference(user_id=user_id, area=area, weight=1.0)
                    db.session.add(pref)
                    existing_prefs[area] = pref
            
            # Update preference weights
            for area, pref in existing_prefs.items():
                if area in valid_areas:
                    pref.weight = min(pref.weight + 0.2, 5.0)  # Increase weight
                else:
                    pref.weight = max(pref.weight - 0.05, 0.5)  # Decrease weight
            db.session.commit()
            
            logger.debug(f"Updated preferences for user_id {user_id}: {valid_areas}")
            return valid_areas
        except requests.RequestException as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            db.session.rollback()
            return []
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            db.session.rollback()
            return []
        except Exception as e:
            logger.error(f"Unexpected error analyzing question: {str(e)}")
            db.session.rollback()
            return []

    def get_choices(self, user_id: int) -> List[str]:
        """Get the minimal set of choices with combined weight > 60% or top 5 by weight."""
        try:
            preferences = Preference.query.filter_by(user_id=user_id).all()
            if not preferences:
                logger.debug(f"No preferences for user_id {user_id}, returning default areas")
                return self.areas[:5]
            
            # Calculate total weight
            total_weight = sum(pref.weight for pref in preferences)
            target_weight = total_weight * 0.6
            
            # Sort preferences by weight (descending)
            sorted_prefs = sorted(preferences, key=lambda x: x.weight, reverse=True)
            
            # Select minimal set exceeding 60%
            selected_areas = []
            current_weight = 0
            for pref in sorted_prefs:
                if len(selected_areas) >= 5:
                    break
                selected_areas.append(pref.area)
                current_weight += pref.weight
                if current_weight >= target_weight:
                    break
            
            # Ensure at least 5 areas
            if len(selected_areas) < 5 and len(sorted_prefs) > len(selected_areas):
                remaining = [p.area for p in sorted_prefs if p.area not in selected_areas]
                selected_areas.extend(remaining[:5 - len(selected_areas)])
            
            logger.debug(f"Choices for user_id {user_id}: {selected_areas}")
            return selected_areas[:5]
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching choices: {str(e)}")
            return self.areas[:5]
        except Exception as e:
            logger.error(f"Unexpected error fetching choices: {str(e)}")
            return self.areas[:5]

    # api/agents/question_analyzer_agent.py
def get_frequent_questions(self, user_id: Optional[int] = None, limit: int = 5) -> List[Dict]:
    """Get the most frequently asked questions for a user or globally, with caching."""
    try:
        now = datetime.utcnow()
        
        # Check cache
        if (self._frequent_questions_cache and 
            self._cache_timestamp and 
            (now - self._cache_timestamp).total_seconds() < self._cache_duration):
            logger.debug("Returning cached frequent questions")
            return self._frequent_questions_cache[:limit]
        
        # Query frequent questions
        query = ChatHistory.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        questions = (
            query
            .group_by(ChatHistory.question)
            .order_by(db.func.count().desc())
            .limit(limit)
            .all()
        )
        
        if questions:
            result = [
                {
                    "question": q.question,
                    "response": q.response or q.question,
                    "count": ChatHistory.query.filter_by(question=q.question).count()
                }
                for q in questions
            ]
        else:
            # Return default questions if none exist
            result = [
                {"question": "What are the termination clauses in the contract?", "response": "What are the termination clauses in the contract?", "count": 0},
                {"question": "Is the non-compete clause enforceable under Italian law?", "response": "Is the non-compete clause enforceable under Italian law?", "count": 0},
                {"question": "What are the salary and benefits details?", "response": "What are the salary and benefits details?", "count": 0},
                {"question": "How many vacation days are provided?", "response": "How many vacation days are provided?", "count": 0},
                {"question": "What are the overtime policies?", "response": "What are the overtime policies?", "count": 0}
            ]
            logger.debug("No frequent questions found, returning default questions")
        
        # Update cache
        self._frequent_questions_cache = result
        self._cache_timestamp = now
        logger.debug(f"Cached frequent questions: {result}")
        return result[:limit]
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching frequent questions: {str(e)}")
        return [
            {"question": "What are the termination clauses in the contract?", "response": "What are the termination clauses in the contract?", "count": 0},
            {"question": "Is the non-compete clause enforceable under Italian law?", "response": "Is the non-compete clause enforceable under Italian law?", "count": 0},
            {"question": "What are the salary and benefits details?", "response": "What are the salary and benefits details?", "count": 0},
            {"question": "How many vacation days are provided?", "response": "How many vacation days are provided?", "count": 0},
            {"question": "What are the overtime policies?", "response": "What are the overtime policies?", "count": 0}
        ]
    except Exception as e:
        logger.error(f"Unexpected error fetching frequent questions: {str(e)}")
        return [
            {"question": "What are the termination clauses in the contract?", "response": "What are the termination clauses in the contract?", "count": 0},
            {"question": "Is the non-compete clause enforceable under Italian law?", "response": "Is the non-compete clause enforceable under Italian law?", "count": 0},
            {"question": "What are the salary and benefits details?", "response": "What are the salary and benefits details?", "count": 0},
            {"question": "How many vacation days are provided?", "response": "How many vacation days are provided?", "count": 0},
            {"question": "What are the overtime policies?", "response": "What are the overtime policies?", "count": 0}
        ]