from database.db import db
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(enum.Enum):
    PASSPORT = "passport"
    CV = "cv"
    DEGREE = "degree"
    MOTIVATION_LETTER = "motivation_letter"
    RECOMMENDATION_LETTER = "recommendation_letter"
    LANGUAGE_CERTIFICATE = "language_certificate"
    OTHER = "other"



class Document(db.Model):
    """Document model representing uploaded files."""
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
    
