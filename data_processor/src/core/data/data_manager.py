"""
Quản lý thu thập dữ liệu từ tất cả các cảm biến.
"""
from concurrent.futures import ThreadPoolExecutor
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.core.data.models import (
    HumidityReading,
    LightReading,
    SensorType,
    SensorStatus,
    SensorReading,
    EnvironmentSnapshot,
    SoilMoistureReading,
    TemperatureReading
)
from src.core.data.collectors import (
    LightCollector,
    TemperatureCollector,
    HumidityCollector,
    SoilMoistureCollector
)

logger = logging.getLogger(__name__)

class DataManager:
    """
    Quản lý thu thập dữ liệu từ tất cả các cảm biến và tạo snapshot của môi trường.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo DataManager."""
        if self._initialized:
            return
            
        logger.info("Initializing DataManager")
        
        # Khởi tạo factory và config (lazy import để tránh circular import)
        from src.infrastructure import get_service_factory
        factory = get_service_factory()
        self.config = factory.get_config_loader()
        self.redis_client = factory.create_redis_client()
        
        # Khởi tạo các collectors
        self.collectors = {
            SensorType.LIGHT: LightCollector(),
            SensorType.TEMPERATURE: TemperatureCollector(),
            SensorType.HUMIDITY: HumidityCollector(),
            SensorType.SOIL_MOISTURE: SoilMoistureCollector()
        }
        
        # Biến theo dõi trạng thái
        self.last_collection_time = {
            SensorType.LIGHT: None,
            SensorType.TEMPERATURE: None,
            SensorType.HUMIDITY: None,
            SensorType.SOIL_MOISTURE: None
        }
        
        # Cấu hình cho dữ liệu cũ
        self.max_data_age = self.config.get('data.max_age_seconds', 300)  # Dữ liệu cũ sau 5 phút
        
        self.collection_lock = threading.Lock()
        self.background_thread = None
        self.is_collecting = False
        self.collection_interval = 60  # Mặc định: 60 giây

        self._snapshot_cache_key = "environment:snapshot:latest"
        self._snapshot_cache_ttl = 120  # 2 phút
        
        self._initialized = True
        logger.info(f"DataManager initialized (max_data_age: {self.max_data_age}s)")
    
    def collect_all_latest_data(self) -> Dict[SensorType, SensorReading]:
        """
        Thu thập dữ liệu mới nhất từ tất cả các cảm biến.
        
        Returns:
            Dict mapping sensor type to sensor reading
        """
        with self.collection_lock:
            results = {}
            
            for sensor_type, collector in self.collectors.items():
                try:
                    reading = collector.collect_latest_data()
                    if reading:
                        results[sensor_type] = reading
                        self.last_collection_time[sensor_type] = datetime.now()
                except Exception as e:
                    logger.error(f"Error collecting data from {sensor_type}: {str(e)}")
                    
            return results
    
    def is_data_stale(self, reading: Optional[SensorReading]) -> bool:
        """
        Kiểm tra xem dữ liệu có quá cũ không.
        
        Args:
            reading: Đọc từ cảm biến cần kiểm tra
            
        Returns:
            bool: True nếu dữ liệu quá cũ hoặc không tồn tại
        """
        if not reading or not reading.timestamp:
            return True
            
        # Tính thời gian đã trôi qua kể từ khi đọc
        time_diff = (datetime.now() - reading.timestamp).total_seconds()
        return time_diff > self.max_data_age
    
    def get_latest_readings(self) -> Dict[SensorType, SensorReading]:
        """
        Lấy giá trị mới nhất từ cache cho tất cả các cảm biến.
        
        Returns:
            Dict mapping sensor type to sensor reading
        """
        results = {}
        
        for sensor_type, collector in self.collectors.items():
            try:
                reading = collector.get_latest_reading_from_cache()
                if reading and not self.is_data_stale(reading):
                    results[sensor_type] = reading
                    # Cập nhật thời gian đọc gần nhất
                    self.last_collection_time[sensor_type] = reading.timestamp
                else:
                    logger.debug(f"No valid reading for {sensor_type} in cache or data is stale")
            except Exception as e:
                logger.error(f"Error getting latest reading for {sensor_type}: {str(e)}")
                
        return results
    
    def get_environment_snapshot(self, collect_if_needed: bool = True, 
                           force_collection: bool = False) -> EnvironmentSnapshot:
        """
        Lấy snapshot với caching.
        """
        from src.infrastructure.monitoring.performance_monitor import monitor_performance
        
        # Check snapshot cache first
        if not force_collection:
            cached = self._get_cached_snapshot()
            if cached:
                return cached
        
        # Lấy từ individual collectors (sẽ dùng cache của chúng)
        with self.collection_lock:
            readings = {}
            missing = []
            
            for sensor_type, collector in self.collectors.items():
                reading = collector.get_latest_reading_from_cache()
                
                if reading:
                    age = (datetime.now() - reading.timestamp).total_seconds()
                    if age < 600:  # 10 phút
                        readings[sensor_type] = reading
                    else:
                        missing.append(sensor_type)
                else:
                    missing.append(sensor_type)
            
            # Chỉ collect missing sensors nếu cần
            if missing and collect_if_needed:
                logger.info(f"Collecting missing sensors: {missing}")
                for sensor_type in missing:
                    reading = self.collectors[sensor_type].collect_latest_data()
                    if reading:
                        readings[sensor_type] = reading
        
        # Create snapshot
        snapshot = EnvironmentSnapshot(
            timestamp=datetime.now(),
            light=readings.get(SensorType.LIGHT),
            temperature=readings.get(SensorType.TEMPERATURE),
            humidity=readings.get(SensorType.HUMIDITY),
            soil_moisture=readings.get(SensorType.SOIL_MOISTURE)
        )
        
        # Cache snapshot
        self._cache_snapshot(snapshot)
        
        return snapshot
    def _get_cached_snapshot(self) -> Optional[EnvironmentSnapshot]:
        """Get cached snapshot."""
        try:
            data = self.redis_client.get(self._snapshot_cache_key)
            if not data:
                return None
                
            # Recreate snapshot
            snapshot = EnvironmentSnapshot(
                timestamp=datetime.fromisoformat(data['timestamp']),
                light=LightReading(**data['light']) if data.get('light') else None,
                temperature=TemperatureReading(**data['temperature']) if data.get('temperature') else None,
                humidity=HumidityReading(**data['humidity']) if data.get('humidity') else None,
                soil_moisture=SoilMoistureReading(**data['soil_moisture']) if data.get('soil_moisture') else None
            )
            
            # Check age
            age = (datetime.now() - snapshot.timestamp).total_seconds()
            if age < self._snapshot_cache_ttl:
                logger.debug(f"Using cached snapshot (age: {age:.1f}s)")
                return snapshot
                
        except Exception as e:
            logger.error(f"Error getting cached snapshot: {e}")
        
        return None
    def _cache_snapshot(self, snapshot: EnvironmentSnapshot):
        """Cache snapshot."""
        try:
            data = {
                'timestamp': snapshot.timestamp.isoformat(),
                'light': snapshot.light.dict() if snapshot.light else None,
                'temperature': snapshot.temperature.dict() if snapshot.temperature else None,
                'humidity': snapshot.humidity.dict() if snapshot.humidity else None,
                'soil_moisture': snapshot.soil_moisture.dict() if snapshot.soil_moisture else None
            }
            
            self.redis_client.set(
                self._snapshot_cache_key,
                data,
                expire=self._snapshot_cache_ttl
            )
        except Exception as e:
            logger.error(f"Error caching snapshot: {e}")
    def start_background_collection(self, interval: int = None) -> bool:
        """Start background collection với dynamic interval."""
        if self.is_collecting:
            return False
            
        self.is_collecting = True
        
        def collection_worker():
            from config.intervals_config import get_dynamic_interval
            
            logger.info("Starting optimized background collection")
            
            while self.is_collecting:
                try:
                    # Get dynamic interval
                    current_interval = interval or get_dynamic_interval("sensor_data")
                    logger.debug(f"Using interval: {current_interval}s")
                    
                    # Collect với cache-first strategy
                    start = time.time()
                    
                    # Không force refresh, dùng cache
                    snapshot = self.get_environment_snapshot(
                        collect_if_needed=True,
                        force_collection=False
                    )
                    
                    duration = time.time() - start
                    if duration > 2.0:
                        logger.warning(f"Slow collection: {duration:.2f}s")
                    
                except Exception as e:
                    logger.error(f"Collection error: {e}")
                    
                # Sleep với dynamic interval
                for _ in range(current_interval):
                    if not self.is_collecting:
                        break
                    time.sleep(1)
        
        self.background_thread = threading.Thread(target=collection_worker, daemon=True)
        self.background_thread.start()
        
        return True
    
    def stop_background_collection(self) -> bool:
        """
        Dừng thu thập dữ liệu ngầm.
        
        Returns:
            bool: Thành công hay thất bại
        """
        if not self.is_collecting:
            logger.warning("Background collection is not running")
            return False
            
        self.is_collecting = False
        
        if self.background_thread:
            self.background_thread.join(timeout=5.0)
            
        logger.info("Background data collection stopped")
        return True

# logger = logging.getLogger(__name__)

class OptimizedDataManager:
    """
    Quản lý thu thập dữ liệu tối ưu với batching và smart caching.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OptimizedDataManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        logger.info("Initializing OptimizedDataManager")
        
        # Initialize services
        from src.infrastructure import get_service_factory
        factory = get_service_factory()
        self.config = factory.get_config_loader()
        
        # Initialize collectors
        self.collectors = {
            SensorType.LIGHT: LightCollector(),
            SensorType.TEMPERATURE: TemperatureCollector(),
            SensorType.HUMIDITY: HumidityCollector(),
            SensorType.SOIL_MOISTURE: SoilMoistureCollector()
        }
        
        # Cache settings
        self.snapshot_cache_key = "environment:snapshot:latest"
        self.snapshot_cache_ttl = 120  # 2 phút cho snapshot
        
        # Batch collection settings
        self.batch_collection_enabled = True
        self.max_parallel_collections = 2  # Giới hạn số request song song
        
        # Background collection settings
        self.collection_lock = threading.Lock()
        self.background_thread = None
        self.is_collecting = False
        
        # Smart collection intervals
        self.base_collection_interval = 180  # 3 phút thay vì 60s
        self.peak_hours_interval = 120  # 2 phút trong giờ cao điểm
        self.off_hours_interval = 300  # 5 phút ngoài giờ cao điểm
        
        # Collection statistics
        self.collection_stats = {
            "total_collections": 0,
            "cache_hits": 0,
            "adafruit_calls": 0,
            "last_collection": None
        }
        
        # Redis client for caching
        self.redis_client = factory.create_redis_client()
        
        self._initialized = True
        logger.info("OptimizedDataManager initialized")
    
    def get_environment_snapshot(
        self, 
        collect_if_needed: bool = True,
        force_collection: bool = False,
        use_cache: bool = True
    ) -> EnvironmentSnapshot:
        """
        Lấy snapshot với smart caching.
        
        Args:
            collect_if_needed: Thu thập nếu cache cũ
            force_collection: Bắt buộc thu thập mới
            use_cache: Sử dụng cache
            
        Returns:
            EnvironmentSnapshot
        """
        # Bước 1: Check snapshot cache first
        if use_cache and not force_collection:
            cached_snapshot = self._get_cached_snapshot()
            if cached_snapshot:
                self.collection_stats["cache_hits"] += 1
                return cached_snapshot
        
        # Bước 2: Lấy từ individual sensor caches
        readings = {}
        missing_sensors = []
        
        with self.collection_lock:
            for sensor_type, collector in self.collectors.items():
                reading = collector.get_latest_reading_from_cache()
                
                if reading:
                    # Kiểm tra tuổi của data
                    age = (datetime.now() - reading.timestamp).total_seconds()
                    if age < 600:  # 10 phút
                        readings[sensor_type] = reading
                    else:
                        missing_sensors.append(sensor_type)
                else:
                    missing_sensors.append(sensor_type)
        
        # Bước 3: Thu thập data còn thiếu nếu cần
        if missing_sensors and (collect_if_needed or force_collection):
            new_readings = self._batch_collect_sensors(missing_sensors)
            readings.update(new_readings)
        
        # Bước 4: Tạo snapshot
        snapshot = EnvironmentSnapshot(
            timestamp=datetime.now(),
            light=readings.get(SensorType.LIGHT),
            temperature=readings.get(SensorType.TEMPERATURE),
            humidity=readings.get(SensorType.HUMIDITY),
            soil_moisture=readings.get(SensorType.SOIL_MOISTURE)
        )
        
        # Bước 5: Cache snapshot
        if use_cache:
            self._cache_snapshot(snapshot)
        
        return snapshot
    
    def _get_cached_snapshot(self) -> Optional[EnvironmentSnapshot]:
        """Lấy snapshot từ cache."""
        try:
            data = self.redis_client.get(self.snapshot_cache_key)
            if data:
                # Recreate snapshot from cached data
                snapshot = EnvironmentSnapshot(
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    light=LightReading(**data['light']) if data.get('light') else None,
                    temperature=TemperatureReading(**data['temperature']) if data.get('temperature') else None,
                    humidity=HumidityReading(**data['humidity']) if data.get('humidity') else None,
                    soil_moisture=SoilMoistureReading(**data['soil_moisture']) if data.get('soil_moisture') else None
                )
                
                # Kiểm tra tuổi của snapshot
                age = (datetime.now() - snapshot.timestamp).total_seconds()
                if age < self.snapshot_cache_ttl:
                    return snapshot
                    
            return None
        except Exception as e:
            logger.error(f"Error getting cached snapshot: {e}")
            return None
    
    def _cache_snapshot(self, snapshot: EnvironmentSnapshot):
        """Cache snapshot."""
        try:
            # Convert to cacheable format
            data = {
                'timestamp': snapshot.timestamp.isoformat(),
                'light': snapshot.light.dict() if snapshot.light else None,
                'temperature': snapshot.temperature.dict() if snapshot.temperature else None,
                'humidity': snapshot.humidity.dict() if snapshot.humidity else None,
                'soil_moisture': snapshot.soil_moisture.dict() if snapshot.soil_moisture else None
            }
            
            self.redis_client.set(
                self.snapshot_cache_key,
                data,
                expire=self.snapshot_cache_ttl
            )
        except Exception as e:
            logger.error(f"Error caching snapshot: {e}")
    
    def _batch_collect_sensors(
        self, 
        sensor_types: List[SensorType]
    ) -> Dict[SensorType, SensorReading]:
        """
        Thu thập dữ liệu từ nhiều sensors với batching.
        
        Args:
            sensor_types: Danh sách sensor types cần thu thập
            
        Returns:
            Dict mapping sensor type to reading
        """
        results = {}
        
        # Nếu batch collection bị tắt, collect tuần tự
        if not self.batch_collection_enabled:
            for sensor_type in sensor_types:
                if sensor_type in self.collectors:
                    reading = self.collectors[sensor_type].collect_latest_data()
                    if reading:
                        results[sensor_type] = reading
            return results
        
        # Batch collection với thread pool
        with ThreadPoolExecutor(max_workers=self.max_parallel_collections) as executor:
            # Submit all collection tasks
            future_to_sensor = {
                executor.submit(
                    self.collectors[sensor_type].collect_latest_data
                ): sensor_type
                for sensor_type in sensor_types
                if sensor_type in self.collectors
            }
            
            # Collect results với timeout
            for future in future_to_sensor:
                sensor_type = future_to_sensor[future]
                try:
                    reading = future.result(timeout=5.0)  # 5s timeout
                    if reading:
                        results[sensor_type] = reading
                except Exception as e:
                    logger.error(f"Error collecting {sensor_type}: {e}")
        
        # Update stats
        self.collection_stats["adafruit_calls"] += len(sensor_types)
        
        return results
    
    def _get_dynamic_interval(self) -> int:
        """
        Lấy interval động dựa trên thời gian trong ngày.
        
        Returns:
            Interval tính bằng giây
        """
        current_hour = datetime.now().hour
        
        # Giờ cao điểm: 6-10 sáng, 14-18 chiều
        if 6 <= current_hour < 10 or 14 <= current_hour < 18:
            return self.peak_hours_interval
        # Giờ thấp điểm: 22-6 sáng
        elif 22 <= current_hour or current_hour < 6:
            return self.off_hours_interval
        # Giờ bình thường
        else:
            return self.base_collection_interval
    
    def start_background_collection(self, interval: Optional[int] = None) -> bool:
        """
        Bắt đầu thu thập dữ liệu ngầm với dynamic interval.
        
        Args:
            interval: Override interval (nếu không sẽ dùng dynamic)
            
        Returns:
            bool: Success
        """
        if self.is_collecting:
            logger.warning("Background collection is already running")
            return False
            
        self.is_collecting = True
        
        def collection_worker():
            logger.info("Starting optimized background data collection")
            
            while self.is_collecting:
                try:
                    # Get dynamic interval
                    current_interval = interval or self._get_dynamic_interval()
                    
                    # Collect all sensors
                    start_time = time.time()
                    
                    # Use smart collection (cache-first)
                    snapshot = self.get_environment_snapshot(
                        collect_if_needed=True,
                        force_collection=False,
                        use_cache=True
                    )
                    
                    # Update stats
                    self.collection_stats["total_collections"] += 1
                    self.collection_stats["last_collection"] = datetime.now()
                    
                    # Log performance
                    elapsed = time.time() - start_time
                    if elapsed > 2.0:  # Log if takes more than 2s
                        logger.warning(f"Collection took {elapsed:.2f}s")
                    
                    # Log stats periodically
                    if self.collection_stats["total_collections"] % 10 == 0:
                        self._log_collection_stats()
                        
                except Exception as e:
                    logger.error(f"Error in background collection: {str(e)}")
                    
                # Sleep with dynamic interval
                for _ in range(current_interval):
                    if not self.is_collecting:
                        break
                    time.sleep(1)
        
        self.background_thread = threading.Thread(target=collection_worker, daemon=True)
        self.background_thread.start()
        
        return True
    
    def _log_collection_stats(self):
        """Log collection statistics."""
        total = self.collection_stats["total_collections"]
        cache_hits = self.collection_stats["cache_hits"]
        adafruit_calls = self.collection_stats["adafruit_calls"]
        
        if total > 0:
            cache_hit_rate = (cache_hits / total) * 100
            calls_per_collection = adafruit_calls / total
            
            logger.info(
                f"Collection Stats - Total: {total}, "
                f"Cache Hit Rate: {cache_hit_rate:.1f}%, "
                f"Avg Adafruit Calls/Collection: {calls_per_collection:.2f}"
            )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        stats = self.collection_stats.copy()
        
        # Calculate rates
        total = stats["total_collections"]
        if total > 0:
            stats["cache_hit_rate"] = (stats["cache_hits"] / total) * 100
            stats["avg_adafruit_calls"] = stats["adafruit_calls"] / total
        else:
            stats["cache_hit_rate"] = 0
            stats["avg_adafruit_calls"] = 0
            
        return stats