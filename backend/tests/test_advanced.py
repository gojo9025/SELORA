"""
Unit tests for SELORA Phase A & B Advanced Modules:
- Sub-Pixel Phase Correlation Refinement
- Cross-Sensor Radiometric Normalization (Wallis & Histogram Match)
- Independent Validation (Leave-K-Out CV-RMSE, SSIM, NCC, MI)
- Mutual Information Fallback Registration
"""

import numpy as np
import cv2
import pytest
from core.refinement.subpixel import refine_registration, phase_correlate
from core.preprocessing.radiometric import radiometric_normalize, histogram_match, wallis_filter
from core.evaluation.validation import validate_registration, compute_ssim, compute_ncc, compute_mutual_information
from core.registration.mutual_information import register_mutual_information, compute_mi


class TestRadiometricNormalization:
    def test_histogram_match_distribution(self):
        src = np.random.randint(40, 120, (150, 150), dtype=np.uint8)
        ref = np.random.randint(120, 240, (150, 150), dtype=np.uint8)
        matched = histogram_match(src, ref)
        assert matched.shape == src.shape
        # Matched mean should shift towards reference mean
        assert abs(matched.mean() - ref.mean()) < abs(src.mean() - ref.mean())

    def test_wallis_filter_statistics(self):
        src = np.random.randint(30, 160, (150, 150), dtype=np.uint8)
        filtered = wallis_filter(src, target_mean=128.0, target_std=40.0)
        assert filtered.shape == src.shape
        assert abs(float(filtered.mean()) - 128.0) < 20.0

    def test_radiometric_normalize_wrapper(self):
        src = np.random.randint(30, 100, (100, 100), dtype=np.uint8)
        ref = np.random.randint(150, 220, (100, 100), dtype=np.uint8)
        src_norm, ref_norm = radiometric_normalize(src, ref, method="histogram_match")
        assert src_norm.shape == src.shape
        assert ref_norm.shape == ref.shape


class TestSubPixelRefinement:
    def test_phase_correlate_synthetic_shift(self):
        # Create patterned lunar surface
        base = np.zeros((200, 200), dtype=np.float32)
        cv2.circle(base, (100, 100), 45, 220, -1)
        cv2.circle(base, (70, 80), 20, 90, -1)
        base = cv2.GaussianBlur(base, (11, 11), 2.5)

        # Shift by sub-pixel displacement
        dx_true, dy_true = 0.35, -0.25
        M = np.float32([[1, 0, dx_true], [0, 1, dy_true]])
        shifted = cv2.warpAffine(base, M, (200, 200))

        dx_est, dy_est, peak = phase_correlate(shifted, base)
        assert peak > 0.4
        # Inverse shift relation
        assert abs(dx_est - (-dx_true)) < 0.25
        assert abs(dy_est - (-dy_true)) < 0.25

    def test_refine_registration_wrapper(self):
        base = np.zeros((150, 150), dtype=np.uint8)
        cv2.circle(base, (75, 75), 35, 200, -1)
        base = cv2.GaussianBlur(base, (9, 9), 2)

        coarse_mat = np.eye(3, dtype=np.float64)
        res = refine_registration(base, base, coarse_mat, model_type="similarity")
        assert res.peak_value > 0.5
        assert res.refined_matrix.shape == (3, 3) or res.refined_matrix.shape == (2, 3)


class TestIndependentValidation:
    def test_ssim_identity(self):
        img = np.random.randint(50, 200, (120, 120), dtype=np.uint8)
        ssim_val = compute_ssim(img, img)
        assert abs(ssim_val - 1.0) < 0.01

    def test_ncc_identity(self):
        img = np.random.randint(50, 200, (120, 120), dtype=np.uint8)
        ncc_val = compute_ncc(img, img)
        assert abs(ncc_val - 1.0) < 0.01

    def test_mutual_information(self):
        img = np.random.randint(50, 200, (120, 120), dtype=np.uint8)
        mi_val = compute_mutual_information(img, img)
        assert mi_val > 1.0


class TestMutualInformationRegistration:
    def test_mi_computation(self):
        img1 = np.ones((100, 100), dtype=np.uint8) * 128
        img2 = np.ones((100, 100), dtype=np.uint8) * 128
        mi = compute_mi(img1, img2)
        assert mi >= 0.0

    def test_mi_registration_fallback(self):
        ref = np.zeros((140, 140), dtype=np.uint8)
        cv2.circle(ref, (70, 70), 30, 200, -1)
        ref = cv2.GaussianBlur(ref, (7, 7), 2)

        # Cross-modal contrast flip with small shift
        src = 255 - ref
        T = np.float32([[1, 0, 3], [0, 1, -2]])
        src_shifted = cv2.warpAffine(src, T, (140, 140))

        res = register_mutual_information(src_shifted, ref, model="similarity", max_iter=25, pyramid_levels=2)
        assert res.final_mi >= res.initial_mi
        assert res.matrix.shape == (3, 3)
