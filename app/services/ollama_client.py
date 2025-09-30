import httpx
import logging
from typing import Dict, Optional
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.api_url = settings.OLLAMA_API_URL
        self.model_config = settings.MODEL_CONFIG
        
    async def generate(self, prompt: str, config: Optional[Dict] = None) -> str:
        """Make async API call to Ollama."""
        if config is None:
            config = self.model_config
            
        payload = {
            "model": settings.MODEL_NAME,
            "prompt": prompt,
            "stream": True,
            **config
        }
        
        timeout = httpx.Timeout(120.0)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip()
        except httpx.TimeoutException:
            logger.error("Model request timed out")
            raise HTTPException(status_code=504, detail="Model request timed out")
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error: %s", e)
            raise HTTPException(status_code=502, detail=f"Model API error: {e}")
        except Exception as e:
            logger.error("Unexpected error calling model: %s", e)
            raise HTTPException(status_code=500, detail=f"Model call failed: {e}")

# Global client instance
ollama_client = OllamaClient()

async def call_model_async(prompt: str, config: dict = None) -> str:
    """Convenience function for model calls"""
    return await ollama_client.generate(prompt, config)

