# src/api/analytics_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
# import json # Removed as it's not explicitly used

from src.core.greenhouse_ai_service import GreenhouseAIService
from src.api.dependencies import get_service # Assuming get_service is correctly defined elsewhere
from src.database import get_db_session # Assuming this is the context manager
from src.database.sensor_data import SensorData # Assuming SQLAlchemy model
from src.database.irrigation_events import IrrigationEvent # Assuming SQLAlchemy model

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
    days: int = Query(7, ge=1, le=90)
    # service: GreenhouseAIService = Depends(get_service) # Removed, was not used
):
    """
    Get historical data analysis.

    Analyzes sensor data and irrigation events over the specified time period.
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    with get_db_session() as session:
        # Get sensor data in time range
        sensor_data_records = session.query(SensorData).filter(
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        ).order_by(SensorData.timestamp).all()

        # Get irrigation events in time range
        irrigation_event_records = session.query(IrrigationEvent).filter(
            IrrigationEvent.start_time >= start_time,
            IrrigationEvent.start_time <= end_time
        ).order_by(IrrigationEvent.start_time).all()

        if not sensor_data_records:
            raise HTTPException(
                status_code=404,
                detail="No sensor data available for the specified time period"
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
            for data in sensor_data_records
        ])

        # Calculate sensor stats
        # Ensure DataFrame is not empty before calling aggregation functions
        if sensor_df.empty:
             sensor_stats = {
                key: {'min': 0.0, 'max': 0.0, 'avg': 0.0, 'median': 0.0}
                for key in ['soil_moisture', 'temperature', 'humidity', 'light_level']
            }
        else:
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
        total_irrigation_events = len(irrigation_event_records)
        total_irrigation_minutes = sum(event.duration_minutes for event in irrigation_event_records if event.duration_minutes is not None)

        if total_irrigation_events > 0:
            average_irrigation_duration = total_irrigation_minutes / total_irrigation_events if total_irrigation_minutes is not None else 0.0
        else:
            average_irrigation_duration = 0.0

        # Calculate soil moisture improvement
        moisture_improvement = None
        if total_irrigation_events > 0:
            valid_events = [
                event for event in irrigation_event_records
                if event.soil_moisture_before is not None and event.soil_moisture_after is not None
            ]

            if valid_events:
                improvements = [
                    event.soil_moisture_after - event.soil_moisture_before
                    for event in valid_events
                ]
                if improvements: # Ensure list is not empty
                    moisture_improvement = sum(improvements) / len(improvements)

        return HistoricalAnalysis(
            period=f"{start_time.date()} to {end_time.date()}",
            sensor_stats=sensor_stats,
            irrigation_events=total_irrigation_events,
            total_irrigation_minutes=int(total_irrigation_minutes) if total_irrigation_minutes is not None else 0,
            average_irrigation_duration=average_irrigation_duration,
            soil_moisture_improvement=moisture_improvement
        )
    # The 'finally session.close()' is no longer needed here because
    # the 'with get_db_session() as session:' context manager handles it.

@router.get("/optimize", response_model=OptimizationRecommendation)
async def get_optimization_recommendation(
    days: int = Query(14, ge=7, le=90)
    # service: GreenhouseAIService = Depends(get_service) # Removed, was not used
):
    """
    Get irrigation schedule optimization recommendation.

    Analyzes historical data to recommend an optimal irrigation schedule.
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    with get_db_session() as session:
        # Get sensor data in time range
        sensor_data_records = session.query(SensorData).filter(
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        ).order_by(SensorData.timestamp).all()

        # Get irrigation events in time range
        irrigation_event_records = session.query(IrrigationEvent).filter(
            IrrigationEvent.start_time >= start_time,
            IrrigationEvent.start_time <= end_time
        ).order_by(IrrigationEvent.start_time).all()

        if not sensor_data_records or not irrigation_event_records:
            raise HTTPException(
                status_code=404,
                detail="Not enough sensor or irrigation data available for optimization for the specified period."
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
            for data in sensor_data_records
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
            for event in irrigation_event_records
        ])

        # Simple optimization: find hours with best moisture improvement
        schedule: List[Dict[str, Any]] = []
        explanation: str = ""

        if not irrigation_df.empty and 'moisture_improvement' in irrigation_df.columns:
            valid_irrigation = irrigation_df.dropna(subset=['moisture_improvement'])

            if not valid_irrigation.empty:
                hour_analysis = valid_irrigation.groupby('hour').agg(
                    moisture_improvement_avg=('moisture_improvement', 'mean'),
                    duration_minutes_avg=('duration_minutes', 'mean'),
                    event_count=('start_time', 'count') # 'start_time' or any non-null column
                ).reset_index()

                # Sort by moisture improvement (most effective first)
                best_hours = hour_analysis.sort_values(
                    'moisture_improvement_avg', ascending=False
                ).head(3) # Take top 3 effective hours

                for _, row in best_hours.iterrows():
                    schedule.append({
                        'hour': int(row['hour']),
                        'duration_minutes': int(round(row['duration_minutes_avg'])), # Round to nearest int
                        'effectiveness_score': float(row['moisture_improvement_avg']),
                        'frequency': 'daily' # Example, could be made more dynamic
                    })

                explanation = (
                    "This schedule is based on historical data showing the hours "
                    "when irrigation has been most effective at improving soil moisture. "
                    "The recommended durations are based on average durations used historically during those hours."
                )
            else: # Fallback if no valid irrigation data with improvement
                schedule = [
                    {'hour': 6, 'duration_minutes': 10, 'effectiveness_score': None, 'frequency': 'daily'},
                    {'hour': 18, 'duration_minutes': 10, 'effectiveness_score': None, 'frequency': 'daily'}
                ]
                explanation = (
                    "Not enough historical data with before/after moisture measurements to calculate effectiveness. "
                    "This is a default schedule based on general best practices for "
                    "watering in the early morning and early evening."
                )
        else: # Fallback if irrigation_df is empty or missing column
            schedule = [
                {'hour': 6, 'duration_minutes': 10, 'effectiveness_score': None, 'frequency': 'daily'},
                {'hour': 18, 'duration_minutes': 10, 'effectiveness_score': None, 'frequency': 'daily'}
            ]
            explanation = (
                "Not enough historical irrigation data to perform optimization. "
                "This is a default schedule based on general best practices for "
                "watering in the early morning and early evening."
            )

        return OptimizationRecommendation(
            schedule=schedule,
            explanation=explanation
        )
    # The 'finally session.close()' is no longer needed here.

@router.get("/model-performance", response_model=Dict[str, Any])
async def get_model_performance(
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Get performance metrics for the AI models.

    Returns evaluation metrics for the local models.
    """
    models_info: Dict[str, Any] = {}

    try:
        # Get irrigation model info
        # Assuming service.model_registry.get_model might return None or raise an error
        irrigation_model = None
        try:
            irrigation_model = service.model_registry.get_model('irrigation')
        except Exception as e:
            # Log this error if desired, e.g., logger.warning("Could not retrieve irrigation model: %s", e)
            pass # Keep irrigation_model as None

        if irrigation_model and hasattr(irrigation_model, 'version'):
            feature_importance_data = None
            if hasattr(irrigation_model, 'get_feature_importance'):
                try:
                    importance_df = irrigation_model.get_feature_importance()
                    if importance_df is not None and not importance_df.empty:
                         feature_importance_data = importance_df.to_dict(orient='records')
                except Exception as e:
                    # Log this error if desired, e.g., logger.warning("Could not get feature importance: %s", e)
                    pass # Keep feature_importance_data as None

            models_info['irrigation'] = {
                'version': irrigation_model.version,
                'feature_importance': feature_importance_data
            }

        # Get chatbot model info
        chatbot_model = None
        try:
            chatbot_model = service.model_registry.get_model('chatbot')
        except Exception as e:
            # Log this error
            pass

        if chatbot_model and hasattr(chatbot_model, 'version'):
            intents_data = None
            if hasattr(chatbot_model, 'intents'):
                intents_data = chatbot_model.intents

            models_info['chatbot'] = {
                'version': chatbot_model.version,
                'intents': intents_data
            }

        # Get available model versions
        if hasattr(service.model_registry, 'list_available_models'):
            try:
                models_info['available_models'] = service.model_registry.list_available_models()
            except Exception as e:
                # Log this error
                models_info['available_models'] = {"error": "Could not retrieve available models."}


        # Get API stats from the service (assuming service.stats is a dict)
        api_usage_stats = {"total_calls": 0, "last_call": None}
        if hasattr(service, 'stats') and isinstance(service.stats, dict):
            api_usage_stats['total_calls'] = service.stats.get('api_calls', 0)
            api_usage_stats['last_call'] = service.stats.get('last_api_call')
        models_info['api_usage'] = api_usage_stats

        if not models_info: # If no model info could be retrieved at all
            return {"message": "No model performance data available at the moment."}

        return models_info
    except Exception as e:
        # Log the exception e here for debugging
        # import logging
        # logging.getLogger(__name__).error(f"Error retrieving model performance: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while retrieving model performance: {str(e)}"
        )