"""
Hệ thống lập lịch tưới tự động.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading
import time

# Tránh circular import
# from src.infrastructure import ServiceFactory

from src.adapters.cloud.actuators.water_pump import WaterPumpController


logger = logging.getLogger(__name__)

class IrrigationScheduler:
    """
    Hệ thống lập lịch tưới tự động.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(IrrigationScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Khởi tạo IrrigationScheduler."""
        if self._initialized:
            return
            
        logger.info("Initializing IrrigationScheduler")
        
        # Khởi tạo các services (lazy import để tránh circular import)
        from src.infrastructure import get_service_factory
        factory = get_service_factory()
        self.config = factory.get_config_loader()
        self.redis_client = factory.create_redis_client()
        self.firebase_client = factory.create_firebase_client("scheduling")
        
        # Khóa Redis cho lịch tưới
        self.redis_key_prefix = self.config.get('redis.key_prefixes.irrigation_schedule', 'schedule:')
        self.redis_schedules_key = f"{self.redis_key_prefix}schedules"
        
        # Lấy WaterPumpController
        self.pump_controller = WaterPumpController()
        
        # Biến theo dõi trạng thái
        self.schedules = []
        self.background_thread = None
        self.is_running = False
        self.check_interval = 60  # Kiểm tra mỗi 60 giây
        
        # Đọc lịch tưới từ storage
        self.load_schedules()
        
        self._initialized = True
        logger.info(f"IrrigationScheduler initialized with {len(self.schedules)} schedules")
    
    def load_schedules(self) -> None:
        """Đọc lịch tưới từ Redis và Firebase."""
        try:
            # Thử đọc từ Redis trước
            schedules = self.redis_client.get(self.redis_schedules_key)
            
            if schedules:
                logger.info(f"Loaded {len(schedules)} schedules from Redis")
                self.schedules = schedules
                return
                
            # Nếu không có trong Redis, đọc từ Firebase
            schedules_data = self.firebase_client.get("schedules")
            
            if schedules_data:
                if isinstance(schedules_data, dict):
                    # Chuyển đổi từ dict thành list
                    schedules = []
                    for schedule_id, schedule in schedules_data.items():
                        schedule['id'] = schedule_id
                        schedules.append(schedule)
                    
                    self.schedules = schedules
                    
                    # Lưu vào Redis
                    self.redis_client.set(self.redis_schedules_key, self.schedules)
                    
                    logger.info(f"Loaded {len(self.schedules)} schedules from Firebase")
                else:
                    logger.error(f"Invalid schedules data format: {type(schedules_data)}")
                    self.schedules = []
            else:
                logger.info("No schedules found in storage")
                self.schedules = []
                
        except Exception as e:
            logger.error(f"Error loading schedules: {str(e)}")
            self.schedules = []
    
    def save_schedules(self) -> bool:
        """
        Lưu lịch tưới vào Redis và Firebase.
        
        Returns:
            bool: Thành công hay thất bại
        """
        try:
            # Lưu vào Redis
            self.redis_client.set(self.redis_schedules_key, self.schedules)
            
            # Lưu vào Firebase
            schedules_dict = {}
            for schedule in self.schedules:
                schedule_id = schedule.get('id')
                if schedule_id:
                    # Tạo bản sao và loại bỏ trường 'id'
                    schedule_copy = schedule.copy()
                    schedule_copy.pop('id')
                    schedules_dict[schedule_id] = schedule_copy
                    
            self.firebase_client.set("schedules", schedules_dict)
            
            logger.info(f"Saved {len(self.schedules)} schedules to storage")
            return True
            
        except Exception as e:
            logger.error(f"Error saving schedules: {str(e)}")
            return False
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách tất cả lịch tưới.
        
        Returns:
            List các lịch tưới
        """
        # Trả về bản sao của danh sách để tránh sửa đổi trực tiếp
        return self.schedules.copy()
    
    def add_schedule(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thêm lịch tưới mới.
        
        Args:
            schedule: Thông tin lịch tưới
            
        Returns:
            Dict chứa kết quả với 'success', 'message', và 'schedule'
        """
        try:
            # Kiểm tra các trường bắt buộc
            required_fields = ['name', 'days', 'start_time', 'duration']
            
            for field in required_fields:
                if field not in schedule:
                    return {
                        "success": False,
                        "message": f"Missing required field: {field}"
                    }
                    
            # Kiểm tra và chuyển đổi định dạng thời gian
            try:
                # Kiểm tra định dạng thời gian
                datetime.strptime(schedule['start_time'], "%H:%M")
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid time format. Use HH:MM (24-hour format)"
                }
                
            # Kiểm tra các ngày trong tuần
            valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            
            if not isinstance(schedule['days'], list):
                return {
                    "success": False,
                    "message": "Days must be a list"
                }
                
            for day in schedule['days']:
                if day.lower() not in valid_days:
                    return {
                        "success": False,
                        "message": f"Invalid day: {day}. Valid days: {valid_days}"
                    }
                    
            # Kiểm tra thời lượng
            try:
                duration = int(schedule['duration'])
                if duration <= 0:
                    return {
                        "success": False,
                        "message": "Duration must be a positive integer"
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "Duration must be a valid integer"
                }
                
            # Tạo ID mới nếu chưa có
            if 'id' not in schedule:
                schedule['id'] = f"schedule_{int(time.time())}_{len(self.schedules)}"
                
            # Thêm thời gian tạo
            schedule['created_at'] = datetime.now().isoformat()
            
            # Đặt trạng thái mặc định là active
            if 'active' not in schedule:
                schedule['active'] = True
                
            # Thêm vào danh sách
            self.schedules.append(schedule)
            
            # Lưu thay đổi
            self.save_schedules()
            
            return {
                "success": True,
                "message": "Schedule added successfully",
                "schedule": schedule
            }
            
        except Exception as e:
            logger.error(f"Error adding schedule: {str(e)}")
            return {
                "success": False,
                "message": f"Error adding schedule: {str(e)}"
            }
    
    def update_schedule(self, schedule_id: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật lịch tưới.
        
        Args:
            schedule_id: ID của lịch tưới
            updated_data: Dữ liệu cập nhật
            
        Returns:
            Dict chứa kết quả với 'success' và 'message'
        """
        try:
            # Tìm lịch trình cần cập nhật
            schedule_index = None
            
            for i, schedule in enumerate(self.schedules):
                if schedule.get('id') == schedule_id:
                    schedule_index = i
                    break
                    
            if schedule_index is None:
                return {
                    "success": False,
                    "message": f"Schedule with ID {schedule_id} not found"
                }
                
            # Kiểm tra định dạng thời gian nếu có
            if 'start_time' in updated_data:
                try:
                    datetime.strptime(updated_data['start_time'], "%H:%M")
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid time format. Use HH:MM (24-hour format)"
                    }
                    
            # Kiểm tra các ngày trong tuần nếu có
            if 'days' in updated_data:
                valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                
                if not isinstance(updated_data['days'], list):
                    return {
                        "success": False,
                        "message": "Days must be a list"
                    }
                    
                for day in updated_data['days']:
                    if day.lower() not in valid_days:
                        return {
                            "success": False,
                            "message": f"Invalid day: {day}. Valid days: {valid_days}"
                        }
                        
            # Kiểm tra thời lượng nếu có
            if 'duration' in updated_data:
                try:
                    duration = int(updated_data['duration'])
                    if duration <= 0:
                        return {
                            "success": False,
                            "message": "Duration must be a positive integer"
                        }
                except ValueError:
                    return {
                        "success": False,
                        "message": "Duration must be a valid integer"
                    }
                    
            # Cập nhật dữ liệu
            current_schedule = self.schedules[schedule_index]
            current_schedule.update(updated_data)
            
            # Thêm thời gian cập nhật
            current_schedule['updated_at'] = datetime.now().isoformat()
            
            # Lưu thay đổi
            self.save_schedules()
            
            return {
                "success": True,
                "message": "Schedule updated successfully",
                "schedule": current_schedule
            }
            
        except Exception as e:
            logger.error(f"Error updating schedule: {str(e)}")
            return {
                "success": False,
                "message": f"Error updating schedule: {str(e)}"
            }
    
    def delete_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """
        Xóa lịch tưới.
        
        Args:
            schedule_id: ID của lịch tưới
            
        Returns:
            Dict chứa kết quả với 'success' và 'message'
        """
        try:
            # Tìm lịch trình cần xóa
            schedule_index = None
            
            for i, schedule in enumerate(self.schedules):
                if schedule.get('id') == schedule_id:
                    schedule_index = i
                    break
                    
            if schedule_index is None:
                return {
                    "success": False,
                    "message": f"Schedule with ID {schedule_id} not found"
                }
                
            # Xóa lịch trình
            deleted_schedule = self.schedules.pop(schedule_index)
            
            # Lưu thay đổi
            self.save_schedules()
            
            return {
                "success": True,
                "message": "Schedule deleted successfully",
                "deleted_schedule": deleted_schedule
            }
            
        except Exception as e:
            logger.error(f"Error deleting schedule: {str(e)}")
            return {
                "success": False,
                "message": f"Error deleting schedule: {str(e)}"
            }
    
    def check_schedules(self) -> Dict[str, Any]:
        """
        Kiểm tra và thực hiện các lịch tưới nếu đến thời gian.
        
        Returns:
            Dict chứa kết quả kiểm tra
        """
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A").lower()
        
        result = {
            "checked_at": now.isoformat(),
            "matched_schedules": [],
            "actions_taken": []
        }
        
        # Đảm bảo pump controller đã thực hiện các tác vụ theo lịch
        pump_check = self.pump_controller.check_scheduled_actions()
        
        # Kiểm tra nếu máy bơm đang chạy, không kích hoạt lịch tưới mới
        pump_status = self.pump_controller.get_status()
        if pump_status["is_on"]:
            result["pump_already_running"] = True
            return result
            
        # Kiểm tra từng lịch tưới
        for schedule in self.schedules:
            # Bỏ qua các lịch không hoạt động
            if not schedule.get('active', True):
                continue
                
            # Kiểm tra ngày trong tuần
            if current_day not in [day.lower() for day in schedule.get('days', [])]:
                continue
                
            # Kiểm tra thời gian (so sánh giờ:phút)
            if schedule.get('start_time') != current_time:
                continue
                
            # Tìm thấy lịch trình phù hợp
            result["matched_schedules"].append(schedule)
            
            # Bật máy bơm với thời lượng được chỉ định
            duration = int(schedule.get('duration', 300))  # mặc định 5 phút
            
            try:
                pump_result = self.pump_controller.turn_on(
                    duration=duration,
                    source="schedule",
                    details={
                        "schedule_id": schedule.get('id'),
                        "schedule_name": schedule.get('name')
                    }
                )
                
                result["actions_taken"].append({
                    "schedule_id": schedule.get('id'),
                    "schedule_name": schedule.get('name'),
                    "action": "turn_on_pump",
                    "duration": duration,
                    "success": pump_result["success"],
                    "message": pump_result["message"]
                })
                
                # Nếu đã kích hoạt một lịch, dừng kiểm tra
                # (không bật máy bơm nhiều lần)
                if pump_result["success"]:
                    break
                    
            except Exception as e:
                logger.error(f"Error executing schedule {schedule.get('id')}: {str(e)}")
                result["actions_taken"].append({
                    "schedule_id": schedule.get('id'),
                    "schedule_name": schedule.get('name'),
                    "action": "turn_on_pump",
                    "success": False,
                    "error": str(e)
                })
                
        return result
    
    def start_background_checking(self) -> bool:
        """
        Bắt đầu kiểm tra lịch tưới ngầm.
        
        Returns:
            bool: Thành công hay thất bại
        """
        if self.is_running:
            logger.warning("Background schedule checking is already running")
            return False
            
        self.is_running = True
        
        def checking_worker():
            logger.info(f"Starting background schedule checking every {self.check_interval} seconds")
            while self.is_running:
                try:
                    # Kiểm tra lịch trình
                    result = self.check_schedules()
                    
                    # Log thông tin nếu có hành động được thực hiện
                    if result["actions_taken"]:
                        logger.info(f"Schedule check triggered {len(result['actions_taken'])} actions")
                        for action in result["actions_taken"]:
                            logger.info(f"  - {action['schedule_name']}: {action['message']}")
                except Exception as e:
                    logger.error(f"Error in background schedule checking: {str(e)}")
                    
                # Sleep for the specified interval
                for _ in range(self.check_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
        
        self.background_thread = threading.Thread(target=checking_worker)
        self.background_thread.daemon = True
        self.background_thread.start()
        
        return True
    
    def stop_background_checking(self) -> bool:
        """
        Dừng kiểm tra lịch tưới ngầm.
        
        Returns:
            bool: Thành công hay thất bại
        """
        if not self.is_running:
            logger.warning("Background schedule checking is not running")
            return False
            
        self.is_running = False
        
        if self.background_thread:
            self.background_thread.join(timeout=5.0)
            
        logger.info("Background schedule checking stopped")
        return True