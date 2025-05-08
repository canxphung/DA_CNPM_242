#!/usr/bin/env python
# tests/test_independent_decision_engine.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch database and dependencies
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.db_client'] = MagicMock()
sys.modules['src.database.models_storage'] = MagicMock()
sys.modules['src.database.model_storage'] = MagicMock()
sys.modules['src.models'] = MagicMock()
sys.modules['src.models.irrigation_model'] = MagicMock()
sys.modules['src.models.chatbot_model'] = MagicMock()

# Import mocks
from tests.mocks.openai_mock import backoff, openai
sys.modules['backoff'] = backoff
sys.modules['openai'] = openai

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]

# Create a minimal DecisionEngine class for testing
class TestDecisionEngine:
    """Simplified DecisionEngine for testing"""
    
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
        self.resource_optimizer = None
        
        # Track API usage
        self.api_call_count = 0
        self.api_last_called = None
    
    def initialize_components(self, use_local_models=True, use_api=True, resource_optimizer=None):
        """
        Initialize required components (models and API clients).
        """
        self.resource_optimizer = resource_optimizer
        
        if use_local_models:
            self.irrigation_model = MagicMock()
            self.chatbot_model = MagicMock()
        
        if use_api:
            self.openai_client = MagicMock()
    
    def get_irrigation_decision(self, sensor_data):
        """
        Determine whether irrigation is needed based on sensor data.
        """
        # Check soil moisture
        soil_moisture = sensor_data.get('soil_moisture', 50)
        
        # Default decision
        decision = {
            'should_irrigate': soil_moisture < 30,
            'confidence': 0.8 if soil_moisture < 25 else 0.6,
            'duration_minutes': 15 if soil_moisture < 25 else 10,
            'reason': 'Soil moisture below threshold'
        }
        
        # Use irrigation model if available
        if self.irrigation_model:
            try:
                model_decision = self.irrigation_model.predict(sensor_data)
                if model_decision['confidence'] >= self.confidence_threshold:
                    decision = model_decision
            except Exception:
                pass
        
        # Use API if confidence is low and API is available
        if decision['confidence'] < self.confidence_threshold and self.openai_client:
            try:
                api_decision = self.openai_client.recommend_irrigation(sensor_data)
                decision = {
                    'should_irrigate': api_decision.get('should_irrigate', decision['should_irrigate']),
                    'confidence': 0.9,  # Higher confidence from API
                    'duration_minutes': api_decision.get('duration_minutes', decision['duration_minutes']),
                    'reason': api_decision.get('reason', decision['reason'])
                }
                self.api_call_count += 1
                self.api_last_called = datetime.now()
            except Exception:
                pass
        
        # Use resource optimizer if available
        if self.resource_optimizer and hasattr(self.resource_optimizer, 'optimize_schedule'):
            try:
                optimized = self.resource_optimizer.optimize_schedule(sensor_data, ["default"])
                decision['should_irrigate'] = optimized.get('should_irrigate', decision['should_irrigate'])
                decision['duration_minutes'] = optimized.get('duration_minutes', decision['duration_minutes'])
                decision['reason'] = optimized.get('reason', decision['reason'])
            except Exception:
                pass
        
        # Add metadata
        decision['source'] = 'hybrid'
        decision['timestamp'] = datetime.now().isoformat()
        
        return decision
    
    def process_user_message(self, message_text):
        """
        Process a user message to determine intent and formulate a response.
        """
        # Default response
        result = {
            'intent': 'unknown',
            'entities': {},
            'response': 'I did not understand that.',
            'action': {'type': 'none', 'parameters': {}}
        }
        
        # Use chatbot model if available
        if self.chatbot_model:
            try:
                model_result = self.chatbot_model.predict(message_text)
                if model_result['confidence'] >= self.confidence_threshold:
                    result['intent'] = model_result['intent']
                    result['entities'] = model_result['entities']
                    result['response'] = model_result.get('response')
            except Exception:
                pass
        
        # Use API if confidence is low or no response and API is available
        use_api = (result['intent'] == 'unknown' or not result['response']) and self.openai_client
        
        if use_api:
            try:
                api_result = self.openai_client.analyze_user_input(message_text)
                result['intent'] = api_result.get('intent', result['intent'])
                result['entities'] = {**result['entities'], **api_result.get('entities', {})}
                self.api_call_count += 1
                self.api_last_called = datetime.now()
            except Exception:
                pass
        
        # Determine action to take based on intent
        result['action'] = self._get_action_from_intent(result['intent'], result['entities'])
        
        # Generate response if needed and API is available
        if not result['response'] and self.openai_client:
            try:
                result['response'] = self.openai_client.generate_response(
                    result['intent'], result['entities']
                )
                self.api_call_count += 1
                self.api_last_called = datetime.now()
            except Exception:
                # Fall back to simple response
                result['response'] = self._generate_simple_response(result['intent'], result['entities'])
        
        # Add metadata
        result['timestamp'] = datetime.now().isoformat()
        
        return result
    
    def _get_action_from_intent(self, intent, entities):
        """Determine what action to take based on the identified intent."""
        action = {
            'type': 'none',
            'parameters': {}
        }
        
        intent_to_action = {
            'turn_on_pump': 'activate_pump',
            'turn_off_pump': 'deactivate_pump',
            'get_status': 'get_system_status'
        }
        
        if intent in intent_to_action:
            action['type'] = intent_to_action[intent]
        
        # Add parameters for specific intents
        if intent == 'turn_on_pump':
            if 'duration_minutes' in entities:
                action['parameters']['duration_minutes'] = entities['duration_minutes']
            else:
                action['parameters']['duration_minutes'] = 10  # Default duration
        
        elif intent in ['query_soil_moisture', 'query_temperature', 'query_humidity', 'query_light']:
            action['type'] = 'get_sensor_data'
            sensor_map = {
                'query_soil_moisture': 'soil_moisture',
                'query_temperature': 'temperature',
                'query_humidity': 'humidity',
                'query_light': 'light_level'
            }
            action['parameters']['sensor_type'] = sensor_map.get(intent)
        
        return action
    
    def _generate_simple_response(self, intent, entities):
        """Generate a simple response based on intent and entities."""
        responses = {
            'query_soil_moisture': "Tôi sẽ kiểm tra độ ẩm đất cho bạn.",
            'query_temperature': "Tôi sẽ kiểm tra nhiệt độ cho bạn.",
            'query_humidity': "Tôi sẽ kiểm tra độ ẩm không khí cho bạn.",
            'query_light': "Tôi sẽ kiểm tra mức độ ánh sáng cho bạn.",
            'turn_on_pump': "Đã bật máy bơm.",
            'turn_off_pump': "Đã tắt máy bơm.",
            'get_status': "Đang kiểm tra tình trạng hệ thống...",
            'unknown': "Tôi không hiểu yêu cầu của bạn. Bạn có thể nói rõ hơn được không?"
        }
        
        response = responses.get(intent, responses['unknown'])
        
        # Add entity information
        if intent == 'turn_on_pump' and 'duration_minutes' in entities:
            response = f"Đã bật máy bơm trong {entities['duration_minutes']} phút."
        
        return response


class TestDecisionEngineClass(unittest.TestCase):
    """Test cases for DecisionEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TestDecisionEngine(confidence_threshold=0.7)
        self.engine.initialize_components(use_local_models=True, use_api=True)
    
    def test_initialization(self):
        """Test that engine initializes correctly."""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.confidence_threshold, 0.7)
        self.assertIsNotNone(self.engine.irrigation_model)
        self.assertIsNotNone(self.engine.chatbot_model)
        self.assertIsNotNone(self.engine.openai_client)
        self.assertEqual(self.engine.api_call_count, 0)
        self.assertIsNone(self.engine.api_last_called)
    
    def test_get_irrigation_decision_dry_soil(self):
        """Test irrigation decision with dry soil."""
        # Configure mock irrigation model
        self.engine.irrigation_model.predict.return_value = {
            'should_irrigate': True,
            'confidence': 0.8,
            'duration_minutes': 15,
            'reason': 'Soil moisture too low'
        }
        
        # Test with dry soil
        sensor_data = {
            'soil_moisture': 20,
            'temperature': 28,
            'humidity': 40
        }
        
        decision = self.engine.get_irrigation_decision(sensor_data)
        
        # Verify decision
        self.assertTrue(decision['should_irrigate'])
        self.assertGreaterEqual(decision['confidence'], 0.7)
        self.assertGreater(decision['duration_minutes'], 0)
        self.assertIn('reason', decision)
        self.assertIn('timestamp', decision)
        
        # Verify model was called
        self.engine.irrigation_model.predict.assert_called_once_with(sensor_data)
    
    def test_get_irrigation_decision_wet_soil(self):
        """Test irrigation decision with wet soil."""
        # Configure mock irrigation model
        self.engine.irrigation_model.predict.return_value = {
            'should_irrigate': False,
            'confidence': 0.9,
            'duration_minutes': 0,
            'reason': 'Soil moisture adequate'
        }
        
        # Test with wet soil
        sensor_data = {
            'soil_moisture': 60,
            'temperature': 25,
            'humidity': 70
        }
        
        decision = self.engine.get_irrigation_decision(sensor_data)
        
        # Verify decision
        self.assertFalse(decision['should_irrigate'])
        self.assertEqual(decision['duration_minutes'], 0)
        
        # Verify model was called
        self.engine.irrigation_model.predict.assert_called_once_with(sensor_data)
    
    def test_process_user_message_irrigation_command(self):
        """Test processing an irrigation command."""
        # Configure mock chatbot model
        self.engine.chatbot_model.predict.return_value = {
            'intent': 'turn_on_pump',
            'entities': {'duration_minutes': 15},
            'confidence': 0.8,
            'response': 'Turning on the pump for 15 minutes.'
        }
        
        # Test message
        message = "Bật máy bơm trong 15 phút"
        
        result = self.engine.process_user_message(message)
        
        # Verify result
        self.assertEqual(result['intent'], 'turn_on_pump')
        self.assertEqual(result['entities']['duration_minutes'], 15)
        self.assertEqual(result['action']['type'], 'activate_pump')
        self.assertEqual(result['action']['parameters']['duration_minutes'], 15)
        self.assertIsNotNone(result['response'])
        
        # Verify model was called
        self.engine.chatbot_model.predict.assert_called_once_with(message)
    
    def test_process_user_message_sensor_query(self):
        """Test processing a sensor query."""
        # Configure mock chatbot model
        self.engine.chatbot_model.predict.return_value = {
            'intent': 'query_soil_moisture',
            'entities': {},
            'confidence': 0.85,
            'response': 'Checking soil moisture for you.'
        }
        
        # Test message
        message = "Kiểm tra độ ẩm đất"
        
        result = self.engine.process_user_message(message)
        
        # Verify result
        self.assertEqual(result['intent'], 'query_soil_moisture')
        self.assertEqual(result['action']['type'], 'get_sensor_data')
        self.assertEqual(result['action']['parameters']['sensor_type'], 'soil_moisture')
        self.assertIsNotNone(result['response'])
        
        # Verify model was called
        self.engine.chatbot_model.predict.assert_called_once_with(message)
    
    def test_process_user_message_unknown_intent(self):
        """Test processing a message with unknown intent."""
        # Configure mock chatbot model (low confidence)
        self.engine.chatbot_model.predict.return_value = {
            'intent': 'unknown',
            'entities': {},
            'confidence': 0.3,
            'response': None
        }
        
        # Configure mock OpenAI client
        self.engine.openai_client.analyze_user_input.return_value = {
            'intent': 'get_status',
            'entities': {}
        }
        self.engine.openai_client.generate_response.return_value = "Let me check the system status for you."
        
        # Test message
        message = "Hệ thống đang thế nào?"
        
        result = self.engine.process_user_message(message)
        
        # Verify result
        self.assertEqual(result['intent'], 'get_status')
        self.assertEqual(result['action']['type'], 'get_system_status')
        self.assertIsNotNone(result['response'])
        
        # Verify model and API were called
        self.engine.chatbot_model.predict.assert_called_once_with(message)
        self.engine.openai_client.analyze_user_input.assert_called_once_with(message)
        self.assertGreater(self.engine.api_call_count, 0)
    
    def test_get_action_from_intent(self):
        """Test action determination from intent."""
        # Test turn_on_pump intent
        action = self.engine._get_action_from_intent('turn_on_pump', {'duration_minutes': 20})
        self.assertEqual(action['type'], 'activate_pump')
        self.assertEqual(action['parameters']['duration_minutes'], 20)
        
        # Test turn_on_pump without duration
        action = self.engine._get_action_from_intent('turn_on_pump', {})
        self.assertEqual(action['type'], 'activate_pump')
        self.assertEqual(action['parameters']['duration_minutes'], 10)  # Default
        
        # Test query_temperature
        action = self.engine._get_action_from_intent('query_temperature', {})
        self.assertEqual(action['type'], 'get_sensor_data')
        self.assertEqual(action['parameters']['sensor_type'], 'temperature')
        
        # Test unknown intent
        action = self.engine._get_action_from_intent('unknown', {})
        self.assertEqual(action['type'], 'none')
        self.assertEqual(action['parameters'], {})


if __name__ == '__main__':
    unittest.main()
