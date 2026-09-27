"""
SELORA Warping Module
Applies the estimated transformation to warp the source image
onto the reference image coordinate system.
"""

from __future__ import annotations
import cv2
import numpy as np
from typing import Optional, Tuple
from loguru import logger


def warp_image(
    src_img: np.ndarray,
    ref_img: np.ndarray,
    matrix: np.ndarray,
    model_type: str,
) -> np.ndarray:
    """
    Warp source image to align with reference image.

    Args:
        src_img:    Source image (BGR or grayscale), original (not preprocessed)
        ref_img:    Reference image — used for output size
        matrix:     2x3 (affine/similarity) or 3x3 (homography)
        model_type: 'affine' | 'similarity' | 'homography'

    Returns:
        Warped source image in reference coordinate frame
    """
    h, w = ref_img.shape[:2]

    if model_type == "homography":
        if matrix.shape != (3, 3):
            raise ValueError(f"Homography must be 3x3, got {matrix.shape}")
        warped = cv2.warpPerspective(
            src_img, matrix, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
    else:
        # Affine / similarity: matrix is 2x3
        M = matrix if matrix.shape == (2, 3) else matrix[:2, :]
        warped = cv2.warpAffine(
            src_img, M, (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )

    logger.info(f"Warped source image: {src_img.shape} → {warped.shape} using {model_type}")
    return warped


def load_original_for_warp(
    image_path: str,
    target_channels: int = 3,
) -> np.ndarray:
    """
    Load the original source image for warping (not the preprocessed grayscale).
    Ensures it has the expected channel count.
    """
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        # Try loading as 8-bit
        img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")

    # Normalize to uint8 if needed
    if img.dtype != np.uint8:
        img_f = img.astype(np.float32)
        img_min, img_max = img_f.min(), img_f.max()
        if img_max > img_min:
            img_f = (img_f - img_min) / (img_max - img_min) * 255
        img = img_f.astype(np.uint8)

    # Ensure 3-channel BGR
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 1:
        img = cv2.cvtColor(img[:, :, 0], cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    return img
