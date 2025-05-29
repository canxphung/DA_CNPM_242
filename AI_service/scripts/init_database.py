# scripts/init_database.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.db_client import engine, Base
from src.database.sensor_data import SensorData
from src.database.irrigation_events import IrrigationEvent
from src.database.models_storage import ModelMetadata

def init_database():
    """Khởi tạo tất cả các bảng trong database"""
    print("Đang tạo các bảng trong database...")
    
    # Điều này sẽ tạo tất cả các bảng được định nghĩa bởi các models
    # kế thừa từ Base
    Base.metadata.create_all(bind=engine)
    
    print("✓ Đã tạo bảng sensor_data")
    print("✓ Đã tạo bảng irrigation_events") 
    print("✓ Đã tạo bảng model_metadata")
    print("\nDatabase đã sẵn sàng!")

if __name__ == "__main__":
    init_database()