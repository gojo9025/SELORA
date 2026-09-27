"""
SELORA Preprocessing Module
Handles intensity normalization, CLAHE, gradient/structural representation,
and multi-scale image pyramids.
"""

from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from loguru import logger


@dataclass
class PreprocessingConfig:
    """Configuration for the preprocessing pipeline."""
    grayscale: bool = True
    normalize: bool = True                  # percentile-based normalization
    percentile_low: float = 1.0
    percentile_high: float = 99.0
    clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: Tuple[int, int] = (8, 8)
    gradient_representation: bool = True    # structural / cross-modal
    noise_reduction: Optional[str] = None   # 'gaussian' | 'median' | 'bilateral' | None
    pyramid_levels: int = 3
    min_pyramid_dim: int = 64              # don't go below this on any dimension


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert any image to single-channel uint8 grayscale."""
    if img.ndim == 2:
        return img
    if img.ndim == 3:
        if img.shape[2] == 1:
            return img[:, :, 0]
        if img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img.shape[2] == 4:
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # Multi-band — use luminance-weighted mean of first 3 bands
        band_img = img[:, :, :3].astype(np.float32)
        weights = np.array([0.114, 0.587, 0.299])
        gray = (band_img * weights).sum(axis=2)
        return np.clip(gray, 0, 255).astype(np.uint8)
    raise ValueError(f"Unsupported image ndim={img.ndim}")


def percentile_normalize(
    img: np.ndarray,
    low: float = 1.0,
    high: float = 99.0,
) -> np.ndarray:
    """Stretch image intensities between low and high percentiles to [0, 255]."""
    img_f = img.astype(np.float32)
    lo = np.percentile(img_f, low)
    hi = np.percentile(img_f, high)
    if hi - lo < 1e-6:
        logger.warning("Image has near-uniform intensity; skipping normalization")
        return img
    normalized = np.clip((img_f - lo) / (hi - lo) * 255, 0, 255)
    return normalized.astype(np.uint8)


def apply_clahe(
    img: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """Apply CLAHE contrast-limited adaptive histogram equalization."""
    if img.dtype != np.uint8:
        img = img.astype(np.uint8)
    clahe = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=tile_grid_size,
    )
    return clahe.apply(img)


def gradient_representation(img: np.ndarray) -> np.ndarray:
    """
    Compute a structural representation based on gradient magnitude.
    This is cross-modal invariant — it captures terrain structure
    regardless of absolute intensity or sensor modality.
    """
    img_f = img.astype(np.float32)
    gx = cv2.Sobel(img_f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(img_f, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    # Normalize gradient to [0, 255]
    mag_min, mag_max = magnitude.min(), magnitude.max()
    if mag_max - mag_min < 1e-6:
        return img
    normalized = ((magnitude - mag_min) / (mag_max - mag_min) * 255)
    return normalized.astype(np.uint8)


def reduce_noise(img: np.ndarray, method: Optional[str]) -> np.ndarray:
    """Optional noise reduction. Avoid excessive smoothing on lunar terrain."""
    if method is None:
        return img
    if method == "gaussian":
        return cv2.GaussianBlur(img, (3, 3), 0)
    if method == "median":
        return cv2.medianBlur(img, 3)
    if method == "bilateral":
        return cv2.bilateralFilter(img, 5, 75, 75)
    logger.warning(f"Unknown noise reduction method: {method}")
    return img


def build_pyramid(
    img: np.ndarray,
    levels: int = 3,
    min_dim: int = 64,
) -> List[np.ndarray]:
    """
    Build a Gaussian image pyramid.
    Level 0 = original, Level 1 = 1/2, Level 2 = 1/4, etc.
    """
    pyramid = [img]
    current = img
    for lvl in range(1, levels):
        h, w = current.shape[:2]
        if min(h, w) // 2 < min_dim:
            logger.debug(f"Pyramid stopped at level {lvl} (min dimension reached)")
            break
        current = cv2.pyrDown(current)
        pyramid.append(current)
    return pyramid


def preprocess(
    img: np.ndarray,
    config: PreprocessingConfig,
    use_gradient: Optional[bool] = None,
) -> Tuple[np.ndarray, List[np.ndarray]]:
    """
    Full preprocessing pipeline.

    Returns:
        processed:  final 2D uint8 grayscale image
        pyramid:    list of downsampled versions [original, 1/2, 1/4, ...]
    """
    # 1. Grayscale
    if config.grayscale:
        img = to_grayscale(img)

    # 2. Noise reduction (before normalization for better percentile estimates)
    img = reduce_noise(img, config.noise_reduction)

    # 3. Intensity normalization
    if config.normalize:
        img = percentile_normalize(img, config.percentile_low, config.percentile_high)

    # 4. CLAHE
    if config.clahe:
        img = apply_clahe(img, config.clahe_clip_limit, config.clahe_tile_grid_size)

    # 5. Gradient/structural representation (optional override)
    use_grad = config.gradient_representation if use_gradient is None else use_gradient
    if use_grad:
        img = gradient_representation(img)

    # 6. Pyramid
    pyramid = build_pyramid(img, config.pyramid_levels, config.min_pyramid_dim)

    return img, pyramid
