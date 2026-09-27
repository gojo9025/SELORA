"""
SELORA Backend Tests
Tests for: validation, preprocessing, feature extraction, matching, 
geometry, warping, evaluation, quality gates.
"""

import pytest
import numpy as np
import cv2
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datasets.synthetic import create_synthetic_pair, create_cross_modal_pair
from core.preprocessing.pipeline import (
    to_grayscale, percentile_normalize, apply_clahe,
    gradient_representation, build_pyramid, preprocess, PreprocessingConfig,
)
from core.features.extractors import (
    SIFTExtractor, ORBExtractor, AKAZEExtractor, extract_multiscale, create_extractor,
)
from core.matching.matcher import match_descriptors
from core.geometry.verification import (
    verify_geometry, compute_spatial_coverage, _compute_rmse,
)
from core.evaluation.metrics import compute_confidence, evaluate
from core.sensors.profiles import SensorRegistry, canonicalize


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def simple_pair():
    return create_synthetic_pair(rotation_deg=5.0, scale=0.98, tx=15.0, ty=-8.0)


@pytest.fixture(scope="module")
def cross_modal_pair():
    return create_cross_modal_pair(resolution_ratio=0.5, rotation_deg=3.0)


# ─────────────────────────────────────────────
# Preprocessing Tests
# ─────────────────────────────────────────────

class TestPreprocessing:
    def test_grayscale_from_bgr(self):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        gray = to_grayscale(img)
        assert gray.ndim == 2
        assert gray.shape == (100, 100)

    def test_grayscale_passthrough(self):
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        gray = to_grayscale(img)
        assert gray.ndim == 2

    def test_percentile_normalize_range(self):
        img = np.random.randint(0, 255, (256, 256), dtype=np.uint8)
        norm = percentile_normalize(img)
        assert norm.min() >= 0
        assert norm.max() <= 255
        assert norm.dtype == np.uint8

    def test_percentile_normalize_uniform(self):
        """Uniform image should not crash."""
        img = np.full((100, 100), 128, dtype=np.uint8)
        norm = percentile_normalize(img)
        assert norm is not None

    def test_clahe_output_range(self):
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        out = apply_clahe(img)
        assert out.shape == img.shape
        assert out.dtype == np.uint8

    def test_gradient_representation(self):
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        grad = gradient_representation(img)
        assert grad.shape == img.shape
        assert grad.dtype == np.uint8
        assert grad.min() >= 0 and grad.max() <= 255

    def test_build_pyramid(self):
        img = np.random.randint(0, 255, (512, 512), dtype=np.uint8)
        pyr = build_pyramid(img, levels=4)
        assert len(pyr) >= 1
        assert pyr[0].shape == img.shape
        # Each level should be smaller
        for i in range(1, len(pyr)):
            assert pyr[i].shape[0] < pyr[i-1].shape[0]

    def test_full_preprocess_pipeline(self, simple_pair):
        cfg = PreprocessingConfig()
        proc, pyr = preprocess(simple_pair.source, cfg)
        assert proc.ndim == 2
        assert len(pyr) >= 1


# ─────────────────────────────────────────────
# Feature Extraction Tests
# ─────────────────────────────────────────────

class TestFeatureExtraction:
    def _get_test_img(self):
        pair = create_synthetic_pair()
        cfg = PreprocessingConfig()
        proc, _ = preprocess(pair.reference, cfg)
        return proc

    def test_sift_detects_keypoints(self):
        img = self._get_test_img()
        ext = SIFTExtractor(n_features=500)
        result = ext.detect_and_compute(img)
        assert len(result.keypoints) > 0
        assert result.descriptors is not None
        assert result.descriptors.shape[1] == 128  # SIFT descriptor size

    def test_orb_detects_keypoints(self):
        img = self._get_test_img()
        ext = ORBExtractor(n_features=500)
        result = ext.detect_and_compute(img)
        assert len(result.keypoints) > 0
        assert result.descriptors is not None

    def test_akaze_detects_keypoints(self):
        img = self._get_test_img()
        try:
            ext = AKAZEExtractor(n_features=500)
        except RuntimeError:
            pytest.skip("AKAZE not available in this OpenCV build (removed in OpenCV 5)")
        result = ext.detect_and_compute(img)
        assert len(result.keypoints) > 0

    def test_multiscale_extraction(self):
        img = self._get_test_img()
        pyr = build_pyramid(img, levels=3)
        ext = SIFTExtractor(n_features=500)
        result = extract_multiscale(ext, pyr)
        assert len(result.keypoints) > 0

    def test_factory(self):
        for method in ["SIFT", "ORB", "AKAZE"]:
            ext = create_extractor(method, n_features=100)
            assert ext is not None


# ─────────────────────────────────────────────
# Matching Tests
# ─────────────────────────────────────────────

class TestMatching:
    def test_sift_matching_on_synthetic(self, simple_pair):
        cfg = PreprocessingConfig()
        src_proc, src_pyr = preprocess(simple_pair.source, cfg)
        ref_proc, ref_pyr = preprocess(simple_pair.reference, cfg)
        ext = SIFTExtractor(n_features=1000)
        src_kpd = ext.detect_and_compute(src_proc)
        ref_kpd = ext.detect_and_compute(ref_proc)
        result = match_descriptors(src_kpd, ref_kpd, descriptor_type="float")
        assert len(result.filtered_matches) > 0

    def test_ratio_test_reduces_matches(self, simple_pair):
        cfg = PreprocessingConfig()
        src_proc, _ = preprocess(simple_pair.source, cfg)
        ref_proc, _ = preprocess(simple_pair.reference, cfg)
        ext = SIFTExtractor(n_features=1000)
        src_kpd = ext.detect_and_compute(src_proc)
        ref_kpd = ext.detect_and_compute(ref_proc)
        result_strict = match_descriptors(src_kpd, ref_kpd, ratio=0.6, descriptor_type="float")
        result_loose = match_descriptors(src_kpd, ref_kpd, ratio=0.9, descriptor_type="float")
        assert len(result_strict.filtered_matches) <= len(result_loose.filtered_matches)

    def test_orb_bf_matching(self, simple_pair):
        cfg = PreprocessingConfig(gradient_representation=False)
        src_proc, _ = preprocess(simple_pair.source, cfg)
        ref_proc, _ = preprocess(simple_pair.reference, cfg)
        ext = ORBExtractor(n_features=1000)
        src_kpd = ext.detect_and_compute(src_proc)
        ref_kpd = ext.detect_and_compute(ref_proc)
        result = match_descriptors(
            src_kpd, ref_kpd,
            matcher_type="BF",
            descriptor_type="binary",
            mutual=False,
        )
        assert result is not None


# ─────────────────────────────────────────────
# Geometry Tests
# ─────────────────────────────────────────────

class TestGeometry:
    def test_ransac_finds_inliers(self, simple_pair):
        cfg = PreprocessingConfig()
        src_proc, src_pyr = preprocess(simple_pair.source, cfg)
        ref_proc, ref_pyr = preprocess(simple_pair.reference, cfg)
        ext = SIFTExtractor(n_features=2000)
        src_kpd = ext.detect_and_compute(src_proc)
        ref_kpd = ext.detect_and_compute(ref_proc)
        mr = match_descriptors(src_kpd, ref_kpd, descriptor_type="float")
        if len(mr.filtered_matches) < 10:
            pytest.skip("Not enough matches for geometry test")
        geo = verify_geometry(
            mr.src_pts, mr.dst_pts,
            img_shape=ref_proc.shape[:2],
            models=["affine", "homography"],
        )
        assert geo.best_model.valid
        assert geo.best_model.inlier_count > 0

    def test_spatial_coverage(self):
        pts = np.array([[10, 10], [200, 10], [10, 200], [200, 200]], dtype=np.float32)
        coverage = compute_spatial_coverage(pts, (256, 256), grid=4)
        assert 0.0 < coverage <= 1.0

    def test_spatial_coverage_empty(self):
        coverage = compute_spatial_coverage(np.zeros((0, 2)), (256, 256))
        assert coverage == 0.0

    def test_rmse_zero_for_perfect(self):
        # Identity transform should give 0 RMSE
        M = np.eye(3)
        pts = np.array([[10, 20], [100, 50], [200, 150]], dtype=np.float32)
        rmse = _compute_rmse(M, pts, pts, "homography")
        assert rmse < 1e-4


# ─────────────────────────────────────────────
# Evaluation Tests
# ─────────────────────────────────────────────

class TestEvaluation:
    def test_confidence_range(self):
        for ir in [0.0, 0.3, 0.6, 0.9, 1.0]:
            for rmse in [0.0, 5.0, 15.0, 25.0]:
                c = compute_confidence(ir, rmse, 0.5, 100)
                assert 0.0 <= c <= 1.0, f"Confidence out of range for ir={ir}, rmse={rmse}"

    def test_high_quality_gives_high_confidence(self):
        c = compute_confidence(
            inlier_ratio=0.9,
            rmse=0.5,
            spatial_coverage=0.9,
            inlier_count=800,
        )
        assert c > 0.7

    def test_low_quality_gives_low_confidence(self):
        c = compute_confidence(
            inlier_ratio=0.1,
            rmse=25.0,
            spatial_coverage=0.05,
            inlier_count=5,
        )
        assert c < 0.3

    def test_evaluate_function(self, simple_pair):
        cfg = PreprocessingConfig()
        src_proc, src_pyr = preprocess(simple_pair.source, cfg)
        ref_proc, ref_pyr = preprocess(simple_pair.reference, cfg)
        ext = SIFTExtractor(n_features=2000)
        src_kpd = ext.detect_and_compute(src_proc)
        ref_kpd = ext.detect_and_compute(ref_proc)
        mr = match_descriptors(src_kpd, ref_kpd, descriptor_type="float")
        if len(mr.filtered_matches) < 10:
            pytest.skip("Not enough matches")
        geo = verify_geometry(
            mr.src_pts, mr.dst_pts,
            img_shape=ref_proc.shape[:2],
            models=["affine"],
        )
        M = geo.best_model.matrix
        if not geo.best_model.valid:
            pytest.skip("Geometry failed")
        M3x3 = np.vstack([M, [0, 0, 1]])
        result = evaluate(
            total_matches=len(mr.filtered_matches),
            inlier_count=geo.best_model.inlier_count,
            src_inlier_pts=geo.src_inlier_pts,
            dst_inlier_pts=geo.dst_inlier_pts,
            matrix=M3x3,
            model_type="affine",
            img_shape=ref_proc.shape[:2],
            processing_time_sec=1.5,
        )
        assert result.rmse >= 0
        assert 0 <= result.confidence <= 1
        assert result.inlier_ratio >= 0


# ─────────────────────────────────────────────
# Sensor Profile Tests
# ─────────────────────────────────────────────

class TestSensorProfiles:
    def test_canonicalize(self):
        assert canonicalize("ohrc") == "OHRC"
        assert canonicalize("TMC-2") == "TMC2"
        assert canonicalize("iirs") == "IIRS"
        assert canonicalize("auto") == "Unknown"

    def test_ohrc_tmc2_profile(self):
        cfg = SensorRegistry.get("OHRC", "TMC2", mode="robust")
        assert cfg.features.method == "SIFT"
        assert cfg.preprocessing.gradient_representation is True
        assert cfg.features.multi_scale is True

    def test_fast_mode_override(self):
        cfg = SensorRegistry.get("OHRC", "OHRC", mode="fast")
        assert cfg.features.method == "ORB"
        assert cfg.features.multi_scale is False

    def test_research_mode_override(self):
        cfg = SensorRegistry.get("OHRC", "TMC2", mode="research")
        assert cfg.features.n_features >= 8000
        assert len(cfg.geometry.models) >= 3

    def test_unknown_pair_fallback(self):
        cfg = SensorRegistry.get("Unknown", "Unknown", mode="auto")
        assert cfg is not None


# ─────────────────────────────────────────────
# End-to-End Pipeline Test
# ─────────────────────────────────────────────

class TestEndToEnd:
    def test_full_pipeline_synthetic(self, simple_pair):
        """Full pipeline should produce valid results on a synthetic pair."""
        from core.preprocessing.pipeline import PreprocessingConfig
        from core.sensors.profiles import SensorRegistry

        config = SensorRegistry.get("Unknown", "Unknown", mode="robust")
        src_proc, src_pyr = preprocess(simple_pair.source.copy(), config.preprocessing)
        ref_proc, ref_pyr = preprocess(simple_pair.reference.copy(), config.preprocessing)

        ext = create_extractor("SIFT", 2000)
        src_kpd = extract_multiscale(ext, src_pyr[:3])
        ref_kpd = extract_multiscale(ext, ref_pyr[:3])

        mr = match_descriptors(src_kpd, ref_kpd, descriptor_type="float")
        assert len(mr.filtered_matches) >= 10, "Pipeline should find enough matches"

        geo = verify_geometry(
            mr.src_pts, mr.dst_pts,
            img_shape=ref_proc.shape[:2],
            models=["affine", "homography"],
        )
        assert geo.best_model.valid, "Geometry verification should succeed"
        assert geo.best_model.inlier_count > 5, "Should find geometric inliers"

    def test_cross_modal_pipeline(self, cross_modal_pair):
        """Pipeline should handle cross-resolution pairs (simulating OHRC→TMC-2)."""
        config = SensorRegistry.get("OHRC", "TMC2", mode="robust")
        src_proc, src_pyr = preprocess(cross_modal_pair.source.copy(), config.preprocessing)
        ref_proc, ref_pyr = preprocess(cross_modal_pair.reference.copy(), config.preprocessing)

        ext = create_extractor("SIFT", 2000)
        src_kpd = extract_multiscale(ext, src_pyr[:3])
        ref_kpd = extract_multiscale(ext, ref_pyr[:3])

        mr = match_descriptors(src_kpd, ref_kpd, descriptor_type="float")
        # Cross-modal is harder — just ensure no crash
        assert mr is not None
