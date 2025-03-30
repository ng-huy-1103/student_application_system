from datetime import datetime
from db import db
import enum

class UserRole(enum.Enum):
    admin = "admin"
    teacher = "teacher"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.teacher)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
