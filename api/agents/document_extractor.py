import os
import base64
import logging
from typing import Optional
import fitz  # PyMuPDF
import requests
from PIL import Image
from docx import Document
import io
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class DocumentExtractor:
    """Universal document text extractor supporting multiple formats"""
    
    SUPPORTED_FORMATS = {
        'pdf': ['.pdf'],
        'document': ['.doc', '.docx', '.rtf'],
        'text': ['.txt', '.md'],
        'image': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    }

    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.logger = logging.getLogger(__name__)

    def _encode_file_to_base64(self, filepath: str) -> str:
        """Convert any file to base64 string"""
        with open(filepath, "rb") as file:
            return base64.b64encode(file.read()).decode('utf-8')

    def _get_file_type(self, filepath: str) -> str:
        """Determine file type from extension"""
        ext = Path(filepath).suffix.lower()
        for file_type, extensions in self.SUPPORTED_FORMATS.items():
            if ext in extensions:
                return file_type
        raise ValueError(f"Unsupported file format: {ext}")

    def _extract_from_openrouter(self, base64_content: str, file_type: str, lang: str = 'en') -> str:
        """Extract text using OpenRouter's AI model"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://legalsafeai.com",
            "Content-Type": "application/json"
        }

        # Create a prompt based on file type and language
        prompts = {
            'pdf': "Extract all text from this PDF document",
            'document': "Extract all text from this document",
            'text': "Process and format this text",
            'image': "Extract all visible text from this image"
        }
        base_prompt = prompts.get(file_type, "Extract all text from this file")
        
        data = {
            "model": "anthropic/claude-3-opus-20240229",
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a specialized text extraction assistant. Extract text accurately from {file_type} files while preserving formatting and structure."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{base_prompt} in {lang}"
                        },
                        {
                            "type": "file",
                            "format": "base64",
                            "media_type": f"application/{file_type}",
                            "data": base64_content
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            self.logger.error(f"OpenRouter API error: {str(e)}")
            return None

    def _fallback_extraction(self, filepath: str, file_type: str) -> str:
        """Fallback extraction methods for different file types"""
        try:
            if file_type == 'pdf':
                return self._extract_pdf_fallback(filepath)
            elif file_type == 'document':
                return self._extract_document_fallback(filepath)
            elif file_type == 'text':
                return self._extract_text_fallback(filepath)
            elif file_type == 'image':
                return self._extract_image_fallback(filepath)
        except Exception as e:
            self.logger.error(f"Fallback extraction error: {str(e)}")
            raise

    def _extract_pdf_fallback(self, filepath: str) -> str:
        """Extract text from PDF using PyMuPDF"""
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def _extract_document_fallback(self, filepath: str) -> str:
        """Extract text from Word documents"""
        doc = Document(filepath)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    def _extract_text_fallback(self, filepath: str) -> str:
        """Extract text from text files"""
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()

    def _extract_image_fallback(self, filepath: str) -> str:
        """Extract text from images using Tesseract"""
        try:
            import pytesseract
            image = Image.open(filepath)
            return pytesseract.image_to_string(image)
        except ImportError:
            self.logger.error("Tesseract not installed for image fallback")
            return ""

    def extract_text(self, filepath: str, lang: str = 'en') -> str:
        """Main method to extract text from any supported file"""
        try:
            file_type = self._get_file_type(filepath)
            
            # Try AI extraction first
            base64_content = self._encode_file_to_base64(filepath)
            ai_text = self._extract_from_openrouter(base64_content, file_type, lang)
            
            if ai_text and len(ai_text.strip()) > 100:
                return ai_text
            
            # Fallback to traditional methods if AI extraction fails
            self.logger.info("Using fallback extraction method")
            return self._fallback_extraction(filepath, file_type)
            
        except Exception as e:
            self.logger.error(f"Text extraction error: {str(e)}")
            raise

def main():
    logging.basicConfig(level=logging.INFO)
    extractor = DocumentExtractor()
    file_path = "esempio_contratto_3.pdf"  # Replace with your file path
    language = 'en'  # Set the language for text extraction (ISO 639-1 code)

    extracted_text = extractor.extract_text(file_path, lang=language)

    if extracted_text:
        print("\nExtracted text:")
        print(extracted_text)
    else:
        print("No text extracted from the file.")

if __name__ == "__main__":
    main()