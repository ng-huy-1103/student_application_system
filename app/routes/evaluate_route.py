from flask import Blueprint, request, jsonify, session, flash
from venv import logger
from database.db import db
from models.application import Application, ApplicationStatus
from models.document import Document, ProcessingStatus
from models.studentinfo import StudentInfo
from models.summary import Summary
from models.user import User
from models.evaluation import Evaluation
import requests

evaluate_bp = Blueprint('evaluate', __name__)

@evaluate_bp.route('/applications/<int:application_id>/evaluations', methods=['POST'])
def create_evaluation(application_id):
    """API endpoint to save evaluation of an application."""
    data = request.get_json()
    evaluator_id = data.get('evaluator_id')
    evaluation_score = data.get('evaluation_score')
    evaluation_comments = data.get('evaluation_comments')
    evaluation_status = data.get('evaluation_status')
    
    try:
        new_eval = Evaluation(
            application_id=application_id,
            evaluator_id=evaluator_id,
            evaluation_score=evaluation_score,
            evaluation_comments=evaluation_comments,
            evaluation_status=evaluation_status
        )
        db.session.add(new_eval)
        db.session.commit()
        return jsonify({"message": "Evaluation created", "evaluation": new_eval.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()

@evaluate_bp.route('/applications/<int:application_id>/evaluations', methods=['GET'])
def get_evaluations_by_app(application_id):
    """API endpoint to get evaluation of an application."""
    try:
        evaluations = Evaluation.query.filter_by(application_id=application_id).all()
        result = [eval.to_dict() for eval in evaluations]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()

@evaluate_bp.route('/users/<int:user_id>/evaluations', methods=['GET'])
def get_evaluation_history(user_id):
    """
    API endpoint to get evaluations of an user
    """
    try:
        evaluations = Evaluation.query.filter_by(evaluator_id=user_id)\
                                        .order_by(Evaluation.evaluation_date.desc()).all()
        result = [evaluation.to_dict() for evaluation in evaluations]
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.close()





