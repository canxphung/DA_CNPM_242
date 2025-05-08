#!/usr/bin/env python
# tests/test_decision_engine.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch database và redis trước khi import các module khác
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.db_client'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()

# Patch models
sys.modules['src.models'] = MagicMock()
sys.modules['src.models.irrigation_model'] = MagicMock()
sys.modules['src.models.chatbot_model'] = MagicMock()
sys.modules['src.models.base_model'] = MagicMock()

# Các class mock
sys.modules['src.models.irrigation_model'].IrrigationModel = MagicMock
sys.modules['src.models.chatbot_model'].ChatbotModel = MagicMock

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]

# Import module cần test
from src.core.decision_engine import DecisionEngine

class TestDecisionEngine(unittest.TestCase):
    """Test cases for DecisionEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = DecisionEngine(confidence_threshold=0.7)
    
    def test_initialization(self):
        """Test that engine initializes correctly."""
        self.assertIsNotNone(self.engine)
        self.assertEqual(self.engine.confidence_threshold, 0.7)
        self.assertIsNone(self.engine.irrigation_model)
        self.assertIsNone(self.engine.chatbot_model)
        self.assertIsNone(self.engine.openai_client)
        self.assertEqual(self.engine.api_call_count, 0)
        self.assertIsNone(self.engine.api_last_called)
    
    @patch('src.core.decision_engine.IrrigationModel')
    @patch('src.core.decision_engine.ChatbotModel')
    @patch('src.core.decision_engine.OpenAIClient')
    def test_initialize_components(self, mock_openai_client, mock_chatbot_model, mock_irrigation_model):
        """Test initialize_components method."""
        # Setup mocks
        mock_irrigation_instance = MagicMock()
        mock_chatbot_instance = MagicMock()
        mock_openai_instance = MagicMock()
        
        mock_irrigation_model.return_value = mock_irrigation_instance
        mock_chatbot_model.return_value = mock_chatbot_instance
        mock_openai_client.return_value = mock_openai_instance
        
        # Initialize with local models only
        self.engine.initialize_components(use_local_models=True, use_api=False)
        
        self.assertIsNotNone(self.engine.irrigation_model)
        self.assertIsNotNone(self.engine.chatbot_model)
        self.assertIsNone(self.engine.openai_client)
        
        mock_irrigation_instance.load.assert_called_once()
        mock_chatbot_instance.load.assert_called_once()
        mock_openai_client.assert_not_called()
        
        # Reset and initialize with API only
        self.engine = DecisionEngine(confidence_threshold=0.7)
        self.engine.initialize_components(use_local_models=False, use_api=True)
        
        self.assertIsNone(self.engine.irrigation_model)
        self.assertIsNone(self.engine.chatbot_model)
        self.assertIsNotNone(self.engine.openai_client)
        
        # Reset and initialize with both
        self.engine = DecisionEngine(confidence_threshold=0.7)
        self.engine.initialize_components(use_local_models=True, use_api=True)
        
        self.assertIsNotNone(self.engine.irrigation_model)
        self.assertIsNotNone(self.engine.chatbot_model)
        self.assertIsNotNone(self.engine.openai_client)
    
    def test_get_irrigation_decision_local_high_confidence(self):
        """Test get_irrigation_decision with local model and high confidence."""
        # Setup mock irrigation model
        self.engine.irrigation_model = MagicMock()
        self.engine.irrigation_model.predict.return_value = {
            'should_irrigate': True,
            'confidence': 0.9,
            'duration_minutes': 15,
            'reason': 'Soil moisture low'
        }
        
        # Mock resource optimizer
        mock_resource_optimizer = MagicMock()
        self.engine.resource_optimizer = mock_resource_optimizer
        
        # Test sensor data
        sensor_data = {
            'soil_moisture': 20,
            'temperature': 30,
            'humidity': 40,
            'light_level': 800
        }
        
        # Get decision
        result = self.engine.get_irrigation_decision(sensor_data)
        
        # Verify result
        self.assertTrue(result['should_irrigate'])
        self.assertEqual(result['confidence'], 0.9)
        self.assertEqual(result['duration_minutes'], 15)
        self.assertEqual(result['source'], 'local_model')
        self.assertFalse(result['used_api'])
        
        # Verify calls
        self.engine.irrigation_model.predict.assert_called_once_with(sensor_data)
    
    def test_get_irrigation_decision_api_fallback(self):
        """Test get_irrigation_decision with API fallback for low confidence."""
        # Setup mock irrigation model with low confidence
        self.engine.irrigation_model = MagicMock()
        self.engine.irrigation_model.predict.return_value = {
            'should_irrigate': True,
            'confidence': 0.5,  # Below threshold
            'duration_minutes': 10,
            'reason': 'Low confidence prediction'
        }
        
        # Setup mock OpenAI client
        self.engine.openai_client = MagicMock()
        self.engine.openai_client.recommend_irrigation.return_value = {
            'should_irrigate': False,  # Different from local model
            'duration_minutes': 0,
            'reason': 'API says no need to irrigate'
        }
        
        # Test sensor data
        sensor_data = {
            'soil_moisture': 35,
            'temperature': 25,
            'humidity': 60,
            'light_level': 500
        }
        
        # Get decision
        result = self.engine.get_irrigation_decision(sensor_data)
        
        # Verify result
        self.assertFalse(result['should_irrigate'])  # API result
        self.assertTrue(result['confidence'] > 0.5)  # Higher than local confidence
        self.assertEqual(result['source'], 'hybrid')
        self.assertTrue(result['used_api'])
        
        # Verify calls
        self.engine.irrigation_model.predict.assert_called_once_with(sensor_data)
        self.engine.openai_client.recommend_irrigation.assert_called_once_with(sensor_data)
        self.assertEqual(self.engine.api_call_count, 1)
        self.assertIsNotNone(self.engine.api_last_called)
    
    def test_get_irrigation_decision_no_models(self):
        """Test get_irrigation_decision with no models available."""
        # No models configured
        self.engine.irrigation_model = None
        self.engine.openai_client = None
        
        # Test sensor data with very low soil moisture
        sensor_data = {
            'soil_moisture': 10,  # Very low
            'temperature': 35,
            'humidity': 30,
            'light_level': 900
        }
        
        # Get decision
        result = self.engine.get_irrigation_decision(sensor_data)
        
        # Verify result uses default logic
        self.assertTrue(result['should_irrigate'])
        self.assertEqual(result['confidence'], 0.5)
        self.assertEqual(result['source'], 'default')
        self.assertFalse(result['used_api'])
    
    def test_process_user_message_local_high_confidence(self):
        """Test process_user_message with local model and high confidence."""
        # Setup mock chatbot model
        self.engine.chatbot_model = MagicMock()
        self.engine.chatbot_model.predict.return_value = {
            'intent': 'turn_on_pump',
            'entities': {'duration_minutes': 15},
            'confidence': 0.8,
            'response': 'Đã bật máy bơm trong 15 phút.'
        }
        
        # Test message
        message_text = "Bật máy bơm trong 15 phút"
        
        # Process message
        result = self.engine.process_user_message(message_text)
        
        # Verify result
        self.assertEqual(result['intent'], 'turn_on_pump')
        self.assertEqual(result['entities'], {'duration_minutes': 15})
        self.assertEqual(result['source'], 'local_model')
        self.assertFalse(result['used_api'])
        self.assertEqual(result['action']['type'], 'activate_pump')
        self.assertEqual(result['action']['parameters']['duration_minutes'], 15)
        
        # Verify calls
        self.engine.chatbot_model.predict.assert_called_once_with(message_text)
    
    def test_process_user_message_api_fallback(self):
        """Test process_user_message with API fallback for low confidence."""
        # Setup mock chatbot model with low confidence
        self.engine.chatbot_model = MagicMock()
        self.engine.chatbot_model.predict.return_value = {
            'intent': 'unknown',
            'entities': {},
            'confidence': 0.4,  # Below threshold
            'response': None
        }
        
        # Setup mock OpenAI client
        self.engine.openai_client = MagicMock()
        self.engine.openai_client.analyze_user_input.return_value = {
            'intent': 'query_soil_moisture',
            'entities': {}
        }
        
        # Test message
        message_text = "Độ ẩm đất hiện tại thế nào?"
        
        # Process message
        result = self.engine.process_user_message(message_text)
        
        # Verify result
        self.assertEqual(result['intent'], 'query_soil_moisture')  # API result
        self.assertEqual(result['source'], 'hybrid')
        self.assertTrue(result['used_api'])
        self.assertEqual(result['action']['type'], 'get_sensor_data')
        self.assertEqual(result['action']['parameters']['sensor_type'], 'soil_moisture')
        
        # Verify calls
        self.engine.chatbot_model.predict.assert_called_once_with(message_text)
        self.engine.openai_client.analyze_user_input.assert_called_once_with(message_text)
        self.assertEqual(self.engine.api_call_count, 1)
        self.assertIsNotNone(self.engine.api_last_called)
    
    def test_get_action_from_intent(self):
        """Test _get_action_from_intent method."""
        # Test turn_on_pump intent
        result = self.engine._get_action_from_intent('turn_on_pump', {'duration_minutes': 20})
        self.assertEqual(result['type'], 'activate_pump')
        self.assertEqual(result['parameters']['duration_minutes'], 20)
        
        # Test turn_on_pump intent without duration
        result = self.engine._get_action_from_intent('turn_on_pump', {})
        self.assertEqual(result['type'], 'activate_pump')
        self.assertEqual(result['parameters']['duration_minutes'], 10)  # Default
        
        # Test turn_off_pump intent
        result = self.engine._get_action_from_intent('turn_off_pump', {})
        self.assertEqual(result['type'], 'deactivate_pump')
        
        # Test query_soil_moisture intent
        result = self.engine._get_action_from_intent('query_soil_moisture', {})
        self.assertEqual(result['type'], 'get_sensor_data')
        self.assertEqual(result['parameters']['sensor_type'], 'soil_moisture')
        
        # Test get_status intent
        result = self.engine._get_action_from_intent('get_status', {})
        self.assertEqual(result['type'], 'get_system_status')
        
        # Test unknown intent
        result = self.engine._get_action_from_intent('unknown', {})
        self.assertEqual(result['type'], 'none')
    
    def test_generate_response(self):
        """Test _generate_response method."""
        # Test with local model
        result = self.engine._generate_response('query_soil_moisture', {}, 'local_model')
        self.assertEqual(result, "Tôi sẽ kiểm tra độ ẩm đất cho bạn.")
        
        # Test with API and unknown intent
        result = self.engine._generate_response('unknown', {}, 'local_model')
        self.assertEqual(result, "Tôi không hiểu yêu cầu của bạn. Bạn có thể nói rõ hơn được không?")
        
        # Test with turn_on_pump intent and duration
        result = self.engine._generate_response('turn_on_pump', {'duration_minutes': 15}, 'local_model')
        self.assertEqual(result, "Đã bật máy bơm trong 15 phút.")
        
        # Test with API available but local model source
        self.engine.openai_client = MagicMock()
        result = self.engine._generate_response('query_temperature', {}, 'openai')
        self.assertIsNone(result)  # Should return None to signal API response generation


if __name__ == '__main__':
    unittest.main()
