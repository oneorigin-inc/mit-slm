from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import badges, health
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.core.config import settings
from app.services.ollama_client import preload_model
from app.services.skill_extractor import skill_service
import logging
import json
import time
import copy

logger = logging.getLogger(__name__)

# ============================================================================
# Request Logging Middleware (Production-Ready Implementation)
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Production-ready middleware for logging incoming API requests.
    Uses proper BaseHTTPMiddleware pattern to handle request body without consuming the stream.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Middleware dispatch method that logs requests and responses.
        Properly handles request body by caching it in an ASGI-compliant way.
        """
        start_time = time.time()
        
        # Read and cache request body for logging
        body = None
        body_bytes = b''
        
        # Get content type
        content_type = request.headers.get("content-type", "")
        
        # Skip body reading for multipart/form-data (file uploads)
        # These requests have streams that can't be cached properly
        if request.method in ["POST", "PUT", "PATCH"] and not content_type.startswith("multipart/form-data"):
            try:
                # Read the body bytes
                body_bytes = await request.body()
                
                if body_bytes:
                    try:
                        body = json.loads(body_bytes.decode('utf-8'))
                        # Remove base64 data from logs to keep them clean
                        if isinstance(body, dict):
                            body = self._sanitize_body_for_logging(body)
                    except json.JSONDecodeError:
                        body = body_bytes.decode('utf-8', errors='ignore')
                else:
                    body = None
                
                # CRITICAL FIX: Always restore the body stream (even if empty)
                # This ensures FastAPI/Pydantic can read the body after middleware
                # The receive function must be set regardless of whether body_bytes is empty
                # Capture body_bytes in closure
                cached_body = body_bytes
                async def receive():
                    return {"type": "http.request", "body": cached_body, "more_body": False}
                
                # Replace request's receive with cached version (proper ASGI pattern)
                request._receive = receive
                logger.debug(f"Body stream restored: {len(cached_body)} bytes cached for FastAPI")
                    
            except Exception as e:
                logger.warning(f"Could not read request body: {e}")
                body = "<unable to read body>"
                # Even on error, restore the stream with empty body
                async def receive():
                    return {"type": "http.request", "body": b"", "more_body": False}
                request._receive = receive
        elif content_type.startswith("multipart/form-data"):
            # For file uploads, just log that it's a multipart request
            body = "<multipart/form-data - file upload>"
        
        # Convert headers to dict for logging (exclude sensitive data if needed)
        headers_dict = dict(request.headers)
        
        # Convert query params to dict
        query_dict = dict(request.query_params)
        
        # Log the incoming request
        logger.info('==============================================================')
        logger.info(
            f"""Network incoming logs >>>
          >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
          request.method          {request.method}
          request.path            {request.url.path}
          request.headers         {json.dumps(headers_dict, indent=1)}
          request.query           {json.dumps(query_dict, indent=1)}
          request.body            {json.dumps(body, indent=1) if isinstance(body, dict) else str(body) if body else "{}"}
          <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"""
        )
        
        # Process the request with proper exception handling
        try:
            logger.info(f"Forwarding request to route handler: {request.method} {request.url.path}")
            response = await call_next(request)
            
            # Log response time
            process_time = time.time() - start_time
            logger.info(f"Request completed in {process_time:.4f}s | Status: {response.status_code}")
            logger.info('==============================================================')
            
            return response
        except Exception as e:
            # Log any exceptions that occur during request processing
            process_time = time.time() - start_time
            logger.error(f"Request failed after {process_time:.4f}s | Error: {type(e).__name__}: {str(e)}", exc_info=True)
            logger.info('==============================================================')
            # Re-raise the exception so FastAPI can handle it properly
            raise
    
    def _sanitize_body_for_logging(self, body: dict) -> dict:
        """
        Remove base64 encoded data from request body for cleaner logs.
        Uses deep copy to avoid modifying the original request body.
        Controlled by ENABLE_LOG_BASE64_DATA config flag.
        """
        # If base64 logging is enabled, return body as-is
        if settings.ENABLE_LOG_BASE64_DATA:
            return body
        
        # Deep copy to ensure we don't modify the original
        sanitized = copy.deepcopy(body)
        
        # Recursively sanitize base64 fields
        self._sanitize_base64_fields(sanitized)
        
        return sanitized
    
    def _sanitize_base64_fields(self, obj: Any) -> None:
        """
        Recursively sanitize base64-encoded fields in the object.
        Modifies the object in-place.
        
        Removes base64 data from fields that:
        - Contain 'logo' in the field name
        - Contain 'base64' in the field name
        - Contain 'image' in the field name and have large string values
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check if field name suggests base64 data
                key_lower = key.lower()
                is_base64_field = any(keyword in key_lower for keyword in ['logo', 'base64', 'image'])
                
                # If it's a string value in a base64-related field
                if is_base64_field and isinstance(value, str):
                    # Check if it looks like base64 (long string, typically > 100 chars)
                    if len(value) > 100:
                        obj[key] = "<base64_data_excluded_from_log>"
                # Recursively sanitize nested structures
                elif isinstance(value, (dict, list)):
                    self._sanitize_base64_fields(value)
        
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    self._sanitize_base64_fields(item)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await preload_model()

    # Initialize LAiSER skill extractor (available for per-request use)
    try:
        logger.info("Initializing LAiSER skill extractor...")
        await skill_service.initialize(
            ai_model_id=settings.LAISER_MODEL_ID,
            hf_token=settings.LAISER_HF_TOKEN,
            use_gpu=settings.LAISER_USE_GPU
        )
        logger.info("LAiSER initialization complete.")
    except Exception as e:
        logger.warning(f"LAiSER initialization failed: {e}. Skill extraction will be unavailable for all requests.")

    yield
    # Shutdown (if needed)

app = FastAPI(title="Badge Generator API", version="1.0.0", lifespan=lifespan)

# Setup logging
setup_logging()

# Include routers
app.include_router(badges.router, prefix="/api/v1")
app.include_router(health.router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware (applies to all routes)
# Using BaseHTTPMiddleware for proper ASGI compliance and scalability
app.add_middleware(RequestLoggingMiddleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

    