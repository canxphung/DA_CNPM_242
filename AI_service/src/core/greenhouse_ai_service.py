# src/core/greenhouse_ai_service.py
import os
import sys
import logging
import json
import uuid
from datetime import datetime, timedelta
import threading
import time
import asyncio
import aiohttp

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.config import DEFAULT_IRRIGATION_DURATION
from src.core.decision_engine import DecisionEngine
from src.core.model_registry import ModelRegistry
from src.core.cache_manager import APICacheManager
from src.core.resource_optimizer import ResourceOptimizer
from src.database import get_db_session
from src.database.sensor_data import SensorData
from src.database.irrigation_events import IrrigationEvent
from src.external_api.openai_client import OpenAIClient
from src.external_api.core_operations_integration import CoreOperationsIntegration

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('greenhouse_ai_service')

class GreenhouseAIService:
    """
    Main service class that integrates all components of the Greenhouse AI system.
    """
    
    def __init__(self, use_api=True, config=None):
        """
        Initialize the Greenhouse AI Service.
        
        Args:
            use_api: Whether to use external API
            config: Configuration object
        """
        logger.info("Initializing Greenhouse AI Service")
        self.config = config
        
        # Initialize components
        self.decision_engine = DecisionEngine()
        self.model_registry = ModelRegistry()
        self.cache_manager = APICacheManager()
        
        # Initialize the OpenAI client if using API
        self.openai_client = OpenAIClient() if use_api else None
        
        # Initialize new components
        self.resource_optimizer = ResourceOptimizer(self.config, self.model_registry)
        self.core_ops_integration = CoreOperationsIntegration(self.config)
        
        # Initialize the decision engine with components
        self.decision_engine.initialize_components(
            use_local_models=True,
            use_api=use_api
        )
        
        # Service state
        self.is_running = False
        self.recommendation_store = {}  # In-memory store for recommendations
        
        # Statistics
        self.stats = {
            'recommendations_created': 0,
            'recommendations_sent': 0,
            'api_calls': 0,
            'last_api_call': None,
            'messages_processed': 0,
            'service_start_time': datetime.now()
        }
        
        logger.info("Greenhouse AI Service initialized successfully")
    
    def start(self):
        """
        Start the service and any background tasks.
        """
        if self.is_running:
            logger.warning("Service is already running")
            return
        
        logger.info("Starting Greenhouse AI Service")
        self.is_running = True
        
        # Start background tasks
        self._start_background_tasks()
        
        logger.info("Greenhouse AI Service started successfully")
    
    def stop(self):
        """
        Stop the service and any background tasks.
        """
        if not self.is_running:
            logger.warning("Service is not running")
            return
        
        logger.info("Stopping Greenhouse AI Service")
        self.is_running = False
        
        # Close any active connections
        if hasattr(self.core_ops_integration, 'close') and callable(self.core_ops_integration.close):
            asyncio.run(self.core_ops_integration.close())
        
        logger.info("Greenhouse AI Service stopped successfully")
    
    async def process_sensor_data(self, sensor_data):
        """
        Process new sensor data and generate recommendations if needed.
        
        Args:
            sensor_data: Dictionary with sensor readings
            
        Returns:
            Dictionary with decision and actions taken
        """
        logger.info(f"Processing sensor data: {sensor_data}")
        
        # Save sensor data to database
        session = get_db_session()
        try:
            SensorData.create(
                session=session,
                soil_moisture=sensor_data.get('soil_moisture'),
                temperature=sensor_data.get('temperature'),
                humidity=sensor_data.get('humidity'),
                light_level=sensor_data.get('light_level')
            )
        finally:
            session.close()
        
        # Get irrigation decision using decision engine (but don't control pump directly)
        decision = self.decision_engine.get_irrigation_decision(sensor_data)
        
        # Create auto recommendation if needed
        actions_taken = []
        
        if decision['should_irrigate'] and decision['confidence'] >= 0.7:
            # Create a recommendation
            recommendation = await self.create_irrigation_recommendation(
                plant_types=["default"],  # Default plant type when no specifics are given
                zones=None,
                priority="normal",
                auto_generated=True
            )
            
            actions_taken.append(f"Created automatic irrigation recommendation (ID: {recommendation['id']})")
        
        result = {
            'decision': decision,
            'actions_taken': actions_taken,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Sensor data processing result: {result}")
        return result
    
    async def process_user_message(self, message_text, user_id=None):
        """
        Process a user message and take appropriate actions.
        
        Args:
            message_text: Text message from user
            user_id: Optional user identifier
            
        Returns:
            Dictionary with response and actions taken
        """
        logger.info(f"Processing user message: '{message_text}'")
        self.stats['messages_processed'] += 1
        
        # Get current sensor data for context
        sensor_data = self._get_current_sensor_data()
        
        # Process message with decision engine
        message_result = self.decision_engine.process_user_message(message_text)
        
        # Generate response if needed
        if message_result['response'] is None and self.openai_client:
            message_result['response'] = self.openai_client.generate_response(
                message_result['intent'],
                message_result['entities'],
                sensor_data
            )
            self.stats['api_calls'] += 1
            self.stats['last_api_call'] = datetime.now()
        
        # Take action based on the intent
        actions_taken = []
        response_text = message_result['response']
        
        # *** Thay thế điều khiển bơm trực tiếp bằng tạo khuyến nghị ***
        if message_result['action']['type'] == 'activate_pump':
            duration = message_result['action']['parameters'].get(
                'duration_minutes', DEFAULT_IRRIGATION_DURATION
            )
            
            # Tạo khuyến nghị tưới
            asyncio.create_task(self.create_irrigation_recommendation(
                plant_types=["default"],
                zones=None,
                priority="high",  # Mức ưu tiên cao vì là yêu cầu trực tiếp từ người dùng
                auto_send=True  # Tự động gửi đến Core Operations
            ))
            
            actions_taken.append(f"Created high priority irrigation recommendation for {duration} minutes")
            response_text = f"Tôi đã tạo khuyến nghị tưới trong {duration} phút và gửi đến hệ thống điều khiển. Hệ thống sẽ bắt đầu tưới ngay lập tức nếu điều kiện cho phép."
            
        elif message_result['action']['type'] == 'get_sensor_data':
            sensor_type = message_result['action']['parameters'].get('sensor_type')
            value = sensor_data.get(sensor_type, 'unknown')
            
            # Enhance response with actual sensor data
            if sensor_type == 'soil_moisture':
                response_text = f"Độ ẩm đất hiện tại là {value}%."
            elif sensor_type == 'temperature':
                response_text = f"Nhiệt độ hiện tại là {value}°C."
            elif sensor_type == 'humidity':
                response_text = f"Độ ẩm không khí hiện tại là {value}%."
            elif sensor_type == 'light_level':
                response_text = f"Cường độ ánh sáng hiện tại là {value} lux."
            
            actions_taken.append(f"Retrieved {sensor_type} data")
        
        elif message_result['action']['type'] == 'get_system_status':
            # Generate system status response
            status = await self._get_system_status()
            
            if self.openai_client:
                # Generate a natural language summary with the API
                response_text = self.openai_client.generate_response(
                    'get_status',
                    {},
                    sensor_data,
                    json.dumps(status, ensure_ascii=False)
                )
                self.stats['api_calls'] += 1
                self.stats['last_api_call'] = datetime.now()
            else:
                # Simple status response
                pump_status = status.get('pump', {}).get('is_active', False)
                pump_status_text = "đang hoạt động" if pump_status else "không hoạt động"
                response_text = (
                    f"Tình trạng hệ thống: Máy bơm {pump_status_text}. "
                    f"Độ ẩm đất: {status.get('sensors', {}).get('soil_moisture')}%. "
                    f"Nhiệt độ: {status.get('sensors', {}).get('temperature')}°C. "
                    f"Độ ẩm không khí: {status.get('sensors', {}).get('humidity')}%. "
                    f"Ánh sáng: {status.get('sensors', {}).get('light_level')} lux."
                )
            
            actions_taken.append("Retrieved system status")
        
        # Return the result with actions taken
        result = {
            'response': response_text,
            'intent': message_result['intent'],
            'actions_taken': actions_taken,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"User message processing result: {result}")
        return result
    
    async def create_irrigation_recommendation(self, plant_types, zones=None, priority="normal", auto_generated=False, auto_send=False):
        """
        Tạo khuyến nghị tưới thông minh dựa trên tình trạng hiện tại.
        
        Args:
            plant_types: Danh sách loại cây 
            zones: Danh sách vùng tưới (tùy chọn)
            priority: Mức ưu tiên
            auto_generated: Có phải được tạo tự động không
            auto_send: Có tự động gửi đến Core Operations không
            
        Returns:
            Khuyến nghị tưới tối ưu
        """
        logger.info(f"Creating irrigation recommendation for plants: {plant_types}")
        
        # Tạo ID duy nhất
        recommendation_id = str(uuid.uuid4())
        
        # Lấy dữ liệu cảm biến từ Core Operations
        sensor_data = await self.core_ops_integration.fetch_sensor_data()
        if not sensor_data or len(sensor_data) == 0:
            sensor_data = self._get_current_sensor_data()
        
        # Chuyển đổi định dạng cảm biến nếu cần
        if isinstance(sensor_data, list) and len(sensor_data) > 0:
            sensor_data = sensor_data[0]  # Lấy điểm dữ liệu mới nhất
        
        # Sử dụng ResourceOptimizer để tạo lịch tưới tối ưu
        optimized_schedule = self.resource_optimizer.optimize_schedule(
            sensor_data, plant_types, zones
        )
        
        # Tính toán lượng nước tiết kiệm
        current_usage = self._estimate_current_water_usage(sensor_data)
        savings = self.resource_optimizer.calculate_water_savings(
            current_usage, optimized_schedule
        )
        
        # Tạo khuyến nghị đầy đủ
        recommendation = {
            "id": recommendation_id,
            "timestamp": datetime.now().isoformat(),
            "should_irrigate": optimized_schedule.get("should_irrigate", False),
            "zones": optimized_schedule.get("zones"),
            "duration_minutes": optimized_schedule.get("duration_minutes"),
            "irrigation_time": optimized_schedule.get("irrigation_time"),
            "irrigation_datetime": optimized_schedule.get("irrigation_datetime"),
            "soil_moisture": optimized_schedule.get("soil_moisture"),
            "reason": optimized_schedule.get("reason"),
            "water_savings": savings,
            "status": "created",
            "sent_to_core": False,
            "auto_generated": auto_generated
        }
        
        # Lưu khuyến nghị vào bộ nhớ 
        self.recommendation_store[recommendation_id] = recommendation
        self.stats['recommendations_created'] += 1
        
        # Lưu khuyến nghị vào Firebase nếu có
        await self._save_recommendation_to_storage(recommendation)
        
        # Gửi khuyến nghị đến Core Operations nếu được yêu cầu
        if auto_send:
            send_result = await self.send_recommendation_to_core(recommendation_id, priority)
            recommendation["sent_to_core"] = send_result.get("success", False)
            recommendation["status"] = "sent" if send_result.get("success", False) else "created"
        
        return recommendation
    
    async def send_recommendation_to_core(self, recommendation_id, priority="normal"):
        """
        Gửi khuyến nghị đã có đến Core Operations Service.
        
        Args:
            recommendation_id: ID của khuyến nghị
            priority: Mức ưu tiên
            
        Returns:
            Kết quả gửi khuyến nghị
        """
        # Tìm khuyến nghị
        recommendation = self.recommendation_store.get(recommendation_id)
        
        if not recommendation:
            # Thử tìm trong Firebase
            recommendation = await self._load_recommendation_from_storage(recommendation_id)
            
        if not recommendation:
            return {
                "success": False,
                "message": f"Recommendation {recommendation_id} not found"
            }
        
        logger.info(f"Sending recommendation {recommendation_id} to Core Operations")
        
        # Gửi khuyến nghị
        result = await self.core_ops_integration.send_recommendation(recommendation, priority)
        
        # Cập nhật trạng thái
        if result.get("success", False):
            recommendation["sent_to_core"] = True
            recommendation["status"] = "sent"
            recommendation["sent_at"] = datetime.now().isoformat()
            self.stats['recommendations_sent'] += 1
            
            # Lưu cập nhật
            self.recommendation_store[recommendation_id] = recommendation
            await self._save_recommendation_to_storage(recommendation)
        
        return result
    
    async def get_recommendation_by_id(self, recommendation_id):
        """
        Lấy khuyến nghị theo ID.
        
        Args:
            recommendation_id: ID của khuyến nghị
            
        Returns:
            Khuyến nghị tương ứng hoặc None
        """
        # Tìm khuyến nghị trong bộ nhớ
        recommendation = self.recommendation_store.get(recommendation_id)
        
        if not recommendation:
            # Thử tìm trong Firebase
            recommendation = await self._load_recommendation_from_storage(recommendation_id)
            
            # Lưu vào bộ nhớ nếu tìm thấy
            if recommendation:
                self.recommendation_store[recommendation_id] = recommendation
                
        return recommendation
    
    async def get_recommendation_history(self, limit=10, days=30):
        """
        Lấy lịch sử khuyến nghị.
        
        Args:
            limit: Số lượng khuyến nghị tối đa
            days: Số ngày lịch sử
            
        Returns:
            Danh sách khuyến nghị
        """
        # Lấy lịch sử từ Firebase
        recommendations = await self._load_recommendations_from_storage(days)
        
        # Sắp xếp theo thời gian giảm dần
        recommendations.sort(
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
        
        # Giới hạn kết quả
        return recommendations[:limit]
    
    async def get_optimized_irrigation_schedule(self, days=14):
        """
        Tạo lịch tưới tối ưu dựa trên dữ liệu lịch sử.
        
        Args:
            days: Số ngày dữ liệu phân tích
            
        Returns:
            Lịch tưới tối ưu
        """
        # Lấy dữ liệu cảm biến lịch sử
        sensor_data = await self.core_ops_integration.fetch_sensor_data(hours=days*24)
        
        # Lấy lịch sử tưới
        irrigation_history = await self.core_ops_integration.get_irrigation_history(days=days)
        
        # Phân tích thời điểm tưới tối ưu
        best_hours = self._analyze_optimal_irrigation_times(sensor_data, irrigation_history)
        
        # Tạo lịch tưới tối ưu hàng tuần
        schedule = []
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            day_schedule = {
                "day": day,
                "schedule": []
            }
            
            # Thêm các thời điểm tưới tối ưu cho mỗi ngày
            for hour, effectiveness in best_hours:
                day_schedule["schedule"].append({
                    "time": f"{hour:02d}:00",
                    "duration_minutes": 10 if effectiveness > 0.7 else 5,
                    "effectiveness": effectiveness
                })
            
            schedule.append(day_schedule)
        
        return {
            "schedule": schedule,
            "analysis_period_days": days,
            "recommendation": (
                "Lịch tưới này dựa trên phân tích hiệu quả tưới trong quá khứ. "
                "Các thời điểm được chọn là những lúc tưới đã mang lại hiệu quả cao nhất "
                "trong việc cải thiện độ ẩm đất và sức khỏe cây trồng."
            )
        }
    
    def get_service_stats(self):
        """
        Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        uptime_seconds = (datetime.now() - self.stats['service_start_time']).total_seconds()
        
        return {
            'is_running': self.is_running,
            'uptime_seconds': uptime_seconds,
            'recommendations_created': self.stats['recommendations_created'],
            'recommendations_sent': self.stats['recommendations_sent'],
            'api_calls': self.stats['api_calls'],
            'messages_processed': self.stats['messages_processed'],
            'last_api_call': self.stats['last_api_call'].isoformat() if self.stats['last_api_call'] else None,
            'service_start_time': self.stats['service_start_time'].isoformat(),
            'cache_stats': self.cache_manager.get_stats()
        }
    
    def retrain_model(self, model_type):
        """
        Retrain a model with the latest data.
        
        Args:
            model_type: Type of model to retrain
            
        Returns:
            Dictionary with training results
        """
        logger.info(f"Retraining {model_type} model")
        
        try:
            model = self.model_registry.train_new_model(model_type)
            
            # Update the model in the decision engine
            if model_type == 'irrigation':
                self.decision_engine.irrigation_model = model
            elif model_type == 'chatbot':
                self.decision_engine.chatbot_model = model
            
            return {
                'success': True,
                'model_type': model_type,
                'version': model.version,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error retraining {model_type} model: {str(e)}")
            return {
                'success': False,
                'model_type': model_type,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_current_sensor_data(self):
        """
        Get the most recent sensor data.
        
        Returns:
            Dictionary with sensor readings
        """
        session = get_db_session()
        try:
            latest = SensorData.get_latest(session)
            
            if latest:
                return {
                    'soil_moisture': latest.soil_moisture,
                    'temperature': latest.temperature,
                    'humidity': latest.humidity,
                    'light_level': latest.light_level,
                    'timestamp': latest.timestamp.isoformat()
                }
            else:
                logger.warning("No sensor data available")
                return {
                    'soil_moisture': None,
                    'temperature': None,
                    'humidity': None,
                    'light_level': None,
                    'timestamp': None
                }
        finally:
            session.close()
    
    async def _get_system_status(self):
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary with system status
        """
        # Get current sensor data
        sensor_data = self._get_current_sensor_data()
        
        # Get status from Core Operations
        core_status = {}
        try:
            # Attempt to get status from Core Operations API
            async with aiohttp.ClientSession() as session:
                core_ops_url = f"{self.config.CORE_OPS_API_URL}/health"
                headers = {"Authorization": f"Bearer {self.config.CORE_OPS_API_KEY}"} if self.config.CORE_OPS_API_KEY else {}
                
                async with session.get(core_ops_url, headers=headers) as response:
                    if response.status == 200:
                        core_status = await response.json()
        except Exception as e:
            logger.error(f"Error getting Core Operations status: {str(e)}")
        
        # Get recent irrigation events
        try:
            irrigation_events = await self.core_ops_integration.get_irrigation_history(days=1)
        except Exception as e:
            logger.error(f"Error getting irrigation history: {str(e)}")
            irrigation_events = []
        
        # Compile the status
        return {
            'sensors': sensor_data,
            'core_operations': core_status,
            'recent_irrigation_events': irrigation_events[:5] if irrigation_events else [],
            'ai_service': {
                'is_running': self.is_running,
                'uptime_seconds': (datetime.now() - self.stats['service_start_time']).total_seconds(),
                'api_calls': self.stats['api_calls'],
                'recommendations_created': self.stats['recommendations_created']
            }
        }
    
    def _estimate_current_water_usage(self, sensor_data):
        """
        Ước tính lượng nước sử dụng hiện tại.
        
        Args:
            sensor_data: Dữ liệu cảm biến hiện tại
            
        Returns:
            Dict chứa lịch tưới ước tính hiện tại
        """
        # Lấy độ ẩm đất
        soil_moisture = sensor_data.get('soil_moisture', 50)
        
        # Ước tính thời gian tưới dựa trên độ ẩm đất
        duration = 0
        if soil_moisture < 30:
            duration = 15  # Rất khô, tưới nhiều
        elif soil_moisture < 40:
            duration = 10  # Khô, tưới trung bình
        elif soil_moisture < 50:
            duration = 5   # Hơi khô, tưới nhẹ
        
        # Tạo lịch tưới ước tính
        if duration > 0:
            return {
                "should_irrigate": True,
                "duration_minutes": duration,
                "irrigation_time": "12:00",  # Giờ trưa (không tối ưu)
                "zones": [
                    {
                        "should_irrigate": True,
                        "duration_minutes": duration,
                        "irrigation_time": "12:00"
                    }
                ]
            }
        else:
            return {
                "should_irrigate": False,
                "duration_minutes": 0,
                "zones": [
                    {
                        "should_irrigate": False,
                        "duration_minutes": 0
                    }
                ]
            }
    
    def _analyze_optimal_irrigation_times(self, sensor_data, irrigation_history):
        """
        Phân tích thời điểm tưới tối ưu dựa trên dữ liệu lịch sử.
        
        Args:
            sensor_data: Dữ liệu cảm biến lịch sử
            irrigation_history: Lịch sử tưới
            
        Returns:
            Danh sách các giờ tối ưu với độ hiệu quả
        """
        # Sắp xếp các giờ trong ngày theo độ hiệu quả tưới
        effectiveness = {
            6: 0.9,   # 6h sáng
            18: 0.85, # 6h chiều
            7: 0.8,   # 7h sáng
            19: 0.75, # 7h tối
            5: 0.7,   # 5h sáng
            20: 0.65, # 8h tối
            8: 0.6,   # 8h sáng
            17: 0.55, # 5h chiều
        }
        
        # Phân tích thời điểm tưới trong lịch sử
        hour_counts = {}
        
        for event in irrigation_history:
            if 'start_time' in event:
                try:
                    if isinstance(event.get('start_time'), str):
                        event_time = datetime.fromisoformat(event['start_time'].replace('Z', '+00:00'))
                        hour = event_time.hour
                        
                        if hour not in hour_counts:
                            hour_counts[hour] = 0
                        hour_counts[hour] += 1
                    else:
                        # Xử lý trường hợp start_time không phải là chuỗi hoặc không tồn tại
                        continue
                except (ValueError, TypeError, KeyError):
                    continue
        
        # Kết hợp phân tích lịch sử với kiến thức về hiệu quả
        final_scores = {}
        
        for hour in range(24):
            # Bắt đầu với giá trị hiệu quả đã biết hoặc giá trị thấp
            score = effectiveness.get(hour, 0.3)
            
            # Tăng điểm nếu đây là giờ được sử dụng thường xuyên trong lịch sử
            if hour in hour_counts:
                frequency_boost = min(0.2, hour_counts[hour] / 20)  # Tối đa +0.2 điểm
                score += frequency_boost
            
            # Giảm điểm cho giờ nóng trong ngày
            if 10 <= hour <= 15:
                score -= 0.3
                
            final_scores[hour] = max(0, min(1, score))  # Giới hạn trong khoảng [0, 1]
        
        # Sắp xếp giờ theo điểm số giảm dần và trả về top 3
        best_hours = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return best_hours
    
    async def _save_recommendation_to_storage(self, recommendation):
        """
        Lưu khuyến nghị vào bộ lưu trữ bền vững.
        
        Args:
            recommendation: Khuyến nghị cần lưu
        """
        # Sửa trong _save_recommendation_to_storage
        if not hasattr(self, 'core_ops_integration') or not self.core_ops_integration or not hasattr(self.core_ops_integration, 'db_ref') or not self.core_ops_integration.db_ref:
            logger.warning("Firebase connection not available")
            return
            
        try:
            # Lưu khuyến nghị vào Firebase
            recommendations_ref = self.core_ops_integration.db_ref.child("ai_recommendations")
            recommendations_ref.child(recommendation["id"]).set(recommendation)
            logger.debug(f"Saved recommendation {recommendation['id']} to Firebase")
        except Exception as e:
            logger.error(f"Error saving recommendation to Firebase: {str(e)}")
    
    async def _load_recommendation_from_storage(self, recommendation_id):
        """
        Tải khuyến nghị từ bộ lưu trữ bền vững.
        
        Args:
            recommendation_id: ID khuyến nghị
            
        Returns:
            Khuyến nghị tìm thấy hoặc None
        """
        if not hasattr(self, 'core_ops_integration') or not self.core_ops_integration or not hasattr(self.core_ops_integration, 'db_ref') or not self.core_ops_integration.db_ref:
            logger.warning("Firebase connection not available")
            return None
            
        try:
            # Tải khuyến nghị từ Firebase
            recommendations_ref = self.core_ops_integration.db_ref.child("ai_recommendations")
            recommendation = recommendations_ref.child(recommendation_id).get()
            
            if recommendation:
                logger.debug(f"Loaded recommendation {recommendation_id} from Firebase")
                return recommendation
            else:
                logger.warning(f"Recommendation {recommendation_id} not found in Firebase")
                return None
        except Exception as e:
            logger.error(f"Error loading recommendation from Firebase: {str(e)}")
            return None
    
    async def _load_recommendations_from_storage(self, days=30):
        """
        Tải danh sách khuyến nghị từ bộ lưu trữ bền vững.
        
        Args:
            days: Số ngày lịch sử
            
        Returns:
            Danh sách khuyến nghị
        """
        if not hasattr(self, 'core_ops_integration') or not self.core_ops_integration or not hasattr(self.core_ops_integration, 'db_ref') or not self.core_ops_integration.db_ref:
            logger.warning("Firebase connection not available")
            # Trả về từ bộ nhớ
            return list(self.recommendation_store.values())
            
        try:
            # Tính thời gian bắt đầu
            start_time = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Tải khuyến nghị từ Firebase
            recommendations_ref = self.core_ops_integration.db_ref.child("ai_recommendations")
            # Lấy tất cả khuyến nghị
            all_recommendations = recommendations_ref.get()
            
            if not all_recommendations:
                logger.warning("No recommendations found in Firebase")
                return list(self.recommendation_store.values())
            
            # Lọc theo thời gian và chuyển thành list
            recommendations = []
            for rec_id, rec in all_recommendations.items():
                if rec.get("timestamp", "") >= start_time:
                    if isinstance(rec, dict):
                        if "id" not in rec:
                            rec["id"] = rec_id
                        recommendations.append(rec)
            
            logger.info(f"Loaded {len(recommendations)} recommendations from Firebase")
            
            # Cập nhật cache
            for rec in recommendations:
                self.recommendation_store[rec["id"]] = rec
                
            return recommendations
        except Exception as e:
            logger.error(f"Error loading recommendations from Firebase: {str(e)}")
            # Trả về từ bộ nhớ
            return list(self.recommendation_store.values())
    
    def _start_background_tasks(self):
        """Start background tasks."""
        def maintenance_task():
            while self.is_running:
                try:
                    # Perform cache maintenance once a day
                    self.cache_manager.perform_maintenance()
                    
                    # Sleep for 1 hour
                    for _ in range(60 * 60):
                        if not self.is_running:
                            break
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in maintenance task: {str(e)}")
                    time.sleep(3600)  # Sleep for an hour if there's an error
        
        # Start the maintenance thread
        maintenance_thread = threading.Thread(target=maintenance_task)
        maintenance_thread.daemon = True
        maintenance_thread.start()