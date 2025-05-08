"""
Module điều khiển máy bơm nước thông qua Adafruit IO.
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
# Sử dụng lazy import để tránh circular import
from typing import List

logger = logging.getLogger(__name__)

class WaterPumpController:
    """
    Điều khiển máy bơm nước thông qua Adafruit IO.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(WaterPumpController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo WaterPumpController."""
        if self._initialized:
            return
            
        logger.info("Initializing WaterPumpController")
        
        # Khởi tạo các services (lazy import để tránh circular import)
        from src.infrastructure import get_service_factory
        factory = get_service_factory()
        self.config = factory.get_config_loader()
        self.adafruit_client = factory.create_adafruit_client()
        self.redis_client = factory.create_redis_client()
        self.firebase_client = factory.create_firebase_client("irrigation_events")
        
        # Lấy khóa feed từ cấu hình
        self.feed_key = self.config.get_actuator_feed_key("water_pump")
        if not self.feed_key:
            logger.warning("No feed key configured for water pump")
        
        # Khóa Redis cho trạng thái máy bơm
        self.redis_key_prefix = self.config.get('redis.key_prefixes.water_pump_state', 'pump:')
        self.redis_state_key = f"{self.redis_key_prefix}state"
        
        # Giới hạn thời gian tưới bảo vệ (mặc định: 30 phút)
        self.max_runtime = int(self.config.get('control.water_pump.max_runtime', 1800))  # giây
        
        # Thời gian chờ giữa các lần tưới (mặc định: 1 giờ)
        self.min_interval = int(self.config.get('control.water_pump.min_interval', 3600))  # giây
        
        # Các giá trị có thể cấu hình
        self.water_rate = float(self.config.get('control.water_pump.water_rate', 0.5))  # lít/giây
        
        # Trạng thái hiện tại
        self._current_state = {
            "is_on": False,
            "start_time": None,
            "scheduled_stop_time": None,
            "last_on_time": None,
            "last_off_time": None,
            "total_runtime_seconds": 0,
            "total_water_used": 0.0  # Lít
        }
        
        # Đọc trạng thái hiện tại từ Redis
        self._load_state()
        
        # Đồng bộ trạng thái với Adafruit
        self._sync_state_with_adafruit()
        
        self._initialized = True
        logger.info(f"WaterPumpController initialized with feed key: {self.feed_key}")
    
    def _load_state(self) -> None:
        """Đọc trạng thái từ Redis."""
        try:
            state = self.redis_client.get(self.redis_state_key)
            if state:
                # Chuyển đổi các trường thời gian từ string về datetime
                if 'start_time' in state and state['start_time']:
                    state['start_time'] = datetime.fromisoformat(state['start_time'])
                    
                if 'scheduled_stop_time' in state and state['scheduled_stop_time']:
                    state['scheduled_stop_time'] = datetime.fromisoformat(state['scheduled_stop_time'])
                    
                if 'last_on_time' in state and state['last_on_time']:
                    state['last_on_time'] = datetime.fromisoformat(state['last_on_time'])
                    
                if 'last_off_time' in state and state['last_off_time']:
                    state['last_off_time'] = datetime.fromisoformat(state['last_off_time'])
                    
                self._current_state.update(state)
                logger.debug(f"Loaded pump state from Redis: {self._current_state}")
        except Exception as e:
            logger.error(f"Error loading pump state from Redis: {str(e)}")
    
    def _save_state(self) -> bool:
        """
        Lưu trạng thái vào Redis.
        
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Chuyển đổi các trường datetime thành string để lưu vào Redis
            state_to_save = self._current_state.copy()
            
            for key in ['start_time', 'scheduled_stop_time', 'last_on_time', 'last_off_time']:
                if key in state_to_save and state_to_save[key]:
                    state_to_save[key] = state_to_save[key].isoformat()
            
            self.redis_client.set(self.redis_state_key, state_to_save)
            return True
        except Exception as e:
            logger.error(f"Error saving pump state to Redis: {str(e)}")
            return False
    
    def _sync_state_with_adafruit(self) -> None:
        """Đồng bộ trạng thái với Adafruit IO."""
        try:
            # Lấy trạng thái hiện tại từ Adafruit
            adafruit_state = self.adafruit_client.get_actuator_state(self.feed_key)
            
            if adafruit_state is None:
                logger.warning("Could not get pump state from Adafruit")
                return
                
            # Nếu trạng thái không khớp, cập nhật trạng thái máy bơm
            if adafruit_state != self._current_state["is_on"]:
                logger.warning(f"Pump state mismatch: Redis={self._current_state['is_on']}, Adafruit={adafruit_state}")
                
                if adafruit_state:
                    # Máy bơm đang bật trong Adafruit nhưng tắt trong Redis
                    if self._current_state["start_time"] is None:
                        self._current_state["start_time"] = datetime.now()
                        
                    self._current_state["is_on"] = True
                    logger.info("Synced pump state: Turned ON in local state")
                else:
                    # Máy bơm đang tắt trong Adafruit nhưng bật trong Redis
                    if self._current_state["is_on"] and self._current_state["start_time"]:
                        self._update_runtime()
                        
                    self._current_state["is_on"] = False
                    self._current_state["start_time"] = None
                    self._current_state["scheduled_stop_time"] = None
                    logger.info("Synced pump state: Turned OFF in local state")
                    
                self._save_state()
                
        except Exception as e:
            logger.error(f"Error syncing state with Adafruit: {str(e)}")
    
    def _update_runtime(self) -> None:
        """Cập nhật thời gian chạy khi tắt máy bơm."""
        if self._current_state["start_time"]:
            run_duration = (datetime.now() - self._current_state["start_time"]).total_seconds()
            
            # Cập nhật tổng thời gian chạy
            self._current_state["total_runtime_seconds"] += run_duration
            
            # Cập nhật lượng nước đã sử dụng
            water_used = run_duration * self.water_rate
            self._current_state["total_water_used"] += water_used
            
            logger.info(f"Pump ran for {run_duration:.1f} seconds, used {water_used:.2f} liters of water")
    
    def _log_irrigation_event(self, duration: float, amount: float, source: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Ghi lại sự kiện tưới.
        
        Args:
            duration: Thời gian tưới (giây)
            amount: Lượng nước sử dụng (lít)
            source: Nguồn kích hoạt (manual, schedule, auto)
            details: Thông tin chi tiết bổ sung
        """
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "water_amount_liters": amount,
                "source": source,
                "details": details or {}
            }
            
            # Lưu vào Firebase
            self.firebase_client.store_irrigation_event(event)
            
            # Lưu vào Redis để truy cập nhanh
            history_key = f"{self.redis_key_prefix}history"
            self.redis_client.redis.lpush(history_key, json.dumps(event))
            # Giữ chỉ 50 sự kiện gần nhất
            self.redis_client.redis.ltrim(history_key, 0, 49)
            
            logger.info(f"Logged irrigation event: {duration:.1f}s, {amount:.2f}L, source: {source}")
        except Exception as e:
            logger.error(f"Error logging irrigation event: {str(e)}")
    
    def _check_safety_constraints(self) -> Dict[str, Any]:
        """
        Kiểm tra các ràng buộc an toàn trước khi bật máy bơm.
        
        Returns:
            Dict với 'can_start' và 'reason' nếu không thể bật
        """
        # Kiểm tra nếu máy bơm đã đang chạy
        if self._current_state["is_on"]:
            return {
                "can_start": False,
                "reason": "already_running"
            }
            
        # Kiểm tra khoảng thời gian tối thiểu giữa các lần tưới
        if self._current_state["last_off_time"]:
            time_since_last_run = (datetime.now() - self._current_state["last_off_time"]).total_seconds()
            if time_since_last_run < self.min_interval:
                return {
                    "can_start": False,
                    "reason": "min_interval_not_met",
                    "time_remaining": self.min_interval - time_since_last_run
                }
                
        # Tất cả các kiểm tra đã vượt qua
        return {
            "can_start": True
        }
    
    def turn_on(self, duration: int = 300, source: str = "manual", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Bật máy bơm nước.
        
        Args:
            duration: Thời gian tưới (giây)
            source: Nguồn kích hoạt (manual, schedule, auto)
            details: Thông tin chi tiết bổ sung
            
        Returns:
            Dict chứa kết quả với 'success', 'message', và các thông tin khác
        """
        if not self.feed_key:
            return {
                "success": False,
                "message": "No feed key configured for water pump"
            }
            
        # Đồng bộ trạng thái trước khi thực hiện thay đổi
        self._sync_state_with_adafruit()
        
        # Kiểm tra các ràng buộc an toàn
        safety_check = self._check_safety_constraints()
        if not safety_check["can_start"]:
            return {
                "success": False,
                "message": f"Cannot start pump: {safety_check['reason']}",
                "details": safety_check
            }
            
        # Giới hạn thời gian tưới tối đa
        if duration > self.max_runtime:
            duration = self.max_runtime
            logger.warning(f"Requested duration exceeded maximum limit, using {duration}s instead")
            
        try:
            # Gửi lệnh bật máy bơm đến Adafruit
            result = self.adafruit_client.turn_actuator_on(self.feed_key)
            
            if result:
                # Cập nhật trạng thái
                now = datetime.now()
                scheduled_stop = now + timedelta(seconds=duration)
                
                self._current_state["is_on"] = True
                self._current_state["start_time"] = now
                self._current_state["scheduled_stop_time"] = scheduled_stop
                self._current_state["last_on_time"] = now
                
                # Lưu trạng thái
                self._save_state()
                
                return {
                    "success": True,
                    "message": f"Water pump turned ON for {duration} seconds",
                    "start_time": now.isoformat(),
                    "scheduled_stop_time": scheduled_stop.isoformat(),
                    "duration": duration
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to turn ON water pump through Adafruit IO"
                }
                
        except Exception as e:
            logger.error(f"Error turning ON water pump: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def turn_off(self, source: str = "manual", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Tắt máy bơm nước.
        
        Args:
            source: Nguồn kích hoạt (manual, schedule, auto)
            details: Thông tin chi tiết bổ sung
            
        Returns:
            Dict chứa kết quả với 'success', 'message', và các thông tin khác
        """
        if not self.feed_key:
            return {
                "success": False,
                "message": "No feed key configured for water pump"
            }
            
        # Đồng bộ trạng thái trước khi thực hiện thay đổi
        self._sync_state_with_adafruit()
        
        # Kiểm tra xem máy bơm có đang chạy không
        if not self._current_state["is_on"]:
            return {
                "success": False,
                "message": "Water pump is already OFF"
            }
            
        try:
            # Gửi lệnh tắt máy bơm đến Adafruit
            result = self.adafruit_client.turn_actuator_off(self.feed_key)
            
            if result:
                # Tính toán thời gian chạy
                start_time = self._current_state["start_time"]
                now = datetime.now()
                
                if start_time:
                    run_duration = (now - start_time).total_seconds()
                    water_used = run_duration * self.water_rate
                    
                    # Cập nhật tổng thời gian chạy và lượng nước
                    self._current_state["total_runtime_seconds"] += run_duration
                    self._current_state["total_water_used"] += water_used
                    
                    # Ghi lại sự kiện tưới
                    self._log_irrigation_event(run_duration, water_used, source, details)
                else:
                    run_duration = 0
                    water_used = 0
                
                # Cập nhật trạng thái
                self._current_state["is_on"] = False
                self._current_state["start_time"] = None
                self._current_state["scheduled_stop_time"] = None
                self._current_state["last_off_time"] = now
                
                # Lưu trạng thái
                self._save_state()
                
                return {
                    "success": True,
                    "message": "Water pump turned OFF",
                    "run_duration": run_duration,
                    "water_used": water_used,
                    "stop_time": now.isoformat()
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to turn OFF water pump through Adafruit IO"
                }
                
        except Exception as e:
            logger.error(f"Error turning OFF water pump: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Lấy trạng thái hiện tại của máy bơm nước.
        
        Returns:
            Dict chứa trạng thái hiện tại
        """
        # Đồng bộ trạng thái với Adafruit
        self._sync_state_with_adafruit()
        
        status = self._current_state.copy()
        
        # Tính toán thông tin bổ sung
        if status["is_on"] and status["start_time"]:
            # Tính thời gian đã chạy
            current_runtime = (datetime.now() - status["start_time"]).total_seconds()
            status["current_runtime_seconds"] = current_runtime
            status["current_water_used"] = current_runtime * self.water_rate
            
            # Tính thời gian còn lại
            if status["scheduled_stop_time"]:
                remaining = (status["scheduled_stop_time"] - datetime.now()).total_seconds()
                status["remaining_seconds"] = max(0, remaining)
            else:
                status["remaining_seconds"] = None
        else:
            status["current_runtime_seconds"] = 0
            status["current_water_used"] = 0
            status["remaining_seconds"] = None
            
        # Chuyển đổi datetime thành string cho JSON
        for key in ['start_time', 'scheduled_stop_time', 'last_on_time', 'last_off_time']:
            if key in status and status[key]:
                status[key] = status[key].isoformat()
                
        # Thêm thông tin từ Adafruit nếu có thể
        try:
            adafruit_state = self.adafruit_client.get_actuator_state(self.feed_key)
            status["adafruit_state"] = adafruit_state
            status["state_synced"] = (adafruit_state == status["is_on"])
        except Exception:
            status["adafruit_state"] = None
            status["state_synced"] = False
            
        return status
    
    def check_scheduled_actions(self) -> Dict[str, Any]:
        """
        Kiểm tra và thực hiện các hành động theo lịch.
        
        Returns:
            Dict chứa kết quả kiểm tra
        """
        # Đồng bộ trạng thái trước khi kiểm tra
        self._sync_state_with_adafruit()
        
        result = {
            "actions_taken": [],
            "state_before": self._current_state["is_on"]
        }
        
        # Kiểm tra nếu cần tắt máy bơm
        if (
            self._current_state["is_on"] and 
            self._current_state["scheduled_stop_time"] and 
            datetime.now() >= self._current_state["scheduled_stop_time"]
        ):
            # Đến thời điểm tắt máy bơm
            stop_result = self.turn_off(source="schedule", details={"reason": "scheduled_stop"})
            
            result["actions_taken"].append({
                "action": "stop_pump",
                "success": stop_result["success"],
                "time": datetime.now().isoformat(),
                "details": stop_result
            })
            
        # Cập nhật kết quả
        result["state_after"] = self._current_state["is_on"]
        
        return result
    
    def get_irrigation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử tưới gần đây.
        
        Args:
            limit: Số lượng bản ghi tối đa
            
        Returns:
            List chứa lịch sử tưới
        """
        try:
            # Thử lấy từ Redis trước (nhanh hơn)
            history_key = f"{self.redis_key_prefix}history"
            events = self.redis_client.redis.lrange(history_key, 0, limit - 1)
            
            if events:
                # Chuyển đổi từ JSON
                return [json.loads(event) for event in events]
            
            # Nếu không có trong Redis, lấy từ Firebase
            return self.firebase_client.get_irrigation_history(limit)
            
        except Exception as e:
            logger.error(f"Error getting irrigation history: {str(e)}")
            return []
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Tính toán thống kê về việc sử dụng máy bơm.
        
        Returns:
            Dict chứa thống kê
        """
        stats = {
            "total_runtime_seconds": self._current_state["total_runtime_seconds"],
            "total_runtime_hours": self._current_state["total_runtime_seconds"] / 3600,
            "total_water_used_liters": self._current_state["total_water_used"],
            "current_status": "ON" if self._current_state["is_on"] else "OFF"
        }
        
        # Lấy lịch sử tưới
        history = self.get_irrigation_history(limit=50)
        
        if history:
            # Tính thống kê cho 24 giờ qua
            now = datetime.now()
            day_ago = now - timedelta(days=1)
            
            events_24h = [
                event for event in history
                if datetime.fromisoformat(event["timestamp"]) >= day_ago
            ]
            
            stats["events_last_24h"] = len(events_24h)
            stats["runtime_last_24h"] = sum(event["duration_seconds"] for event in events_24h)
            stats["water_used_last_24h"] = sum(event["water_amount_liters"] for event in events_24h)
            
            # Tính trung bình
            if history:
                stats["avg_duration_per_event"] = sum(event["duration_seconds"] for event in history) / len(history)
                stats["avg_water_per_event"] = sum(event["water_amount_liters"] for event in history) / len(history)
            
        return stats