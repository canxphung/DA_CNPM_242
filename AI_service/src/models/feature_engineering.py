import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.database.db_client import get_db_session
from src.database.sensor_data import SensorData

class FeatureEngineering:
    """
    Utilities for processing and engineering features from sensor data.
    """
    @staticmethod
    def normalize_data(data):
        """
        Normalize sensor data to a 0-1 range.
        
        Args:
            data: Dictionary or DataFrame with sensor readings
            
        Returns:
            Dictionary with normalized values
        """
        # Define typical ranges for each sensor
        ranges = {
            'soil_moisture': (0, 100),
            'temperature': (0, 50),
            'humidity': (0, 100),
            'light_level': (0, 20000)
        }

        # Normalize each sensor reading
        normalized_data = {}

        # Check if data is a DataFrame or a dictionary
        if isinstance(data, pd.DataFrame):
            for feature, (min_val, max_val) in ranges.items():
                normalized_data[feature] = (data[feature] - min_val) / (max_val - min_val)
                # Clip values to ensure they are within the range [0, 1]
                normalized_data[feature] = max(0, min(1, normalized_data[feature]))

        return normalized_data
    
    @staticmethod
    def get_time_features(timestamp):
        """
        Extract time-based features from a timestamp.
        
        Args:
            timestamp: Datetime object
        """
        return {
            'hour': timestamp.hour / 24.0,  # Normalize hour to [0, 1]
            'day_of_week': timestamp.weekday() / 6.0,  # Normalize day of week to [0, 1]
            'month': timestamp.month / 12.0,  # Normalize month to [0, 1]
            'is_daytime': 1.0 if 6 <= timestamp.hour < 18 else 0.0,  # Daytime or nighttime
        }
        
    @staticmethod
    def get_historical_features(current_timestamp, hours_back=24, interval_hours=3):
        """
        Get historical features for the last 'hours_back' hours with 'interval_hours' intervals.
        
        Args:
            current_timestamp: Current datetime object
            hours_back: Number of hours to look back
            interval_hours: Interval in hours for historical data
        """
        features = {}
        with get_db_session() as session:
            for i in range(interval_hours, hours_back + 1, interval_hours):
                past_timestamp = current_timestamp - timedelta(hours=i)
                # Query the database for sensor data at the past timestamp
                feature = {}
                data = session.query(SensorData).filter(SensorData.timestamp <= past_timestamp).order_by(SensorData.timestamp.desc()).first()
                if data:

                    h_prefix = f"h{i}_"
                    features[f"{h_prefix}soil_moisture"] = data.soil_moisture
                    features[f"{h_prefix}temperature"] = data.temperature
                    features[f"{h_prefix}humidity"] = data.humidity
                    features[f"{h_prefix}light_level"] = data.light_level
                else:
                    # If no data is found, use NaN or some default value
                    h_prefix = f"h{i}_"
                    features[f"{h_prefix}soil_moisture"] = None
                    features[f"{h_prefix}temperature"] = None
                    features[f"{h_prefix}humidity"] = None
                    features[f"{h_prefix}light_level"] = None
            return features

    @staticmethod
    def prepare_model_input(current_data, include_historical=True, include_time=True):
        """
        Prepare the input data for the model.
        
        Args:
            current_data: Current sensor readings as dict or SensorData object
            include_historical: Whether to include historical data
            include_time: Whether to include time-based features
            
        Returns:
            Dictionary with prepared features
        """

        features = {}
        # Extract current sensor data
        if isinstance(current_data, SensorData):
            # If it's a SensorData object
            features.update({
                'soil_moisture': current_data.soil_moisture,
                'temperature': current_data.temperature,
                'humidity': current_data.humidity,
                'light_level': current_data.light_level,
                'timestamp': current_data.timestamp
            })
            timestamp = current_data.timestamp
        else:
            # If it's a dictionary
            features.update({
                'soil_moisture': current_data.get('soil_moisture'),
                'temperature': current_data.get('temperature'),
                'humidity': current_data.get('humidity'),
                'light_level': current_data.get('light_level'),
            })
            timestamp = current_data.get('timestamp', datetime.now())

        # Add historical features
        if include_historical:
            historical_features = FeatureEngineering.get_historical_features(timestamp)
            features.update(historical_features)

        # Normalize current features
        norm_current = FeatureEngineering.normalize_data({
            'soil_moisture': features['soil_moisture'],
            'temperature': features['temperature'],
            'humidity': features['humidity'],
            'light_level': features['light_level']
        })

        # Update features with normalized values
        for k, v in norm_current.items():
            features[f"{k}"] = v
        
        return features
    
    @staticmethod
    def handle_missing_value(feature_dict):
        """
        Handle missing values in the feature dictionary.
        
        Args:
            feature_dict: Dictionary with features
        returns:
            Dictionary with missing values handled
        """
        result = {}
        # For each feature, replace None with the mean of the feature
        for key, value in feature_dict.items():
            if value is None:
                # For historical features, use the current value
                if key.startswith("h") and '_' in key:
                    # Extract the sensor type
                    sensor_type = key.split('_',1)[1]
                    # Use the current value for that sensor type
                    if sensor_type in feature_dict and feature_dict[sensor_type] is not None:
                        result[key] = feature_dict[sensor_type]
                    else:
                        # Default value if no current value is available
                        defaults = {
                            'soil_moisture': 50.0,
                            'temperature': 25.0,
                            'humidity': 60.0,
                            'light_level': 5000
                        }
                        result[key] = defaults.get(sensor_type, 0.0)   

                else:
                    # For non-historical features, use the mean of the feature
                    defaults = {
                        'soil_moisture': 50.0,
                        'temperature': 25.0,
                        'humidity': 60.0,
                        'light_level': 5000,
                        'hour': 0.5,
                        'day_of_week': 0.5,
                        'month': 0.5,
                        'is_daytime': 1.0
                    }
                    result[key] = defaults.get(key, 0.0)
            else:
                result[key] = value
        return result
    