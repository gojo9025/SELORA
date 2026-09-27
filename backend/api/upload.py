"""
SELORA Image Upload API
POST /api/images/upload
GET  /api/images/{image_id}
"""

from __future__ import annotations
import uuid
import shutil
from pathlib import Path
from typing import Optional
import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from loguru import logger

from config import settings
from schemas import ImageInfo

router = APIRouter()

# In-memory store for image metadata
_IMAGES: dict[str, dict] = {}


ALLOWED_MIMETYPES = {
    "image/png", "image/jpeg", "image/tiff",
    "image/x-tiff", "image/geotiff",
}
ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}


@router.post("/upload", response_model=ImageInfo, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    sensor: Optional[str] = Form(default="auto"),
):
    """
    Upload a lunar image (PNG/JPG/TIFF/GeoTIFF).
    Returns image metadata and a server-side image_id for subsequent API calls.
    """
    # ── Validate file extension ───────────────────────────────────────────────
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_SUFFIXES)}",
        )

    # ── Read and size-check ───────────────────────────────────────────────────
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {settings.MAX_FILE_SIZE_MB} MB.",
        )

    # ── Decode to validate ────────────────────────────────────────────────────
    arr = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None:
        # Try TIFF via file on disk
        img = _try_load_tiff(content, suffix)
    if img is None:
        raise HTTPException(status_code=422, detail="Image could not be decoded. File may be corrupt.")

    # ── Dimension check ───────────────────────────────────────────────────────
    h = img.shape[0]
    w = img.shape[1]
    if h > settings.MAX_IMAGE_HEIGHT or w > settings.MAX_IMAGE_WIDTH:
        raise HTTPException(
            status_code=413,
            detail=f"Image dimensions ({w}×{h}) exceed maximum ({settings.MAX_IMAGE_WIDTH}×{settings.MAX_IMAGE_HEIGHT}).",
        )

    # ── Check for NaN/Inf ─────────────────────────────────────────────────────
    img_f = img.astype(np.float32)
    if np.isnan(img_f).any() or np.isinf(img_f).any():
        raise HTTPException(status_code=422, detail="Image contains NaN or Inf values.")

    # ── Save to disk ──────────────────────────────────────────────────────────
    image_id = str(uuid.uuid4())[:12]
    save_path = Path(settings.UPLOAD_DIR) / f"{image_id}{suffix}"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(content)

    # ── Detect sensor from user hint ──────────────────────────────────────────
    detected_sensor = _detect_sensor(sensor or "auto", file.filename or "")

    channels = 1 if img.ndim == 2 else img.shape[2]
    dtype_str = str(img.dtype)

    # ── Check for GeoTIFF metadata ────────────────────────────────────────────
    has_geo = _has_geotiff_metadata(str(save_path))

    info = ImageInfo(
        image_id=image_id,
        filename=file.filename or "unknown",
        width=w,
        height=h,
        channels=channels,
        dtype=dtype_str,
        file_size_bytes=len(content),
        sensor=detected_sensor,
        has_geotiff_metadata=has_geo,
    )
    _IMAGES[image_id] = info.model_dump()
    logger.info(f"Uploaded: {image_id} ({w}×{h}, {channels}ch, sensor={detected_sensor})")
    return info


@router.get("/{image_id}", response_model=ImageInfo)
async def get_image(image_id: str):
    if image_id not in _IMAGES:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")
    return _IMAGES[image_id]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_sensor(sensor: str, filename: str) -> str:
    """Determine sensor from user selection or filename heuristics."""
    if sensor and sensor.lower() not in ("auto", "unknown", ""):
        return sensor.upper().replace("-", "").replace("_", "").replace("TMC2", "TMC2")

    fn = filename.upper()
    if "OHRC" in fn:
        return "OHRC"
    if "TMC" in fn or "TMC2" in fn:
        return "TMC2"
    if "IIRS" in fn:
        return "IIRS"
    return "Unknown"


def _try_load_tiff(content: bytes, suffix: str) -> Optional[np.ndarray]:
    """Try to load TIFF via saving to temp file."""
    if suffix not in (".tiff", ".tif"):
        return None
    try:
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(content)
            tmp = f.name
        img = cv2.imread(tmp, cv2.IMREAD_UNCHANGED)
        os.unlink(tmp)
        return img
    except Exception as e:
        logger.warning(f"TIFF fallback load failed: {e}")
        return None


def _has_geotiff_metadata(path: str) -> bool:
    try:
        import rasterio
        with rasterio.open(path) as src:
            return src.crs is not None
    except Exception:
        return False


def get_image_store() -> dict:
    """Expose image store for use by other modules."""
    return _IMAGES
