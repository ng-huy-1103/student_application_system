from flask import Blueprint, request, jsonify, g
import logging
from web_service.services import (
    get_application_data, get_applications_list,
    get_user_data, get_users_list, get_evaluation_history,
    create_evaluation, update_application_status
)

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/applications', methods=['GET'])
def api_get_applications():
    """Get list of applications with optional filtering."""
    try:
        data = get_applications_list()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_applications: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/application/<int:application_id>', methods=['GET'])
def api_get_application(application_id):
    """Get detailed application data."""
    try:
        data = get_application_data(application_id)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Application not found'
            }), 404
            
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_application: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/application/<int:application_id>/review', methods=['POST'])
def api_create_review(application_id):
    if not request.is_json:
        return jsonify(success=False, error="Content-Type must be application/json"), 415

    data = request.get_json()
    decision = data.get('decision')
    comments = data.get('comments')
    score = data.get('score')
    reviewer_id = data.get('reviewer_id')

    if not decision:
        return jsonify(success=False, error="Decision is required"), 400
    if decision not in ['approved', 'rejected', 'invited']:
        return jsonify(success=False,
                       error="Invalid decision. Must be one of: approved, rejected, invited"), 400

    if score is not None:
        try:
            score = int(score)
            if score < 0 or score > 100:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify(success=False, error="Score must be between 0 and 100"), 400

    if not reviewer_id:
        reviewer = getattr(g, 'user', None)
        if isinstance(reviewer, dict):
            reviewer_id = reviewer.get('id')
    try:
        reviewer_id = int(reviewer_id)
    except (TypeError, ValueError):
        return jsonify(success=False, error="Invalid reviewer_id"), 400

    result = create_evaluation(application_id, reviewer_id, decision, comments, score)
    if result:
        return jsonify(success=True, data=result), 201
    else:
        logger.error(f"Failed to create evaluation for application {application_id}")
        return jsonify(success=False, error="Failed to create evaluation"), 500
    
@api_bp.route('/application/<int:application_id>/history', methods=['GET'])
def api_get_evaluation_history(application_id):
    try:
        data = get_evaluation_history(application_id)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_evaluation_history: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/application/<int:application_id>/status', methods=['PUT'])
def api_update_application_status(application_id):
    try:
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
            
        status = data['status']
        
        valid_statuses = ['submitted', 'processing', 'evaluated', 'rejected', 'approved', 'invited_to_interview']
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {valid_statuses}'
            }), 400
        
        success = update_application_status(application_id, status)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to update application status'
            }), 500
            
        return jsonify({
            'success': True,
            'message': 'Application status updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in api_update_application_status: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@api_bp.route('/users', methods=['GET'])
def api_get_users():
    """Get list of users (admin only)."""
    try:
        data = get_users_list()
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_users: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@api_bp.route('/user/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """Get user data by ID."""
    try:
        data = get_user_data(user_id)
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
            
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error in api_get_user: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
@api_bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API routes."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@api_bp.errorhandler(405)
def api_method_not_allowed(error):
    """Handle 405 errors for API routes."""
    return jsonify({
        'success': False,
        'error': 'Method not allowed'
    }), 405

@api_bp.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors for API routes."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

