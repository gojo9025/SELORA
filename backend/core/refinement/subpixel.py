"""
SELORA Sub-Pixel Refinement Module
Phase-correlation based sub-pixel registration refinement.

After coarse feature-based alignment, this module computes a Fourier-domain
cross-correlation between the warped source and the reference to detect
residual sub-pixel shifts with accuracy down to ~0.1 pixels.

This is the standard refinement technique used in production remote sensing
pipelines (ENVI, ERDAS IMAGINE, ASP).
"""

from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from loguru import logger


@dataclass
class SubPixelResult:
    """Result of sub-pixel refinement."""
    dx: float                      # Sub-pixel shift in X (columns)
    dy: float                      # Sub-pixel shift in Y (rows)
    peak_value: float              # Correlation peak value (0-1, higher = more confident)
    refined_matrix: np.ndarray     # Updated transformation matrix
    improvement_px: float          # Magnitude of the sub-pixel correction applied


def _to_gray_float(img: np.ndarray) -> np.ndarray:
    """Convert image to single-channel float32."""
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    return gray.astype(np.float32)


def _apply_window(img: np.ndarray) -> np.ndarray:
    """Apply a Hann window to reduce spectral leakage in FFT."""
    h, w = img.shape
    win_h = np.hanning(h).reshape(-1, 1)
    win_w = np.hanning(w).reshape(1, -1)
    window = win_h * win_w
    return img * window


def phase_correlate(
    warped: np.ndarray,
    reference: np.ndarray,
    window_size: Optional[int] = None,
) -> Tuple[float, float, float]:
    """
    Compute sub-pixel shift between warped source and reference using
    phase correlation in the Fourier domain.

    Uses OpenCV's phaseCorrelate which implements the Fourier Shift Theorem
    with sub-pixel interpolation via weighted centroid of the correlation peak.

    Args:
        warped:     Warped source image (after coarse alignment)
        reference:  Reference image
        window_size: Optional window size for local correlation

    Returns:
        (dx, dy, peak_value) — sub-pixel shift and confidence
    """
    src_gray = _to_gray_float(warped)
    ref_gray = _to_gray_float(reference)

    # Ensure same dimensions
    h = min(src_gray.shape[0], ref_gray.shape[0])
    w = min(src_gray.shape[1], ref_gray.shape[1])
    src_gray = src_gray[:h, :w]
    ref_gray = ref_gray[:h, :w]

    # Create valid mask (exclude border regions where warped image is black)
    src_mask = src_gray > 5.0  # pixels that aren't black border
    ref_mask = ref_gray > 5.0

    valid_mask = src_mask & ref_mask
    if valid_mask.sum() < 0.1 * h * w:
        logger.warning("Sub-pixel: insufficient overlap for refinement")
        return 0.0, 0.0, 0.0

    # Apply windowing to reduce edge effects
    src_windowed = _apply_window(src_gray)
    ref_windowed = _apply_window(ref_gray)

    # OpenCV phase correlation with sub-pixel accuracy
    (dx, dy), peak = cv2.phaseCorrelate(src_windowed, ref_windowed)

    return float(dx), float(dy), float(peak)


def phase_correlate_multiregion(
    warped: np.ndarray,
    reference: np.ndarray,
    grid: int = 3,
    min_overlap_fraction: float = 0.3,
) -> Tuple[float, float, float]:
    """
    Robust sub-pixel estimation by computing phase correlation on a grid
    of sub-regions, then taking the median shift. This is more robust
    to local distortions than a single global correlation.

    Args:
        warped:     Warped source image
        reference:  Reference image
        grid:       NxN grid of sub-regions
        min_overlap_fraction: minimum valid pixel fraction per region

    Returns:
        (dx, dy, median_peak) — robust sub-pixel shift
    """
    src_gray = _to_gray_float(warped)
    ref_gray = _to_gray_float(reference)

    h = min(src_gray.shape[0], ref_gray.shape[0])
    w = min(src_gray.shape[1], ref_gray.shape[1])
    src_gray = src_gray[:h, :w]
    ref_gray = ref_gray[:h, :w]

    cell_h = h // grid
    cell_w = w // grid

    shifts_x = []
    shifts_y = []
    peaks = []

    for gi in range(grid):
        for gj in range(grid):
            y0 = gi * cell_h
            x0 = gj * cell_w
            y1 = min(y0 + cell_h, h)
            x1 = min(x0 + cell_w, w)

            src_patch = src_gray[y0:y1, x0:x1]
            ref_patch = ref_gray[y0:y1, x0:x1]

            # Skip patches with too much black border
            valid_frac = (src_patch > 5.0).mean()
            if valid_frac < min_overlap_fraction:
                continue

            src_win = _apply_window(src_patch)
            ref_win = _apply_window(ref_patch)

            try:
                (dx, dy), peak = cv2.phaseCorrelate(src_win, ref_win)
                if peak > 0.05:  # minimum confidence threshold
                    shifts_x.append(dx)
                    shifts_y.append(dy)
                    peaks.append(peak)
            except cv2.error:
                continue

    if len(shifts_x) < 2:
        # Fall back to global correlation
        logger.info("Sub-pixel: multiregion had <2 valid regions, using global")
        return phase_correlate(warped, reference)

    # Use median for robustness against outlier regions
    dx = float(np.median(shifts_x))
    dy = float(np.median(shifts_y))
    peak = float(np.median(peaks))

    logger.info(
        f"Sub-pixel multiregion: dx={dx:.4f}, dy={dy:.4f}, "
        f"peak={peak:.4f} ({len(shifts_x)}/{grid*grid} regions)"
    )
    return dx, dy, peak


def refine_registration(
    warped: np.ndarray,
    reference: np.ndarray,
    coarse_matrix: np.ndarray,
    model_type: str,
    use_multiregion: bool = True,
) -> SubPixelResult:
    """
    Apply sub-pixel refinement to an already-warped registration.

    Takes the coarse transformation matrix, estimates residual sub-pixel
    shift via phase correlation, and composes the correction into the
    final refined matrix.

    Args:
        warped:         Warped source image (output of coarse registration)
        reference:      Reference image
        coarse_matrix:  The coarse transformation matrix (3x3)
        model_type:     'similarity' | 'affine' | 'homography'
        use_multiregion: If True, use grid-based robust estimation

    Returns:
        SubPixelResult with refined matrix and shift information
    """
    # Estimate sub-pixel residual
    if use_multiregion:
        dx, dy, peak = phase_correlate_multiregion(warped, reference)
    else:
        dx, dy, peak = phase_correlate(warped, reference)

    magnitude = np.sqrt(dx**2 + dy**2)
    logger.info(f"Sub-pixel refinement: dx={dx:.4f}px, dy={dy:.4f}px, "
                f"magnitude={magnitude:.4f}px, peak={peak:.4f}")

    # Sanity check: if shift is too large, something went wrong
    if magnitude > 5.0:
        logger.warning(f"Sub-pixel shift too large ({magnitude:.2f}px), clamping to 0")
        dx, dy, peak = 0.0, 0.0, 0.0
        magnitude = 0.0

    # Compose sub-pixel translation into the coarse matrix
    # T_refined = T_subpixel @ T_coarse
    # where T_subpixel is a pure translation [dx, dy]
    T_sub = np.array([
        [1.0, 0.0, dx],
        [0.0, 1.0, dy],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)

    # Ensure coarse matrix is 3x3
    if coarse_matrix.shape == (2, 3):
        M_coarse = np.vstack([coarse_matrix, [0, 0, 1]])
    else:
        M_coarse = coarse_matrix.copy().astype(np.float64)

    # The sub-pixel correction is applied in the reference coordinate system,
    # so we pre-multiply: T_refined = T_sub @ T_coarse
    refined = T_sub @ M_coarse

    # Convert back to original format if needed
    if model_type in ("similarity", "affine") and coarse_matrix.shape == (2, 3):
        refined_out = refined[:2, :]
    else:
        refined_out = refined

    return SubPixelResult(
        dx=dx,
        dy=dy,
        peak_value=peak,
        refined_matrix=refined_out,
        improvement_px=magnitude,
    )
