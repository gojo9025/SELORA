"""
SELORA — Single Unified Application Entry Point
Sensor-aware Lunar Image Registration & Optical Alignment
ISRO Smart India Hackathon 2026 (Problem Statement: 26166)

Runs the complete application (Frontend UI + FastAPI Backend + Computer Vision Engine)
in a single unified process on http://localhost:8000.
"""

import sys
from pathlib import Path
import importlib.util

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_OUT = ROOT_DIR / "frontend" / "out"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load the backend FastAPI application
backend_main_path = BACKEND_DIR / "main.py"
spec = importlib.util.spec_from_file_location("backend_app_module", backend_main_path)
backend_app_module = importlib.util.module_from_spec(spec)
sys.modules["backend_app_module"] = backend_app_module
spec.loader.exec_module(backend_app_module)

# Re-export app for ASGI servers like uvicorn main:app
app = backend_app_module.app

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

# Mount Next.js static export if available
if FRONTEND_OUT.exists() and (FRONTEND_OUT / "index.html").exists():
    logger.info(f"Unified SELORA App: Mounting frontend from {FRONTEND_OUT}")

    # 1. Mount _next static assets directory
    next_static = FRONTEND_OUT / "_next"
    if next_static.exists():
        app.mount("/_next", StaticFiles(directory=str(next_static)), name="next_static")

    # 2. Specific page routes
    @app.get("/", include_in_schema=False)
    async def serve_home():
        return FileResponse(FRONTEND_OUT / "index.html")

    @app.get("/workspace", include_in_schema=False)
    async def serve_workspace():
        wp = FRONTEND_OUT / "workspace.html"
        return FileResponse(wp if wp.exists() else FRONTEND_OUT / "workspace" / "index.html")

    @app.get("/benchmark/compare", include_in_schema=False)
    async def serve_benchmark_compare():
        cp = FRONTEND_OUT / "benchmark" / "compare.html"
        if not cp.exists():
            cp = FRONTEND_OUT / "benchmark" / "compare" / "index.html"
        return FileResponse(cp)

    @app.get("/benchmark", include_in_schema=False)
    async def serve_benchmark():
        bp = FRONTEND_OUT / "benchmark.html"
        return FileResponse(bp if bp.exists() else FRONTEND_OUT / "benchmark" / "index.html")

    @app.get("/results/{rest:path}", include_in_schema=False)
    async def serve_results(rest: str):
        # Client component reads window.location.pathname to parse actual registration ID
        rp = FRONTEND_OUT / "results" / "view.html"
        if not rp.exists():
            rp = FRONTEND_OUT / "results" / "[id].html"
        if not rp.exists():
            rp = FRONTEND_OUT / "index.html"
        return FileResponse(rp)

    # 3. Mount remaining root static files (favicon.ico, svgs, etc.)
    app.mount("/", StaticFiles(directory=str(FRONTEND_OUT), html=True), name="frontend_root")
else:
    logger.warning(
        f"Frontend build not found at {FRONTEND_OUT}. "
        "Run 'npm run build' inside frontend/ to compile the unified UI."
    )


if __name__ == "__main__":
    import uvicorn
    import webbrowser

    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print("=" * 72)
    print("  🌕 SELORA — Unified Application (ISRO SIH 2026)")
    print("  Sensor-aware Lunar Image Registration & Optical Alignment")
    print("=" * 72)
    print(f"  [✓] Full App Running: {url}")
    print(f"  [✓] Interactive Workspace: {url}/workspace")
    print(f"  [✓] Benchmark Suite: {url}/benchmark")
    print(f"  [✓] Comparative Matrix: {url}/benchmark/compare")
    print(f"  [✓] Swagger API Docs: {url}/docs")
    print("=" * 72)
    print("  Press CTRL+C to terminate the application.")
    print("=" * 72)

    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run("main:app", host=host, port=port, reload=True)
