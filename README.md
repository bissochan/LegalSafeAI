# LegalSafeAI

An AI-powered legal document analysis tool with built-in student information search capabilities.

## Features

### Contract Analysis
- Automatic contract parsing and analysis
- Risk assessment and scoring
- Section-by-section evaluation
- Multi-language support (EN, ES, FR, IT, DE)
- Interactive Q&A with the contract
- Translation of analysis results

### Student Information Search
- University-specific information search
- Multiple search categories:
  - Working student regulations
  - Student housing
  - Research opportunities
  - Internships
  - Job offers
- Custom keyword search capability
- Relevance scoring
- Multi-language support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/LegalSafeAI.git
cd LegalSafeAI
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with:
```env
FLASK_SECRET_KEY=your_secret_key
OPENROUTER_API_KEY=your_openrouter_api_key
SERPAPI_KEY=your_serp_api_key
```

## Usage

1. Start the Flask application:
```bash
python run.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

### Contract Analysis
1. Click "Contract Analysis" mode
2. Upload a contract document (.pdf, .docx, .txt)
3. Click "Analyze Contract"
4. View the analysis results and scores
5. Use the chat feature to ask questions about the contract

### Student Information Search
1. Click "Student Search" mode
2. Enter university name
3. Select search category or use custom search
4. View relevant results with sources and relevance scores

## Requirements

```
python 3.8+
pydantic
python-dotenv
pymupdf
numpy
pillow
requests
pydantic-ai
flask
flask-session
werkzeug
apscheduler
gunicorn
python-docx
asyncio
fuzzywuzzy
python-Levenshtein
pdfplumber
```

## API Endpoints

### Contract Analysis
- `/api/document/extract` - Extract text from documents
- `/api/shadow/analyze` - Perform deep analysis
- `/api/summary/analyze` - Generate contract summary
- `/api/evaluator/evaluate` - Score contract sections
- `/api/translator/translate` - Translate results
- `/api/chat/start` - Start chat session
- `/api/chat/message` - Send chat message
- `/api/chat/end` - End chat session

### Student Search
- `/api/student/search` - Search university information
- `/api/web/focused-search` - Perform focused web search

## Configuration

The application can be configured through environment variables:
- `FLASK_SECRET_KEY` - Application secret key
- `OPENROUTER_API_KEY` - OpenRouter API key for AI analysis
- `SERPAPI_KEY` - SerpAPI key for web searches

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)
Project Link: [https://github.com/yourusername/LegalSafeAI](https://github.com/yourusername/LegalSafeAI)