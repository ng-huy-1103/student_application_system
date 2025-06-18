"""
Configuration for web service.
"""
import os
from pathlib import Path

WEB_SERVICE_HOST = os.getenv("WEB_SERVICE_HOST", "0.0.0.0")
WEB_SERVICE_PORT = int(os.getenv("WEB_SERVICE_PORT", 5000))

OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://localhost:5001")

LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:5002")

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = os.path.join(BASE_DIR, "../uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx"}

DOCUMENT_TYPES = {
    "passport": "Passport",
    "cv": "CV / Resume",
    "degree": "University Degree",
    "motivation_letter": "Motivation Letter",
    "recommendation_letter": "Recommendation Letter",
    "language_certificate": "Russian Language Certificate",
    "achievements": "Personal Achievements",
    "additional_documents": "Additional Documents"
}

