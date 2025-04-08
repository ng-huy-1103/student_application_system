from flask import Blueprint, request, jsonify, session, flash
from database.db import db
import bcrypt
from models.application import Application

navigate_bp = Blueprint('navigate', __name__)

@navigate_bp.route('/history', methods = ['GET'])
def history():
    """Display application history."""
    try:
        # Get all applications
        applications = db.session.query(Application).order_by(Application.submission_date.desc()).all()
        result = []
        for app in applications:
            result.append({
                "id": app.id,
                "submission_date": app.submission_date,
                "evaluation_date": app.evaluation_date,
                "evaluation_score": app.evaluation_score,
                "status": app.status
            })
        return jsonify(result), 200
    
    except Exception as e:
        flash(f'Error retrieving history: {str(e)}', 'error')
        return jsonify({f'error': {str(e)}}), 500    
    finally:
        db.session.close()

