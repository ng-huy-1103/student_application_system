"""
LLM Service main application.
"""
from flask import Flask, request, jsonify
import os
import sys
import uuid
import json
import logging
from datetime import datetime

# Add parent directory to path to import database modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_service.config import LLM_SERVICE_HOST, LLM_SERVICE_PORT
from llm_service.utils.llm_processor import LLMProcessor
from database.db import get_session
from database.models import Application, StudentInfo, Summary, ApplicationStatus

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("llm_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy", 
        "service": "llm_service",
        "model": "LLaMA2-7B (Ollama)"
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_documents():
    """Analyze documents and extract student information."""
    try:
        data = request.json
        
        # Log dữ liệu nhận được để debug
        logger.debug(f"Received data: {json.dumps(data, indent=2)}")
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        application_id = data.get('application_id')
        documents = data.get('documents', [])
        
        if not application_id or not documents:
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Phân loại tài liệu theo loại
        categorized_docs = {}
        for doc in documents:
            doc_type = doc.get('document_type', 'unknown')
            content = doc.get('content_text', '')
            language = doc.get('language', 'en')  
            
            if doc_type not in categorized_docs:
                categorized_docs[doc_type] = []
            
            categorized_docs[doc_type].append({
                'content': content,
                'language': language,
                'document_id': doc.get('document_id')
            })
        
        # Xử lý với LLM processor
        llm_processor = LLMProcessor()
        result = llm_processor.process_application(application_id, categorized_docs)
        
        # Cập nhật database
        session = get_session()
        try:
            # Cập nhật trạng thái application
            application = session.query(Application).filter(Application.id == application_id).first()
            
            if not application:
                return jsonify({"error": f"Application not found with ID: {application_id}"}), 404
            
            application.status = ApplicationStatus.EVALUATED.value
            application.evaluation_score = result.get('evaluation', {}).get('score', 0)
            application.evaluation_date = datetime.utcnow()
            
            # Kiểm tra xem đã có StudentInfo chưa
            student_info = session.query(StudentInfo).filter(StudentInfo.application_id == application_id).first()
            
            if student_info:
                # Cập nhật thông tin sinh viên hiện có
                student_info.name = result.get('student_info', {}).get('name', '')
                student_info.gender = result.get('student_info', {}).get('gender', '')
                student_info.date_of_birth = result.get('student_info', {}).get('date_of_birth', '')
                student_info.age = result.get('student_info', {}).get('age', 0)
                student_info.nationality = result.get('student_info', {}).get('nationality', '')
                student_info.previous_university = result.get('student_info', {}).get('previous_university', '')
                student_info.gpa = result.get('student_info', {}).get('gpa', 0.0)
                student_info.russian_language_level = result.get('student_info', {}).get('russian_language_level', '')
            else:
                # Tạo mới thông tin sinh viên
                student_info = StudentInfo(
                    application_id=application_id,
                    name=result.get('student_info', {}).get('name', ''),
                    gender=result.get('student_info', {}).get('gender', ''),
                    date_of_birth=result.get('student_info', {}).get('date_of_birth', ''),
                    age=result.get('student_info', {}).get('age', 0),
                    nationality=result.get('student_info', {}).get('nationality', ''),
                    previous_university=result.get('student_info', {}).get('previous_university', ''),
                    gpa=result.get('student_info', {}).get('gpa', 0.0),
                    russian_language_level=result.get('student_info', {}).get('russian_language_level', '')
                )
                session.add(student_info)
            
            # Kiểm tra xem đã có Summary chưa
            summary = session.query(Summary).filter(Summary.application_id == application_id).first()
            
            if summary:
                # Cập nhật tóm tắt hiện có
                summary.cv_summary = result.get('summaries', {}).get('cv_summary', '')
                summary.motivation_letter_summary = result.get('summaries', {}).get('motivation_letter_summary', '')
                summary.recommendation_letter_summary = result.get('summaries', {}).get('recommendation_letter_summary', '')
                summary.recommendation_author = result.get('summaries', {}).get('recommendation_author', '')
                summary.achievements_summary = result.get('summaries', {}).get('achievements_summary', '')
                summary.additional_documents_summary = result.get('summaries', {}).get('additional_documents_summary', '')
                summary.evaluation_comments = result.get('evaluation', {}).get('comments', '')
            else:
                # Tạo mới tóm tắt
                summary = Summary(
                    application_id=application_id,
                    cv_summary=result.get('summaries', {}).get('cv_summary', ''),
                    motivation_letter_summary=result.get('summaries', {}).get('motivation_letter_summary', ''),
                    recommendation_letter_summary=result.get('summaries', {}).get('recommendation_letter_summary', ''),
                    recommendation_author=result.get('summaries', {}).get('recommendation_author', ''),
                    achievements_summary=result.get('summaries', {}).get('achievements_summary', ''),
                    additional_documents_summary=result.get('summaries', {}).get('additional_documents_summary', ''),
                    evaluation_comments=result.get('evaluation', {}).get('comments', '')
                )
                session.add(summary)
            
            session.commit()
            
            return jsonify({
                "task_id": task_id,
                "status": "completed",
                "application_id": application_id
            })
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Error analyzing documents: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a processing task."""
    return jsonify({
        "task_id": task_id,
        "status": "completed"
    })

if __name__ == '__main__':
    app.run(host=LLM_SERVICE_HOST, port=LLM_SERVICE_PORT, debug=True)
