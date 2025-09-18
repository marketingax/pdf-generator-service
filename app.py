# === app.py ===
# Created: September 18, 2025 - 12:00 PM
# Purpose: Flask web application for generating and compressing PDFs via webhook
# Key Exports:
#   - Flask app with /webhook endpoint for PDF generation
#   - /download/<filename> endpoint for PDF retrieval
#   - /health endpoint for Railway monitoring
# Interactions:
#   - Used by: Railway deployment, webhook triggers
# Notes:
#   - Includes automatic file cleanup after 24 hours
#   - Integrates PDF compression to reduce file sizes

import os
import json
import uuid
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, send_file, url_for
from flask_cors import CORS
from werkzeug.exceptions import BadRequest, NotFound

from pdf_generator import create_pdf
from pdf_compressor import compress_pdf_file
from file_manager import setup_directories, cleanup_old_files, schedule_cleanup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    """Application configuration settings"""
    
    # File storage settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'generated_pdfs')
    MAX_FILE_AGE_HOURS = int(os.environ.get('MAX_FILE_AGE_HOURS', '24'))
    
    # Server settings
    PORT = int(os.environ.get('PORT', '8080'))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # Security settings
    API_KEY = os.environ.get('API_KEY', None)  # Optional API key authentication
    
    # PDF settings
    COMPRESSION_ENABLED = os.environ.get('COMPRESSION_ENABLED', 'true').lower() == 'true'
    COMPRESSION_LEVEL = int(os.environ.get('COMPRESSION_LEVEL', '3'))

app.config.from_object(Config)

def validate_api_key():
    """Validate API key if configured"""
    if not Config.API_KEY:
        return True  # No API key required
    
    provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    return provided_key == Config.API_KEY

def validate_webhook_payload(data):
    """
    Validate incoming webhook payload
    
    Expected format:
    {
        "title": "Your Flyer Title",
        "canva_link": "https://canva.com/design/...",
        "etsy_design_link": "https://www.etsy.com/listing/...", // optional
        "logo_url": "https://example.com/logo.jpg", // optional
        "flyer_image_url": "https://example.com/flyer.jpg" // optional
    }
    """
    required_fields = ['title', 'canva_link']
    
    if not isinstance(data, dict):
        raise BadRequest("Payload must be a JSON object")
    
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        raise BadRequest(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate URLs
    canva_link = data['canva_link']
    if not (canva_link.startswith('http://') or canva_link.startswith('https://')):
        raise BadRequest("canva_link must be a valid URL")
    
    # Validate optional image URLs
    for field in ['etsy_design_link', 'logo_url', 'flyer_image_url']:
        if field in data and data[field]:
            if not (data[field].startswith('http://') or data[field].startswith('https://')):
                raise BadRequest(f"{field} must be a valid URL")
    
    # Use default Etsy link if not provided
    if 'etsy_design_link' not in data or not data['etsy_design_link']:
        data['etsy_design_link'] = "https://www.etsy.com/listing/1827167654/custom-flyer-design-party-flyer-canva"
    
    return data

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway monitoring"""
    try:
        # Check if upload directory exists and is writable
        upload_dir = Path(Config.UPLOAD_FOLDER)
        upload_dir.mkdir(exist_ok=True)
        
        # Test file creation
        test_file = upload_dir / 'health_check.txt'
        test_file.write_text('test')
        test_file.unlink()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'upload_directory': str(upload_dir.absolute()),
            'compression_enabled': Config.COMPRESSION_ENABLED
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Main webhook endpoint for PDF generation
    
    Accepts JSON payload with title, canva_link, and optional etsy_design_link
    Returns JSON with download URL and file information
    """
    try:
        # Validate API key if configured
        if not validate_api_key():
            logger.warning("Unauthorized webhook request")
            return jsonify({'error': 'Invalid or missing API key'}), 401
        
        # Parse and validate request data
        if not request.is_json:
            raise BadRequest("Content-Type must be application/json")
        
        data = validate_webhook_payload(request.get_json())
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.pdf"
        filepath = Path(Config.UPLOAD_FOLDER) / filename
        
        logger.info(f"Generating PDF for title: {data['title']}")
        
        # Create the PDF
        create_pdf(
            output_path=str(filepath),
            title=data['title'],
            canva_link=data['canva_link'],
            etsy_design_link=data['etsy_design_link'],
            logo_url=data.get('logo_url'),
            flyer_image_url=data.get('flyer_image_url')
        )
        
        # Compress the PDF if enabled
        if Config.COMPRESSION_ENABLED:
            logger.info(f"Compressing PDF: {filename}")
            compressed_path = compress_pdf_file(
                input_file=str(filepath),
                compression_level=Config.COMPRESSION_LEVEL
            )
            
            # If compression created a new file, replace the original
            if compressed_path != str(filepath):
                filepath.unlink()  # Remove original
                Path(compressed_path).rename(filepath)  # Rename compressed to original name
        
        # Get file information
        file_size = filepath.stat().st_size
        
        # Generate download URL (ensure HTTPS)
        download_url = url_for('download_file', filename=filename, _external=True)
        if download_url.startswith('http://'):
            download_url = download_url.replace('http://', 'https://', 1)
        
        logger.info(f"PDF generated successfully: {filename} ({file_size} bytes)")
        
        return jsonify({
            'success': True,
            'message': 'PDF generated successfully',
            'file_id': file_id,
            'filename': filename,
            'download_url': download_url,
            'file_size': file_size,
            'compressed': Config.COMPRESSION_ENABLED,
            'expires_at': (datetime.utcnow() + timedelta(hours=Config.MAX_FILE_AGE_HOURS)).isoformat(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except BadRequest as e:
        logger.warning(f"Bad request: {e.description}")
        return jsonify({'error': e.description}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred while generating the PDF'
        }), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    Download endpoint for generated PDFs
    
    Serves PDF files with proper headers and handles missing files gracefully
    """
    try:
        # Validate filename format (UUID.pdf)
        if not filename.endswith('.pdf') or len(filename) != 40:  # 36 chars UUID + 4 chars ".pdf"
            raise NotFound("Invalid filename format")
        
        filepath = Path(Config.UPLOAD_FOLDER) / filename
        
        if not filepath.exists():
            logger.warning(f"Requested file not found: {filename}")
            raise NotFound("File not found or has expired")
        
        logger.info(f"Serving file: {filename}")
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=f"template_{filename}",
            mimetype='application/pdf'
        )
        
    except NotFound as e:
        return jsonify({'error': str(e.description)}), 404
    
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        return jsonify({'error': 'Error serving file'}), 500

@app.route('/status/<file_id>', methods=['GET'])
def file_status(file_id):
    """
    Check the status of a generated file
    
    Returns file information if it exists, or 404 if not found/expired
    """
    try:
        filename = f"{file_id}.pdf"
        filepath = Path(Config.UPLOAD_FOLDER) / filename
        
        if not filepath.exists():
            return jsonify({'error': 'File not found or has expired'}), 404
        
        stat = filepath.stat()
        created_time = datetime.fromtimestamp(stat.st_ctime)
        expires_time = created_time + timedelta(hours=Config.MAX_FILE_AGE_HOURS)
        
        # Generate download URL (ensure HTTPS)
        download_url = url_for('download_file', filename=filename, _external=True)
        if download_url.startswith('http://'):
            download_url = download_url.replace('http://', 'https://', 1)
        
        return jsonify({
            'file_id': file_id,
            'filename': filename,
            'file_size': stat.st_size,
            'created_at': created_time.isoformat(),
            'expires_at': expires_time.isoformat(),
            'download_url': download_url,
            'status': 'available' if datetime.utcnow() < expires_time else 'expired'
        })
        
    except Exception as e:
        logger.error(f"Error checking file status {file_id}: {e}")
        return jsonify({'error': 'Error checking file status'}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

def initialize_app():
    """Initialize the application"""
    try:
        # Set up directories
        setup_directories(Config.UPLOAD_FOLDER)
        
        # Start cleanup scheduler
        schedule_cleanup(Config.UPLOAD_FOLDER, Config.MAX_FILE_AGE_HOURS)
        
        logger.info("Application initialized successfully")
        logger.info(f"Upload folder: {Config.UPLOAD_FOLDER}")
        logger.info(f"File cleanup interval: {Config.MAX_FILE_AGE_HOURS} hours")
        logger.info(f"Compression enabled: {Config.COMPRESSION_ENABLED}")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

if __name__ == '__main__':
    # Initialize the application
    initialize_app()
    
    # Run the Flask app
    logger.info(f"Starting server on {Config.HOST}:{Config.PORT}")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )

