
import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

class Config:
    
    # Cấu hình Adafruit IO
    ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME")
    ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")
    ADAFRUIT_FEED_KEYS = os.getenv("ADAFRUIT_FEED_KEYS", "").split(",")
    ADAFRUIT_IO_SERVER = os.getenv("ADAFRUIT_IO_SERVER")
    ADAFRUIT_IO_PORT = int(os.getenv("ADAFRUIT_IO_PORT"))
    
    # Cấu hình MongoDB
    MONGODB_URI = os.getenv("MONGODB_URI")
    MONGODB_DB = os.getenv("MONGODB_DB")
    MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")
    
    # Cấu hình AI Service
    AI_SERVICE_URL = os.getenv("AI_SERVICE_URL")
    AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT"))
    
    # Cấu hình logging
    LOG_LEVEL = os.getenv("LOG_LEVEL")
    
    # Cấu hình retry
    MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS"))
    RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY"))
    
    @classmethod
    def validate(cls):
 
        required_vars = [
            "ADAFRUIT_IO_USERNAME", 
            "ADAFRUIT_IO_KEY", 
            "ADAFRUIT_FEED_KEYS"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Thiếu các biến môi trường bắt buộc: {', '.join(missing_vars)}")
        
        # Kiểm tra danh sách feed keys
        if not cls.ADAFRUIT_FEED_KEYS or cls.ADAFRUIT_FEED_KEYS[0] == '':
            raise ValueError("ADAFRUIT_FEED_KEYS không thể trống")
        
        return True