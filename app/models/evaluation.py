from database.db import db
from sqlalchemy import CheckConstraint
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from datetime import datetime
import enum

class EvaluationStatus(enum.Enum):
    REJECTED = "rejected"
    APPROVED = "approved"
    PENDING = "pending"


class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    evaluator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    evaluation_score = Column(Integer, nullable=True)
    evaluation_comments = Column(Text, nullable=True)
    evaluation_status = Column(String(20), nullable=False, default = EvaluationStatus.PENDING.value)
    evaluation_date = Column(DateTime, default=datetime.now())

    
    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'evaluator_id': self.evaluator_id,
            'evaluation_score': self.evaluation_score,
            'evaluation_comments': self.evaluation_comments,
            'evaluation_status': self.evaluation_status,
            'evaluation_date': self.evaluation_date.isoformat() if self.evaluation_date else None,
        }
