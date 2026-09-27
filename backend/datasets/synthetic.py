"""
SELORA Synthetic Image Generator
Creates synthetic lunar-like test image pairs with known ground-truth transformations.
Used for unit testing and benchmarking.
"""

from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class SyntheticPair:
    source: np.ndarray
    reference: np.ndarray
    ground_truth_matrix: np.ndarray         # 3x3 homography or 2x3 affine
    model_type: str
    transform_params: dict


def _make_lunar_texture(h: int = 512, w: int = 512, seed: int = 42) -> np.ndarray:
    """
    Generate a synthetic lunar surface texture:
    - Gaussian noise base
    - Several crater-like circular features
    - Gradient illumination
    """
    rng = np.random.RandomState(seed)
    # Base noise
    img = rng.randn(h, w).astype(np.float32) * 30 + 128
    img = np.clip(img, 0, 255).astype(np.float32)

    # Add crater-like features (dark rings with bright rims)
    n_craters = rng.randint(8, 20)
    for _ in range(n_craters):
        cx = rng.randint(0, w)
        cy = rng.randint(0, h)
        r = rng.randint(15, 60)
        # Bright rim
        cv2.circle(img, (cx, cy), r, 200 + rng.randint(0, 55), 3)
        # Dark interior
        cv2.circle(img, (cx, cy), max(1, r - 5), 40 + rng.randint(0, 30), -1)

    # Add small rocks / boulders
    n_rocks = rng.randint(20, 50)
    for _ in range(n_rocks):
        cx = rng.randint(0, w)
        cy = rng.randint(0, h)
        r = rng.randint(2, 8)
        cv2.circle(img, (cx, cy), r, 160 + rng.randint(0, 60), -1)

    # Gradient illumination
    grad = np.linspace(0.85, 1.15, w, dtype=np.float32)
    img = img * grad[np.newaxis, :]
    img = np.clip(img, 0, 255).astype(np.uint8)

    # Smooth slightly (real lunar imagery is not pure noise)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    return img


def create_synthetic_pair(
    rotation_deg: float = 5.0,
    scale: float = 0.95,
    tx: float = 20.0,
    ty: float = -10.0,
    noise_std: float = 5.0,
    brightness_shift: float = 20.0,
    size: int = 512,
    seed: int = 42,
) -> SyntheticPair:
    """
    Create a synthetic (source, reference) image pair with a known affine transform.
    The reference is the original; the source is the warped version.
    Registration should recover the inverse transform.
    """
    ref = _make_lunar_texture(size, size, seed=seed)

    # Build affine transform: rotation + scale + translation
    cx, cy = size / 2, size / 2
    angle_rad = np.deg2rad(rotation_deg)
    cos_a, sin_a = np.cos(angle_rad) * scale, np.sin(angle_rad) * scale

    M = np.array([
        [cos_a, -sin_a, (1 - cos_a) * cx + sin_a * cy + tx],
        [sin_a,  cos_a, (1 - cos_a) * cy - sin_a * cx + ty],
    ], dtype=np.float64)

    src = cv2.warpAffine(ref, M, (size, size),
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    # Add independent noise
    if noise_std > 0:
        noise = np.random.RandomState(seed + 1).randn(size, size).astype(np.float32) * noise_std
        src_f = src.astype(np.float32) + noise
        src = np.clip(src_f, 0, 255).astype(np.uint8)

    # Add brightness shift to simulate illumination difference
    if brightness_shift != 0:
        src_f = src.astype(np.float32) + brightness_shift
        src = np.clip(src_f, 0, 255).astype(np.uint8)

    M3x3 = np.vstack([M, [0, 0, 1]])

    return SyntheticPair(
        source=src,
        reference=ref,
        ground_truth_matrix=M3x3,
        model_type="affine",
        transform_params={
            "rotation_deg": rotation_deg,
            "scale": scale,
            "tx": tx,
            "ty": ty,
            "noise_std": noise_std,
            "brightness_shift": brightness_shift,
        },
    )


def create_cross_modal_pair(
    resolution_ratio: float = 0.5,
    rotation_deg: float = 3.0,
    tx: float = 10.0,
    ty: float = -5.0,
    size: int = 512,
    seed: int = 42,
) -> SyntheticPair:
    """
    Create a pair simulating cross-modal / cross-resolution imagery.
    Reference is high-res, source is blurred+scaled to simulate lower-resolution sensor.
    """
    ref = _make_lunar_texture(size, size, seed=seed)

    # Simulate lower-resolution by blur + downsample + upsample
    small_size = int(size * resolution_ratio)
    small = cv2.resize(ref, (small_size, small_size), interpolation=cv2.INTER_AREA)
    upscaled = cv2.resize(small, (size, size), interpolation=cv2.INTER_LINEAR)

    # Apply transform
    cx, cy = size / 2, size / 2
    angle_rad = np.deg2rad(rotation_deg)
    M = np.array([
        [np.cos(angle_rad), -np.sin(angle_rad), tx + (1 - np.cos(angle_rad)) * cx + np.sin(angle_rad) * cy],
        [np.sin(angle_rad),  np.cos(angle_rad), ty + (1 - np.cos(angle_rad)) * cy - np.sin(angle_rad) * cx],
    ], dtype=np.float64)
    src = cv2.warpAffine(upscaled, M, (size, size))

    # Spectral difference simulation: apply histogram shift
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    src = clahe.apply(src)

    M3x3 = np.vstack([M, [0, 0, 1]])
    return SyntheticPair(
        source=src,
        reference=ref,
        ground_truth_matrix=M3x3,
        model_type="affine",
        transform_params={
            "resolution_ratio": resolution_ratio,
            "rotation_deg": rotation_deg,
            "tx": tx,
            "ty": ty,
        },
    )
