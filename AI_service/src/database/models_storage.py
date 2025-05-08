from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
import uuid
from .db_client import Base

class ModelMetadata(Base):
    """
    Model for storing metadata about machine learning models in the database.
    """
    __tablename__ = "model_metadata"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False, index = True)  # Type of model (e.g., "classification", "regression")
    version = Column(String(50), nullable=False)
    file_path = Column(String, nullable=False)  # Path to the model file
    created_by = Column(DateTime, default=func.now())  # User who created the model
    accuracy = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
 
    @classmethod
    def create(cls, db, type, version, file_path, accuracy):
        """
        Create a new model metadata entry.
        """
        if type:
            db.query(cls).filter(
                cls.type == type,
                cls.is_active == True
            ).update({cls.is_active: False})

        model_metadata = cls(
            type=type,
            version=version,
            file_path=file_path,
            accuracy=accuracy,
            is_active=True
        )
        db.add(model_metadata)
        db.commit()
        db.refresh(model_metadata)
        return model_metadata
    
    @classmethod
    def get_active_model(cls, db, type):
        """
        Get the active model metadata entry for a specific type.
        """
        return db.query(cls).filter(
            cls.type == type,
            cls.is_active == True
        ).first()