from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import badges, health
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.core.config import settings
from app.services.ollama_client import preload_model
from app.services.skill_extractor import skill_service
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await preload_model()

    # Initialize LAiSER skill extractor (available for per-request use)
    try:
        logger.info("Initializing LAiSER skill extractor...")
        await skill_service.initialize(
            ai_model_id=settings.LAISER_MODEL_ID,
            hf_token=settings.LAISER_HF_TOKEN,
            use_gpu=settings.LAISER_USE_GPU
        )
        logger.info("LAiSER initialization complete.")
    except Exception as e:
        logger.warning(f"LAiSER initialization failed: {e}. Skill extraction will be unavailable for all requests.")

    yield
    # Shutdown (if needed)

app = FastAPI(title="Badge Generator API", version="1.0.0", lifespan=lifespan)

# Setup logging
setup_logging()

# Include routers
app.include_router(badges.router, prefix="/api/v1")
app.include_router(health.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

    