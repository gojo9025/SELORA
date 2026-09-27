"""
SELORA Backend — FastAPI Application Entry Point
Sensor-aware Lunar Image Registration & Optical Alignment
SIH Problem Statement 26166
"""

import shutil
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

    # A mounted production disk starts empty. Seed only the bundled benchmark
    # inputs, without replacing user uploads or prior processing results.
    seed_dir = Path(settings.SEED_DATA_DIR)
    upload_dir = Path(settings.UPLOAD_DIR)
    if seed_dir.exists() and seed_dir.resolve() != upload_dir.resolve():
        for seed_file in seed_dir.glob("demo_*.png"):
            target = upload_dir / seed_file.name
            if not target.exists():
                shutil.copy2(seed_file, target)

    logger.info("SELORA backend started — storage directories ready")
    yield
    logger.info("SELORA backend shutting down")


app = FastAPI(
    title="SELORA API",
    description="Sensor-aware Lunar Image Registration & Optical Alignment",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — development origins by default; set CORS_ORIGINS for the Vercel domain
# in production. The app has no cookie-authenticated endpoints, so credentials
# are intentionally disabled.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
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
