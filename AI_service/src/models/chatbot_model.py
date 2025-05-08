# src/models/chatbot_model.py
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import re
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.models.base_model import BaseModel

class ChatbotModel(BaseModel):
    """
    Simple chatbot model for Vietnamese text classification.
    Uses TF-IDF and Multinomial Naive Bayes to classify user intents.
    """
    
    def __init__(self, version="0.1.0"):
        """Initialize the chatbot model."""
        super().__init__(model_type="chatbot", version=version)
        self.intents = []
        self.intent_patterns = {}
        
    def preprocess_input(self, text):
        """
        Preprocess input text for intent classification.
        
        Args:
            text: Input text from user
            
        Returns:
            Preprocessed text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = re.sub(r'[.,!?;:()\[\]{}]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_entities(self, text):
        """
        Extract entities from text (numbers, time periods, etc.)
        
        Args:
            text: Input text from user
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Extract numbers (for duration, etc.)
        number_match = re.search(r'(\d+)', text)
        if number_match:
            entities['number'] = int(number_match.group(1))
        
        # Extract time units (minutes, hours)
        if 'phút' in text.lower():
            entities['time_unit'] = 'minutes'
        elif 'giờ' in text.lower() or 'tiếng' in text.lower():
            entities['time_unit'] = 'hours'
        
        # If both number and time_unit are present, create a duration
        if 'number' in entities and 'time_unit' in entities:
            if entities['time_unit'] == 'minutes':
                entities['duration_minutes'] = entities['number']
            elif entities['time_unit'] == 'hours':
                entities['duration_minutes'] = entities['number'] * 60
        
        return entities
    
    def predict(self, text):
        """
        Classify user intent from text input.
        
        Args:
            text: Input text from user
            
        Returns:
            Dictionary with intent classification and extracted entities:
            {
                'intent': str,
                'confidence': float,
                'entities': dict
            }
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() or train() first.")
        
        # Preprocess input
        processed_text = self.preprocess_input(text)
        
        # Extract entities
        entities = self.extract_entities(text)
        
        # Check for pattern matches first (for simple, deterministic intents)
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, processed_text, re.IGNORECASE):
                    return {
                        'intent': intent,
                        'confidence': 1.0,  # Perfect match for pattern
                        'entities': entities
                    }
        
        # If no pattern match, use the classifier
        probabilities = self.model.predict_proba([processed_text])[0]
        max_prob_index = np.argmax(probabilities)
        predicted_intent = self.model.classes_[max_prob_index]
        confidence = probabilities[max_prob_index]
        
        return {
            'intent': predicted_intent,
            'confidence': float(confidence),
            'entities': entities
        }
    
    def train(self, data):
        """
        Train the chatbot model.
        
        Args:
            data: DataFrame with 'text' and 'intent' columns,
                  or path to a JSON file with intents and examples
            
        Returns:
            Self with trained model
        """
        # Handle different data input formats
        if isinstance(data, str):
            # Assume it's a path to a JSON file
            with open(data, 'r', encoding='utf-8') as f:
                intent_data = json.load(f)
            
            texts = []
            intents = []
            self.intent_patterns = {}
            
            # Process each intent
            for intent in intent_data:
                intent_name = intent['intent']
                
                # Store patterns for direct matching
                if 'patterns' in intent:
                    self.intent_patterns[intent_name] = intent['patterns']
                
                # Store examples for training
                if 'examples' in intent:
                    for example in intent['examples']:
                        texts.append(self.preprocess_input(example))
                        intents.append(intent_name)
        
        elif isinstance(data, pd.DataFrame):
            # Assume it's a DataFrame with text and intent columns
            texts = data['text'].apply(self.preprocess_input)
            intents = data['intent']
            
            # If there's a patterns column, process it
            if 'patterns' in data.columns:
                for intent_name in data['intent'].unique():
                    patterns = data[data['intent'] == intent_name]['patterns'].dropna()
                    if not patterns.empty:
                        self.intent_patterns[intent_name] = patterns.tolist()
        else:
            raise ValueError("Data must be a DataFrame or path to a JSON file")
        
        # Store unique intents
        self.intents = list(set(intents))
        
        # Create and train the model pipeline
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('classifier', MultinomialNB())
        ])
        
        self.model.fit(texts, intents)
        
        # Evaluate on training data (not ideal, but it's a starting point)
        predictions = self.model.predict(texts)
        accuracy = accuracy_score(intents, predictions)
        
        # Save model with accuracy
        self.save(accuracy=accuracy)
        
        return self
    
    def evaluate(self, test_data):
        """
        Evaluate model performance on test data.
        
        Args:
            test_data: DataFrame with 'text' and 'intent' columns
            
        Returns:
            Dictionary with performance metrics
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load() or train() first.")
        
        # Preprocess text
        texts = test_data['text'].apply(self.preprocess_input)
        intents = test_data['intent']
        
        # Make predictions
        predictions = self.model.predict(texts)
        
        # Calculate metrics
        accuracy = accuracy_score(intents, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            intents, predictions, average='weighted'
        )
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
    
    def get_intent_examples(self):
        """
        Get examples of intents for reference.
        
        Returns:
            Dictionary mapping intent names to example texts
        """
        return self.intent_patterns