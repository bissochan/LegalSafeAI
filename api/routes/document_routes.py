from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from agents.document_extractor import DocumentExtractor
import os
import logging
from pathlib import Path

document_bp = Blueprint('document', __name__)
document_extractor = DocumentExtractor()
logger = logging.getLogger(__name__)

@document_bp.route('/extract', methods=['POST'])
def extract_text():
    """Extract text from uploaded document"""
    try:
        # Debug logging
        logger.debug(f"Request files: {request.files}")
        logger.debug(f"Request form: {request.form}")
        
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400

        if not file or not file.filename:
            logger.error("Invalid file")
            return jsonify({'error': 'Invalid file'}), 400

        # Create temp directory if it doesn't exist
        temp_dir = Path(current_app.instance_path) / 'uploads'
        temp_dir.mkdir(parents=True, exist_ok=True)

        filename = secure_filename(file.filename)
        temp_path = temp_dir / filename

        try:
            # Save uploaded file
            file.save(str(temp_path))
            logger.debug(f"File saved to {temp_path}")

            # Extract text
            language = request.form.get('language', 'en')
            extracted_text = document_extractor.extract_text(str(temp_path), lang=language)

            if not extracted_text:
                raise ValueError("No text could be extracted from the document")

            return jsonify({
                'status': 'success',
                'text': extracted_text
            })

        except Exception as e:
            logger.error(f"Extraction error: {str(e)}")
            return jsonify({'error': f'Text extraction failed: {str(e)}'}), 500

        finally:
            # Clean up the temporary file
            if temp_path.exists():
                temp_path.unlink()
                logger.debug(f"Cleaned up temporary file {temp_path}")

    except Exception as e:
        logger.error(f"Request handling error: {str(e)}")
        return jsonify({'error': str(e)}), 400