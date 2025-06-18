from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import relationship
import enum
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class UserRole(enum.Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"

class EvaluationStatus(enum.Enum):
    REJECTED = "rejected"
    APPROVED = "approved"
    PENDING = "pending"
    INVITED_TO_INTERVIEW = "invited_to_interview"

class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), default=UserRole.REVIEWER.value)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    applications = relationship("Application", back_populates="uploaded_by")

    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user is admin."""
        return self.role == UserRole.ADMIN.value

    def is_reviewer(self):
        """Check if user is reviewer."""
        return self.role == UserRole.REVIEWER.value
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

class DocumentType(enum.Enum):
    PASSPORT = "passport"
    CV = "cv"
    DEGREE = "degree"
    MOTIVATION_LETTER = "motivation_letter"
    RECOMMENDATION_LETTER = "recommendation_letter"
    LANGUAGE_CERTIFICATE = "language_certificate"
    ACHIEVEMENTS = "achievements"
    ADDITIONAL_DOCUMENTS = "additional_documents"
    OTHER = "other"

class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ApplicationStatus(enum.Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    EVALUATED = "evaluated"
    REJECTED = "rejected"
    APPROVED = "approved"
    INVITED_TO_INTERVIEW = "invited_to_interview"

class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True)
    student_name = Column(String(255), nullable=True)
    submission_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default=ApplicationStatus.SUBMITTED.value)
    evaluation_score = Column(Float, nullable=True)
    evaluation_date = Column(DateTime, nullable=True)

    uploaded_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    uploaded_by = relationship("User", back_populates="applications")

    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    student_info = relationship("StudentInfo", back_populates="application", uselist=False, cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="application", uselist=False, cascade="all, delete-orphan")
    evaluations = relationship("ReviewerEvaluation", back_populates="application", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application(id={self.id}, student_name={self.student_name}, status={self.status})>"

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)  # mime type
    upload_date = Column(DateTime, default=datetime.utcnow)
    document_type = Column(String(50), default=DocumentType.OTHER.value)
    content_text = Column(Text, nullable=True)
    processing_status = Column(String(20), default=ProcessingStatus.PENDING.value)
    
    # Relationships
    application = relationship("Application", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, document_type={self.document_type})>"

class StudentInfo(Base):
    __tablename__ = 'student_info'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(String(50), nullable=True)
    age = Column(Integer, nullable=True)
    nationality = Column(String(100), nullable=True)
    previous_university = Column(String(255), nullable=True)
    gpa = Column(Float, nullable=True)
    russian_language_level = Column(String(50), nullable=True)
    
    # Relationships
    application = relationship("Application", back_populates="student_info")

    def __repr__(self):
        return f"<StudentInfo(id={self.id}, name={self.name})>"

class Summary(Base):
    __tablename__ = 'summaries'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, unique=True)
    cv_summary = Column(Text, nullable=True)
    motivation_letter_summary = Column(Text, nullable=True)
    recommendation_letter_summary = Column(Text, nullable=True)
    recommendation_author = Column(String(255), nullable=True)
    achievements_summary = Column(Text, nullable=True)
    additional_documents_summary = Column(Text, nullable=True)
    evaluation_comments = Column(Text, nullable=True)
    application = relationship("Application", back_populates="summary")

    def __repr__(self):
        return f"<Summary(id={self.id}, application_id={self.application_id})>"
    
class ReviewerDecision(enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    INVITED = "invited"

class ReviewerEvaluation(Base):
    __tablename__ = 'reviewer_evaluations'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False)
    reviewer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    decision = Column(String(30), nullable=False)  
    comments = Column(Text, nullable=True)
    score = Column(Integer, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="evaluations")
    reviewer = relationship("User")

    def __repr__(self):
        return f"<ReviewerEvaluation(application_id={self.application_id}, reviewer_id={self.reviewer_id}, decision={self.decision}, score={self.score})>"


