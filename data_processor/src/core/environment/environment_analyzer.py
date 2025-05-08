"""
Analyzer tổng hợp cho toàn bộ môi trường.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.core.data.models import (
    SensorType,
    SensorStatus,
    SensorReading,
    EnvironmentSnapshot
)
from src.core.environment.analyzers import (
    SoilMoistureAnalyzer,
    TemperatureAnalyzer,
    HumidityAnalyzer,
    LightAnalyzer
)

logger = logging.getLogger(__name__)

class EnvironmentAnalyzer:
    """
    Analyzer tổng hợp cho toàn bộ môi trường.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(EnvironmentAnalyzer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo EnvironmentAnalyzer."""
        if self._initialized:
            return
            
        logger.info("Initializing EnvironmentAnalyzer")
        
        # Khởi tạo các analyzers chuyên biệt
        self.analyzers = {
            SensorType.SOIL_MOISTURE: SoilMoistureAnalyzer(),
            SensorType.TEMPERATURE: TemperatureAnalyzer(),
            SensorType.HUMIDITY: HumidityAnalyzer(),
            SensorType.LIGHT: LightAnalyzer()
        }
        
        self._initialized = True
        logger.info("EnvironmentAnalyzer initialized")
    
    def analyze_reading(self, reading: SensorReading) -> Dict[str, Any]:
        """
        Phân tích một đọc cảm biến cụ thể.
        
        Args:
            reading: Đọc cảm biến cần phân tích
            
        Returns:
            Dict chứa kết quả phân tích
        """
        sensor_type = reading.sensor_type
        
        if sensor_type not in self.analyzers:
            logger.warning(f"No analyzer available for sensor type: {sensor_type}")
            return {
                "sensor_type": sensor_type,
                "analyzed": False,
                "reason": "no_analyzer_available"
            }
            
        analyzer = self.analyzers[sensor_type]
        
        try:
            result = analyzer.analyze(reading)
            return {
                "sensor_type": sensor_type,
                "analyzed": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error analyzing {sensor_type} reading: {str(e)}")
            return {
                "sensor_type": sensor_type,
                "analyzed": False,
                "reason": "analysis_error",
                "error": str(e)
            }
    
    def analyze_snapshot(self, snapshot: EnvironmentSnapshot) -> Dict[str, Any]:
        """
        Phân tích toàn bộ snapshot môi trường.
        
        Args:
            snapshot: Snapshot môi trường cần phân tích
            
        Returns:
            Dict chứa kết quả phân tích
        """
        results = {}
        
        # Phân tích từng thành phần trong snapshot
        if snapshot.soil_moisture:
            results[SensorType.SOIL_MOISTURE] = self.analyze_reading(snapshot.soil_moisture)
            
        if snapshot.temperature:
            results[SensorType.TEMPERATURE] = self.analyze_reading(snapshot.temperature)
            
        if snapshot.humidity:
            results[SensorType.HUMIDITY] = self.analyze_reading(snapshot.humidity)
            
        if snapshot.light:
            results[SensorType.LIGHT] = self.analyze_reading(snapshot.light)
            
        # Tổng hợp và đưa ra khuyến nghị
        overall_status = snapshot.get_overall_status()
        irrigation_recommendation = self._generate_irrigation_recommendation(snapshot, results)
        
        return {
            "timestamp": snapshot.timestamp,
            "overall_status": overall_status,
            "analysis": {key.value: value for key, value in results.items()},
            "irrigation_recommendation": irrigation_recommendation,
            "action_items": self._generate_action_items(snapshot, results, overall_status)
        }
    
    def _generate_irrigation_recommendation(
        self,
        snapshot: EnvironmentSnapshot,
        analysis_results: Dict[SensorType, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Tạo khuyến nghị tưới nước dựa trên phân tích.
        
        Args:
            snapshot: Snapshot môi trường
            analysis_results: Kết quả phân tích
            
        Returns:
            Dict chứa khuyến nghị tưới nước
        """
        needs_water = False
        urgency = "none"
        reason = ""
        
        # Kiểm tra độ ẩm đất
        if SensorType.SOIL_MOISTURE in analysis_results and analysis_results[SensorType.SOIL_MOISTURE]["analyzed"]:
            soil_result = analysis_results[SensorType.SOIL_MOISTURE]["result"]
            
            if soil_result.get("needs_water", False):
                needs_water = True
                risk_level = soil_result.get("risk_level", "none")
                
                if risk_level in ["extreme", "high"]:
                    urgency = "high"
                    reason = "soil_too_dry"
                elif risk_level == "medium":
                    urgency = "medium"
                    reason = "soil_somewhat_dry"
        
        # Kiểm tra nhiệt độ cao
        if (
            SensorType.TEMPERATURE in analysis_results and 
            analysis_results[SensorType.TEMPERATURE]["analyzed"] and 
            not needs_water  # Chỉ kiểm tra nếu chưa quyết định tưới
        ):
            temp_result = analysis_results[SensorType.TEMPERATURE]["result"]
            
            if temp_result.get("status") in [SensorStatus.CRITICAL, SensorStatus.WARNING]:
                stress_level = temp_result.get("stress_level", "none")
                
                if stress_level in ["extreme", "high"] and temp_result.get("value", 0) > 30:
                    needs_water = True
                    urgency = "medium"
                    reason = "high_temperature"
        
        # Kiểm tra độ ẩm không khí thấp
        if (
            SensorType.HUMIDITY in analysis_results and 
            analysis_results[SensorType.HUMIDITY]["analyzed"] and 
            urgency == "none"  # Chỉ kiểm tra nếu chưa có lý do khẩn cấp
        ):
            humidity_result = analysis_results[SensorType.HUMIDITY]["result"]
            
            if humidity_result.get("condition") in ["very_dry", "dry"] and needs_water:
                # Tăng mức khẩn cấp nếu cả độ ẩm đất thấp và độ ẩm không khí thấp
                urgency = "high"
                reason += "_with_dry_air"
        
        # Xác định lượng nước đề xuất
        water_amount = "none"
        if needs_water:
            if urgency == "high":
                water_amount = "heavy"
            elif urgency == "medium":
                water_amount = "moderate"
            else:
                water_amount = "light"
        
        return {
            "needs_water": needs_water,
            "urgency": urgency,
            "reason": reason,
            "recommended_water_amount": water_amount,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_action_items(
        self,
        snapshot: EnvironmentSnapshot,
        analysis_results: Dict[SensorType, Dict[str, Any]],
        overall_status: SensorStatus
    ) -> List[Dict[str, Any]]:
        """
        Tạo danh sách các hành động đề xuất.
        
        Args:
            snapshot: Snapshot môi trường
            analysis_results: Kết quả phân tích
            overall_status: Trạng thái tổng thể
            
        Returns:
            List các hành động đề xuất
        """
        action_items = []
        
        # Thêm hành động tưới nước nếu cần
        if SensorType.SOIL_MOISTURE in analysis_results and analysis_results[SensorType.SOIL_MOISTURE]["analyzed"]:
            soil_result = analysis_results[SensorType.SOIL_MOISTURE]["result"]
            
            if soil_result.get("needs_water", False):
                action_items.append({
                    "action": "water_plants",
                    "priority": "high" if soil_result.get("risk_level") in ["extreme", "high"] else "medium",
                    "details": f"Soil moisture is low ({soil_result.get('value', 0)}{soil_result.get('unit', '')})"
                })
        
        # Thêm hành động về nhiệt độ nếu cần
        if SensorType.TEMPERATURE in analysis_results and analysis_results[SensorType.TEMPERATURE]["analyzed"]:
            temp_result = analysis_results[SensorType.TEMPERATURE]["result"]
            
            if temp_result.get("status") in [SensorStatus.CRITICAL, SensorStatus.WARNING]:
                if temp_result.get("value", 0) > 35:
                    action_items.append({
                        "action": "reduce_temperature",
                        "priority": "high",
                        "details": f"Temperature is too high ({temp_result.get('value', 0)}{temp_result.get('unit', '')})"
                    })
                elif temp_result.get("value", 0) < 15:
                    action_items.append({
                        "action": "increase_temperature",
                        "priority": "high",
                        "details": f"Temperature is too low ({temp_result.get('value', 0)}{temp_result.get('unit', '')})"
                    })
        
        # Thêm hành động về độ ẩm không khí nếu cần
        if SensorType.HUMIDITY in analysis_results and analysis_results[SensorType.HUMIDITY]["analyzed"]:
            humidity_result = analysis_results[SensorType.HUMIDITY]["result"]
            
            if humidity_result.get("disease_risk") in ["severe", "high"]:
                action_items.append({
                    "action": "improve_air_circulation",
                    "priority": "medium",
                    "details": f"High humidity may cause diseases ({humidity_result.get('value', 0)}{humidity_result.get('unit', '')})"
                })
        
        # Thêm hành động về ánh sáng nếu cần
        if SensorType.LIGHT in analysis_results and analysis_results[SensorType.LIGHT]["analyzed"]:
            light_result = analysis_results[SensorType.LIGHT]["result"]
            
            if light_result.get("status") in [SensorStatus.CRITICAL, SensorStatus.WARNING]:
                if light_result.get("value", 0) < 200:
                    action_items.append({
                        "action": "increase_light",
                        "priority": "medium",
                        "details": f"Light level is too low ({light_result.get('value', 0)}{light_result.get('unit', '')})"
                    })
        
        return action_items