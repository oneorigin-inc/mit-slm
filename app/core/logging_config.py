"""
Logging configuration for DCC Model API
"""
import logging
import logging.handlers
from pathlib import Path
from app.core.config import get_config


def setup_logging():
    """Setup logging configuration"""
    config = get_config()
    
    # Create logs directory if it doesn't exist
    config.LOGS_DIR.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler with rotation
            logging.handlers.RotatingFileHandler(
                config.LOG_FILE,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Set specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)