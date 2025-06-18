"""
Configuration for OCR service.
"""
import os
from pathlib import Path

# Service configuration
OCR_SERVICE_HOST = os.getenv('OCR_SERVICE_HOST', '0.0.0.0')
OCR_SERVICE_PORT = int(os.getenv('OCR_SERVICE_PORT', 5001))

# Upload folder configuration
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = os.path.join(BASE_DIR, '../uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt'}
# Sử dụng CPU thay vì GPU để tránh xung đột bộ nhớ với LLM_service
USE_GPU = False


