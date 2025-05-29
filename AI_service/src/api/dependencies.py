# src/api/dependencies.py
"""
Module quản lý dependencies chung cho API.
Giải quyết vấn đề circular import bằng cách tập trung dependencies.
"""
from typing import Generator
from src.core.greenhouse_ai_service import GreenhouseAIService

# Instance duy nhất của service (Singleton pattern)
_greenhouse_service = None

def get_greenhouse_service() -> GreenhouseAIService:
    """
    Lấy instance của GreenhouseAIService.
    Sử dụng lazy initialization để tránh tạo service khi import.
    """
    global _greenhouse_service
    if _greenhouse_service is None:
        # Import config ở đây để tránh circular import
        import config.config as app_config
        _greenhouse_service = GreenhouseAIService(config=app_config)
    return _greenhouse_service

def get_service() -> GreenhouseAIService:
    """
    Dependency function cho FastAPI.
    Returns instance của GreenhouseAIService.
    """
    return get_greenhouse_service()