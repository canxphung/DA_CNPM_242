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

@router.get("/snapshot")
async def get_environment_snapshot(
    collect: bool = Query(True, description="Thu thập dữ liệu mới nếu cần"),
    analyze: bool = Query(False, description="Phân tích dữ liệu")
):
    """
    Lấy snapshot hiện tại của môi trường.
    
    Args:
        collect: Nếu True, thu thập dữ liệu mới nếu cache quá cũ
        analyze: Nếu True, phân tích dữ liệu và trả về kết quả phân tích
    """
    try:
        snapshot = data_manager.get_environment_snapshot(collect_if_needed=collect)
        
        result = {
            "timestamp": snapshot.timestamp.isoformat(),
            "status": snapshot.get_overall_status(),
            "sensors": {
                "light": snapshot.light.dict() if snapshot.light else None,
                "temperature": snapshot.temperature.dict() if snapshot.temperature else None,
                "humidity": snapshot.humidity.dict() if snapshot.humidity else None,
                "soil_moisture": snapshot.soil_moisture.dict() if snapshot.soil_moisture else None
            }
        }
        
        # Phân tích nếu được yêu cầu
        if analyze:
            analysis = environment_analyzer.analyze_snapshot(snapshot)
            result["analysis"] = analysis
            
        return result
    except Exception as e:
        logger.error(f"Error getting environment snapshot: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting environment snapshot: {str(e)}"
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
        
        # Thu thập dữ liệu mới nếu được yêu cầu
        if collect:
            reading = collector.collect_latest_data()
            if limit == 1 and reading:
                return reading.dict()
                
        # Lấy dữ liệu từ cache
        if limit == 1:
            reading = collector.get_latest_reading_from_cache()
            if reading:
                return reading.dict()
            else:
                # Nếu không có trong cache và không được yêu cầu thu thập, trả về lỗi
                if not collect:
                    return {
                        "error": "No data available in cache",
                        "sensor_type": sensor_type
                    }
                else:
                    return {
                        "error": "Failed to collect data",
                        "sensor_type": sensor_type
                    }
        else:
            # Lấy nhiều bản ghi
            readings = collector.get_recent_readings_from_cache(limit=limit)
            if not readings and collect:
                # Nếu không có dữ liệu trong cache, thử lấy dữ liệu lịch sử từ Adafruit
                readings = collector.collect_historical_data(limit=limit)
                
            # Trả về danh sách dict
            return {
                "sensor_type": sensor_type,
                "count": len(readings),
                "data": [reading.dict() for reading in readings]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data for sensor {sensor_type}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting data for sensor {sensor_type}: {str(e)}"
        )