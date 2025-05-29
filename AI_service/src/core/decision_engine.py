# src/core/decision_engine.py
import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add project root to path
# This is generally needed if you run this file directly and it needs to import
# other modules from your project. If run as part of a larger application (e.g., via `python -m ...`),
# or if your project is installed, this might not be strictly necessary or could be handled differently.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.config import CONFIDENCE_THRESHOLD
from src.models.irrigation_model import IrrigationModel # Assuming this class exists
from src.models.chatbot_model import ChatbotModel     # Assuming this class exists
from src.external_api.openai_client import OpenAIClient # Assuming this class exists
# from src.core.resource_optimizer import ResourceOptimizer # Assuming this class exists for type hinting, replace Any if used

# Default values that could be moved to config
DEFAULT_API_CONFIDENCE = 0.9
HYBRID_DISAGREEMENT_CONFIDENCE = 0.8
DEFAULT_PUMP_DURATION_MINUTES = 10
FALLBACK_SOIL_MOISTURE_THRESHOLD = 30
EMERGENCY_FALLBACK_CONFIDENCE = 0.5

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

    def __init__(self, confidence_threshold: Optional[float] = None):
        """
        Initialize the decision engine.

        Args:
            confidence_threshold: Threshold for model confidence (0.0-1.0)
        """
        self.confidence_threshold: float = confidence_threshold or CONFIDENCE_THRESHOLD

        self.irrigation_model: Optional[IrrigationModel] = None
        self.chatbot_model: Optional[ChatbotModel] = None
        self.openai_client: Optional[OpenAIClient] = None
        self.resource_optimizer: Optional[Any] = None # Replace 'Any' with 'ResourceOptimizer' type if available

        self.api_call_count: int = 0
        self.api_last_called: Optional[datetime] = None

        logger.info(f"Decision Engine initialized with confidence threshold: {self.confidence_threshold}")

    def initialize_components(self,
                              use_local_models: bool = True,
                              use_api: bool = True,
                              resource_optimizer_instance: Optional[Any] = None): # Replace 'Any' with 'ResourceOptimizer' type
        """
        Initialize required components (models and API clients).

        Args:
            use_local_models: Whether to initialize local models.
            use_api: Whether to initialize API clients.
            resource_optimizer_instance: Optional ResourceOptimizer instance.
        """
        self.resource_optimizer = resource_optimizer_instance
        try:
            if use_local_models:
                logger.info("Initializing local models...")
                try:
                    self.irrigation_model = IrrigationModel()
                    self.irrigation_model.load_model()
                    logger.info("Local irrigation model initialized successfully.")
                except Exception as e:
                    logger.error(f"Error initializing local irrigation model: {str(e)}. It will not be available.")
                    self.irrigation_model = None

                try:
                    self.chatbot_model = ChatbotModel()
                    self.chatbot_model.load_model()
                    logger.info("Local chatbot model initialized successfully.")
                except Exception as e:
                    logger.error(f"Error initializing local chatbot model: {str(e)}. It will not be available.")
                    self.chatbot_model = None

            if use_api:
                logger.info("Initializing API client...")
                try:
                    self.openai_client = OpenAIClient(use_cache=True)
                    logger.info("API client initialized successfully.")
                except Exception as e:
                    logger.error(f"Error initializing OpenAI client: {str(e)}. API features will not be available.")
                    self.openai_client = None

        except Exception as e: # Catch-all for unexpected issues during component setup
            logger.error(f"Unexpected error during component initialization: {str(e)}")
            if use_local_models and self.irrigation_model is None and self.chatbot_model is None:
                 logger.warning("Local models failed to initialize.")
            if use_api and self.openai_client is None:
                logger.warning("API client failed to initialize.")


    def get_irrigation_decision(self, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine whether irrigation is needed based on sensor data.
        Uses local model first, then API if confidence is low or local model unavailable.

        Args:
            sensor_data: Dictionary with current sensor readings.

        Returns:
            Dictionary with irrigation decision and metadata.
        """
        start_time = time.time()
        local_prediction_result: Optional[Dict[str, Any]] = None
        api_prediction_result: Optional[Dict[str, Any]] = None
        final_decision: Dict[str, Any]
        source: str = "default_initial"

        final_decision = {
            'should_irrigate': sensor_data.get('soil_moisture', 50) < FALLBACK_SOIL_MOISTURE_THRESHOLD,
            'confidence': 0.1,
            'duration_minutes': DEFAULT_PUMP_DURATION_MINUTES,
            'reason': 'Initial default pending model/API analysis.',
            'used_resource_optimizer': False
        }

        if self.irrigation_model:
            try:
                local_prediction_result = self.irrigation_model.predict(sensor_data)
                logger.info(f"Local irrigation model prediction: {local_prediction_result}")
                if local_prediction_result['confidence'] >= self.confidence_threshold:
                    logger.info(f"Using local model prediction (confidence: {local_prediction_result['confidence']:.2f})")
                    source = "local_model"
                    final_decision = local_prediction_result.copy()
                else:
                    logger.info(f"Local model confidence too low: {local_prediction_result['confidence']:.2f}. Considering API.")
                    source = "local_model_low_confidence"
            except Exception as e:
                logger.error(f"Error in local irrigation model: {str(e)}. Will try API if available.")
                local_prediction_result = None
                source = "local_model_error"
        else:
            logger.info("Local irrigation model not available. Will try API if available.")
            source = "no_local_model"

        use_api_for_irrigation = (
            (local_prediction_result is None or
             local_prediction_result['confidence'] < self.confidence_threshold)
            and self.openai_client
        )

        if use_api_for_irrigation:
            try:
                logger.info("Requesting irrigation recommendation from OpenAI API.")
                api_prediction_result = self.openai_client.recommend_irrigation(sensor_data)
                self.api_call_count += 1
                self.api_last_called = datetime.now()
                logger.info(f"API irrigation recommendation: {api_prediction_result}")

                api_should_irrigate = api_prediction_result.get('should_irrigate', False)
                api_duration = api_prediction_result.get('duration_minutes', DEFAULT_PUMP_DURATION_MINUTES)
                api_reason = api_prediction_result.get('reason', 'Based on API analysis')

                if local_prediction_result is None or source in ["local_model_error", "no_local_model"]:
                    source = "openai_api"
                    final_decision = {
                        'should_irrigate': api_should_irrigate,
                        'confidence': DEFAULT_API_CONFIDENCE,
                        'duration_minutes': api_duration,
                        'reason': api_reason
                    }
                else:
                    source = "hybrid_local_api"
                    confidence = DEFAULT_API_CONFIDENCE
                    if local_prediction_result['should_irrigate'] == api_should_irrigate:
                        confidence = max(local_prediction_result['confidence'], DEFAULT_API_CONFIDENCE)
                    else:
                        confidence = HYBRID_DISAGREEMENT_CONFIDENCE
                    final_decision = {
                        'should_irrigate': api_should_irrigate,
                        'confidence': confidence,
                        'duration_minutes': api_duration,
                        'reason': f"Combined: Local ({local_prediction_result.get('reason', 'N/A')}) & API ({api_reason})"
                    }
            except Exception as e:
                logger.error(f"Error in API irrigation recommendation: {str(e)}")
                api_prediction_result = None
                if local_prediction_result is not None and source != "local_model_error":
                    logger.info("API failed, falling back to available local model prediction.")
                    source = "local_model_api_fallback"
                    final_decision = local_prediction_result.copy()
                else:
                    logger.warning("API failed and no reliable local model prediction. Using emergency fallback.")
                    source = "emergency_fallback_api_failed"
                    final_decision = {
                        'should_irrigate': sensor_data.get('soil_moisture', 50) < FALLBACK_SOIL_MOISTURE_THRESHOLD,
                        'confidence': EMERGENCY_FALLBACK_CONFIDENCE,
                        'duration_minutes': DEFAULT_PUMP_DURATION_MINUTES,
                        'reason': 'Emergency fallback: Both local model and API failed or unavailable.'
                    }
        elif local_prediction_result is not None and source == "local_model":
            pass
        elif local_prediction_result is not None and source == "local_model_low_confidence":
            logger.info("API not used/available. Sticking with low-confidence local model prediction.")
            final_decision = local_prediction_result.copy()
            source = "local_model_low_confidence_no_api"
        elif local_prediction_result is None and self.openai_client is None:
            logger.warning("Neither local model nor API available for irrigation. Using emergency fallback.")
            source = "emergency_fallback_no_systems"
            final_decision = {
                'should_irrigate': sensor_data.get('soil_moisture', 50) < FALLBACK_SOIL_MOISTURE_THRESHOLD,
                'confidence': EMERGENCY_FALLBACK_CONFIDENCE,
                'duration_minutes': DEFAULT_PUMP_DURATION_MINUTES,
                'reason': 'Emergency fallback: No models or API available.'
            }

        if hasattr(self, 'resource_optimizer') and self.resource_optimizer:
            try:
                logger.info("Applying resource optimizer to irrigation decision.")
                optimized_schedule = self.resource_optimizer.optimize_schedule(
                    sensor_data, ["default_irrigation_profile"]
                )
                if optimized_schedule:
                    logger.info(f"Resource optimizer suggestion: {optimized_schedule}")
                    if 'should_irrigate' in optimized_schedule and \
                       optimized_schedule['should_irrigate'] != final_decision.get('should_irrigate'):
                        if final_decision.get('confidence', 0) < 0.75 or optimized_schedule.get('confidence', DEFAULT_API_CONFIDENCE) > final_decision.get('confidence', 0):
                            final_decision['should_irrigate'] = optimized_schedule['should_irrigate']
                            final_decision['reason'] = optimized_schedule.get('reason', final_decision.get('reason', '')) + " (Optimized)"
                            final_decision['confidence'] = max(final_decision.get('confidence', 0.5), optimized_schedule.get('confidence', 0.75))
                    if 'duration_minutes' in optimized_schedule:
                        final_decision['duration_minutes'] = optimized_schedule['duration_minutes']
                    final_decision['used_resource_optimizer'] = True
                    source += "_optimized"
            except Exception as e:
                logger.error(f"Error using ResourceOptimizer for irrigation: {str(e)}")
                final_decision['used_resource_optimizer'] = False

        execution_time = time.time() - start_time
        metadata = {
            'source': source,
            'execution_time_seconds': round(execution_time, 4),
            'timestamp': datetime.now().isoformat(),
            'used_api': api_prediction_result is not None
        }
        if 'used_resource_optimizer' not in final_decision:
            final_decision['used_resource_optimizer'] = False
        final_decision.update(metadata)
        logger.info(f"Final irrigation decision: {final_decision.get('should_irrigate')} from source: {source}, confidence: {final_decision.get('confidence', 0):.2f}")
        return final_decision

    def process_user_message(self, message_text: str) -> Dict[str, Any]:
        """
        Process a user message to determine intent and formulate a response.
        Uses local model first, then API if confidence is low or local unavailable.

        Args:
            message_text: Text message from user.

        Returns:
            Dictionary with intent, response, action, and metadata.
        """
        start_time = time.time()
        local_result: Optional[Dict[str, Any]] = None
        api_result: Optional[Dict[str, Any]] = None
        source: str = "default_initial"
        intent: str = "unknown"
        entities: Dict[str, Any] = {}

        if self.chatbot_model:
            try:
                local_result = self.chatbot_model.predict(message_text)
                logger.info(f"Local chatbot prediction: {local_result}")
                if local_result['confidence'] >= self.confidence_threshold:
                    logger.info(f"Using local chatbot (confidence: {local_result['confidence']:.2f})")
                    source = "local_model"
                    intent = local_result['intent']
                    entities = local_result.get('entities', {})
                else:
                    logger.info(f"Local chatbot confidence too low: {local_result['confidence']:.2f}. Considering API.")
                    source = "local_model_low_confidence"
            except Exception as e:
                logger.error(f"Error in local chatbot model: {str(e)}. Will try API if available.")
                local_result = None
                source = "local_model_error"
        else:
            logger.info("Local chatbot model not available. Will try API if available.")
            source = "no_local_model"

        use_api_for_chat = (
            (intent == "unknown" or
             (local_result and local_result.get('confidence',0) < self.confidence_threshold) or # Access confidence safely
             local_result is None)
            and self.openai_client
        )

        if use_api_for_chat:
            try:
                logger.info("Analyzing message with OpenAI API.")
                api_result = self.openai_client.analyze_user_input(message_text)
                self.api_call_count += 1
                self.api_last_called = datetime.now()
                logger.info(f"API message analysis: {api_result}")

                api_intent = api_result.get('intent', 'unknown')
                api_entities = api_result.get('entities', {})

                if local_result is None or source in ["local_model_error", "no_local_model"]:
                    source = "openai_api"
                    intent = api_intent
                    entities = api_entities
                else:
                    source = "hybrid_local_api"
                    local_intent = local_result.get('intent', 'unknown') # Safe access
                    local_confidence = local_result.get('confidence', 0) # Safe access
                    if local_intent == api_intent or local_confidence < 0.5:
                        intent = api_intent
                    else:
                        logger.warning(f"Intent mismatch: Local '{local_intent}', API '{api_intent}'. Using API.")
                        intent = api_intent
                    entities = {**local_result.get('entities',{}), **api_entities}
            except Exception as e:
                logger.error(f"Error in API message analysis: {str(e)}")
                api_result = None
                if local_result is not None and source != "local_model_error" and intent == "unknown":
                    logger.info("API failed, falling back to available local chatbot result.")
                    source = "local_model_api_fallback"
                    intent = local_result.get('intent', 'unknown')
                    entities = local_result.get('entities', {})
                elif intent == "unknown":
                    logger.warning("API failed and no reliable local chatbot result. Intent remains 'unknown'.")
                    source = "emergency_fallback_api_failed"
                    intent = "unknown"
                    entities = {}
        elif intent != "unknown":
             pass
        elif local_result is not None and source == "local_model_low_confidence":
            logger.info("API not used/available. Sticking with low-confidence local chatbot result.")
            intent = local_result.get('intent', 'unknown')
            entities = local_result.get('entities', {})
            source = "local_model_low_confidence_no_api"
        elif local_result is None and self.openai_client is None:
            logger.warning("Neither local model nor API available for chat. Intent remains 'unknown'.")
            source = "emergency_fallback_no_systems"
            intent = "unknown"
            entities = {}

        action = self._get_action_from_intent(intent, entities)
        response_text = self._generate_response(intent, entities, source, message_text)

        execution_time = time.time() - start_time
        result = {
            'intent': intent,
            'entities': entities,
            'response': response_text,
            'action': action,
            'source': source,
            'execution_time_seconds': round(execution_time, 4),
            'timestamp': datetime.now().isoformat(),
            'used_api': api_result is not None
        }
        logger.info(f"Final message processing result: intent='{intent}', source='{source}'")
        return result

    def _get_action_from_intent(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine what action to take based on the identified intent.
        """
        action: Dict[str, Any] = {'type': 'none', 'parameters': {}}
        if intent == 'turn_on_pump':
            action['type'] = 'activate_pump'
            action['parameters']['duration_minutes'] = entities.get('duration_minutes', DEFAULT_PUMP_DURATION_MINUTES)
        elif intent == 'turn_off_pump':
            action['type'] = 'deactivate_pump'
        elif intent in ['query_soil_moisture', 'query_temperature', 'query_humidity', 'query_light']:
            action['type'] = 'get_sensor_data'
            sensor_map: Dict[str, str] = {
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

    def _generate_response(self, intent: str, entities: Dict[str, Any], source: str, original_message: str) -> str:
        """
        Generate a response message based on intent and entities.
        """
        if source not in ["local_model", "local_model_low_confidence_no_api", "local_model_api_fallback"] and self.openai_client:
            try:
                # Placeholder for potential API call for response generation
                # For now, falls through to template-based responses.
                # logger.info(f"Considering API for response generation for intent '{intent}' from source '{source}'")
                pass
            except Exception as e:
                logger.error(f"Error during API response consideration: {str(e)}. Falling back to template.")

        responses: Dict[str, str] = {
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

        if intent == 'turn_on_pump' and 'duration_minutes' in entities:
            response = f"Đã bật máy bơm trong {entities['duration_minutes']} phút."
        elif intent == 'schedule_irrigation':
            time_str = f" vào lúc {entities['time']}" if 'time' in entities else ""
            duration_str = f" trong {entities['duration_minutes']} phút" if 'duration_minutes' in entities else ""
            if time_str or duration_str:
                 response = f"Đã đặt lịch tưới{time_str}{duration_str}."
            # else: # This part might be too verbose if only intent is schedule_irrigation without params
            #     response = "Đã ghi nhận yêu cầu đặt lịch tưới. Vui lòng cung cấp thêm thời gian và thời lượng."
        return response
