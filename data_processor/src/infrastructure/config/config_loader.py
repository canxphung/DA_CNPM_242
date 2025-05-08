"""
Bộ tải cấu hình tập trung cho ứng dụng.
"""
import os
import logging
import json
from typing import Any, Dict, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigLoader:
    """
    Bộ tải và quản lý cấu hình tập trung.
    """
    
    def __init__(self, load_env: bool = True, env_file: Optional[str] = None):
        """
        Khởi tạo bộ tải cấu hình.
        
        Args:
            load_env: Tự động tải biến môi trường từ .env
            env_file: Đường dẫn đến tệp .env
        """
        self.config = {}
        
        # Tải biến môi trường
        if load_env:
            load_dotenv(dotenv_path=env_file)
            
        # Tải các tệp cấu hình
        self._load_all_configs()
        
    def _load_all_configs(self) -> None:
        """Tải tất cả các tệp cấu hình."""
        config_dir = os.path.join(os.getcwd(), 'config')
        
        # Kiểm tra thư mục cấu hình
        if not os.path.exists(config_dir):
            logger.warning(f"Config directory not found: {config_dir}")
            return
            
        # Tải cấu hình Adafruit
        adafruit_config_path = os.path.join(config_dir, 'adafruit_config.py')
        if os.path.exists(adafruit_config_path):
            from config.adafruit_config import ADAFRUIT_CONFIG
            self.config['adafruit'] = ADAFRUIT_CONFIG
            
        # Tải cấu hình Redis
        redis_config_path = os.path.join(config_dir, 'redis_config.py')
        if os.path.exists(redis_config_path):
            from config.redis_config import DEFAULT_EXPIRATION, KEY_PREFIXES
            self.config['redis'] = {
                'default_expiration': DEFAULT_EXPIRATION,
                'key_prefixes': KEY_PREFIXES
            }
            
        # Tải cấu hình Firebase
        firebase_config_path = os.path.join(config_dir, 'firebase_config.py')
        if os.path.exists(firebase_config_path):
            from config.firebase_config import DATABASE_STRUCTURE, SECURITY_RULES
            self.config['firebase'] = {
                'database_structure': DATABASE_STRUCTURE,
                'security_rules': SECURITY_RULES
            }
            
        logger.info(f"Loaded configuration modules: {', '.join(self.config.keys())}")
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Lấy giá trị cấu hình theo khóa.
        
        Args:
            key: Khóa cấu hình (ví dụ: 'adafruit.sensor_feeds.light')
            default: Giá trị mặc định nếu không tìm thấy
            
        Returns:
            Giá trị cấu hình
        """
        if not key:
            return default
            
        # Phân tách khóa thành các phần
        parts = key.split('.')
        
        # Duyệt qua cấu trúc cấu hình
        current = self.config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current
        
    def get_adafruit_credentials(self) -> Dict[str, str]:
        """
        Lấy thông tin đăng nhập Adafruit IO.
        
        Returns:
            Dict chứa username và key
        """
        return {
            'username': os.getenv('ADAFRUIT_IO_USERNAME', ''),
            'key': os.getenv('ADAFRUIT_IO_KEY', '')
        }
        
    def get_redis_connection_params(self) -> Dict[str, Any]:
        """
        Lấy thông số kết nối Redis.
        
        Returns:
            Dict chứa thông số kết nối
        """
        return {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'db': int(os.getenv('REDIS_DB', 0)),
            'password': os.getenv('REDIS_PASSWORD', None)
        }
        
    def get_firebase_credentials_path(self) -> str:
        """
        Lấy đường dẫn đến tệp thông tin đăng nhập Firebase.
        
        Returns:
            Đường dẫn đến tệp credentials
        """
        return os.getenv('FIREBASE_CREDENTIALS_PATH', './config/firebase-credentials.json')
        
    def get_firebase_database_url(self) -> str:
        """
        Lấy URL của Firebase Realtime Database.
        
        Returns:
            URL của database
        """
        return os.getenv('FIREBASE_DATABASE_URL', '')
        
    def get_sensor_feed_key(self, sensor_type: str) -> Optional[str]:
        """
        Lấy khóa feed của loại cảm biến.
        
        Args:
            sensor_type: Loại cảm biến (light, temperature, humidity, soil_moisture)
            
        Returns:
            Khóa feed hoặc None nếu không tìm thấy
        """
        return self.get(f'adafruit.sensor_feeds.{sensor_type}')
        
    def get_actuator_feed_key(self, actuator_type: str) -> Optional[str]:
        """
        Lấy khóa feed của loại thiết bị điều khiển.
        
        Args:
            actuator_type: Loại thiết bị điều khiển (water_pump)
            
        Returns:
            Khóa feed hoặc None nếu không tìm thấy
        """
        return self.get(f'adafruit.actuator_feeds.{actuator_type}')