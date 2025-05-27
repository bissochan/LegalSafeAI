import requests
import json
from dotenv import load_dotenv
import os
from typing import List, Dict, Any

class ShadowAgent:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # Get the API key from the environment
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set OPENROUTER_API_KEY in your .env file.")

        self.base_prompt = """You are a legal contract analysis expert. Analyze the contract provided and generate a detailed report.
        If focal points are provided, pay special attention to those areas while maintaining a comprehensive analysis.
        
        Structure your analysis as follows:
        1. Overview of key terms and conditions
        2. Detailed analysis of focal points (if provided) or main contract sections
        3. Potential risks and concerns
        4. Recommendations for improvement
        5. Overall assessment
        
        For each focal point or main section:
        - Explain the relevant terms
        - Identify potential issues
        - Suggest improvements
        - Rate the clarity and fairness (1-10)
        """

    def analyze(self, contract_text: str, language: str = 'en', focal_points: List[str] = None) -> str:
        """
        Analyze the provided contract for gray areas in the specified language.

        Args:
            contract_text (str): The contract to analyze.
            language (str): The language for the analysis response.
            focal_points: Optional list of specific areas to focus on

        Returns:
            str: The analysis result from the model.
        """
        if not contract_text:
            contract_text = ""

        # Add language to system prompt
        system_prompt = f"""Analyze this employment contract and respond in {language}.
        Follow this template for your response:
        Act as an experienced legal consultant tasked with thoroughly analyzing a contract. 
        Your primary goal is to identify any areas of ambiguity, potential pitfalls, unfavorable clauses, 
        formal errors, or defects within the contract that could pose risks or uncertainties for my client.

        Specifically, I need you to:

            respond in {language}
            Clearly highlight each section or clause that you deem problematic or unclear.
            Explain concisely and understandably the nature of the identified issue and its potential implications.
            Suggest possible modifications or additions to the contract to resolve ambiguities or mitigate risks.
            Pay close attention to:
                Unclear or missing definitions.
                Broad or unspecific liability exclusion clauses.
                Ambiguous or potentially burdensome termination clauses.
                Unclear payment terms and penalties.
                Clauses related to intellectual property (if applicable).
                Governing law and jurisdiction clauses (if applicable).
                Any discrepancies or contradictions between different clauses.
            Provide a concise summary of the main critical points identified.
            Always respond kind and polite."""

        # Prepare the prompt
        if focal_points:
            analysis_prompt = f"{system_prompt}\n\nFocus especially on these areas:\n"
            for point in focal_points:
                analysis_prompt += f"- {point}\n"
        else:
            analysis_prompt = system_prompt

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            data=json.dumps({
                "model": "google/gemini-2.0-flash-001",  # Optional
                "messages": [
                    {
                        "role": "system",
                        "content": analysis_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Hi, this is a contract, can you analyze if it is shady for me? is important that you respond in {language}\nContract: {contract_text}"
                    }
                ]
            })
        )

        # Handle and return the response
        if response.status_code == 200:
            try:
                response_data = response.json()
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    return response_data['choices'][0]['message']['content']
                else:
                    return "No valid response from the model."
            except json.JSONDecodeError:
                return "Failed to decode the response JSON."
        else:
            return f"Request failed with status code {response.status_code}: {response.text}"


