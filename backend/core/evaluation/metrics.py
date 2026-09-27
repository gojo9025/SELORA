"""
SELORA Evaluation Module
Computes registration quality metrics: RMSE, inlier ratio, spatial coverage,
and composite confidence score.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple
import math


@dataclass
class EvaluationResult:
    total_matches: int
    inlier_count: int
    inlier_ratio: float
    rmse: float
    median_reprojection_error: float
    spatial_coverage: float
    confidence: float
    processing_time_sec: float
    transform_model: str
    pyramid_levels_used: int


def compute_reprojection_errors(
    M: np.ndarray,
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    model_type: str,
) -> np.ndarray:
    """Compute per-point reprojection errors."""
    if len(src_pts) == 0:
        return np.array([])
    if model_type == "homography":
        src_h = np.hstack([src_pts, np.ones((len(src_pts), 1), dtype=np.float32)])
        proj = (M @ src_h.T).T
        proj[:, :2] /= proj[:, 2:3]
        errors = np.linalg.norm(proj[:, :2] - dst_pts, axis=1)
    else:
        M23 = M[:2, :] if M.shape == (3, 3) else M
        src_h = np.hstack([src_pts, np.ones((len(src_pts), 1), dtype=np.float32)])
        proj = (M23 @ src_h.T).T
        errors = np.linalg.norm(proj - dst_pts, axis=1)
    return errors


def compute_confidence(
    inlier_ratio: float,
    rmse: float,
    spatial_coverage: float,
    inlier_count: int,
) -> float:
    """
    Compute engineering quality confidence score [0, 1].

    Formula:
        confidence = 0.35 × clamp(inlier_ratio / 0.8)
                   + 0.25 × clamp(1 - rmse / 20)
                   + 0.25 × clamp(spatial_coverage / 0.8)
                   + 0.15 × clamp(inlier_count / 500)

    This is an engineering quality score, not a calibrated probability.
    """
    def clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    c = (
        0.35 * clamp(inlier_ratio / 0.8)
        + 0.25 * clamp(1.0 - rmse / 20.0)
        + 0.25 * clamp(spatial_coverage / 0.8)
        + 0.15 * clamp(inlier_count / 500.0)
    )
    return round(c, 4)


def evaluate(
    total_matches: int,
    inlier_count: int,
    src_inlier_pts: np.ndarray,
    dst_inlier_pts: np.ndarray,
    matrix: np.ndarray,
    model_type: str,
    img_shape: Tuple[int, int],
    processing_time_sec: float,
    pyramid_levels: int = 1,
    grid_size: int = 4,
) -> EvaluationResult:
    """Compute all evaluation metrics."""
    inlier_ratio = inlier_count / total_matches if total_matches > 0 else 0.0

    # Reprojection errors on inliers
    errors = compute_reprojection_errors(matrix, src_inlier_pts, dst_inlier_pts, model_type)
    if len(errors) > 0:
        rmse = float(np.sqrt((errors ** 2).mean()))
        median_err = float(np.median(errors))
    else:
        rmse = 0.0
        median_err = 0.0

    # Spatial coverage
    from core.geometry.verification import compute_spatial_coverage
    coverage = compute_spatial_coverage(dst_inlier_pts, img_shape, grid_size)

    # Confidence
    confidence = compute_confidence(inlier_ratio, rmse, coverage, inlier_count)

    return EvaluationResult(
        total_matches=total_matches,
        inlier_count=inlier_count,
        inlier_ratio=round(inlier_ratio, 4),
        rmse=round(rmse, 4),
        median_reprojection_error=round(median_err, 4),
        spatial_coverage=round(coverage, 4),
        confidence=confidence,
        processing_time_sec=round(processing_time_sec, 3),
        transform_model=model_type,
        pyramid_levels_used=pyramid_levels,
    )
