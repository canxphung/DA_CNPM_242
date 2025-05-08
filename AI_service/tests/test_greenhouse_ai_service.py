#!/usr/bin/env python
# tests/test_greenhouse_ai_service.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch database và redis trước khi import các module khác
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.db_client'] = MagicMock()
sys.modules['src.database.sensor_data'] = MagicMock()
sys.modules['src.database.irrigation_events'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()

# Import mocks
from tests.mocks.db_mock import get_db_session, SensorData, IrrigationEvent

# Patch lại các module database
sys.modules['src.database'].get_db_session = get_db_session
sys.modules['src.database.sensor_data'].SensorData = SensorData
sys.modules['src.database.irrigation_events'].IrrigationEvent = IrrigationEvent

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]

# Import module cần test
from src.core.greenhouse_ai_service import GreenhouseAIService

class TestGreenhouseAIService(unittest.TestCase):
    """Test cases for GreenhouseAIService."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config using các giá trị từ config_mock
        self.mock_config = MagicMock()
        self.mock_config.CORE_OPS_API_URL = CORE_OPS_API_URL
        self.mock_config.CORE_OPS_API_KEY = CORE_OPS_API_KEY
        self.mock_config.DEFAULT_IRRIGATION_DURATION = DEFAULT_IRRIGATION_DURATION
        
        # Create service with mocked dependencies
        with patch('src.core.greenhouse_ai_service.DecisionEngine'), \
             patch('src.core.greenhouse_ai_service.ModelRegistry'), \
             patch('src.core.greenhouse_ai_service.APICacheManager'), \
             patch('src.core.greenhouse_ai_service.ResourceOptimizer'), \
             patch('src.core.greenhouse_ai_service.OpenAIClient'), \
             patch('src.core.greenhouse_ai_service.CoreOperationsIntegration'):
            self.service = GreenhouseAIService(config=self.mock_config)
    
    def test_initialization(self):
        """Test that service initializes correctly."""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.decision_engine)
        self.assertIsNotNone(self.service.model_registry)
        self.assertIsNotNone(self.service.cache_manager)
        self.assertIsNotNone(self.service.resource_optimizer)
        self.assertIsNotNone(self.service.core_ops_integration)
        self.assertFalse(self.service.is_running)
        
    def test_start_stop(self):
        """Test start and stop methods."""
        # Test start
        self.service.start()
        self.assertTrue(self.service.is_running)
        
        # Test stop
        with patch.object(self.service.core_ops_integration, 'close', new_callable=AsyncMock) as mock_close:
            self.service.stop()
            self.assertFalse(self.service.is_running)
            # Cannot directly test async method call in stop() from a sync test
    
    @patch('src.core.greenhouse_ai_service.get_db_session')
    def test_get_current_sensor_data(self, mock_get_db_session):
        """Test _get_current_sensor_data method."""
        # Set up mock session and query response
        mock_session = MagicMock()
        mock_get_db_session.return_value = mock_session
        
        # Test with sensor data available
        mock_latest = MagicMock()
        mock_latest.soil_moisture = 45
        mock_latest.temperature = 25
        mock_latest.humidity = 60
        mock_latest.light_level = 800
        mock_latest.timestamp = datetime.now()
        
        with patch('src.core.greenhouse_ai_service.SensorData') as mock_sensor_data:
            mock_sensor_data.get_latest.return_value = mock_latest
            result = self.service._get_current_sensor_data()
            
            self.assertEqual(result['soil_moisture'], 45)
            self.assertEqual(result['temperature'], 25)
            self.assertEqual(result['humidity'], 60)
            self.assertEqual(result['light_level'], 800)
            self.assertIsNotNone(result['timestamp'])
        
        # Test with no sensor data available
        with patch('src.core.greenhouse_ai_service.SensorData') as mock_sensor_data:
            mock_sensor_data.get_latest.return_value = None
            result = self.service._get_current_sensor_data()
            
            self.assertIsNone(result['soil_moisture'])
            self.assertIsNone(result['temperature'])
            self.assertIsNone(result['humidity'])
            self.assertIsNone(result['light_level'])
            self.assertIsNone(result['timestamp'])
    
    async def async_test_process_sensor_data(self):
        """Test process_sensor_data method."""
        # Sample sensor data
        sensor_data = {
            'soil_moisture': 25,
            'temperature': 30,
            'humidity': 40,
            'light_level': 900
        }
        
        # Mock the DB session
        with patch('src.core.greenhouse_ai_service.get_db_session') as mock_get_db_session:
            mock_session = MagicMock()
            mock_get_db_session.return_value = mock_session
            
            # Mock decision engine to return need for irrigation
            self.service.decision_engine.get_irrigation_decision.return_value = {
                'should_irrigate': True,
                'confidence': 0.8,
                'duration_minutes': 10,
                'reason': 'Soil moisture low'
            }
            
            # Mock create_irrigation_recommendation
            mock_recommendation = {
                'id': '1234',
                'should_irrigate': True,
                'duration_minutes': 10
            }
            self.service.create_irrigation_recommendation = AsyncMock(return_value=mock_recommendation)
            
            # Call the method
            result = await self.service.process_sensor_data(sensor_data)
            
            # Verify the result
            self.assertTrue('decision' in result)
            self.assertTrue('actions_taken' in result)
            self.assertTrue('timestamp' in result)
            self.assertTrue(len(result['actions_taken']) > 0)
            
            # Verify create_irrigation_recommendation was called
            self.service.create_irrigation_recommendation.assert_called_once()
    
    async def async_test_process_user_message(self):
        """Test process_user_message method."""
        # Sample message
        message = "Tưới cây trong 15 phút"
        
        # Mock dependencies
        with patch.object(self.service, '_get_current_sensor_data') as mock_get_sensor_data:
            mock_get_sensor_data.return_value = {
                'soil_moisture': 30,
                'temperature': 25,
                'humidity': 60,
                'light_level': 800,
                'timestamp': datetime.now().isoformat()
            }
            
            # Mock decision engine
            self.service.decision_engine.process_user_message.return_value = {
                'intent': 'turn_on_pump',
                'entities': {'duration_minutes': 15},
                'response': None,
                'action': {'type': 'activate_pump', 'parameters': {'duration_minutes': 15}}
            }
            
            # Mock create_irrigation_recommendation
            self.service.create_irrigation_recommendation = AsyncMock()
            
            # Call the method
            result = await self.service.process_user_message(message)
            
            # Verify the result
            self.assertEqual(result['intent'], 'turn_on_pump')
            self.assertTrue('response' in result)
            self.assertTrue('actions_taken' in result)
            self.assertTrue(len(result['actions_taken']) > 0)
            
            # Verify create_irrigation_recommendation was called
            self.service.create_irrigation_recommendation.assert_called_once()
    
    async def async_test_create_irrigation_recommendation(self):
        """Test create_irrigation_recommendation method."""
        # Set up mocks
        self.service.core_ops_integration.fetch_sensor_data = AsyncMock(return_value=[])
        self.service.resource_optimizer.optimize_schedule.return_value = {
            'should_irrigate': True,
            'duration_minutes': 10,
            'zones': [{'id': 1, 'duration_minutes': 10}],
            'irrigation_time': '08:00',
            'irrigation_datetime': datetime.now().isoformat(),
            'soil_moisture': 25,
            'reason': 'Optimized for morning irrigation'
        }
        self.service.resource_optimizer.calculate_water_savings.return_value = {
            'liters_saved': 5,
            'percent_reduction': 20
        }
        self.service._save_recommendation_to_storage = AsyncMock()
        
        # Call the method
        result = await self.service.create_irrigation_recommendation(
            plant_types=["tomato", "cucumber"],
            priority="high"
        )
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertTrue('id' in result)
        self.assertTrue('should_irrigate' in result)
        self.assertTrue('duration_minutes' in result)
        self.assertTrue('zones' in result)
        self.assertTrue('water_savings' in result)
        self.assertEqual(result['status'], 'created')
        self.assertFalse(result['sent_to_core'])
        
        # Verify the methods were called
        self.service.resource_optimizer.optimize_schedule.assert_called_once()
        self.service._save_recommendation_to_storage.assert_called_once()

    @patch('asyncio.run')
    def test_async_methods(self, mock_run):
        """Run async test methods with asyncio."""
        # Setup mock return for asyncio.run
        mock_run.side_effect = lambda coro: asyncio.get_event_loop().run_until_complete(coro)
        
        # Run the async tests
        asyncio.run(self.async_test_process_sensor_data())
        asyncio.run(self.async_test_process_user_message())
        asyncio.run(self.async_test_create_irrigation_recommendation())


if __name__ == '__main__':
    unittest.main()
