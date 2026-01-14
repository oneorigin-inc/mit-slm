from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

async def check_ollama_model_status() -> dict:
    """
    Check if Ollama model is available using the tags API.
    
    Returns:
        dict with status information about the Ollama model
    """
    try:
        # Get Ollama base URL from settings
        ollama_base_url = settings.OLLAMA_API_URL.replace('/api/generate', '')
        model_name = settings.MODEL_NAME
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check available models using tags API
            try:
                tags_response = await client.get(f"{ollama_base_url}/api/tags")
                tags_response.raise_for_status()
                tags_data = tags_response.json()
                
                # Check if our model is in the available models list
                model_available = False
                model_info = None
                
                if "models" in tags_data:
                    for model in tags_data["models"]:
                        if model.get("name") == model_name:
                            model_available = True
                            model_info = {
                                "name": model.get("name"),
                                "size": model.get("size", 0),
                                "modified_at": model.get("modified_at"),
                                "digest": model.get("digest", "")[:12] if model.get("digest") else None
                            }
                            break
                
                return {
                    "available": True,
                    "model_available": model_available,
                    "model_name": model_name,
                    "model_info": model_info,
                    "ollama_url": ollama_base_url
                }
            except httpx.HTTPStatusError as e:
                logger.warning(f"Ollama tags API returned error: {e}")
                return {
                    "available": False,
                    "model_available": False,
                    "model_name": model_name,
                    "error": f"Ollama API error: {e.response.status_code}"
                }
                
    except httpx.ConnectError as e:
        logger.warning(f"Cannot connect to Ollama service: {e}")
        return {
            "available": False,
            "model_available": False,
            "model_name": model_name,
            "error": "Cannot connect to Ollama service"
        }
    except Exception as e:
        logger.error(f"Error checking Ollama status: {e}", exc_info=True)
        return {
            "available": False,
            "model_available": False,
            "model_name": model_name,
            "error": str(e)
        }

@router.get("/health")
async def health_check():
    """
    Health check endpoint that verifies:
    - Service is running
    - Ollama model is loaded and available
    
    Note: Logging for this endpoint is suppressed to reduce log noise.
    """
    # Use DEBUG level to reduce log noise (filtered by HealthCheckFilter)
    logger.debug("Health check endpoint called")
    
    # Check Ollama model status using tags API
    ollama_status = await check_ollama_model_status()
    
    # Determine overall health status
    if ollama_status.get("available") and ollama_status.get("model_available"):
        status = "healthy"
        status_code = 200
        message = f"Service is healthy. Ollama model '{ollama_status['model_name']}' is available."
    elif ollama_status.get("available") and not ollama_status.get("model_available"):
        status = "degraded"
        status_code = 200  # Still return 200 but indicate degraded state
        message = f"Service is running but Ollama model '{ollama_status['model_name']}' is not available in Ollama."
    else:
        status = "unhealthy"
        status_code = 503
        message = f"Service is unhealthy. Ollama service is not available: {ollama_status.get('error', 'Unknown error')}"
    
    response = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "ollama": {
            "available": ollama_status.get("available", False),
            "model_available": ollama_status.get("model_available", False),
            "model_name": ollama_status.get("model_name"),
            "model_info": ollama_status.get("model_info")
        }
    }
    
    # Use DEBUG level to reduce log noise (filtered by HealthCheckFilter)
    logger.debug(f"Health check response: status={status}, ollama_available={ollama_status.get('available')}, model_available={ollama_status.get('model_available')}")
    
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=response)
    
    return response

