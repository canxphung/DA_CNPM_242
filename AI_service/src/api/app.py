# src/api/app.py
import os
import sys
import logging
from fastapi import FastAPI, Depends
import uvicorn

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.config import API_HOST, API_PORT
from src.core.greenhouse_ai_service import GreenhouseAIService
from src.api.error_handler import add_exception_handlers
from src.api.dependencies import get_greenhouse_service

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('api')

# Tải cấu hình
import config.config as app_config

# Create FastAPI app
app = FastAPI(
    title="Greenhouse AI Service API",
    description="API for the Smart Greenhouse AI Service",
    version="0.1.0",
)

# Add exception handlers
add_exception_handlers(app)


from src.api.chat_routes import router as chat_router
from src.api.recommendation_routes import router as recommendation_router
from src.api.sensor_routes import router as sensor_router
from src.api.analytics_routes import router as analytics_router


# Include routers
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(recommendation_router, prefix="/api/recommendation", tags=["recommendation"])
app.include_router(sensor_router, prefix="/api/sensors", tags=["sensors"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])

@app.on_event("startup")
async def startup_event():
    """Start the service when the API starts."""
    service = get_greenhouse_service()
    service.start()
    logger.info("Greenhouse AI Service started")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the service when the API stops."""
    service = get_greenhouse_service()
    await service.stop()
    logger.info("Greenhouse AI Service stopped")

@app.get("/", tags=["health"])
async def root():
    """Root endpoint for health check."""
    return {"status": "online", "service": "Greenhouse AI Service"}

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint with service stats."""
    service = get_greenhouse_service()
    return {
        "status": "healthy" if service.is_running else "not running",
        "stats": service.get_service_stats()
    }

def start():
    """Start the API server."""
    uvicorn.run(
        "src.api.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )

if __name__ == "__main__":
    start()