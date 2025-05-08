"""
Quản lý thu thập dữ liệu từ tất cả các cảm biến.
"""
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from src.core.data.models import (
    SensorType,
    SensorStatus,
    SensorReading,
    EnvironmentSnapshot
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
    
    def get_environment_snapshot(self, collect_if_needed: bool = True, force_collection: bool = False) -> EnvironmentSnapshot:
        """
        Tạo và trả về snapshot của môi trường hiện tại.
        
        Args:
            collect_if_needed: Nếu True, thu thập dữ liệu mới nếu cache thiếu hoặc quá cũ
            force_collection: Nếu True, luôn thu thập dữ liệu mới bất kể cache
            
        Returns:
            EnvironmentSnapshot: Snapshot của môi trường
        """
        # Nếu force_collection = True, bỏ qua cache và lấy dữ liệu mới
        if force_collection:
            readings = self.collect_all_latest_data()
            logger.info("Forced collection of new data for environment snapshot")
        else:
            # Trước tiên, thử lấy từ cache
            readings = self.get_latest_readings()
            
            # Nếu collect_if_needed = True và thiếu dữ liệu, thu thập dữ liệu mới
            if collect_if_needed and len(readings) < len(self.collectors):
                missing_types = set(self.collectors.keys()) - set(readings.keys())
                logger.info(f"Missing data for sensors: {missing_types}, collecting new data")
                
                new_readings = self.collect_all_latest_data()
                
                # Cập nhật readings với dữ liệu mới
                readings.update(new_readings)
        
        # Tạo snapshot từ dữ liệu
        snapshot = EnvironmentSnapshot(
            timestamp=datetime.now(),
            light=readings.get(SensorType.LIGHT),
            temperature=readings.get(SensorType.TEMPERATURE),
            humidity=readings.get(SensorType.HUMIDITY),
            soil_moisture=readings.get(SensorType.SOIL_MOISTURE)
        )
        
        return snapshot
    
    def start_background_collection(self, interval: int = 60) -> bool:
        """
        Bắt đầu thu thập dữ liệu ngầm theo định kỳ.
        
        Args:
            interval: Khoảng thời gian giữa các lần thu thập (giây)
            
        Returns:
            bool: Thành công hay thất bại
        """
        if self.is_collecting:
            logger.warning("Background collection is already running")
            return False
            
        self.collection_interval = interval
        self.is_collecting = True
        
        def collection_worker():
            logger.info(f"Starting background data collection every {interval} seconds")
            while self.is_collecting:
                try:
                    self.collect_all_latest_data()
                except Exception as e:
                    logger.error(f"Error in background collection: {str(e)}")
                    
                # Sleep for the specified interval
                for _ in range(interval):
                    if not self.is_collecting:
                        break
                    time.sleep(1)
        
        self.background_thread = threading.Thread(target=collection_worker)
        self.background_thread.daemon = True
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