"""
API routes for DCC Model API
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.models.schemas import GenerateRequest, GenerateResponse, HealthResponse
from app.services.ollama_service import ollama_service
from app.core.logging_config import get_logger
import json

logger = get_logger(__name__)
router = APIRouter()


def get_ollama_service():
    """Dependency to get Ollama service instance"""
    return ollama_service


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        logger.info("Health check requested")
        health_data = await ollama_service.health_check()
        
        return HealthResponse(**health_data)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate badge metadata from course content"""
    try:
        logger.info(f"Generate request received - Content length: {len(request.content)}")
        
        # Generate response
        result = await ollama_service.generate(
            content=request.content,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            top_k=request.top_k,
            repeat_penalty=request.repeat_penalty
        )
        
        logger.info("Generation completed successfully")
        return GenerateResponse(**result)
        
    except Exception as e:
        logger.error(f"Generate request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generate request failed: {e}")


@router.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    """Generate badge metadata with streaming response"""
    try:
        logger.info(f"Streaming generate request received - Content length: {len(request.content)}")
        
        async def generate_stream_response():
            try:
                async for chunk in ollama_service.generate_stream(
                    content=request.content,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                    top_k=request.top_k,
                    repeat_penalty=request.repeat_penalty
                ):
                    # Format as Server-Sent Events
                    data = json.dumps(chunk)
                    yield f"data: {data}\n\n"
                    
            except Exception as e:
                logger.error(f"Streaming generation failed: {e}")
                error_chunk = {
                    "type": "error",
                    "content": f"Streaming generation failed: {e}"
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming request setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Streaming request setup failed: {e}")
