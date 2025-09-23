"""
Main FastAPI application for DCC Model API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_config
from app.core.logging_config import setup_logging
from app.api.routes import router
import uvicorn

# Setup logging
logger = setup_logging()

# Get configuration
config = get_config()

# Create FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description="API for generating Open Badges 3.0 compliant metadata from course content"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes with versioning
app.include_router(router, prefix="/api/v1", tags=["api-v1"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DCC Model API",
        "version": config.API_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "generate_badge_suggestions": "/api/v1/generate-badge-suggestions",
        "generate_badge_suggestions_stream": "/api/v1/generate-badge-suggestions/stream"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )