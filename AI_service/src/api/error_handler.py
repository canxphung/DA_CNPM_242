# src/api/error_handler.py
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Set up logging
logger = logging.getLogger('error_handler')

async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors()
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )

def add_exception_handlers(app: FastAPI):
    """Add exception handlers to the FastAPI app."""
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)