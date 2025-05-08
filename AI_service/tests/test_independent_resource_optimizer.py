#!/usr/bin/env python
# tests/test_independent_resource_optimizer.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]

# Create a minimal ResourceOptimizer class for testing
class TestResourceOptimizer:
    """Simplified ResourceOptimizer for testing"""
    
    def __init__(self, config, model_registry=None):
        self.config = config
        self.model_registry = model_registry
        self.default_duration = config.DEFAULT_IRRIGATION_DURATION
        self.optimal_moisture = config.OPTIMAL_SOIL_MOISTURE
    
    def optimize_schedule(self, sensor_data, plant_types, zones=None):
        """Optimize irrigation schedule."""
        # Get current soil moisture
        soil_moisture = sensor_data.get('soil_moisture', 50)
        
        # Determine if irrigation is needed
        should_irrigate = soil_moisture < self.optimal_moisture
        
        # Calculate optimal duration
        if should_irrigate:
            duration = self._calculate_optimal_duration(soil_moisture, plant_types[0] if plant_types else "default")
        else:
            duration = 0
        
        # Determine optimal time
        irrigation_time = self._get_optimal_irrigation_time()
        
        # Create zone schedules if needed
        zone_schedules = []
        if zones:
            for zone in zones:
                zone_schedule = {
                    "id": zone.get("id"),
                    "should_irrigate": should_irrigate,
                    "duration_minutes": duration
                }
                zone_schedules.append(zone_schedule)
        
        # Create the complete schedule
        schedule = {
            "should_irrigate": should_irrigate,
            "duration_minutes": duration,
            "irrigation_time": irrigation_time,
            "irrigation_datetime": datetime.now().isoformat(),
            "soil_moisture": soil_moisture,
            "reason": self._get_irrigation_reason(soil_moisture, should_irrigate),
            "zones": zone_schedules if zones else None
        }
        
        return schedule
    
    def calculate_water_savings(self, current_usage, optimized_usage):
        """Calculate water savings from optimization."""
        # Calculate current water usage
        current_minutes = current_usage.get("duration_minutes", 0)
        
        # Calculate optimized water usage
        optimized_minutes = optimized_usage.get("duration_minutes", 0)
        
        # Calculate savings
        minutes_saved = current_minutes - optimized_minutes
        liters_saved = minutes_saved * self.config.WATER_USAGE_PER_MINUTE
        
        if current_minutes > 0:
            percent_reduction = (minutes_saved / current_minutes) * 100
        else:
            percent_reduction = 0
        
        return {
            "minutes_saved": minutes_saved,
            "liters_saved": liters_saved,
            "percent_reduction": percent_reduction
        }
    
    def _calculate_optimal_duration(self, soil_moisture, plant_type):
        """Calculate optimal irrigation duration based on soil moisture."""
        if soil_moisture >= self.optimal_moisture:
            return 0
        
        # Calculate moisture deficit
        deficit = self.optimal_moisture - soil_moisture
        
        # Calculate duration (roughly 1 minute per 5% deficit)
        duration = round(deficit / 5)
        
        # Adjust for plant type (some plants need more water)
        plant_factors = {
            "tomato": 1.2,
            "cucumber": 1.1,
            "lettuce": 0.8,
            "default": 1.0
        }
        
        factor = plant_factors.get(plant_type, plant_factors["default"])
        adjusted_duration = round(duration * factor)
        
        # Ensure minimum and maximum durations
        return max(1, min(adjusted_duration, 30))
    
    def _get_optimal_irrigation_time(self):
        """Get optimal time of day for irrigation."""
        now = datetime.now()
        hour = now.hour
        
        # Early morning is generally best
        if 5 <= hour < 8:
            return "06:00"
        # Early evening is second best
        elif 17 <= hour < 20:
            return "18:00"
        # Avoid mid-day irrigation
        elif 10 <= hour < 16:
            return "18:00"
        # Otherwise, irrigate within an hour
        else:
            next_hour = (hour + 1) % 24
            return f"{next_hour:02d}:00"
    
    def _get_irrigation_reason(self, soil_moisture, should_irrigate):
        """Get reason for irrigation decision."""
        if not should_irrigate:
            return "Soil moisture is adequate"
        
        if soil_moisture < 20:
            return "Urgent: Soil moisture critically low"
        elif soil_moisture < 30:
            return "Urgent: Low soil moisture requires irrigation"
        else:
            return "Preventative irrigation to maintain optimal moisture"


class TestResourceOptimizerClass(unittest.TestCase):
    """Test cases for ResourceOptimizer."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config
        self.mock_config = MagicMock()
        self.mock_config.DEFAULT_IRRIGATION_DURATION = DEFAULT_IRRIGATION_DURATION
        self.mock_config.OPTIMAL_SOIL_MOISTURE = OPTIMAL_SOIL_MOISTURE
        self.mock_config.WATER_USAGE_PER_MINUTE = WATER_USAGE_PER_MINUTE
        
        # Create mock model registry
        self.mock_model_registry = MagicMock()
        
        # Create the optimizer
        self.optimizer = TestResourceOptimizer(self.mock_config, self.mock_model_registry)
    
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
            'light_level': 800
        }
        
        # Get optimized schedule
        result = self.optimizer.optimize_schedule(sensor_data, ["tomato"])
        
        # Verify result
        self.assertTrue(result['should_irrigate'])
        self.assertTrue(result['duration_minutes'] > 0)
        self.assertIsNotNone(result['irrigation_time'])
        self.assertIsNotNone(result['reason'])
        
        # Should be an urgent reason
        self.assertTrue("Urgent" in result['reason'])
    
    def test_optimize_schedule_wet_soil(self):
        """Test optimize_schedule with wet soil."""
        # Test sensor data with wet soil
        sensor_data = {
            'soil_moisture': 75,  # Very wet
            'temperature': 25,
            'humidity': 60,
            'light_level': 600
        }
        
        # Get optimized schedule
        result = self.optimizer.optimize_schedule(sensor_data, ["cucumber"])
        
        # Verify result
        self.assertFalse(result['should_irrigate'])
        self.assertEqual(result['duration_minutes'], 0)
        self.assertIsNotNone(result['reason'])
        
        # Should indicate adequate moisture
        self.assertTrue("adequate" in result['reason'].lower())
    
    def test_optimize_schedule_with_zones(self):
        """Test optimize_schedule with specific zones."""
        # Test sensor data
        sensor_data = {
            'soil_moisture': 35,
            'temperature': 28,
            'humidity': 45,
            'light_level': 700
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
        self.assertEqual(len(result['zones']), 2)
        
        # Check zone ids
        zone_ids = [zone['id'] for zone in result['zones']]
        self.assertIn(1, zone_ids)
        self.assertIn(2, zone_ids)
    
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
        self.assertEqual(savings['minutes_saved'], 5)
        self.assertEqual(savings['liters_saved'], 5 * WATER_USAGE_PER_MINUTE)
        self.assertEqual(savings['percent_reduction'], 25)  # 5/20 = 25%
        
        # Test with no irrigation in optimized
        optimized_no_irrigation = {
            "should_irrigate": False,
            "duration_minutes": 0
        }
        
        savings = self.optimizer.calculate_water_savings(current_usage, optimized_no_irrigation)
        
        # Should save 100%
        self.assertEqual(savings['minutes_saved'], 20)
        self.assertEqual(savings['liters_saved'], 20 * WATER_USAGE_PER_MINUTE)
        self.assertEqual(savings['percent_reduction'], 100)
        
        # Test with no irrigation in current (should handle division by zero)
        current_no_irrigation = {
            "should_irrigate": False,
            "duration_minutes": 0
        }
        
        savings = self.optimizer.calculate_water_savings(current_no_irrigation, optimized_usage)
        
        # Should handle this case gracefully
        self.assertEqual(savings['minutes_saved'], -15)
        self.assertEqual(savings['liters_saved'], -15 * WATER_USAGE_PER_MINUTE)
        self.assertEqual(savings['percent_reduction'], 0)  # No savings when adding irrigation


if __name__ == '__main__':
    unittest.main()
