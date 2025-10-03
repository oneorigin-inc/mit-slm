from fastapi import FastAPI
from app.routers import badges, health
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging

app = FastAPI(title="Badge Generator API", version="1.0.0")

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
    uvicorn.run(app, host="0.0.0.0", port=8000)

