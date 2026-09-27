"""
SELORA Counterfactual Illumination Renderer
Given a relative topographic relief map from estimate_relief_map(),
re-renders the terrain under arbitrary target solar illumination angles.
Uses Lambertian shading: I = max(0, N · L).
"""

from __future__ import annotations
import cv2
import numpy as np
from loguru import logger


def render_at_sun_angle(
    relief_map: np.ndarray,
    target_azimuth: float,
    target_elevation: float,
    gradient_scale: float = 1.5,
) -> np.ndarray:
    """
    Given a relief map from estimate_relief_map(), re-render 
    the terrain as if the sun were at the target position.
    Uses Lambertian shading: I = max(0, N · L)
    Returns uint8 shaded image.

    Args:
        relief_map:       2D array representing relative topographic relief.
        target_azimuth:   Solar azimuth in degrees [0, 360).
        target_elevation: Solar elevation in degrees [5, 85].
        gradient_scale:   Vertical relief sensitivity scaling factor (default: 1.5).

    Returns:
        uint8 2D grayscale shaded image [0, 255].
    """
    if relief_map is None:
        raise ValueError("render_at_sun_angle: relief_map cannot be None")
    if relief_map.ndim != 2:
        raise ValueError(f"render_at_sun_angle expects 2D array, got shape {relief_map.shape}")

    # Ensure float32 normalized in [0, 1]
    if relief_map.dtype == np.uint8:
        z = relief_map.astype(np.float32) / 255.0
    else:
        z_min, z_max = float(relief_map.min()), float(relief_map.max())
        if z_max > z_min:
            z = (relief_map.astype(np.float32) - z_min) / (z_max - z_min)
        else:
            z = np.zeros_like(relief_map, dtype=np.float32)

    # 1. Target illumination unit vector L
    elev_deg = float(np.clip(target_elevation, 5.0, 85.0))
    az_deg = float(target_azimuth % 360.0)

    theta = np.radians(elev_deg)   # elevation above horizon
    phi = np.radians(az_deg)       # azimuth in image plane

    # Solar vector components
    sx = np.cos(theta) * np.cos(phi)
    sy = np.cos(theta) * np.sin(phi)
    sz = np.sin(theta)

    # 2. Surface normal calculation N = [-p, -q, 1] / sqrt(p^2 + q^2 + 1)
    # Smooth relief before differentiation to suppress sub-pixel ripples
    z_smooth = cv2.GaussianBlur(z, (5, 5), 1.5)
    p = (cv2.Sobel(z_smooth, cv2.CV_32F, 1, 0, ksize=3) / 8.0) * gradient_scale
    q = (cv2.Sobel(z_smooth, cv2.CV_32F, 0, 1, ksize=3) / 8.0) * gradient_scale

    norm = np.sqrt(p * p + q * q + 1.0)
    nx = -p / norm
    ny = -q / norm
    nz = 1.0 / norm

    # 3. Lambertian dot product: I = max(0, N · L)
    dot = nx * sx + ny * sy + nz * sz
    shaded = np.clip(dot, 0.0, 1.0)

    # Convert to uint8 grayscale [0, 255]
    shaded_uint8 = (shaded * 255.0).astype(np.uint8)

    logger.debug(
        f"Counterfactual render: target_az={az_deg:.1f}°, target_elev={elev_deg:.1f}°, "
        f"output min={shaded_uint8.min()}, max={shaded_uint8.max()}, mean={shaded_uint8.mean():.1f}"
    )

    return shaded_uint8
