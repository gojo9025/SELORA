"""
SELORA Registration API
POST /api/register
GET  /api/registration/{id}
GET  /api/registration/{id}/metrics
GET  /api/registration/{id}/transform
GET  /api/registration/{id}/visualizations
GET  /api/registration/{id}/download/{artifact}
"""

from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from loguru import logger

from schemas import RegistrationRequest, RegistrationResult
from core.pipeline import run_registration
from core.database import get_registration, get_all_registrations
from config import settings

router = APIRouter()

@router.get("/registrations")
async def list_registrations():
    results = get_all_registrations()
    return results

@router.post("/register")
async def register(req: RegistrationRequest, background_tasks: BackgroundTasks):
    """
    Trigger the full registration pipeline.
    """
    logger.info(
        f"Register request: src={req.source_image_id} ref={req.reference_image_id} "
        f"src_sensor={req.source_sensor} ref_sensor={req.reference_sensor} mode={req.mode}"
    )

    result = run_registration(
        source_image_id=req.source_image_id,
        reference_image_id=req.reference_image_id,
        source_sensor=req.source_sensor,
        reference_sensor=req.reference_sensor,
        mode=req.mode,
        override_config=req.override_config,
    )
    return result

@router.get("/registration/{reg_id}")
async def get_result(reg_id: str):
    result = get_registration(reg_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Registration '{reg_id}' not found.")
    return result

@router.get("/registration/{reg_id}/metrics")
async def get_metrics(reg_id: str):
    result = get_registration(reg_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Registration not found.")
    if result.status == "failed":
        raise HTTPException(status_code=422, detail="Registration failed — no metrics available.")
    return result.metrics or {}

@router.get("/registration/{reg_id}/transform")
async def get_transform(reg_id: str):
    result = get_registration(reg_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Registration not found.")
    if result.status == "failed":
        raise HTTPException(status_code=422, detail="Registration failed — no transform available.")
    return result.transformation or {}

@router.get("/registration/{reg_id}/visualizations")
async def get_visualizations(reg_id: str):
    result = get_registration(reg_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Registration not found.")
    return result.visualizations or {}

@router.get("/registration/{reg_id}/download/{artifact}")
async def download_artifact(reg_id: str, artifact: str):
    """
    Download a result artifact.
    artifact: 'registered' | 'overlay' | 'difference' | 'error_heatmap' | 'matches' | 'metrics'
    """
    result = get_registration(reg_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Registration not found.")

    vis = result.visualizations
    if not vis:
        raise HTTPException(status_code=404, detail="No visualizations available.")

    artifact_map = {
        "registered": (vis.registered_image, "registered.jpg", "image/jpeg"),
        "overlay": (vis.overlay_image, "overlay.jpg", "image/jpeg"),
        "difference": (vis.difference_map, "difference_map.jpg", "image/jpeg"),
        "error_heatmap": (vis.error_heatmap, "error_heatmap.jpg", "image/jpeg"),
        "matches": (vis.match_visualization, "match_visualization.jpg", "image/jpeg"),
        "points_csv": (vis.points_csv, "match_points.csv", "text/csv"),
        "registered_geotiff": (vis.registered_geotiff, "registered.tif", "image/tiff"),
    }

    if artifact == "metrics":
        import json
        metrics = result.metrics.model_dump() if result.metrics else {}
        transform = result.transformation.model_dump() if result.transformation else {}
        config = result.config_used or {}
        payload = {
            "registration_id": reg_id,
            "metrics": metrics,
            "transformation": transform,
            "config_used": config,
            "warnings": result.warnings or [],
        }
        from fastapi.responses import JSONResponse
        return JSONResponse(content=payload, headers={
            "Content-Disposition": f"attachment; filename=metrics_{reg_id}.json"
        })

    if artifact not in artifact_map:
        raise HTTPException(status_code=400, detail=f"Unknown artifact '{artifact}'. Valid: {list(artifact_map.keys()) + ['metrics']}")

    url, filename, media_type = artifact_map[artifact]
    if not url:
        raise HTTPException(status_code=404, detail="Artifact not generated.")

    # Convert URL back to file path
    rel = url.replace("/static/", "")
    file_path = Path(settings.DATA_ROOT) / rel
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk.")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )
