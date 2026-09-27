"""
SELORA Feature Extraction Module
Pluggable FeatureExtractor ABC + SIFT, ORB, AKAZE implementations.
"""

from __future__ import annotations
import cv2
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple
from loguru import logger


@dataclass
class KeypointDescriptors:
    keypoints: List[cv2.KeyPoint]
    descriptors: Optional[np.ndarray]   # None if extraction failed


class FeatureExtractor(ABC):
    """Abstract base class for all feature extractors."""

    @abstractmethod
    def detect_and_compute(self, img: np.ndarray) -> KeypointDescriptors:
        """Detect keypoints and compute descriptors on a grayscale image."""
        ...

    @property
    @abstractmethod
    def descriptor_type(self) -> str:
        """Return 'float' for SIFT-style or 'binary' for ORB-style descriptors."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


# ─────────────────────────────────────────────
# SIFT
# ─────────────────────────────────────────────

class SIFTExtractor(FeatureExtractor):
    """
    Scale-Invariant Feature Transform.
    Best baseline for cross-modal/multi-scale lunar imagery.
    """

    def __init__(
        self,
        n_features: int = 5000,
        n_octave_layers: int = 3,
        contrast_threshold: float = 0.04,
        edge_threshold: float = 10.0,
        sigma: float = 1.6,
    ):
        self._sift = cv2.SIFT_create(
            nfeatures=n_features,
            nOctaveLayers=n_octave_layers,
            contrastThreshold=contrast_threshold,
            edgeThreshold=edge_threshold,
            sigma=sigma,
        )
        self._n_features = n_features

    def detect_and_compute(self, img: np.ndarray) -> KeypointDescriptors:
        kps, descs = self._sift.detectAndCompute(img, None)
        if kps is None or len(kps) == 0:
            logger.warning("SIFT: No keypoints detected")
            return KeypointDescriptors([], None)
        logger.debug(f"SIFT: {len(kps)} keypoints")
        return KeypointDescriptors(list(kps), descs)

    @property
    def descriptor_type(self) -> str:
        return "float"

    @property
    def name(self) -> str:
        return "SIFT"


# ─────────────────────────────────────────────
# ORB
# ─────────────────────────────────────────────

class ORBExtractor(FeatureExtractor):
    """
    Oriented FAST and Rotated BRIEF.
    Much faster than SIFT, binary descriptors.
    Used in FAST mode.
    """

    def __init__(self, n_features: int = 5000, scale_factor: float = 1.2, n_levels: int = 8):
        self._orb = cv2.ORB_create(
            nfeatures=n_features,
            scaleFactor=scale_factor,
            nlevels=n_levels,
        )

    def detect_and_compute(self, img: np.ndarray) -> KeypointDescriptors:
        kps, descs = self._orb.detectAndCompute(img, None)
        if kps is None or len(kps) == 0:
            logger.warning("ORB: No keypoints detected")
            return KeypointDescriptors([], None)
        logger.debug(f"ORB: {len(kps)} keypoints")
        return KeypointDescriptors(list(kps), descs)

    @property
    def descriptor_type(self) -> str:
        return "binary"

    @property
    def name(self) -> str:
        return "ORB"


# ─────────────────────────────────────────────
# AKAZE
# ─────────────────────────────────────────────

class AKAZEExtractor(FeatureExtractor):
    """
    Accelerated-KAZE.
    Good balance of speed and robustness. Binary descriptors.
    Works with OpenCV 4.x and 5.x.
    """

    def __init__(self, n_features: int = 5000):
        # OpenCV 5 renamed AKAZE_create → AKAZE.create
        if hasattr(cv2, 'AKAZE_create'):
            self._akaze = cv2.AKAZE_create()  # type: ignore[attr-defined]
        elif hasattr(cv2, 'AKAZE'):
            self._akaze = cv2.AKAZE.create()  # type: ignore[attr-defined]
        else:
            raise RuntimeError("AKAZE not available in this OpenCV build")
        self._n_features = n_features

    def detect_and_compute(self, img: np.ndarray) -> KeypointDescriptors:
        kps, descs = self._akaze.detectAndCompute(img, None)
        if kps is None or len(kps) == 0:
            logger.warning("AKAZE: No keypoints detected")
            return KeypointDescriptors([], None)
        # Limit to n_features by response score
        if len(kps) > self._n_features:
            kps_descs = sorted(zip(kps, descs), key=lambda x: -x[0].response)
            kps_descs = kps_descs[:self._n_features]
            kps, descs = zip(*kps_descs)
            kps = list(kps)
            descs = np.array(descs)
        logger.debug(f"AKAZE: {len(kps)} keypoints")
        return KeypointDescriptors(list(kps), descs)

    @property
    def descriptor_type(self) -> str:
        return "binary"

    @property
    def name(self) -> str:
        return "AKAZE"


# ─────────────────────────────────────────────
# Spatial Grid Bucketing (Uniform Distribution)
# ─────────────────────────────────────────────

def apply_spatial_bucketing(
    kps: List[cv2.KeyPoint],
    descs: np.ndarray,
    width: int,
    height: int,
    max_keypoints: int,
    grid_rows: int = 10,
    grid_cols: int = 10
) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
    """
    Ensure uniform spatial distribution of keypoints using a grid bucketing approach.
    Prevents keypoint clustering in high-contrast areas (e.g., craters).
    """
    if not kps or len(kps) <= max_keypoints:
        return kps, descs

    pts_per_cell = max(1, max_keypoints // (grid_rows * grid_cols))
    
    grid = [[[] for _ in range(grid_cols)] for _ in range(grid_rows)]
    
    cell_w = max(1.0, width / grid_cols)
    cell_h = max(1.0, height / grid_rows)
    
    for i, kp in enumerate(kps):
        c = int(kp.pt[0] / cell_w)
        r = int(kp.pt[1] / cell_h)
        c = min(c, grid_cols - 1)
        r = min(r, grid_rows - 1)
        grid[r][c].append((kp, descs[i]))
        
    filtered_kps = []
    filtered_descs = []
    
    for r in range(grid_rows):
        for c in range(grid_cols):
            cell_pts = grid[r][c]
            if not cell_pts:
                continue
            # Sort by response (descending)
            cell_pts.sort(key=lambda x: x[0].response, reverse=True)
            # Take top pts_per_cell
            top_pts = cell_pts[:pts_per_cell]
            for kp, desc in top_pts:
                filtered_kps.append(kp)
                filtered_descs.append(desc)
                
    if not filtered_kps:
        return kps, descs
        
    logger.debug(f"Spatial bucketing: reduced from {len(kps)} to {len(filtered_kps)} keypoints")
    return filtered_kps, np.array(filtered_descs)


# ─────────────────────────────────────────────
# Multi-scale extraction
# ─────────────────────────────────────────────

def extract_multiscale(
    extractor: FeatureExtractor,
    pyramid: List[np.ndarray],
    scale_up: bool = True,
) -> KeypointDescriptors:
    """
    Extract features from each pyramid level and merge.
    Keypoints are scaled back to level-0 coordinates.
    """
    all_kps: List[cv2.KeyPoint] = []
    all_descs: List[np.ndarray] = []

    for level, img in enumerate(pyramid):
        result = extractor.detect_and_compute(img)
        if not result.keypoints or result.descriptors is None:
            continue
        scale = 2 ** level
        if scale_up and scale > 1:
            scaled_kps = []
            for kp in result.keypoints:
                kp2 = cv2.KeyPoint(
                    x=kp.pt[0] * scale,
                    y=kp.pt[1] * scale,
                    size=kp.size * scale,
                    angle=kp.angle,
                    response=kp.response,
                    octave=kp.octave,
                    class_id=kp.class_id,
                )
                scaled_kps.append(kp2)
            all_kps.extend(scaled_kps)
        else:
            all_kps.extend(result.keypoints)
        all_descs.append(result.descriptors)

    if not all_kps:
        return KeypointDescriptors([], None)

    merged_descs = np.vstack(all_descs)
    
    # Apply spatial bucketing to ensure uniform distribution
    if hasattr(extractor, '_n_features'):
        h, w = pyramid[0].shape[:2]
        all_kps, merged_descs = apply_spatial_bucketing(
            all_kps, merged_descs, 
            width=w, height=h, 
            max_keypoints=getattr(extractor, '_n_features')
        )
    
    logger.info(f"Multi-scale extraction: {len(all_kps)} total keypoints from {len(pyramid)} levels")
    return KeypointDescriptors(all_kps, merged_descs)


# ─────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────

def create_extractor(method: str, n_features: int = 5000) -> FeatureExtractor:
    """Factory for FeatureExtractor instances."""
    m = method.upper()
    if m == "SIFT":
        return SIFTExtractor(n_features=n_features)
    if m == "ORB":
        return ORBExtractor(n_features=n_features)
    if m == "AKAZE":
        try:
            return AKAZEExtractor(n_features=n_features)
        except RuntimeError:
            logger.warning("AKAZE not available in this OpenCV build, falling back to SIFT")
            return SIFTExtractor(n_features=n_features)
    if m == "DEEP":
        try:
            from core.features.learned import KorniaFeatureExtractor
            return KorniaFeatureExtractor(n_features=n_features)
        except ImportError as e:
            logger.warning(f"Failed to load Kornia DEEP extractor ({e}), falling back to SIFT")
            return SIFTExtractor(n_features=n_features)
            
    logger.warning(f"Unknown feature method '{method}', falling back to SIFT")
    return SIFTExtractor(n_features=n_features)
