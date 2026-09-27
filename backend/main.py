"""
SELORA Backend — FastAPI Application Entry Point
Sensor-aware Lunar Image Registration & Optical Alignment
SIH Problem Statement 26166
"""

import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from api import upload, registration, evaluation, benchmark
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — create storage directories on startup."""
    for d in [
        settings.UPLOAD_DIR,
        settings.PROCESSED_DIR,
        settings.RESULTS_DIR,
        settings.VISUALIZATIONS_DIR,
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info("SELORA backend started — storage directories ready")
    yield
    logger.info("SELORA backend shutting down")


app = FastAPI(
    title="SELORA API",
    description="Sensor-aware Lunar Image Registration & Optical Alignment",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure data root exists before mounting
Path(settings.DATA_ROOT).mkdir(parents=True, exist_ok=True)
# Static file serving for generated images
app.mount("/static", StaticFiles(directory=str(settings.DATA_ROOT)), name="static")

# Routers
app.include_router(upload.router, prefix="/api/images", tags=["images"])
app.include_router(registration.router, prefix="/api", tags=["registration"])
app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])
app.include_router(benchmark.router, prefix="/api/benchmark", tags=["benchmark"])


@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "SELORA", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
