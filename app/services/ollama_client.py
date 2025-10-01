import httpx
import logging
import json
import time
from typing import Dict, Optional, AsyncGenerator, Any
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.api_url = settings.OLLAMA_API_URL
        self.model_config = settings.MODEL_CONFIG
        
    async def generate_stream(self, content: str, temperature: float = 0.15, max_tokens: int = 400, 
                            top_p: float = 0.8, top_k: int = 30, repeat_penalty: float = 1.05) -> AsyncGenerator[Dict[str, Any], None]:
        """Make streaming API call to Ollama with structured response format."""
        payload = {
            "model": settings.MODEL_NAME,
            "prompt": content,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
                "top_k": top_k,
                "repeat_penalty": repeat_penalty
            }
        }
        
        timeout = httpx.Timeout(120.0)
        request_id = f"req_{hash(content)}_{int(time.time())}"
        accumulated_response = ""
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", self.api_url, json=payload) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                
                                # Handle token chunks
                                if "response" in data and not data.get("done", False):
                                    token_content = data["response"]
                                    accumulated_response += token_content
                                    
                                    yield {
                                        "type": "token",
                                        "content": token_content,
                                        "accumulated": accumulated_response,
                                        "request_id": request_id
                                    }
                                
                                # Handle final response
                                elif data.get("done", False):
                                    yield {
                                        "type": "final",
                                        "content": accumulated_response,
                                        "request_id": request_id,
                                        "total_duration": data.get("total_duration"),
                                        "load_duration": data.get("load_duration"),
                                        "prompt_eval_count": data.get("prompt_eval_count"),
                                        "eval_count": data.get("eval_count")
                                    }
                                    break
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse JSON line: {line} - Error: {e}")
                                continue
                                
        except httpx.TimeoutException:
            logger.error("Model request timed out for request_id: %s", request_id)
            yield {
                "type": "error",
                "content": "Model request timed out",
                "request_id": request_id,
                "error_code": "timeout"
            }
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error for request_id %s: %s", request_id, e)
            yield {
                "type": "error",
                "content": f"Model API error: {e.response.status_code} - {e.response.text}",
                "request_id": request_id,
                "error_code": "http_error",
                "status_code": e.response.status_code
            }
        except Exception as e:
            logger.error("Unexpected error calling model for request_id %s: %s", request_id, e)
            yield {
                "type": "error",
                "content": f"Model call failed: {str(e)}",
                "request_id": request_id,
                "error_code": "unexpected_error"
            }

    async def generate(self, prompt: str, config: Optional[Dict] = None) -> str:
        """Make async API call to Ollama."""
        if config is None:
            config = self.model_config
            
        payload = {
            "model": settings.MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": config
        }
        
        timeout = httpx.Timeout(120.0)
        request_id = f"req_{hash(prompt)}_{int(time.time())}"
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Making non-streaming request {request_id} to model {settings.MODEL_NAME}")
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                result = response.json()
                
                response_text = result.get("response", "").strip()
                logger.info(f"Non-streaming request {request_id} completed successfully, response length: {len(response_text)}")
                
                return response_text
                
        except httpx.TimeoutException:
            logger.error("Model request timed out for request_id: %s", request_id)
            raise HTTPException(status_code=504, detail="Model request timed out")
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error for request_id %s: %s - %s", request_id, e.response.status_code, e.response.text)
            raise HTTPException(status_code=502, detail=f"Model API error: {e.response.status_code}")
        except Exception as e:
            logger.error("Unexpected error calling model for request_id %s: %s", request_id, e)
            raise HTTPException(status_code=500, detail=f"Model call failed: {str(e)}")

    async def generate_with_parameters(self, prompt: str, temperature: float = 0.15, 
                                     max_tokens: int = 400, top_p: float = 0.8, 
                                     top_k: int = 30, repeat_penalty: float = 1.05) -> str:
        """Generate response with specific parameters."""
        config = {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repeat_penalty
        }
        return await self.generate(prompt, config)

# Global client instance
ollama_client = OllamaClient()

# Convenience functions
async def call_model_stream_async(prompt: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
    """Convenience function for streaming model calls with parameter support"""
    async for chunk in ollama_client.generate_stream(prompt, **kwargs):
        yield chunk

async def call_model_async(prompt: str, config: Optional[Dict] = None) -> str:
    """Convenience function for non-streaming model calls"""
    return await ollama_client.generate(prompt, config)

async def call_model_with_params_async(prompt: str, **kwargs) -> str:
    """Convenience function for model calls with specific parameters"""
    return await ollama_client.generate_with_parameters(prompt, **kwargs)
