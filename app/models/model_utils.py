"""
Model utility functions for MCS architecture
"""
from typing import Dict, Any, Optional
from app.core.config import get_config
from app.core.logging_config import get_logger

logger = get_logger(__name__)
config = get_config()


def validate_model_data(data: Dict[str, Any], required_fields: list) -> bool:
    """Validate model data structure"""
    if not isinstance(data, dict):
        logger.warning("Data must be a dictionary")
        return False
    
    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False
    
    return True


def convert_to_dict(data: Any) -> Dict[str, Any]:
    """Convert data to dictionary format"""
    if isinstance(data, dict):
        return data
    elif hasattr(data, '__dict__'):
        return data.__dict__
    else:
        logger.warning("Cannot convert data to dictionary")
        return {}


def sanitize_input(text: str) -> str:
    """Sanitize input text"""
    if not isinstance(text, str):
        return str(text)
    
    # Remove potentially harmful characters
    sanitized = text.strip()
    # Add more sanitization logic as needed
    
    return sanitized


def format_error_response(error: str, error_code: Optional[str] = None) -> Dict[str, Any]:
    """Format error response"""
    response = {
        "error": error,
        "success": False
    }
    
    if error_code:
        response["error_code"] = error_code
    
    return response


def format_success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Format success response"""
    return {
        "data": data,
        "message": message,
        "success": True
    }
