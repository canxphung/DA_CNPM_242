"""
Lớp cơ sở cho các bộ thu thập dữ liệu cảm biến.
"""
import logging
import time
from typing import Dict, Any, Optional, List, Union, Type, TypeVar, Generic
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from src.core.data.models import (
    SensorReading, 
    SensorType, 
    SensorStatus
)
# Tránh circular import
# from src.infrastructure import ServiceFactory
from src.infrastructure.database import RedisClient, FirebaseClient
from src.adapters.cloud.adafruit import AdafruitIOClient

logger = logging.getLogger(__name__)

# Định nghĩa generic type cho class BaseCollector
T = TypeVar('T', bound=SensorReading)

class BaseCollector(Generic[T], ABC):
    """
    Lớp cơ sở trừu tượng cho các bộ thu thập dữ liệu cảm biến.
    """
    
    def __init__(self, sensor_type: SensorType):
        """
        Khởi tạo bộ thu thập.
        
        Args:
            sensor_type: Loại cảm biến
        """
        self.sensor_type = sensor_type
        
        # Khởi tạo các services (lazy import để tránh circular import)
        from src.infrastructure import get_service_factory
        factory = get_service_factory()
        self.config = factory.get_config_loader()
        self.adafruit_client = factory.create_adafruit_client()
        self.redis_client = factory.create_redis_client()
        self.firebase_client = factory.create_firebase_client("sensor_data")
        
        # Lấy khóa feed từ cấu hình
        self.feed_key = self.config.get_sensor_feed_key(sensor_type.value)
        if not self.feed_key:
            logger.warning(f"No feed key configured for sensor type: {sensor_type}")
            
        # Lấy cấu hình key prefix từ Redis
        self.key_prefix = self.config.get('redis.key_prefixes.sensor_data', 'sensor:')
        
        logger.info(f"Initialized {self.__class__.__name__} for sensor type: {sensor_type}")
    
    def parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """
        Chuyển đổi chuỗi timestamp từ Adafruit thành đối tượng datetime.
        Hỗ trợ nhiều định dạng ISO 8601 khác nhau.
        
        Args:
            timestamp_str: Chuỗi thời gian từ Adafruit
            
        Returns:
            datetime: Đối tượng datetime đã chuyển đổi hoặc thời gian hiện tại nếu lỗi
        """
        if not timestamp_str:
            return datetime.now()
            
        try:
            # Xử lý các định dạng ISO khác nhau
            timestamp_str = timestamp_str.replace('Z', '+00:00')
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_str}': {str(e)}")
            return datetime.now()
    
    def parse_value(self, raw_value: Any) -> tuple[float, str]:
        """
        Chuyển đổi giá trị thô thành số thực và chuỗi.
        
        Args:
            raw_value: Giá trị thô từ Adafruit
            
        Returns:
            tuple: (giá trị số thực, chuỗi gốc)
        """
        # Đảm bảo raw_value là string
        str_value = str(raw_value) if raw_value is not None else "0"
        
        try:
            # Chuyển đổi thành số thực
            float_value = float(str_value)
            return float_value, str_value
        except (ValueError, TypeError):
            logger.warning(f"Could not convert sensor value to float: {str_value}")
            return 0.0, str_value
    
    @abstractmethod
    def process_raw_data(self, raw_data: Dict[str, Any]) -> T:
        """
        Xử lý dữ liệu thô từ Adafruit thành model SensorReading.
        
        Args:
            raw_data: Dữ liệu thô từ Adafruit
            
        Returns:
            T: Dữ liệu đã xử lý (lớp con của SensorReading)
        """
        pass
    
    def collect_latest_data(self) -> Optional[SensorReading]:
        """
        Thu thập dữ liệu mới nhất từ cảm biến.
        
        Returns:
            SensorReading hoặc None nếu không thể thu thập dữ liệu
        """
        if not self.feed_key:
            logger.error(f"Cannot collect data: No feed key configured for {self.sensor_type}")
            return None
            
        try:
            # Lấy dữ liệu mới nhất từ Adafruit
            raw_data = self.adafruit_client.get_last_data(self.feed_key)
            if not raw_data:
                logger.warning(f"No data available for feed: {self.feed_key}")
                return None
                
            # Xử lý dữ liệu thô
            reading = self.process_raw_data(raw_data)
            
            # Lưu vào cache
            self._cache_reading(reading)
            
            # Lưu vào storage
            self._store_reading(reading)
            
            return reading
            
        except Exception as e:
            logger.error(f"Error collecting data for {self.sensor_type}: {str(e)}")
            return None
    
    def collect_historical_data(self, limit: int = 10) -> List[SensorReading]:
        """
        Thu thập dữ liệu lịch sử từ cảm biến.
        
        Args:
            limit: Số lượng điểm dữ liệu tối đa
            
        Returns:
            List các SensorReading
        """
        if not self.feed_key:
            logger.error(f"Cannot collect data: No feed key configured for {self.sensor_type}")
            return []
            
        try:
            # Lấy dữ liệu lịch sử từ Adafruit
            raw_data_list = self.adafruit_client.get_data(self.feed_key, limit)
            if not raw_data_list:
                logger.warning(f"No historical data available for feed: {self.feed_key}")
                return []
                
            # Xử lý từng điểm dữ liệu
            readings = []
            for raw_data in raw_data_list:
                reading = self.process_raw_data(raw_data)
                readings.append(reading)
                
            return readings
            
        except Exception as e:
            logger.error(f"Error collecting historical data for {self.sensor_type}: {str(e)}")
            return []
    
    def _cache_reading(self, reading: SensorReading) -> bool:
        """
        Lưu đọc cảm biến vào cache.
        
        Args:
            reading: Đọc cảm biến cần lưu
            
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Tạo khóa Redis
            cache_key = f"{self.key_prefix}{self.sensor_type.value}:latest"
            
            # Lưu giá trị với thời gian hết hạn
            expiration = self.config.get('redis.default_expiration', 3600)  # 1 giờ mặc định
            self.redis_client.set(cache_key, reading.dict(), expiration)
            
            # Lưu vào danh sách lịch sử gần đây
            history_key = f"{self.key_prefix}{self.sensor_type.value}:history"
            self.redis_client.redis.lpush(history_key, reading.json())
            # Giữ chỉ 100 giá trị gần nhất
            self.redis_client.redis.ltrim(history_key, 0, 99)
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching reading for {self.sensor_type}: {str(e)}")
            return False
    
    def _store_reading(self, reading: SensorReading) -> bool:
        """
        Lưu đọc cảm biến vào storage dài hạn.
        
        Args:
            reading: Đọc cảm biến cần lưu
            
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Lưu vào Firebase
            data = reading.dict()
            # Chuyển đổi datetime thành ISO string
            if isinstance(data.get('timestamp'), datetime):
                data['timestamp'] = data['timestamp'].isoformat()
                
            self.firebase_client.store_sensor_data(self.sensor_type.value, data)
            return True
            
        except Exception as e:
            logger.error(f"Error storing reading for {self.sensor_type}: {str(e)}")
            return False
    
    def get_latest_reading_from_cache(self) -> Optional[SensorReading]:
        """
        Lấy đọc cảm biến mới nhất từ cache.
        
        Returns:
            SensorReading hoặc None nếu không có trong cache
        """
        try:
            cache_key = f"{self.key_prefix}{self.sensor_type.value}:latest"
            data = self.redis_client.get(cache_key)
            
            if not data:
                return None
                
            # Xác định lớp con của SensorReading dựa trên sensor_type
            reading_class = self._get_reading_class()
            
            # Tạo đối tượng từ dữ liệu
            return reading_class(**data)
            
        except Exception as e:
            logger.error(f"Error getting latest reading from cache for {self.sensor_type}: {str(e)}")
            return None
    
    def get_recent_readings_from_cache(self, limit: int = 10) -> List[SensorReading]:
        """
        Lấy các đọc cảm biến gần đây từ cache.
        
        Args:
            limit: Số lượng điểm dữ liệu tối đa
            
        Returns:
            List các SensorReading
        """
        try:
            history_key = f"{self.key_prefix}{self.sensor_type.value}:history"
            data_list = self.redis_client.redis.lrange(history_key, 0, limit - 1)
            
            if not data_list:
                return []
                
            # Xác định lớp con của SensorReading dựa trên sensor_type
            reading_class = self._get_reading_class()
            
            # Tạo danh sách đối tượng từ dữ liệu
            readings = []
            for data_json in data_list:
                import json
                data = json.loads(data_json)
                readings.append(reading_class(**data))
                
            return readings
            
        except Exception as e:
            logger.error(f"Error getting recent readings from cache for {self.sensor_type}: {str(e)}")
            return []
    
    def _get_reading_class(self) -> Type[SensorReading]:
        """
        Lấy lớp con của SensorReading dựa trên sensor_type.
        
        Returns:
            Type[SensorReading]: Lớp con tương ứng
        """
        from src.core.data.models import (
            LightReading,
            TemperatureReading,
            HumidityReading,
            SoilMoistureReading
        )
        
        mapping = {
            SensorType.LIGHT: LightReading,
            SensorType.TEMPERATURE: TemperatureReading,
            SensorType.HUMIDITY: HumidityReading,
            SensorType.SOIL_MOISTURE: SoilMoistureReading
        }
        
        return mapping.get(self.sensor_type, SensorReading)