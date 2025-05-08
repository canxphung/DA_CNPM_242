"""
Bộ thu thập dữ liệu từ cảm biến ánh sáng.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.data.models import (
    SensorType,
    SensorStatus,
    LightReading
)
from .base_collector import BaseCollector

logger = logging.getLogger(__name__)

class LightCollector(BaseCollector[LightReading]):
    """Bộ thu thập dữ liệu từ cảm biến ánh sáng."""
    
    def __init__(self):
        """Khởi tạo bộ thu thập cảm biến ánh sáng."""
        super().__init__(SensorType.LIGHT)
    
    def process_raw_data(self, raw_data: Dict[str, Any]) -> LightReading:
        """
        Xử lý dữ liệu thô từ Adafruit thành LightReading.
        
        Args:
            raw_data: Dữ liệu thô từ Adafruit
            
        Returns:
            LightReading: Dữ liệu đã xử lý
        """
        try:
            # Sử dụng các hàm tiện ích từ lớp cha
            value, raw_value = self.parse_value(raw_data.get('value', '0'))
            timestamp = self.parse_timestamp(raw_data.get('created_at'))
                
            # Tạo đối tượng LightReading
            reading = LightReading(
                sensor_type=SensorType.LIGHT,
                value=value,
                raw_value=raw_value,
                unit="lux",
                timestamp=timestamp,
                feed_id=raw_data.get('id'),
                metadata={
                    "feed_key": self.feed_key,
                    "source": "adafruit_io"
                }
            )
            
            return reading
            
        except Exception as e:
            logger.error(f"Error processing light sensor data: {str(e)}")
            # Trả về giá trị mặc định trong trường hợp lỗi
            return LightReading(
                sensor_type=SensorType.LIGHT,
                value=0.0,
                raw_value="0",
                unit="lux",
                status=SensorStatus.UNKNOWN,
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            )