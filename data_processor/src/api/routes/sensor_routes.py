"""
Routes API cho dữ liệu cảm biến.
"""
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from src.core.data import (
    DataManager,
    SensorType,
    SensorReading,
    EnvironmentSnapshot
)
from src.core.environment import EnvironmentAnalyzer

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Tạo router
router = APIRouter()

# Khởi tạo DataManager và EnvironmentAnalyzer
data_manager = DataManager()
environment_analyzer = EnvironmentAnalyzer()

@router.get("/")
async def get_all_sensors():
    """Lấy danh sách tất cả cảm biến."""
    sensors = [sensor_type.value for sensor_type in SensorType]
    return {"sensors": sensors}

@router.get("/collect")
async def collect_all_sensors():
    """Thu thập dữ liệu mới nhất từ tất cả cảm biến."""
    try:
        readings = data_manager.collect_all_latest_data()
        
        # Chuyển kết quả thành dict để serialization
        results = {}
        for sensor_type, reading in readings.items():
            results[sensor_type.value] = reading.dict()
            
        return {
            "success": True,
            "message": f"Collected data from {len(readings)} sensors",
            "data": results
        }
    except Exception as e:
        logger.error(f"Error collecting sensor data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting sensor data: {str(e)}"
        )

# @router.get("/{sensor_type}")
# async def get_sensor_data(
#     sensor_type: str,
#     collect: bool = Query(False, description="Thu thập dữ liệu mới"),
#     limit: int = Query(1, description="Số lượng bản ghi", ge=1, le=100)
# ):
#     """
#     Lấy dữ liệu từ sensor.
#     MẶC ĐỊNH: Dùng cache (collect=False)
#     """
#     # ... validation code ...
    
#     collector = data_manager.collectors[sensor_enum]
    
#     if limit == 1:
#         # Single reading - use cache by default
#         if collect:
#             # Force refresh only if explicitly requested
#             reading = collector.collect_latest_data(force_refresh=True)
#         else:
#             # DEFAULT: Use cache
#             reading = collector.get_latest_reading_from_cache()
            
#             # If no cache, collect
#             if not reading:
#                 reading = collector.collect_latest_data()
        
#         return reading.dict() if reading else {"error": "No data available"}
#     else:
#         # Multiple readings
#         readings = collector.get_recent_readings_from_cache(limit=limit)
        
#         if not readings and collect:
#             # Only fetch from Adafruit if explicitly requested
#             readings = collector.collect_historical_data(limit=limit)
        
#         return {
#             "sensor_type": sensor_type,
#             "count": len(readings),
#             "data": [r.dict() for r in readings]
#         }

@router.get("/snapshot")
async def get_environment_snapshot(
    collect: bool = Query(False, description="Force thu thập dữ liệu mới"),
    analyze: bool = Query(False, description="Phân tích dữ liệu")
):
    """
    Lấy snapshot môi trường.
    MẶC ĐỊNH: Dùng cache (collect=False)
    """
    snapshot = data_manager.get_environment_snapshot(
        collect_if_needed=True,
        force_collection=collect  # Chỉ force nếu được yêu cầu
    )

@router.get("/analyze")
async def analyze_environment():
    """Phân tích môi trường hiện tại."""
    try:
        # Lấy snapshot hiện tại
        snapshot = data_manager.get_environment_snapshot(collect_if_needed=True)
        
        # Phân tích snapshot
        analysis = environment_analyzer.analyze_snapshot(snapshot)
        
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing environment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing environment: {str(e)}"
        )

@router.get("/analyze/{sensor_type}")
async def analyze_sensor(
    sensor_type: str,
    collect: bool = Query(False, description="Thu thập dữ liệu mới")
):
    """
    Phân tích dữ liệu từ một loại cảm biến cụ thể.
    
    Args:
        sensor_type: Loại cảm biến (light, temperature, humidity, soil_moisture)
        collect: Nếu True, thu thập dữ liệu mới từ Adafruit
    """
    try:
        # Kiểm tra loại cảm biến hợp lệ
        valid_sensors = [sensor_type.value for sensor_type in SensorType]
        
        if sensor_type not in valid_sensors:
            raise HTTPException(
                status_code=404,
                detail=f"Sensor type '{sensor_type}' not found. Valid types: {valid_sensors}"
            )
            
        # Chuyển đổi thành SensorType enum
        sensor_enum = SensorType(sensor_type)
        
        # Lấy dữ liệu mới nhất
        collector = data_manager.collectors[sensor_enum]
        
        if collect:
            reading = collector.collect_latest_data()
        else:
            reading = collector.get_latest_reading_from_cache()
            
        if not reading:
            return {
                "error": "No data available",
                "sensor_type": sensor_type
            }
            
        # Phân tích dữ liệu
        analysis = environment_analyzer.analyze_reading(reading)
        
        return {
            "sensor_type": sensor_type,
            "timestamp": reading.timestamp.isoformat(),
            "reading": reading.dict(),
            "analysis": analysis
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing data for sensor {sensor_type}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing data for sensor {sensor_type}: {str(e)}"
        )

@router.get("/{sensor_type}")
async def get_sensor_data(
    sensor_type: str,
    collect: bool = Query(False, description="Thu thập dữ liệu mới"),
    limit: int = Query(1, description="Số lượng bản ghi", ge=1, le=100)
):
    """
    Lấy dữ liệu từ một loại cảm biến cụ thể.
    
    Args:
        sensor_type: Loại cảm biến (light, temperature, humidity, soil_moisture)
        collect: Nếu True, thu thập dữ liệu mới từ Adafruit
        limit: Số lượng bản ghi muốn lấy
    """
    try:
        # Kiểm tra loại cảm biến hợp lệ
        valid_sensors = [sensor_type.value for sensor_type in SensorType]
        
        if sensor_type not in valid_sensors:
            raise HTTPException(
                status_code=404,
                detail=f"Sensor type '{sensor_type}' not found. Valid types: {valid_sensors}"
            )
            
        # Chuyển đổi thành SensorType enum
        sensor_enum = SensorType(sensor_type)
        
        # Lấy collector tương ứng
        collector = data_manager.collectors[sensor_enum]
    
        if limit == 1:
            # Single reading - use cache by default
            if collect:
                # Force refresh only if explicitly requested
                reading = collector.collect_latest_data(force_refresh=True)
            else:
                # DEFAULT: Use cache
                reading = collector.get_latest_reading_from_cache()
                
                # If no cache, collect
                if not reading:
                    reading = collector.collect_latest_data()
            
            return reading.dict() if reading else {"error": "No data available"}
        else:
            # Multiple readings
            readings = collector.get_recent_readings_from_cache(limit=limit)
            
            if not readings and collect:
                # Only fetch from Adafruit if explicitly requested
                readings = collector.collect_historical_data(limit=limit)
            
            return {
                "sensor_type": sensor_type,
                "count": len(readings),
                "data": [r.dict() for r in readings]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data for sensor {sensor_type}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting data for sensor {sensor_type}: {str(e)}"
        )