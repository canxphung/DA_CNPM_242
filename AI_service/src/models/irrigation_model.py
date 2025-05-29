# src/models/irrigation_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.models.base_model import BaseModel
from src.models.feature_engineering import FeatureEngineering

class IrrigationModel(BaseModel):
    """
    Model for predicting irrigation needs based on sensor data.
    Uses Random Forest Classifier to decide whether irrigation is needed.
    """
    
    def __init__(self, version="0.1.0"):
        """Initialize the irrigation model."""
        super().__init__(model_type="irrigation", version=version)
        self.scaler = StandardScaler()
    
    def load_model(self, model_path=None):
        super().load_model(model_path)

        # Load scaler
        if self.model_path:
            scaler_path = self.model_path.replace(".pkl", "_scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as file:
                    self.scaler = pickle.load(file)
            else:
                raise FileNotFoundError(f"Scaler file not found: {scaler_path}")
        return self

    def save_model(self, accuracy=None, extra_metadata=None):
        model_path = super().save_model(accuracy, extra_metadata)
        
        # Save scaler
        scaler_path = model_path.replace(".pkl", "_scaler.pkl")
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)

        return model_path

    def preprocess_input(self, data):
        """
        Preprocess input data for irrigation prediction.
        
        Args:
            data: Dictionary with sensor data or SensorData object
            
        Returns:
            Preprocessed data as numpy array ready for prediction
        """
        # Prepare features with feature engineering
        features = FeatureEngineering.prepare_model_input(data)
        
        # Handle any missing values
        features = FeatureEngineering.handle_missing_values(features)
        
        # If we have feature_columns from a trained model, use only those
        if self.feature_columns:
            # Create a vector in the correct order
            X = np.array([features.get(col, 0.0) for col in self.feature_columns]).reshape(1, -1)
        else:
            # Otherwise use all features
            X = np.array(list(features.values())).reshape(1, -1)
        
        return X
    
    def predict(self, data):
        """
        Predict whether irrigation is needed.
        
        Args:
            data: Dictionary with sensor data or SensorData object
            
        Returns:
            Dictionary with prediction and confidence:
            {
                'should_irrigate': True/False,
                'confidence': float (0-1)
            }
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() or train() first.")
        
        # Preprocess the input data
        X = self.preprocess_input(data)
        
        # Make prediction
        # For Random Forest, predict_proba returns probabilities for each class
        probabilities = self.model.predict_proba(X)[0]
        prediction = self.model.predict(X)[0]
        
        # Get confidence (probability of the predicted class)
        confidence = probabilities[1] if prediction == 1 else probabilities[0]
        
        return {
            'should_irrigate': bool(prediction),
            'confidence': float(confidence)
        }
    
    def train(self, data):
        """
        Train the irrigation prediction model.
        
        Args:
            data: DataFrame with sensor data and irrigation events
                Must contain sensor readings and 'irrigated' target column
            
        Returns:
            Self with trained model
        """
        # Ensure data has the right columns
        required_cols = ['soil_moisture', 'temperature', 'humidity', 'light_level', 'irrigated']
        if not all(col in data.columns for col in required_cols):
            missing = [col for col in required_cols if col not in data.columns]
            raise ValueError(f"Training data missing required columns: {missing}")
        
        # Split features and target
        X = data.drop('irrigated', axis=1)
        y = data['irrigated']
        
        # Save feature column names for future predictions
        self.feature_columns = list(X.columns)
        
        # Split training and validation sets
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        self.scaler.fit(X_train)
        X_train_scaled = self.scaler.transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train Random Forest model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=42
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate on validation set
        y_pred = self.model.predict(X_val_scaled)
        accuracy = accuracy_score(y_val, y_pred)
        
        # Save model with accuracy metric
        self.save(accuracy=accuracy, extra_metadata={
            'precision': precision_score(y_val, y_pred),
            'recall': recall_score(y_val, y_pred),
            'f1': f1_score(y_val, y_pred)
        })
        
        return self
    
    def evaluate(self, test_data):
        """
        Evaluate model performance on test data.
        
        Args:
            test_data: DataFrame with sensor data and 'irrigated' target column
            
        Returns:
            Dictionary with performance metrics
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() or train() first.")
        
        # Split features and target
        X_test = test_data.drop('irrigated', axis=1)
        y_test = test_data['irrigated']
        
        # Scale features
        X_test_scaled = self.scaler.transform(X_test)
        
        # Make predictions
        y_pred = self.model.predict(X_test_scaled)
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred)
        }
        
        return metrics
    
    def get_feature_importance(self):
        """
        Get feature importance from the trained model.
        
        Returns:
            DataFrame with feature names and importance scores
        """
        if self.model is None or not hasattr(self.model, 'feature_importances_'):
            raise ValueError("Model not trained or doesn't support feature importance.")
        
        importances = self.model.feature_importances_
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importances
        })
        
        return feature_importance.sort_values('importance', ascending=False)