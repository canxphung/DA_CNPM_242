"""
Thiết lập kết nối đến Redis và Firebase.
"""
import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, db
from .redis_client import RedisClient

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Biến toàn cục lưu trữ kết nối
redis_client = None
firebase_app = None

async def init_database_connections():
    """Khởi tạo tất cả các kết nối database."""
    global redis_client, firebase_app
    
    # Khởi tạo kết nối Redis
    redis_client = init_redis_connection()
    
    # Khởi tạo kết nối Firebase
    firebase_app = init_firebase_connection()
    
    logger.info("All database connections initialized")

def init_redis_connection():
    """Khởi tạo kết nối Redis."""
    try:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        db = int(os.getenv("REDIS_DB", 0))
        password = os.getenv("REDIS_PASSWORD", None)
        
        client = RedisClient(
            host=host,
            port=port,
            db=db,
            password=password
        )
        
        logger.info(f"Redis connection established: {host}:{port}")
        return client
    
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise

def init_firebase_connection():
    """Khởi tạo kết nối Firebase."""
    try:
        global firebase_app
        
        # Kiểm tra xem Firebase đã được khởi tạo chưa
        if firebase_app is not None:
            logger.info("Firebase app already initialized")
            return firebase_app
            
        # Nếu đã có một app khác được khởi tạo, sử dụng nó
        if firebase_admin._apps:
            logger.info("Using existing Firebase app")
            firebase_app = firebase_admin._apps.get('[DEFAULT]')
            return firebase_app
        
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        db_url = os.getenv("FIREBASE_DATABASE_URL")
        
        if not cred_path or not os.path.exists(cred_path):
            logger.error(f"Firebase credentials file not found: {cred_path}")
            raise FileNotFoundError(f"Firebase credentials file not found: {cred_path}")
        
        cred = credentials.Certificate(cred_path)
        firebase_app = firebase_admin.initialize_app(cred, {
            'databaseURL': db_url
        })
        
        logger.info(f"Firebase connection established to {db_url}")
        return firebase_app
    
    except Exception as e:
        logger.error(f"Failed to connect to Firebase: {str(e)}")
        raise

def get_redis_client():
    """Trả về instance Redis client đã được khởi tạo."""
    global redis_client
    if redis_client is None:
        # Nếu chưa được khởi tạo, thử khởi tạo
        redis_client = init_redis_connection()
    return redis_client

def get_firebase_db_reference(path=None):
    """
    Trả về tham chiếu đến Firebase Realtime Database.
    
    Args:
        path: Đường dẫn trong database (tùy chọn)
        
    Returns:
        Tham chiếu đến database
    """
    global firebase_app
    
    # Nếu firebase_app chưa được khởi tạo, thử khởi tạo
    if firebase_app is None:
        firebase_app = init_firebase_connection()
        
    if firebase_app is None:
        raise RuntimeError("Firebase app has not been initialized")
    
    # Đảm bảo path là chuỗi hợp lệ
    if path is None:
        path = ""  # Sử dụng chuỗi rỗng thay vì None
        
    return db.reference(path)