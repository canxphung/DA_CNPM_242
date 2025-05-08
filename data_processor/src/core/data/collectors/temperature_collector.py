"""
Bộ thu thập dữ liệu từ cảm biến nhiệt độ.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.data.models import (
    SensorType,
    SensorStatus,
    TemperatureReading
)
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

class TemperatureCollector(BaseCollector[TemperatureReading]):
    """Bộ thu thập dữ liệu từ cảm biến nhiệt độ."""
    
    def __init__(self):
        """Khởi tạo bộ thu thập cảm biến nhiệt độ."""
        super().__init__(SensorType.TEMPERATURE)
    
    def process_raw_data(self, raw_data: Dict[str, Any]) -> TemperatureReading:
        """
        Xử lý dữ liệu thô từ Adafruit thành TemperatureReading.
        
        Args:
            raw_data: Dữ liệu thô từ Adafruit
            
        Returns:
            TemperatureReading: Dữ liệu đã xử lý
        """
        try:
            # Sử dụng các hàm tiện ích từ lớp cha
            value, raw_value = self.parse_value(raw_data.get('value', '0'))
            timestamp = self.parse_timestamp(raw_data.get('created_at'))
                
            # Tạo đối tượng TemperatureReading
            reading = TemperatureReading(
                sensor_type=SensorType.TEMPERATURE,
                value=value,
                raw_value=raw_value,
                unit="°C",
                timestamp=timestamp,
                feed_id=raw_data.get('id'),
                metadata={
                    "feed_key": self.feed_key,
                    "source": "adafruit_io",
                    "sensor_model": "DHT20"
                }
            )
            
            return reading
            
        except Exception as e:
            logger.error(f"Error processing temperature sensor data: {str(e)}")
            # Trả về giá trị mặc định trong trường hợp lỗi
            return TemperatureReading(
                sensor_type=SensorType.TEMPERATURE,
                value=0.0,
                raw_value="0",
                unit="°C",
                status=SensorStatus.UNKNOWN,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )