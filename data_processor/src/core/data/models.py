"""
Models dữ liệu cho các loại cảm biến và môi trường.
"""
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

class SensorType(str, Enum):
    """Các loại cảm biến được hỗ trợ."""
    LIGHT = "light"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    SOIL_MOISTURE = "soil_moisture"

class SensorStatus(str, Enum):
    """Trạng thái của cảm biến."""
    NORMAL = "normal"       # Hoạt động bình thường
    WARNING = "warning"     # Cảnh báo (giá trị gần ngưỡng)
    CRITICAL = "critical"   # Nguy hiểm (giá trị vượt ngưỡng)
    UNKNOWN = "unknown"     # Không xác định

class SensorReading(BaseModel):
    """Model cơ bản cho kết quả đọc từ cảm biến."""
    sensor_type: SensorType
    value: float
    raw_value: str = None
    unit: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: SensorStatus = SensorStatus.NORMAL
    feed_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

    class Config:
        """Cấu hình model."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class LightReading(SensorReading):
    """Kết quả đọc từ cảm biến ánh sáng."""
    sensor_type: SensorType = SensorType.LIGHT
    unit: str = "lux"
    
    @validator('status', pre=True, always=True)
    def set_status(cls, status, values):
        """Tự động tính trạng thái dựa trên giá trị."""
        if 'value' not in values:
            return SensorStatus.UNKNOWN
            
        value = values['value']
        if value < 50:  # Ánh sáng quá thấp
            return SensorStatus.CRITICAL
        elif value < 200:  # Ánh sáng thấp
            return SensorStatus.WARNING
        elif value > 10000:  # Ánh sáng quá cao
            return SensorStatus.WARNING
        return SensorStatus.NORMAL

class TemperatureReading(SensorReading):
    """Kết quả đọc từ cảm biến nhiệt độ."""
    sensor_type: SensorType = SensorType.TEMPERATURE
    unit: str = "°C"
    
    @validator('status', pre=True, always=True)
    def set_status(cls, status, values):
        """Tự động tính trạng thái dựa trên giá trị."""
        if 'value' not in values:
            return SensorStatus.UNKNOWN
            
        value = values['value']
        if value < 10:  # Nhiệt độ quá thấp
            return SensorStatus.CRITICAL
        elif value < 15:  # Nhiệt độ thấp
            return SensorStatus.WARNING
        elif value > 35:  # Nhiệt độ cao
            return SensorStatus.WARNING
        elif value > 40:  # Nhiệt độ quá cao
            return SensorStatus.CRITICAL
        return SensorStatus.NORMAL

class HumidityReading(SensorReading):
    """Kết quả đọc từ cảm biến độ ẩm không khí."""
    sensor_type: SensorType = SensorType.HUMIDITY
    unit: str = "%"
    
    @validator('status', pre=True, always=True)
    def set_status(cls, status, values):
        """Tự động tính trạng thái dựa trên giá trị."""
        if 'value' not in values:
            return SensorStatus.UNKNOWN
            
        value = values['value']
        if value < 30:  # Độ ẩm quá thấp
            return SensorStatus.CRITICAL
        elif value < 40:  # Độ ẩm thấp
            return SensorStatus.WARNING
        elif value > 80:  # Độ ẩm cao
            return SensorStatus.WARNING
        elif value > 90:  # Độ ẩm quá cao
            return SensorStatus.CRITICAL
        return SensorStatus.NORMAL

class SoilMoistureReading(SensorReading):
    """Kết quả đọc từ cảm biến độ ẩm đất."""
    sensor_type: SensorType = SensorType.SOIL_MOISTURE
    unit: str = "%"
    
    @validator('status', pre=True, always=True)
    def set_status(cls, status, values):
        """Tự động tính trạng thái dựa trên giá trị."""
        if 'value' not in values:
            return SensorStatus.UNKNOWN
            
        value = values['value']
        if value < 20:  # Đất quá khô
            return SensorStatus.CRITICAL
        elif value < 30:  # Đất khô
            return SensorStatus.WARNING
        elif value > 80:  # Đất ẩm
            return SensorStatus.WARNING
        elif value > 90:  # Đất quá ẩm
            return SensorStatus.CRITICAL
        return SensorStatus.NORMAL

class EnvironmentSnapshot(BaseModel):
    """
    Tổng hợp dữ liệu môi trường từ nhiều cảm biến tại một thời điểm.
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    light: Optional[LightReading] = None
    temperature: Optional[TemperatureReading] = None
    humidity: Optional[HumidityReading] = None
    soil_moisture: Optional[SoilMoistureReading] = None
    
    def get_overall_status(self) -> SensorStatus:
        """
        Tính toán trạng thái tổng thể của môi trường.
        
        Returns:
            SensorStatus: Trạng thái nghiêm trọng nhất trong các cảm biến
        """
        # Kiểm tra xem có trạng thái CRITICAL nào không
        for reading in [self.light, self.temperature, self.humidity, self.soil_moisture]:
            if reading and reading.status == SensorStatus.CRITICAL:
                return SensorStatus.CRITICAL
                
        # Kiểm tra xem có trạng thái WARNING nào không
        for reading in [self.light, self.temperature, self.humidity, self.soil_moisture]:
            if reading and reading.status == SensorStatus.WARNING:
                return SensorStatus.WARNING
                
        # Nếu tất cả đều NORMAL hoặc không có dữ liệu
        if any(reading for reading in [self.light, self.temperature, self.humidity, self.soil_moisture]):
            return SensorStatus.NORMAL
        else:
            return SensorStatus.UNKNOWN