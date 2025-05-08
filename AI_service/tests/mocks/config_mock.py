# tests/mocks/config_mock.py
"""
Mock configuration for tests
"""

# Database configuration
DATABASE_URL = "sqlite:///:memory:"  # Sử dụng SQLite in-memory cho tests

# API configuration
API_HOST = "127.0.0.1"
API_PORT = 8000

# OpenAI API configuration
OPENAI_API_KEY = "test_openai_key"

# Cache configuration
CACHE_STORAGE_PATH = "/tmp/test_cache"

# Model storage configuration
MODEL_STORAGE_PATH = "/tmp/test_models"

# Irrigation configuration
DEFAULT_IRRIGATION_DURATION = 10
OPTIMAL_SOIL_MOISTURE = 50
WATER_USAGE_PER_MINUTE = 2

# Core Operations API configuration
CORE_OPS_API_URL = "http://localhost:8001"
CORE_OPS_API_KEY = "test_api_key"
CORE_OPS_REDIS_HOST = "localhost"
CORE_OPS_REDIS_PORT = 6379
CORE_OPS_REDIS_DB = 0
CORE_OPS_REDIS_PASSWORD = ""
CORE_OPS_FIREBASE_CREDENTIALS_PATH = "path/to/test_credentials.json"
CORE_OPS_FIREBASE_DATABASE_URL = "https://test-db.firebaseio.com"

# Decision engine configuration
CONFIDENCE_THRESHOLD = 0.7
