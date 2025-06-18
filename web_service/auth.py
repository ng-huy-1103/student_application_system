"""
Authentication utilities for the web service.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request, g
from database.db import get_session
from database.models import User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        db_session = get_session()
        try:
            user = db_session.query(User).filter(User.id == session['user_id']).first()
            if not user or not user.is_admin():
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
        finally:
            db_session.close()
            
        return f(*args, **kwargs)
    return decorated_function

def reviewer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        db_session = get_session()
        try:
            user = db_session.query(User).filter(User.id == session['user_id']).first()
            if not user or not user.is_reviewer():
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
        finally:
            db_session.close()
            
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' not in session:
        return None
    
    db_session = get_session()
    try:
        return db_session.query(User).filter(User.id == session['user_id']).first()
    finally:
        db_session.close()
