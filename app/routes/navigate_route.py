from flask import Blueprint, request, jsonify, session, flash
from venv import logger
from database.db import db
from models.application import Application, ApplicationStatus
from models.document import Document, ProcessingStatus
from models.studentinfo import StudentInfo
from models.summary import Summary
from models.user import User
import requests

LLM_SERVICE_URL = "http://localhost:5002"

navigate_bp = Blueprint('navigate', __name__)

@navigate_bp.route('/documents', methods=['GET'])
def get_documents():
    """API endpoint to get documents for an application."""
    application_id = request.args.get('application_id')
    
    if not application_id:
        return jsonify({"error": "Application ID is required"}), 400
    
    try:
        documents = db.session.query(Document).filter(Document.application_id == application_id).all()
        
        result = []
        for doc in documents:
            result.append({
                "id": doc.id,
                "file_name": doc.file_name,
                "file_type": doc.file_type,
                "document_type": doc.document_type,
                "processing_status": doc.processing_status
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        db.session.close()

@navigate_bp.route('/applications', methods=['GET'])
def get_applications():
    """API endpoint to get all applications."""
    session = db.session
    try:
        applications = session.query(Application).order_by(Application.submission_date.desc()).all()
        
        result = []
        for app in applications:
            result.append({
                "id": app.id,
                "submission_date": app.submission_date.isoformat(),
                "status": app.status,
                "evaluation_score": app.evaluation_score,
                "evaluation_date": app.evaluation_date
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        session.close()

@navigate_bp.route('/application/<int:application_id>')
def application(application_id):
    """Display application details and status."""
    session = db.session
    try:
        # Get application
        application = session.query(Application).filter(Application.id == application_id).first()
        
        if not application:
            flash('Application not found', 'error')
            return jsonify({"error": "Application not found"}), 400
        
        # Get documents
        documents = session.query(Document).filter(Document.application_id == application_id).all()
        print(doc for doc in documents)
        # Get student info and summaries if available
        student_info = session.query(StudentInfo).filter(StudentInfo.application_id == application_id).first()
        summary = session.query(Summary).filter(Summary.application_id == application_id).first()
        
        # Check if all documents are processed
        all_processed = all(doc.processing_status == ProcessingStatus.COMPLETED.value for doc in documents)
        print(application_id)
        # If all documents are processed and application is still in SUBMITTED status, send to LLM Service
        if all_processed and application.status == ApplicationStatus.SUBMITTED.value and documents:
    # Prepare documents for LLM Service
            docs_for_llm = []
            for doc in documents:
                docs_for_llm.append({
                    "document_id": doc.id,
                    "document_type": doc.document_type,
                    "content_text": doc.content_text
                })
            
            # Send to LLM Service for analysis
            try:
                llm_response = requests.post(
                    f"{LLM_SERVICE_URL}/api/analyze",
                    json={
                        "application_id": application_id,
                        "documents": docs_for_llm
                    },
                    timeout=60  # Tăng timeout lên 60 giây
                )
                
                if llm_response.status_code != 200:
                    logger.error(f"LLM Service error: {llm_response.status_code} - {llm_response.text}")
                    flash(f'Error analyzing application: {llm_response.json().get("error", "Unknown error")}', 'error')
                else:
                    logger.info(f"LLM Service response: {llm_response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                logger.error(f"Cannot connect to LLM Service at {LLM_SERVICE_URL}")
                flash('Cannot connect to LLM Service. Please check if the service is running.', 'error')
            except requests.exceptions.Timeout:
                logger.error(f"Timeout connecting to LLM Service at {LLM_SERVICE_URL}")
                flash('LLM Service request timed out. The model might be processing a large document.', 'error')
            except Exception as e:
                logger.error(f"Error communicating with LLM Service: {str(e)}")
                flash(f'Error communicating with LLM Service: {str(e)}', 'error')
        # Refresh data after LLM processing
        application = session.query(Application).filter(Application.id == application_id).first()
        student_info = session.query(StudentInfo).filter(StudentInfo.application_id == application_id).first()
        summary = session.query(Summary).filter(Summary.application_id == application_id).first()
        
        result = {
            "application": application.to_dict() if application else None,
            "student_info": student_info.to_dict() if student_info else None,
            "summary": summary.to_dict() if summary else None,
        }
        return jsonify(result), 200
    
    except Exception as e:
        flash(f'Error retrieving application: {str(e)}', 'error')
        return jsonify({"error": str(e)}), 500
    
    finally:
        session.close()

