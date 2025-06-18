import os
import sys
import logging
from datetime import datetime
from sqlalchemy import func, desc, and_

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_session
from database.models import (
    Application, Document, StudentInfo, Summary,
    DocumentType, ProcessingStatus, ApplicationStatus,
    User, UserRole, ReviewerEvaluation, ReviewerDecision
)

logger = logging.getLogger(__name__)

def get_application_data(application_id):
    """
    Get complete application data including student info, documents, summaries, and evaluations.
    
    Args:
        application_id (int): The application ID
        
    Returns:
        dict: Complete application data or None if not found
    """
    db_session = get_session()
    try:
        application = db_session.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            return None
        student_info = db_session.query(StudentInfo).filter(
            StudentInfo.application_id == application_id
        ).first()
        
        documents = db_session.query(Document).filter(
            Document.application_id == application_id
        ).all()
        
        summary = db_session.query(Summary).filter(
            Summary.application_id == application_id
        ).first()
        
        evaluations = db_session.query(ReviewerEvaluation, User).join(
            User, ReviewerEvaluation.reviewer_id == User.id
        ).filter(
            ReviewerEvaluation.application_id == application_id
        ).order_by(desc(ReviewerEvaluation.created_at)).all()
        
        uploaded_by = None
        if application.uploaded_by_id:
            uploaded_by = db_session.query(User).filter(
                User.id == application.uploaded_by_id
            ).first()
        
        result = {
            'application': {
                'id': application.id,
                'student_name': application.student_name,
                'submission_date': application.submission_date.isoformat() if application.submission_date else None,
                'status': application.status,
                'evaluation_score': application.evaluation_score,
                'evaluation_date': application.evaluation_date.isoformat() if application.evaluation_date else None,
                'uploaded_by': {
                    'id': uploaded_by.id,
                    'username': uploaded_by.username,
                    'full_name': f"{uploaded_by.first_name or ''} {uploaded_by.last_name or ''}".strip()
                } if uploaded_by else None
            },
            'student_info': {
                'id': student_info.id,
                'name': student_info.name,
                'gender': student_info.gender,
                'date_of_birth': student_info.date_of_birth,
                'age': student_info.age,
                'nationality': student_info.nationality,
                'previous_university': student_info.previous_university,
                'gpa': student_info.gpa,
                'russian_language_level': student_info.russian_language_level
            } if student_info else None,
            'documents': [
                {
                    'id': doc.id,
                    'file_name': doc.file_name,
                    'file_path': doc.file_path,
                    'file_type': doc.file_type,
                    'upload_date': doc.upload_date.isoformat() if doc.upload_date else None,
                    'document_type': doc.document_type,
                    'content_text': doc.content_text,
                    'processing_status': doc.processing_status
                } for doc in documents
            ],
            'summary': {
                'id': summary.id,
                'cv_summary': summary.cv_summary,
                'motivation_letter_summary': summary.motivation_letter_summary,
                'recommendation_letter_summary': summary.recommendation_letter_summary,
                'recommendation_author': summary.recommendation_author,
                'achievements_summary': summary.achievements_summary,
                'additional_documents_summary': summary.additional_documents_summary,
                'evaluation_comments': summary.evaluation_comments
            } if summary else None,
            'evaluations': [
                {
                    'id': eval_obj.id,
                    'decision': eval_obj.decision,
                    'comments': eval_obj.comments,
                    'score': eval_obj.score,
                    'created_at': eval_obj.created_at.isoformat() if eval_obj.created_at else None,
                    'reviewer': {
                        'id': user.id,
                        'username': user.username,
                        'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip()
                    }
                } for eval_obj, user in evaluations
            ]
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting application data for ID {application_id}: {e}")
        return None
    finally:
        db_session.close()

def get_applications_list(filters=None):
    db_session = get_session()
    try:
        query = db_session.query(Application, User).outerjoin(
            User, Application.uploaded_by_id == User.id
        )
        applications = query.order_by(desc(Application.submission_date))
        
        total = query.count()
        
        result = {
            'applications': [
                {
                    'id': app.id,
                    'student_name': app.student_name,
                    'submission_date': app.submission_date.isoformat() if app.submission_date else None,
                    'status': app.status,
                    'evaluation_score': app.evaluation_score,
                    'evaluation_date': app.evaluation_date.isoformat() if app.evaluation_date else None,
                    'uploaded_by': {
                        'id': user.id,
                        'username': user.username,
                        'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip()
                    } if user else None
                } for app, user in applications
            ]
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting applications list: {e}")
        return None
    finally:
        db_session.close()

def get_user_data(user_id):
    db_session = get_session()
    try:
        user = db_session.query(User).filter(User.id == user_id).first()
        
        if not user:
            return None
            
        result = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_active': user.is_active
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting user data for ID {user_id}: {e}")
        return None
    finally:
        db_session.close()

def get_users_list(filters=None):
    db_session = get_session()
    try:
        query = db_session.query(User)
        
        # Apply filters
        if filters:
            if filters.get('role'):
                query = query.filter(User.role == filters['role'])
            if filters.get('is_active') is not None:
                query = query.filter(User.is_active == filters['is_active'])
        
        # Order by username
        users = query.order_by(User.username).all()
        
        result = [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active
            } for user in users
        ]
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting users list: {e}")
        return []
    finally:
        db_session.close()

def get_evaluation_history(application_id):

    db_session = get_session()
    try:
        evaluations = db_session.query(ReviewerEvaluation, User).join(
            User, ReviewerEvaluation.reviewer_id == User.id
        ).filter(
            ReviewerEvaluation.application_id == application_id
        ).order_by(desc(ReviewerEvaluation.created_at)).all()
        
        result = [
            {
                'id': eval_obj.id,
                'decision': eval_obj.decision,
                'comments': eval_obj.comments,
                'score': eval_obj.score,
                'created_at': eval_obj.created_at.isoformat() if eval_obj.created_at else None,
                'reviewer': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip()
                }
            } for eval_obj, user in evaluations
        ]
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting evaluation history for application {application_id}: {e}")
        return []
    finally:
        db_session.close()

def create_evaluation(application_id, reviewer_id, decision, comments=None, score=None):
    db_session = get_session()
    try:
        # Check if application exists
        application = db_session.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            return None
            
        # Create evaluation
        evaluation = ReviewerEvaluation(
            application_id=application_id,
            reviewer_id=reviewer_id,
            decision=decision,
            comments=comments,
            score=score
        )
        
        db_session.add(evaluation)
        
        # Update application status and score if needed
        if decision == ReviewerDecision.APPROVED.value:
            application.status = ApplicationStatus.APPROVED.value
        elif decision == ReviewerDecision.REJECTED.value:
            application.status = ApplicationStatus.REJECTED.value
        elif decision == ReviewerDecision.INVITED.value:
            application.status = ApplicationStatus.INVITED_TO_INTERVIEW.value
        else:
            application.status = ApplicationStatus.EVALUATED.value
            
        if score is not None:
            application.evaluation_score = score
            
        application.evaluation_date = datetime.utcnow()
        
        db_session.commit()
        
        # Get reviewer info for response
        reviewer = db_session.query(User).filter(User.id == reviewer_id).first()
        
        result = {
            'id': evaluation.id,
            'application_id': application_id,
            'decision': decision,
            'comments': comments,
            'score': score,
            'created_at': evaluation.created_at.isoformat(),
            'reviewer': {
                'id': reviewer.id,
                'username': reviewer.username,
                'full_name': f"{reviewer.first_name or ''} {reviewer.last_name or ''}".strip()
            }
        }
        
        return result
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error creating evaluation: {e}")
        return None
    finally:
        db_session.close()

def update_application_status(application_id, status):
    db_session = get_session()
    try:
        application = db_session.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            return False
            
        application.status = status
        db_session.commit()
        
        return True
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error updating application status: {e}")
        return False
    finally:
        db_session.close()

