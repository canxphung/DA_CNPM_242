"""
Hệ thống quyết định tưới nước tự động dựa trên phân tích môi trường.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Tránh circular import
# from src.infrastructure import ServiceFactory
from src.core.data import (
    DataManager,
    SensorType,
    SensorStatus
)
from src.core.environment import EnvironmentAnalyzer
from src.adapters.cloud.actuators.water_pump import WaterPumpController

logger = logging.getLogger(__name__)

class IrrigationDecisionMaker:
    """
    Hệ thống quyết định tưới nước tự động.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(IrrigationDecisionMaker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo IrrigationDecisionMaker."""
        if self._initialized:
            return
            
        logger.info("Initializing IrrigationDecisionMaker")
        
        # Khởi tạo các services (lazy import để tránh circular import)
        from src.infrastructure import get_service_factory
        factory = get_service_factory()
        self.config = factory.get_config_loader()
        self.redis_client = factory.create_redis_client()
        self.firebase_client = factory.create_firebase_client("irrigation_decisions")
        
        # Khóa Redis
        self.redis_key_prefix = self.config.get('redis.key_prefixes.irrigation_decisions', 'decision:')
        self.redis_last_decision_key = f"{self.redis_key_prefix}last"
        self.redis_history_key = f"{self.redis_key_prefix}history"
        
        # Các phụ thuộc
        self.data_manager = DataManager()
        self.environment_analyzer = EnvironmentAnalyzer()
        self.pump_controller = WaterPumpController()
        
        # Cấu hình tưới
        self.min_decision_interval = int(self.config.get('control.auto_irrigation.min_decision_interval', 3600))  # giây
        self.enabled = bool(self.config.get('control.auto_irrigation.enabled', False))
        
        # Tham số tưới
        self.moisture_thresholds = {
            "critical": float(self.config.get('control.auto_irrigation.moisture_critical', 20.0)),
            "low": float(self.config.get('control.auto_irrigation.moisture_low', 30.0)),
            "optimal": float(self.config.get('control.auto_irrigation.moisture_optimal', 50.0))
        }
        
        self.watering_durations = {
            "light": int(self.config.get('control.auto_irrigation.duration_light', 60)),  # 1 phút
            "normal": int(self.config.get('control.auto_irrigation.duration_normal', 180)),  # 3 phút
            "heavy": int(self.config.get('control.auto_irrigation.duration_heavy', 300))  # 5 phút
        }
        
        self._initialized = True
        logger.info("IrrigationDecisionMaker initialized")
    
    def is_auto_irrigation_enabled(self) -> bool:
        """
        Kiểm tra xem tưới tự động có được bật không.
        
        Returns:
            bool: True nếu tưới tự động được bật
        """
        return self.enabled
    
    def enable_auto_irrigation(self, enabled: bool = True) -> Dict[str, Any]:
        """
        Bật/tắt tưới tự động.
        
        Args:
            enabled: Trạng thái bật/tắt
            
        Returns:
            Dict chứa kết quả
        """
        self.enabled = enabled
        
        # Lưu cấu hình
        try:
            self.firebase_client.set("config/auto_irrigation_enabled", enabled)
            self.redis_client.hset("config", "auto_irrigation_enabled", enabled)
            
            logger.info(f"Auto irrigation {'enabled' if enabled else 'disabled'}")
            
            return {
                "success": True,
                "message": f"Auto irrigation {'enabled' if enabled else 'disabled'}",
                "enabled": enabled
            }
        except Exception as e:
            logger.error(f"Error setting auto irrigation state: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "enabled": self.enabled
            }
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Lấy cấu hình tưới tự động.
        
        Returns:
            Dict chứa cấu hình
        """
        return {
            "enabled": self.enabled,
            "min_decision_interval_seconds": self.min_decision_interval,
            "moisture_thresholds": self.moisture_thresholds,
            "watering_durations": self.watering_durations
        }
    
    def update_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật cấu hình tưới tự động.
        
        Args:
            config: Cấu hình mới
            
        Returns:
            Dict chứa kết quả
        """
        try:
            # Cập nhật trạng thái bật/tắt
            if 'enabled' in config:
                self.enabled = bool(config['enabled'])
                
            # Cập nhật khoảng thời gian tối thiểu
            if 'min_decision_interval' in config:
                new_interval = int(config['min_decision_interval'])
                if new_interval >= 60:  # Ít nhất 1 phút
                    self.min_decision_interval = new_interval
                    
            # Cập nhật ngưỡng độ ẩm
            if 'moisture_thresholds' in config and isinstance(config['moisture_thresholds'], dict):
                for key, value in config['moisture_thresholds'].items():
                    if key in self.moisture_thresholds and isinstance(value, (int, float)):
                        self.moisture_thresholds[key] = float(value)
                        
            # Cập nhật thời lượng tưới
            if 'watering_durations' in config and isinstance(config['watering_durations'], dict):
                for key, value in config['watering_durations'].items():
                    if key in self.watering_durations and isinstance(value, int):
                        self.watering_durations[key] = int(value)
                        
            # Lưu cấu hình
            self.firebase_client.set("config", {
                "auto_irrigation_enabled": self.enabled,
                "min_decision_interval": self.min_decision_interval,
                "moisture_thresholds": self.moisture_thresholds,
                "watering_durations": self.watering_durations
            })
            
            logger.info("Updated auto irrigation configuration")
            
            return {
                "success": True,
                "message": "Configuration updated successfully",
                "config": self.get_configuration()
            }
            
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "config": self.get_configuration()
            }
    
    def get_last_decision(self) -> Optional[Dict[str, Any]]:
        """
        Lấy quyết định tưới gần đây nhất.
        
        Returns:
            Dict chứa quyết định gần đây nhất hoặc None
        """
        try:
            # Thử lấy từ Redis
            last_decision = self.redis_client.get(self.redis_last_decision_key)
            
            if last_decision:
                return last_decision
                
            # Nếu không có trong Redis, lấy từ Firebase
            last_decision = self.firebase_client.get("last_decision")
            
            # Lưu vào Redis để truy cập nhanh lần sau
            if last_decision:
                self.redis_client.set(self.redis_last_decision_key, last_decision)
                
            return last_decision
            
        except Exception as e:
            logger.error(f"Error getting last decision: {str(e)}")
            return None
    
    def can_make_decision(self) -> Dict[str, Any]:
        """
        Kiểm tra xem có thể đưa ra quyết định tưới không.
        
        Returns:
            Dict chứa kết quả kiểm tra
        """
        # Kiểm tra xem tưới tự động có bật không
        if not self.enabled:
            return {
                "can_decide": False,
                "reason": "auto_irrigation_disabled"
            }
            
        # Kiểm tra xem máy bơm có đang chạy không
        pump_status = self.pump_controller.get_status()
        if pump_status["is_on"]:
            return {
                "can_decide": False,
                "reason": "pump_already_running"
            }
            
        # Kiểm tra thời gian tối thiểu giữa các quyết định
        last_decision = self.get_last_decision()
        
        if last_decision:
            last_time = datetime.fromisoformat(last_decision.get("timestamp"))
            time_since_last = (datetime.now() - last_time).total_seconds()
            
            if time_since_last < self.min_decision_interval:
                return {
                    "can_decide": False,
                    "reason": "min_interval_not_met",
                    "time_remaining": self.min_decision_interval - time_since_last,
                    "last_decision": last_decision
                }
                
        # Kiểm tra xem có dữ liệu cảm biến độ ẩm đất không
        soil_reading = self.data_manager.collectors[SensorType.SOIL_MOISTURE].get_latest_reading_from_cache()
        
        if not soil_reading:
            return {
                "can_decide": False,
                "reason": "no_soil_moisture_data"
            }
            
        # Tất cả các điều kiện đã đáp ứng
        return {
            "can_decide": True
        }
    
    def _get_ai_recommendation(self) -> Optional[Dict[str, Any]]:
        """Lấy khuyến nghị AI gần đây nhất từ Redis."""
        recommendation_key = f"{self.redis_key_prefix}ai_recommendation"
        recommendation = self.redis_client.get(recommendation_key)
        
        # Xóa khuyến nghị sau khi đã sử dụng
        if recommendation:
            self.redis_client.delete(recommendation_key)
        
        return recommendation
    
    def make_decision(self) -> Dict[str, Any]:
        """
        Đưa ra quyết định tưới nước dựa trên phân tích môi trường.
        
        Returns:
            Dict chứa quyết định tưới
        """
        now = datetime.now()
        
        # Kiểm tra điều kiện trước khi quyết định
        check_result = self.can_make_decision()
        
        if not check_result["can_decide"]:
            return {
                "success": False,
                "timestamp": now.isoformat(),
                "message": f"Cannot make decision: {check_result['reason']}",
                "details": check_result
            }
            
        try:
            # Thu thập và phân tích dữ liệu môi trường
            logger.info("Making irrigation decision based on environment analysis")
            
            # Lấy snapshot môi trường
            snapshot = self.data_manager.get_environment_snapshot(collect_if_needed=True)
            
            # Phân tích snapshot
            analysis = self.environment_analyzer.analyze_snapshot(snapshot)
            
            # Lấy khuyến nghị tưới từ phân tích
            irrigation_rec = analysis.get("irrigation_recommendation", {})
            ai_recommendation = self._get_ai_recommendation()
    
            
            # Tạo quyết định
            decision = {
                "timestamp": now.isoformat(),
                "needs_water": irrigation_rec.get("needs_water", False),
                "urgency": irrigation_rec.get("urgency", "none"),
                "reason": irrigation_rec.get("reason", ""),
                "water_amount": irrigation_rec.get("recommended_water_amount", "none"),
                "analysis_summary": {
                    "overall_status": analysis.get("overall_status"),
                    "soil_moisture": None
                },
                "action_taken": None
            }

            # Ai recommendation
            if ai_recommendation:
                # Nếu có khuyến nghị AI gần đây và đáng tin cậy
                ai_confidence = ai_recommendation.get("confidence", 0)
                ai_should_irrigate = ai_recommendation.get("should_irrigate", False)
                ai_duration = ai_recommendation.get("duration_minutes", 0)
                
                if ai_confidence >= self.config.get('control.ai_recommendation.min_confidence', 0.7):
                    logger.info(f"Using AI recommendation: irrigate={ai_should_irrigate}, duration={ai_duration}min")
                    
                    # Ghi đè quyết định với khuyến nghị AI
                    decision["needs_water"] = ai_should_irrigate
                    decision["water_amount"] = "heavy" if ai_duration > 15 else "moderate" if ai_duration > 5 else "light"
                    decision["reason"] = ai_recommendation.get("reason", decision["reason"]) + " (AI recommended)"
            
            # Thêm dữ liệu độ ẩm đất vào tóm tắt
            if snapshot.soil_moisture:
                decision["analysis_summary"]["soil_moisture"] = {
                    "value": snapshot.soil_moisture.value,
                    "unit": snapshot.soil_moisture.unit,
                    "status": snapshot.soil_moisture.status
                }
                
            # Xác định xem có cần tưới không
            if decision["needs_water"]:
                # Xác định thời lượng tưới dựa trên mức độ khẩn cấp
                watering_amount = decision["water_amount"]
                
                if watering_amount == "heavy":
                    duration = self.watering_durations["heavy"]
                elif watering_amount == "moderate":
                    duration = self.watering_durations["normal"]
                else:
                    duration = self.watering_durations["light"]
                    
                # Kích hoạt máy bơm
                pump_result = self.pump_controller.turn_on(
                    duration=duration,
                    source="auto",
                    details={
                        "decision_timestamp": now.isoformat(),
                        "urgency": decision["urgency"],
                        "reason": decision["reason"]
                    }
                )
                
                # Cập nhật kết quả
                decision["action_taken"] = {
                    "action": "irrigation_started",
                    "duration": duration,
                    "success": pump_result["success"],
                    "message": pump_result["message"]
                }
                
                logger.info(f"Auto irrigation decision: WATER for {duration}s (Reason: {decision['reason']})")
            else:
                logger.info("Auto irrigation decision: NO WATER NEEDED")
                decision["action_taken"] = {
                    "action": "no_action",
                    "message": "No irrigation needed"
                }
                
            # Lưu quyết định
            self._save_decision(decision)
            
            return {
                "success": True,
                "decision": decision
            }
            
        except Exception as e:
            logger.error(f"Error making irrigation decision: {str(e)}")
            return {
                "success": False,
                "timestamp": now.isoformat(),
                "message": f"Error: {str(e)}"
            }
    
    def _save_decision(self, decision: Dict[str, Any]) -> None:
        """
        Lưu quyết định tưới vào storage.
        
        Args:
            decision: Quyết định cần lưu
        """
        try:
            # Lưu vào Redis
            self.redis_client.set(self.redis_last_decision_key, decision)
            
            # Thêm vào danh sách lịch sử
            self.redis_client.redis.lpush(self.redis_history_key, json.dumps(decision))
            # Giữ chỉ 100 quyết định gần nhất
            self.redis_client.redis.ltrim(self.redis_history_key, 0, 99)
            
            # Lưu vào Firebase
            self.firebase_client.set("last_decision", decision)
            self.firebase_client.push("decision_history", decision)
            
            logger.debug(f"Saved irrigation decision at {decision['timestamp']}")
            
        except Exception as e:
            logger.error(f"Error saving decision: {str(e)}")
    
    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử quyết định tưới.
        
        Args:
            limit: Số lượng bản ghi tối đa
            
        Returns:
            List chứa lịch sử quyết định
        """
        try:
            # Thử lấy từ Redis
            history = self.redis_client.redis.lrange(self.redis_history_key, 0, limit - 1)
            
            if history:
                return [json.loads(item) for item in history]
                
            # Nếu không có trong Redis, lấy từ Firebase
            history_data = self.firebase_client.get("decision_history", default={})
            
            if not history_data:
                return []
                
            # Chuyển đổi từ dict thành list
            history = []
            for key, value in history_data.items():
                if isinstance(value, dict):
                    value["id"] = key
                    history.append(value)
                    
            # Sắp xếp theo thời gian giảm dần
            history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Giới hạn số lượng
            return history[:limit]
            
        except Exception as e:
            logger.error(f"Error getting decision history: {str(e)}")
            return []