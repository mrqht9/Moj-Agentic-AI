import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    API_KEY = os.environ.get('API_KEY')
    
    # Gemini Models
    TEXT_MODEL = "gemini-2.5-flash"
    IMAGE_GEN_MODEL = "imagen-4.0-generate-001"
    IMAGE_EDIT_MODEL = "gemini-2.5-flash"
    
    # App Settings
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
