from database.db import db
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class ApplicationStatus(enum.Enum):
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    EVALUATED = "evaluated"
    REJECTED = "rejected"
    APPROVED = "approved"


class Application(db.Model):
    """Application model representing a student's application."""
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True)
    submission_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default=ApplicationStatus.SUBMITTED.value)
    evaluation_score = Column(Float, nullable=True)
    evaluation_date = Column(DateTime, nullable=True)
    
    # Relationships
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    student_info = relationship("StudentInfo", back_populates="application", uselist=False, cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="application", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Application(id={self.id}, status={self.status})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "status": self.status,
            "evaluation_score": self.evaluation_score,
            "evaluation_date": self.evaluation_date.isoformat() if self.evaluation_date else None
        }