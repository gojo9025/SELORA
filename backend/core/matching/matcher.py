"""
SELORA Matching Module
BFMatcher and FLANN-based matching with Lowe ratio test and mutual matching.
"""

from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from loguru import logger

from core.features.extractors import KeypointDescriptors


@dataclass
class MatchResult:
    matches: List[cv2.DMatch]              # all raw matches (before ratio test)
    filtered_matches: List[cv2.DMatch]     # after ratio + mutual filter
    src_pts: np.ndarray                    # Nx2 float32
    dst_pts: np.ndarray                    # Nx2 float32


def _knn_ratio_filter(
    matches_knn: List[List[cv2.DMatch]],
    ratio: float,
) -> List[cv2.DMatch]:
    """Apply Lowe's ratio test."""
    good = []
    for pair in matches_knn:
        if len(pair) < 2:
            continue
        m, n = pair[0], pair[1]
        if m.distance < ratio * n.distance:
            good.append(m)
    return good


def _mutual_nn_filter(
    matches_fwd: List[cv2.DMatch],
    descs_src: np.ndarray,
    descs_ref: np.ndarray,
    is_binary: bool,
) -> List[cv2.DMatch]:
    """
    Mutual nearest-neighbor filter.
    A match src→ref is kept only if ref→src also points back to src.
    """
    if is_binary:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    else:
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

    # Build index: for each ref descriptor, find best match in src
    matches_bwd = matcher.knnMatch(descs_ref, descs_src, k=1)
    bwd_map = {m[0].queryIdx: m[0].trainIdx for m in matches_bwd if m}

    mutual = []
    for m in matches_fwd:
        if bwd_map.get(m.trainIdx) == m.queryIdx:
            mutual.append(m)
    return mutual


def match_descriptors(
    src_kpd: KeypointDescriptors,
    ref_kpd: KeypointDescriptors,
    matcher_type: str = "FLANN",
    ratio: float = 0.75,
    mutual: bool = True,
    descriptor_type: str = "float",
) -> MatchResult:
    """
    Full descriptor matching pipeline.
    1. kNN match (k=2)
    2. Ratio test
    3. Optional mutual nearest-neighbor filter
    Returns MatchResult with point arrays ready for geometric verification.
    """
    if src_kpd.descriptors is None or ref_kpd.descriptors is None:
        logger.error("Cannot match: one or both descriptor arrays are None")
        return MatchResult([], [], np.zeros((0, 2)), np.zeros((0, 2)))

    is_binary = descriptor_type == "binary"

    # Neural matcher
    if matcher_type == "LIGHTGLUE":
        from core.features.learned import match_lightglue
        cv_matches, filtered, src_pts, dst_pts = match_lightglue(src_kpd, ref_kpd)
        logger.info(f"Matching: {len(filtered)} neural matches via LightGlue")
        if not filtered:
            return MatchResult([], [], np.zeros((0, 2)), np.zeros((0, 2)))
        return MatchResult(cv_matches, filtered, src_pts, dst_pts)

    # Classic matcher
    if matcher_type == "FLANN" and not is_binary:
        index_params = dict(algorithm=1, trees=8)  # FLANN_INDEX_KDTREE
        search_params = dict(checks=100)
        matcher = cv2.FlannBasedMatcher(index_params, search_params)
    else:
        norm = cv2.NORM_HAMMING if is_binary else cv2.NORM_L2
        matcher = cv2.BFMatcher(norm, crossCheck=False)

    descs_src = src_kpd.descriptors.astype(np.float32) if not is_binary else src_kpd.descriptors
    descs_ref = ref_kpd.descriptors.astype(np.float32) if not is_binary else ref_kpd.descriptors

    # kNN match
    try:
        knn_matches = matcher.knnMatch(descs_src, descs_ref, k=2)
    except cv2.error as e:
        logger.error(f"Matching failed: {e}")
        return MatchResult([], [], np.zeros((0, 2)), np.zeros((0, 2)))

    all_raw = [m[0] for m in knn_matches if len(m) >= 1]

    # Ratio test
    filtered = _knn_ratio_filter(knn_matches, ratio)
    logger.info(f"Matching: {len(all_raw)} raw → {len(filtered)} after ratio test ({ratio})")

    # Mutual nearest-neighbor
    if mutual and len(filtered) > 0:
        filtered = _mutual_nn_filter(filtered, descs_src, descs_ref, is_binary)
        logger.info(f"Matching: {len(filtered)} after mutual NN filter")

    if not filtered:
        return MatchResult(all_raw, [], np.zeros((0, 2)), np.zeros((0, 2)))

    src_pts = np.float32(
        [src_kpd.keypoints[m.queryIdx].pt for m in filtered]
    )
    dst_pts = np.float32(
        [ref_kpd.keypoints[m.trainIdx].pt for m in filtered]
    )

    return MatchResult(all_raw, filtered, src_pts, dst_pts)
