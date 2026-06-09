import httpx
import logging
import json
import time
from typing import Dict, Optional, AsyncGenerator, Any
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_metrics(ollama_response: Dict[str, Any]) -> Dict[str, Optional[int]]:
    """Extract metrics from Ollama API response."""
    return {
        "total_duration": ollama_response.get("total_duration"),
        "load_duration": ollama_response.get("load_duration"),
        "prompt_eval_count": ollama_response.get("prompt_eval_count"),
        "prompt_eval_duration": ollama_response.get("prompt_eval_duration"),
        "eval_count": ollama_response.get("eval_count"),
        "eval_duration": ollama_response.get("eval_duration")
    }

class OllamaClient:
    def __init__(self):
        self.api_url = settings.OLLAMA_API_URL
        self.model_config = settings.MODEL_CONFIG

    async def generate_stream(
        self, 
        content: str, 
        temperature: float = 0.10, 
        max_tokens: int = 1024,
        top_p: float = 0.9, 
        top_k: int = 50, 
        repeat_penalty: float = 1.05,
        context_length: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Make streaming API call to Ollama with structured response format."""
        
        # Use user context length or default from model config
        max_ctx_len = self.model_config.get("num_ctx", 4096)
        ctx_len = context_length if context_length is not None else max_ctx_len
        
        payload = {
            "model": settings.MODEL_NAME,
            "prompt": content,
            "stream": True,
            "keep_alive": "24h",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": top_p,
                "top_k": top_k,
                "repeat_penalty": repeat_penalty,
                "num_ctx": ctx_len
            }
        }

        timeout = httpx.Timeout(300.0)
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
                                    # Extract metrics
                                    metrics = extract_metrics(data)
                                    
                                    # Log metrics
                                    prompt_count = metrics.get("prompt_eval_count") or 0
                                    eval_count = metrics.get("eval_count") or 0
                                    logger.info(
                                        f"Ollama metrics [{request_id}]: "
                                        f"prompt_eval_count={prompt_count}, "
                                        f"eval_count={eval_count}, "
                                        f"total={prompt_count + eval_count}"
                                    )
                                    yield {
                                        "type": "final",
                                        "content": accumulated_response,
                                        "request_id": request_id,
                                        "metrics": metrics

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

    async def generate(self, prompt: str, config: Optional[Dict] = None) -> tuple[str, Dict[str, Any]]:
        """Make async API call to Ollama. Returns (response_text, metrics)."""
        if config is None:
            config = self.model_config.copy()
        else:
            config = config.copy()

        # Keep alive default or from config
        keep_alive = config.pop("keep_alive", "6h")

        # Set default context length if not provided
        if "num_ctx" not in config:
            config["num_ctx"] = self.model_config.get("num_ctx", 2048)

        payload = {
            "model": settings.MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": config
        }

        timeout = httpx.Timeout(300.0)
        request_id = f"req_{hash(prompt)}_{int(time.time())}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Making non-streaming request {request_id} to model {settings.MODEL_NAME} with keep_alive={keep_alive}")
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                result = response.json()

                response_text = result.get("response", "").strip()
                # Extract metrics
                metrics = extract_metrics(result)
                
                # Log metrics
                prompt_count = metrics.get("prompt_eval_count") or 0
                eval_count = metrics.get("eval_count") or 0
                logger.info(
                    f"Non-streaming request {request_id} completed. "
                    f"Response length: {len(response_text)}, "
                    f"Ollama metrics: prompt_eval_count={prompt_count}, "
                    f"eval_count={eval_count}, total={prompt_count + eval_count}"
                )
                
                return response_text, metrics
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
                                       top_k: int = 30, repeat_penalty: float = 1.05, 
                                       context_length: Optional[int] = None) -> tuple[str, Dict[str, Any]]:
        """Generate response with specific parameters."""
        config = {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repeat_penalty,
        }

        if context_length is not None:
            config["num_ctx"] = context_length

        response_text, metrics = await self.generate(prompt, config)
        return response_text, metrics
    
    def get_metrics_from_stream(self, stream_chunks: list) -> Optional[Dict[str, Any]]:
        """
        Extract metrics from a completed stream.
        
        Args:
            stream_chunks: List of chunks from a completed stream
            
        Returns:
            Metrics dictionary if found, None otherwise
        """
        for chunk in reversed(stream_chunks):  # Look for final chunk
            if chunk.get("type") == "final" and "metrics" in chunk:
                return chunk["metrics"]
        return None

# Global client instance
ollama_client = OllamaClient()

# Convenience functions
async def call_model_stream_async(prompt: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
    """Convenience function for streaming model calls with parameter support"""
    async for chunk in ollama_client.generate_stream(prompt, **kwargs):
        yield chunk

async def call_model_async(prompt: str, config: Optional[Dict] = None) -> tuple[str, Dict[str, Any]]:
    """Convenience function for non-streaming model calls. Returns (response_text, metrics)."""
    return await ollama_client.generate(prompt, config)

async def call_model_with_params_async(prompt: str, **kwargs) -> tuple[str, Dict[str, Any]]:
    """Convenience function for model calls with specific parameters. Returns (response_text, metrics)."""
    return await ollama_client.generate_with_parameters(prompt, **kwargs)

async def preload_model() -> bool:
    """Preload the model into memory using streaming to minimize resource usage"""
    try:
        logger.info(f"Preloading model {settings.MODEL_NAME}...")
        # Use streaming with a minimal prompt to load model
        async for chunk in ollama_client.generate_stream("test", max_tokens=1):
            if chunk.get("type") == "final":
                logger.info(f"Model {settings.MODEL_NAME} preloaded successfully")
                return True
            elif chunk.get("type") == "error":
                logger.error(f"Failed to preload model: {chunk.get('content')}")
                return False
        return True
    except Exception as e:
        logger.error(f"Model preload failed: {e}")
        return False
