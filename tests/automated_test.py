import os
import requests
import json
from datetime import datetime
import time
import random
import logging
import traceback
from typing import List, Dict, Optional
import urllib3

# Disable urllib3 warnings for cleaner logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomatedTester:
    def __init__(self, contract_dir: str):
        self.base_url = "http://localhost:5000"
        self.contract_dir = contract_dir
        self.output_dir = "automated_tests"
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create output directory
        self.test_dir = os.path.join(self.output_dir, self.timestamp)
        os.makedirs(self.test_dir, exist_ok=True)
        logger.info(f"Created test output directory: {self.test_dir}")

        # List of interests for analysis
        self.interests = [
            'sick_leave', 'vacation', 'overtime', 'termination', 'confidentiality',
            'non_compete', 'intellectual_property', 'governing_law', 'jurisdiction',
            'dispute_resolution', 'liability', 'salary', 'benefits', 'work_hours',
            'performance_evaluation', 'duties', 'responsibilities'
        ]

        # Question pool for chat interactions
        self.question_pool = {
            'sick_leave': [
                "What are the provisions for sick leave in this contract?",
                "How many sick days are provided annually?",
                "Are unused sick days carried over to the next year?",
                "Is a doctor's note required for sick leave?",
                "Are there any penalties for excessive sick leave?"
            ],
            'vacation': [
                "What is the vacation policy outlined in the contract?",
                "How many vacation days are provided per year?",
                "How does vacation accrual work in this contract?",
                "Are there restrictions on when vacation can be taken?",
                "Can unused vacation days be paid out or carried over?"
            ],
            'overtime': [
                "What are the overtime compensation terms in the contract?",
                "Is overtime mandatory or voluntary?",
                "How is overtime calculated (e.g., time-and-a-half)?",
                "Are there limits on overtime hours?",
                "Who is eligible for overtime pay?"
            ],
            'termination': [
                "What are the conditions for terminating the contract?",
                "Is there a notice period required for termination?",
                "Are there any severance payments outlined?",
                "What constitutes a breach leading to termination?",
                "Are there any post-termination obligations?"
            ],
            'confidentiality': [
                "What are the confidentiality obligations in the contract?",
                "What types of information are considered confidential?",
                "How long does the confidentiality obligation last?",
                "Are there penalties for breaching confidentiality?",
                "Who can confidential information be shared with?"
            ],
            'non_compete': [
                "Is there a non-compete clause in the contract?",
                "What is the duration of the non-compete clause?",
                "What geographic areas does the non-compete cover?",
                "What activities are restricted by the non-compete?",
                "Is the non-compete enforceable under the contract's governing law?"
            ],
            'intellectual_property': [
                "Who owns the intellectual property created during employment?",
                "Are there any clauses regarding assignment of intellectual property?",
                "What types of intellectual property are covered in the contract?",
                "Are there any exceptions to intellectual property assignment?",
                "How are pre-existing intellectual property rights handled?"
            ],
            'governing_law': [
                "What is the governing law of the contract?",
                "How does the governing law affect contract enforcement?",
                "Are there any specific legal frameworks referenced?",
                "Does the governing law impact dispute resolution?",
                "Is the governing law favorable to the employee or employer?"
            ],
            'jurisdiction': [
                "Which jurisdiction governs disputes under this contract?",
                "Are there specific courts designated for disputes?",
                "Can disputes be resolved in multiple jurisdictions?",
                "How does jurisdiction affect legal proceedings?",
                "Is there a choice of law clause related to jurisdiction?"
            ],
            'dispute_resolution': [
                "What is the process for resolving disputes in the contract?",
                "Is arbitration or mediation required for disputes?",
                "Are there any time limits for initiating dispute resolution?",
                "Who bears the cost of dispute resolution processes?",
                "Can disputes be escalated to litigation?"
            ],
            'liability': [
                "What are the liability clauses in the contract?",
                "Are there limits to liability for either party?",
                "Who is responsible for damages caused by breaches?",
                "Are there indemnification clauses in the contract?",
                "How are liability disputes handled?"
            ],
            'salary': [
                "What is the base salary outlined in the contract?",
                "Are there provisions for salary increases or bonuses?",
                "How frequently is salary paid (e.g., monthly, bi-weekly)?",
                "Are there deductions or withholdings specified?",
                "Is there a performance-based component to the salary?"
            ],
            'benefits': [
                "What benefits are included in the contract?",
                "Are health insurance benefits provided?",
                "Are there retirement or pension benefits outlined?",
                "What other perks or benefits are included?",
                "Are benefits subject to change during the contract term?"
            ],
            'work_hours': [
                "What are the expected work hours in the contract?",
                "Are there provisions for flexible working hours?",
                "Is remote work or telecommuting allowed?",
                "Are there penalties for not meeting work hour requirements?",
                "How are work hours tracked or reported?"
            ],
            'performance_evaluation': [
                "How is performance evaluated under the contract?",
                "What are the criteria for performance reviews?",
                "How often are performance evaluations conducted?",
                "Are performance evaluations tied to compensation?",
                "Who conducts the performance evaluations?"
            ],
            'duties': [
                "What are the primary duties outlined in the contract?",
                "Are there specific tasks assigned to the role?",
                "Can duties be modified during the contract term?",
                "Are there any reporting requirements for duties?",
                "What happens if duties are not performed adequately?"
            ],
            'responsibilities': [
                "What are the key responsibilities in the contract?",
                "Are responsibilities clearly defined for the role?",
                "Are there any supervisory responsibilities?",
                "How are responsibilities enforced or monitored?",
                "Can additional responsibilities be assigned?"
            ]
        }

    def save_test_result(self, contract_name: str, test_num: int, content: Dict):
        """Save test results to a file with error tracking"""
        filename = f"{contract_name}_test{test_num}.txt"
        filepath = os.path.join(self.test_dir, filename)
        
        content['metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'contract_name': contract_name,
            'test_number': test_num,
            'has_errors': len(content.get('errors', [])) > 0
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved test results to {filepath}")

            if content.get('errors'):
                error_log = os.path.join(self.test_dir, f"{contract_name}_test{test_num}_errors.txt")
                with open(error_log, 'w', encoding='utf-8') as f:
                    json.dump({'errors': content['errors']}, f, ensure_ascii=False, indent=2)
                logger.info(f"Saved error log to {error_log}")
        except Exception as e:
            logger.error(f"Failed to save test result for {contract_name}_test{test_num}: {str(e)}")

    def get_contract_files(self) -> List[str]:
        """Get list of PDF contract files in the contract directory"""
        if os.path.isdir(self.contract_dir):
            return [f for f in os.listdir(self.contract_dir) if f.endswith('.pdf')]
        return []

    def test_contract_analysis(self, contract_path: str, focal_points: Optional[List[str]], 
                             test_num: int, contract_name: str) -> Dict:
        """Run contract analysis and return results for a specific test"""
        logger.info(f"Starting contract analysis test {test_num} for {contract_name} with focal points: {focal_points or 'None'}")
        print(f"Running analysis test {test_num} for {contract_name}...")
        test_results = {
            'contract_name': contract_name,
            'test_number': test_num,
            'focal_points': focal_points if focal_points else [],
            'analysis': {},
            'errors': []
        }

        try:
            # Extract text from PDF
            with open(contract_path, 'rb') as f:
                files = {'file': f}
                for attempt in range(3):
                    delay = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    try:
                        response = requests.post(
                            f"{self.base_url}/api/document/extract",
                            files=files,
                            headers={'Accept': 'application/json'},
                            timeout=15
                        )
                        response.raise_for_status()
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        if attempt == 2:
                            raise Exception(f"Text extraction failed after 3 attempts: {str(e)}")
                        logger.warning(f"Extraction attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
            
            contract_text = response.json().get('text', '')
            if not contract_text:
                raise Exception("No text extracted from contract")
            test_results['analysis']['extracted_text'] = contract_text

            # Run analyses
            analyses = [
                ('shadow', '/api/shadow/analyze'),
                ('summary', '/api/summary/analyze'),
                ('evaluator', '/api/evaluator/evaluate')
            ]

            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            for analysis_type, endpoint in analyses:
                print(f"Analyzing {analysis_type} for test {test_num}...")
                payload = {
                    'text': contract_text,
                    'focal_points': focal_points if focal_points else None
                }
                for attempt in range(3):
                    delay = 2 ** attempt
                    try:
                        response = requests.post(
                            f"{self.base_url}{endpoint}",
                            json=payload,
                            headers=headers,
                            timeout=30
                        )
                        response.raise_for_status()
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        if attempt == 2:
                            raise Exception(f"{analysis_type} analysis failed after 3 attempts: {str(e)}")
                        logger.warning(f"{analysis_type} attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
                
                test_results['analysis'][analysis_type] = response.json()

            logger.info(f"Contract analysis test {test_num} for {contract_name} completed successfully")
            print(f"Analysis test {test_num} for {contract_name} completed.")

        except Exception as e:
            logger.error(f"Contract analysis test {test_num} for {contract_name} failed: {str(e)}")
            test_results['errors'].append({'analysis_error': str(e)})
            print(f"Analysis test {test_num} for {contract_name} failed: {str(e)}")
        
        return test_results

    def test_chat_interaction(self, contract_path: str, focal_points: Optional[List[str]], 
                             test_num: int, contract_name: str, test_results: Dict):
        logger.info(f"Starting chat interaction test {test_num} for {contract_name}")
        print(f"Running chat interaction test {test_num} for {contract_name}...")
        test_results['chat_interactions'] = []
    
        try:
            # Extract text
            with open(contract_path, 'rb') as f:
                files = {'file': f}
                for attempt in range(3):
                    delay = 2 ** attempt
                    try:
                        extract_response = requests.post(
                            f"{self.base_url}/api/document/extract",
                            files=files,
                            headers={'Accept': 'application/json'},
                            timeout=15
                        )
                        extract_response.raise_for_status()
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        if attempt == 2:
                            raise Exception(f"Text extraction failed after 3 attempts: {str(e)}")
                        logger.warning(f"Extraction attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
            
            contract_text = extract_response.json().get('text', '')
            if not contract_text:
                raise Exception("No text extracted from contract")
    
            # Start chat session with retries
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            chat_id = None
            for session_attempt in range(2):
                for attempt in range(3):
                    delay = 2 ** attempt
                    try:
                        start_response = requests.post(
                            f"{self.base_url}/api/chat/start",
                            json={'contract_text': contract_text},
                            headers=headers,
                            timeout=15
                        )
                        start_response.raise_for_status()
                        session_data = start_response.json()
                        chat_id = session_data.get('session_id')
                        if chat_id:
                            logger.info(f"Chat session started with ID: {chat_id}")
                            break
                        raise Exception(f"No session ID returned: {json.dumps(session_data)}")
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        if attempt == 2:
                            raise Exception(f"Chat session start failed after 3 attempts: {str(e)}")
                        logger.warning(f"Chat start attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
                    except requests.exceptions.HTTPError as e:
                        error_response = start_response.json() if start_response.text else {}
                        raise Exception(f"Chat session start failed: {str(e)}, Server response: {json.dumps(error_response)}")
                
                if chat_id:
                    break
                logger.warning(f"Session attempt {session_attempt + 1} failed. Retrying session start...")
                time.sleep(5)
    
            if not chat_id:
                raise Exception("Failed to start chat session after multiple attempts")
    
            # Select questions
            if focal_points:
                available_questions = []
                for focal_point in focal_points:
                    available_questions.extend(self.question_pool.get(focal_point, []))
            else:
                available_questions = [q for sublist in self.question_pool.values() for q in sublist]
            
            if not available_questions:
                raise Exception("No questions available for selected focal points")
            
            selected_questions = random.sample(
                available_questions,
                min(5, len(available_questions))
            )
    
            # Ask questions
            for i, question in enumerate(selected_questions, 1):
                print(f"Sending chat question {i} for test {test_num}...")
                chat_interaction = {
                    'question': question,
                    'timestamp': datetime.now().isoformat()
                }
                for attempt in range(3):
                    delay = 2 ** attempt
                    try:
                        response = requests.post(
                            f"{self.base_url}/api/chat/message",
                            json={
                                'session_id': chat_id,
                                'message': question
                            },
                            headers=headers,
                            timeout=15
                        )
                        response.raise_for_status()
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        if attempt == 2:
                            raise Exception(f"Chat message {i} failed after 3 attempts: {str(e)}")
                        logger.warning(f"Chat message {i} attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                        time.sleep(delay)
                    except requests.exceptions.HTTPError as e:
                        error_response = response.json() if response.text else {}
                        raise Exception(f"Chat message {i} failed: {str(e)}, Server response: {json.dumps(error_response)}")
                
                chat_response = response.json()
                chat_interaction['response'] = chat_response
                
                # Validate response content
                response_text = chat_response.get('response', '')
                if response_text.startswith('Received:'):
                    logger.warning(f"Chat response for question {i} is a placeholder: {response_text}")
                
                test_results['chat_interactions'].append(chat_interaction)
                time.sleep(2)
    
            # End chat session
            for attempt in range(3):
                delay = 2 ** attempt
                try:
                    requests.post(
                        f"{self.base_url}/api/chat/end",
                        json={'session_id': chat_id},
                        headers=headers,
                        timeout=15
                    )
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    if attempt == 2:
                        logger.warning(f"Failed to end chat session after 3 attempts: {str(e)}")
                    logger.warning(f"Chat end attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                    time.sleep(delay)
            
            logger.info(f"Chat interaction test {test_num} for {contract_name} completed successfully")
            print(f"Chat interaction test {test_num} for {contract_name} completed.")
    
        except Exception as e:
            logger.error(f"Chat interaction test {test_num} for {contract_name} failed: {str(e)}")
            test_results['errors'].append({'chat_error': str(e)})
            print(f"Chat interaction test {test_num} for {contract_name} failed: {str(e)}")
    
    def run_tests(self):
        """Run tests for all PDF contracts in the directory"""
        contract_files = self.get_contract_files()
        if not contract_files:
            logger.error("No PDF contracts found in the directory.")
            print("No PDF contracts found in the directory.")
            return

        for contract_file in contract_files:
            contract_path = os.path.join(self.contract_dir, contract_file)
            contract_name = os.path.splitext(contract_file)[0]
            logger.info(f"Processing contract: {contract_file}")
            print(f"\nProcessing contract: {contract_file}")

            for test_num in range(1, 6):
                try:
                    num_focal_points = min(test_num - 1, len(self.interests))
                    focal_points = random.sample(self.interests, num_focal_points) if num_focal_points > 0 else None
                    test_results = self.test_contract_analysis(
                        contract_path=contract_path,
                        focal_points=focal_points,
                        test_num=test_num,
                        contract_name=contract_name
                    )
                    self.test_chat_interaction(
                        contract_path=contract_path,
                        focal_points=focal_points,
                        test_num=test_num,
                        contract_name=contract_name,
                        test_results=test_results
                    )
                    self.save_test_result(contract_name, test_num, test_results)
                except Exception as e:
                    logger.error(f"Test {test_num} for {contract_name} failed: {str(e)}")
                    traceback.print_exc()
                    print(f"Test {test_num} for {contract_name} failed: {str(e)}")
                    test_results = {
                        'contract_name': contract_name,
                        'test_number': test_num,
                        'focal_points': focal_points if focal_points else [],
                        'analysis': {},
                        'errors': [{'test_error': str(e)}]
                    }
                    self.save_test_result(contract_name, test_num, test_results)

def main():
    contract_dir = r"C:\Users\lucab\Desktop\LegalSafeAI\contracts\original"
    if not os.path.isdir(contract_dir):
        logger.error(f"Directory {contract_dir} does not exist.")
        print(f"Directory {contract_dir} does not exist.")
        return

    tester = AutomatedTester(contract_dir)
    tester.run_tests()

if __name__ == "__main__":
    main()