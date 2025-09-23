# Ollama Service with Multiplexing Support
# This is the service layer for external Ollama API integration with HTTP/2 multiplexing

import asyncio
import json
import re
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from asyncio import Queue, Lock, Semaphore
from app.core.config import get_config
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class OllamaService:
    """Service layer for external Ollama API integration with HTTP/2 multiplexing support"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.config = get_config()
            self.base_url = self.config.OLLAMA_URL
            self.model_name = self.config.MODEL_NAME
            self.system_prompt = self.config.load_system_prompt()
            
            # Multiplexing configuration
            self.max_concurrent_requests = self.config.MAX_CONCURRENT_REQUESTS
            self.enable_multiplexing = self.config.ENABLE_MULTIPLEXING
            self.semaphore = Semaphore(self.max_concurrent_requests)
            self.request_counter = 0
            self.active_requests = 0
            
            # Connection pool for better performance
            self.client_pool = None
            self._initialized = True
            
            logger.info(f"OllamaService initialized with {self.max_concurrent_requests} concurrent requests (multiplexing: {self.enable_multiplexing})")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self.client_pool is None:
            # Create client with connection pooling and keep-alive
            timeout_config = httpx.Timeout(
                connect=30.0,
                read=300.0,
                write=30.0,
                pool=30.0
            )
            
            limits = httpx.Limits(
                max_keepalive_connections=self.config.CONNECTION_POOL_SIZE,
                max_connections=self.config.CONNECTION_POOL_SIZE * 2,
                keepalive_expiry=self.config.KEEPALIVE_TIMEOUT
            )
            
            # Try to enable HTTP/2, fallback to HTTP/1.1 if not available
            try:
                self.client_pool = httpx.AsyncClient(
                    timeout=timeout_config,
                    limits=limits,
                    http2=True  # Enable HTTP/2 for better multiplexing
                )
                logger.info("HTTP/2 multiplexing enabled")
            except Exception as e:
                logger.warning(f"HTTP/2 not available, falling back to HTTP/1.1: {e}")
                self.client_pool = httpx.AsyncClient(
                    timeout=timeout_config,
                    limits=limits,
                    http2=False  # Fallback to HTTP/1.1
                )
        
        return self.client_pool
    
    async def _acquire_slot(self) -> int:
        """Acquire a slot for processing a request"""
        await self.semaphore.acquire()
        self.request_counter += 1
        self.active_requests += 1
        request_id = self.request_counter
        
        logger.info(f"Request #{request_id} acquired slot (active: {self.active_requests}/{self.max_concurrent_requests})")
        return request_id
    
    async def _release_slot(self, request_id: int):
        """Release a slot after processing a request"""
        self.active_requests = max(0, self.active_requests - 1)
        self.semaphore.release()
        logger.info(f"Request #{request_id} released slot (active: {self.active_requests}/{self.max_concurrent_requests})")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama service health and model availability"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            
            if response.status_code != 200:
                return {
                    "status": "unhealthy",
                    "ollama_url": self.base_url,
                    "available_models": [],
                    "target_model": self.model_name,
                    "model_available": False,
                    "error": f"Ollama service error: {response.status_code}"
                }
            
            models_data = response.json()
            available_models = [model.get("name", "") for model in models_data.get("models", [])]
            model_available = any(self.model_name in model for model in available_models)
            
            return {
                "status": "healthy",
                "ollama_url": self.base_url,
                "available_models": available_models,
                "target_model": self.model_name,
                "model_available": model_available,
                "model_path": str(self.config.MODEL_DIR / "MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf") if self.config.MODEL_DIR.exists() else None,
                "system_prompt_loaded": bool(self.system_prompt),
                "system_prompt_preview": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt,
                "active_requests": self.active_requests,
                "max_concurrent_requests": self.max_concurrent_requests,
                "queue_status": "ready" if self.active_requests < self.max_concurrent_requests else "busy",
                "multiplexing_enabled": True
            }
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "ollama_url": self.base_url,
                "available_models": [],
                "target_model": self.model_name,
                "model_available": False,
                "model_path": str(self.config.MODEL_DIR / "MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf") if self.config.MODEL_DIR.exists() else None,
                "system_prompt_loaded": bool(self.system_prompt),
                "system_prompt_preview": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt,
                "active_requests": self.active_requests,
                "error": str(e)
            }
    
    async def generate(self, content: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Ollama with multiplexing support"""
        request_id = await self._acquire_slot()
        
        try:
            logger.info(f"Request #{request_id}: Starting generation for content length: {len(content)}")
            
            # Prepare the prompt with system prompt
            prompt = f"System: {self.system_prompt}\n\nUser: {content}\n\nIMPORTANT: Return ONLY valid JSON. No explanatory text, no markdown, no code blocks. Just the raw JSON object."
            
            # Prepare Ollama request
            ollama_payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.DEFAULT_TEMPERATURE),
                    "num_predict": kwargs.get("max_tokens", self.config.DEFAULT_MAX_TOKENS),
                    "top_p": kwargs.get("top_p", self.config.DEFAULT_TOP_P),
                    "top_k": kwargs.get("top_k", self.config.DEFAULT_TOP_K),
                    "repeat_penalty": kwargs.get("repeat_penalty", self.config.DEFAULT_REPEAT_PENALTY),
                    "num_ctx": self.config.DEFAULT_NUM_CTX
                }
            }
            
            logger.info(f"Request #{request_id}: Sending request to Ollama model: {self.model_name}")
            
            # Send request using multiplexed client
            client = await self._get_client()
            response = await client.post(f"{self.base_url}/api/generate", json=ollama_payload)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Request #{request_id}: Generation successful - Response length: {len(result.get('response', ''))}")
                
                # Clean and validate JSON response
                cleaned_response = self._clean_json_response(result.get("response", ""))
                
                # Parse the cleaned JSON string into a Python object
                parsed_response = json.loads(cleaned_response)
                
                return {
                    "response": parsed_response,
                    "model": self.model_name,
                    "usage": {
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                        "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                    },
                    "request_id": request_id
                }
            else:
                logger.error(f"Request #{request_id}: Ollama generation failed: {response.status_code} - {response.text}")
                raise Exception(f"Generation failed: {response.text}")
                    
        except httpx.ConnectError as e:
            logger.error(f"Request #{request_id}: Connection error: {e}")
            raise Exception(f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            logger.error(f"Request #{request_id}: Timeout error: {e}")
            raise Exception(f"Request timeout: {e}")
        except httpx.RemoteProtocolError as e:
            logger.error(f"Request #{request_id}: Protocol error: {e}")
            raise Exception(f"Connection protocol error: {e}")
        except Exception as e:
            logger.error(f"Request #{request_id}: Generate request failed: {e}")
            raise Exception(f"Generate request failed: {e}")
        finally:
            await self._release_slot(request_id)
    
    async def generate_stream(self, content: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response using Ollama with multiplexing support"""
        request_id = await self._acquire_slot()
        
        try:
            logger.info(f"Request #{request_id}: Starting streaming generation for content length: {len(content)}")
            
            # Prepare the prompt with system prompt
            prompt = f"System: {self.system_prompt}\n\nUser: {content}\n\nIMPORTANT: Return ONLY valid JSON. No explanatory text, no markdown, no code blocks. Just the raw JSON object."
            
            # Prepare Ollama request with streaming enabled
            ollama_payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,  # Enable streaming
                "options": {
                    "temperature": kwargs.get("temperature", self.config.DEFAULT_TEMPERATURE),
                    "num_predict": kwargs.get("max_tokens", self.config.DEFAULT_MAX_TOKENS),
                    "top_p": kwargs.get("top_p", self.config.DEFAULT_TOP_P),
                    "top_k": kwargs.get("top_k", self.config.DEFAULT_TOP_K),
                    "repeat_penalty": kwargs.get("repeat_penalty", self.config.DEFAULT_REPEAT_PENALTY),
                    "num_ctx": self.config.DEFAULT_NUM_CTX
                }
            }
            
            logger.info(f"Request #{request_id}: Sending streaming request to Ollama model: {self.model_name}")
            
            # Send streaming request using multiplexed client
            client = await self._get_client()
            async with client.stream("POST", f"{self.base_url}/api/generate", json=ollama_payload) as response:
                if response.status_code == 200:
                    accumulated_text = ""
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    token = data["response"]
                                    accumulated_text += token
                                    
                                    # Yield each token as it arrives
                                    yield {
                                        "type": "token",
                                        "content": token,
                                        "accumulated": accumulated_text,
                                        "done": data.get("done", False),
                                        "request_id": request_id
                                    }
                                
                                if data.get("done", False):
                                    # Final response - try to parse accumulated JSON
                                    try:
                                        cleaned_response = self._clean_json_response(accumulated_text)
                                        parsed_response = json.loads(cleaned_response)
                                        
                                        yield {
                                            "type": "final",
                                            "content": parsed_response,
                                            "model": self.model_name,
                                            "usage": {
                                                "prompt_tokens": data.get("prompt_eval_count", 0),
                                                "completion_tokens": data.get("eval_count", 0),
                                                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                                            },
                                            "request_id": request_id
                                        }
                                    except json.JSONDecodeError:
                                        yield {
                                            "type": "error",
                                            "content": "Failed to parse JSON response",
                                            "raw_response": accumulated_text[:200] + "..." if len(accumulated_text) > 200 else accumulated_text,
                                            "request_id": request_id
                                        }
                                    break
                                    
                            except json.JSONDecodeError:
                                continue
                else:
                    error_text = await response.aread()
                    logger.error(f"Request #{request_id}: Ollama streaming failed: {response.status_code} - {error_text}")
                    yield {
                        "type": "error",
                        "content": f"Generation failed: {error_text.decode()}",
                        "request_id": request_id
                    }
                        
        except httpx.ConnectError as e:
            logger.error(f"Request #{request_id}: Connection error: {e}")
            yield {
                "type": "error",
                "content": f"Connection failed: {e}",
                "request_id": request_id
            }
        except httpx.TimeoutException as e:
            logger.error(f"Request #{request_id}: Timeout error: {e}")
            yield {
                "type": "error",
                "content": f"Request timeout: {e}",
                "request_id": request_id
            }
        except httpx.RemoteProtocolError as e:
            logger.error(f"Request #{request_id}: Protocol error: {e}")
            yield {
                "type": "error",
                "content": f"Connection protocol error: {e}",
                "request_id": request_id
            }
        except Exception as e:
            logger.error(f"Request #{request_id}: Streaming request failed: {e}")
            yield {
                "type": "error",
                "content": f"Streaming request failed: {e}",
                "request_id": request_id
            }
        finally:
            await self._release_slot(request_id)
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean and extract JSON from model response"""
        try:
            # Remove markdown code blocks
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = re.sub(r'`\s*', '', response_text)
            
            # Find JSON object boundaries
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx + 1]
                
                # Validate JSON
                json.loads(json_str)
                return json_str
            else:
                # If no JSON found, try to parse the whole response
                json.loads(response_text.strip())
                return response_text.strip()
                
        except json.JSONDecodeError:
            # If JSON parsing fails, return a default JSON structure
            logger.warning("Failed to parse JSON from response, returning default structure")
            return json.dumps({
                "error": "Failed to generate valid JSON",
                "raw_response": response_text[:200] + "..." if len(response_text) > 200 else response_text
            })
    
    async def close(self):
        """Close the HTTP client pool"""
        if self.client_pool:
            await self.client_pool.aclose()
            self.client_pool = None


# Global instance
ollama_service = OllamaService()
