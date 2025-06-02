
"""
Lớp cơ sở cho các bộ thu thập dữ liệu cảm biến.
"""
import logging
import time
from typing import Dict, Any, Optional, List, Union, Type, TypeVar, Generic
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
# Import json for use in get_recent_readings_from_cache, though Pydantic's parse_raw handles it.
# It's already used in get_recent_readings_from_cache.
import json 

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

         # Cache settings được tối ưu
        self.cache_ttl = 600  # 10 phút thay vì 1 giờ
        self.stale_threshold = 300  # 5 phút - data cũ nhưng vẫn dùng được
        self.max_stale_age = 900  # 15 phút - quá cũ, cần refresh
        
        # Rate limiting cho Adafruit calls
        self._last_adafruit_call = {}
        self._min_call_interval = 30  # Tối thiểu 30s giữa các calls
    
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
    
    def collect_latest_data(self, force_refresh: bool = False) -> Optional[SensorReading]:
        """
        Thu thập dữ liệu với Cache-First Strategy.
        
        Args:
            force_refresh: Bắt buộc lấy từ Adafruit (bỏ qua cache)
            
        Returns:
            SensorReading hoặc None
        """
        # Bước 1: Kiểm tra cache trước (trừ khi force_refresh)
        if not force_refresh:
            cached_reading = self.get_latest_reading_from_cache()
            
            if cached_reading:
                age = (datetime.now() - cached_reading.timestamp).total_seconds()
                
                # Nếu data còn fresh (< 5 phút), dùng luôn
                if age < self.stale_threshold:
                    logger.debug(f"Using fresh cached data for {self.sensor_type} (age: {age:.1f}s)")
                    return cached_reading
                    
                # Nếu data stale nhưng chưa quá cũ (5-15 phút)
                elif age < self.max_stale_age:
                    # Kiểm tra rate limiting
                    if self._should_refresh_from_adafruit():
                        # Thử refresh async (không block)
                        self._async_refresh_from_adafruit()
                    
                    # Vẫn trả về cached data (stale-while-revalidate)
                    logger.debug(f"Using stale cached data for {self.sensor_type} (age: {age:.1f}s)")
                    return cached_reading
        
        # Bước 2: Nếu không có cache hoặc quá cũ, lấy từ Adafruit
        return self._fetch_from_adafruit()
    
    def collect_latest_data_optimized(self, force_refresh: bool = False) -> Optional[SensorReading]:
        """
        Thu thập dữ liệu với Cache-First Strategy.
        
        Args:
            force_refresh: Bắt buộc lấy từ Adafruit (bỏ qua cache)
            
        Returns:
            SensorReading hoặc None
        """
        # Check cache first
        if not force_refresh:
            cached_reading = self.get_latest_reading_from_cache()
            
            if cached_reading:
                age = (datetime.now() - cached_reading.timestamp).total_seconds()
                
                # Fresh data (< 5 phút)
                if age < 300:
                    logger.debug(f"Cache hit for {self.sensor_type} (age: {age:.1f}s)")
                    return cached_reading
                
                # Stale but usable (5-10 phút)
                elif age < 600:
                    logger.debug(f"Using stale data for {self.sensor_type} (age: {age:.1f}s)")
                    # TODO: Trigger background refresh
                    return cached_reading
        
        # Cache miss hoặc force refresh
        return self._fetch_from_adafruit()
    
    def _should_refresh_from_adafruit(self) -> bool:
        """Kiểm tra xem có nên gọi Adafruit không (rate limiting)."""
        now = time.time()
        last_call = self._last_adafruit_call.get(self.sensor_type, 0)
        
        if now - last_call < self._min_call_interval:
            return False
            
        return True
    
    def _fetch_from_adafruit(self) -> Optional[SensorReading]:
        """
        Lấy dữ liệu từ Adafruit (helper method).
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
            
            # Lưu vào cache với TTL tùy chỉnh
            self._cache_reading(reading, ttl=600)  # 10 phút
            
            # Lưu vào storage
            self._store_reading(reading)
            
            return reading
            
        except Exception as e:
            logger.error(f"Error collecting data for {self.sensor_type}: {str(e)}")
            return None
        
    def _async_refresh_from_adafruit(self):
        """Refresh data từ Adafruit trong background (non-blocking)."""
        import threading
        
        def refresh_worker():
            try:
                self._fetch_from_adafruit()
            except Exception as e:
                logger.error(f"Background refresh failed for {self.sensor_type}: {e}")
        
        thread = threading.Thread(target=refresh_worker, daemon=True)
        thread.start()

    def get_latest_reading_from_cache(self) -> Optional[SensorReading]:
        """
        Lấy đọc cảm biến mới nhất từ cache.
        
        Returns:
            SensorReading hoặc None nếu không có trong cache
        """
        try:
            cache_key = f"{self.key_prefix}{self.sensor_type.value}:latest"
            # MODIFIED: Retrieve JSON string and parse it
            json_data = self.redis_client.get(cache_key) 
            
            if not json_data:
                return None
                
            # Xác định lớp con của SensorReading dựa trên sensor_type
            reading_class = self._get_reading_class()
            
            # FIX: json_data đã là string (không phải bytes) vì decode_responses=True trong RedisClient
            # Nên parse trực tiếp, không cần decode
            return reading_class.parse_raw(json_data)
            
        except Exception as e:
            logger.error(f"Error getting latest reading from cache for {self.sensor_type}: {str(e)}")
            return None
    
    def _cache_reading(self, reading: SensorReading, ttl: Optional[int] = None) -> bool:
        """
        Lưu đọc cảm biến vào cache.
        
        Args:
            reading: Đọc cảm biến cần lưu
            ttl: Time-to-live tùy chỉnh (giây)
            
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Tạo khóa Redis
            cache_key = f"{self.key_prefix}{self.sensor_type.value}:latest"
            
            # Sử dụng TTL tùy chỉnh hoặc mặc định
            expiration = ttl if ttl is not None else self.config.get('redis.default_expiration', 3600)
            
            # Store as JSON string
            self.redis_client.set(cache_key, reading.json(), expiration) 
            
            # Lưu vào danh sách lịch sử gần đây
            history_key = f"{self.key_prefix}{self.sensor_type.value}:history"
            self.redis_client.redis.lpush(history_key, reading.json())
            # Giữ chỉ 100 giá trị gần nhất
            self.redis_client.redis.ltrim(history_key, 0, 99)
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching reading for {self.sensor_type}: {str(e)}")
            return False
    
    def _async_store_reading(self, reading: SensorReading):
        """Store reading to Firebase async (non-blocking)."""
        import threading
        
        def store_worker():
            try:
                self._store_reading(reading)
            except Exception as e:
                logger.error(f"Background store failed for {self.sensor_type}: {e}")
        
        thread = threading.Thread(target=store_worker, daemon=True)
        thread.start()
    
    def collect_historical_data(self, limit: int = 10, use_cache: bool = True) -> List[SensorReading]:
        """Collect historical data với cache support."""
        # Thử lấy từ cache trước
        if use_cache:
            cached_history = self.get_recent_readings_from_cache(limit)
            if len(cached_history) >= limit:
                return cached_history
                
        # Nếu cache không đủ, lấy từ Adafruit
        if not self._should_refresh_from_adafruit():
            # Rate limited, trả về cache có sẵn
            return self.get_recent_readings_from_cache(limit)
            
        try:
            self._last_adafruit_call[self.sensor_type] = time.time()
            
            raw_data_list = self.adafruit_client.get_data(self.feed_key, limit)
            if not raw_data_list:
                return []
                
            readings = []
            for raw_data in raw_data_list:
                reading = self.process_raw_data(raw_data)
                readings.append(reading)
                
            # Cache tất cả readings
            for reading in readings:
                self._async_store_reading(reading)
                
            return readings
            
        except Exception as e:
            logger.error(f"Error collecting historical data for {self.sensor_type}: {str(e)}")
            return self.get_recent_readings_from_cache(limit)
    
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
            # MODIFIED: Store as JSON string to ensure datetime is serialized correctly
            self.redis_client.set(cache_key, reading.json(), expiration) 
            
            # Lưu vào danh sách lịch sử gần đây (already stores as JSON string)
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
    
    # def get_latest_reading_from_cache(self) -> Optional[SensorReading]:
    #     """
    #     Lấy đọc cảm biến mới nhất từ cache.
        
    #     Returns:
    #         SensorReading hoặc None nếu không có trong cache
    #     """
    #     try:
    #         cache_key = f"{self.key_prefix}{self.sensor_type.value}:latest"
    #         # MODIFIED: Retrieve JSON string and parse it
    #         json_data = self.redis_client.get(cache_key) 
            
    #         if not json_data:
    #             return None
                
    #         # Xác định lớp con của SensorReading dựa trên sensor_type
    #         reading_class = self._get_reading_class()
            
    #         # Tạo đối tượng từ dữ liệu JSON thô
    #         # Pydantic's parse_raw method can deserialize a JSON string into a model instance
    #         return reading_class.parse_raw(json_data)
            
    #     except Exception as e:
    #         logger.error(f"Error getting latest reading from cache for {self.sensor_type}: {str(e)}")
    #         return None
    
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
            # lrange returns a list of strings (JSON strings in this case)
            data_list = self.redis_client.redis.lrange(history_key, 0, limit - 1)
            
            if not data_list:
                return []
                
            # Xác định lớp con của SensorReading dựa trên sensor_type
            reading_class = self._get_reading_class()
            
            # Tạo danh sách đối tượng từ dữ liệu
            readings = []
            for data_json in data_list:
                # FIX: Check if data_json is bytes or string
                if isinstance(data_json, bytes):
                    data_json_str = data_json.decode('utf-8')
                else:
                    data_json_str = data_json
                
                # Parse JSON string to dict
                data = json.loads(data_json_str)
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
