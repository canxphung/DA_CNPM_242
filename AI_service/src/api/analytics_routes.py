# src/api/analytics_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import json

from src.core.greenhouse_ai_service import GreenhouseAIService
from src.api.app import get_service
from src.database import get_db_session
from src.database.sensor_data import SensorData
from src.database.irrigation_events import IrrigationEvent

router = APIRouter()

class HistoricalAnalysis(BaseModel):
    """Model for historical data analysis."""
    period: str
    sensor_stats: Dict[str, Dict[str, float]]
    irrigation_events: int
    total_irrigation_minutes: int
    average_irrigation_duration: float
    soil_moisture_improvement: Optional[float] = None

class OptimizationRecommendation(BaseModel):
    """Model for optimization recommendations."""
    schedule: List[Dict[str, Any]]
    explanation: str

@router.get("/history", response_model=HistoricalAnalysis)
async def get_historical_analysis(
    days: int = Query(7, ge=1, le=90),
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Get historical data analysis.
    
    Analyzes sensor data and irrigation events over the specified time period.
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    session = get_db_session()
    try:
        # Get sensor data in time range
        sensor_data = session.query(SensorData).filter(
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        ).order_by(SensorData.timestamp).all()
        
        # Get irrigation events in time range
        irrigation_events = session.query(IrrigationEvent).filter(
            IrrigationEvent.start_time >= start_time,
            IrrigationEvent.start_time <= end_time
        ).order_by(IrrigationEvent.start_time).all()
        
        if not sensor_data:
            raise HTTPException(
                status_code=404,
                detail="No data available for the specified time period"
            )
        
        # Prepare analysis
        # Convert sensor data to pandas DataFrame for easier analysis
        sensor_df = pd.DataFrame([
            {
                'timestamp': data.timestamp,
                'soil_moisture': data.soil_moisture,
                'temperature': data.temperature,
                'humidity': data.humidity,
                'light_level': data.light_level
            }
            for data in sensor_data
        ])
        
        # Calculate sensor stats
        sensor_stats = {
            'soil_moisture': {
                'min': float(sensor_df['soil_moisture'].min()),
                'max': float(sensor_df['soil_moisture'].max()),
                'avg': float(sensor_df['soil_moisture'].mean()),
                'median': float(sensor_df['soil_moisture'].median())
            },
            'temperature': {
                'min': float(sensor_df['temperature'].min()),
                'max': float(sensor_df['temperature'].max()),
                'avg': float(sensor_df['temperature'].mean()),
                'median': float(sensor_df['temperature'].median())
            },
            'humidity': {
                'min': float(sensor_df['humidity'].min()),
                'max': float(sensor_df['humidity'].max()),
                'avg': float(sensor_df['humidity'].mean()),
                'median': float(sensor_df['humidity'].median())
            },
            'light_level': {
                'min': float(sensor_df['light_level'].min()),
                'max': float(sensor_df['light_level'].max()),
                'avg': float(sensor_df['light_level'].mean()),
                'median': float(sensor_df['light_level'].median())
            }
        }
        
        # Calculate irrigation stats
        total_irrigation_events = len(irrigation_events)
        total_irrigation_minutes = sum(event.duration_minutes for event in irrigation_events)
        
        if total_irrigation_events > 0:
            average_irrigation_duration = total_irrigation_minutes / total_irrigation_events
        else:
            average_irrigation_duration = 0
        
        # Calculate soil moisture improvement
        moisture_improvement = None
        if total_irrigation_events > 0:
            valid_events = [
                event for event in irrigation_events 
                if event.soil_moisture_before is not None and event.soil_moisture_after is not None
            ]
            
            if valid_events:
                improvements = [
                    event.soil_moisture_after - event.soil_moisture_before 
                    for event in valid_events
                ]
                moisture_improvement = sum(improvements) / len(improvements)
        
        return {
            "period": f"{start_time.date()} to {end_time.date()}",
            "sensor_stats": sensor_stats,
            "irrigation_events": total_irrigation_events,
            "total_irrigation_minutes": total_irrigation_minutes,
            "average_irrigation_duration": average_irrigation_duration,
            "soil_moisture_improvement": moisture_improvement
        }
    finally:
        session.close()

@router.get("/optimize", response_model=OptimizationRecommendation)
async def get_optimization_recommendation(
    days: int = Query(14, ge=7, le=90),
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Get irrigation schedule optimization recommendation.
    
    Analyzes historical data to recommend an optimal irrigation schedule.
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    session = get_db_session()
    try:
        # Get sensor data in time range
        sensor_data = session.query(SensorData).filter(
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        ).order_by(SensorData.timestamp).all()
        
        # Get irrigation events in time range
        irrigation_events = session.query(IrrigationEvent).filter(
            IrrigationEvent.start_time >= start_time,
            IrrigationEvent.start_time <= end_time
        ).order_by(IrrigationEvent.start_time).all()
        
        if not sensor_data or not irrigation_events:
            raise HTTPException(
                status_code=404,
                detail="Not enough data available for optimization"
            )
        
        # Prepare data
        sensor_df = pd.DataFrame([
            {
                'timestamp': data.timestamp,
                'hour': data.timestamp.hour,
                'day_of_week': data.timestamp.weekday(),
                'soil_moisture': data.soil_moisture,
                'temperature': data.temperature,
                'humidity': data.humidity,
                'light_level': data.light_level
            }
            for data in sensor_data
        ])
        
        irrigation_df = pd.DataFrame([
            {
                'start_time': event.start_time,
                'hour': event.start_time.hour,
                'day_of_week': event.start_time.weekday(),
                'duration_minutes': event.duration_minutes,
                'soil_moisture_before': event.soil_moisture_before,
                'soil_moisture_after': event.soil_moisture_after,
                'moisture_improvement': (
                    event.soil_moisture_after - event.soil_moisture_before
                    if event.soil_moisture_after is not None and event.soil_moisture_before is not None
                    else None
                )
            }
            for event in irrigation_events
        ])
        
        # Simple optimization: find hours with best moisture improvement
        if not irrigation_df.empty and 'moisture_improvement' in irrigation_df.columns:
            # Remove rows with no improvement data
            valid_irrigation = irrigation_df.dropna(subset=['moisture_improvement'])
            
            if not valid_irrigation.empty:
                # Group by hour of day
                hour_analysis = valid_irrigation.groupby('hour').agg({
                    'moisture_improvement': 'mean',
                    'duration_minutes': 'mean',
                    'start_time': 'count'
                }).reset_index()
                
                hour_analysis = hour_analysis.rename(columns={'start_time': 'count'})
                
                # Sort by moisture improvement (most effective first)
                best_hours = hour_analysis.sort_values(
                    'moisture_improvement', ascending=False
                ).head(3)
                
                # Create schedule
                schedule = []
                for _, row in best_hours.iterrows():
                    schedule.append({
                        'hour': int(row['hour']),
                        'duration_minutes': int(row['duration_minutes']),
                        'effectiveness': float(row['moisture_improvement']),
                        'frequency': 'daily'
                    })
                
                explanation = (
                    "This schedule is based on historical data showing the hours "
                    "when irrigation has been most effective at improving soil moisture. "
                    "The recommended durations are based on average durations used historically."
                )
            else:
                # Default schedule based on best practices
                schedule = [
                    {'hour': 6, 'duration_minutes': 10, 'effectiveness': None, 'frequency': 'daily'},
                    {'hour': 18, 'duration_minutes': 10, 'effectiveness': None, 'frequency': 'daily'}
                ]
                explanation = (
                    "Not enough historical data with before/after moisture measurements. "
                    "This is a default schedule based on general best practices for "
                    "watering in the early morning and early evening."
                )
        else:
            # Default schedule
            schedule = [
                {'hour': 6, 'duration_minutes': 10, 'effectiveness': None, 'frequency': 'daily'},
                {'hour': 18, 'duration_minutes': 10, 'effectiveness': None, 'frequency': 'daily'}
            ]
            explanation = (
                "Not enough historical irrigation data. "
                "This is a default schedule based on general best practices for "
                "watering in the early morning and early evening."
            )
        
        return {
            "schedule": schedule,
            "explanation": explanation
        }
        
        # Note: In a more advanced implementation, we would use the OpenAI API
        # to generate more sophisticated optimization recommendations
    finally:
        session.close()

@router.get("/model-performance", response_model=Dict[str, Any])
async def get_model_performance(
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Get performance metrics for the AI models.
    
    Returns evaluation metrics for the local models.
    """
    models_info = {}
    
    try:
        # Get irrigation model info
        irrigation_model = service.model_registry.get_model('irrigation')
        if irrigation_model:
            feature_importance = None
            try:
                importance_df = irrigation_model.get_feature_importance()
                feature_importance = importance_df.to_dict(orient='records')
            except Exception:
                pass
            
            models_info['irrigation'] = {
                'version': irrigation_model.version,
                'feature_importance': feature_importance
            }
        
        # Get chatbot model info
        chatbot_model = service.model_registry.get_model('chatbot')
        if chatbot_model:
            models_info['chatbot'] = {
                'version': chatbot_model.version,
                'intents': chatbot_model.intents
            }
        
        # Get available model versions
        models_info['available_models'] = service.model_registry.list_available_models()
        
        # Get API stats
        models_info['api_usage'] = {
            'total_calls': service.stats['api_calls'],
            'last_call': service.stats['last_api_call']
        }
        
        return models_info
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving model performance: {str(e)}"
        )