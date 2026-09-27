"""
SELORA Geometric Verification Module
RANSAC-based outlier rejection, multi-model fitting,
model selection, and spatial coverage analysis.
"""

from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from loguru import logger


@dataclass
class ModelFitResult:
    """Result of fitting one geometric model."""
    model_type: str                          # 'similarity' | 'affine' | 'homography'
    matrix: Optional[np.ndarray]            # 2x3 or 3x3
    inlier_mask: Optional[np.ndarray]       # bool array length N
    inlier_count: int
    inlier_ratio: float
    rmse: float
    score: float                             # composite model quality score
    valid: bool


@dataclass
class GeometryResult:
    """Final geometry result after model comparison."""
    best_model: ModelFitResult
    all_models: List[ModelFitResult]
    src_inlier_pts: np.ndarray              # Nx2 after RANSAC
    dst_inlier_pts: np.ndarray
    spatial_coverage: float


def _fit_homography(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    ransac_threshold: float,
    max_iter: int,
) -> ModelFitResult:
    if len(src_pts) < 4:
        return ModelFitResult("homography", None, None, 0, 0.0, 999.0, 0.0, False)
    try:
        H, mask = cv2.findHomography(
            src_pts, dst_pts,
            method=cv2.USAC_MAGSAC,
            ransacReprojThreshold=ransac_threshold,
            maxIters=max_iter,
            confidence=0.995,
        )
        if H is None:
            return ModelFitResult("homography", None, None, 0, 0.0, 999.0, 0.0, False)
        mask = mask.ravel().astype(bool)
        inliers = mask.sum()
        total = len(mask)
        ratio = inliers / total if total > 0 else 0.0
        rmse = _compute_rmse(H, src_pts[mask], dst_pts[mask], "homography")
        score = _model_score(ratio, rmse, inliers)
        return ModelFitResult("homography", H, mask, int(inliers), ratio, rmse, score, True)
    except cv2.error as e:
        logger.warning(f"Homography fitting failed: {e}")
        return ModelFitResult("homography", None, None, 0, 0.0, 999.0, 0.0, False)


def _fit_affine(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    ransac_threshold: float,
    max_iter: int,
) -> ModelFitResult:
    if len(src_pts) < 4:
        return ModelFitResult("affine", None, None, 0, 0.0, 999.0, 0.0, False)
    try:
        A, mask = cv2.estimateAffine2D(
            src_pts, dst_pts,
            method=cv2.RANSAC,
            ransacReprojThreshold=ransac_threshold,
            maxIters=max_iter,
            confidence=0.995,
        )
        if A is None:
            return ModelFitResult("affine", None, None, 0, 0.0, 999.0, 0.0, False)
        mask = mask.ravel().astype(bool)
        inliers = mask.sum()
        total = len(mask)
        ratio = inliers / total if total > 0 else 0.0
        # Convert 2x3 affine to 3x3 for consistent RMSE calculation
        A3x3 = np.vstack([A, [0, 0, 1]])
        rmse = _compute_rmse(A3x3, src_pts[mask], dst_pts[mask], "affine")
        score = _model_score(ratio, rmse, inliers)
        return ModelFitResult("affine", A, mask, int(inliers), ratio, rmse, score, True)
    except cv2.error as e:
        logger.warning(f"Affine fitting failed: {e}")
        return ModelFitResult("affine", None, None, 0, 0.0, 999.0, 0.0, False)


def _fit_similarity(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    ransac_threshold: float,
    max_iter: int,
) -> ModelFitResult:
    if len(src_pts) < 3:
        return ModelFitResult("similarity", None, None, 0, 0.0, 999.0, 0.0, False)
    try:
        S, mask = cv2.estimateAffinePartial2D(
            src_pts, dst_pts,
            method=cv2.RANSAC,
            ransacReprojThreshold=ransac_threshold,
            maxIters=max_iter,
            confidence=0.995,
        )
        if S is None:
            return ModelFitResult("similarity", None, None, 0, 0.0, 999.0, 0.0, False)
        mask = mask.ravel().astype(bool)
        inliers = mask.sum()
        total = len(mask)
        ratio = inliers / total if total > 0 else 0.0
        S3x3 = np.vstack([S, [0, 0, 1]])
        rmse = _compute_rmse(S3x3, src_pts[mask], dst_pts[mask], "similarity")
        score = _model_score(ratio, rmse, inliers)
        return ModelFitResult("similarity", S, mask, int(inliers), ratio, rmse, score, True)
    except cv2.error as e:
        logger.warning(f"Similarity fitting failed: {e}")
        return ModelFitResult("similarity", None, None, 0, 0.0, 999.0, 0.0, False)


def _compute_rmse(
    M: np.ndarray,
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    model_type: str,
) -> float:
    """Compute RMSE reprojection error for a set of inlier point pairs."""
    if len(src_pts) == 0:
        return 0.0
    if model_type == "homography":
        src_h = np.hstack([src_pts, np.ones((len(src_pts), 1))])
        proj = (M @ src_h.T).T
        proj[:, :2] /= proj[:, 2:3]
        errors = np.linalg.norm(proj[:, :2] - dst_pts, axis=1)
    else:
        # affine/similarity: M is 2x3 or 3x3
        if M.shape == (3, 3):
            M23 = M[:2, :]
        else:
            M23 = M
        src_h = np.hstack([src_pts, np.ones((len(src_pts), 1))])
        proj = (M23 @ src_h.T).T
        errors = np.linalg.norm(proj - dst_pts, axis=1)
    rmse = float(np.sqrt((errors ** 2).mean()))
    return rmse


def _model_score(inlier_ratio: float, rmse: float, inlier_count: int) -> float:
    """Higher score = better model. Balances inlier ratio and accuracy."""
    ratio_score = inlier_ratio
    rmse_score = max(0.0, 1.0 - rmse / 20.0)
    count_score = min(1.0, inlier_count / 200.0)
    return 0.5 * ratio_score + 0.35 * rmse_score + 0.15 * count_score


def compute_spatial_coverage(
    pts: np.ndarray,
    img_shape: Tuple[int, int],
    grid: int = 4,
) -> float:
    """
    Divide image into grid×grid cells.
    Measure fraction of cells that contain at least one inlier keypoint.
    """
    if len(pts) == 0:
        return 0.0
    h, w = img_shape
    cell_h = h / grid
    cell_w = w / grid
    occupied = set()
    for x, y in pts:
        ci = min(int(y / cell_h), grid - 1)
        cj = min(int(x / cell_w), grid - 1)
        occupied.add((ci, cj))
    return len(occupied) / (grid * grid)


def verify_geometry(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    img_shape: Tuple[int, int],
    models: List[str],
    ransac_threshold: float = 3.0,
    max_iter: int = 2000,
) -> GeometryResult:
    """
    Fit multiple geometric models, select the best one.
    Returns the best ModelFitResult and spatial coverage.
    """
    all_results: List[ModelFitResult] = []

    for model in models:
        if model == "homography":
            r = _fit_homography(src_pts, dst_pts, ransac_threshold, max_iter)
        elif model == "affine":
            r = _fit_affine(src_pts, dst_pts, ransac_threshold, max_iter)
        elif model == "similarity":
            r = _fit_similarity(src_pts, dst_pts, ransac_threshold, max_iter)
        else:
            logger.warning(f"Unknown geometry model: {model}")
            continue
        all_results.append(r)
        logger.info(
            f"Model {model}: inliers={r.inlier_count} "
            f"ratio={r.inlier_ratio:.2%} rmse={r.rmse:.2f} score={r.score:.3f}"
        )

    valid_results = [r for r in all_results if r.valid and r.inlier_count > 0]
    if not valid_results:
        dummy = ModelFitResult("homography", None, None, 0, 0.0, 999.0, 0.0, False)
        return GeometryResult(dummy, all_results, np.zeros((0, 2)), np.zeros((0, 2)), 0.0)

    # Select highest-scoring model
    best = max(valid_results, key=lambda r: r.score)
    logger.info(f"Selected model: {best.model_type} (score={best.score:.3f})")

    mask = best.inlier_mask
    src_inliers = src_pts[mask]
    dst_inliers = dst_pts[mask]
    coverage = compute_spatial_coverage(dst_inliers, img_shape)

    return GeometryResult(best, all_results, src_inliers, dst_inliers, coverage)


def decompose_homography(H: np.ndarray) -> Dict[str, float]:
    """
    Decompose a homography into approximate rotation, scale, translation.
    Valid only when the homography is close to a similarity/affine transform.
    """
    try:
        # Approximate from top-left 2x2 block
        A = H[:2, :2] / H[2, 2]
        tx = H[0, 2] / H[2, 2]
        ty = H[1, 2] / H[2, 2]
        scale_x = np.sqrt(A[0, 0] ** 2 + A[1, 0] ** 2)
        scale_y = np.sqrt(A[0, 1] ** 2 + A[1, 1] ** 2)
        scale = float((scale_x + scale_y) / 2)
        angle = float(np.degrees(np.arctan2(A[1, 0], A[0, 0])))
        return {
            "rotation_deg": angle,
            "scale": scale,
            "translation_x": float(tx),
            "translation_y": float(ty),
        }
    except Exception:
        return {}


def decompose_transform_full(
    matrix: np.ndarray,
    model_type: str,
) -> Dict[str, Any]:
    """
    Full geometric decomposition of any 2x3 or 3x3 transformation matrix.

    Uses SVD to extract:
      - rotation_deg: net rotation angle
      - scale_x / scale_y: per-axis scaling
      - scale: uniform scale (average)
      - shear: shear factor (tan of skew angle)
      - aspect_ratio: scale_x / scale_y (deviation from 1.0 indicates anisotropic distortion)
      - translation_x / translation_y: pixel offsets
      - perspective_kx / perspective_ky: perspective keystoning components (homography row 3)
      - perspective_strength: L2 norm of perspective row — 0 for affine-like, higher for projective warp
      - determinant: matrix determinant (should be > 0; <0 indicates reflection)
      - condition_number: ratio of singular values — measures numerical health
      - dof: degrees of freedom of the model

    Returns a dict suitable for direct inclusion in the API schema.
    """
    result: Dict[str, Any] = {
        "model_type": model_type,
        "dof": {"similarity": 4, "affine": 6, "homography": 8}.get(model_type, 0),
    }

    try:
        # Normalize to 3x3
        if matrix.shape == (2, 3):
            H = np.vstack([matrix, [0, 0, 1]])
        else:
            H = matrix.copy()

        # Normalize by H[2,2] for homographies
        if abs(H[2, 2]) > 1e-8:
            H = H / H[2, 2]

        # ── Translation ──
        result["translation_x"] = float(H[0, 2])
        result["translation_y"] = float(H[1, 2])

        # ── Perspective keystoning ──
        px, py = float(H[2, 0]), float(H[2, 1])
        result["perspective_kx"] = px
        result["perspective_ky"] = py
        result["perspective_strength"] = float(np.hypot(px, py))

        # ── Affine part: upper-left 2x2 → SVD decomposition ──
        A = H[:2, :2]
        det = float(np.linalg.det(A))
        result["determinant"] = det

        # SVD: A = U · S · Vt  =>  rotation, scale, rotation
        U, S, Vt = np.linalg.svd(A)

        # Singular values = per-axis scales
        sx, sy = float(S[0]), float(S[1])
        result["scale_x"] = sx
        result["scale_y"] = sy
        result["scale"] = (sx + sy) / 2.0
        result["aspect_ratio"] = sx / sy if sy > 1e-8 else float("inf")
        result["condition_number"] = sx / sy if sy > 1e-8 else float("inf")

        # Net rotation: combine U and Vt rotations
        angle_u = float(np.degrees(np.arctan2(U[1, 0], U[0, 0])))
        angle_v = float(np.degrees(np.arctan2(Vt[1, 0], Vt[0, 0])))
        # For a pure rotation+scale, angle_u and angle_v combine
        rotation = angle_u + angle_v
        # Normalize to [-180, 180]
        rotation = float(((rotation + 180) % 360) - 180)
        result["rotation_deg"] = rotation

        # Shear: reconstruct R^{-1} A to isolate shear
        cos_r = np.cos(np.radians(rotation))
        sin_r = np.sin(np.radians(rotation))
        R_inv = np.array([[cos_r, sin_r], [-sin_r, cos_r]])
        M = R_inv @ A
        # M should be approximately [[sx, shear*sy], [0, sy]]
        shear = float(M[0, 1] / M[1, 1]) if abs(M[1, 1]) > 1e-8 else 0.0
        result["shear"] = shear

        # ── Classify distortion severity ──
        distortion_flags: List[str] = []
        if abs(rotation) > 1.0:
            distortion_flags.append(f"Rotation: {rotation:.2f}°")
        if abs(1.0 - result["scale"]) > 0.02:
            distortion_flags.append(f"Scale: {result['scale']:.4f}×")
        if abs(result["aspect_ratio"] - 1.0) > 0.03:
            distortion_flags.append(f"Anisotropic: {result['aspect_ratio']:.3f}")
        if abs(shear) > 0.01:
            distortion_flags.append(f"Shear: {shear:.4f}")
        if result["perspective_strength"] > 1e-6:
            distortion_flags.append(f"Perspective: {result['perspective_strength']:.2e}")
        if det < 0:
            distortion_flags.append("Reflection detected")

        result["distortion_flags"] = distortion_flags
        result["distortion_summary"] = (
            "Near-identity (minimal distortion)"
            if len(distortion_flags) == 0
            else " · ".join(distortion_flags)
        )

    except Exception as e:
        logger.warning(f"Transform decomposition failed: {e}")
        result["error"] = str(e)

    return result
