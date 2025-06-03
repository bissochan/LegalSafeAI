# LegalSafeAI - Contract Analyzer

**LegalSafeAI** is an AI-powered web application designed to analyze legal contracts, providing detailed insights, scores, and recommendations. With a modern, user-friendly interface, it supports multiple languages, interactive chat for contract queries, and a comprehensive analysis of contract sections. Built with Flask, JavaScript, and a sleek CSS design, LegalSafeAI is ideal for legal professionals and individuals seeking to understand contract terms.

## Features

- **Contract Upload & Analysis**: Upload contracts in PDF, DOCX, or TXT format for automated analysis, including section scores, summary, detailed analysis, and evaluation.
- **Multilingual Support**: Switch between English, Spanish, French, Italian, and German with real-time translation of UI and analysis results.
- **Interactive Chat**: Ask questions about the contract with formatted responses (e.g., bold text, lists) powered by an AI chatbot.
- **Modern UI**: Features a responsive sidebar, tabbed analysis results, collapsible chat panel, and enhanced score cards with hover effects.
- **Accessible Design**: Includes ARIA attributes and keyboard navigation for improved accessibility.
- **Chat History**: View past questions and answers for reference.
- **Frequent Questions**: Quick access to commonly asked contract-related questions.

## Screenshots

![Main Interface](screenshots/main_interface.png)  
![Chat Panel](screenshots/chat_panel.png)  
![Analysis Tabs](screenshots/analysis_tabs.png)  

*Note: Replace placeholders with actual screenshots.*

## Prerequisites

- Python 3.8+
- Node.js (optional, for frontend development)
- A modern web browser (Chrome, Firefox, Safari, Edge)
- Dependencies listed in `requirements.txt`

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/legalsafeai.git
   cd legalsafeai

    Set Up a Virtual Environment
    bash

python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

Install Dependencies
bash

pip install -r requirements.txt

Run the Application
bash

    python app.py

    Access the Application
    Open your browser and navigate to http://localhost:5000

Usage

    Upload a contract file (PDF, DOCX, or TXT)

    View the automated analysis in the dashboard

    Interact with the AI chatbot for specific contract questions

    Switch languages using the language selector

    Explore analysis tabs for detailed insights

Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements.
License

MIT License
Contact

For questions or support, contact: your.email@example.com