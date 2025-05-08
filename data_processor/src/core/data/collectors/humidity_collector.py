"""
Bộ thu thập dữ liệu từ cảm biến độ ẩm không khí.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.data.models import (
    SensorType,
    SensorStatus,
    HumidityReading
)
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

class HumidityCollector(BaseCollector[HumidityReading]):
    """Bộ thu thập dữ liệu từ cảm biến độ ẩm không khí."""
    
    def __init__(self):
        """Khởi tạo bộ thu thập cảm biến độ ẩm không khí."""
        super().__init__(SensorType.HUMIDITY)
    
    def process_raw_data(self, raw_data: Dict[str, Any]) -> HumidityReading:
        """
        Xử lý dữ liệu thô từ Adafruit thành HumidityReading.
        
        Args:
            raw_data: Dữ liệu thô từ Adafruit
            
        Returns:
            HumidityReading: Dữ liệu đã xử lý
        """
        try:
            # Sử dụng các hàm tiện ích từ lớp cha
            value, raw_value = self.parse_value(raw_data.get('value', '0'))
            timestamp = self.parse_timestamp(raw_data.get('created_at'))
                
            # Tạo đối tượng HumidityReading
            reading = HumidityReading(
                sensor_type=SensorType.HUMIDITY,
                value=value,
                raw_value=raw_value,
                unit="%",
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
            logger.error(f"Error processing humidity sensor data: {str(e)}")
            # Trả về giá trị mặc định trong trường hợp lỗi
            return HumidityReading(
                sensor_type=SensorType.HUMIDITY,
                value=0.0,
                raw_value="0",
                unit="%",
                status=SensorStatus.UNKNOWN,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )