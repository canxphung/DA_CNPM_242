"""
Analyzer chuyên biệt cho dữ liệu nhiệt độ.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics

from src.core.data.models import (
    SensorType,
    SensorReading,
    SensorStatus,
    TemperatureReading
)
from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)

class TemperatureAnalyzer(BaseAnalyzer):
    """
    Analyzer chuyên biệt cho dữ liệu nhiệt độ.
    """
    
    def __init__(
        self,
        min_threshold: float = 10.0,  # Ngưỡng dưới: 10°C (quá lạnh)
        max_threshold: float = 40.0,  # Ngưỡng trên: 40°C (quá nóng)
        optimal_range: tuple = (18.0, 30.0),  # Khoảng tối ưu
        warning_margin: float = 0.15  # Biên độ cảnh báo
    ):
        """
        Khởi tạo TemperatureAnalyzer với các ngưỡng.
        
        Args:
            min_threshold: Ngưỡng dưới (quá lạnh)
            max_threshold: Ngưỡng trên (quá nóng)
            optimal_range: Khoảng tối ưu (min, max)
            warning_margin: Biên độ cảnh báo
        """
        super().__init__(min_threshold, max_threshold, warning_margin)
        self.optimal_min, self.optimal_max = optimal_range
    
    def analyze(self, reading: TemperatureReading) -> Dict[str, Any]:
        """
        Phân tích dữ liệu nhiệt độ.
        
        Args:
            reading: Dữ liệu nhiệt độ
            
        Returns:
            Dict chứa kết quả phân tích
        """
        if not isinstance(reading, TemperatureReading):
            raise ValueError("Reading must be a TemperatureReading")
            
        value = reading.value
        status = self.evaluate_status(value)
        
        return {
            "value": value,
            "unit": reading.unit,
            "timestamp": reading.timestamp,
            "status": status,
            "description": self.get_range_description(value),
            "stress_level": self._calculate_stress_level(value),
            "growth_condition": self._get_growth_condition(value)
        }
    
    def analyze_trend(self, readings: List[TemperatureReading], hours: int = 24) -> Dict[str, Any]:
        """
        Phân tích xu hướng nhiệt độ theo thời gian.
        
        Args:
            readings: Danh sách dữ liệu nhiệt độ
            hours: Khoảng thời gian phân tích (giờ)
            
        Returns:
            Dict chứa kết quả phân tích xu hướng
        """
        if not readings:
            return {
                "trend": "unknown",
                "rate_of_change": 0.0,
                "forecast": "unknown"
            }
            
        # Sắp xếp readings theo thời gian
        sorted_readings = sorted(readings, key=lambda r: r.timestamp)
        
        # Lọc readings trong khoảng thời gian chỉ định
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_readings = [r for r in sorted_readings if r.timestamp >= cutoff_time]
        
        if len(recent_readings) < 2:
            return {
                "trend": "unknown",
                "rate_of_change": 0.0,
                "forecast": "unknown"
            }
            
        # Tính toán xu hướng
        first_reading = recent_readings[0]
        last_reading = recent_readings[-1]
        
        time_diff = (last_reading.timestamp - first_reading.timestamp).total_seconds() / 3600  # giờ
        if time_diff < 1:  # Ít nhất 1 giờ để phân tích xu hướng
            return {
                "trend": "unknown",
                "rate_of_change": 0.0,
                "forecast": "unknown"
            }
            
        temp_diff = last_reading.value - first_reading.value
        rate_of_change = temp_diff / time_diff  # °C / giờ
        
        # Xác định xu hướng
        if abs(rate_of_change) < 0.2:  # Thay đổi ít hơn 0.2°C mỗi giờ
            trend = "stable"
        else:
            trend = "cooling" if rate_of_change < 0 else "warming"
            
        # Tính các chỉ số thống kê
        values = [r.value for r in recent_readings]
        stats = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values)
        }
        
        # Dự đoán 6 giờ tới
        forecast_value = last_reading.value + rate_of_change * 6
        
        # Đánh giá forecast
        forecast_condition = self._get_growth_condition(forecast_value)
        
        return {
            "trend": trend,
            "rate_of_change": rate_of_change,
            "statistics": stats,
            "forecast": {
                "hours": 6,
                "value": forecast_value,
                "condition": forecast_condition
            },
            "recommendation": self._get_trend_recommendation(trend, rate_of_change, last_reading.value)
        }
    
    def _calculate_stress_level(self, value: float) -> str:
        """
        Tính toán mức độ stress của cây trồng dựa trên nhiệt độ.
        
        Args:
            value: Giá trị nhiệt độ
            
        Returns:
            str: Mức độ stress (none, low, medium, high, extreme)
        """
        if value < self.min_threshold:
            return "extreme"  # Quá lạnh
        elif value < self.optimal_min - 3:
            return "high"  # Lạnh
        elif value < self.optimal_min:
            return "medium"  # Hơi lạnh
        elif value > self.max_threshold:
            return "extreme"  # Quá nóng
        elif value > self.optimal_max + 3:
            return "high"  # Nóng
        elif value > self.optimal_max:
            return "medium"  # Hơi nóng
        else:
            return "none"  # Trong khoảng tối ưu
    
    def _get_growth_condition(self, value: float) -> str:
        """
        Đánh giá điều kiện phát triển của cây trồng dựa trên nhiệt độ.
        
        Args:
            value: Giá trị nhiệt độ
            
        Returns:
            str: Điều kiện phát triển
        """
        if value < self.min_threshold:
            return "growth_halted"  # Ngừng phát triển
        elif value < self.optimal_min - 3:
            return "slow_growth"  # Phát triển chậm
        elif value < self.optimal_min:
            return "reduced_growth"  # Giảm tốc độ phát triển
        elif value > self.max_threshold:
            return "heat_damage"  # Tổn thương do nhiệt
        elif value > self.optimal_max + 3:
            return "stressed_growth"  # Phát triển trong điều kiện stress
        elif value > self.optimal_max:
            return "suboptimal_growth"  # Phát triển không tối ưu
        else:
            return "optimal_growth"  # Phát triển tối ưu
    
    def _get_trend_recommendation(self, trend: str, rate_of_change: float, current_value: float) -> str:
        """
        Đưa ra đề xuất dựa trên xu hướng nhiệt độ.
        
        Args:
            trend: Xu hướng (cooling, stable, warming)
            rate_of_change: Tốc độ thay đổi (°C/giờ)
            current_value: Giá trị hiện tại
            
        Returns:
            str: Đề xuất
        """
        if trend == "unknown":
            return "collect_more_data"
            
        if current_value < self.min_threshold:
            return "protect_from_cold"
            
        if current_value > self.max_threshold:
            return "protect_from_heat"
            
        if trend == "cooling":
            if current_value < self.optimal_min + 3 and rate_of_change < -0.5:
                return "prepare_for_cold"
            else:
                return "normal_monitoring"
        elif trend == "warming":
            if current_value > self.optimal_max - 3 and rate_of_change > 0.5:
                return "prepare_for_heat"
            elif current_value < self.optimal_min and rate_of_change > 0:
                return "favorable_warming"
            else:
                return "normal_monitoring"
        else:  # stable
            if current_value < self.optimal_min:
                return "monitor_for_cold_stress"
            elif current_value > self.optimal_max:
                return "monitor_for_heat_stress"
            else:
                return "maintain_conditions"