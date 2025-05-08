# src/core/model_registry.py
import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.database import get_db_session
from src.database.model_storage import ModelMetadata
from src.models.irrigation_model import IrrigationModel
from src.models.chatbot_model import ChatbotModel
from src.models.training import ModelTraining

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('model_registry')

class ModelRegistry:
    """
    Registry for managing model versions, training, and loading.
    """
    
    def __init__(self):
        """Initialize the model registry."""
        self.models = {}
        
    def get_model(self, model_type, version=None, reload=False):
        """
        Get a model instance of the specified type and version.
        
        Args:
            model_type: Type of model ('irrigation', 'chatbot')
            version: Specific version to load, or None for active version
            reload: Whether to reload the model from storage
            
        Returns:
            Model instance
        """
        # Check if we already have this model loaded
        model_key = f"{model_type}_{version}" if version else model_type
        
        if model_key in self.models and not reload:
            logger.info(f"Returning cached model: {model_key}")
            return self.models[model_key]
        
        # Load the model
        if model_type == 'irrigation':
            model = IrrigationModel(version=version if version else "0.1.0")
        elif model_type == 'chatbot':
            model = ChatbotModel(version=version if version else "0.1.0")
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        try:
            model.load()
            self.models[model_key] = model
            logger.info(f"Loaded model: {model_key}")
            return model
        except Exception as e:
            logger.error(f"Error loading model {model_key}: {str(e)}")
            raise
    
    def train_new_model(self, model_type, custom_training_data=None):
        """
        Train a new model version.
        
        Args:
            model_type: Type of model to train
            custom_training_data: Optional custom training data
            
        Returns:
            Newly trained model
        """
        logger.info(f"Training new {model_type} model")
        
        if model_type == 'irrigation':
            if custom_training_data:
                model = IrrigationModel(version=self._generate_version(model_type))
                model.train(custom_training_data)
            else:
                model = ModelTraining.train_irrigation_model()
        elif model_type == 'chatbot':
            if custom_training_data:
                model = ChatbotModel(version=self._generate_version(model_type))
                model.train(custom_training_data)
            else:
                model = ModelTraining.train_chatbot_model()
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Cache the model
        model_key = f"{model_type}_{model.version}"
        self.models[model_key] = model
        self.models[model_type] = model  # Update default model
        
        logger.info(f"Successfully trained new {model_type} model version {model.version}")
        
        return model
    
    def list_available_models(self):
        """
        List all available model versions in the database.
        
        Returns:
            Dictionary of model types and their versions
        """
        session = get_db_session()
        try:
            models = session.query(ModelMetadata).all()
            
            # Group by model type
            result = {}
            for model in models:
                if model.type not in result:
                    result[model.type] = []
                
                result[model.type].append({
                    'version': model.version,
                    'created_at': model.created_at.isoformat(),
                    'accuracy': model.accuracy,
                    'is_active': model.is_active,
                    'file_path': model.file_path
                })
            
            return result
        finally:
            session.close()
    
    def set_active_model(self, model_type, version):
        """
        Set the active model version for a given type.
        
        Args:
            model_type: Type of model
            version: Version to set as active
            
        Returns:
            True if successful, False otherwise
        """
        session = get_db_session()
        try:
            # Find the model with the specified version
            model = session.query(ModelMetadata).filter(
                ModelMetadata.type == model_type,
                ModelMetadata.version == version
            ).first()
            
            if not model:
                logger.error(f"Model not found: {model_type} version {version}")
                return False
            
            # Set all models of this type to inactive
            session.query(ModelMetadata).filter(
                ModelMetadata.type == model_type
            ).update({ModelMetadata.is_active: False})
            
            # Set the specified model to active
            model.is_active = True
            session.commit()
            
            # Reload the model
            self.get_model(model_type, reload=True)
            
            logger.info(f"Set {model_type} model version {version} as active")
            return True
        except Exception as e:
            logger.error(f"Error setting active model: {str(e)}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def _generate_version(self, model_type):
        """
        Generate a new version number based on existing versions.
        
        Args:
            model_type: Type of model
            
        Returns:
            New version string (semantic versioning)
        """
        session = get_db_session()
        try:
            # Get the latest version of this model type
            latest = session.query(ModelMetadata).filter(
                ModelMetadata.type == model_type
            ).order_by(ModelMetadata.created_at.desc()).first()
            
            if not latest:
                return "0.1.0"  # Initial version
            
            # Parse version components
            try:
                major, minor, patch = map(int, latest.version.split('.'))
                # Increment patch version
                patch += 1
                return f"{major}.{minor}.{patch}"
            except ValueError:
                # If version parsing fails, use timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M")
                return f"0.1.0-{timestamp}"
        finally:
            session.close()