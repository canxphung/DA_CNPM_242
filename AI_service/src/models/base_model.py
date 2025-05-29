import os 
import sys    
import pickle
import json
import numpy as np
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.config import MODEL_STORAGE_PATH
from src.database import get_db_session
from src.database.models_storage import ModelMetadata

class BaseModel:
    """
    Base class for all local models in the system.
    Provides methods for loading, saving, and evaluating models.
    """
    def __init__(self, model_type, version="0.1.0"):
        """
        Initialize the BaseModel with model type and version.
        
        Args:
            model_type (str): Type of the model.
            version (str): Version of the model.
        """
        self.model_type = model_type
        self.version = version
        self.model = None
        self.model_path = None
        self.feature_columns = []

    def save_model(self, accuracy = None, extra_metadata=None):
        """
        Save the model tho disk and register in the database.
        Atgs:
            acuracy: Optional accuracy metric for the model.
            extra_metadata: Optional dictionary for additional metadata.
        Returns
            Path to the saved model.
        """
        if self.model is None:
            raise ValueError("Model is not trained yet. Cannot save.")
        # Create models filename using model type and version
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.model_type}_{self.version}_{timestamp}.pkl"

        # Ensure the directory exists
        os.makedirs(MODEL_STORAGE_PATH, exist_ok=True)
        filepath = os.path.join(MODEL_STORAGE_PATH, filename)

        # Create matadata file for feature columns and other info
        metadata = {
            "model_type": self.model_type,
            "version": self.version,
            "feature_columns": self.feature_columns,
            "create_at": datetime.now().isoformat(),
            "accuracy": accuracy,
        }

        if extra_metadata:
            metadata.update(extra_metadata)
        
        metadata_path = os.path.join(MODEL_STORAGE_PATH, f"{self.model_type}_{self.version}_{timestamp}.json")

        # Save the model and metadata
        with open(filepath, 'wb') as file:
            pickle.dump(self.model, file)

        with open(metadata_path, 'w') as file:
            json.dump(metadata, indent=2)

        # Register the model in the database
        with get_db_session() as session:
            ModelMetadata.create(
                db=session,
                type=self.model_type,
                version=self.version,
                file_path=filepath,
                accuracy=accuracy
            )

        # Update the model path
        self.model_path = filepath
        return filepath

    def load_model(self, model_path=None):
        """
        Load the model from the file system.
        
        Args:
            model_path (str): Optional path to specific model file.

        Returns:
            Self with loaded model.
        """
        if model_path:
            # Load from specific path
            with open(model_path, 'rb') as file:
                self.model = pickle.load(file)
            self.model_path = model_path

            # Try to load metadata file if it exists
            metadata_path = model_path.replace(".pkl", ".json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as file:
                    metadata = json.load(file)
                    if "feature_columns" in metadata:
                        self.feature_columns = metadata["feature_columns"]
        else:
            # Get active model from the database
            with get_db_session() as session:
                model_metadata = ModelMetadata.get_active_model(
                    session,
                    self.model_type
                )
                if model_metadata:
                    self.model_path = model_metadata.file_path
                    with open(self.model_path, 'rb') as file:
                        self.model = pickle.load(file)

                    self.model_path = model_metadata.file_path
                    self.version = model_metadata.version

                    # Load metadata
                    metadata_path = self.model_path.replace(".pkl", ".json")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as file:
                            metadata = json.load(file)
                            if "feature_columns" in metadata:
                                self.feature_columns = metadata["feature_columns"]
                else:
                    raise ValueError(f"No active model found for type {self.model_type}")
        return self
    def preprocess_input(self, data):
        """
        Preprocess input data before prediction.
        To be implemented by subclasses.
        
        Args:
            data: Input data for prediction
            
        Returns:
            Preprocessed data ready for model input
        """
        raise NotImplementedError("Subclasses must implement preprocess_input method")
    
    def predict(self, data):
        """
        Make a prediction using the model.
        To be implemented by subclasses.
        
        Args:
            data: Input data for prediction
            
        Returns:
            Model prediction
        """
        raise NotImplementedError("Subclasses must implement predict method")
    
    def train(self, data):
        """
        Train the model.
        To be implemented by subclasses.
        
        Args:
            data: Training data
            
        Returns:
            Trained model
        """
        raise NotImplementedError("Subclasses must implement train method")
    
    def evaluate(self, test_data):
        """
        Evaluate model performance.
        To be implemented by subclasses.
        
        Args:
            test_data: Test data
            
        Returns:
            Evaluation metrics
        """
        raise NotImplementedError("Subclasses must implement evaluate method")
    


