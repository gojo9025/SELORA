"""
SELORA Benchmark API
POST /api/benchmark/run
GET  /api/benchmark/{id}
Compares multiple methods (ORB, SIFT, AKAZE, SELORA) on the same image pair.
"""

from __future__ import annotations
import uuid
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger
import cv2
import numpy as np
from pathlib import Path

from schemas import BenchmarkRequest, BenchmarkResult, BenchmarkRow
from config import settings
from core.preprocessing.pipeline import preprocess, PreprocessingConfig
from core.features.extractors import create_extractor, extract_multiscale
from core.matching.matcher import match_descriptors
from core.geometry.verification import verify_geometry, compute_spatial_coverage
from core.evaluation.metrics import compute_confidence
from core.pipeline import _image_path, _load_image

router = APIRouter()
_BENCHMARKS: Dict[str, Any] = {}


def _detect_sensor_from_filename(filename: str) -> str:
    fn = filename.lower()
    if "ohrc" in fn:
        return "OHRC"
    if "tmc" in fn:
        return "TMC2"
    if "iirs" in fn:
        return "IIRS"
    return "Unknown"


def _is_cross_modal_pair(src_name: str, ref_name: str) -> bool:
    src_sensor = _detect_sensor_from_filename(src_name)
    ref_sensor = _detect_sensor_from_filename(ref_name)
    if src_sensor != "Unknown" and ref_sensor != "Unknown":
        return src_sensor != ref_sensor
    return False


METHOD_CONFIGS = {
    "orb": {
        "feature": "ORB",
        "n_features": 5000,
        "matcher": "BF",
        "ratio": 0.80,
        "mutual": False,
        "multi_scale": False,
        "gradient": False,
        "models": ["affine"],
    },
    "sift": {
        "feature": "SIFT",
        "n_features": 5000,
        "matcher": "FLANN",
        "ratio": 0.75,
        "mutual": True,
        "multi_scale": True,
        "gradient": False,
        "models": ["affine", "homography"],
    },
    "akaze": {
        "feature": "AKAZE",
        "n_features": 5000,
        "matcher": "BF",
        "ratio": 0.75,
        "mutual": False,
        "multi_scale": False,
        "gradient": False,
        "models": ["affine", "homography"],
    },
    "deep": {
        "feature": "DEEP",
        "n_features": 5000,
        "matcher": "FLANN",
        "ratio": 0.85,
        "mutual": True,
        "multi_scale": False,
        "gradient": False,
        "models": ["affine", "homography"],
    },
    "loftr": {
        "feature": "LOFTR",
        "n_features": 5000,
        "matcher": "LOFTR",
        "ratio": 0.90,
        "mutual": False,
        "multi_scale": False,
        "gradient": False,
        "models": ["homography"],
    },
    "selora_same": {
        "feature": "SIFT",
        "n_features": 8000,
        "matcher": "FLANN",
        "ratio": 0.75,
        "mutual": True,
        "multi_scale": True,
        "gradient": False,   # Disabled for same-modality
        "models": ["similarity", "affine", "homography"],
    },
    "selora_cross": {
        "feature": "SIFT",
        "n_features": 8000,
        "matcher": "FLANN",
        "ratio": 0.75,
        "mutual": True,
        "multi_scale": True,
        "gradient": True,    # Enabled for cross-modal
        "models": ["similarity", "affine", "homography"],
    },
    "selora_relief": {
        "feature": "SIFT",
        "n_features": 8000,
        "matcher": "FLANN",
        "ratio": 0.75,
        "mutual": True,
        "multi_scale": True,
        "gradient": False,
        "photoclinometry": True,
        "models": ["similarity", "affine", "homography"],
    },
    # Backward compatibility alias
    "selora": {
        "feature": "SIFT",
        "n_features": 8000,
        "matcher": "FLANN",
        "ratio": 0.75,
        "mutual": True,
        "multi_scale": True,
        "gradient": False,
        "models": ["similarity", "affine", "homography"],
    },
}

DEFAULT_BENCHMARK_METHODS = ["orb", "sift", "akaze", "deep", "loftr", "selora_same", "selora_cross", "selora_relief"]


def _run_single_method(
    src_raw: np.ndarray,
    ref_raw: np.ndarray,
    method_key: str,
    is_cross_modal: bool = False,
) -> BenchmarkRow:
    if method_key == "selora":
        effective_key = "selora_cross" if is_cross_modal else "selora_same"
        row_name = "SELORA"
    elif method_key == "selora_same":
        effective_key = "selora_same"
        row_name = "SELORA_same"
    elif method_key == "selora_cross":
        effective_key = "selora_cross"
        row_name = "SELORA_cross"
    elif method_key == "selora_relief":
        effective_key = "selora_relief"
        row_name = "SELORA_relief"
    elif method_key == "loftr":
        effective_key = "loftr"
        row_name = "LOFTR"
    else:
        effective_key = method_key
        row_name = method_key.upper()

    cfg = METHOD_CONFIGS.get(effective_key, METHOD_CONFIGS["selora_same"])
    t0 = time.time()

    pre_cfg = PreprocessingConfig(
        grayscale=True,
        normalize=True,
        clahe=True,
        gradient_representation=cfg.get("gradient", False),
        pyramid_levels=3 if cfg["multi_scale"] else 1,
    )

    src_proc, src_pyr = preprocess(src_raw.copy(), pre_cfg)
    ref_proc, ref_pyr = preprocess(ref_raw.copy(), pre_cfg)

    # Photoclinometry Shape-from-Shading relief transform
    if cfg.get("photoclinometry", False):
        try:
            from core.photoclinometry.shading import estimate_relief_map
            src_proc = estimate_relief_map(src_proc, sun_azimuth=45.0, sun_elevation=30.0, albedo_model="lunar_lambert")
            ref_proc = estimate_relief_map(ref_proc, sun_azimuth=225.0, sun_elevation=60.0, albedo_model="lunar_lambert")
            if cfg["multi_scale"]:
                from core.preprocessing.pipeline import build_pyramid
                src_pyr = build_pyramid(src_proc, 3)
                ref_pyr = build_pyramid(ref_proc, 3)
        except Exception as e:
            logger.warning(f"Benchmark photoclinometry failed: {e}")

    # Special handling for LoFTR detector-free learned matcher
    if effective_key == "loftr":
        from core.features.learned import match_loftr
        try:
            src_pts, ref_pts, conf = match_loftr(src_proc, ref_proc)
        except Exception as e:
            logger.error(f"LoFTR execution failed: {e}")
            src_pts = np.zeros((0, 2), dtype=np.float32)
            ref_pts = np.zeros((0, 2), dtype=np.float32)
            conf = np.zeros((0,), dtype=np.float32)

        if len(src_pts) >= 10:
            total_matches = len(src_pts)
            geo = verify_geometry(
                src_pts,
                ref_pts,
                img_shape=ref_proc.shape[:2],
                models=cfg["models"],
                ransac_threshold=3.0,
            )
            best = geo.best_model
            inliers = best.inlier_count if best.valid else 0
            rmse = best.rmse if best.valid else 999.0
            coverage = geo.spatial_coverage
        else:
            total_matches = len(src_pts)
            inliers = 0
            rmse = 999.0
            coverage = 0.0

        inlier_ratio = inliers / total_matches if total_matches > 0 else 0.0
        confidence = compute_confidence(inlier_ratio, rmse, coverage, inliers)
        elapsed = time.time() - t0

        return BenchmarkRow(
            method=row_name,
            matches=total_matches,
            inliers=inliers,
            inlier_ratio=round(inlier_ratio, 4),
            rmse=round(rmse, 4),
            processing_time_sec=round(elapsed, 3),
            coverage=round(coverage, 4),
            confidence=round(confidence, 4),
        )

    extractor = create_extractor(cfg["feature"], cfg["n_features"])

    if cfg["multi_scale"]:
        src_kpd = extract_multiscale(extractor, src_pyr[:3])
        ref_kpd = extract_multiscale(extractor, ref_pyr[:3])
    else:
        src_kpd = extractor.detect_and_compute(src_proc)
        ref_kpd = extractor.detect_and_compute(ref_proc)

    match_result = match_descriptors(
        src_kpd, ref_kpd,
        matcher_type=cfg["matcher"],
        ratio=cfg["ratio"],
        mutual=cfg["mutual"],
        descriptor_type=extractor.descriptor_type,
    )
    total_matches = len(match_result.filtered_matches)

    # Geometry
    if total_matches >= 10:
        geo = verify_geometry(
            match_result.src_pts,
            match_result.dst_pts,
            img_shape=ref_proc.shape[:2],
            models=cfg["models"],
            ransac_threshold=3.0,
        )
        best = geo.best_model
        inliers = best.inlier_count if best.valid else 0
        rmse = best.rmse if best.valid else 999.0
        coverage = geo.spatial_coverage
    else:
        inliers = 0
        rmse = 999.0
        coverage = 0.0

    inlier_ratio = inliers / total_matches if total_matches > 0 else 0.0
    confidence = compute_confidence(inlier_ratio, rmse, coverage, inliers)
    elapsed = time.time() - t0

    return BenchmarkRow(
        method=row_name,
        matches=total_matches,
        inliers=inliers,
        inlier_ratio=round(inlier_ratio, 4),
        rmse=round(rmse, 4),
        processing_time_sec=round(elapsed, 3),
        coverage=round(coverage, 4),
        confidence=round(confidence, 4),
    )


@router.post("/run")
async def run_benchmark(req: BenchmarkRequest):
    src_path = _image_path(req.source_image_id)
    ref_path = _image_path(req.reference_image_id)

    if not src_path or not ref_path:
        raise HTTPException(status_code=404, detail="Image(s) not found.")

    src_raw = _load_image(src_path)
    ref_raw = _load_image(ref_path)

    if src_raw is None or ref_raw is None:
        raise HTTPException(status_code=422, detail="Failed to decode images.")

    src_name = Path(src_path).name if src_path else ""
    ref_name = Path(ref_path).name if ref_path else ""
    is_cross = _is_cross_modal_pair(src_name, ref_name)

    benchmark_id = str(uuid.uuid4())[:12]
    rows: List[BenchmarkRow] = []

    methods_to_run = req.methods if req.methods else DEFAULT_BENCHMARK_METHODS

    for method in methods_to_run:
        method_key = method.lower()
        if method_key not in METHOD_CONFIGS:
            logger.warning(f"Unknown benchmark method: {method}")
            continue
        logger.info(f"[{benchmark_id}] Benchmarking: {method}")
        try:
            row = _run_single_method(src_raw, ref_raw, method_key, is_cross_modal=is_cross)
            rows.append(row)
        except Exception as e:
            logger.error(f"Benchmark method {method} failed: {e}")

    result = BenchmarkResult(benchmark_id=benchmark_id, rows=rows)
    _BENCHMARKS[benchmark_id] = result.model_dump()
    return result


class PresetUploadRequest(BaseModel):
    preset_id: str


PRESETS_DATA = [
    {
        "id": "same_sensor",
        "label": "Same-Sensor (Easy)",
        "source": "demo_same_source.png",
        "reference": "demo_same_reference.png",
        "description": "Same sensor, 5° rotation. Standard case.",
        "difficulty": "easy",
    },
    {
        "id": "cross_sensor",
        "label": "Cross-Sensor OHRC→TMC2 (Hard)",
        "source": "demo_ohrc_source.png",
        "reference": "demo_tmc2_reference.png",
        "description": "20:1 scale ratio, cross-modal simulation.",
        "difficulty": "hard",
    },
    {
        "id": "extreme_illum",
        "label": "Extreme Illumination (Very Hard)",
        "source": "demo_hard_source.png",
        "reference": "demo_hard_reference.png",
        "description": "15° rotation, 40-intensity brightness shift.",
        "difficulty": "very_hard",
    },
]


@router.get("/presets")
async def list_presets():
    """Return available benchmark presets with file paths and difficulty."""
    raw_dir = Path(settings.UPLOAD_DIR)
    available = []
    for p in PRESETS_DATA:
        if (raw_dir / p["source"]).exists() and (raw_dir / p["reference"]).exists():
            available.append(p)
    return {"presets": available}


@router.post("/upload-preset")
async def upload_preset(req: PresetUploadRequest):
    """
    Look up preset by ID, verify files exist in data/raw/, register in _IMAGES,
    and return source_image_id and reference_image_id.
    """
    preset = next((p for p in PRESETS_DATA if p["id"] == req.preset_id), None)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset '{req.preset_id}' not found.")

    raw_dir = Path(settings.UPLOAD_DIR)
    src_file = raw_dir / preset["source"]
    ref_file = raw_dir / preset["reference"]

    if not src_file.exists() or not ref_file.exists():
        raise HTTPException(status_code=404, detail="Preset demo files missing from data/raw/")

    from api.upload import _IMAGES, _detect_sensor, _has_geotiff_metadata

    def register_demo_file(fpath: Path) -> str:
        img_id = fpath.stem
        if img_id not in _IMAGES:
            img = cv2.imread(str(fpath), cv2.IMREAD_UNCHANGED)
            h, w = (img.shape[0], img.shape[1]) if img is not None else (512, 512)
            channels = 1 if img is None or img.ndim == 2 else img.shape[2]
            detected_sensor = _detect_sensor("auto", fpath.name)
            info = {
                "image_id": img_id,
                "filename": fpath.name,
                "width": w,
                "height": h,
                "channels": channels,
                "dtype": str(img.dtype) if img is not None else "uint8",
                "file_size_bytes": fpath.stat().st_size,
                "sensor": detected_sensor,
                "has_geotiff_metadata": _has_geotiff_metadata(str(fpath)),
            }
            _IMAGES[img_id] = info
        return img_id

    src_id = register_demo_file(src_file)
    ref_id = register_demo_file(ref_file)

    return {
        "preset_id": req.preset_id,
        "source_image_id": src_id,
        "reference_image_id": ref_id,
        "label": preset["label"],
        "difficulty": preset["difficulty"],
    }


@router.get("/{benchmark_id}")
async def get_benchmark(benchmark_id: str):
    result = _BENCHMARKS.get(benchmark_id)
    if not result:
        raise HTTPException(status_code=404, detail="Benchmark not found.")
    return result
