"""
SELORA Mutual Information (MI) Cross-Modal Registration Module
Information-theoretic intensity-based registration fallback.

When feature matching fails (common in multi-modal remote sensing pairs like
OHRC optical vs. IIRS infrared where gradient distributions and intensities
differ non-linearly), this module performs direct intensity-based registration
by maximizing Shannon Mutual Information (MI).

    MI(A, B) = H(A) + H(B) - H(A, B)

Where H is Shannon entropy computed over the joint 2D intensity histogram.
Optimization is performed via Powell's method or Nelder-Mead in a coarse-to-fine
pyramid structure.
"""

from __future__ import annotations
import cv2
import time
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from scipy.optimize import minimize
from loguru import logger


@dataclass
class MIRegistrationResult:
    """Result of Mutual Information registration."""
    success: bool
    matrix: np.ndarray             # 3x3 transformation matrix
    model: str                     # "similarity" or "affine"
    initial_mi: float              # Mutual information before registration (bits)
    final_mi: float                # Mutual information after registration (bits)
    mi_gain: float                 # final_mi - initial_mi
    iterations: int
    processing_time_sec: float
    message: str


def compute_mi(
    img1: np.ndarray,
    img2: np.ndarray,
    bins: int = 32,
    mask: Optional[np.ndarray] = None,
) -> float:
    """
    Compute Shannon Mutual Information (MI) between two images in bits.

    Args:
        img1, img2: Grayscale images (uint8 or float, same shape)
        bins:       Number of histogram bins per channel (32 or 64 is typical)
        mask:       Optional boolean mask indicating valid non-background pixels

    Returns:
        Mutual information in bits. Higher = more information shared.
    """
    if img1.shape != img2.shape:
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = img1[:h, :w]
        img2 = img2[:h, :w]
        if mask is not None:
            mask = mask[:h, :w]

    if mask is None:
        mask = (img1 > 5) & (img2 > 5)

    v1 = img1[mask].ravel()
    v2 = img2[mask].ravel()

    if len(v1) < 100:
        return 0.0

    # 2D Joint histogram
    hist_2d, _, _ = np.histogram2d(v1, v2, bins=bins, range=[[0, 256], [0, 256]])

    # Convert to probabilities
    pxy = hist_2d / np.sum(hist_2d)
    px = np.sum(pxy, axis=1)  # Marginal for img1
    py = np.sum(pxy, axis=0)  # Marginal for img2

    # Non-zero entries only for numerical stability
    nzs = pxy > 0
    nz_x = px > 0
    nz_y = py > 0

    h_xy = -np.sum(pxy[nzs] * np.log2(pxy[nzs]))
    h_x = -np.sum(px[nz_x] * np.log2(px[nz_x]))
    h_y = -np.sum(py[nz_y] * np.log2(py[nz_y]))

    mi = h_x + h_y - h_xy
    return float(max(0.0, mi))


def _params_to_matrix(params: np.ndarray, model: str, center: Tuple[float, float]) -> np.ndarray:
    """Convert optimization parameter vector to a 3x3 transformation matrix."""
    cx, cy = center
    if model == "similarity":
        # params: [tx, ty, angle_deg, scale]
        tx, ty, angle, scale = params
        rad = np.radians(angle)
        cos_a = np.cos(rad) * scale
        sin_a = np.sin(rad) * scale

        # Transform around image center
        # T(cx+tx, cy+ty) * R * S * T(-cx, -cy)
        m = np.array([
            [cos_a, -sin_a, (1 - cos_a) * cx + sin_a * cy + tx],
            [sin_a,  cos_a, -sin_a * cx + (1 - cos_a) * cy + ty],
            [0.0,    0.0,   1.0]
        ], dtype=np.float64)
        return m

    elif model == "affine":
        # params: [a11, a12, tx, a21, a22, ty]
        a11, a12, tx, a21, a22, ty = params
        return np.array([
            [a11, a12, tx],
            [a21, a22, ty],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

    elif model == "translation":
        tx, ty = params
        return np.array([
            [1.0, 0.0, tx],
            [0.0, 1.0, ty],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

    raise ValueError(f"Unknown model: {model}")


def _matrix_to_params(matrix: np.ndarray, model: str, center: Tuple[float, float]) -> np.ndarray:
    """Decompose 3x3 matrix into initial parameter vector."""
    cx, cy = center
    if model == "similarity":
        # Extract rotation, scale, translation
        a = matrix[0, 0]
        b = matrix[1, 0]
        scale = float(np.hypot(a, b))
        angle = float(np.degrees(np.arctan2(b, a)))
        tx = float(matrix[0, 2])
        ty = float(matrix[1, 2])
        return np.array([tx, ty, angle, scale if scale > 0 else 1.0], dtype=np.float64)

    elif model == "affine":
        return np.array([
            matrix[0, 0], matrix[0, 1], matrix[0, 2],
            matrix[1, 0], matrix[1, 1], matrix[1, 2]
        ], dtype=np.float64)

    elif model == "translation":
        return np.array([matrix[0, 2], matrix[1, 2]], dtype=np.float64)

    return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)


def register_mutual_information(
    source: np.ndarray,
    reference: np.ndarray,
    model: str = "similarity",
    initial_matrix: Optional[np.ndarray] = None,
    max_iter: int = 60,
    pyramid_levels: int = 2,
) -> MIRegistrationResult:
    """
    Perform direct intensity-based image registration using Mutual Information.

    Args:
        source:         Source grayscale image (uint8)
        reference:      Reference grayscale image (uint8)
        model:          Transformation type: "similarity", "affine", or "translation"
        initial_matrix: Optional 3x3 prior matrix (e.g. from coarse feature matching)
        max_iter:       Maximum optimizer iterations per pyramid level
        pyramid_levels: Number of multi-resolution pyramid levels for coarse-to-fine search

    Returns:
        MIRegistrationResult with optimal matrix and convergence statistics.
    """
    start_t = time.time()

    # Pre-check grayscale
    if source.ndim == 3:
        source = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    if reference.ndim == 3:
        reference = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)

    h_ref, w_ref = reference.shape[:2]
    center = (w_ref / 2.0, h_ref / 2.0)

    # Initial matrix setup
    if initial_matrix is None:
        curr_matrix = np.eye(3, dtype=np.float64)
    else:
        curr_matrix = initial_matrix.copy().astype(np.float64)
        if curr_matrix.shape == (2, 3):
            curr_matrix = np.vstack([curr_matrix, [0.0, 0.0, 1.0]])

    # Compute baseline initial MI
    warped_init = cv2.warpPerspective(source, curr_matrix, (w_ref, h_ref))
    initial_mi = compute_mi(warped_init, reference)

    # Build multi-resolution pyramid
    src_pyr = [source]
    ref_pyr = [reference]
    for _ in range(pyramid_levels - 1):
        src_pyr.append(cv2.pyrDown(src_pyr[-1]))
        ref_pyr.append(cv2.pyrDown(ref_pyr[-1]))

    # Scale matrices for coarse levels
    # Optimization goes from coarsest (highest downsample) to finest (original)
    for level in reversed(range(pyramid_levels)):
        src_lvl = src_pyr[level]
        ref_lvl = ref_pyr[level]
        scale_factor = 2 ** level

        lvl_h, lvl_w = ref_lvl.shape[:2]
        lvl_center = (lvl_w / 2.0, lvl_h / 2.0)

        # Rescale matrix for current pyramid level
        S_down = np.array([
            [1.0 / scale_factor, 0.0, 0.0],
            [0.0, 1.0 / scale_factor, 0.0],
            [0.0, 0.0, 1.0]
        ])
        S_up = np.linalg.inv(S_down)
        lvl_matrix = S_down @ curr_matrix @ S_up

        init_params = _matrix_to_params(lvl_matrix, model, lvl_center)

        # Objective function to MINIMIZE (-MI)
        def loss_func(p):
            T = _params_to_matrix(p, model, lvl_center)
            # Warp source to reference frame
            warped = cv2.warpPerspective(
                src_lvl, T, (lvl_w, lvl_h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0
            )
            # Valid mutual mask
            mask = (warped > 5) & (ref_lvl > 5)
            if np.count_nonzero(mask) < 0.15 * lvl_w * lvl_h:
                # Penalty for loss of overlap
                return 10.0
            mi = compute_mi(warped, ref_lvl, bins=32, mask=mask)
            return -mi

        # Bounds / step constraints
        try:
            res = minimize(
                loss_func,
                init_params,
                method="Powell",
                options={"maxiter": max_iter, "xtol": 1e-3, "ftol": 1e-3}
            )
            opt_lvl_matrix = _params_to_matrix(res.x, model, lvl_center)
            # Upscale matrix back to full resolution for the next level
            curr_matrix = S_up @ opt_lvl_matrix @ S_down
        except Exception as opt_err:
            logger.warning(f"MI optimization failed at level {level}: {opt_err}")

    # Evaluate final alignment
    warped_final = cv2.warpPerspective(source, curr_matrix, (w_ref, h_ref))
    final_mi = compute_mi(warped_final, reference)
    elapsed = time.time() - start_t

    success = final_mi >= initial_mi or (final_mi > 0.5)

    return MIRegistrationResult(
        success=success,
        matrix=curr_matrix,
        model=model,
        initial_mi=initial_mi,
        final_mi=final_mi,
        mi_gain=final_mi - initial_mi,
        iterations=max_iter * pyramid_levels,
        processing_time_sec=elapsed,
        message=f"MI maximized from {initial_mi:.3f} to {final_mi:.3f} bits (+{final_mi - initial_mi:.3f})"
    )
