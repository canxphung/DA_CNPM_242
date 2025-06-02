"""
Điểm vào chính của ứng dụng Core Operations Service.
"""
import uvicorn
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, Request
# IMPORTANT: Comment out or remove this import to avoid conflicts
# from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Import our custom CORS middleware
from src.infrastructure.middlewares.cors_middleware import GatewayAwareCORSMiddleware

from src.api.routes import register_routes
from src.infrastructure.logging import setup_logging
from src.infrastructure import get_service_factory
from src.core.data import DataManager
from src.core.control import IrrigationManager
from src.infrastructure.database.connections import init_database_connections
from fastapi import FastAPI
from src.infrastructure.middlewares.cors_middleware import GatewayAwareCORSMiddleware

# Tải biến môi trường từ .env
load_dotenv()

# Thiết lập logging
setup_logging()
logger = logging.getLogger(__name__)

# Đọc thông tin phiên bản từ biến môi trường
VERSION = os.getenv("API_VERSION", "0.1.0")
ENV = os.getenv("ENVIRONMENT", "development")

# Tạo lifespan context manager thay thế cho on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Xử lý vòng đời của ứng dụng (startup và shutdown)."""
    # Startup
    logger.info("Application starting up")
    
    # Khởi tạo các kết nối database (đợi cho nó hoàn thành)
    await init_database_connections()
    
    # Khởi tạo tất cả các service
    factory = get_service_factory()
    factory.init_all_services()
    
    # Khởi tạo các feed Adafruit cần thiết
    # Khởi tạo các feed Adafruit cần thiết
    logger.info("Initializing required Adafruit IO feeds")
    adafruit_client = factory.create_adafruit_client()

    # Lấy tên feed thực từ config
    config = factory.get_config_loader()
    required_feeds = [
        config.get('adafruit.sensor_feeds.light'),
        config.get('adafruit.sensor_feeds.temperature'), 
        config.get('adafruit.sensor_feeds.humidity'),
        config.get('adafruit.sensor_feeds.soil_moisture'),
        config.get('adafruit.actuator_feeds.water_pump')
    ]

    # Lọc bỏ None values
    required_feeds = [f for f in required_feeds if f]

    adafruit_client.initialize_feeds(required_feeds)
    
    # QUAN TRỌNG: Đăng ký routes sau khi các kết nối đã được khởi tạo
    register_routes(app)
    
    # Khởi tạo DataManager và bắt đầu thu thập dữ liệu ngầm
    data_manager = DataManager()
    # Lấy interval từ cấu hình mới
    collection_interval = factory.get_config_loader().get_interval('sensor_data', 180)
    data_manager.start_background_collection(interval=collection_interval)
    logger.info(f"Started optimized background collection (interval: {collection_interval}s)")
    
    # Log performance config
    logger.info("Performance optimizations enabled:")
    logger.info("- Cache-first strategy: ENABLED")
    logger.info("- Rate limiting: 30s minimum between Adafruit calls")
    logger.info("- Stale-while-revalidate: ENABLED")
    
    # yield
    
    # Khởi động hệ thống tưới
    try:
        irrigation_manager = IrrigationManager()
        result = irrigation_manager.start_system()
        
        if result["success"]:
            logger.info("Irrigation system started successfully")
        else:
            logger.warning(f"Irrigation system started with warnings: {result}")
    except Exception as e:
        logger.error(f"Error starting irrigation system: {str(e)}")
    
    # Tiếp tục xử lý request    
    yield
    
    # Shutdown
    logger.info("Application shutting down")
    
    # Dừng thu thập dữ liệu ngầm
    data_manager = DataManager()
    data_manager.stop_background_collection()
    logger.info("Stopped background data collection")
    
    # Dừng hệ thống tưới
    try:
        irrigation_manager = IrrigationManager()
        result = irrigation_manager.stop_system()
        
        if result["success"]:
            logger.info("Irrigation system stopped successfully")
        else:
            logger.warning(f"Irrigation system stopped with warnings: {result}")
    except Exception as e:
        logger.error(f"Error stopping irrigation system: {str(e)}")

# app = FastAPI()
# app.add_middleware(GatewayAwareCORSMiddleware)
# Tạo ứng dụng FastAPI với metadata chi tiết hơn
app = FastAPI(
    title="Core Operations Service",
    description="""
    Microservice để thu thập dữ liệu cảm biến và điều khiển hệ thống tưới tự động.
    
    ## Tính năng chính
    
    * Thu thập dữ liệu từ các cảm biến (ánh sáng, nhiệt độ, độ ẩm, độ ẩm đất)
    * Phân tích môi trường và đưa ra khuyến nghị tưới
    * Điều khiển máy bơm nước (thủ công, theo lịch, tự động)
    * Lập lịch tưới theo thời gian
    * Hệ thống ra quyết định tự động dựa trên phân tích dữ liệu
    
    ## Thiết bị hỗ trợ
    
    * Cảm biến ánh sáng
    * Cảm biến nhiệt độ-độ ẩm DHT20
    * Cảm biến độ ẩm đất
    * Máy bơm nước
    
    ## Lưu trữ dữ liệu
    
    * Redis (cache và dữ liệu tạm thời)
    * Firebase (lưu trữ dài hạn)
    
    ## Tích hợp
    
    * Dữ liệu từ cảm biến được lấy từ Adafruit IO
    * Điều khiển máy bơm qua Adafruit IO
    """,
    version=VERSION,
    contact={
        "name": "Your Name",
        "email": "your.email@example.com",
    },
    license_info={
        "name": "MIT",
    },
    docs_url=None,  # Tắt docs mặc định để tùy chỉnh
    redoc_url=None,  # Tắt redoc mặc định
    lifespan=lifespan,  # Thêm lifespan context manager
)

# REMOVED: Default CORS middleware

# ADDED: Custom CORS middleware that's aware of the API Gateway
app.add_middleware(
    GatewayAwareCORSMiddleware,
    allow_origins=["*"],  # Trong môi trường production, chỉ định rõ các origin được phép
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-CSRF-Token", "X-Requested-With", "Origin", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Proxied-By"]
)

# Tùy chỉnh OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Thêm thông tin phiên bản
    openapi_schema["info"]["x-api-version"] = VERSION
    openapi_schema["info"]["x-environment"] = ENV
    
    # Thêm tags để nhóm các API
    openapi_schema["tags"] = [
        {
            "name": "sensors",
            "description": "Endpoints liên quan đến dữ liệu cảm biến và phân tích môi trường"
        },
        {
            "name": "control",
            "description": "Endpoints liên quan đến điều khiển hệ thống tưới"
        },
        {
            "name": "system",
            "description": "Endpoints liên quan đến trạng thái và quản lý hệ thống"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Tùy chỉnh trang docs
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
    )

# NEW: Add debug endpoint for CORS testing
@app.get("/debug/headers", tags=["debug"])
async def debug_headers(request: Request):
    """Debug endpoint that returns all request headers."""
    return {
        "request_headers": dict(request.headers),
        "cors_handled_by_gateway": request.headers.get("X-Backend-CORS-Handled") == "true",
        "origin": request.headers.get("origin", "No origin header")
    }

# Tạo route thông tin phiên bản
@app.get("/version", tags=["system"])
async def get_version():
    """Lấy thông tin phiên bản của API."""
    return {
        "version": VERSION,
        "environment": ENV,
        "build_date": os.getenv("BUILD_DATE", "unknown"),
        "commit_hash": os.getenv("COMMIT_HASH", "unknown")
    }

# Tạo route chính
@app.get("/", tags=["system"])
async def root():
    """Route chính."""
    return {
        "service": "Core Operations Service",
        "status": "running",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["system"])
async def health_check():
    """Kiểm tra trạng thái hoạt động của service."""
    try:
        # Kiểm tra DataManager
        data_manager = DataManager()
        latest_readings = data_manager.get_latest_readings()
        
        # Kiểm tra IrrigationManager
        irrigation_manager = IrrigationManager()
        system_status = irrigation_manager.get_system_status()
        
        # Kiểm tra tất cả các kết nối cần thiết
        factory = get_service_factory()
        redis_client = factory.create_redis_client()
        adafruit_client = factory.create_adafruit_client()
        
        # Kiểm tra Redis
        redis_ok = redis_client.exists("test_key") is not None
        
        # Kiểm tra Adafruit
        adafruit_feeds = None
        try:
            adafruit_feeds = adafruit_client.client.feeds()
            adafruit_ok = True
        except Exception:
            adafruit_ok = False
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": VERSION,
            "sensors": {
                "available": len(latest_readings),
                "status": "ok" if len(latest_readings) > 0 else "warning"
            },
            "irrigation": {
                "pump_status": system_status["pump"]["is_on"],
                "auto_irrigation": system_status["auto_irrigation"]["enabled"],
                "schedules_count": system_status["scheduler"]["schedules_count"]
            },
            "connections": {
                "redis": "ok" if redis_ok else "error",
                "adafruit": "ok" if adafruit_ok else "error",
                "adafruit_feeds": len(adafruit_feeds) if adafruit_feeds else 0
            }
        }
        
        # Xác định HTTP status code
        if (not redis_ok or not adafruit_ok or len(latest_readings) == 0):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_status
            )
            
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    logger.info(f"Starting server at http://{host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True  # Bật tính năng tự động tải lại (development only)
    )