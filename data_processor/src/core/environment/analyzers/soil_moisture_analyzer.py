"""
Analyzer chuyên biệt cho dữ liệu độ ẩm đất.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics

from src.core.data.models import (
    SensorType,
    SensorReading,
    SensorStatus,
    SoilMoistureReading
)
from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)

class SoilMoistureAnalyzer(BaseAnalyzer):
    """
    Analyzer chuyên biệt cho dữ liệu độ ẩm đất.
    """
    
    def __init__(
        self,
        min_threshold: float = 20.0,  # Ngưỡng dưới: 20% (quá khô)
        max_threshold: float = 90.0,  # Ngưỡng trên: 90% (quá ướt)
        optimal_range: tuple = (40.0, 70.0),  # Khoảng tối ưu
        warning_margin: float = 0.15  # Biên độ cảnh báo
    ):
        """
        Khởi tạo SoilMoistureAnalyzer với các ngưỡng.
        
        Args:
            min_threshold: Ngưỡng dưới (quá khô)
            max_threshold: Ngưỡng trên (quá ướt)
            optimal_range: Khoảng tối ưu (min, max)
            warning_margin: Biên độ cảnh báo
        """
        super().__init__(min_threshold, max_threshold, warning_margin)
        self.optimal_min, self.optimal_max = optimal_range
    
    def analyze(self, reading: SoilMoistureReading) -> Dict[str, Any]:
        """
        Phân tích dữ liệu độ ẩm đất.
        
        Args:
            reading: Dữ liệu độ ẩm đất
            
        Returns:
            Dict chứa kết quả phân tích
        """
        if not isinstance(reading, SoilMoistureReading):
            raise ValueError("Reading must be a SoilMoistureReading")
            
        value = reading.value
        status = self.evaluate_status(value)
        
        needs_water = value < self.optimal_min
        
        return {
            "value": value,
            "unit": reading.unit,
            "timestamp": reading.timestamp,
            "status": status,
            "description": self.get_range_description(value),
            "needs_water": needs_water,
            "risk_level": self._calculate_risk_level(value),
            "watering_recommendation": self._get_watering_recommendation(value)
        }
    
    def analyze_trend(self, readings: List[SoilMoistureReading], hours: int = 24) -> Dict[str, Any]:
        """
        Phân tích xu hướng độ ẩm đất theo thời gian.
        
        Args:
            readings: Danh sách dữ liệu độ ẩm đất
            hours: Khoảng thời gian phân tích (giờ)
            
        Returns:
            Dict chứa kết quả phân tích xu hướng
        """
        if not readings:
            return {
                "trend": "unknown",
                "rate_of_change": 0.0,
                "hours_until_dry": None,
                "recommendation": "collect_more_data"
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
                "hours_until_dry": None,
                "recommendation": "collect_more_data"
            }
            
        # Tính toán xu hướng
        first_reading = recent_readings[0]
        last_reading = recent_readings[-1]
        
        time_diff = (last_reading.timestamp - first_reading.timestamp).total_seconds() / 3600  # giờ
        if time_diff < 1:  # Ít nhất 1 giờ để phân tích xu hướng
            return {
                "trend": "unknown",
                "rate_of_change": 0.0,
                "hours_until_dry": None,
                "recommendation": "collect_more_data"
            }
            
        moisture_diff = last_reading.value - first_reading.value
        rate_of_change = moisture_diff / time_diff  # % / giờ
        
        # Xác định xu hướng
        if abs(rate_of_change) < 0.5:  # Thay đổi ít hơn 0.5% mỗi giờ
            trend = "stable"
        else:
            trend = "decreasing" if rate_of_change < 0 else "increasing"
            
        # Dự đoán thời gian cho đến khi đất khô
        hours_until_dry = None
        if rate_of_change < 0:  # Nếu độ ẩm đang giảm
            moisture_to_min = last_reading.value - self.min_threshold
            if moisture_to_min > 0:
                hours_until_dry = moisture_to_min / abs(rate_of_change)
                
        # Tính các chỉ số thống kê
        values = [r.value for r in recent_readings]
        stats = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values)
        }
        
        # Đưa ra đề xuất
        recommendation = self._get_trend_recommendation(trend, rate_of_change, last_reading.value, hours_until_dry)
        
        return {
            "trend": trend,
            "rate_of_change": rate_of_change,
            "hours_until_dry": hours_until_dry,
            "statistics": stats,
            "recommendation": recommendation
        }
    
    def _calculate_risk_level(self, value: float) -> str:
        """
        Tính toán mức độ rủi ro dựa trên giá trị độ ẩm đất.
        
        Args:
            value: Giá trị độ ẩm đất
            
        Returns:
            str: Mức độ rủi ro (none, low, medium, high, extreme)
        """
        if value < self.min_threshold:
            return "extreme"  # Quá khô, nguy cơ chết cây
        elif value < self.optimal_min - 5:
            return "high"  # Khô, cần tưới ngay
        elif value < self.optimal_min:
            return "medium"  # Hơi khô, nên theo dõi
        elif value > self.max_threshold:
            return "high"  # Quá ướt, nguy cơ úng
        elif value > self.optimal_max + 5:
            return "medium"  # Hơi ướt, nên theo dõi
        else:
            return "none"  # Trong khoảng tối ưu
    
    def _get_watering_recommendation(self, value: float) -> str:
        """
        Đưa ra đề xuất tưới dựa trên giá trị độ ẩm đất.
        
        Args:
            value: Giá trị độ ẩm đất
            
        Returns:
            str: Đề xuất tưới
        """
        if value < self.min_threshold:
            return "water_immediately"  # Tưới ngay lập tức
        elif value < self.optimal_min - 5:
            return "water_soon"  # Tưới trong thời gian tới
        elif value < self.optimal_min:
            return "monitor"  # Theo dõi
        elif value > self.max_threshold:
            return "stop_watering"  # Ngừng tưới
        elif value > self.optimal_max:
            return "no_water_needed"  # Không cần tưới
        else:
            return "optimal"  # Độ ẩm tối ưu
    
    def _get_trend_recommendation(
        self,
        trend: str,
        rate_of_change: float,
        current_value: float,
        hours_until_dry: Optional[float]
    ) -> str:
        """
        Đưa ra đề xuất dựa trên xu hướng độ ẩm đất.
        
        Args:
            trend: Xu hướng (decreasing, stable, increasing)
            rate_of_change: Tốc độ thay đổi (%/giờ)
            current_value: Giá trị hiện tại
            hours_until_dry: Số giờ đến khi đất khô
            
        Returns:
            str: Đề xuất
        """
        if trend == "unknown":
            return "collect_more_data"
            
        if current_value < self.min_threshold:
            return "water_immediately"
            
        if trend == "decreasing":
            if hours_until_dry and hours_until_dry < 3:
                return "water_soon"
            elif hours_until_dry and hours_until_dry < 12:
                return "schedule_watering"
            elif current_value < self.optimal_min:
                return "monitor_closely"
            else:
                return "normal_monitoring"
        elif trend == "stable":
            if current_value < self.optimal_min:
                return "consider_watering"
            elif current_value > self.optimal_max:
                return "monitor_for_excess"
            else:
                return "maintain_current_conditions"
        else:  # increasing
            if current_value > self.max_threshold:
                return "stop_watering"
            elif current_value > self.optimal_max:
                return "reduce_watering"
            else:
                return "normal_monitoring"