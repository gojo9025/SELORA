"""
SELORA Advanced Validation Module
Independent accuracy assessment using cross-validation and image-level metrics.

This module addresses two critical jury questions:
1. "Your RMSE uses the same points you fitted — that's circular."
   → We compute Leave-K-Out cross-validated RMSE
2. "How do you measure if the registered image actually looks right?"
   → We compute SSIM and NCC on the overlapping region

These are the standard validation metrics in the remote sensing literature.
"""

from __future__ import annotations
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from loguru import logger


@dataclass
class ValidationResult:
    """Independent validation metrics."""
    # Cross-validated accuracy
    cv_rmse: float                  # Leave-K-Out cross-validated RMSE
    fit_rmse: float                 # Standard RMSE (on training points)
    cv_improvement: float           # (fit_rmse - cv_rmse) / fit_rmse — negative = overfitting

    # Image-level quality
    ssim: float                     # Structural Similarity Index [-1, 1]
    ncc: float                      # Normalized Cross-Correlation [-1, 1]
    mutual_information: float       # Mutual Information (bits)

    # Overlap analysis
    overlap_fraction: float         # Fraction of reference covered by warped source


def compute_ssim(
    img1: np.ndarray,
    img2: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> float:
    """
    Compute Structural Similarity Index (SSIM) between two images.

    SSIM measures the perceived quality difference between two images,
    considering luminance, contrast, and structure. It's the standard
    metric for registration quality assessment in remote sensing.

    Uses the Wang et al. (2004) formulation with default constants.

    Args:
        img1, img2: Grayscale images (same size)
        mask:       Optional binary mask for valid region

    Returns:
        SSIM value in [-1, 1], where 1 = identical
    """
    # Convert to grayscale float
    if img1.ndim == 3:
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    if img2.ndim == 3:
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    h = min(img1.shape[0], img2.shape[0])
    w = min(img1.shape[1], img2.shape[1])
    img1 = img1[:h, :w].astype(np.float64)
    img2 = img2[:h, :w].astype(np.float64)

    # SSIM constants (for 8-bit images, L=255)
    L = 255.0
    C1 = (0.01 * L) ** 2
    C2 = (0.03 * L) ** 2

    # Create valid overlap mask
    if mask is None:
        # Auto-detect: exclude black borders from warped images
        valid1 = img1 > 5.0
        valid2 = img2 > 5.0
        mask = (valid1 & valid2).astype(np.float64)
    else:
        mask = mask.astype(np.float64)

    if mask.sum() < 100:
        logger.warning("SSIM: insufficient valid pixels")
        return 0.0

    # Window size for local statistics
    ksize = 11
    kernel = cv2.getGaussianKernel(ksize, 1.5)
    window = kernel @ kernel.T

    # Masked images
    m1 = img1 * mask
    m2 = img2 * mask

    # Local means
    mu1 = cv2.filter2D(m1, -1, window)
    mu2 = cv2.filter2D(m2, -1, window)
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    # Local variances and covariance
    sigma1_sq = cv2.filter2D(m1 ** 2, -1, window) - mu1_sq
    sigma2_sq = cv2.filter2D(m2 ** 2, -1, window) - mu2_sq
    sigma12 = cv2.filter2D(m1 * m2, -1, window) - mu1_mu2

    # SSIM map
    numerator = (2 * mu1_mu2 + C1) * (2 * sigma12 + C2)
    denominator = (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
    ssim_map = numerator / (denominator + 1e-10)

    # Mean SSIM over valid region
    mask_eroded = cv2.erode(mask.astype(np.uint8), np.ones((ksize, ksize), np.uint8))
    if mask_eroded.sum() < 10:
        return float(np.mean(ssim_map[mask > 0]))

    return float(np.mean(ssim_map[mask_eroded > 0]))


def compute_ncc(
    img1: np.ndarray,
    img2: np.ndarray,
) -> float:
    """
    Compute Normalized Cross-Correlation (NCC) between two images
    in the overlapping region.

    NCC is the standard similarity measure for template matching
    and registration quality. It's invariant to linear intensity changes.

    Args:
        img1, img2: Images (same size, grayscale or BGR)

    Returns:
        NCC value in [-1, 1], where 1 = perfectly correlated
    """
    if img1.ndim == 3:
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    if img2.ndim == 3:
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    h = min(img1.shape[0], img2.shape[0])
    w = min(img1.shape[1], img2.shape[1])
    a = img1[:h, :w].astype(np.float64)
    b = img2[:h, :w].astype(np.float64)

    # Valid overlap mask
    valid = (a > 5.0) & (b > 5.0)
    if valid.sum() < 100:
        return 0.0

    a_valid = a[valid]
    b_valid = b[valid]

    a_norm = a_valid - a_valid.mean()
    b_norm = b_valid - b_valid.mean()

    denom = np.sqrt((a_norm ** 2).sum() * (b_norm ** 2).sum())
    if denom < 1e-10:
        return 0.0

    ncc = float((a_norm * b_norm).sum() / denom)
    return ncc


def compute_mutual_information(
    img1: np.ndarray,
    img2: np.ndarray,
    bins: int = 64,
) -> float:
    """
    Compute Mutual Information between two images.

    MI measures the statistical dependence between pixel intensities.
    High MI indicates good registration regardless of the intensity
    mapping function — making it ideal for cross-modal assessment.

    I(A, B) = H(A) + H(B) - H(A, B)

    Args:
        img1, img2: Images (same size)
        bins:       Number of histogram bins

    Returns:
        Mutual information in bits
    """
    if img1.ndim == 3:
        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    if img2.ndim == 3:
        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    h = min(img1.shape[0], img2.shape[0])
    w = min(img1.shape[1], img2.shape[1])
    a = img1[:h, :w].ravel().astype(np.float64)
    b = img2[:h, :w].ravel().astype(np.float64)

    # Valid overlap
    valid = (a > 5.0) & (b > 5.0)
    if valid.sum() < 100:
        return 0.0

    a = a[valid]
    b = b[valid]

    # Joint histogram
    joint_hist, _, _ = np.histogram2d(a, b, bins=bins, range=[[0, 256], [0, 256]])
    joint_hist = joint_hist / joint_hist.sum()

    # Marginal distributions
    p_a = joint_hist.sum(axis=1)
    p_b = joint_hist.sum(axis=0)

    # Mutual information
    # I(A,B) = sum p(a,b) * log2(p(a,b) / (p(a)*p(b)))
    mi = 0.0
    for i in range(bins):
        for j in range(bins):
            if joint_hist[i, j] > 1e-10 and p_a[i] > 1e-10 and p_b[j] > 1e-10:
                mi += joint_hist[i, j] * np.log2(joint_hist[i, j] / (p_a[i] * p_b[j]))

    return float(mi)


def compute_overlap_fraction(
    warped: np.ndarray,
    reference: np.ndarray,
) -> float:
    """Compute what fraction of the reference image is covered by the warped source."""
    if warped.ndim == 3:
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    else:
        warped_gray = warped

    h = min(warped_gray.shape[0], reference.shape[0] if reference.ndim == 2 else reference.shape[0])
    w = min(warped_gray.shape[1], reference.shape[1] if reference.ndim == 2 else reference.shape[1])
    crop = warped_gray[:h, :w]

    valid = crop > 5  # non-black pixels
    total = h * w
    return float(valid.sum() / total) if total > 0 else 0.0


def cross_validate_rmse(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
    matrix: np.ndarray,
    model_type: str,
    n_folds: int = 5,
) -> float:
    """
    Compute cross-validated RMSE by holding out subsets of correspondences.

    This addresses the circular validation problem: standard RMSE uses the
    same points that were used to estimate the transformation. Cross-validated
    RMSE tests on unseen points, giving a more honest accuracy estimate.

    Args:
        src_pts:     Source inlier points (Nx2)
        dst_pts:     Destination inlier points (Nx2)
        matrix:      Estimated transformation matrix
        model_type:  'similarity' | 'affine' | 'homography'
        n_folds:     Number of cross-validation folds

    Returns:
        Cross-validated RMSE in pixels
    """
    n = len(src_pts)
    if n < 10:
        logger.warning("CV-RMSE: too few points for cross-validation")
        return -1.0

    # Ensure minimum fold size
    n_folds = min(n_folds, n // 4)
    if n_folds < 2:
        n_folds = 2

    indices = np.arange(n)
    np.random.seed(42)  # Reproducibility
    np.random.shuffle(indices)

    fold_size = n // n_folds
    all_errors = []

    for fold in range(n_folds):
        # Split into train and test
        test_start = fold * fold_size
        test_end = test_start + fold_size if fold < n_folds - 1 else n
        test_idx = indices[test_start:test_end]
        train_idx = np.concatenate([indices[:test_start], indices[test_end:]])

        train_src = src_pts[train_idx]
        train_dst = dst_pts[train_idx]
        test_src = src_pts[test_idx]
        test_dst = dst_pts[test_idx]

        # Re-estimate transform on training points
        try:
            if model_type == "homography":
                if len(train_src) < 4:
                    continue
                M, mask = cv2.findHomography(train_src, train_dst, cv2.RANSAC, 3.0)
            elif model_type == "affine":
                if len(train_src) < 3:
                    continue
                M, mask = cv2.estimateAffine2D(train_src, train_dst, method=cv2.RANSAC)
                if M is not None:
                    M = np.vstack([M, [0, 0, 1]])
            else:  # similarity
                if len(train_src) < 2:
                    continue
                M, mask = cv2.estimateAffinePartial2D(train_src, train_dst, method=cv2.RANSAC)
                if M is not None:
                    M = np.vstack([M, [0, 0, 1]])

            if M is None:
                continue

            # Compute reprojection error on TEST points
            test_h = np.hstack([test_src, np.ones((len(test_src), 1))])
            if model_type == "homography":
                proj = (M @ test_h.T).T
                proj[:, :2] /= proj[:, 2:3]
                errors = np.linalg.norm(proj[:, :2] - test_dst, axis=1)
            else:
                M23 = M[:2, :]
                proj = (M23 @ test_h.T).T
                errors = np.linalg.norm(proj - test_dst, axis=1)

            all_errors.extend(errors.tolist())
        except (cv2.error, np.linalg.LinAlgError):
            continue

    if len(all_errors) == 0:
        return -1.0

    cv_rmse = float(np.sqrt(np.mean(np.array(all_errors) ** 2)))
    logger.info(f"Cross-validated RMSE: {cv_rmse:.4f}px ({n_folds}-fold, {len(all_errors)} test points)")
    return cv_rmse


def validate_registration(
    warped: np.ndarray,
    reference: np.ndarray,
    src_inlier_pts: np.ndarray,
    dst_inlier_pts: np.ndarray,
    matrix: np.ndarray,
    model_type: str,
    fit_rmse: float,
) -> ValidationResult:
    """
    Comprehensive independent validation of registration quality.

    Args:
        warped:          Warped source image
        reference:       Reference image
        src_inlier_pts:  Source inlier correspondences (Nx2)
        dst_inlier_pts:  Reference inlier correspondences (Nx2)
        matrix:          Transformation matrix
        model_type:      'similarity' | 'affine' | 'homography'
        fit_rmse:        RMSE from the fitting step (for comparison)

    Returns:
        ValidationResult with all independent metrics
    """
    logger.info("Computing independent validation metrics...")

    # 1. Cross-validated RMSE
    cv_rmse = cross_validate_rmse(src_inlier_pts, dst_inlier_pts, matrix, model_type)

    # 2. SSIM
    ssim = compute_ssim(warped, reference)
    logger.info(f"SSIM: {ssim:.4f}")

    # 3. NCC
    ncc = compute_ncc(warped, reference)
    logger.info(f"NCC: {ncc:.4f}")

    # 4. Mutual Information
    mi = compute_mutual_information(warped, reference)
    logger.info(f"Mutual Information: {mi:.4f} bits")

    # 5. Overlap fraction
    overlap = compute_overlap_fraction(warped, reference)
    logger.info(f"Overlap fraction: {overlap:.2%}")

    # 6. Improvement metric
    if cv_rmse > 0 and fit_rmse > 0:
        cv_improvement = (fit_rmse - cv_rmse) / fit_rmse
    else:
        cv_improvement = 0.0

    return ValidationResult(
        cv_rmse=round(cv_rmse, 4),
        fit_rmse=round(fit_rmse, 4),
        cv_improvement=round(cv_improvement, 4),
        ssim=round(ssim, 4),
        ncc=round(ncc, 4),
        mutual_information=round(mi, 4),
        overlap_fraction=round(overlap, 4),
    )
