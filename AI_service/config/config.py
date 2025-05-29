import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# load_dotenv(os.path.dirname(__file__).parent + '/.env')
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# AI api configuration
AI_API_URL = os.getenv('AI_API_URL')

# model configuration
MODEL_STORAGE_PATH = os.getenv('MODEL_STORAGE_PATH')
CACHE_STORAGE_PATH = os.getenv('CACHE_STORAGE_PATH')

# API configuration
API_HOST = os.getenv('API_HOST')
API_PORT = int(os.getenv('API_PORT'))

# Cấu hình tích hợp Core Operations Service
CORE_OPS_API_URL = os.getenv('CORE_OPS_API_URL')
CORE_OPS_API_KEY = os.getenv('CORE_OPS_API_KEY')

# Cấu hình kết nối đến Core Operations Redis
CORE_OPS_REDIS_HOST = os.getenv('CORE_OPS_REDIS_HOST', 'localhost')
CORE_OPS_REDIS_PORT = int(os.getenv('CORE_OPS_REDIS_PORT', '6379'))
CORE_OPS_REDIS_DB = int(os.getenv('CORE_OPS_REDIS_DB', '0'))
CORE_OPS_REDIS_PASSWORD = os.getenv('CORE_OPS_REDIS_PASSWORD', '')

# Cấu hình kết nối đến Core Operations Firebase
CORE_OPS_FIREBASE_CREDENTIALS_PATH = os.getenv('CORE_OPS_FIREBASE_CREDENTIALS_PATH')
CORE_OPS_FIREBASE_DATABASE_URL = os.getenv('CORE_OPS_FIREBASE_DATABASE_URL')

# Cấu hình tối ưu hóa tài nguyên
RESOURCE_OPTIMIZATION = {
    "min_water_saving_percent": float(os.getenv('MIN_WATER_SAVING_PERCENT', '10')),
    "preferred_times": os.getenv('PREFERRED_IRRIGATION_TIMES', '06:00,18:00').split(','),
    "avoid_times": os.getenv('AVOID_IRRIGATION_TIMES', '12:00,13:00').split(',')
}

# Cấu hình OpenAI - mặc định
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.7'))

# Cấu hình mặc định tưới
DEFAULT_IRRIGATION_DURATION = int(os.getenv('DEFAULT_IRRIGATION_DURATION', '10'))