from fastapi import FastAPI
from app.routers import badges, health
from app.core.logging import setup_logging

app = FastAPI(title="Badge Generator API", version="1.0.0")

# Setup logging
setup_logging()

# Include routers
app.include_router(badges.router, prefix="/api/v1")
app.include_router(health.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

