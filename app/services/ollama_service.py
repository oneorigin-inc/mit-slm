"""
Ollama service for model interactions
"""
import json
import re
import httpx
from typing import Dict, Any, Optional
from app.core.config import get_config
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class OllamaService:
    """Service for interacting with Ollama API"""
    
    def __init__(self):
        self.config = get_config()
        self.base_url = self.config.OLLAMA_URL
        self.model_name = self.config.MODEL_NAME
        self.system_prompt = self.config.load_system_prompt()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama service health and model availability"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check Ollama service
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code != 200:
                    return {
                        "status": "unhealthy",
                        "ollama_url": self.base_url,
                        "available_models": [],
                        "target_model": self.model_name,
                        "model_available": False,
                        "model_path": str(self.config.MODEL_DIR / "MIT_OB_Phi-4-mini-instruct.Q4_K_M.gguf") if self.config.MODEL_DIR.exists() else None,
                        "system_prompt_loaded": bool(self.system_prompt),
                        "system_prompt_preview": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt,
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
                    "system_prompt_preview": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt
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
                "error": str(e)
            }
    
    async def generate_stream(self, content: str, **kwargs):
        """Generate streaming response using Ollama"""
        try:
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
            
            logger.info(f"Sending streaming request to Ollama model: {self.model_name}")
            
            # Send streaming request to Ollama
            async with httpx.AsyncClient(timeout=120.0) as client:
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
                                            "done": data.get("done", False)
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
                                                }
                                            }
                                        except json.JSONDecodeError:
                                            yield {
                                                "type": "error",
                                                "content": "Failed to parse JSON response",
                                                "raw_response": accumulated_text[:200] + "..." if len(accumulated_text) > 200 else accumulated_text
                                            }
                                        break
                                        
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.aread()
                        logger.error(f"Ollama streaming failed: {response.status_code} - {error_text}")
                        yield {
                            "type": "error",
                            "content": f"Generation failed: {error_text.decode()}"
                        }
                        
        except Exception as e:
            logger.error(f"Streaming request failed: {e}")
            yield {
                "type": "error",
                "content": f"Streaming request failed: {e}"
            }
    
    async def generate(self, content: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Ollama (non-streaming)"""
        try:
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
            
            logger.info(f"Sending request to Ollama model: {self.model_name}")
            
            # Send request to Ollama
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=ollama_payload)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Generation successful - Response length: {len(result.get('response', ''))}")
                    
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
                        }
                    }
                else:
                    logger.error(f"Ollama generation failed: {response.status_code} - {response.text}")
                    raise Exception(f"Generation failed: {response.text}")
                    
        except Exception as e:
            logger.error(f"Generate request failed: {e}")
            raise Exception(f"Generate request failed: {e}")
    
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
