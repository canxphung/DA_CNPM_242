"""
Routes API cho điều khiển hệ thống tưới.
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Path, Depends
from pydantic import BaseModel, Field

from src.core.control import (
    IrrigationManager,
    IrrigationScheduler,
    IrrigationDecisionMaker
)
from src.infrastructure.dependencies import (
    handle_exceptions,
    get_irrigation_manager,
    get_water_pump_controller
)
from src.infrastructure.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    OperationError
)

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Tạo router
router = APIRouter()

# Models for request bodies
class ScheduleCreate(BaseModel):
    name: str = Field(..., description="Tên lịch tưới")
    days: List[str] = Field(..., description="Các ngày trong tuần (monday, tuesday, ...)")
    start_time: str = Field(..., description="Thời gian bắt đầu (HH:MM)")
    duration: int = Field(..., description="Thời lượng tưới (giây)")
    active: bool = Field(True, description="Trạng thái hoạt động")
    description: Optional[str] = Field(None, description="Mô tả")

class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Tên lịch tưới")
    days: Optional[List[str]] = Field(None, description="Các ngày trong tuần (monday, tuesday, ...)")
    start_time: Optional[str] = Field(None, description="Thời gian bắt đầu (HH:MM)")
    duration: Optional[int] = Field(None, description="Thời lượng tưới (giây)")
    active: Optional[bool] = Field(None, description="Trạng thái hoạt động")
    description: Optional[str] = Field(None, description="Mô tả")

class AutoIrrigationConfig(BaseModel):
    enabled: Optional[bool] = Field(None, description="Bật/tắt tưới tự động")
    min_decision_interval: Optional[int] = Field(None, description="Khoảng thời gian tối thiểu giữa các quyết định (giây)")
    moisture_thresholds: Optional[Dict[str, float]] = Field(None, description="Ngưỡng độ ẩm")
    watering_durations: Optional[Dict[str, int]] = Field(None, description="Thời lượng tưới")

class RecommendationModel(BaseModel):
    source: str
    recommendation: Dict[str, Any]
    priority: str = "normal"
    timestamp: str

@router.post("/recommendation", summary="Nhận khuyến nghị tưới từ AI Service")
@handle_exceptions
async def receive_ai_recommendation(
    recommendation: RecommendationModel = Body(...),
    manager: IrrigationManager = Depends(get_irrigation_manager)
):
    """
    Nhận khuyến nghị tưới từ AI Service và xử lý dựa trên
    cấu hình hệ thống hiện tại.
    """
    result = manager.process_ai_recommendation(recommendation)
    return result

@router.get("/status", summary="Lấy trạng thái hệ thống tưới")
@handle_exceptions
async def get_system_status(
    manager: IrrigationManager = Depends(get_irrigation_manager)
):
    """
    Lấy trạng thái tổng hợp của hệ thống tưới bao gồm:
    - Trạng thái máy bơm
    - Cấu hình tưới tự động
    - Danh sách lịch trình
    """
    return manager.get_system_status()

@router.get("/history", summary="Lấy lịch sử tưới")
@handle_exceptions
async def get_irrigation_history(
    manager: IrrigationManager = Depends(get_irrigation_manager)
):
    """
    Lấy lịch sử tưới bao gồm:
    - Các sự kiện tưới đã xảy ra
    - Các quyết định tưới tự động
    - Thống kê sử dụng nước
    """
    return manager.get_irrigation_history()

@router.post("/system/{action}", summary="Điều khiển hệ thống tưới")
@handle_exceptions
async def control_system(
    action: str = Path(..., description="Hành động: 'start' hoặc 'stop'"),
    manager: IrrigationManager = Depends(get_irrigation_manager)
):
    """
    Điều khiển toàn bộ hệ thống tưới.
    
    - **start**: Khởi động hệ thống, bắt đầu thu thập dữ liệu và lập lịch
    - **stop**: Dừng hệ thống, dừng tất cả các quá trình ngầm
    """
    if action.lower() not in ["start", "stop"]:
        raise ValidationError(
            message=f"Invalid action: {action}. Valid actions: 'start' or 'stop'",
            field="action"
        )
        
    if action.lower() == "start":
        result = manager.start_system()
        return {
            "success": result["success"],
            "message": "Irrigation system started",
            "details": result
        }
    else:  # stop
        result = manager.stop_system()
        return {
            "success": result["success"],
            "message": "Irrigation system stopped",
            "details": result
        }

@router.post("/pump/{action}", summary="Điều khiển máy bơm nước")
@handle_exceptions
async def control_pump(
    action: str = Path(..., description="Hành động: 'on' hoặc 'off'"),
    duration: int = Query(300, description="Thời lượng tưới nếu bật (giây)", ge=5, le=1800),
    manager: IrrigationManager = Depends(get_irrigation_manager)
):
    """
    Điều khiển thủ công máy bơm nước.
    
    - **on**: Bật máy bơm trong thời gian chỉ định
    - **off**: Tắt máy bơm
    
    Khi bật máy bơm, bạn có thể chỉ định thời lượng tưới (tính bằng giây).
    Máy bơm sẽ tự động tắt sau khi hết thời gian.
    """
    if action.lower() not in ["on", "off"]:
        raise ValidationError(
            message=f"Invalid action: {action}. Valid actions: 'on' or 'off'",
            field="action"
        )
        
    result = manager.manually_control_pump(action, duration)
    
    if not result["success"]:
        raise OperationError(
            message=result.get("message", "Failed to control pump"),
            operation=f"pump_{action.lower()}"
        )
        
    return result

@router.get("/pump/status", summary="Lấy trạng thái máy bơm")
@handle_exceptions
async def get_pump_status(
    pump_controller = Depends(get_water_pump_controller)
):
    """
    Lấy trạng thái hiện tại của máy bơm nước bao gồm:
    - Trạng thái bật/tắt
    - Thời gian bắt đầu (nếu đang bật)
    - Thời gian dự kiến tắt (nếu đang bật)
    - Thống kê sử dụng
    """
    return pump_controller.get_status()

@router.get("/schedules", summary="Lấy danh sách lịch tưới")
@handle_exceptions
async def get_schedules():
    """
    Lấy danh sách tất cả các lịch tưới đã được cấu hình.
    """
    scheduler = IrrigationScheduler()
    schedules = scheduler.get_schedules()
    return {"schedules": schedules, "count": len(schedules)}

@router.post("/schedules", summary="Tạo lịch tưới mới")
@handle_exceptions
async def create_schedule(schedule: ScheduleCreate):
    """
    Tạo lịch tưới mới với các thông tin:
    - Tên lịch tưới
    - Các ngày trong tuần
    - Thời gian bắt đầu (định dạng HH:MM)
    - Thời lượng tưới (giây)
    - Trạng thái hoạt động
    - Mô tả (tùy chọn)
    """
    scheduler = IrrigationScheduler()
    result = scheduler.add_schedule(schedule.dict())
    
    if not result["success"]:
        raise ValidationError(
            message=result["message"],
            field="schedule"
        )
        
    return result

@router.put("/schedules/{schedule_id}", summary="Cập nhật lịch tưới")
@handle_exceptions
async def update_schedule(
    schedule_id: str = Path(..., description="ID của lịch tưới cần cập nhật"),
    schedule: ScheduleUpdate = Body(...)
):
    """
    Cập nhật thông tin của một lịch tưới đã tồn tại.
    """
    update_data = {k: v for k, v in schedule.dict().items() if v is not None}
    
    if not update_data:
        raise ValidationError(
            message="No update data provided",
            field="schedule"
        )
        
    scheduler = IrrigationScheduler()
    result = scheduler.update_schedule(schedule_id, update_data)
    
    if not result["success"]:
        if "not found" in result["message"]:
            raise ResourceNotFoundError(
                message=result["message"],
                resource_type="schedule",
                resource_id=schedule_id
            )
        else:
            raise ValidationError(
                message=result["message"],
                field="schedule"
            )
            
    return result

@router.delete("/schedules/{schedule_id}", summary="Xóa lịch tưới")
@handle_exceptions
async def delete_schedule(
    schedule_id: str = Path(..., description="ID của lịch tưới cần xóa")
):
    """
    Xóa một lịch tưới khỏi hệ thống.
    """
    scheduler = IrrigationScheduler()
    result = scheduler.delete_schedule(schedule_id)
    
    if not result["success"]:
        raise ResourceNotFoundError(
            message=result["message"],
            resource_type="schedule",
            resource_id=schedule_id
        )
            
    return result

@router.get("/auto", summary="Lấy cấu hình tưới tự động")
@handle_exceptions
async def get_auto_irrigation_config():
    """
    Lấy cấu hình hiện tại của hệ thống tưới tự động.
    """
    decision_maker = IrrigationDecisionMaker()
    return decision_maker.get_configuration()

@router.put("/auto", summary="Cập nhật cấu hình tưới tự động")
@handle_exceptions
async def update_auto_irrigation_config(config: AutoIrrigationConfig):
    """
    Cập nhật cấu hình của hệ thống tưới tự động.
    """
    decision_maker = IrrigationDecisionMaker()
    
    update_data = {k: v for k, v in config.dict().items() if v is not None}
    
    if not update_data:
        raise ValidationError(
            message="No update data provided",
            field="config"
        )
            
    result = decision_maker.update_configuration(update_data)
    
    if not result["success"]:
        raise ValidationError(
            message=result["message"],
            field="config"
        )
        
    return result

@router.post("/auto/{action}", summary="Điều khiển tưới tự động")
@handle_exceptions
async def control_auto_irrigation(
    action: str = Path(..., description="Hành động: 'enable', 'disable', hoặc 'trigger'"),
    manager: IrrigationManager = Depends(get_irrigation_manager)
):
    """
    Điều khiển hệ thống tưới tự động.
    
    - **enable**: Bật tưới tự động
    - **disable**: Tắt tưới tự động
    - **trigger**: Kích hoạt một quyết định tưới ngay lập tức
    """
    decision_maker = IrrigationDecisionMaker()
    
    if action.lower() not in ["enable", "disable", "trigger"]:
        raise ValidationError(
            message=f"Invalid action: {action}. Valid actions: 'enable', 'disable', or 'trigger'",
            field="action"
        )
        
    if action.lower() == "enable":
        result = decision_maker.enable_auto_irrigation(True)
        return result
    elif action.lower() == "disable":
        result = decision_maker.enable_auto_irrigation(False)
        return result
    elif action.lower() == "trigger":
        result = manager.trigger_manual_decision()
        return result
    
# Thêm vào cuối file control_routes.py
@router.get("/test-simple-route")
async def test_simple_route_func():
    return {"message": "This is a super simple route"}