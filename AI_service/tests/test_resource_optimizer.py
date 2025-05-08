#!/usr/bin/env python
# tests/test_resource_optimizer.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch database và các module khác trước khi import
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.db_client'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['firebase_admin'] = MagicMock()

# Patch models
sys.modules['src.models'] = MagicMock()
sys.modules['src.models.irrigation_model'] = MagicMock()
sys.modules['src.models.base_model'] = MagicMock()

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]

# Import module cần test
from src.core.resource_optimizer import ResourceOptimizer

class TestResourceOptimizer(unittest.TestCase):
    """Test cases for ResourceOptimizer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config using các giá trị từ config_mock
        self.mock_config = MagicMock()
        self.mock_config.DEFAULT_IRRIGATION_DURATION = DEFAULT_IRRIGATION_DURATION
        self.mock_config.OPTIMAL_SOIL_MOISTURE = OPTIMAL_SOIL_MOISTURE
        self.mock_config.WATER_USAGE_PER_MINUTE = WATER_USAGE_PER_MINUTE  # liters
        
        # Create mock model registry
        self.mock_model_registry = MagicMock()
        
        # Create the optimizer
        self.optimizer = ResourceOptimizer(self.mock_config, self.mock_model_registry)
    
    def test_initialization(self):
        """Test that optimizer initializes correctly."""
        self.assertIsNotNone(self.optimizer)
        self.assertEqual(self.optimizer.config, self.mock_config)
        self.assertEqual(self.optimizer.model_registry, self.mock_model_registry)
    
    def test_optimize_schedule_dry_soil(self):
        """Test optimize_schedule with dry soil."""
        # Test sensor data with very dry soil
        sensor_data = {
            'soil_moisture': 20,  # Very dry
            'temperature': 30,
            'humidity': 40,
            'light_level': 800,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get optimized schedule
        result = self.optimizer.optimize_schedule(sensor_data, ["tomato"])
        
        # Verify result
        self.assertTrue(result['should_irrigate'])
        self.assertTrue(result['duration_minutes'] > 0)
        self.assertIsNotNone(result['irrigation_time'])
        self.assertIsNotNone(result['reason'])
        
        # Soil is very dry, so it should recommend irrigation soon
        self.assertTrue('Urgent' in result['reason'] or 'Low soil moisture' in result['reason'])
    
    def test_optimize_schedule_wet_soil(self):
        """Test optimize_schedule with wet soil."""
        # Test sensor data with wet soil
        sensor_data = {
            'soil_moisture': 75,  # Very wet
            'temperature': 25,
            'humidity': 60,
            'light_level': 600,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get optimized schedule
        result = self.optimizer.optimize_schedule(sensor_data, ["cucumber"])
        
        # Verify result
        self.assertFalse(result['should_irrigate'])
        self.assertEqual(result['duration_minutes'], 0)
        self.assertIsNotNone(result['reason'])
        
        # Soil is wet, so it should not recommend irrigation
        self.assertTrue('Adequate' in result['reason'] or 'soil moisture is sufficient' in result['reason'])
    
    def test_optimize_schedule_specific_zones(self):
        """Test optimize_schedule with specific zones."""
        # Test sensor data
        sensor_data = {
            'soil_moisture': 35,
            'temperature': 28,
            'humidity': 45,
            'light_level': 700,
            'timestamp': datetime.now().isoformat()
        }
        
        # Define zones
        zones = [
            {"id": 1, "name": "Zone 1", "plant_type": "tomato"},
            {"id": 2, "name": "Zone 2", "plant_type": "lettuce"}
        ]
        
        # Get optimized schedule
        result = self.optimizer.optimize_schedule(sensor_data, ["tomato", "lettuce"], zones)
        
        # Verify result
        self.assertTrue(result['should_irrigate'])
        self.assertIsNotNone(result['zones'])
        self.assertTrue(len(result['zones']) == 2)
        
        # Check zone-specific data
        for zone in result['zones']:
            self.assertIn('id', zone)
            self.assertIn('should_irrigate', zone)
            self.assertIn('duration_minutes', zone)
    
    def test_calculate_optimal_duration(self):
        """Test calculate_optimal_duration method."""
        # Test with very dry soil
        duration = self.optimizer._calculate_optimal_duration(20, "tomato")
        self.assertTrue(duration > 0)
        
        # Test with optimal moisture
        duration = self.optimizer._calculate_optimal_duration(50, "tomato")
        self.assertEqual(duration, 0)
        
        # Test with wet soil
        duration = self.optimizer._calculate_optimal_duration(80, "tomato")
        self.assertEqual(duration, 0)
        
        # Test with different plant types
        duration_tomato = self.optimizer._calculate_optimal_duration(30, "tomato")
        duration_lettuce = self.optimizer._calculate_optimal_duration(30, "lettuce")
        
        # Different plants might need different durations
        self.assertIsNotNone(duration_tomato)
        self.assertIsNotNone(duration_lettuce)
    
    def test_get_optimal_irrigation_time(self):
        """Test get_optimal_irrigation_time method."""
        # Test with morning current time
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 7, 1, 8, 0)  # 8 AM
            morning_time = self.optimizer._get_optimal_irrigation_time()
            
            # Optimal time should be close to current time or at a standard morning time
            self.assertIsInstance(morning_time, str)
        
        # Test with afternoon current time
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 7, 1, 14, 0)  # 2 PM
            afternoon_time = self.optimizer._get_optimal_irrigation_time()
            
            # Should avoid mid-day irrigation
            self.assertIsInstance(afternoon_time, str)
        
        # Test with evening current time
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 7, 1, 18, 0)  # 6 PM
            evening_time = self.optimizer._get_optimal_irrigation_time()
            
            # Optimal time should be close to current time or at a standard evening time
            self.assertIsInstance(evening_time, str)
    
    def test_calculate_water_savings(self):
        """Test calculate_water_savings method."""
        # Current usage with long duration
        current_usage = {
            "should_irrigate": True,
            "duration_minutes": 20,
            "zones": [
                {"should_irrigate": True, "duration_minutes": 20}
            ]
        }
        
        # Optimized usage with shorter duration
        optimized_usage = {
            "should_irrigate": True,
            "duration_minutes": 15,
            "zones": [
                {"should_irrigate": True, "duration_minutes": 15}
            ]
        }
        
        # Calculate savings
        savings = self.optimizer.calculate_water_savings(current_usage, optimized_usage)
        
        # Verify result
        self.assertIsNotNone(savings)
        self.assertTrue('liters_saved' in savings)
        self.assertTrue('percent_reduction' in savings)
        self.assertEqual(savings['liters_saved'], 10)  # 5 minutes saved * 2 liters/minute
        self.assertEqual(savings['percent_reduction'], 25)  # 5/20 = 25%
        
        # Test with no irrigation in optimized
        optimized_no_irrigation = {
            "should_irrigate": False,
            "duration_minutes": 0,
            "zones": [
                {"should_irrigate": False, "duration_minutes": 0}
            ]
        }
        
        savings = self.optimizer.calculate_water_savings(current_usage, optimized_no_irrigation)
        
        # Should save 100%
        self.assertEqual(savings['liters_saved'], 40)  # 20 minutes saved * 2 liters/minute
        self.assertEqual(savings['percent_reduction'], 100)
        
        # Test with no irrigation in current (should handle division by zero)
        current_no_irrigation = {
            "should_irrigate": False,
            "duration_minutes": 0,
            "zones": [
                {"should_irrigate": False, "duration_minutes": 0}
            ]
        }
        
        savings = self.optimizer.calculate_water_savings(current_no_irrigation, optimized_usage)
        
        # Should handle this case gracefully
        self.assertEqual(savings['liters_saved'], 0)
        self.assertEqual(savings['percent_reduction'], 0)


if __name__ == '__main__':
    unittest.main()
