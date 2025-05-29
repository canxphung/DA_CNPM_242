"""
Custom CORS middleware that defers to the API Gateway when needed.
"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

class GatewayAwareCORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware that checks if the API Gateway is already handling CORS.
    If the 'X-Backend-CORS-Handled' header is present, this middleware will
    skip adding CORS headers to avoid conflicts.
    """
    
    def __init__(
        self, 
        app,
        allow_origins=None,
        allow_methods=None,
        allow_headers=None,
        allow_credentials=False,
        expose_headers=None,
        max_age=600
    ):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        self.allow_headers = allow_headers or ["Authorization", "Content-Type", "Accept"]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age
        
    async def dispatch(self, request: Request, call_next):
        # Check if the API Gateway is handling CORS
        if request.headers.get("X-Backend-CORS-Handled") == "true":
            logger.debug(f"CORS handled by API Gateway for {request.url.path}")
            response = await call_next(request)
            return response
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(request, response)
            return response
            
        # Process the request and add CORS headers to the response
        response = await call_next(request)
        self._add_cors_headers(request, response)
        
        return response
    
    def _add_cors_headers(self, request: Request, response: Response):
        origin = request.headers.get("origin")
        
        # Skip if no origin (same-origin request)
        if not origin:
            return
            
        # Check if the origin is allowed
        if "*" in self.allow_origins or origin in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            
            # Add other CORS headers
            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
                
            if request.method == "OPTIONS":
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
                response.headers["Access-Control-Max-Age"] = str(self.max_age)
                
            if self.expose_headers:
                response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)