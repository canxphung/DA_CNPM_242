"""
Bộ thu thập dữ liệu từ cảm biến độ ẩm đất.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.data.models import (
    SensorType,
    SensorStatus,
    SoilMoistureReading
)
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

class SoilMoistureCollector(BaseCollector[SoilMoistureReading]):
    """Bộ thu thập dữ liệu từ cảm biến độ ẩm đất."""
    
    def __init__(self):
        """Khởi tạo bộ thu thập cảm biến độ ẩm đất."""
        super().__init__(SensorType.SOIL_MOISTURE)
    
    def process_raw_data(self, raw_data: Dict[str, Any]) -> SoilMoistureReading:
        """
        Xử lý dữ liệu thô từ Adafruit thành SoilMoistureReading.
        
        Args:
            raw_data: Dữ liệu thô từ Adafruit
            
        Returns:
            SoilMoistureReading: Dữ liệu đã xử lý
        """
        try:
            # Sử dụng các hàm tiện ích từ lớp cha
            value, raw_value = self.parse_value(raw_data.get('value', '0'))
            timestamp = self.parse_timestamp(raw_data.get('created_at'))
                
            # Tạo đối tượng SoilMoistureReading
            reading = SoilMoistureReading(
                sensor_type=SensorType.SOIL_MOISTURE,
                value=value,
                raw_value=raw_value,
                unit="%",
                timestamp=timestamp,
                feed_id=raw_data.get('id'),
                metadata={
                    "feed_key": self.feed_key,
                    "source": "adafruit_io"
                }
            )
            
            return reading
            
        except Exception as e:
            logger.error(f"Error processing soil moisture sensor data: {str(e)}")
            # Trả về giá trị mặc định trong trường hợp lỗi
            return SoilMoistureReading(
                sensor_type=SensorType.SOIL_MOISTURE,
                value=0.0,
                raw_value="0",
                unit="%",
                status=SensorStatus.UNKNOWN,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )