"""
OCR Service main application.
"""
from flask import Flask, request, jsonify
import os
import sys
import uuid
from werkzeug.utils import secure_filename
# Thêm thư mục cha vào đường dẫn để nhập các mô-đun cơ sở dữ liệu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ocr_service.config import OCR_SERVICE_HOST, OCR_SERVICE_PORT, UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from ocr_service.utils.ocr_processor import OCRProcessor
from database.db import get_session, init_db
from database.models import Document, ProcessingStatus, DocumentType

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB


os.makedirs(UPLOAD_FOLDER, exist_ok=True)


ocr_processor = OCRProcessor()

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "ocr_service"})

@app.route('/api/process', methods=['POST'])
def process_document():
    """
    Process a document using OCR.
    
    Expected JSON payload:
    {
        "document_id": "integer",
        "file_path": "string",
        "document_type": "string"  
    }
    """

    data = request.json
    
    if not data or 'document_id' not in data or 'file_path' not in data or 'document_type' not in data:
        return jsonify({"error": "Invalid request data"}), 400
    
    document_id = data['document_id']
    file_path = data['file_path']
    document_type = data['document_type']  
    
  
    if not os.path.exists(file_path):
        return jsonify({"error": f"File not found: {file_path}"}), 404
    
   
    task_id = str(uuid.uuid4())
    
    session = get_session()
    try:
        document = session.query(Document).filter(Document.id == document_id).first()
        if document:
            document.processing_status = ProcessingStatus.PROCESSING.value
            document.document_type = document_type 
            session.commit()
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        session.close()
    
    try:

        extracted_text = ocr_processor.process_document(file_path)
        

        language = ocr_processor.detect_language(extracted_text)
        

        processed_file_path = f"{os.path.splitext(file_path)[0]}_processed.txt"
        with open(processed_file_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        session = get_session()
        try:
            document = session.query(Document).filter(Document.id == document_id).first()
            if document:
                document.content_text = extracted_text
                document.processing_status = ProcessingStatus.COMPLETED.value
                session.commit()
        except Exception as e:
            session.rollback()
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        finally:
            session.close()
        
        return jsonify({
            "task_id": task_id,
            "status": "completed",
            "document_id": document_id,
            "document_type": document_type,
            "language": language
        })
    
    except Exception as e:
        session = get_session()
        try:
            document = session.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = ProcessingStatus.FAILED.value
                session.commit()
        except Exception as db_e:
            session.rollback()
        finally:
            session.close()
        
        return jsonify({
            "task_id": task_id,
            "status": "failed",
            "document_id": document_id,
            "error": str(e)
        }), 500

@app.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a processing task."""

    return jsonify({
        "task_id": task_id,
        "status": "completed"
    })

if __name__ == '__main__':
    init_db()
    app.run(host=OCR_SERVICE_HOST, port=OCR_SERVICE_PORT, debug=True)
