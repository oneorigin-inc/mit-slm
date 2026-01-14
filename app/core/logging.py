import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


class HealthCheckFilter(logging.Filter):
    """
    Filter to suppress health check endpoint logs.
    Filters out logs that contain '/health' path or health check related messages.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Return False to suppress the log record, True to allow it.
        
        Args:
            record: The log record to filter
            
        Returns:
            bool: False to suppress, True to allow
        """
        # Get the log message
        message = record.getMessage()
        
        # Suppress logs containing health check path
        if '/health' in message or 'health check' in message.lower():
            return False
        
        # Suppress logs from health router
        if record.name == 'app.routers.health':
            return False
        
        # Allow all other logs
        return True


def setup_logging(
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Setup application logging with rotating file handler
    
    Args:
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Single log file path
    log_file = logs_dir / "badge_generator.log"
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create health check filter
    health_filter = HealthCheckFilter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(health_filter)
    
    # Rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(health_filter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logger = logging.getLogger("badge_generator")
    logger.info("Logging initialized")
    return logger