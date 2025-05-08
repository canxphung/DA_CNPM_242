"""
Định nghĩa các dependency cho FastAPI.
"""
import logging
from fastapi import Request, HTTPException, status
from typing import Dict, Any, Callable

from src.infrastructure.exceptions import BaseServiceException, service_exception_handler
from src.infrastructure import get_service_factory as factory_getter
from src.adapters.cloud.actuators.water_pump import WaterPumpController
from src.core.control import IrrigationManager

logger = logging.getLogger(__name__)

async def get_service_factory(request: Request) -> Any:
    """
    Dependency để lấy ServiceFactory.
    
    Args:
        request: FastAPI request
        
    Returns:
        ServiceFactory instance
    """
    return factory_getter()

async def get_irrigation_manager(request: Request) -> IrrigationManager:
    """
    Dependency để lấy IrrigationManager.
    
    Args:
        request: FastAPI request
        
    Returns:
        IrrigationManager instance
    """
    return IrrigationManager()

async def get_water_pump_controller(request: Request) -> WaterPumpController:
    """
    Dependency để lấy WaterPumpController.
    
    Args:
        request: FastAPI request
        
    Returns:
        WaterPumpController instance
    """
    return WaterPumpController()

def handle_exceptions(func: Callable) -> Callable:
    """
    Decorator để xử lý exception từ service.
    
    Args:
        func: Function cần wrap
        
    Returns:
        Function đã được wrap
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BaseServiceException as exc:
            logger.error(f"Service exception: {exc.message}", exc_info=True)
            raise service_exception_handler(exc)
        except HTTPException:
            # Nếu đã là HTTP exception, chuyển tiếp
            raise
        except Exception as exc:
            logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "An unexpected error occurred",
                    "error": str(exc)
                }
            )
            
    return wrapper