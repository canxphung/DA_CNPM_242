"""
Quản lý cấu hình tập trung cho hệ thống.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from src.infrastructure.exceptions import ConfigurationError
from ..factory import ServiceFactory

logger = logging.getLogger(__name__)

class SystemConfigManager:
    """
    Quản lý cấu hình tập trung cho hệ thống.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(SystemConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo SystemConfigManager."""
        if self._initialized:
            return
            
        logger.info("Initializing SystemConfigManager")
        
        # Khởi tạo các services
        factory = ServiceFactory()
        self.redis_client = factory.create_redis_client()
        self.firebase_client = factory.create_firebase_client("system_config")
        self.config_loader = factory.get_config_loader()
        
        # Khóa Redis cho cấu hình hệ thống
        self.redis_config_key = "system:config"
        
        # Cấu hình mặc định
        self._default_config = {
            "system": {
                "name": "Core Operations Service",
                "version": os.getenv("API_VERSION", "0.1.0"),
                "environment": os.getenv("ENVIRONMENT", "development"),
                "log_level": "INFO"
            },
            "data_collection": {
                "enabled": True,
                "interval": 60,
                "storage_days": 30
            },
            "sensors": {
                "light": {
                    "enabled": True,
                    "thresholds": {
                        "min": 200.0,
                        "max": 10000.0,
                        "optimal_min": 1000.0,
                        "optimal_max": 7000.0
                    }
                },
                "temperature": {
                    "enabled": True,
                    "thresholds": {
                        "min": 10.0,
                        "max": 40.0,
                        "optimal_min": 18.0,
                        "optimal_max": 30.0
                    }
                },
                "humidity": {
                    "enabled": True,
                    "thresholds": {
                        "min": 30.0,
                        "max": 90.0,
                        "optimal_min": 40.0,
                        "optimal_max": 70.0
                    }
                },
                "soil_moisture": {
                    "enabled": True,
                    "thresholds": {
                        "min": 20.0,
                        "max": 90.0,
                        "optimal_min": 40.0,
                        "optimal_max": 70.0
                    }
                }
            },
            "irrigation": {
                "pump": {
                    "max_runtime": 1800,
                    "min_interval": 3600,
                    "water_rate": 0.5
                },
                "auto": {
                    "enabled": False,
                    "min_decision_interval": 3600,
                    "moisture_thresholds": {
                        "critical": 20.0,
                        "low": 30.0,
                        "optimal": 50.0
                    },
                    "watering_durations": {
                        "light": 60,
                        "normal": 180,
                        "heavy": 300
                    }
                },
                "scheduler": {
                    "enabled": True,
                    "check_interval": 60
                }
            }
        }
        
        # Cấu hình hiện tại
        self._config = self._default_config.copy()
        
        # Tải cấu hình
        self._load_config()
        
        self._initialized = True
        logger.info("SystemConfigManager initialized")
    
    def _load_config(self) -> None:
        """Tải cấu hình từ Redis và Firebase."""
        try:
            # Thử tải từ Redis trước
            redis_config = self.redis_client.get(self.redis_config_key)
            
            if redis_config:
                logger.info("Loaded system config from Redis")
                self._config.update(redis_config)
                return
                
            # Nếu không có trong Redis, tải từ Firebase
            firebase_config = self.firebase_client.get("config")
            
            if firebase_config:
                logger.info("Loaded system config from Firebase")
                self._config.update(firebase_config)
                
                # Lưu vào Redis
                self.redis_client.set(self.redis_config_key, self._config)
                
        except Exception as e:
            logger.error(f"Error loading system config: {str(e)}")
            # Sử dụng cấu hình mặc định
            logger.warning("Using default system config")
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình hiện tại.
        
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Thêm timestamp
            self._config["_last_updated"] = datetime.now().isoformat()
            
            # Lưu vào Redis
            self.redis_client.set(self.redis_config_key, self._config)
            
            # Lưu vào Firebase
            self.firebase_client.set("config", self._config)
            
            logger.info("Saved system config")
            return True
        except Exception as e:
            logger.error(f"Error saving system config: {str(e)}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """
        Lấy toàn bộ cấu hình hệ thống.
        
        Returns:
            Dict: Cấu hình hệ thống
        """
        return self._config.copy()
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Lấy giá trị cấu hình theo đường dẫn.
        
        Args:
            path: Đường dẫn đến giá trị (ví dụ: "irrigation.auto.enabled")
            default: Giá trị mặc định nếu không tìm thấy
            
        Returns:
            Giá trị cấu hình
        """
        if not path:
            return default
            
        # Phân tách đường dẫn
        parts = path.split(".")
        
        # Duyệt qua cấu trúc cấu hình
        current = self._config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current
    
    def set(self, path: str, value: Any) -> bool:
        """
        Đặt giá trị cấu hình theo đường dẫn.
        
        Args:
            path: Đường dẫn đến giá trị (ví dụ: "irrigation.auto.enabled")
            value: Giá trị mới
            
        Returns:
            bool: Thành công hay thất bại
        """
        if not path:
            raise ConfigurationError("Configuration path cannot be empty")
            
        # Phân tách đường dẫn
        parts = path.split(".")
        
        # Tìm vị trí cần đặt giá trị
        current = self._config
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                # Tạo cấu trúc nếu chưa tồn tại
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Không thể đặt giá trị vào không phải dict
                raise ConfigurationError(
                    f"Cannot set configuration at '{path}': '{'.'.join(parts[:i+1])}' is not a dictionary"
                )
                
            current = current[part]
            
        # Đặt giá trị
        current[parts[-1]] = value
        
        # Lưu cấu hình
        return self.save_config()
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """
        Cập nhật nhiều giá trị cấu hình.
        
        Args:
            updates: Dict chứa các cập nhật dạng {path: value}
            
        Returns:
            bool: Thành công hay thất bại
        """
        success = True
        
        for path, value in updates.items():
            try:
                # Đặt từng giá trị nhưng không lưu ngay
                if not path:
                    continue
                    
                # Phân tách đường dẫn
                parts = path.split(".")
                
                # Tìm vị trí cần đặt giá trị
                current = self._config
                for i, part in enumerate(parts[:-1]):
                    if part not in current:
                        # Tạo cấu trúc nếu chưa tồn tại
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        # Không thể đặt giá trị vào không phải dict
                        raise ConfigurationError(
                            f"Cannot set configuration at '{path}': '{'.'.join(parts[:i+1])}' is not a dictionary"
                        )
                        
                    current = current[part]
                    
                # Đặt giá trị
                current[parts[-1]] = value
                
            except Exception as e:
                logger.error(f"Error updating config at '{path}': {str(e)}")
                success = False
                
        # Lưu cấu hình nếu có thay đổi thành công
        if success:
            return self.save_config()
            
        return success
    
    def reset(self, path: Optional[str] = None) -> bool:
        """
        Đặt lại cấu hình về mặc định.
        
        Args:
            path: Đường dẫn cấu hình cần đặt lại (nếu là None thì đặt lại tất cả)
            
        Returns:
            bool: Thành công hay thất bại
        """
        if path is None:
            # Đặt lại toàn bộ cấu hình
            self._config = self._default_config.copy()
            return self.save_config()
            
        # Phân tách đường dẫn
        parts = path.split(".")
        
        # Tìm giá trị mặc định
        default_value = None
        current_default = self._default_config
        
        for part in parts:
            if isinstance(current_default, dict) and part in current_default:
                current_default = current_default[part]
            else:
                # Không tìm thấy đường dẫn trong cấu hình mặc định
                logger.warning(f"Path '{path}' not found in default configuration")
                return False
                
        # Đặt giá trị về mặc định
        return self.set(path, current_default)