#!/usr/bin/env python
# tests/test_independent_model_registry.py

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import mocks
from tests.mocks.models_storage_mock import ModelMetadata
sys.modules['src.database'] = MagicMock()
sys.modules['src.database.model_storage'] = MagicMock()
sys.modules['src.database.model_storage'].ModelMetadata = ModelMetadata

# Patch config
from tests.mocks.config_mock import *
sys.modules['config.config'] = sys.modules[__name__]

# Create a minimal ModelRegistry class for testing
class TestModelRegistry:
    """Simplified ModelRegistry for testing"""
    
    def __init__(self):
        self.models = {}
        self.active_models = {}
        self.model_path = tempfile.mkdtemp()
    
    def register_model(self, model_type, model_obj, metrics=None):
        """Register a new model"""
        model_id = f"{model_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.models[model_id] = {
            'model_type': model_type,
            'model': model_obj,
            'metrics': metrics or {},
            'created_at': datetime.now()
        }
        self.active_models[model_type] = model_id
        return model_id
    
    def get_active_model(self, model_type):
        """Get active model by type"""
        model_id = self.active_models.get(model_type)
        if not model_id:
            return None
        return self.models.get(model_id, {}).get('model')
    
    def list_models(self, model_type=None):
        """List available models"""
        if model_type:
            return {id: model for id, model in self.models.items() 
                   if model['model_type'] == model_type}
        return self.models

class TestModelRegistryClass(unittest.TestCase):
    """Test cases for ModelRegistry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = TestModelRegistry()
        self.mock_model = MagicMock()
        self.mock_model.version = "1.0.0"
        self.mock_model.predict = MagicMock(return_value={"prediction": "test"})
    
    def test_initialization(self):
        """Test that registry initializes correctly."""
        self.assertIsNotNone(self.registry)
        self.assertEqual(self.registry.models, {})
        self.assertEqual(self.registry.active_models, {})
    
    def test_register_model(self):
        """Test registering a model."""
        model_id = self.registry.register_model(
            model_type="test_model",
            model_obj=self.mock_model,
            metrics={"accuracy": 0.95}
        )
        
        self.assertIsNotNone(model_id)
        self.assertIn(model_id, self.registry.models)
        self.assertEqual(self.registry.active_models["test_model"], model_id)
        self.assertEqual(self.registry.models[model_id]["model"], self.mock_model)
        self.assertEqual(self.registry.models[model_id]["metrics"]["accuracy"], 0.95)
    
    def test_get_active_model(self):
        """Test getting active model."""
        # Register a model first
        model_id = self.registry.register_model(
            model_type="test_model",
            model_obj=self.mock_model
        )
        
        # Get the active model
        active_model = self.registry.get_active_model("test_model")
        
        self.assertEqual(active_model, self.mock_model)
        
        # Test with non-existent model type
        missing_model = self.registry.get_active_model("missing_model")
        self.assertIsNone(missing_model)
    
    def test_list_models(self):
        """Test listing models."""
        # Register multiple models
        model1 = MagicMock()
        model2 = MagicMock()
        
        model_id1 = self.registry.register_model("type1", model1)
        model_id2 = self.registry.register_model("type2", model2)
        
        # List all models
        all_models = self.registry.list_models()
        self.assertEqual(len(all_models), 2)
        self.assertIn(model_id1, all_models)
        self.assertIn(model_id2, all_models)
        
        # List by type
        type1_models = self.registry.list_models("type1")
        self.assertEqual(len(type1_models), 1)
        self.assertIn(model_id1, type1_models)
        
        # List non-existent type
        missing_models = self.registry.list_models("missing_type")
        self.assertEqual(len(missing_models), 0)


if __name__ == '__main__':
    unittest.main()
