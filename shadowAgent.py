import requests
import json
from dotenv import load_dotenv
import os

class ShadowAgent:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        # Get the API key from the environment
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("API key not found. Please set OPENROUTER_API_KEY in your .env file.")

        # Placeholder contract
        self.placeholder_contract = """
        This is a contract between the parties. The parties agree to the following terms and conditions. 
        The first party shall provide services to the second party. The second party shall pay the first 
        party a fee of $1000. The first party shall not be liable for any damages arising from the services 
        provided. The contract shall be governed by the laws of the state of California.
        """

    def analyze(self, contract=None):
        """
        Analyze the provided contract for gray areas. If no contract is provided, use the placeholder contract.

        Args:
            contract (str): The contract to analyze.

        Returns:
            str: The analysis result from the model.
        """
        if not contract:
            contract = self.placeholder_contract

        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Replace with your site URL if needed.
                "X-Title": "<YOUR_SITE_NAME>",      # Optional. Replace with your site name if needed.
            },
            data=json.dumps({
                "model": "google/gemini-2.0-flash-001",  # Optional
                "messages": [
                    {
                        "role": "system",
                        "content": """Act as an experienced legal consultant tasked with thoroughly analyzing a contract. 
                        Your primary goal is to identify any areas of ambiguity, potential pitfalls, unfavorable clauses, 
                        formal errors, or defects within the contract that could pose risks or uncertainties for my client.

                        Specifically, I need you to:

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
                    },
                    {
                        "role": "user",
                        "content": f"Hi, this is a contract, can you analyze if it is shady for me?\nContract: {contract}"
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


