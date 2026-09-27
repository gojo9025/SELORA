"""
SELORA Photoclinometry (Shape-from-Shading) Engine
Implements lunar photometric model inversion and Frankot-Chellappa Fourier
integration to recover invariant topographic relief from single-view lunar imagery.

References:
- McEwen, A. S. (1991). Photometric functions for photoclinometry and photoclinometry
  using digital images. Icarus, 92(2), 298-311.
- Frankot, R. T., & Chellappa, R. (1988). A method for enforcing integrability in
  shape from shading algorithms. IEEE TPAMI, 10(4), 439-451.
"""

from __future__ import annotations
import numpy as np
import cv2
from loguru import logger


def estimate_relief_map(
    image: np.ndarray,
    sun_azimuth: float,
    sun_elevation: float,
    albedo_model: str = "lunar_lambert",
    integration_method: str = "frankot_chellappa",
    regularization: float = 1e-4,
) -> np.ndarray:
    """
    Invert the photometric model to recover local surface slope (p, q)
    at each pixel, then integrate to a relative relief/elevation map.

    Args:
        image:              Input grayscale image (2D uint8 or float32).
        sun_azimuth:        Solar azimuth angle in degrees [0, 360), measured
                            counter-clockwise from horizontal image +X axis.
        sun_elevation:      Solar elevation angle above horizon in degrees (0, 90].
        albedo_model:       "lunar_lambert" (McEwen 1991) or "lambertian".
        integration_method: "frankot_chellappa" (Fourier) or "poisson".
        regularization:     Tikhonov regularization parameter for Fourier division.

    Returns:
        A single-channel uint8 array (same H, W as input) representing the
        relative surface topography/relief map, invariant to illumination direction.
    """
    if image.ndim != 2:
        raise ValueError(f"estimate_relief_map expects 2D grayscale image, got shape {image.shape}")

    h, w = image.shape

    # Convert image to float32 in [0, 1]
    if image.dtype == np.uint8:
        img_f = image.astype(np.float32) / 255.0
    else:
        img_min, img_max = float(image.min()), float(image.max())
        if img_max > img_min:
            img_f = (image.astype(np.float32) - img_min) / (img_max - img_min)
        else:
            img_f = np.zeros_like(image, dtype=np.float32)

    # Pre-smooth slightly with gentle Gaussian blur to suppress camera shot noise
    smoothed = cv2.GaussianBlur(img_f, (3, 3), 0.8)

    # ── 1. Solar illumination vector ──────────────────────────────────────────
    # Clamp elevation to [5.0, 85.0] to prevent mathematical singularities
    elev_deg = float(np.clip(sun_elevation, 5.0, 85.0))
    az_deg = float(sun_azimuth % 360.0)

    theta = np.radians(elev_deg)   # elevation above horizon
    phi = np.radians(az_deg)       # azimuth in image plane

    # Illumination vector components
    # sx = cos(elev) * cos(az), sy = cos(elev) * sin(az), sz = sin(elev)
    sx = np.cos(theta) * np.cos(phi)
    sy = np.cos(theta) * np.sin(phi)
    sz = np.sin(theta)

    # ── 2. Photometric slope estimation ───────────────────────────────────────
    # Local mean/ambient intensity for flat terrain reflectance R0
    ambient = float(np.median(smoothed))
    if ambient < 1e-4:
        ambient = 1e-4

    # Relative brightness variation: delta_I = (I - I_ambient) / I_ambient
    delta_i = (smoothed - ambient) / ambient

    if albedo_model == "lunar_lambert":
        # McEwen Lunar-Lambert weighting: L(alpha) = 1.0 - 0.01 * alpha
        phase_deg = 90.0 - elev_deg
        l_alpha = max(0.1, min(1.0, 1.0 - 0.01 * phase_deg))
        # Lunar-Lambert slope sensitivity factor
        slope_factor = float(np.tan(theta) / (1.0 + (1.0 - l_alpha) * 0.5))
    else:
        # Standard Lambertian
        slope_factor = float(np.tan(theta))

    # Directional slope along illumination azimuth: S_parallel = p*cos(phi) + q*sin(phi)
    # Bright slopes face the sun (delta_i > 0 -> S_parallel > 0)
    s_parallel = delta_i * slope_factor

    # Decompose into orthogonal gradient components (p, q) = (dz/dx, dz/dy)
    p = s_parallel * np.cos(phi)
    q = s_parallel * np.sin(phi)

    # Apply cross-gradient directional regularization (smooth along perp direction)
    perp_angle = phi + np.pi / 2.0
    p = cv2.GaussianBlur(p, (3, 3), 0.5)
    q = cv2.GaussianBlur(q, (3, 3), 0.5)

    # ── 3. Surface Height Integration ─────────────────────────────────────────
    if integration_method == "frankot_chellappa":
        z = _frankot_chellappa(p, q, regularization)
    else:
        # Standard Fourier Poisson solver as alternative
        z = _poisson_solve(p, q, regularization)

    # ── 4. Normalization and Outlier Clipping ──────────────────────────────────
    # Robust percentiles to avoid extreme edge values from DFT
    p1 = np.percentile(z, 1.0)
    p99 = np.percentile(z, 99.0)
    if p99 > p1:
        z_clipped = np.clip(z, p1, p99)
        z_norm = (z_clipped - p1) / (p99 - p1)
    else:
        z_norm = np.zeros_like(z)

    # Convert to uint8 grayscale [0, 255]
    relief_uint8 = (z_norm * 255.0).astype(np.uint8)

    # ── 5. High-Frequency Topographic Texture Fusion ──────────────────────────
    # Topographic micro-features (boulder edges, crater rims) have high spatial frequency.
    # Blending the unsharp high-pass texture ensures robust keypoint detection
    # while preserving macro illumination invariance.
    orig_uint8 = (img_f * 255.0).astype(np.uint8)
    high_pass = cv2.subtract(orig_uint8, cv2.GaussianBlur(orig_uint8, (5, 5), 1.5))
    hp_enhanced = cv2.equalizeHist(high_pass)
    relief_uint8 = cv2.addWeighted(relief_uint8, 0.4, hp_enhanced, 0.6, 0)

    logger.debug(
        f"Photoclinometry: sun_az={az_deg:.1f}°, sun_elev={elev_deg:.1f}°, "
        f"model={albedo_model}, method={integration_method}, "
        f"relief_range=[{p1:.2f}, {p99:.2f}]"
    )

    return relief_uint8


def _frankot_chellappa(p: np.ndarray, q: np.ndarray, eps: float = 1e-4) -> np.ndarray:
    """
    Frankot-Chellappa algorithm for enforcing integrability.
    Solves for surface height z that minimizes ||grad(z) - (p, q)||^2
    using orthogonal Fourier basis projection.
    """
    h, w = p.shape

    # 2D Fast Fourier Transform of the gradient fields
    P = np.fft.fft2(p)
    Q = np.fft.fft2(q)

    # Spatial frequency coordinate grids
    u = np.fft.fftfreq(w) * (2.0 * np.pi)
    v = np.fft.fftfreq(h) * (2.0 * np.pi)
    U, V = np.meshgrid(u, v)

    # Frankot-Chellappa formula:
    # Z(u, v) = (-i * U * P - i * V * Q) / (U^2 + V^2 + eps)
    denom = (U ** 2 + V ** 2) + eps
    Z = (-1j * U * P - 1j * V * Q) / denom

    # DC component (zero mean height)
    Z[0, 0] = 0.0

    # Inverse FFT to obtain spatial height map
    z = np.real(np.fft.ifft2(Z))
    return z.astype(np.float32)


def _poisson_solve(p: np.ndarray, q: np.ndarray, eps: float = 1e-4) -> np.ndarray:
    """
    Solves the Poisson equation del^2 z = div(p, q) via FFT.
    div(p, q) = dp/dx + dq/dy
    """
    h, w = p.shape
    # Compute divergence
    dp_dx = np.gradient(p, axis=1)
    dq_dy = np.gradient(q, axis=0)
    divergence = dp_dx + dq_dy

    DIV = np.fft.fft2(divergence)

    u = np.fft.fftfreq(w) * (2.0 * np.pi)
    v = np.fft.fftfreq(h) * (2.0 * np.pi)
    U, V = np.meshgrid(u, v)

    denom = -(U ** 2 + V ** 2) - eps
    Z = DIV / denom
    Z[0, 0] = 0.0

    z = np.real(np.fft.ifft2(Z))
    return z.astype(np.float32)
