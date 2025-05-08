# src/core/decision_engine.py
import os
import sys
import time
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.config import CONFIDENCE_THRESHOLD
from src.models.irrigation_model import IrrigationModel
from src.models.chatbot_model import ChatbotModel
from src.external_api.openai_client import OpenAIClient

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('decision_engine')

class DecisionEngine:
    """
    Decision engine that coordinates between local models and external APIs.
    Makes intelligent decisions on which systems to use based on confidence levels,
    availability, and optimization strategies.
    """
    
    def __init__(self, confidence_threshold=None):
        """
        Initialize the decision engine.
        
        Args:
            confidence_threshold: Threshold for model confidence (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold or CONFIDENCE_THRESHOLD
        
        # Initialize models and API clients
        self.irrigation_model = None
        self.chatbot_model = None
        self.openai_client = None
        
        # Track API usage
        self.api_call_count = 0
        self.api_last_called = None
        
        logger.info(f"Decision Engine initialized with confidence threshold: {self.confidence_threshold}")
    
    def initialize_components(self, use_local_models=True, use_api=True, resource_optimizer=None):
        """
        Initialize required components (models and API clients).
        
        Args:
            use_local_models: Whether to initialize local models
            use_api: Whether to initialize API clients
            resource_optimizer: Optional ResourceOptimizer instance
        """
        self.resource_optimizer = resource_optimizer
        try:
            if use_local_models:
                logger.info("Initializing local models...")
                self.irrigation_model = IrrigationModel()
                self.irrigation_model.load()
                
                self.chatbot_model = ChatbotModel()
                self.chatbot_model.load()
                logger.info("Local models initialized successfully")
            
            if use_api:
                logger.info("Initializing API client...")
                self.openai_client = OpenAIClient(use_cache=True)
                logger.info("API client initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            # If local models fail to load, try to use API as fallback
            if use_local_models and use_api and self.openai_client is None:
                logger.info("Attempting to initialize API client as fallback...")
                self.openai_client = OpenAIClient(use_cache=True)
    
    def get_irrigation_decision(self, sensor_data):
        """
        Determine whether irrigation is needed based on sensor data.
        Uses local model first, then API if confidence is low.
        
        Args:
            sensor_data: Dictionary with current sensor readings
            
        Returns:
            Dictionary with irrigation decision and metadata
        """
        start_time = time.time()
        local_prediction = None
        api_prediction = None
        source = "hybrid"
        
        # Step 1: Try local model first
        if self.irrigation_model:
            try:
                local_prediction = self.irrigation_model.predict(sensor_data)
                logger.info(f"Local irrigation model prediction: {local_prediction}")
                
                # If confidence is high enough, use local model result
                if local_prediction['confidence'] >= self.confidence_threshold:
                    logger.info(f"Using local model prediction (confidence: {local_prediction['confidence']:.2f})")
                    source = "local_model"
                    final_decision = local_prediction
                else:
                    logger.info(f"Local model confidence too low: {local_prediction['confidence']:.2f}")
            except Exception as e:
                logger.error(f"Error in local irrigation model: {str(e)}")
                local_prediction = None
        
        # Step 2: If local prediction is None or confidence is low, try API
        if (local_prediction is None or 
            local_prediction['confidence'] < self.confidence_threshold) and self.openai_client:
            try:
                logger.info("Requesting irrigation recommendation from OpenAI API")
                api_prediction = self.openai_client.recommend_irrigation(sensor_data)
                self.api_call_count += 1
                self.api_last_called = datetime.now()
                
                logger.info(f"API irrigation recommendation: {api_prediction}")
                
                if local_prediction is None:
                    source = "openai"
                    final_decision = {
                        'should_irrigate': api_prediction.get('should_irrigate', False),
                        'confidence': 0.9,  # Assume fairly high confidence for API
                        'duration_minutes': api_prediction.get('duration_minutes', 10),
                        'reason': api_prediction.get('reason', 'Based on API analysis')
                    }
                else:
                    # Combine both predictions
                    source = "hybrid"
                    # If both agree, high confidence
                    if local_prediction['should_irrigate'] == api_prediction.get('should_irrigate', False):
                        confidence = max(local_prediction['confidence'], 0.9)
                    else:
                        # If they disagree, go with API but with reduced confidence
                        confidence = 0.8
                    
                    final_decision = {
                        'should_irrigate': api_prediction.get('should_irrigate', False),
                        'confidence': confidence,
                        'duration_minutes': api_prediction.get('duration_minutes', 10),
                        'reason': api_prediction.get('reason', 'Based on combined analysis')
                    }
                
            except Exception as e:
                logger.error(f"Error in API irrigation recommendation: {str(e)}")
                
                # Fallback to local prediction if API fails
                if local_prediction is not None:
                    source = "local_model"
                    final_decision = local_prediction
                else:
                    # If both fail, use conservative default
                    source = "default"
                    final_decision = {
                        'should_irrigate': sensor_data.get('soil_moisture', 50) < 30,
                        'confidence': 0.5,
                        'duration_minutes': 10,
                        'reason': 'Based on default threshold (emergency fallback)'
                    }
        # Tích hợp với ResourceOptimizer nếu có
        if resource_optimizer is not None and hasattr(self, 'resource_optimizer') and self.resource_optimizer:
            try:
                # Sử dụng ResourceOptimizer để điều chỉnh quyết định
                optimized_schedule = self.resource_optimizer.optimize_schedule(
                    sensor_data, ["default"]
                )
                
                # Tích hợp kết quả từ ResourceOptimizer vào quyết định cuối cùng
                if 'final_decision' in locals():
                    # Điều chỉnh nên tưới hay không
                    if optimized_schedule["should_irrigate"] != final_decision["should_irrigate"]:
                        # Ưu tiên khuyến nghị của ResourceOptimizer nếu độ tin cậy cao
                        if final_decision["confidence"] < 0.8:
                            final_decision["should_irrigate"] = optimized_schedule["should_irrigate"]
                            final_decision["reason"] = optimized_schedule["reason"]
                    
                    # Điều chỉnh thời lượng tưới
                    if optimized_schedule.get("duration_minutes"):
                        final_decision["duration_minutes"] = optimized_schedule["duration_minutes"]
                    
                    # Đánh dấu đã sử dụng ResourceOptimizer
                    final_decision["used_resource_optimizer"] = True
            except Exception as e:
                logger.error(f"Error using ResourceOptimizer: {str(e)}")
        
        # If we haven't set a final decision yet, use the local prediction
        if 'final_decision' not in locals():
            source = "local_model"
            final_decision = local_prediction
        
        # Add metadata to the decision
        execution_time = time.time() - start_time
        metadata = {
            'source': source,
            'execution_time_seconds': execution_time,
            'timestamp': datetime.now().isoformat(),
            'used_api': api_prediction is not None
        }
        
        final_decision.update(metadata)
        logger.info(f"Final irrigation decision: {final_decision['should_irrigate']} from source: {source}")
        
        return final_decision
    
    def process_user_message(self, message_text):
        """
        Process a user message to determine intent and formulate a response.
        Uses local model first, then API if confidence is low.
        
        Args:
            message_text: Text message from user
            
        Returns:
            Dictionary with intent, response, and action to take
        """
        start_time = time.time()
        local_result = None
        api_result = None
        source = "hybrid"
        
        # Step 1: Try local chatbot model first
        if self.chatbot_model:
            try:
                local_result = self.chatbot_model.predict(message_text)
                logger.info(f"Local chatbot prediction: {local_result}")
                
                # If confidence is high enough, use local result
                if local_result['confidence'] >= self.confidence_threshold:
                    logger.info(f"Using local chatbot (confidence: {local_result['confidence']:.2f})")
                    source = "local_model"
                    intent = local_result['intent']
                    entities = local_result['entities']
                else:
                    logger.info(f"Local chatbot confidence too low: {local_result['confidence']:.2f}")
            except Exception as e:
                logger.error(f"Error in local chatbot model: {str(e)}")
                local_result = None
        
        # Step 2: If local result is None or confidence is low, try API
        if (local_result is None or 
            local_result['confidence'] < self.confidence_threshold) and self.openai_client:
            try:
                logger.info("Analyzing message with OpenAI API")
                api_result = self.openai_client.analyze_user_input(message_text)
                self.api_call_count += 1
                self.api_last_called = datetime.now()
                
                logger.info(f"API message analysis: {api_result}")
                
                if local_result is None:
                    source = "openai"
                    intent = api_result.get('intent', 'unknown')
                    entities = api_result.get('entities', {})
                else:
                    # Compare local and API results
                    source = "hybrid"
                    
                    # If they agree on intent, use that with high confidence
                    if local_result['intent'] == api_result.get('intent'):
                        intent = local_result['intent']
                    else:
                        # If they disagree, use API intent
                        intent = api_result.get('intent', local_result['intent'])
                    
                    # Combine entities, with API results taking precedence
                    entities = {**local_result['entities'], **api_result.get('entities', {})}
            except Exception as e:
                logger.error(f"Error in API message analysis: {str(e)}")
                
                # Fallback to local result if API fails
                if local_result is not None:
                    source = "local_model"
                    intent = local_result['intent']
                    entities = local_result['entities']
                else:
                    # If both fail, set unknown intent
                    source = "default"
                    intent = "unknown"
                    entities = {}
        
        # If we haven't set intent yet, use the local prediction
        if 'intent' not in locals():
            source = "local_model"
            intent = local_result['intent']
            entities = local_result['entities']
        
        # Determine action to take based on intent
        action = self._get_action_from_intent(intent, entities)
        
        # Generate response text
        response_text = self._generate_response(intent, entities, source)
        
        # Add metadata to the result
        execution_time = time.time() - start_time
        result = {
            'intent': intent,
            'entities': entities,
            'response': response_text,
            'action': action,
            'source': source,
            'execution_time_seconds': execution_time,
            'timestamp': datetime.now().isoformat(),
            'used_api': api_result is not None
        }
        
        logger.info(f"Final message processing result: intent={intent}, source={source}")
        
        return result
    
    def _get_action_from_intent(self, intent, entities):
        """
        Determine what action to take based on the identified intent.
        
        Args:
            intent: User intent
            entities: Extracted entities
            
        Returns:
            Dictionary with action details
        """
        action = {
            'type': 'none',
            'parameters': {}
        }
        
        if intent == 'turn_on_pump':
            action['type'] = 'activate_pump'
            
            # Extract duration if available
            if 'duration_minutes' in entities:
                action['parameters']['duration_minutes'] = entities['duration_minutes']
            else:
                action['parameters']['duration_minutes'] = 10  # Default duration
        
        elif intent == 'turn_off_pump':
            action['type'] = 'deactivate_pump'
        
        elif intent in ['query_soil_moisture', 'query_temperature', 
                        'query_humidity', 'query_light']:
            action['type'] = 'get_sensor_data'
            sensor_map = {
                'query_soil_moisture': 'soil_moisture',
                'query_temperature': 'temperature',
                'query_humidity': 'humidity',
                'query_light': 'light_level'
            }
            action['parameters']['sensor_type'] = sensor_map.get(intent)
        
        elif intent == 'get_status':
            action['type'] = 'get_system_status'
        
        elif intent == 'schedule_irrigation':
            action['type'] = 'schedule_irrigation'
            if 'time' in entities:
                action['parameters']['time'] = entities['time']
            if 'duration_minutes' in entities:
                action['parameters']['duration_minutes'] = entities['duration_minutes']
        
        return action
    
    def _generate_response(self, intent, entities, source):
        """
        Generate a response message based on intent and entities.
        
        Args:
            intent: User intent
            entities: Extracted entities
            source: Source of the intent detection
            
        Returns:
            Response text
        """
        # For complex responses, use the API if available
        if source != "local_model" and self.openai_client:
            try:
                # We'll implement this in the service layer where we have sensor data available
                return None  # Signal that we should use API for response generation
            except Exception as e:
                logger.error(f"Error generating API response: {str(e)}")
                # Fall back to template responses
        
        # Simple template-based responses
        responses = {
            'query_soil_moisture': "Tôi sẽ kiểm tra độ ẩm đất cho bạn.",
            'query_temperature': "Tôi sẽ kiểm tra nhiệt độ cho bạn.",
            'query_humidity': "Tôi sẽ kiểm tra độ ẩm không khí cho bạn.",
            'query_light': "Tôi sẽ kiểm tra mức độ ánh sáng cho bạn.",
            'turn_on_pump': "Đã bật máy bơm.",
            'turn_off_pump': "Đã tắt máy bơm.",
            'get_status': "Đang kiểm tra tình trạng hệ thống...",
            'schedule_irrigation': "Tôi sẽ đặt lịch tưới cho bạn.",
            'unknown': "Tôi không hiểu yêu cầu của bạn. Bạn có thể nói rõ hơn được không?"
        }
        
        response = responses.get(intent, responses['unknown'])
        
        # Add entity information if available
        if intent == 'turn_on_pump' and 'duration_minutes' in entities:
            response = f"Đã bật máy bơm trong {entities['duration_minutes']} phút."
        
        return response