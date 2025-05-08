from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from .db_client import Base

class SensorData(Base):
    """
    Model for storing sensor data in the database.
    """
    __tablename__ = "sensor_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=func.now(), index = True)
    soil_moisture = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    light_level = Column(Float, nullable=False)
    
    @classmethod
    def create(cls, db, soil_moisture, temperature, humidity, light_level):
        """
        Create a new sensor data entry.
        """
        sensor_data = cls(
            soil_moisture=soil_moisture,
            temperature=temperature,
            humidity=humidity,
            light_level=light_level
        )
        db.add(sensor_data)
        db.commit()
        db.refresh(sensor_data)
        return sensor_data
    
    @classmethod
    def get_latest(cls, db):
        """
        Get the latest sensor data entry.
        """
        return db.query(cls).order_by(cls.timestamp.desc()).first()
    
    @classmethod
    def get_data_in_range(cls, db, start_time, end_time):
        """
        Get sensor data entries within a specified time range.
        """
        return db.query(cls).filter(cls.timestamp.between(start_time, end_time)).order_by(cls.timestamp).all()
    