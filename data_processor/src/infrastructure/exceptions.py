"""
Định nghĩa các exception tùy chỉnh cho ứng dụng.
"""
from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class BaseServiceException(Exception):
    """Base exception cho tất cả các service exception."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class ConfigurationError(BaseServiceException):
    """Exception khi gặp lỗi cấu hình."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="configuration_error",
            details=details
        )

class ConnectionError(BaseServiceException):
    """Exception khi gặp lỗi kết nối đến service bên ngoài."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["service"] = service_name
        super().__init__(
            message=message,
            error_code="connection_error",
            details=details
        )

class DataAccessError(BaseServiceException):
    """Exception khi gặp lỗi truy cập dữ liệu."""
    
    def __init__(
        self,
        message: str,
        source: str,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["source"] = source
        super().__init__(
            message=message,
            error_code="data_access_error",
            details=details
        )

class SensorError(BaseServiceException):
    """Exception khi gặp lỗi liên quan đến cảm biến."""
    
    def __init__(
        self,
        message: str,
        sensor_type: str,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["sensor_type"] = sensor_type
        super().__init__(
            message=message,
            error_code="sensor_error",
            details=details
        )

class ActuatorError(BaseServiceException):
    """Exception khi gặp lỗi liên quan đến cơ cấu chấp hành."""
    
    def __init__(
        self,
        message: str,
        actuator_type: str,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["actuator_type"] = actuator_type
        super().__init__(
            message=message,
            error_code="actuator_error",
            details=details
        )

class ValidationError(BaseServiceException):
    """Exception khi gặp lỗi validation."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            error_code="validation_error",
            details=details
        )

class SchedulingError(BaseServiceException):
    """Exception khi gặp lỗi lập lịch."""
    
    def __init__(
        self,
        message: str,
        schedule_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if schedule_id:
            details["schedule_id"] = schedule_id
        super().__init__(
            message=message,
            error_code="scheduling_error",
            details=details
        )

class ResourceNotFoundError(BaseServiceException):
    """Exception khi không tìm thấy tài nguyên."""
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(
            message=message,
            error_code="resource_not_found",
            details=details
        )

class OperationError(BaseServiceException):
    """Exception khi một thao tác thất bại."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["operation"] = operation
        super().__init__(
            message=message,
            error_code="operation_error",
            details=details
        )

# Hàm chuyển đổi service exception thành HTTP exception
def service_exception_handler(exc: BaseServiceException) -> HTTPException:
    """
    Chuyển đổi service exception thành HTTP exception.
    
    Args:
        exc: Service exception
        
    Returns:
        HTTPException: HTTP exception tương ứng
    """
    # Ánh xạ error_code sang status_code
    status_code_map = {
        "configuration_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "connection_error": status.HTTP_503_SERVICE_UNAVAILABLE,
        "data_access_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "sensor_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "actuator_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "validation_error": status.HTTP_400_BAD_REQUEST,
        "scheduling_error": status.HTTP_400_BAD_REQUEST,
        "resource_not_found": status.HTTP_404_NOT_FOUND,
        "operation_error": status.HTTP_400_BAD_REQUEST
    }
    
    status_code = status_code_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=status_code,
        detail={
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )