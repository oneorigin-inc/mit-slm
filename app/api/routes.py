"""
API routes for DCC Model API - MCS Architecture (Function-based)
"""
from fastapi import APIRouter
from app.models.schemas import GenerateRequest, GenerateResponse, HealthResponse
from app.controllers import (
    generate_badge_suggestions,
    generate_badge_suggestions_stream,
    health_check
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check_endpoint():
    """Health check endpoint"""
    return await health_check()


@router.post("/generate-badge-suggestions", response_model=GenerateResponse)
async def generate_badge_suggestions_endpoint(request: GenerateRequest):
    """Generate badge suggestions from course content"""
    return await generate_badge_suggestions(request)


@router.post("/generate-badge-suggestions/stream")
async def generate_badge_suggestions_stream_endpoint(request: GenerateRequest):
    """Generate badge suggestions with streaming response"""
    return await generate_badge_suggestions_stream(request)
