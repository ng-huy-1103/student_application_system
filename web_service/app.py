from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, g, send_file
import os
import sys
import uuid
import json
import shutil
from werkzeug.utils import secure_filename
import requests
from datetime import datetime
from sqlalchemy import func
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from web_service.config import (
        WEB_SERVICE_HOST, WEB_SERVICE_PORT, UPLOAD_FOLDER,
        ALLOWED_EXTENSIONS, OCR_SERVICE_URL, LLM_SERVICE_URL,
        DOCUMENT_TYPES
    )
    from database.db import get_session, init_db
    from database.models import (
        Application, Document, StudentInfo, Summary,
        DocumentType, ProcessingStatus, ApplicationStatus,
        User, UserRole, ReviewerEvaluation, ReviewerDecision
    )
    from web_service.auth import login_required, admin_required, reviewer_required, get_current_user
    from web_service.api_routes import api_bp
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  
app.register_blueprint(api_bp, url_prefix='/api')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.before_request
def before_request():
    """Set current user for templates."""
    g.current_user = get_current_user()

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    """Render the index page."""
    return render_template("index.html", current_user=g.current_user)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    if g.current_user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"

        if not username or not password:
            flash("Please enter username and password", "error")
            return redirect(url_for("login"))

        db_session = get_session()
        try:
            user = db_session.query(User).filter(User.username == username).first()

            if not user or not user.check_password(password):
                flash("Invalid username or password", "error")
                return redirect(url_for("login"))

            if not user.is_active:
                flash("Your account is inactive. Please contact an administrator.", "error")
                return redirect(url_for("login"))

            user.last_login = datetime.utcnow()
            db_session.commit()

            session["user_id"] = user.id
            if remember:
                session.permanent = True

            flash("Login successful", "success")
            logger.info(f"User {username} logged in successfully.")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("index"))

        except Exception as e:
            db_session.rollback()
            logger.error(f"Login error for user {username}: {e}")
            flash(f"Error during login. Please try again.", "error")
            return redirect(url_for("login"))
        finally:
            db_session.close()

    return render_template("login.html", current_user=g.current_user)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration."""
    if g.current_user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not email or not password or not confirm_password:
            flash("Please fill in all required fields", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("register"))

        db_session = get_session()
        try:
            existing_user = db_session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing_user:
                if existing_user.username == username:
                    flash("Username already exists", "error")
                else:
                    flash("Email already exists", "error")
                return redirect(url_for("register"))

            new_user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.REVIEWER.value, 
                is_active=True
            )
            new_user.set_password(password)

            db_session.add(new_user)
            db_session.commit()

            logger.info(f"New user registered: {username}")
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            db_session.rollback()
            logger.error(f"Registration error: {e}")
            flash(f"Error during registration. Please try again.", "error")
            return redirect(url_for("register"))
        finally:
            db_session.close()

    return render_template("register.html", current_user=g.current_user)

@app.route("/logout")
def logout():
    """Handle user logout."""
    username = g.current_user.username if g.current_user else "Unknown"
    session.pop("user_id", None)
    logger.info(f"User {username} logged out.")
    flash("You have been logged out", "info")
    return redirect(url_for("index"))

@app.route("/admin/users")
@admin_required
def admin_users():
    """Display user management page."""
    db_session = get_session()
    try:
        users = db_session.query(User).order_by(User.username).all()
        return render_template("admin_users.html", users=users, current_user=g.current_user, user_roles=[role.value for role in UserRole])
    except Exception as e:
        logger.error(f"Error fetching users for admin: {e}")
        flash(f"Error loading user management page.", "error")
        return redirect(url_for("index"))
    finally:
        db_session.close()

@app.route("/admin/users/add", methods=["POST"])
@admin_required
def admin_add_user():
    """Add a new user via admin panel."""
    username = request.form.get("username")
    email = request.form.get("email")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    password = request.form.get("password")
    role = request.form.get("role")
    is_active = request.form.get("is_active") == "on"

    if not username or not email or not password or not role:
        flash("Username, email, password, and role are required", "error")
        return redirect(url_for("admin_users"))

    if role not in [r.value for r in UserRole]:
        flash("Invalid role selected", "error")
        return redirect(url_for("admin_users"))

    db_session = get_session()
    try:
        existing_user = db_session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("Username or email already exists", "error")
            return redirect(url_for("admin_users"))
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=is_active
        )
        new_user.set_password(password)

        db_session.add(new_user)
        db_session.commit()

        logger.info(f"Admin added new user: {username} with role {role}")
        flash("User added successfully", "success")
        return redirect(url_for("admin_users"))

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error adding user via admin: {e}")
        flash(f"Error adding user.", "error")
        return redirect(url_for("admin_users"))
    finally:
        db_session.close()

@app.route("/admin/users/edit", methods=["POST"])
@admin_required
def admin_edit_user():
    """Edit an existing user via admin panel."""
    user_id = request.form.get("user_id")
    username = request.form.get("username")
    email = request.form.get("email")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    password = request.form.get("password")
    role = request.form.get("role")
    is_active = request.form.get("is_active") == "on"

    if not user_id or not username or not email or not role:
        flash("User ID, username, email, and role are required", "error")
        return redirect(url_for("admin_users"))

    if role not in [r.value for r in UserRole]:
        flash("Invalid role selected", "error")
        return redirect(url_for("admin_users"))

    db_session = get_session()
    try:
        user = db_session.query(User).filter(User.id == user_id).first()

        if not user:
            flash("User not found", "error")
            return redirect(url_for("admin_users"))
        if username != user.username and db_session.query(User).filter(User.username == username).count() > 0:
            flash("Username already exists for another user", "error")
            return redirect(url_for("admin_users"))
        if email != user.email and db_session.query(User).filter(User.email == email).count() > 0:
            flash("Email already exists for another user", "error")
            return redirect(url_for("admin_users"))

        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.role = role
        user.is_active = is_active

        if password:
            user.set_password(password)

        db_session.commit()

        logger.info(f"Admin updated user ID: {user_id}")
        flash("User updated successfully", "success")
        return redirect(url_for("admin_users"))

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error editing user ID {user_id} via admin: {e}")
        flash(f"Error updating user.", "error")
        return redirect(url_for("admin_users"))
    finally:
        db_session.close()

@app.route("/admin/users/delete", methods=["POST"])
@admin_required
def admin_delete_user():
    """Delete a user via admin panel."""
    user_id = request.form.get("user_id")

    if not user_id:
        flash("User ID is required", "error")
        return redirect(url_for("admin_users"))

    db_session = get_session()
    try:
        user = db_session.query(User).filter(User.id == user_id).first()

        if not user:
            flash("User not found", "error")
            return redirect(url_for("admin_users"))
        if user.username == "admin":
            flash("Cannot delete the default admin user", "error")
            return redirect(url_for("admin_users"))
        if user.id == g.current_user.id:
             flash("Cannot delete your own account", "error")
             return redirect(url_for("admin_users"))

        db_session.delete(user)
        db_session.commit()

        logger.warning(f"Admin deleted user ID: {user_id}, Username: {user.username}")
        flash("User deleted successfully", "success")
        return redirect(url_for("admin_users"))

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error deleting user ID {user_id} via admin: {e}")
        flash(f"Error deleting user.", "error")
        return redirect(url_for("admin_users"))
    finally:
        db_session.close()


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Handle file uploads and create a new application."""
    if request.method == "POST":
        student_name = request.form.get("student_name")
        if not student_name:
            flash("Please enter student name", "error")
            return redirect(request.url)

        safe_student_name = secure_filename(student_name)
        if not safe_student_name:
             flash("Invalid student name provided.", "error")
             return redirect(request.url)

        db_session = get_session()
        try:
            application = Application(
                student_name=student_name, 
                uploaded_by_id=g.current_user.id
            )
            db_session.add(application)
            db_session.flush()
            application_id = application.id
            logger.info(f"Created new application ID: {application_id} for student: {student_name}")
            student_dir = os.path.join(app.config["UPLOAD_FOLDER"], safe_student_name)
            os.makedirs(student_dir, exist_ok=True)

            uploaded_files_count = 0
            for doc_type_key, doc_type_label in DOCUMENT_TYPES.items():
                doc_type_dir = os.path.join(student_dir, doc_type_key)
                os.makedirs(doc_type_dir, exist_ok=True)

                if doc_type_key not in request.files:
                    continue

                file = request.files[doc_type_key]
                if file.filename == "":
                    continue 

                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(doc_type_dir, filename)
                    absolute_file_path = os.path.abspath(file_path)

                    try:
                        file.save(absolute_file_path)
                        logger.info(f"Saved file: {absolute_file_path} for app ID: {application_id}")
                        uploaded_files_count += 1

                        document = Document(
                            application_id=application_id,
                            file_name=filename,
                            file_path=absolute_file_path, 
                            file_type=file.content_type,
                            document_type=doc_type_key, 
                            processing_status=ProcessingStatus.PENDING.value 
                        )
                        db_session.add(document)
                    except Exception as save_err:
                         logger.error(f"Error saving file {filename} for app ID {application_id}: {save_err}")
                         flash(f"Error saving file {filename}.", "error")
                         continue
                elif file:
                    flash(f"File type not allowed for {doc_type_label}: {file.filename}", "warning")

            if uploaded_files_count == 0:
                 db_session.rollback() 
                 flash("No valid files were uploaded. Application not created.", "error")
                 return redirect(request.url)

            db_session.commit()
            flash(f"Application created successfully with {uploaded_files_count} document(s).", "success")
            return redirect(url_for("application", application_id=application_id))

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error during file upload for student {student_name}: {e}")
            flash(f"An unexpected error occurred during upload. Please try again.", "error")
            return redirect(request.url)
        finally:
            db_session.close()
    return render_template("upload.html", document_types=DOCUMENT_TYPES, current_user=g.current_user)

@app.route("/application/<int:application_id>")
@login_required
def application(application_id):
    session = get_session()
    try:
        application = session.query(Application).filter(Application.id == application_id).first()
        if not application:
            flash("Application not found", "error")
            return redirect(url_for("history"))
        if not (g.current_user.is_admin() or g.current_user.is_reviewer()):
            flash("You do not have permission to view this application.", "error")
            return redirect(url_for("history"))

        student_info = session.query(StudentInfo).filter(StudentInfo.application_id == application_id).first()
        summary = session.query(Summary).filter(Summary.application_id == application_id).first()
        documents = session.query(Document).filter(Document.application_id == application_id).order_by(Document.upload_date).all()
        evaluations = session.query(ReviewerEvaluation).filter(ReviewerEvaluation.application_id == application_id).all()

        can_process = any(doc.processing_status == ProcessingStatus.PENDING.value for doc in documents)
        all_processed_successfully = all(doc.processing_status == ProcessingStatus.COMPLETED.value for doc in documents) if documents else False
        analysis_pending = application.status in [ApplicationStatus.SUBMITTED.value, ApplicationStatus.PROCESSING.value] and not summary
        can_analyze = all_processed_successfully and analysis_pending

        return render_template(
            "application.html",
            application=application,
            student_info=student_info,
            summary=summary,
            documents=documents,
            evaluations=evaluations,
            document_types=DOCUMENT_TYPES,
            processing_status_enum=ProcessingStatus,
            can_process=can_process,
            can_analyze=can_analyze,
            current_user=g.current_user
        )

    except Exception as e:
        flash("Error loading application details.", "error")
        return redirect(url_for("history"))
    finally:
        session.close()

@app.route("/document/<int:document_id>/view")
@login_required
def view_document(document_id):
    """View or download a document file."""
    db_session = get_session()
    try:
        document = db_session.query(Document).filter(Document.id == document_id).first()
        if not document:
            flash("Document not found", "error")
            return redirect(url_for("history"))

        application = db_session.query(Application).filter(Application.id == document.application_id).first()
        if not (g.current_user.is_admin() or g.current_user.is_reviewer()):
            flash("You do not have permission to view this document.", "error")
            return redirect(url_for("history"))

        if not os.path.exists(document.file_path):
            flash("File not found on server", "error")
            return redirect(url_for("application", application_id=document.application_id))

        return send_file(
            document.file_path,
            as_attachment=False, 
            download_name=document.file_name
        )

    except Exception as e:
        logger.error(f"Error viewing document ID {document_id}: {e}")
        flash("Error accessing document", "error")
        return redirect(url_for("history"))
    finally:
        db_session.close()

@app.route("/document/<int:document_id>/download")
@login_required
def download_document(document_id):
    """Download a document file."""
    db_session = get_session()
    try:
        document = db_session.query(Document).filter(Document.id == document_id).first()
        if not document:
            flash("Document not found", "error")
            return redirect(url_for("history"))

        application = db_session.query(Application).filter(Application.id == document.application_id).first()
        if not (g.current_user.is_admin() or g.current_user.is_reviewer()):
            flash("You do not have permission to download this document.", "error")
            return redirect(url_for("history"))

        if not os.path.exists(document.file_path):
            flash("File not found on server", "error")
            return redirect(url_for("application", application_id=document.application_id))

        return send_file(
            document.file_path,
            as_attachment=True,
            download_name=document.file_name
        )

    except Exception as e:
        logger.error(f"Error downloading document ID {document_id}: {e}")
        flash("Error downloading document", "error")
        return redirect(url_for("history"))
    finally:
        db_session.close()

@app.route("/application/<int:application_id>/process_documents", methods=["POST"])
@login_required
def process_documents(application_id):
    """Trigger processing (OCR or direct extraction) for pending documents."""
    db_session = get_session()
    try:
        application = db_session.query(Application).filter(Application.id == application_id).first()
        if not application:
            flash("Application not found", "error")
            return redirect(url_for("history"))
        
        if not g.current_user.is_admin() and application.uploaded_by_id != g.current_user.id:
             flash("You do not have permission to process documents for this application.", "error")
             return redirect(url_for("application", application_id=application_id))

        documents_to_process = db_session.query(Document).filter(
            Document.application_id == application_id,
            Document.processing_status == ProcessingStatus.PENDING.value
        ).all()

        if not documents_to_process:
            flash("No documents are pending processing.", "info")
            return redirect(url_for("application", application_id=application_id))

        logger.info(f"Starting document processing for application ID: {application_id}")
        application.status = ApplicationStatus.PROCESSING.value
        db_session.commit()

        processed_count = 0
        failed_count = 0
        for document in documents_to_process:
            logger.info(f"Sending document ID {document.id} ({document.file_name}) to OCR service.")
            try:
                document.processing_status = ProcessingStatus.PROCESSING.value
                db_session.commit()

                ocr_payload = {
                    "document_id": document.id,
                    "file_path": document.file_path,
                    "document_type": document.document_type
                }
                ocr_response = requests.post(f"{OCR_SERVICE_URL}/api/process", json=ocr_payload, timeout=240) 

                ocr_response.raise_for_status() 
                logger.info(f"Successfully requested processing for document ID {document.id}. OCR service response: {ocr_response.status_code}")
                processed_count += 1

            except requests.exceptions.RequestException as req_err:
                logger.error(f"Failed to send document ID {document.id} to OCR service: {req_err}")
                document.processing_status = ProcessingStatus.FAILED.value
                db_session.commit()
                failed_count += 1
            except Exception as e:
                logger.error(f"Unexpected error processing document ID {document.id}: {e}")
                document.processing_status = ProcessingStatus.FAILED.value
                db_session.commit()
                failed_count += 1

        db_session.refresh(application)

        all_docs = db_session.query(Document).filter(Document.application_id == application_id).all()
        if all(doc.processing_status != ProcessingStatus.PENDING.value for doc in all_docs):
             pass

        if failed_count > 0:
            flash(f"Requested processing for {processed_count} document(s). {failed_count} request(s) failed. Check document statuses.", "warning")
        else:
            flash(f"Requested processing for {processed_count} document(s). Check status updates below.", "success")

        return redirect(url_for("application", application_id=application_id))

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error in process_documents route for app ID {application_id}: {e}")
        flash("An unexpected error occurred while starting document processing.", "error")
        return redirect(url_for("application", application_id=application_id))
    finally:
        db_session.close()

@app.route("/application/<int:application_id>/analyze", methods=["POST"])
@login_required
def analyze_application(application_id):
    """Trigger LLM analysis for all completed documents in an application."""
    db_session = get_session()
    try:
        application = db_session.query(Application).filter(Application.id == application_id).first()
        if not application:
            flash("Application not found", "error")
            return redirect(url_for("history"))

        if not g.current_user.is_admin() and application.uploaded_by_id != g.current_user.id:
             flash("You do not have permission to analyze this application.", "error")
             return redirect(url_for("application", application_id=application_id))

        existing_summary = db_session.query(Summary).filter(Summary.application_id == application_id).first()
        if existing_summary:
             flash("Application has already been analyzed.", "info")
             return redirect(url_for("application", application_id=application_id))

        documents = db_session.query(Document).filter(Document.application_id == application_id).all()
        if not documents:
            flash("No documents found for this application.", "error")
            return redirect(url_for("application", application_id=application_id))

        completed_docs = []
        pending_docs = []
        failed_docs = []
        for doc in documents:
            if doc.processing_status == ProcessingStatus.COMPLETED.value:
                if doc.content_text:
                     completed_docs.append(doc)
                else:
                     logger.warning(f"Document ID {doc.id} is COMPLETED but has no content_text. Skipping for analysis.")
                     failed_docs.append(doc) 
            elif doc.processing_status == ProcessingStatus.PENDING.value or doc.processing_status == ProcessingStatus.PROCESSING.value:
                pending_docs.append(doc)
            else:
                failed_docs.append(doc)

        if pending_docs:
            flash(f"{len(pending_docs)} document(s) are still pending or processing. Cannot analyze yet.", "warning")
            return redirect(url_for("application", application_id=application_id))

        if not completed_docs:
             flash("No successfully processed documents with text content found. Cannot analyze.", "error")
             return redirect(url_for("application", application_id=application_id))

        logger.info(f"Starting LLM analysis for application ID: {application_id} with {len(completed_docs)} documents.")
        llm_payload = {
            "application_id": application_id,
            "documents": [
                {
                    "document_id": doc.id,
                    "document_type": doc.document_type,
                    "content_text": doc.content_text,
                }
                for doc in completed_docs
            ]
        }

        try:
            llm_response = requests.post(f"{LLM_SERVICE_URL}/api/analyze", json=llm_payload, timeout=240) 
            llm_response.raise_for_status()

            logger.info(f"Successfully requested LLM analysis for application ID {application_id}. LLM service response: {llm_response.status_code}")
            flash("Analysis requested successfully. Results will appear once processed by the LLM service.", "success")

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Failed to send analysis request for application ID {application_id} to LLM service: {req_err}")
            flash("Failed to request analysis from LLM service.", "error")
        except Exception as e:
            logger.error(f"Unexpected error during LLM analysis request for application ID {application_id}: {e}")
            flash("An unexpected error occurred while requesting analysis.", "error")

        return redirect(url_for("application", application_id=application_id))

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error in analyze_application route for app ID {application_id}: {e}")
        flash("An unexpected error occurred.", "error")
        return redirect(url_for("application", application_id=application_id))
    finally:
        db_session.close()

@app.route("/history")
@login_required
def history():
    """Display application history based on user role."""
    db_session = get_session()
    try:
        query = db_session.query(Application)
        applications = query.order_by(Application.submission_date.desc()).all()
        
        applications_with_avg_scores = []
        for app in applications:
            evaluations = db_session.query(ReviewerEvaluation).filter(
                ReviewerEvaluation.application_id == app.id,
                ReviewerEvaluation.score.isnot(None)
            ).all()
            
            if evaluations:
                avg_score = sum(eval.score for eval in evaluations) / len(evaluations)
            else:
                avg_score = None
                
            applications_with_avg_scores.append({
                'application': app,
                'avg_reviewer_score': avg_score
            })
        
        return render_template("history.html", applications_with_scores=applications_with_avg_scores, current_user=g.current_user)

    except Exception as e:
        logger.error(f"Error fetching application history for user {g.current_user.username}: {e}")
        flash("Error loading application history.", "error")
        return redirect(url_for("index"))
    finally:
        db_session.close()

@app.route("/dashboard")
@login_required
def dashboard():
    db_session = get_session()
    try:
        base_query = db_session.query(Application)
        student_info_query = db_session.query(StudentInfo).join(Application)

        total_applications = base_query.count()
        approved_applications = base_query.filter(Application.status == ApplicationStatus.APPROVED.value).count()
        rejected_applications = base_query.filter(Application.status == ApplicationStatus.REJECTED.value).count()
        invited_applications = base_query.filter(Application.status == ApplicationStatus.INVITED_TO_INTERVIEW.value).count()
        pending_applications = total_applications - approved_applications - rejected_applications - invited_applications

        status_counts = base_query.with_entities(
            Application.status,
            func.count(Application.id)
        ).group_by(Application.status).all()

        status_data = {status.value: 0 for status in ApplicationStatus}
        for status, count in status_counts:
            if status in status_data:
                status_data[status] = count

        avg_score_results = base_query.with_entities(Application.evaluation_score).all()
        avg_score = sum([score[0] for score in avg_score_results]) / len(avg_score_results) if avg_score_results else 0

        language_levels_data = student_info_query.with_entities(
            StudentInfo.russian_language_level,
            func.count(StudentInfo.id)
        ).filter(StudentInfo.russian_language_level.isnot(None), func.length(func.trim(StudentInfo.russian_language_level)) > 0).group_by(StudentInfo.russian_language_level).all()
        language_levels = {level: count for level, count in language_levels_data}

        nationalities_data = student_info_query.with_entities(
            StudentInfo.nationality,
            func.count(StudentInfo.id)
        ).filter(StudentInfo.nationality.isnot(None), func.length(func.trim(StudentInfo.nationality)) > 0).group_by(StudentInfo.nationality).order_by(func.count(StudentInfo.id).desc()).limit(10).all()
        nationalities = {nat: count for nat, count in nationalities_data}

        reviewers = db_session.query(User)\
        .filter(User.role == UserRole.REVIEWER.value)\
        .order_by(User.id)\
        .limit(3).all()
        apps = base_query.order_by(Application.submission_date.desc()).all()

        table_rows = []
        for app in apps:
            evaluations = db_session.query(ReviewerEvaluation).filter(
                ReviewerEvaluation.application_id == app.id,
                ReviewerEvaluation.score.isnot(None)
            ).all()
            
            if evaluations:
                avg_reviewer_score = sum(eval.score for eval in evaluations) / len(evaluations)
            else:
                avg_reviewer_score = None
            
            row = {
                'id': app.id,
                'student_name': app.student_name,
                'final_status': app.status,
                'avg_reviewer_score': avg_reviewer_score
            }
            for idx, rev in enumerate(reviewers, start=1):
                ev = next((e for e in app.evaluations if e.reviewer_id == rev.id), None)
                row[f'decision{idx}'] = ev.decision if ev else ''
                row[f'comment{idx}'] = ev.comments if ev and ev.comments else ''  # Lấy comment reviewer
                row[f'score{idx}'] = ev.score if ev and ev.score is not None else ''  # Lấy score reviewer
            table_rows.append(row)

        return render_template(
            "dashboard.html",
            total_applications=total_applications,
            status_data=status_data,
            application_status_enum=ApplicationStatus,
            approved_applications=approved_applications,
            rejected_applications=rejected_applications,
            invited_applications=invited_applications,
            pending_applications=pending_applications,
            avg_score=avg_score,
            language_levels=language_levels,
            nationalities=nationalities,
            reviewers=reviewers,
            table_rows=table_rows,
            current_user=g.current_user
        )
    except Exception as e:
        logger.error(f"Error generating dashboard data for user {g.current_user.username}: {e}")
        flash("Error loading dashboard data.", "error")
        return redirect(url_for("index"))
    finally:
        db_session.close()

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "web_service"})

@app.route("/application/<int:application_id>/review", methods=["POST"])
@reviewer_required
def submit_review(application_id):
    session = get_session()
    try:
        application = session.query(Application).filter_by(id=application_id).first()
        if not application:
            return jsonify({"error": "Application not found"}), 404

        decision = request.form.get("decision")
        comments = request.form.get("comments", "")
        score = request.form.get("score") 
        user_id = g.current_user.id

        if decision not in [d.value for d in ReviewerDecision]:
            return jsonify({"error": "Invalid decision value"}), 400

        if score:
            try:
                score = int(score)
                if score < 0 or score > 100:
                    return jsonify({"error": "Score must be between 0 and 100"}), 400
            except ValueError:
                return jsonify({"error": "Invalid score format"}), 400
        else:
            score = None

        review = session.query(ReviewerEvaluation).filter_by(application_id=application_id, reviewer_id=user_id).first()
        if review:
            review.decision = decision
            review.comments = comments
            review.score = score
            review.created_at = datetime.utcnow()
        else:
            review = ReviewerEvaluation(
                application_id=application_id,
                reviewer_id=user_id,
                decision=decision,
                comments=comments,
                score=score
            )
            session.add(review)

        session.flush()
        
        all_reviews = session.query(ReviewerEvaluation).filter_by(application_id=application_id).all()
        if len(all_reviews) < 3:
            application.status = ApplicationStatus.EVALUATED.value
        else:
            decisions = [r.decision for r in all_reviews]
            for d in ['approved', 'rejected', 'invited']:
                if decisions.count(d) >= 2:
                    application.status = {
                        'approved': ApplicationStatus.APPROVED.value,
                        'rejected': ApplicationStatus.REJECTED.value,
                        'invited': ApplicationStatus.INVITED_TO_INTERVIEW.value
                    }[d]
                    break
            else:
                application.status = ApplicationStatus.EVALUATED.value

        session.commit()
        return jsonify({"success": True, "new_status": application.status})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route("/application/<int:application_id>/reviews")
@login_required
def application_reviews(application_id):
    session = get_session()
    try:
        application = session.query(Application).filter_by(id=application_id).first()
        if not application:
            flash("Application not found", "error")
            return redirect(url_for("index"))

        evaluations = session.query(ReviewerEvaluation).filter_by(application_id=application_id).all()
        return render_template("review_history.html", application=application, evaluations=evaluations, current_user=g.current_user)
    except Exception as e:
        flash(f"Error loading reviews: {str(e)}", "error")
        return redirect(url_for("index"))
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    logger.info(f"Starting Web Service on {WEB_SERVICE_HOST}:{WEB_SERVICE_PORT}")
    app.run(host=WEB_SERVICE_HOST, port=WEB_SERVICE_PORT, debug=True)

