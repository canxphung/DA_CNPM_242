"""
Analyzer chuyên biệt cho dữ liệu ánh sáng.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics

from src.core.data.models import (
    SensorType,
    SensorReading,
    SensorStatus,
    LightReading
)
from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)

class LightAnalyzer(BaseAnalyzer):
    """
    Analyzer chuyên biệt cho dữ liệu ánh sáng.
    """
    
    def __init__(
        self,
        min_threshold: float = 200.0,  # Ngưỡng dưới: 200 lux (quá tối)
        max_threshold: float = 10000.0,  # Ngưỡng trên: 10000 lux (quá sáng)
        optimal_range: tuple = (1000.0, 7000.0),  # Khoảng tối ưu
        warning_margin: float = 0.15  # Biên độ cảnh báo
    ):
        """
        Khởi tạo LightAnalyzer với các ngưỡng.
        
        Args:
            min_threshold: Ngưỡng dưới (quá tối)
            max_threshold: Ngưỡng trên (quá sáng)
            optimal_range: Khoảng tối ưu (min, max)
            warning_margin: Biên độ cảnh báo
        """
        super().__init__(min_threshold, max_threshold, warning_margin)
        self.optimal_min, self.optimal_max = optimal_range
    
    def analyze(self, reading: LightReading) -> Dict[str, Any]:
        """
        Phân tích dữ liệu ánh sáng.
        
        Args:
            reading: Dữ liệu ánh sáng
            
        Returns:
            Dict chứa kết quả phân tích
        """
        if not isinstance(reading, LightReading):
            raise ValueError("Reading must be a LightReading")
            
        value = reading.value
        status = self.evaluate_status(value)
        
        # Đánh giá dựa trên thời gian trong ngày
        time_of_day = self._get_time_of_day(reading.timestamp)
        expected_range = self._get_expected_range(time_of_day)
        
        # Kiểm tra xem giá trị có nằm trong khoảng dự kiến không
        in_expected_range = expected_range[0] <= value <= expected_range[1]
        
        return {
            "value": value,
            "unit": reading.unit,
            "timestamp": reading.timestamp,
            "status": status,
            "description": self.get_range_description(value),
            "time_of_day": time_of_day,
            "expected_range": expected_range,
            "in_expected_range": in_expected_range,
            "light_condition": self._get_light_condition(value),
            "plant_impact": self._get_plant_impact(value)
        }
    
    def analyze_trend(self, readings: List[LightReading], hours: int = 24) -> Dict[str, Any]:
        """
        Phân tích xu hướng ánh sáng theo thời gian.
        
        Args:
            readings: Danh sách dữ liệu ánh sáng
            hours: Khoảng thời gian phân tích (giờ)
            
        Returns:
            Dict chứa kết quả phân tích xu hướng
        """
        if not readings:
            return {
                "trend": "unknown",
                "day_night_cycle": "unknown",
                "total_light_hours": 0
            }
            
        # Sắp xếp readings theo thời gian
        sorted_readings = sorted(readings, key=lambda r: r.timestamp)
        
        # Lọc readings trong khoảng thời gian chỉ định
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_readings = [r for r in sorted_readings if r.timestamp >= cutoff_time]
        
        if len(recent_readings) < 2:
            return {
                "trend": "unknown",
                "day_night_cycle": "unknown",
                "total_light_hours": 0
            }
            
        # Phân loại thành ngày và đêm
        day_threshold = 500  # lux, ngưỡng để coi là "ngày"
        
        # Tính số giờ có ánh sáng
        day_readings = [r for r in recent_readings if r.value >= day_threshold]
        total_readings = len(recent_readings)
        
        if total_readings == 0:
            light_hours = 0
        else:
            light_hours = len(day_readings) / total_readings * hours
            
        # Tính các chỉ số thống kê
        values = [r.value for r in recent_readings]
        stats = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0
        }
        
        # Xác định chu kỳ ngày đêm
        if not day_readings:
            day_night_cycle = "continuous_night"
        elif len(day_readings) == total_readings:
            day_night_cycle = "continuous_day"
        else:
            # Kiểm tra xem có chu kỳ ngày đêm không
            timestamps = [r.timestamp for r in recent_readings]
            values_high = [r.value >= day_threshold for r in recent_readings]
            
            # Đếm số lần chuyển đổi giữa ngày và đêm
            transitions = sum(1 for i in range(1, len(values_high)) if values_high[i] != values_high[i-1])
            
            if transitions >= 2:
                day_night_cycle = "normal"
            elif transitions == 1:
                day_night_cycle = "single_transition"
            else:
                day_night_cycle = "irregular"
        
        return {
            "statistics": stats,
            "day_night_cycle": day_night_cycle,
            "total_light_hours": light_hours,
            "light_percentage": (len(day_readings) / total_readings * 100) if total_readings > 0 else 0,
            "recommendation": self._get_light_recommendation(light_hours, day_night_cycle, stats["mean"])
        }
    
    def _get_time_of_day(self, timestamp: datetime) -> str:
        """
        Xác định thời điểm trong ngày.
        
        Args:
            timestamp: Thời gian
            
        Returns:
            str: Thời điểm trong ngày (morning, afternoon, evening, night)
        """
        hour = timestamp.hour
        
        if 5 <= hour < 10:
            return "morning"
        elif 10 <= hour < 16:
            return "afternoon"
        elif 16 <= hour < 20:
            return "evening"
        else:
            return "night"
    
    def _get_expected_range(self, time_of_day: str) -> tuple:
        """
        Lấy khoảng ánh sáng dự kiến dựa trên thời điểm trong ngày.
        
        Args:
            time_of_day: Thời điểm trong ngày
            
        Returns:
            tuple: Khoảng dự kiến (min, max)
        """
        if time_of_day == "morning":
            return (500, 5000)
        elif time_of_day == "afternoon":
            return (1000, 10000)
        elif time_of_day == "evening":
            return (200, 3000)
        else:  # night
            return (0, 200)
    
    def _get_light_condition(self, value: float) -> str:
        """
        Đánh giá điều kiện ánh sáng.
        
        Args:
            value: Giá trị ánh sáng
            
        Returns:
            str: Điều kiện ánh sáng
        """
        if value < 50:
            return "dark"
        elif value < 200:
            return "dim"
        elif value < 1000:
            return "moderate"
        elif value < 5000:
            return "bright"
        elif value < 10000:
            return "very_bright"
        else:
            return "intense"
    
    def _get_plant_impact(self, value: float) -> str:
        """
        Đánh giá tác động lên cây trồng.
        
        Args:
            value: Giá trị ánh sáng
            
        Returns:
            str: Tác động lên cây trồng
        """
        if value < 50:
            return "insufficient_for_growth"
        elif value < 200:
            return "minimal_growth"
        elif value < 1000:
            return "slow_growth"
        elif value < 5000:
            return "good_growth"
        elif value < 10000:
            return "optimal_growth"
        else:
            return "potential_light_stress"
    
    def _get_light_recommendation(self, light_hours: float, day_night_cycle: str, avg_intensity: float) -> str:
        """
        Đưa ra đề xuất dựa trên phân tích ánh sáng.
        
        Args:
            light_hours: Số giờ có ánh sáng
            day_night_cycle: Chu kỳ ngày đêm
            avg_intensity: Cường độ ánh sáng trung bình
            
        Returns:
            str: Đề xuất
        """
        if light_hours < 6:
            return "insufficient_light"
        elif light_hours > 16:
            return "excessive_light_duration"
            
        if day_night_cycle not in ["normal", "single_transition"]:
            return "irregular_light_cycle"
            
        if avg_intensity < self.min_threshold:
            return "increase_light_intensity"
        elif avg_intensity > self.max_threshold:
            return "reduce_light_intensity"
        elif avg_intensity < self.optimal_min:
            return "slightly_low_intensity"
        elif avg_intensity > self.optimal_max:
            return "slightly_high_intensity"
        else:
            return "optimal_light_conditions"