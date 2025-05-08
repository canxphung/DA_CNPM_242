"""
Lớp cơ sở cho các analyzer môi trường.
"""
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from src.core.data.models import (
    SensorReading,
    SensorStatus
)

logger = logging.getLogger(__name__)

class BaseAnalyzer(ABC):
    """
    Lớp cơ sở trừu tượng cho các analyzer môi trường.
    """
    
    def __init__(self, min_threshold: float, max_threshold: float, warning_margin: float = 0.15):
        """
        Khởi tạo base analyzer với các ngưỡng.
        
        Args:
            min_threshold: Ngưỡng dưới (quá khô, quá lạnh, v.v.)
            max_threshold: Ngưỡng trên (quá ẩm, quá nóng, v.v.)
            warning_margin: Biên độ cảnh báo (% của khoảng ngưỡng)
        """
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.warning_margin = warning_margin
        
    def evaluate_status(self, value: float) -> SensorStatus:
        """
        Đánh giá trạng thái dựa trên giá trị.
        
        Args:
            value: Giá trị cần đánh giá
            
        Returns:
            SensorStatus: Trạng thái tương ứng
        """
        # Tính ngưỡng cảnh báo
        range_size = self.max_threshold - self.min_threshold
        warning_size = range_size * self.warning_margin
        
        min_warning = self.min_threshold + warning_size
        max_warning = self.max_threshold - warning_size
        
        # Đánh giá trạng thái
        if value < self.min_threshold:
            return SensorStatus.CRITICAL
        elif value < min_warning:
            return SensorStatus.WARNING
        elif value > self.max_threshold:
            return SensorStatus.CRITICAL
        elif value > max_warning:
            return SensorStatus.WARNING
        else:
            return SensorStatus.NORMAL
    
    @abstractmethod
    def analyze(self, reading: SensorReading) -> Dict[str, Any]:
        """
        Phân tích dữ liệu cảm biến.
        
        Args:
            reading: Dữ liệu cảm biến
            
        Returns:
            Dict chứa kết quả phân tích
        """
        pass
    
    @abstractmethod
    def analyze_trend(self, readings: List[SensorReading], hours: int = 24) -> Dict[str, Any]:
        """
        Phân tích xu hướng dữ liệu theo thời gian.
        
        Args:
            readings: Danh sách dữ liệu cảm biến
            hours: Khoảng thời gian phân tích (giờ)
            
        Returns:
            Dict chứa kết quả phân tích xu hướng
        """
        pass
    
    def get_range_description(self, value: float) -> str:
        """
        Trả về mô tả khoảng giá trị.
        
        Args:
            value: Giá trị cần mô tả
            
        Returns:
            str: Mô tả khoảng giá trị
        """
        status = self.evaluate_status(value)
        
        if status == SensorStatus.CRITICAL:
            if value < self.min_threshold:
                return "critically_low"
            else:
                return "critically_high"
        elif status == SensorStatus.WARNING:
            if value < self.min_threshold + (self.max_threshold - self.min_threshold) / 2:
                return "warning_low"
            else:
                return "warning_high"
        else:
            if value < self.min_threshold + (self.max_threshold - self.min_threshold) / 3:
                return "normal_low"
            elif value > self.min_threshold + 2 * (self.max_threshold - self.min_threshold) / 3:
                return "normal_high"
            else:
                return "optimal"