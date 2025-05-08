# src/models/training.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.database import get_db_session, Session
from src.database.sensor_data import SensorData
from src.database.irrigation_events import IrrigationEvent
from src.models.irrigation_model import IrrigationModel
from src.models.chatbot_model import ChatbotModel
from src.models.feature_engineering import FeatureEngineering

class ModelTraining:
    """
    Utility class for training and updating models.
    """
    
    @staticmethod
    def prepare_irrigation_training_data(days_back=30):
        """
        Prepare training data for the irrigation model from historical data.
        
        Args:
            days_back: Number of days of historical data to include
            
        Returns:
            DataFrame ready for training
        """
        session = get_db_session()
        try:
            # Get the date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Get sensor data
            sensor_data = session.query(SensorData).filter(
                SensorData.timestamp >= start_date,
                SensorData.timestamp <= end_date
            ).order_by(SensorData.timestamp).all()
            
            # Get irrigation events
            irrigation_events = session.query(IrrigationEvent).filter(
                IrrigationEvent.start_time >= start_date,
                IrrigationEvent.start_time <= end_date
            ).order_by(IrrigationEvent.start_time).all()
            
            # Create a map of timestamps to irrigation events
            irrigation_map = {}
            for event in irrigation_events:
                # Mark a 2-hour window after irrigation as "recently irrigated"
                event_time = event.start_time
                for i in range(120):  # 120 minutes
                    key_time = event_time + timedelta(minutes=i)
                    irrigation_map[key_time.strftime("%Y-%m-%d %H:%M")] = True
            
            # Prepare feature rows
            rows = []
            for data in sensor_data:
                # Basic features
                row = {
                    'soil_moisture': data.soil_moisture,
                    'temperature': data.temperature,
                    'humidity': data.humidity,
                    'light_level': data.light_level
                }
                
                # Add time features
                time_features = FeatureEngineering.get_time_features(data.timestamp)
                row.update(time_features)
                
                # Determine if this timestamp should have triggered irrigation
                # Logic: If soil moisture is below threshold AND no recent irrigation
                timestamp_key = data.timestamp.strftime("%Y-%m-%d %H:%M")
                recently_irrigated = irrigation_map.get(timestamp_key, False)
                
                # Create irrigation target
                # Simplified logic: irrigate if soil moisture below 30% and not recently irrigated
                should_irrigate = data.soil_moisture < 30 and not recently_irrigated
                row['irrigated'] = int(should_irrigate)
                
                rows.append(row)
            
            return pd.DataFrame(rows)
        finally:
            session.close()
    
    @staticmethod
    def prepare_default_chatbot_data():
        """
        Prepare default training data for the chatbot model.
        This creates a simple intent dataset in Vietnamese.
        
        Returns:
            Path to JSON file with intent data
        """
        intents = [
            {
                "intent": "query_soil_moisture",
                "patterns": [
                    "độ ẩm đất",
                    "đất có khô không",
                    "đất có ẩm không",
                    "cần tưới không"
                ],
                "examples": [
                    "Độ ẩm đất hiện tại là bao nhiêu?",
                    "Đất có khô không?",
                    "Kiểm tra độ ẩm đất giúp tôi",
                    "Đất có ẩm không?",
                    "Cần tưới cây không?",
                    "Độ ẩm đất thế nào rồi?"
                ]
            },
            {
                "intent": "query_temperature",
                "patterns": [
                    "nhiệt độ",
                    "nóng không"
                ],
                "examples": [
                    "Nhiệt độ hiện tại là bao nhiêu?",
                    "Trong nhà kính nóng không?",
                    "Kiểm tra nhiệt độ giúp tôi",
                    "Bây giờ nhiệt độ là bao nhiêu?"
                ]
            },
            {
                "intent": "query_humidity",
                "patterns": [
                    "độ ẩm không khí",
                    "độ ẩm trong không khí"
                ],
                "examples": [
                    "Độ ẩm không khí hiện tại là bao nhiêu?",
                    "Kiểm tra độ ẩm không khí giúp tôi",
                    "Độ ẩm trong không khí thế nào?"
                ]
            },
            {
                "intent": "query_light",
                "patterns": [
                    "ánh sáng",
                    "cường độ ánh sáng"
                ],
                "examples": [
                    "Ánh sáng hiện tại là bao nhiêu?",
                    "Cường độ ánh sáng thế nào?",
                    "Kiểm tra ánh sáng giúp tôi"
                ]
            },
            {
                "intent": "turn_on_pump",
                "patterns": [
                    "bật máy bơm",
                    "tưới nước",
                    "tưới cây"
                ],
                "examples": [
                    "Bật máy bơm đi",
                    "Tưới nước cho cây",
                    "Bật máy bơm trong 10 phút",
                    "Tưới nước trong 15 phút",
                    "Tưới cây ngay bây giờ"
                ]
            },
            {
                "intent": "turn_off_pump",
                "patterns": [
                    "tắt máy bơm",
                    "dừng tưới",
                    "ngừng tưới"
                ],
                "examples": [
                    "Tắt máy bơm đi",
                    "Dừng tưới nước",
                    "Ngừng tưới cây",
                    "Tắt máy bơm ngay bây giờ"
                ]
            },
            {
                "intent": "get_status",
                "patterns": [
                    "tình trạng",
                    "trạng thái",
                    "báo cáo"
                ],
                "examples": [
                    "Cho tôi biết tình trạng nhà kính",
                    "Báo cáo trạng thái hiện tại",
                    "Tình trạng các cảm biến thế nào?",
                    "Nhà kính đang hoạt động thế nào?"
                ]
            },
            {
                "intent": "schedule_irrigation",
                "patterns": [
                    "hẹn giờ tưới",
                    "lịch tưới",
                    "đặt lịch"
                ],
                "examples": [
                    "Hẹn giờ tưới lúc 6h sáng",
                    "Đặt lịch tưới hàng ngày",
                    "Tạo lịch tưới hàng tuần",
                    "Đặt lịch tưới 2 lần mỗi ngày"
                ]
            }
        ]
        
        # Ensure the data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Save intents to JSON file
        json_path = 'data/chatbot_intents.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(intents, f, ensure_ascii=False, indent=2)
        
        return json_path
    
    @staticmethod
    def train_irrigation_model():
        """
        Train the irrigation model with historical data.
        
        Returns:
            Trained IrrigationModel
        """
        # Prepare training data
        training_data = ModelTraining.prepare_irrigation_training_data()
        
        # Check if we have enough data
        if len(training_data) < 10:
            print("Warning: Not enough data to train a reliable model. Using default values.")
            # Create synthetic data for initial training
            np.random.seed(42)
            synthetic_data = []
            
            for _ in range(100):
                soil_moisture = np.random.uniform(10, 90)
                temperature = np.random.uniform(15, 40)
                humidity = np.random.uniform(30, 90)
                light_level = np.random.uniform(1000, 15000)
                
                # Simplified irrigation logic
                should_irrigate = 1 if soil_moisture < 30 else 0
                
                synthetic_data.append({
                    'soil_moisture': soil_moisture,
                    'temperature': temperature,
                    'humidity': humidity,
                    'light_level': light_level,
                    'hour': np.random.uniform(0, 1),
                    'day_of_week': np.random.uniform(0, 1),
                    'month': np.random.uniform(0, 1),
                    'is_daytime': np.random.choice([0, 1]),
                    'irrigated': should_irrigate
                })
            
            training_data = pd.DataFrame(synthetic_data)
        
        # Create and train model
        model = IrrigationModel(version="0.1.0")
        model.train(training_data)
        
        return model
    
    @staticmethod
    def train_chatbot_model():
        """
        Train the chatbot model with default or custom data.
        
        Returns:
            Trained ChatbotModel
        """
        # Prepare default chatbot data
        intent_data_path = ModelTraining.prepare_default_chatbot_data()
        
        # Create and train model
        model = ChatbotModel(version="0.1.0")
        model.train(intent_data_path)
        
        return model