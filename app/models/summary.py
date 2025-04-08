from database.db import db
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class Summary(db.Model):
    """Summary model containing summaries of different documents."""
    __tablename__ = 'summaries'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, unique=True)
    cv_summary = Column(Text, nullable=True)
    motivation_letter_summary = Column(Text, nullable=True)
    recommendation_letter_summary = Column(Text, nullable=True)
    recommendation_author = Column(String(255), nullable=True)
    evaluation_comments = Column(Text, nullable=True)
    
    # Relationships
    application = relationship("Application", back_populates="summary")

    def __repr__(self):
        return f"<Summary(id={self.id}, application_id={self.application_id})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.submission_date.isoformat() if self.submission_date else None,
            "cv_summary": self.status,
            "motivation_letter_summary": self.motivation_letter_summary,
            "recommendation_letter_summary": self.recommendation_letter_summary,
            "recommendation_author": self.recommendation_author,
            "evaluation_comments": self.evaluation_comments
        }