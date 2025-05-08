"""
Routes API cho khuyến nghị tưới thông minh.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.core.greenhouse_ai_service import GreenhouseAIService
from src.api.app import get_service

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Tạo router
router = APIRouter()

# Models for request/response
class PlantInfo(BaseModel):
    """Thông tin về loại cây."""
    type: str
    name: Optional[str] = None
    stage: Optional[str] = None  # seedling, vegetative, flowering, fruiting

class ZoneInfo(BaseModel):
    """Thông tin về vùng tưới."""
    id: str
    name: Optional[str] = None
    plant_types: List[str]
    soil_moisture: Optional[float] = None
    location: Optional[str] = None

class RecommendationRequest(BaseModel):
    """Yêu cầu tạo khuyến nghị tưới."""
    plant_types: List[str] = Field(..., description="Các loại cây trồng")
    zones: Optional[List[ZoneInfo]] = Field(None, description="Thông tin về các vùng tưới")
    priority: Optional[str] = Field("normal", description="Mức ưu tiên (normal, high, low)")

class WaterSavings(BaseModel):
    """Thông tin tiết kiệm nước."""
    saved_water_liters: float
    saved_percentage: float
    current_water_usage: float
    optimized_water_usage: float

class ZoneRecommendation(BaseModel):
    """Khuyến nghị tưới cho một vùng cụ thể."""
    zone_id: str
    name: Optional[str] = None
    should_irrigate: bool
    duration_minutes: float
    irrigation_time: Optional[str] = None
    irrigation_datetime: Optional[str] = None
    plant_types: List[str]

class RecommendationResponse(BaseModel):
    """Phản hồi cho yêu cầu tạo khuyến nghị."""
    id: str
    timestamp: str
    should_irrigate: bool
    zones: Optional[List[ZoneRecommendation]] = None
    duration_minutes: Optional[float] = None
    irrigation_time: Optional[str] = None
    irrigation_datetime: Optional[str] = None
    soil_moisture: Optional[float] = None
    reason: str
    water_savings: Optional[WaterSavings] = None
    status: str  # created, sent, accepted, rejected, applied
    sent_to_core: bool

class HistoricalRecommendation(BaseModel):
    """Khuyến nghị tưới lịch sử với kết quả áp dụng."""
    id: str
    timestamp: str
    recommendation: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]] = None
    water_savings: Optional[WaterSavings] = None

@router.post("/create", response_model=RecommendationResponse)
async def create_recommendation(
    request: RecommendationRequest,
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Tạo khuyến nghị tưới dựa trên tình trạng hiện tại và loại cây trồng.
    
    Khuyến nghị sẽ bao gồm thời điểm tưới tối ưu, thời lượng tưới, và lượng nước tiết kiệm
    so với lịch tưới thông thường.
    """
    try:
        result = await service.create_irrigation_recommendation(
            request.plant_types,
            request.zones,
            request.priority
        )
        return result
    except Exception as e:
        logger.error(f"Error creating recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[HistoricalRecommendation])
async def get_recommendation_history(
    limit: int = Query(10, description="Số lượng khuyến nghị tối đa"),
    days: int = Query(30, description="Số ngày lịch sử"),
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Lấy lịch sử khuyến nghị và kết quả áp dụng.
    
    Returns một danh sách các khuyến nghị đã tạo, trạng thái của chúng,
    và kết quả nếu đã được áp dụng.
    """
    try:
        history = await service.get_recommendation_history(limit, days)
        return history
    except Exception as e:
        logger.error(f"Error getting recommendation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str = Path(..., description="ID của khuyến nghị"),
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Lấy thông tin chi tiết về một khuyến nghị cụ thể.
    """
    try:
        recommendation = await service.get_recommendation_by_id(recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found")
        return recommendation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendation {recommendation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{recommendation_id}/send", response_model=Dict[str, Any])
async def send_recommendation_to_core(
    recommendation_id: str = Path(..., description="ID của khuyến nghị"),
    priority: str = Query("normal", description="Mức ưu tiên (normal, high, low)"),
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Gửi một khuyến nghị đã có đến Core Operations Service.
    """
    try:
        result = await service.send_recommendation_to_core(recommendation_id, priority)
        return result
    except Exception as e:
        logger.error(f"Error sending recommendation {recommendation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/optimize/schedule", response_model=Dict[str, Any])
async def get_optimized_schedule(
    days: int = Query(14, ge=7, le=90, description="Số ngày dữ liệu phân tích"),
    service: GreenhouseAIService = Depends(get_service)
):
    """
    Tạo lịch tưới tối ưu dựa trên dữ liệu lịch sử.
    
    Phân tích dữ liệu cảm biến và lịch sử tưới để đề xuất lịch tưới tối ưu
    cho hiệu quả cao nhất và tiết kiệm nước.
    """
    try:
        schedule = await service.get_optimized_irrigation_schedule(days)
        return schedule
    except Exception as e:
        logger.error(f"Error creating optimized schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))