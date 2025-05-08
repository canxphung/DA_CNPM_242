"""
Script kiểm tra kết nối đến các dịch vụ bên ngoài.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Thiết lập logging cơ bản
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Tải biến môi trường
load_dotenv()

def test_redis_connection():
    """Kiểm tra kết nối đến Redis."""
    try:
        from src.infrastructure.database import RedisClient
        
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
        
        # Thử set và get giá trị
        test_key = "test:connection"
        test_value = "Redis connection successful!"
        
        client.set(test_key, test_value)
        retrieved_value = client.get(test_key)
        client.delete(test_key)
        
        if retrieved_value == test_value:
            logger.info(f"✅ Redis connection successful: {host}:{port}")
            return True
        else:
            logger.error(f"❌ Redis connection failed: {host}:{port} (Data mismatch)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        return False

def test_firebase_connection():
    """Kiểm tra kết nối đến Firebase."""
    try:
        from src.infrastructure.database import FirebaseClient
        
        # Kiểm tra tệp credentials
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not os.path.exists(cred_path):
            logger.error(f"❌ Firebase credentials file not found: {cred_path}")
            return False
        
        # Khởi tạo client
        client = FirebaseClient("test")
        
        # Thử thao tác dữ liệu
        test_path = "test/connection"
        test_data = {"status": "Firebase connection successful!", "timestamp": client._get_reference().get_server_time()}
        
        client.set(test_path, test_data)
        retrieved_data = client.get(test_path)
        client.delete(test_path)
        
        if retrieved_data and retrieved_data.get("status") == test_data["status"]:
            logger.info(f"✅ Firebase connection successful")
            return True
        else:
            logger.error(f"❌ Firebase connection failed (Data mismatch)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Firebase connection failed: {str(e)}")
        return False

def test_adafruit_connection():
    """Kiểm tra kết nối đến Adafruit IO."""
    try:
        from src.adapters.cloud.adafruit import AdafruitIOClient
        
        username = os.getenv('ADAFRUIT_IO_USERNAME', '')
        key = os.getenv('ADAFRUIT_IO_KEY', '')
        
        if not username or not key:
            logger.error(f"❌ Adafruit IO credentials not found in environment variables")
            return False
            
        client = AdafruitIOClient(username, key)
        
        # Lấy danh sách feeds để kiểm tra kết nối
        try:
            feeds = client.client.feeds()
            logger.info(f"✅ Adafruit IO connection successful. Found {len(feeds)} feeds")
            return True
        except Exception as e:
            logger.error(f"❌ Adafruit IO connection failed when retrieving feeds: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Adafruit IO connection failed: {str(e)}")
        return False

def run_tests():
    """Chạy tất cả các kiểm tra kết nối."""
    logger.info("=== Testing Core Operations Service Connections ===\n")
    
    redis_result = test_redis_connection()
    firebase_result = test_firebase_connection()
    adafruit_result = test_adafruit_connection()
    
    logger.info("\n=== Connection Test Results ===")
    logger.info(f"Redis: {'✅ PASS' if redis_result else '❌ FAIL'}")
    logger.info(f"Firebase: {'✅ PASS' if firebase_result else '❌ FAIL'}")
    logger.info(f"Adafruit IO: {'✅ PASS' if adafruit_result else '❌ FAIL'}")
    
    all_passed = redis_result and firebase_result and adafruit_result
    
    if all_passed:
        logger.info("\n🎉 All connection tests PASSED!")
    else:
        logger.info("\n⚠️ Some connection tests FAILED. Please check the logs above.")
        
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)