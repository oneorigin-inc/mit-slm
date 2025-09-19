"""
Pydantic models for DCC Model API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GenerateRequest(BaseModel):
    """Request model for text generation"""
    content: str = Field(..., description="Course content to generate badge metadata from")
    temperature: Optional[float] = Field(0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(1024, ge=1, le=4096, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: Optional[int] = Field(30, ge=1, le=100, description="Top-k sampling parameter")
    repeat_penalty: Optional[float] = Field(1.02, ge=0.0, le=2.0, description="Repeat penalty")


class UsageInfo(BaseModel):
    """Token usage information"""
    prompt_tokens: int = Field(0, description="Number of tokens in prompt")
    completion_tokens: int = Field(0, description="Number of tokens in completion")
    total_tokens: int = Field(0, description="Total number of tokens")


class GenerateResponse(BaseModel):
    """Response model for text generation"""
    response: Dict[str, Any] = Field(..., description="Generated response as JSON object")
    model: str = Field(..., description="Model used for generation")
    usage: UsageInfo = Field(..., description="Token usage information")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    ollama_url: str = Field(..., description="Ollama server URL")
    available_models: list = Field(..., description="List of available models")
    target_model: str = Field(..., description="Target model name")
    model_available: bool = Field(..., description="Whether target model is available")
    model_path: Optional[str] = Field(None, description="Path to model file")
    system_prompt_loaded: bool = Field(False, description="Whether system prompt is loaded")
    system_prompt_preview: str = Field("", description="Preview of system prompt")
    error: Optional[str] = Field(None, description="Error message if any")


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: Optional[str] = Field(None, description="Error timestamp")
