from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.routers import badges, health
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.core.config import settings
from app.services.ollama_client import preload_model
from app.services.skill_extractor import skill_service
import logging
import json
import time

logger = logging.getLogger(__name__)

# ============================================================================
# Request Logging Middleware
# ============================================================================
async def log_requests_middleware(request: Request, call_next):
    """
    Middleware to log all incoming API requests in a systematic format.
    Captures method, path, headers, query parameters, and body.
    """
    start_time = time.time()
    
    # Read request body (for POST/PUT requests)
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body = json.loads(body_bytes.decode('utf-8'))
                except json.JSONDecodeError:
                    body = body_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Could not read request body: {e}")
            body = "<unable to read body>"
    
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
      request.body            {json.dumps(body, indent=1) if body else "{}"}
      <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"""
    )
    
    # Process the request
    response = await call_next(request)
    
    # Log response time
    process_time = time.time() - start_time
    logger.info(f"Request completed in {process_time:.4f}s | Status: {response.status_code}")
    logger.info('==============================================================')
    
    return response

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
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    return await log_requests_middleware(request, call_next)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

    