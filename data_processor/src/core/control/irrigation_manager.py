"""
Quản lý tổng hợp hệ thống tưới.
"""
import logging
import json
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Tránh circular import ở đây
# from src.infrastructure import ServiceFactory
from src.adapters.cloud.actuators.water_pump import WaterPumpController
from src.core.control.scheduling import IrrigationScheduler
from src.core.control.irrigation import IrrigationDecisionMaker

logger = logging.getLogger(__name__)

class IrrigationManager:
    """
    Quản lý tổng hợp hệ thống tưới.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(IrrigationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo IrrigationManager."""
        if self._initialized:
            return
            
        logger.info("Initializing IrrigationManager")
        
        # Khởi tạo các services (lazy import để tránh circular import)
        from src.infrastructure import get_service_factory
        factory = get_service_factory()
        self.config = factory.get_config_loader()
        
        # Khởi tạo các thành phần
        self.pump_controller = WaterPumpController()
        self.scheduler = IrrigationScheduler()
        self.decision_maker = IrrigationDecisionMaker()
        
        # Biến theo dõi trạng thái
        self.background_thread = None
        self.is_running = False
        
        # Lấy interval từ cấu hình mới
        self.check_interval = self.config.get_interval('auto_decision', 900)
        logger.info(f"IrrigationManager initialized with check interval: {self.check_interval}s")
        
        # Đồng bộ trạng thái
        self._initialized = True
        logger.info("IrrigationManager initialized")
    
    def start_system(self) -> Dict[str, Any]:
        """
        Khởi động toàn bộ hệ thống tưới.
        
        Returns:
            Dict chứa kết quả
        """
        result = {
            "success": True,
            "components": {}
        }
        
        # Khởi động scheduler
        try:
            scheduler_result = self.scheduler.start_background_checking()
            result["components"]["scheduler"] = {
                "success": scheduler_result,
                "message": "Irrigation scheduler started" if scheduler_result else "Failed to start irrigation scheduler"
            }
        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}")
            result["components"]["scheduler"] = {
                "success": False,
                "message": f"Error: {str(e)}"
            }
            result["success"] = False
            
        # Khởi động auto decision maker
        try:
            self.start_background_decisions()
            result["components"]["auto_decision"] = {
                "success": True,
                "message": "Auto decision maker started"
            }
        except Exception as e:
            logger.error(f"Error starting auto decision maker: {str(e)}")
            result["components"]["auto_decision"] = {
                "success": False,
                "message": f"Error: {str(e)}"
            }
            result["success"] = False
            
        return result
    
    def stop_system(self) -> Dict[str, Any]:
        """
        Dừng toàn bộ hệ thống tưới.
        
        Returns:
            Dict chứa kết quả
        """
        result = {
            "success": True,
            "components": {}
        }
        
        # Dừng scheduler
        try:
            scheduler_result = self.scheduler.stop_background_checking()
            result["components"]["scheduler"] = {
                "success": scheduler_result,
                "message": "Irrigation scheduler stopped" if scheduler_result else "Failed to stop irrigation scheduler"
            }
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
            result["components"]["scheduler"] = {
                "success": False,
                "message": f"Error: {str(e)}"
            }
            result["success"] = False
            
        # Dừng auto decision maker
        try:
            self.stop_background_decisions()
            result["components"]["auto_decision"] = {
                "success": True,
                "message": "Auto decision maker stopped"
            }
        except Exception as e:
            logger.error(f"Error stopping auto decision maker: {str(e)}")
            result["components"]["auto_decision"] = {
                "success": False,
                "message": f"Error: {str(e)}"
            }
            result["success"] = False
            
        # Đảm bảo máy bơm đã tắt
        try:
            pump_status = self.pump_controller.get_status()
            if pump_status["is_on"]:
                stop_result = self.pump_controller.turn_off(source="system", details={"reason": "system_shutdown"})
                result["components"]["pump"] = {
                    "success": stop_result["success"],
                    "message": "Water pump stopped" if stop_result["success"] else "Failed to stop water pump"
                }
            else:
                result["components"]["pump"] = {
                    "success": True,
                    "message": "Water pump already OFF"
                }
        except Exception as e:
            logger.error(f"Error stopping pump: {str(e)}")
            result["components"]["pump"] = {
                "success": False,
                "message": f"Error: {str(e)}"
            }
            result["success"] = False
            
        return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái tổng hợp của hệ thống tưới.
        
        Returns:
            Dict chứa trạng thái hệ thống
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "pump": self.pump_controller.get_status(),
            "scheduler": {
                "active": self.scheduler.is_running,
                "schedules_count": len(self.scheduler.get_schedules()),
                "schedules": self.scheduler.get_schedules()
            },
            "auto_irrigation": {
                "enabled": self.decision_maker.is_auto_irrigation_enabled(),
                "active": self.is_running,
                "config": self.decision_maker.get_configuration(),
                "last_decision": self.decision_maker.get_last_decision()
            }
        }
        
        return status
    
    def manually_control_pump(self, action: str, duration: int = 300) -> Dict[str, Any]:
        """
        Điều khiển thủ công máy bơm nước.
        
        Args:
            action: 'on' hoặc 'off'
            duration: Thời gian tưới nếu bật (giây)
            
        Returns:
            Dict chứa kết quả điều khiển
        """
        if action.lower() == "on":
            return self.pump_controller.turn_on(duration=duration, source="manual")
        elif action.lower() == "off":
            return self.pump_controller.turn_off(source="manual")
        else:
            return {
                "success": False,
                "message": f"Invalid action: {action}. Valid actions: 'on' or 'off'"
            }
    
    def start_background_decisions(self) -> bool:
        """
        Bắt đầu kiểm tra và đưa ra quyết định tưới tự động ngầm.
        
        Returns:
            bool: Thành công hay thất bại
        """
        if self.is_running:
            logger.warning("Background decision making is already running")
            return False
            
        self.is_running = True
        
        def decision_worker():
            logger.info(f"Starting background decision making every {self.check_interval} seconds")
            while self.is_running:
                try:
                    # Kiểm tra xem có thể đưa ra quyết định không
                    if self.decision_maker.is_auto_irrigation_enabled():
                        check_result = self.decision_maker.can_make_decision()
                        
                        if check_result["can_decide"]:
                            # Đưa ra quyết định
                            result = self.decision_maker.make_decision()
                            
                            if result["success"] and result["decision"]["needs_water"]:
                                logger.info(f"Auto irrigation triggered: {result['decision']['reason']}")
                        else:
                            logger.debug(f"Cannot make decision: {check_result['reason']}")
                except Exception as e:
                    logger.error(f"Error in background decision making: {str(e)}")
                    
                # Sleep for the specified interval
                for _ in range(self.check_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
        
        self.background_thread = threading.Thread(target=decision_worker)
        self.background_thread.daemon = True
        self.background_thread.start()
        
        return True
    
    def stop_background_decisions(self) -> bool:
        """
        Dừng kiểm tra và đưa ra quyết định tưới tự động ngầm.
        
        Returns:
            bool: Thành công hay thất bại
        """
        if not self.is_running:
            logger.warning("Background decision making is not running")
            return False
            
        self.is_running = False
        
        if self.background_thread:
            self.background_thread.join(timeout=5.0)
            
        logger.info("Background decision making stopped")
        return True
    
    def trigger_manual_decision(self) -> Dict[str, Any]:
        """
        Kích hoạt quyết định tưới thủ công.
        
        Returns:
            Dict chứa kết quả quyết định
        """
        return self.decision_maker.make_decision()
    
    def get_irrigation_history(self) -> Dict[str, Any]:
        """
        Lấy lịch sử tưới tổng hợp.
        
        Returns:
            Dict chứa lịch sử tưới
        """
        pump_history = self.pump_controller.get_irrigation_history(limit=20)
        decision_history = self.decision_maker.get_decision_history(limit=20)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "irrigation_events": pump_history,
            "auto_decisions": decision_history,
            "statistics": self.pump_controller.calculate_statistics()
        }
    def process_ai_recommendation(self, recommendation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Xử lý khuyến nghị tưới từ AI Service.
        
        Args:
            recommendation_data: Dữ liệu khuyến nghị từ AI Service
            
        Returns:
            Dict chứa kết quả xử lý
        """
        logger.info(f"Received AI recommendation: {recommendation_data}")
        
        # Trích xuất dữ liệu
        source = recommendation_data.get("source", "unknown")
        priority = recommendation_data.get("priority", "normal")
        recommendation = recommendation_data.get("recommendation", {})
        
        # Kiểm tra cấu hình để xem có áp dụng khuyến nghị hay không
        config = self.config.get('control.ai_recommendation', {})
        apply_recommendations = config.get('enabled', False)
        allowed_sources = config.get('allowed_sources', [])
        
        if not apply_recommendations:
            return {
                "success": False,
                "message": "AI recommendations are disabled",
                "accepted": False
            }
        
        if source not in allowed_sources and 'all' not in allowed_sources:
            return {
                "success": False,
                "message": f"Source '{source}' is not allowed",
                "accepted": False
            }
        
        # Kiểm tra xem khuyến nghị có đề xuất tưới không
        should_irrigate = recommendation.get("should_irrigate", False)
        duration_minutes = recommendation.get("duration_minutes", 0)
        zones = recommendation.get("zones", None)
        
        if should_irrigate and duration_minutes > 0:
            # Nếu đây là khuyến nghị ưu tiên cao, thực hiện ngay
            if priority == "high":
                if zones:
                    # Xử lý tưới theo từng vùng (cần triển khai)
                    result = self._handle_zone_irrigation(zones)
                else:
                    # Tưới toàn bộ
                    result = self.manually_control_pump("on", duration_minutes * 60, source="ai_recommendation")
                
                return {
                    "success": result["success"],
                    "message": f"Applied high priority AI recommendation: {result['message']}",
                    "accepted": True,
                    "action_taken": "immediate_irrigation"
                }
            else:
                # Lưu vào hàng đợi để xem xét trong chu kỳ quyết định tiếp theo
                self._queue_recommendation(recommendation)
                
                return {
                    "success": True,
                    "message": "Recommendation queued for next decision cycle",
                    "accepted": True,
                    "action_taken": "queued"
                }
        else:
            return {
                "success": True,
                "message": "Recommendation received but no irrigation action needed",
                "accepted": True,
                "action_taken": "none"
            }

    def _queue_recommendation(self, recommendation):
        """Lưu khuyến nghị vào hàng đợi."""
        # Thực hiện lưu vào Redis hoặc bộ nhớ
        recommendation_key = f"{self.redis_key_prefix}ai_recommendation"
        self.redis_client.set(recommendation_key, recommendation)