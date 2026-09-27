"""
SELORA Visualization Module
Generates match visualizations, difference maps, overlay images, thumbnails.
"""

from __future__ import annotations
import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger


def _ensure_bgr(img: np.ndarray) -> np.ndarray:
    """Convert any image to 3-channel BGR uint8."""
    if img.dtype != np.uint8:
        img = np.clip(img.astype(np.float32), 0, 255).astype(np.uint8)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 1:
        img = cv2.cvtColor(img[:, :, 0], cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


def _resize_to_height(img: np.ndarray, target_h: int) -> np.ndarray:
    """Resize image to target height preserving aspect ratio."""
    h, w = img.shape[:2]
    scale = target_h / h
    new_w = int(w * scale)
    return cv2.resize(img, (new_w, target_h), interpolation=cv2.INTER_AREA)


def draw_matches(
    src_img: np.ndarray,
    src_kps: List[cv2.KeyPoint],
    ref_img: np.ndarray,
    ref_kps: List[cv2.KeyPoint],
    matches: List[cv2.DMatch],
    inlier_mask: Optional[np.ndarray] = None,
    show: str = "inliers",       # 'all' | 'inliers' | 'outliers'
    max_height: int = 600,
    max_matches_display: int = 300,
) -> np.ndarray:
    """
    Draw feature correspondences between source and reference images.
    Color coding: green = inlier, red = outlier.
    """
    src_bgr = _ensure_bgr(src_img)
    ref_bgr = _ensure_bgr(ref_img)

    # Resize both to same height for side-by-side
    target_h = min(max_height, src_bgr.shape[0], ref_bgr.shape[0])
    src_disp = _resize_to_height(src_bgr, target_h)
    ref_disp = _resize_to_height(ref_bgr, target_h)

    src_scale = target_h / src_bgr.shape[0]
    ref_scale = target_h / ref_bgr.shape[0]

    # Scale keypoints
    def scale_kps(kps, scale):
        return [cv2.KeyPoint(kp.pt[0]*scale, kp.pt[1]*scale,
                              kp.size*scale, kp.angle, kp.response,
                              kp.octave, kp.class_id) for kp in kps]

    src_kps_s = scale_kps(src_kps, src_scale)
    ref_kps_s = scale_kps(ref_kps, ref_scale)

    # Filter matches based on show mode
    if inlier_mask is not None and len(inlier_mask) == len(matches):
        inlier_matches = [m for m, v in zip(matches, inlier_mask) if v]
        outlier_matches = [m for m, v in zip(matches, inlier_mask) if not v]
    else:
        inlier_matches = matches
        outlier_matches = []

    if show == "inliers":
        display_matches = inlier_matches[:max_matches_display]
        match_color = (0, 200, 80)       # green
    elif show == "outliers":
        display_matches = outlier_matches[:max_matches_display]
        match_color = (0, 60, 220)       # red
    else:
        display_matches = matches[:max_matches_display]
        match_color = None               # auto color

    flags = cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
    out = cv2.drawMatches(
        src_disp, src_kps_s,
        ref_disp, ref_kps_s,
        display_matches,
        None,
        matchColor=match_color if match_color else (0, 200, 80),
        singlePointColor=(100, 100, 100),
        flags=flags,
    )

    # Add label overlay
    label = f"{'INLIERS' if show=='inliers' else 'ALL MATCHES'}: {len(display_matches)}"
    cv2.putText(out, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return out


def generate_difference_map(
    registered: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    """
    Generate absolute difference map between registered source and reference.
    Colorized with a hot colormap for visual clarity.
    """
    reg = _ensure_bgr(registered)
    ref = _ensure_bgr(reference)

    # Resize to same dimensions if needed
    if reg.shape[:2] != ref.shape[:2]:
        reg = cv2.resize(reg, (ref.shape[1], ref.shape[0]))

    reg_g = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY).astype(np.float32)
    ref_g = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY).astype(np.float32)

    diff = np.abs(reg_g - ref_g)
    diff_norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    diff_color = cv2.applyColorMap(diff_norm, cv2.COLORMAP_HOT)
    return diff_color


def generate_overlay(
    registered: np.ndarray,
    reference: np.ndarray,
    alpha: float = 0.5,
) -> np.ndarray:
    """
    Generate alpha-blended overlay between registered source and reference.
    Default 50/50 blend.
    """
    reg = _ensure_bgr(registered)
    ref = _ensure_bgr(reference)

    if reg.shape[:2] != ref.shape[:2]:
        reg = cv2.resize(reg, (ref.shape[1], ref.shape[0]))

    overlay = cv2.addWeighted(reg, alpha, ref, 1.0 - alpha, 0)
    return overlay


def generate_error_heatmap(
    registered: np.ndarray,
    reference: np.ndarray,
) -> np.ndarray:
    """
    Generate a smoothed spatial error heatmap.
    Uses Gaussian blur and TURBO colormap for a professional look.
    """
    reg = _ensure_bgr(registered)
    ref = _ensure_bgr(reference)

    if reg.shape[:2] != ref.shape[:2]:
        reg = cv2.resize(reg, (ref.shape[1], ref.shape[0]))

    reg_g = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY).astype(np.float32)
    ref_g = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Calculate absolute difference
    diff = np.abs(reg_g - ref_g)
    
    # Apply Gaussian blur to create a smooth heatmap effect
    # The kernel size should scale roughly with image size, we use a fixed relative size
    k_size = max(31, (min(diff.shape) // 20) | 1) # Must be odd
    smoothed_diff = cv2.GaussianBlur(diff, (k_size, k_size), 0)
    
    # Normalize to 0-255
    diff_norm = cv2.normalize(smoothed_diff, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    
    # Apply modern TURBO colormap
    heatmap_color = cv2.applyColorMap(diff_norm, cv2.COLORMAP_TURBO)
    return heatmap_color



def generate_thumbnail(img: np.ndarray, max_size: int = 256) -> np.ndarray:
    """Generate a small thumbnail for quick preview."""
    img = _ensure_bgr(img)
    h, w = img.shape[:2]
    scale = min(max_size / h, max_size / w, 1.0)
    new_h, new_w = int(h * scale), int(w * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def generate_counterfactual_render(
    source_relief: np.ndarray,
    target_sun_azimuth: float,
    target_sun_elevation: float,
) -> np.ndarray:
    """
    Render source terrain relief at reference illumination angle.
    Returns BGR uint8 image.
    """
    from core.photoclinometry.render import render_at_sun_angle
    shaded = render_at_sun_angle(source_relief, target_sun_azimuth, target_sun_elevation)
    return _ensure_bgr(shaded)


def save_image(img: np.ndarray, path: str) -> bool:
    """Save an image to disk. Returns True on success."""
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        result = cv2.imwrite(path, img)
        if not result:
            logger.error(f"cv2.imwrite failed for {path}")
        return result
    except Exception as e:
        logger.error(f"Failed to save image {path}: {e}")
        return False
