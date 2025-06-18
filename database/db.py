import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from database.models import Base, User, UserRole
import logging

logger = logging.getLogger(__name__)


DATABASE_URL = f"postgresql://postgres:Tienmanh2001@localhost:5432/student_analysis"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    """Get a database session."""
    return SessionLocal()

def init_db():
    """Initialize the database (create tables)."""
    Base.metadata.create_all(bind=engine)
    session = get_session()
    try:
        admin_user = session.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role=UserRole.ADMIN.value,
                first_name='Admin',
                last_name='User',
                is_active=True
            )
            admin_user.set_password('admin123')
            session.add(admin_user)
            print("Default admin user created.")
            reviewer1 = User(first_name = "User", last_name="Reviewer 1", username="rev1", email='rev1@example.com', is_active=True, role=UserRole.REVIEWER.value)
            reviewer1.set_password('123456')
            reviewer2 = User(first_name = "User", last_name="Reviewer 2", username="rev2", email='rev2@example.com', is_active=True, role=UserRole.REVIEWER.value)
            reviewer2.set_password('123456')
            reviewer3 = User(first_name = "User", last_name="Reviewer 3", username="rev3", email='rev3@example.com', is_active=True, role=UserRole.REVIEWER.value)
            reviewer3.set_password('123456')
            session.add(reviewer1)
            session.add(reviewer2)
            session.add(reviewer3)
            session.commit()
        
    except Exception as e:
        session.rollback()
        print(f"Error creating default admin user: {str(e)}")
    finally:
        session.close()

