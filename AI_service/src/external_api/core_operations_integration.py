"""
Tích hợp với Core Operations Service.
"""
import logging
import json
import aiohttp
import asyncio
import redis
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class CoreOperationsIntegration:
    """
    Lớp tích hợp với Core Operations Service, hỗ trợ giao tiếp hai chiều 
    để phối hợp hệ thống AI với hệ thống điều khiển phần cứng.
    """
    
    def __init__(self, config):
        """
        Khởi tạo tích hợp với Core Operations Service.
        
        Args:
            config: Cấu hình hệ thống chứa thông tin kết nối
        """
        # Khởi tạo HTTP client
        self.base_url = config.CORE_OPS_API_URL
        self.api_key = config.CORE_OPS_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        self.session = None  # Sẽ khởi tạo khi cần
        
        # Khởi tạo Redis client để truy cập Redis của Core Operations
        try:
            self.redis = redis.Redis(
                host=config.CORE_OPS_REDIS_HOST,
                port=config.CORE_OPS_REDIS_PORT,
                db=config.CORE_OPS_REDIS_DB,
                password=config.CORE_OPS_REDIS_PASSWORD,
                decode_responses=True
            )
            self.redis_key_prefix = "ai:"  # Tiền tố cho khóa Redis của AI Service
            logger.info(f"Connected to Core Operations Redis at {config.CORE_OPS_REDIS_HOST}:{config.CORE_OPS_REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Core Operations Redis: {str(e)}")
            self.redis = None
        
        # Khởi tạo Firebase client để truy cập Firebase của Core Operations
        try:
            # Chỉ khởi tạo nếu chưa có ứng dụng Firebase nào
            if not firebase_admin._apps:
                cred = credentials.Certificate(config.CORE_OPS_FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': config.CORE_OPS_FIREBASE_DATABASE_URL
                })
            self.db_ref = db.reference()
            logger.info(f"Connected to Core Operations Firebase at {config.CORE_OPS_FIREBASE_DATABASE_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Core Operations Firebase: {str(e)}")
            self.db_ref = None
    
    async def initialize(self):
        """Khởi tạo phiên HTTP."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Đóng phiên HTTP."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def send_recommendation(self, recommendation_data, priority="normal") -> Dict[str, Any]:
        """
        Gửi khuyến nghị tưới từ AI Service đến Core Operations Service.
        
        Args:
            recommendation_data: Dữ liệu khuyến nghị tưới
            priority: Mức ưu tiên ("normal", "high", "low")
            
        Returns:
            Kết quả từ Core Operations Service
        """
        await self.initialize()
        
        endpoint = f"{self.base_url}/api/control/recommendation"
        
        payload = {
            "source": "ai_service",
            "recommendation": recommendation_data,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            async with self.session.post(endpoint, json=payload, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error sending recommendation: {response.status} - {await response.text()}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status}",
                        "message": await response.text()
                    }
        except Exception as e:
            logger.error(f"Failed to send recommendation: {str(e)}")
            
            # Fallback: Lưu vào Redis nếu API call thất bại
            if self.redis:
                try:
                    self.store_recommendation_in_redis(recommendation_data, priority)
                    return {
                        "success": True,
                        "message": "Recommendation stored in Redis (API fallback)",
                        "via": "redis_fallback"
                    }
                except Exception as redis_error:
                    logger.error(f"Redis fallback also failed: {str(redis_error)}")
            
            return {"success": False, "error": str(e)}
    
    async def fetch_sensor_data(self, hours_back=24, interval_minutes=None) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu cảm biến từ Core Operations Service.
        
        Args:
            hours_back: Số giờ dữ liệu lịch sử cần lấy
            interval_minutes: Khoảng thời gian giữa các điểm dữ liệu (nếu có)
            
        Returns:
            Danh sách dữ liệu cảm biến
        """
        await self.initialize()
        
        endpoint = f"{self.base_url}/api/sensors/history?hours={hours_back}"
        if interval_minutes:
            endpoint += f"&interval={interval_minutes}"
        
        try:
            async with self.session.get(endpoint, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error fetching sensor data: {response.status} - {await response.text()}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch sensor data: {str(e)}")
            
            # Fallback: Thử lấy từ Firebase nếu có
            if self.db_ref:
                try:
                    return self.fetch_sensor_data_from_firebase(hours_back)
                except Exception as firebase_error:
                    logger.error(f"Firebase fallback also failed: {str(firebase_error)}")
                    
            return []
    
    async def get_irrigation_history(self, days_back=30) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử tưới từ Core Operations Service.
        
        Args:
            days_back: Số ngày dữ liệu lịch sử cần lấy
            
        Returns:
            Danh sách các sự kiện tưới
        """
        await self.initialize()
        
        endpoint = f"{self.base_url}/api/control/history?days={days_back}"
        
        try:
            async with self.session.get(endpoint, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error fetching irrigation history: {response.status} - {await response.text()}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch irrigation history: {str(e)}")
            
            # Fallback: Thử lấy từ Firebase nếu có
            if self.db_ref:
                try:
                    return self.fetch_irrigation_history_from_firebase(days_back)
                except Exception as firebase_error:
                    logger.error(f"Firebase fallback also failed: {str(firebase_error)}")
                    
            return []
    
    def store_recommendation_in_redis(self, recommendation_data, priority="normal") -> bool:
        """
        Lưu khuyến nghị vào Redis của Core Operations.
        
        Args:
            recommendation_data: Dữ liệu khuyến nghị
            priority: Mức ưu tiên
            
        Returns:
            True nếu thành công
        """
        if not self.redis:
            logger.error("Redis connection not available")
            return False
        
        try:
            # Tạo key với timestamp để đảm bảo duy nhất
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d%H%M%S")
            key = f"{self.redis_key_prefix}recommendation:{timestamp}"
            
            # Thêm thông tin timestamp và priority
            data = {
                "recommendation": recommendation_data,
                "priority": priority,
                "timestamp": now.isoformat(),
                "from": "ai_service"
            }
            
            # Lưu vào Redis với thời gian hết hạn 24 giờ
            self.redis.setex(key, 86400, json.dumps(data))
            
            # Đẩy thông báo vào kênh Redis
            self.redis.publish("notifications:recommendations", json.dumps({
                "type": "new_recommendation",
                "key": key,
                "priority": priority,
                "timestamp": now.isoformat()
            }))
            
            logger.info(f"Stored recommendation in Redis with key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing recommendation in Redis: {str(e)}")
            return False
    
    def fetch_sensor_data_from_firebase(self, hours_back=24) -> List[Dict[str, Any]]:
        """
        Lấy dữ liệu cảm biến từ Firebase của Core Operations.
        
        Args:
            hours_back: Số giờ dữ liệu lịch sử cần lấy
            
        Returns:
            Danh sách dữ liệu cảm biến
        """
        if not self.db_ref:
            logger.error("Firebase connection not available")
            return []
        
        try:
            # Tạo thời gian bắt đầu
            start_time = datetime.now() - timedelta(hours=hours_back)
            start_time_str = start_time.isoformat()
            
            # Truy vấn Firebase
            sensor_ref = self.db_ref.child("sensor_data")
            # Giới hạn kết quả và sắp xếp theo thời gian giảm dần
            query = sensor_ref.order_by_child("timestamp").start_at(start_time_str).limit_to_last(1000)
            result = query.get()
            
            # Chuyển đổi kết quả thành list
            data = []
            if result:
                for key, value in result.items():
                    value['id'] = key
                    data.append(value)
                
                # Sắp xếp theo thời gian
                data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                
            return data
            
        except Exception as e:
            logger.error(f"Error fetching sensor data from Firebase: {str(e)}")
            return []
    
    def fetch_irrigation_history_from_firebase(self, days_back=30) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử tưới từ Firebase của Core Operations.
        
        Args:
            days_back: Số ngày dữ liệu lịch sử cần lấy
            
        Returns:
            Danh sách các sự kiện tưới
        """
        if not self.db_ref:
            logger.error("Firebase connection not available")
            return []
        
        try:
            # Tạo thời gian bắt đầu
            start_time = datetime.now() - timedelta(days=days_back)
            start_time_str = start_time.isoformat()
            
            # Truy vấn Firebase
            events_ref = self.db_ref.child("irrigation_events")
            # Giới hạn kết quả và sắp xếp theo thời gian
            query = events_ref.order_by_child("timestamp").start_at(start_time_str)
            result = query.get()
            
            # Chuyển đổi kết quả thành list
            events = []
            if result:
                for key, value in result.items():
                    value['id'] = key
                    events.append(value)
                
                # Sắp xếp theo thời gian
                events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                
            return events
            
        except Exception as e:
            logger.error(f"Error fetching irrigation history from Firebase: {str(e)}")
            return []