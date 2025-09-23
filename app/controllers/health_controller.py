"""
Health controller functions for MCS architecture
"""
from typing import Dict, Any
from app.models.schemas import HealthResponse
from app.services.ollama_service import ollama_service
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _handle_error(error: Exception, operation: str) -> Exception:
    """Handle and log errors consistently"""
    error_message = f"{operation} failed: {str(error)}"
    logger.error(error_message)
    return Exception(error_message)


def _log_request(operation: str, request_data: Dict[str, Any]):
    """Log incoming requests"""
    logger.info(f"{operation} - {_summarize_request(request_data)}")


def _log_response(operation: str, success: bool):
    """Log response completion"""
    status = "completed successfully" if success else "failed"
    logger.info(f"{operation} {status}")


def _summarize_request(request_data: Dict[str, Any]) -> str:
    """Create a summary of request data for logging"""
    return "no parameters" if not request_data else "health check request"


async def health_check() -> HealthResponse:
    """Check service health and model availability"""
    try:
        # Log the health check request
        _log_request("Health check", {})
        
        # Call the service layer for health check
        health_data = await ollama_service.health_check()
        
        # Format the response
        formatted_health = _format_health_response(health_data)
        
        # Log successful completion
        _log_response("Health check", True)
        
        return HealthResponse(**formatted_health)
        
    except Exception as e:
        # Handle health check errors
        _log_response("Health check", False)
        raise _handle_error(e, "Health check")


def _format_health_response(health_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format health check response"""
    return {
        "status": health_data.get("status", "unknown"),
        "ollama_url": health_data.get("ollama_url", ""),
        "available_models": health_data.get("available_models", []),
        "target_model": health_data.get("target_model", ""),
        "model_available": health_data.get("model_available", False),
        "model_path": health_data.get("model_path"),
        "system_prompt_loaded": health_data.get("system_prompt_loaded", False),
        "system_prompt_preview": health_data.get("system_prompt_preview", ""),
        "active_requests": health_data.get("active_requests", 0),
        "max_concurrent_requests": health_data.get("max_concurrent_requests", 0),
        "queue_status": health_data.get("queue_status", "unknown"),
        "multiplexing_enabled": health_data.get("multiplexing_enabled", False),
        "error": health_data.get("error")
    }