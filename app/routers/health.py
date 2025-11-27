from fastapi import APIRouter
from datetime import datetime
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.get("/config")
async def get_config():
    """Get current configuration (for debugging)."""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "model_name": settings.MODEL_NAME,
        "model_config": settings.MODEL_CONFIG,
        "ollama_api_url": settings.OLLAMA_API_URL,
        "llamacpp": {
            "model_source": settings.LLAMACPP_MODEL_SOURCE,
            "model_path": settings.LLAMACPP_MODEL_PATH,
            "n_ctx": settings.LLAMACPP_N_CTX,
            "n_gpu_layers": settings.LLAMACPP_N_GPU_LAYERS,
        }
    }

