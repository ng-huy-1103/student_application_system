from database.db import db
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class StudentInfo(db.Model):
    """StudentInfo model containing extracted student information."""
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