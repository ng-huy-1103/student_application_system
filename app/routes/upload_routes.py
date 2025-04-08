from flask import Blueprint, request, jsonify, flash
import os
import requests
import uuid
from werkzeug.utils import secure_filename
from database.db import db
from models.document import Document
from models.application import *
from models.document import *
import datetime

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt'}

OCR_SERVICE_URL = "http://localhost:5001"

os.makedirs("uploads", exist_ok=True)

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ALLOWED_DOCUMENT_TYPES = [
    'passport', 
    'academic_record', 
    'recommendation_letter', 
    'resume', 
    'motivation_letter', 
    'language_certificate', 
    'personal_achievements', 
    'additional_education_documents', 
    'education_level_certificate',
    'other'
]

@upload_bp.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and application submission."""
    # Check if files were uploaded
    if 'files[]' not in request.files:
        return jsonify({"error": 'No files selected'}), 400
    
    files = request.files.getlist('files[]')
    
    # Check if any file was selected
    if not files or files[0].filename == '':
        return jsonify({"error": 'No files selected'}), 400
    
    # Create new application
    try:
        new_application = Application(
            submission_date=datetime.datetime.now(),
            status=ApplicationStatus.SUBMITTED.value
        )
        db.session.add(new_application)
        db.session.commit()
        application_id = new_application.id
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating application: {str(e)}', 'error')
        return jsonify({'error': str(e)}), 500
    finally:
        db.session.close()
    
    # Create application directory
    application_dir = os.path.join('uploads', str(application_id))
    os.makedirs(application_dir, exist_ok=True)
    
    # Process each file
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(application_dir, filename)
            file.save(file_path)
            
            # Save document in database
            try:
                new_document = Document(
                    application_id=application_id,
                    file_name=filename,
                    file_path=file_path,
                    file_type=file.content_type,
                    upload_date=datetime.datetime.now(),
                    processing_status=ProcessingStatus.PENDING.value
                )
                db.session.add(new_document)
                db.session.commit()
                document_id = new_document.id
                
                # Send document to OCR Service for processing
                ocr_response = requests.post(
                    f"{OCR_SERVICE_URL}/api/process",
                    json={
                        "document_id": document_id,
                        "file_path": file_path,
                        "file_type": file.content_type
                    }
                )
                
                if ocr_response.status_code != 200:
                    flash(f'Error processing document: {ocr_response.json().get("error", "Unknown error")}', 'error')
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving document: {str(e)}', 'error')
                return jsonify({'error': str(e)}), 500
            finally:
                db.session.close()
    
    return jsonify({"application_id": application_id}), 200










    
