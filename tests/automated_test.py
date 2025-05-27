import os
import requests
import json
from datetime import datetime
import time

class AutomatedTester:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.output_dir = "automated_tests"
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create output directory
        self.test_dir = os.path.join(self.output_dir, self.timestamp)
        os.makedirs(self.test_dir, exist_ok=True)

        self.default_focal_points = [
            "working_hours",
            "compensation",
            "benefits",
            "termination",
            "intellectual_property"
        ]

    def save_response(self, filename: str, content: dict):
        """Save response to a file"""
        filepath = os.path.join(self.test_dir, f"{filename}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    def test_contract_analysis(self, contract_path: str, focal_points: list = None):
        """
        Run complete contract analysis and save results
        
        Args:
            contract_path: Path to contract file
            focal_points: Optional list of focal points for analysis
        """
        print("Starting contract analysis test...")

        try:
            # Extract text
            with open(contract_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.base_url}/api/document/extract", files=files)
            
            if response.status_code != 200:
                raise Exception(f"Text extraction failed: {response.status_code}")
            
            contract_text = response.json().get('text', '')
            self.save_response('01_extracted_text', {'text': contract_text})

            # Run analyses with focal points
            analyses = [
                ('shadow', '/api/shadow/analyze'),
                ('summary', '/api/summary/analyze'),
                ('evaluator', '/api/evaluator/evaluate')
            ]

            for analysis_type, endpoint in analyses:
                payload = {
                    'text': contract_text,
                    'focal_points': focal_points if focal_points else None
                }
                
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=payload
                )
                if response.status_code != 200:
                    raise Exception(f"{analysis_type} analysis failed: {response.status_code}")
                
                self.save_response(f"02_{analysis_type}_analysis", response.json())

            print("Contract analysis test completed successfully")

        except Exception as e:
            print(f"Contract analysis test failed: {str(e)}")
            self.save_response('error_log', {'error': str(e)})

    def test_chat_interaction(self, contract_path: str):
        """Test chat interactions with predefined questions"""
        print("Starting chat interaction test...")

        questions = [
            "What are the main terms of compensation in this contract?",
            "Explain the termination clauses in detail.",
            "What are my obligations regarding confidentiality?",
            "Are there any non-compete clauses? If yes, explain them.",
            "What benefits are included in this contract?"
        ]

        try:
            # Start chat session
            with open(contract_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.base_url}/api/chat/start", files=files)
            
            if response.status_code != 200:
                raise Exception(f"Chat session start failed: {response.status_code}")
            
            session_data = response.json()
            chat_id = session_data.get('session_id')

            # Ask each question and save response
            for i, question in enumerate(questions, 1):
                chat_interaction = {
                    'question': question,
                    'timestamp': datetime.now().isoformat()
                }

                response = requests.post(
                    f"{self.base_url}/api/chat/message",
                    json={
                        'session_id': chat_id,
                        'message': question
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"Chat message failed: {response.status_code}")
                
                chat_interaction['response'] = response.json()
                self.save_response(f"03_chat_interaction_{i}", chat_interaction)
                
                # Add delay between questions
                time.sleep(2)

            # End chat session
            requests.post(f"{self.base_url}/api/chat/end", json={'session_id': chat_id})
            print("Chat interaction test completed successfully")

        except Exception as e:
            print(f"Chat interaction test failed: {str(e)}")
            self.save_response('chat_error_log', {'error': str(e)})

def main():
    tester = AutomatedTester()
    
    # Path to your test contract
    contract_path = "path/to/your/test_contract.pdf"
    
    # Test with focal points
    focal_points = [
        "working_hours",
        "compensation",
        "benefits",
        "termination",
        "intellectual_property"
    ]
    
    # Run tests with and without focal points
    print("\nRunning test with focal points...")
    tester.test_contract_analysis(contract_path, focal_points)
    tester.test_chat_interaction(contract_path)
    
    print("\nRunning test without focal points...")
    tester.test_contract_analysis(contract_path)
    tester.test_chat_interaction(contract_path)

if __name__ == "__main__":
    main()