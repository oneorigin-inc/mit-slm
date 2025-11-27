import logging
import time
from typing import Dict, Optional, AsyncGenerator, Any, cast
from fastapi import HTTPException
from llama_cpp import Llama
from app.core.config import settings

logger = logging.getLogger(__name__)


class LlamaCppClient:
    """Client for llama-cpp-python models supporting both local and HuggingFace models."""

    def __init__(self):
        self.llm: Optional[Llama] = None
        self.model_config = settings.MODEL_CONFIG

    def load_model(self):
        """Load model from either local path or HuggingFace."""
        if self.llm is not None:
            logger.info("Model already loaded, skipping reload")
            return

        try:
            if settings.LLAMACPP_MODEL_SOURCE == "huggingface":
                # Load from HuggingFace
                if not settings.LLAMACPP_HF_REPO_ID or not settings.LLAMACPP_HF_FILENAME:
                    raise ValueError(
                        "LLAMACPP_HF_REPO_ID and LLAMACPP_HF_FILENAME must be set "
                        "when using HuggingFace model source"
                    )

                logger.info(
                    f"Loading model from HuggingFace: {settings.LLAMACPP_HF_REPO_ID}/{settings.LLAMACPP_HF_FILENAME}"
                )

                # Use LLAMACPP_N_CTX if set in .env, otherwise fall back to MODEL_NUM_CTX
                n_ctx = settings.LLAMACPP_N_CTX if settings.LLAMACPP_N_CTX is not None else settings.NUM_CTX
                logger.info(f"Using context window: {n_ctx} (LLAMACPP_N_CTX={settings.LLAMACPP_N_CTX}, MODEL_NUM_CTX={settings.NUM_CTX})")

                # Prepare kwargs for from_pretrained
                load_kwargs = {
                    "repo_id": settings.LLAMACPP_HF_REPO_ID,
                    "filename": settings.LLAMACPP_HF_FILENAME,
                    "n_ctx": n_ctx,
                    "n_gpu_layers": settings.LLAMACPP_N_GPU_LAYERS,
                    "verbose": settings.LLAMACPP_VERBOSE
                }

                # Add HuggingFace token if provided (required for private/gated repos)
                if settings.LLAMACPP_HF_TOKEN:
                    load_kwargs["token"] = settings.LLAMACPP_HF_TOKEN
                    logger.info("Using HuggingFace authentication token")

                self.llm = Llama.from_pretrained(**load_kwargs)
                logger.info(f"Model loaded successfully from HuggingFace (n_ctx={n_ctx})")

            elif settings.LLAMACPP_MODEL_SOURCE == "local":
                # Load from local path
                if not settings.LLAMACPP_MODEL_PATH:
                    raise ValueError(
                        "LLAMACPP_MODEL_PATH must be set when using local model source"
                    )

                logger.info(f"Loading model from local path: {settings.LLAMACPP_MODEL_PATH}")

                # Use LLAMACPP_N_CTX if set in .env, otherwise fall back to MODEL_NUM_CTX
                n_ctx = settings.LLAMACPP_N_CTX if settings.LLAMACPP_N_CTX is not None else settings.NUM_CTX
                logger.info(f"Using context window: {n_ctx} (LLAMACPP_N_CTX={settings.LLAMACPP_N_CTX}, MODEL_NUM_CTX={settings.NUM_CTX})")

                self.llm = Llama(
                    model_path=settings.LLAMACPP_MODEL_PATH,
                    n_ctx=n_ctx,
                    n_gpu_layers=settings.LLAMACPP_N_GPU_LAYERS,
                    verbose=settings.LLAMACPP_VERBOSE
                )
                logger.info(f"Model loaded successfully from local path (n_ctx={n_ctx})")

            else:
                raise ValueError(
                    f"Invalid LLAMACPP_MODEL_SOURCE: {settings.LLAMACPP_MODEL_SOURCE}. "
                    "Must be 'local' or 'huggingface'"
                )

        except Exception as e:
            logger.error(f"Failed to load llama-cpp model: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load llama-cpp model: {str(e)}"
            )

    async def generate_stream(
        self,
        content: str,
        temperature: float = 0.10,
        max_tokens: int = 400,
        top_p: float = 0.9,
        top_k: int = 50,
        repeat_penalty: float = 1.05,
        context_length: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Make streaming call to llama-cpp with structured response format using chat completion.

        Note: context_length parameter is accepted but cannot be changed at runtime for llama-cpp.
        Context size is fixed at model load time. Set LLAMACPP_N_CTX in .env to change it.
        """

        if self.llm is None:
            self.load_model()

        # Warn if context_length override is attempted
        if context_length is not None:
            logger.warning(
                "context_length parameter is not supported at runtime for llama-cpp. "
                "Context size is fixed at model load time. Current n_ctx: %s. "
                "To change context size, set LLAMACPP_N_CTX in .env and restart.",
                self.llm.n_ctx() if self.llm else "unknown"
            )

        request_id = f"req_{hash(content)}_{int(time.time())}"
        accumulated_response = ""

        try:
            start_time = time.time()

            # Create chat completion with streaming (using system prompt)
            if self.llm is None:
                raise HTTPException(
                    status_code=500,
                    detail="Llama-cpp model not loaded"
                )

            # Use chat completion format with system prompt
            messages = [
                {"role": "system", "content": settings.BADGE_SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ]

            stream = self.llm.create_chat_completion(
                messages=cast(Any, messages),
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repeat_penalty,
                stream=True
            )

            token_count = 0

            # Stream tokens from chat completion
            for output in stream:
                # Support both dict-like responses and objects from llama-cpp stream items
                if isinstance(output, dict):
                    choices = output.get("choices")
                else:
                    choices = getattr(output, "choices", None)

                if choices and len(choices) > 0:
                    choice = choices[0]

                    # Chat completion uses "delta" instead of "text"
                    if isinstance(choice, dict):
                        delta = choice.get("delta", {})
                        # Get content from delta
                        if isinstance(delta, dict):
                            token_content = delta.get("content", "")
                        else:
                            token_content = getattr(delta, "content", "")
                    else:
                        delta = getattr(choice, "delta", None)
                        if delta:
                            token_content = getattr(delta, "content", "")
                        else:
                            token_content = ""

                    if token_content:
                        accumulated_response += token_content
                        token_count += 1

                        yield {
                            "type": "token",
                            "content": token_content,
                            "accumulated": accumulated_response,
                            "request_id": request_id
                        }

            # Calculate metrics
            end_time = time.time()
            total_duration_ns = int((end_time - start_time) * 1e9)

            metrics = {
                "total_duration": total_duration_ns,
                "load_duration": None,  # Not available in llama-cpp
                "prompt_eval_count": None,  # Not directly available
                "prompt_eval_duration": None,  # Not directly available
                "eval_count": token_count,
                "eval_duration": total_duration_ns
            }

            logger.info(
                f"Llama-cpp streaming completed [{request_id}]: "
                f"eval_count={token_count}, "
                f"duration={total_duration_ns/1e9:.2f}s"
            )

            # Yield final response
            yield {
                "type": "final",
                "content": accumulated_response,
                "request_id": request_id,
                "metrics": metrics
            }

        except Exception as e:
            logger.error(f"Error in llama-cpp streaming for request_id {request_id}: {e}")
            yield {
                "type": "error",
                "content": f"Llama-cpp call failed: {str(e)}",
                "request_id": request_id,
                "error_code": "unexpected_error"
            }

    async def generate(
        self,
        prompt: str,
        config: Optional[Dict] = None
    ) -> tuple[str, Dict[str, Any]]:
        """Make async call to llama-cpp using chat completion. Returns (response_text, metrics)."""

        if self.llm is None:
            self.load_model()

        # Ensure we have a config dict to work with
        if config is None:
            config = self.model_config.copy()
        else:
            config = config.copy()

        request_id = f"req_{hash(prompt)}_{int(time.time())}"
        start_time = time.time()

        try:
            if self.llm is None:
                raise HTTPException(
                    status_code=500,
                    detail="Llama-cpp model not loaded"
                )

            # Use chat completion format with system prompt
            messages = [
                {"role": "system", "content": settings.BADGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            # Make a chat completion call (non-streaming)
            output = self.llm.create_chat_completion(
                messages=cast(Any, messages),
                temperature=config.get("temperature", 0.10),
                max_tokens=config.get("num_predict", 400),
                top_p=config.get("top_p", 0.9),
                top_k=config.get("top_k", 50),
                repeat_penalty=config.get("repeat_penalty", 1.05),
                stream=False
            )

            end_time = time.time()

            # Normalize output into text and token count from chat completion
            response_text = ""
            token_count = 0

            if isinstance(output, dict):
                choices = output.get("choices", []) or []
                usage = output.get("usage", {}) or {}
            else:
                choices = getattr(output, "choices", None) or []
                usage = getattr(output, "usage", None) or {}

            if choices and len(choices) > 0:
                first_choice = choices[0]
                # Chat completion returns message.content instead of text
                if isinstance(first_choice, dict):
                    message = first_choice.get("message", {})
                    if isinstance(message, dict):
                        response_text = (message.get("content", "") or "").strip()
                    else:
                        response_text = (getattr(message, "content", "") or "").strip()
                else:
                    message = getattr(first_choice, "message", None)
                    if message:
                        response_text = (getattr(message, "content", "") or "").strip()
                    else:
                        response_text = ""

            # Extract token usage if available
            if isinstance(usage, dict):
                token_count = usage.get("completion_tokens", 0) or 0
            else:
                token_count = getattr(usage, "completion_tokens", 0) or 0

            # Fall back to word count if tokens not available
            if token_count <= 0:
                token_count = len(response_text.split())

            total_duration_ns = int((end_time - start_time) * 1e9)

            metrics = {
                "total_duration": total_duration_ns,
                "load_duration": None,
                "prompt_eval_count": None,
                "prompt_eval_duration": None,
                "eval_count": token_count,
                "eval_duration": total_duration_ns
            }

            logger.info(
                f"Llama-cpp request {request_id} completed. "
                f"Response length: {len(response_text)}, "
                f"eval_count={metrics['eval_count']}, "
                f"duration={total_duration_ns/1e9:.2f}s"
            )

            return response_text, metrics

        except Exception as e:
            logger.error(f"Error in llama-cpp generation for request_id {request_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Llama-cpp call failed: {str(e)}"
            )

    async def generate_with_parameters(
        self,
        prompt: str,
        temperature: float = 0.15,
        max_tokens: int = 400,
        top_p: float = 0.8,
        top_k: int = 30,
        repeat_penalty: float = 1.05,
        context_length: Optional[int] = None
    ) -> tuple[str, Dict[str, Any]]:
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
        for chunk in reversed(stream_chunks):
            if chunk.get("type") == "final" and "metrics" in chunk:
                return chunk["metrics"]
        return None


# Global client instance
llamacpp_client = LlamaCppClient()


async def preload_llamacpp_model() -> bool:
    """Preload the llama-cpp model into memory"""
    try:
        logger.info("Preloading llama-cpp model...")
        llamacpp_client.load_model()
        logger.info("Llama-cpp model preloaded successfully")
        return True
    except Exception as e:
        logger.error(f"Llama-cpp model preload failed: {e}")
        return False
