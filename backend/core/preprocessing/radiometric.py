"""
SELORA Radiometric Normalization Module
Proper cross-sensor radiometric calibration for multi-modal registration.

Unlike simple CLAHE (which is adaptive histogram equalization), this module
implements two proper remote sensing radiometric normalization techniques:

1. Histogram Matching — matches the source image intensity distribution
   to the reference image distribution. Standard in ENVI/ERDAS.

2. Wallis Filter — local mean/variance normalization that forces both
   images to have similar local statistics. Used by photogrammetry
   pipelines (Agisoft, Pix4D) for multi-temporal matching.

These are applied BEFORE feature extraction to improve cross-sensor
feature correspondence quality.
"""

from __future__ import annotations
import cv2
import numpy as np
from typing import Tuple
from loguru import logger


def histogram_match(
    source: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    """
    Match the histogram of the source image to the reference image.

    Uses the cumulative distribution function (CDF) transfer method.
    This ensures both images have similar intensity distributions,
    which dramatically improves feature matching for cross-sensor pairs.

    Args:
        source:     Source image (grayscale uint8)
        reference:  Reference image (grayscale uint8)

    Returns:
        Histogram-matched source image (same shape as source)
    """
    if source.ndim != 2 or reference.ndim != 2:
        raise ValueError("histogram_match expects single-channel images")

    # Compute histograms and CDFs
    src_hist, _ = np.histogram(source.ravel(), bins=256, range=(0, 256))
    ref_hist, _ = np.histogram(reference.ravel(), bins=256, range=(0, 256))

    src_cdf = np.cumsum(src_hist).astype(np.float64)
    ref_cdf = np.cumsum(ref_hist).astype(np.float64)

    # Normalize CDFs to [0, 1]
    src_cdf /= src_cdf[-1]
    ref_cdf /= ref_cdf[-1]

    # Build lookup table: for each source intensity, find the reference
    # intensity whose CDF value is closest
    lookup = np.zeros(256, dtype=np.uint8)
    for src_val in range(256):
        # Find the reference value with the closest CDF
        diff = np.abs(ref_cdf - src_cdf[src_val])
        lookup[src_val] = np.argmin(diff)

    # Apply the lookup table
    matched = lookup[source]

    logger.info(
        f"Histogram matching: src mean {source.mean():.1f}→{matched.mean():.1f}, "
        f"ref mean {reference.mean():.1f}"
    )
    return matched


def wallis_filter(
    image: np.ndarray,
    target_mean: float = 127.0,
    target_std: float = 50.0,
    kernel_size: int = 31,
    contrast_gain: float = 0.8,
    brightness_gain: float = 0.9,
) -> np.ndarray:
    """
    Apply Wallis filter for local mean/variance normalization.

    The Wallis filter adjusts local image statistics (mean and standard
    deviation) to match target values. This is the standard technique
    in photogrammetric pipelines for normalizing images taken under
    different illumination conditions.

    Formula per pixel:
        out(x,y) = [image(x,y) - local_mean(x,y)] * gain + target_mean

    where gain = target_std / (contrast_gain * local_std + (1-contrast_gain) * target_std)

    Args:
        image:           Input grayscale image (uint8)
        target_mean:     Target local mean (default 127)
        target_std:      Target local standard deviation (default 50)
        kernel_size:     Size of local neighborhood (must be odd)
        contrast_gain:   Contrast enhancement factor [0, 1]
        brightness_gain: Brightness enhancement factor [0, 1]

    Returns:
        Wallis-filtered image (uint8)
    """
    if image.ndim != 2:
        raise ValueError("wallis_filter expects single-channel images")

    img_f = image.astype(np.float64)

    # Compute local mean and local standard deviation
    local_mean = cv2.blur(img_f, (kernel_size, kernel_size))
    local_sq_mean = cv2.blur(img_f ** 2, (kernel_size, kernel_size))
    local_var = np.maximum(local_sq_mean - local_mean ** 2, 0.0)
    local_std = np.sqrt(local_var)

    # Compute gain
    # gain = (c * target_std) / (c * local_std + (1-c) * target_std)
    c = contrast_gain
    numerator = c * target_std
    denominator = c * local_std + (1.0 - c) * target_std
    # Avoid division by zero
    denominator = np.maximum(denominator, 1e-6)
    gain = numerator / denominator

    # Apply Wallis transformation
    # output = gain * (image - local_mean) + brightness_gain * target_mean + (1 - brightness_gain) * local_mean
    b = brightness_gain
    output = gain * (img_f - local_mean) + b * target_mean + (1.0 - b) * local_mean

    # Clip and convert back to uint8
    output = np.clip(output, 0, 255).astype(np.uint8)

    logger.info(
        f"Wallis filter: mean {image.mean():.1f}→{output.mean():.1f}, "
        f"std {image.std():.1f}→{output.std():.1f}"
    )
    return output


def radiometric_normalize(
    source: np.ndarray,
    reference: np.ndarray,
    method: str = "histogram_match",
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply radiometric normalization to make source and reference images
    radiometrically consistent.

    Args:
        source:     Source image (grayscale uint8)
        reference:  Reference image (grayscale uint8)
        method:     'histogram_match' | 'wallis' | 'both'

    Returns:
        (normalized_source, normalized_reference) tuple
    """
    src = source.copy()
    ref = reference.copy()

    if method == "histogram_match":
        src = histogram_match(src, ref)
    elif method == "wallis":
        # Apply Wallis to both images with same target statistics
        target_mean = 127.0
        target_std = 50.0
        src = wallis_filter(src, target_mean, target_std)
        ref = wallis_filter(ref, target_mean, target_std)
    elif method == "both":
        # First match histograms, then apply Wallis
        src = histogram_match(src, ref)
        target_mean = ref.mean()
        target_std = ref.std()
        src = wallis_filter(src, target_mean, target_std)
        ref = wallis_filter(ref, target_mean, target_std)
    else:
        logger.warning(f"Unknown radiometric method '{method}', skipping")

    return src, ref
