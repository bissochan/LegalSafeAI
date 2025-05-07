# LegalSafeAI

LegalSafeAI is a comprehensive contract analysis tool that leverages AI to provide detailed assessments of employment contracts. It combines multiple analysis approaches to identify potential issues, evaluate contract terms, and provide actionable recommendations.

## Features

- **Shadow Analysis**: Identifies ambiguous areas, potential risks, and unfavorable clauses
- **Detailed Contract Analysis**: Evaluates 17 key contract aspects including:
  - Sick leave, vacation, and overtime policies
  - Termination clauses
  - Confidentiality and non-compete agreements
  - Intellectual property rights
  - Benefits and compensation
  - Work hours and responsibilities
- **Multi-Model Evaluation**: Uses multiple AI models to validate analysis accuracy
- **PDF Processing**: Handles both native PDFs and scanned documents
- **Web Interface**: User-friendly interface for contract uploads and analysis
- **Structured Output**: Generates detailed JSON reports with scores and recommendations

## Documentation

For detailed information about the project, please refer to:
- [Architecture Documentation](https://docs.google.com/document/d/16NRgPNfQAgirhzmx4Sdm4cbQvAZzv7McQdEldCN5jtY/edit?usp=sharing)
- [Requirements Documentation](https://docs.google.com/document/d/1yWA7sgaBD_8a07xRo1Rd_r1ITXn7VDPXf0ucCEgiOy4/edit?usp=sharing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/LegalSafeAI.git
cd LegalSafeAI
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with:
```
OPENROUTER_API_KEY=your_api_key_here
```

4. Install Tesseract OCR (for scanned document support):
- Windows: Download and install from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- Linux: `sudo apt-get install tesseract-ocr`
- Mac: `brew install tesseract`

## Usage

### Command Line Interface
```bash
python main.py
```

### Web Interface
```bash
python legalApp.py
```
Then open `http://localhost:5000` in your browser.

## API Components

- **ShadowAgent**: Identifies potential risks and ambiguities
- **ContractAnalyzerAgent**: Performs detailed contract analysis
- **ResponseEvaluator**: Validates analysis accuracy
- **PdfExtractor**: Handles PDF text extraction

## Output Format

The analysis generates a structured JSON output including:
- Metadata (timestamp, contract name, overall score)
- Structured analysis of 17 contract aspects
- Executive summary
- Key points
- Potential issues
- Recommendations
- Evaluation scores from multiple models

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenRouter API for AI model access
- Tesseract OCR for document processing
- PyMuPDF for PDF handling