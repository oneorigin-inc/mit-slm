"""
Main entry point for DCC Model API
"""
import uvicorn
from app.core.config import get_config

if __name__ == "__main__":
    config = get_config()
    
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )
