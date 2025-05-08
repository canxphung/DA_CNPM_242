"""
Factory để khởi tạo các thành phần chính của ứng dụng.
"""
import logging
import os
from typing import Dict, Optional
from .config.config_loader import ConfigLoader
from .database import RedisClient, FirebaseClient
from src.adapters.cloud.adafruit import AdafruitIOClient
from .database.connections import get_redis_client, get_firebase_db_reference

logger = logging.getLogger(__name__)

class ServiceFactory:
    """
    Factory để khởi tạo và quản lý các service dependencies.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ServiceFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo factory nếu chưa được khởi tạo."""
        if self._initialized:
            return
            
        logger.info("Initializing ServiceFactory")
        self.config_loader = ConfigLoader()
        self.services = {}
        self._initialized = True
        
    def get_config_loader(self) -> ConfigLoader:
        """
        Lấy instance của ConfigLoader.
        
        Returns:
            ConfigLoader instance
        """
        return self.config_loader
        
    def create_redis_client(self) -> RedisClient:
        """
        Tạo và trả về RedisClient.
        
        Returns:
            RedisClient instance
        """
        if 'redis_client' not in self.services:
            # Sử dụng hàm get_redis_client từ connections.py thay vì tạo mới
            self.services['redis_client'] = get_redis_client()
            logger.info("Created Redis client")
        return self.services['redis_client']
        
    def create_firebase_client(self, base_path: str = "") -> FirebaseClient:
        """
        Tạo và trả về FirebaseClient.
        
        Args:
            base_path: Đường dẫn cơ sở trong database
            
        Returns:
            FirebaseClient instance
        """
        service_key = f'firebase_client_{base_path}'
        if service_key not in self.services:
            # Đảm bảo base_path là chuỗi, không phải None
            if base_path is None:
                base_path = ""
                
            # Kiểm tra xem Firebase app đã được khởi tạo chưa (qua get_firebase_db_reference)
            # Sử dụng chuỗi rỗng cho path mặc định
            _ = get_firebase_db_reference("")
            
            # Sau khi đảm bảo Firebase đã được khởi tạo, tạo client
            self.services[service_key] = FirebaseClient(base_path)
            logger.info(f"Created Firebase client with base path: '{base_path}'")
        return self.services[service_key]
        
    def create_adafruit_client(self) -> AdafruitIOClient:
        """
        Tạo và trả về AdafruitIOClient.
        
        Returns:
            AdafruitIOClient instance
        """
        if 'adafruit_client' not in self.services:
            credentials = self.config_loader.get_adafruit_credentials()
            self.services['adafruit_client'] = AdafruitIOClient(
                username=credentials['username'],
                key=credentials['key']
            )
            logger.info("Created Adafruit IO client")
        return self.services['adafruit_client']
        
    def init_all_services(self) -> None:
        """Khởi tạo tất cả các service."""
        # Không gọi init_database_connections() ở đây nữa vì nó đã được gọi trong lifespan
        self.create_redis_client()
        self.create_firebase_client()
        self.create_adafruit_client()
        logger.info("All services initialized")