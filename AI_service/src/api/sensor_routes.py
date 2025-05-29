# src/api/sensor_routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.core.greenhouse_ai_service import GreenhouseAIService
from src.api.dependencies import get_service
from src.database import get_db_session
from src.database.sensor_data import SensorData

router = APIRouter()

class SensorDataRequest(BaseModel):
    """Model for posting new sensor data."""
    soil_moisture: float
    temperature: float
    humidity: float
    light_level: float

class SensorDataResponse(BaseModel):
    """Model for sensor data response."""
    soil_moisture: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    light_level: Optional[float] = None
    timestamp: Optional[str] = None

class ProcessSensorResult(BaseModel):
    """Model for processing sensor data result."""
    decision: Dict[str, Any]
    actions_taken: List[str]
    timestamp: str

@router.get("/current", response_model=SensorDataResponse)
async def get_current_sensor_data(
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Get the current sensor readings.
    
    Returns the most recent values from all sensors.
    """
    data = service._get_current_sensor_data()
    
    if not data['timestamp']:
        raise HTTPException(
            status_code=404,
            detail="No sensor data available"
        )
    
    return data

@router.post("/data", response_model=ProcessSensorResult)
async def post_sensor_data(
    data: SensorDataRequest,
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Submit new sensor readings and process them.
    
    This endpoint accepts new sensor data, stores it in the database,
    and processes it to make irrigation decisions.
    """
    # Convert request to dictionary
    sensor_data = {
        'soil_moisture': data.soil_moisture,
        'temperature': data.temperature,
        'humidity': data.humidity,
        'light_level': data.light_level
    }
    
    # Process the sensor data
    result = service.process_sensor_data(sensor_data)
    
    return result

@router.get("/history", response_model=List[SensorDataResponse])
async def get_sensor_history(
    hours: int = 24,
    skip: int = 0,
    limit: int = 100
):
    """
    Get historical sensor data.
    
    Returns sensor readings from the specified time period.
    """
    if hours <= 0 or hours > 720:  # Max 30 days
        raise HTTPException(
            status_code=400,
            detail="Hours must be between 1 and 720"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    with get_db_session() as session:
    
        # Get sensor data in time range
        data = session.query(SensorData).filter(
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time
        ).order_by(SensorData.timestamp.desc()).offset(skip).limit(limit).all()
        
        if not data:
            return []
        
        # Convert to response format
        result = []
        for item in data:
            result.append({
                'soil_moisture': item.soil_moisture,
                'temperature': item.temperature,
                'humidity': item.humidity,
                'light_level': item.light_level,
                'timestamp': item.timestamp.isoformat()
            })
        
        return result