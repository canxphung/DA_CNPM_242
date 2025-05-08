"""
Routes API cho quản lý hệ thống.
"""
import logging
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Body, Path, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from src.infrastructure.config.system_config import SystemConfigManager
from src.infrastructure.dependencies import handle_exceptions
from src.infrastructure.exceptions import ValidationError, ConfigurationError

# Khởi tạo logger
logger = logging.getLogger(__name__)

# Tạo router
router = APIRouter()

# Models for request bodies
class ConfigUpdate(BaseModel):
    path: str = Field(..., description="Đường dẫn cấu hình (ví dụ: 'irrigation.auto.enabled')")
    value: Any = Field(..., description="Giá trị mới")

class BulkConfigUpdate(BaseModel):
    updates: List[ConfigUpdate] = Field(..., description="Danh sách các cập nhật cấu hình")

@router.get("/config", summary="Lấy cấu hình hệ thống")
@handle_exceptions
async def get_system_config(
    path: Optional[str] = Query(None, description="Đường dẫn cấu hình cụ thể (nếu không cung cấp sẽ trả về toàn bộ)")
):
    """
    Lấy cấu hình hệ thống.
    
    Nếu không cung cấp đường dẫn, endpoint sẽ trả về toàn bộ cấu hình.
    Nếu cung cấp đường dẫn, chỉ trả về giá trị tại đường dẫn đó.
    """
    config_manager = SystemConfigManager()
    
    if path:
        value = config_manager.get(path)
        if value is None:
            raise ValidationError(
                message=f"Configuration path '{path}' not found",
                field="path"
            )
        return {
            "path": path,
            "value": value
        }
    else:
        return config_manager.get_config()

@router.put("/config", summary="Cập nhật cấu hình hệ thống")
@handle_exceptions
async def update_system_config(update: ConfigUpdate):
    """
    Cập nhật một giá trị cấu hình hệ thống.
    """
    config_manager = SystemConfigManager()
    
    try:
        success = config_manager.set(update.path, update.value)
        
        if not success:
            raise ConfigurationError(
                message=f"Failed to update configuration at '{update.path}'",
                details={"path": update.path, "value": update.value}
            )
            
        return {
            "success": True,
            "message": f"Configuration updated at '{update.path}'",
            "path": update.path,
            "value": update.value
        }
    except ConfigurationError as e:
        raise e
    except Exception as e:
        raise ConfigurationError(
            message=str(e),
            details={"path": update.path, "value": update.value}
        )

@router.put("/config/bulk", summary="Cập nhật nhiều cấu hình hệ thống")
@handle_exceptions
async def bulk_update_system_config(updates: BulkConfigUpdate):
    """
    Cập nhật nhiều giá trị cấu hình hệ thống cùng một lúc.
    """
    config_manager = SystemConfigManager()
    
    try:
        # Chuyển đổi thành dict {path: value}
        updates_dict = {update.path: update.value for update in updates.updates}
        
        success = config_manager.update(updates_dict)
        
        if not success:
            raise ConfigurationError(
                message="Failed to update some configuration values",
                details={"updates": updates_dict}
            )
            
        return {
            "success": True,
            "message": f"Updated {len(updates.updates)} configuration values",
            "updated_paths": list(updates_dict.keys())
        }
    except ConfigurationError as e:
        raise e
    except Exception as e:
        raise ConfigurationError(
            message=str(e),
            details={"updates": updates.updates}
        )

@router.post("/config/reset", summary="Đặt lại cấu hình hệ thống")
@handle_exceptions
async def reset_system_config(
    path: Optional[str] = Query(None, description="Đường dẫn cấu hình cụ thể cần đặt lại (nếu không cung cấp sẽ đặt lại toàn bộ)")
):
    """
    Đặt lại cấu hình hệ thống về giá trị mặc định.
    
    Nếu không cung cấp đường dẫn, sẽ đặt lại toàn bộ cấu hình.
    Nếu cung cấp đường dẫn, chỉ đặt lại giá trị tại đường dẫn đó.
    """
    config_manager = SystemConfigManager()
    
    success = config_manager.reset(path)
    
    if not success:
        message = f"Failed to reset configuration at '{path}'" if path else "Failed to reset configuration"
        raise ConfigurationError(message=message)
        
    message = f"Configuration reset at '{path}'" if path else "Configuration reset to defaults"
    return {
        "success": True,
        "message": message
    }

@router.get("/info", summary="Lấy thông tin hệ thống")
async def get_system_info():
    """
    Lấy thông tin chung về hệ thống, gồm phiên bản, môi trường, và các thống kê khác.
    """
    config_manager = SystemConfigManager()
    system_config = config_manager.get("system", {})
    
    return {
        "name": system_config.get("name", "Core Operations Service"),
        "version": system_config.get("version", "0.1.0"),
        "environment": system_config.get("environment", "development"),
        "uptime": "Unknown",  # Sẽ triển khai sau
        "timestamp": datetime.now().isoformat(),
        "build_date": os.getenv("BUILD_DATE", "unknown"),
        "commit_hash": os.getenv("COMMIT_HASH", "unknown")
    }