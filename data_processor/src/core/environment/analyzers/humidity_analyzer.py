"""
Analyzer chuyên biệt cho dữ liệu độ ẩm không khí.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics

from src.core.data.models import (
    SensorType,
    SensorReading,
    SensorStatus,
    HumidityReading
)
from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)

class HumidityAnalyzer(BaseAnalyzer):
    """
    Analyzer chuyên biệt cho dữ liệu độ ẩm không khí.
    """
    
    def __init__(
        self,
        min_threshold: float = 30.0,  # Ngưỡng dưới: 30% (quá khô)
        max_threshold: float = 90.0,  # Ngưỡng trên: 90% (quá ẩm)
        optimal_range: tuple = (40.0, 70.0),  # Khoảng tối ưu
        warning_margin: float = 0.15  # Biên độ cảnh báo
    ):
        """
        Khởi tạo HumidityAnalyzer với các ngưỡng.
        
        Args:
            min_threshold: Ngưỡng dưới (quá khô)
            max_threshold: Ngưỡng trên (quá ẩm)
            optimal_range: Khoảng tối ưu (min, max)
            warning_margin: Biên độ cảnh báo
        """
        super().__init__(min_threshold, max_threshold, warning_margin)
        self.optimal_min, self.optimal_max = optimal_range
    
    def analyze(self, reading: HumidityReading) -> Dict[str, Any]:
        """
        Phân tích dữ liệu độ ẩm không khí.
        
        Args:
            reading: Dữ liệu độ ẩm không khí
            
        Returns:
            Dict chứa kết quả phân tích
        """
        if not isinstance(reading, HumidityReading):
            raise ValueError("Reading must be a HumidityReading")
            
        value = reading.value
        status = self.evaluate_status(value)
        
        return {
            "value": value,
            "unit": reading.unit,
            "timestamp": reading.timestamp,
            "status": status,
            "description": self.get_range_description(value),
            "condition": self._get_condition(value),
            "disease_risk": self._calculate_disease_risk(value)
        }
    
    def analyze_trend(self, readings: List[HumidityReading], hours: int = 24) -> Dict[str, Any]:
        """
        Phân tích xu hướng độ ẩm không khí theo thời gian.
        
        Args:
            readings: Danh sách dữ liệu độ ẩm không khí
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
            
        humidity_diff = last_reading.value - first_reading.value
        rate_of_change = humidity_diff / time_diff  # % / giờ
        
        # Xác định xu hướng
        if abs(rate_of_change) < 0.5:  # Thay đổi ít hơn 0.5% mỗi giờ
            trend = "stable"
        else:
            trend = "drying" if rate_of_change < 0 else "humidifying"
            
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
        forecast_value = max(0, min(100, forecast_value))  # Giới hạn trong khoảng 0-100%
        
        # Đánh giá forecast
        forecast_condition = self._get_condition(forecast_value)
        forecast_risk = self._calculate_disease_risk(forecast_value)
        
        return {
            "trend": trend,
            "rate_of_change": rate_of_change,
            "statistics": stats,
            "forecast": {
                "hours": 6,
                "value": forecast_value,
                "condition": forecast_condition,
                "disease_risk": forecast_risk
            },
            "recommendation": self._get_trend_recommendation(trend, rate_of_change, last_reading.value)
        }
    
    def _get_condition(self, value: float) -> str:
        """
        Đánh giá điều kiện độ ẩm không khí.
        
        Args:
            value: Giá trị độ ẩm không khí
            
        Returns:
            str: Điều kiện độ ẩm
        """
        if value < self.min_threshold:
            return "very_dry"
        elif value < self.optimal_min:
            return "dry"
        elif value > self.max_threshold:
            return "very_humid"
        elif value > self.optimal_max:
            return "humid"
        else:
            return "comfortable"
    
    def _calculate_disease_risk(self, value: float) -> str:
        """
        Tính toán nguy cơ bệnh dịch dựa trên độ ẩm không khí.
        
        Args:
            value: Giá trị độ ẩm không khí
            
        Returns:
            str: Mức độ nguy cơ (low, medium, high, severe)
        """
        if value > 85:
            return "severe"  # Nguy cơ nấm mốc và bệnh dịch cao
        elif value > 75:
            return "high"  # Nguy cơ bệnh dịch cao
        elif value > 65:
            return "medium"  # Nguy cơ trung bình
        else:
            return "low"  # Nguy cơ thấp
    
    def _get_trend_recommendation(self, trend: str, rate_of_change: float, current_value: float) -> str:
        """
        Đưa ra đề xuất dựa trên xu hướng độ ẩm không khí.
        
        Args:
            trend: Xu hướng (drying, stable, humidifying)
            rate_of_change: Tốc độ thay đổi (%/giờ)
            current_value: Giá trị hiện tại
            
        Returns:
            str: Đề xuất
        """
        if trend == "unknown":
            return "collect_more_data"
            
        if current_value < self.min_threshold:
            return "increase_humidity"
            
        if current_value > self.max_threshold:
            return "reduce_humidity"
            
        if trend == "drying":
            if current_value < self.optimal_min + 5 and rate_of_change < -1.0:
                return "prevent_further_drying"
            else:
                return "normal_monitoring"
        elif trend == "humidifying":
            if current_value > self.optimal_max - 5 and rate_of_change > 1.0:
                return "prevent_excess_humidity"
            elif current_value > 75:
                return "monitor_for_disease"
            else:
                return "normal_monitoring"
        else:  # stable
            if current_value > 75:
                return "monitor_for_disease"
            elif current_value < self.optimal_min:
                return "consider_humidity_increase"
            else:
                return "maintain_conditions"