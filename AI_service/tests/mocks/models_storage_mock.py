# tests/mocks/models_storage_mock.py
"""
Mock for models storage modules
"""
from unittest.mock import MagicMock
from datetime import datetime

class ModelMetadata:
    """Mock class for ModelMetadata"""
    
    def __init__(self, 
                 model_id=None, 
                 model_type=None, 
                 version=None, 
                 created_at=None,
                 metrics=None,
                 is_active=True):
        self.id = model_id or "mock-model-123"
        self.model_type = model_type or "irrigation"
        self.version = version or "v1.0.0"
        self.created_at = created_at or datetime.now()
        self.metrics = metrics or {"accuracy": 0.95, "f1_score": 0.92}
        self.is_active = is_active
    
    @staticmethod
    def create(session, **kwargs):
        """Create a new model metadata record"""
        return ModelMetadata(**kwargs)
    
    @staticmethod
    def get_active_model(session, model_type):
        """Get active model of specific type"""
        return ModelMetadata(model_type=model_type, is_active=True)
    
    @staticmethod
    def get_by_id(session, model_id):
        """Get model by ID"""
        return ModelMetadata(model_id=model_id)
    
    @staticmethod
    def list_models(session, model_type=None, limit=10):
        """List models of specific type"""
        return [ModelMetadata(model_type=model_type) for _ in range(3)]
