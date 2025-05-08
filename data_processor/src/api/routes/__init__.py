"""
Đăng ký tất cả API routes.
"""

def register_routes(app):
    """
    Đăng ký tất cả routes API với ứng dụng FastAPI.
    
    Args:
        app: Đối tượng FastAPI app
    """
    # Import routes ở đây để tránh circular import
    from .sensor_routes import router as sensor_router
    from .control_routes import router as control_router
    from .system_routes import router as system_router
    
    # Đăng ký routers với ứng dụng
    app.include_router(sensor_router, prefix="/api/sensors", tags=["sensors"])
    app.include_router(control_router, prefix="/api/control", tags=["control"])
    app.include_router(system_router, prefix="/api/system", tags=["system"])