from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
import uuid
from .db_client import Base

class IrrigationEvent(Base):
    """
    Model for storing irrigation events in the database.
    """
    __tablename__ = "irrigation_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    start_time = Column(DateTime, default=func.now(), index=True)
    duration_minutes = Column(Integer, nullable=False)  # Duration in seconds
    trigger_type = Column(String, nullable=False) # Trigger type (e.g., "manual", "automatic")
    soil_moisture_before = Column(Integer, nullable=True)  # Soil moisture before irrigation
    soil_moisture_after = Column(Integer, nullable=True)  # Soil moisture after irrigation
    recommendation_source = Column(String, nullable=True)  # Source of recommendation (e.g., "AI", "user")

    @classmethod
    def create(cls, db, duration_minutes, trigger_type, soil_moisture_before=None, soil_moisture_after=None, recommendation_source=None):
        """
        Create a new irrigation event entry.
        """
        irrigation_event = cls(
            duration_minutes=duration_minutes,
            trigger_type=trigger_type,
            soil_moisture_before=soil_moisture_before,
            soil_moisture_after=soil_moisture_after,
            recommendation_source=recommendation_source
        )
        db.add(irrigation_event)
        db.commit()
        db.refresh(irrigation_event)
        return irrigation_event
    
    @classmethod
    def update_moisture(cls, db, event_id, soil_moisture_after=None):
        """
        Update soil moisture values for an existing irrigation event.
        """
        event = db.query(cls).filter(cls.id == event_id).first()
        if event:
            if soil_moisture_after is not None:
                event.soil_moisture_after = soil_moisture_after
            db.commit()
            db.refresh(event)
        return event
    
    @classmethod
    def get_recent_events(cls, db, limit=10):
        """
        Get the most recent irrigation events.
        """
        return db.query(cls).order_by(cls.start_time.desc()).limit(limit).all()