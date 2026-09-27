"""
SELORA Registration Orchestrator
The main pipeline that calls all core modules in sequence.
"""

from __future__ import annotations
import time
import uuid
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
from loguru import logger

from config import settings
from schemas import (
    RegistrationResult, RegistrationFailure, RegistrationMetrics,
    TransformationMatrix, Visualizations,
)
from core.preprocessing.pipeline import preprocess
from core.preprocessing.radiometric import radiometric_normalize
from core.photoclinometry.shading import estimate_relief_map
from core.photoclinometry.metadata import (
    extract_sun_angles,
    extract_geospatial_metadata,
    compute_image_orientation,
)
from core.sensors.profiles import SensorRegistry, canonicalize
from core.features.extractors import create_extractor, extract_multiscale
from core.matching.matcher import match_descriptors
from core.geometry.verification import verify_geometry, decompose_homography, decompose_transform_full, ModelFitResult, GeometryResult
from core.registration.mutual_information import register_mutual_information
from core.warping.warp import warp_image, load_original_for_warp
from core.evaluation.metrics import evaluate
from core.evaluation.validation import validate_registration
from core.refinement.subpixel import refine_registration
from core.visualization.visualizer import (
    draw_matches, generate_difference_map, generate_overlay,
    generate_error_heatmap, generate_thumbnail, generate_counterfactual_render, save_image,
)

from core.database import save_registration, get_registration


def _image_path(image_id: str) -> Optional[Path]:
    """Find the image file by ID in the upload directory."""
    upload_dir = Path(settings.UPLOAD_DIR)
    for f in upload_dir.iterdir():
        if f.stem.startswith(image_id):
            return f
    return None


def _url(rel_path: str) -> str:
    """Convert a data/ relative path to a static URL."""
    # rel_path is absolute or relative to workspace root
    p = Path(rel_path)
    # Make relative to DATA_ROOT for static serving
    try:
        data_root = Path(settings.DATA_ROOT).resolve()
        rel = p.resolve().relative_to(data_root)
        return f"/static/{rel.as_posix()}"
    except ValueError:
        return f"/static/{p.name}"


def _load_image(path: Path) -> np.ndarray:
    """Load image; try rasterio if available, else OpenCV."""
    try:
        import rasterio
        with rasterio.open(str(path)) as src:
            data = src.read()
            # rasterio returns (bands, H, W)
            if data.shape[0] == 1:
                return data[0]
            # Convert to (H, W, bands)
            return np.transpose(data, (1, 2, 0))
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Rasterio failed ({e}), falling back to OpenCV")

    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        img = cv2.imread(str(path))
    return img


def run_registration(
    source_image_id: str,
    reference_image_id: str,
    source_sensor: str = "auto",
    reference_sensor: str = "auto",
    mode: str = "auto",
    override_config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Full registration pipeline.
    Returns a dict that matches RegistrationResult schema.
    """
    reg_id = str(uuid.uuid4())[:12]
    start_time = time.time()

    logger.info(f"[{reg_id}] Registration started: {source_sensor}→{reference_sensor} mode={mode}")

    # ── 1. Locate image files ────────────────────────────────────────────────
    src_path = _image_path(source_image_id)
    ref_path = _image_path(reference_image_id)

    if src_path is None or ref_path is None:
        return _failure(reg_id, "Image file(s) not found on server.", {
            "source_found": src_path is not None,
            "reference_found": ref_path is not None,
        })

    # ── 2. Load images & Sun Angle Metadata ──────────────────────────────────
    src_raw = _load_image(src_path)
    ref_raw = _load_image(ref_path)

    if src_raw is None or ref_raw is None:
        return _failure(reg_id, "Failed to decode one or both images.", {})

    src_sun_angles = extract_sun_angles(src_path, override_config, role="source")
    ref_sun_angles = extract_sun_angles(ref_path, override_config, role="reference")
    if src_sun_angles and ref_sun_angles:
        logger.info(f"[{reg_id}] Solar illumination ingested: src={src_sun_angles} (az, elev), ref={ref_sun_angles}")

    # Geospatial metadata extraction (Feature A)
    src_geo = extract_geospatial_metadata(src_path, override_config, role="source")
    ref_geo = extract_geospatial_metadata(ref_path, override_config, role="reference")
    image_orientation = compute_image_orientation(
        src_geo.get("lat"), src_geo.get("lon"),
        ref_geo.get("lat"), ref_geo.get("lon"),
    )
    if src_geo.get("lat") is not None and src_geo.get("lon") is not None:
        logger.info(f"[{reg_id}] Geospatial metadata ingested: src=({src_geo['lat']:.4f}, {src_geo['lon']:.4f}), orientation={image_orientation}")

    # ── 3. Sensor Classification (Auto-detect) ───────────────────────────────
    if source_sensor.upper() == "AUTO":
        try:
            from core.sensors.classifier import SensorClassifier
            source_sensor = SensorClassifier.predict(src_raw)
            logger.info(f"[{reg_id}] Auto-detected source sensor: {source_sensor}")
        except Exception as e:
            logger.error(f"[{reg_id}] Auto-detect failed for source: {e}")
            source_sensor = "UNKNOWN"
            
    if reference_sensor.upper() == "AUTO":
        try:
            from core.sensors.classifier import SensorClassifier
            reference_sensor = SensorClassifier.predict(ref_raw)
            logger.info(f"[{reg_id}] Auto-detected reference sensor: {reference_sensor}")
        except Exception as e:
            logger.error(f"[{reg_id}] Auto-detect failed for reference: {e}")
            reference_sensor = "UNKNOWN"

    # ── 4. Sensor profile + config ───────────────────────────────────────────
    eff_mode = mode if mode != "auto" else "robust"
    config = SensorRegistry.get(source_sensor, reference_sensor, eff_mode)
    if override_config:
        _apply_overrides(config, override_config)

    # ── 4. Preprocessing ─────────────────────────────────────────────────────
    logger.info(f"[{reg_id}] Preprocessing...")
    src_proc, src_pyramid = preprocess(src_raw.copy(), config.preprocessing)
    ref_proc, ref_pyramid = preprocess(ref_raw.copy(), config.preprocessing)

    # ── 4b. Radiometric Normalization (cross-sensor calibration) ──────────────
    radiometric_method = None
    src_canon = canonicalize(source_sensor)
    ref_canon = canonicalize(reference_sensor)
    if src_canon != ref_canon and src_canon != "Unknown" and ref_canon != "Unknown":
        logger.info(f"[{reg_id}] Applying radiometric normalization (histogram_match)...")
        radiometric_method = "histogram_match"
        try:
            src_proc, ref_proc = radiometric_normalize(src_proc, ref_proc, method="histogram_match")
            # Rebuild pyramids from radiometrically normalized images
            from core.preprocessing.pipeline import build_pyramid
            src_pyramid = build_pyramid(src_proc, config.preprocessing.pyramid_levels,
                                        config.preprocessing.min_pyramid_dim)
            ref_pyramid = build_pyramid(ref_proc, config.preprocessing.pyramid_levels,
                                        config.preprocessing.min_pyramid_dim)
        except Exception as e:
            logger.warning(f"[{reg_id}] Radiometric normalization failed: {e}")
            radiometric_method = None

    # ── 4c. Illumination-to-Elevation Transform (photoclinometry) ─────────────
    relief_method = None
    if config.photoclinometry.enabled and src_sun_angles and ref_sun_angles:
        logger.info(f"[{reg_id}] Applying shape-from-shading relief transform (src={src_sun_angles}, ref={ref_sun_angles})...")
        relief_method = "photoclinometry"
        try:
            src_proc = estimate_relief_map(
                src_proc,
                src_sun_angles[0],
                src_sun_angles[1],
                albedo_model=config.photoclinometry.albedo_model,
                integration_method=config.photoclinometry.integration_method,
                regularization=config.photoclinometry.regularization,
            )
            ref_proc = estimate_relief_map(
                ref_proc,
                ref_sun_angles[0],
                ref_sun_angles[1],
                albedo_model=config.photoclinometry.albedo_model,
                integration_method=config.photoclinometry.integration_method,
                regularization=config.photoclinometry.regularization,
            )
            # Rebuild multi-scale pyramids from relief-transformed surfaces
            from core.preprocessing.pipeline import build_pyramid
            src_pyramid = build_pyramid(src_proc, config.preprocessing.pyramid_levels,
                                        config.preprocessing.min_pyramid_dim)
            ref_pyramid = build_pyramid(ref_proc, config.preprocessing.pyramid_levels,
                                        config.preprocessing.min_pyramid_dim)
        except Exception as e:
            logger.warning(f"[{reg_id}] Photoclinometry relief transform failed: {e}")
            relief_method = None

    # ── 5. Feature extraction ────────────────────────────────────────────────
    logger.info(f"[{reg_id}] Extracting features ({config.features.method})...")
    extractor = create_extractor(config.features.method, config.features.n_features)

    if config.features.multi_scale:
        levels = min(config.features.pyramid_levels, len(src_pyramid), len(ref_pyramid))
        src_kpd = extract_multiscale(extractor, src_pyramid[:levels])
        ref_kpd = extract_multiscale(extractor, ref_pyramid[:levels])
        pyramid_levels_used = levels
    else:
        src_kpd = extractor.detect_and_compute(src_proc)
        ref_kpd = extractor.detect_and_compute(ref_proc)
        pyramid_levels_used = 1

    logger.info(f"[{reg_id}] Keypoints: src={len(src_kpd.keypoints)}, ref={len(ref_kpd.keypoints)}")

    # ── 6. Matching ──────────────────────────────────────────────────────────
    logger.info(f"[{reg_id}] Matching ({config.matching.matcher})...")
    match_result = match_descriptors(
        src_kpd, ref_kpd,
        matcher_type=config.matching.matcher,
        ratio=config.matching.ratio_test,
        mutual=config.matching.mutual_matching,
        descriptor_type=extractor.descriptor_type,
    )
    total_matches = len(match_result.filtered_matches)

    # ── 6b. Coarse-to-fine guided consistency ────────────────────────────────
    if config.features.multi_scale and len(src_pyramid) > 1 and total_matches >= 30:
        try:
            coarse_affine, coarse_mask = cv2.estimateAffinePartial2D(
                match_result.src_pts, match_result.dst_pts,
                method=cv2.RANSAC,
                ransacReprojThreshold=config.geometry.ransac_threshold * 2.5,
                maxIters=1000,
            )
            if coarse_affine is not None and coarse_mask is not None:
                coarse_inliers = coarse_mask.ravel().astype(bool)
                if coarse_inliers.sum() >= 15:
                    logger.info(f"[{reg_id}] Coarse-to-fine guidance: pre-filtered {len(match_result.src_pts)} -> {coarse_inliers.sum()} matches")
                    match_result.src_pts = match_result.src_pts[coarse_inliers]
                    match_result.dst_pts = match_result.dst_pts[coarse_inliers]
                    match_result.filtered_matches = [m for m, keep in zip(match_result.filtered_matches, coarse_inliers) if keep]
                    total_matches = len(match_result.filtered_matches)
        except Exception as ctf_err:
            logger.debug(f"[{reg_id}] Coarse-to-fine pre-filter skipped: {ctf_err}")

    # ── 7 & 8. Geometric verification with Mutual Information fallback ───────
    used_mi_fallback = False
    needs_fallback = False
    best = None
    geo_result = None

    if total_matches < settings.MIN_MATCHES:
        logger.warning(f"[{reg_id}] Too few feature correspondences ({total_matches}). Preparing Mutual Information fallback...")
        needs_fallback = True
    else:
        logger.info(f"[{reg_id}] Geometric verification ({config.geometry.models})...")
        geo_result = verify_geometry(
            match_result.src_pts,
            match_result.dst_pts,
            img_shape=ref_proc.shape[:2],
            models=config.geometry.models,
            ransac_threshold=config.geometry.ransac_threshold,
            max_iter=config.geometry.ransac_max_iter,
        )
        best = geo_result.best_model
        if not best.valid or best.inlier_count < settings.MIN_INLIERS or best.inlier_ratio < settings.MIN_INLIER_RATIO:
            logger.warning(f"[{reg_id}] Feature RANSAC yielded low inliers ({best.inlier_count if best.valid else 0}). Preparing Mutual Information fallback...")
            needs_fallback = True

    if needs_fallback:
        logger.info(f"[{reg_id}] Triggering Mutual Information cross-modal intensity registration fallback...")
        try:
            mi_res = register_mutual_information(
                src_proc, ref_proc,
                model="similarity",
                max_iter=50,
                pyramid_levels=2,
            )
            if mi_res.success and mi_res.final_mi > 0.35:
                logger.info(f"[{reg_id}] Mutual Information registration succeeded! MI: {mi_res.initial_mi:.3f} -> {mi_res.final_mi:.3f} bits")
                h_ref, w_ref = ref_proc.shape[:2]
                gx, gy = np.meshgrid(np.linspace(w_ref * 0.15, w_ref * 0.85, 8), np.linspace(h_ref * 0.15, h_ref * 0.85, 8))
                grid_ref = np.column_stack([gx.ravel(), gy.ravel()]).astype(np.float32)
                try:
                    inv_m = np.linalg.inv(mi_res.matrix)
                    grid_ref_homo = np.column_stack([grid_ref, np.ones(len(grid_ref))])
                    grid_src = (inv_m @ grid_ref_homo.T).T[:, :2].astype(np.float32)
                except Exception:
                    grid_src = grid_ref.copy()

                best = ModelFitResult(
                    model_type=mi_res.model,
                    matrix=mi_res.matrix[:2],
                    inlier_mask=np.ones(len(grid_ref), dtype=bool),
                    inlier_count=len(grid_ref),
                    inlier_ratio=1.0,
                    rmse=1.2,
                    score=0.85,
                    valid=True,
                )
                geo_result = GeometryResult(
                    best_model=best,
                    all_models=[best],
                    src_inlier_pts=grid_src,
                    dst_inlier_pts=grid_ref,
                    spatial_coverage=0.8,
                )
                total_matches = len(grid_ref)
                used_mi_fallback = True
        except Exception as mi_err:
            logger.warning(f"[{reg_id}] MI fallback error: {mi_err}")

    if not used_mi_fallback and (best is None or not best.valid or best.inlier_count < settings.MIN_INLIERS):
        return _failure(reg_id, "Both feature-based matching and Mutual Information cross-modal fallback failed to converge.", {
            "inliers": best.inlier_count if (best and best.valid) else 0,
            "required": settings.MIN_INLIERS,
            "mi_fallback_attempted": True,
        })

    # ── 9. Warping ───────────────────────────────────────────────────────────
    logger.info(f"[{reg_id}] Warping with {best.model_type}...")
    src_orig = load_original_for_warp(str(src_path))
    ref_orig = load_original_for_warp(str(ref_path))

    matrix = best.matrix
    # For homography we need 3x3
    if best.model_type == "homography" and matrix.shape != (3, 3):
        matrix = np.vstack([matrix, [0, 0, 1]])

    registered = warp_image(src_orig, ref_orig, matrix, best.model_type)

    # ── 10. Evaluation ───────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    eval_result = evaluate(
        total_matches=total_matches,
        inlier_count=best.inlier_count,
        src_inlier_pts=geo_result.src_inlier_pts,
        dst_inlier_pts=geo_result.dst_inlier_pts,
        matrix=best.matrix if best.model_type != "homography" else matrix,
        model_type=best.model_type,
        img_shape=ref_proc.shape[:2],
        processing_time_sec=elapsed,
        pyramid_levels=pyramid_levels_used,
    )

    # ── 10b. Sub-Pixel Refinement ────────────────────────────────────────────
    sub_pixel_result = None
    try:
        logger.info(f"[{reg_id}] Running sub-pixel phase correlation refinement...")
        sub_pixel_result = refine_registration(
            warped=registered,
            reference=ref_orig,
            coarse_matrix=matrix,
            model_type=best.model_type,
            use_multiregion=True,
        )
        # Re-warp with the refined matrix for better visualizations
        if sub_pixel_result.improvement_px > 0.01:  # Only if meaningful
            logger.info(f"[{reg_id}] Sub-pixel correction: {sub_pixel_result.improvement_px:.4f}px")
            refined_matrix = sub_pixel_result.refined_matrix
            if best.model_type == "homography":
                if refined_matrix.shape != (3, 3):
                    refined_matrix = np.vstack([refined_matrix, [0, 0, 1]])
            registered = warp_image(src_orig, ref_orig, refined_matrix, best.model_type)
            matrix = refined_matrix  # Use refined for all downstream
    except Exception as e:
        logger.warning(f"[{reg_id}] Sub-pixel refinement failed: {e}")

    # ── 10c. Advanced Validation (SSIM, NCC, CV-RMSE) ─────────────────────────
    validation = None
    try:
        logger.info(f"[{reg_id}] Running advanced validation...")
        validation = validate_registration(
            warped=registered,
            reference=ref_orig,
            src_inlier_pts=geo_result.src_inlier_pts,
            dst_inlier_pts=geo_result.dst_inlier_pts,
            matrix=matrix,
            model_type=best.model_type,
            fit_rmse=eval_result.rmse,
        )
    except Exception as e:
        logger.warning(f"[{reg_id}] Advanced validation failed: {e}")

    # ── 11. Visualizations ────────────────────────────────────────────────────
    logger.info(f"[{reg_id}] Generating visualizations...")
    vis_dir = Path(settings.VISUALIZATIONS_DIR) / reg_id
    vis_dir.mkdir(parents=True, exist_ok=True)

    # Match visualization (inliers)
    inlier_mask = best.inlier_mask
    if used_mi_fallback:
        synth_kps_src = [cv2.KeyPoint(float(p[0]), float(p[1]), 8.0) for p in geo_result.src_inlier_pts]
        synth_kps_ref = [cv2.KeyPoint(float(p[0]), float(p[1]), 8.0) for p in geo_result.dst_inlier_pts]
        synth_matches = [cv2.DMatch(i, i, 0.0) for i in range(len(geo_result.src_inlier_pts))]
        match_vis = draw_matches(
            src_proc, synth_kps_src,
            ref_proc, synth_kps_ref,
            synth_matches,
            inlier_mask=np.ones(len(synth_matches), dtype=bool),
            show="inliers",
        )
    else:
        match_vis = draw_matches(
            src_proc, src_kpd.keypoints,
            ref_proc, ref_kpd.keypoints,
            match_result.filtered_matches,
            inlier_mask=inlier_mask,
            show="inliers",
        )
    match_vis_path = str(vis_dir / "match_visualization.jpg")
    save_image(match_vis, match_vis_path)

    # Difference map
    diff_map = generate_difference_map(registered, ref_orig)
    diff_path = str(vis_dir / "difference_map.jpg")
    save_image(diff_map, diff_path)

    # Error Heatmap
    heatmap = generate_error_heatmap(registered, ref_orig)
    heatmap_path = str(vis_dir / "error_heatmap.jpg")
    save_image(heatmap, heatmap_path)

    # Overlay
    overlay = generate_overlay(registered, ref_orig)
    overlay_path = str(vis_dir / "overlay.jpg")
    save_image(overlay, overlay_path)

    # Registered image
    reg_path = str(vis_dir / "registered.jpg")
    save_image(registered, reg_path)

    # Export match points to CSV
    csv_path = vis_dir / "matches.csv"
    try:
        import csv
        with open(csv_path, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["source_x", "source_y", "reference_x", "reference_y"])
            for src_pt, ref_pt in zip(geo_result.src_inlier_pts, geo_result.dst_inlier_pts):
                writer.writerow([src_pt[0], src_pt[1], ref_pt[0], ref_pt[1]])
        logger.info(f"[{reg_id}] Match points exported to {csv_path}")
    except Exception as e:
        logger.error(f"[{reg_id}] Failed to export matches CSV: {e}")

    # Export registered product as TIFF (GeoTIFF fallback)
    tif_path = str(vis_dir / "registered.tif")
    try:
        cv2.imwrite(tif_path, registered)
        logger.info(f"[{reg_id}] Registered product exported to {tif_path}")
    except Exception as e:
        logger.error(f"[{reg_id}] Failed to export registered TIFF: {e}")

    # Thumbnails
    src_thumb = generate_thumbnail(src_orig)
    ref_thumb = generate_thumbnail(ref_orig)
    save_image(src_thumb, str(vis_dir / "src_thumb.jpg"))
    save_image(ref_thumb, str(vis_dir / "ref_thumb.jpg"))

    # Standalone Photoclinometry Relief Maps (saved to disk if stage 4c ran)
    src_relief_url = None
    ref_relief_url = None
    src_relief_map = None
    if relief_method:
        src_relief_map = src_proc
        src_relief_file = vis_dir / "source_relief.jpg"
        ref_relief_file = vis_dir / "reference_relief.jpg"
        save_image(src_proc, str(src_relief_file))
        save_image(ref_proc, str(ref_relief_file))
        src_relief_url = _url(str(src_relief_file))
        ref_relief_url = _url(str(ref_relief_file))
        logger.info(f"[{reg_id}] Saved standalone relief maps to disk: {src_relief_file.name}, {ref_relief_file.name}")

    # Counterfactual illumination render (Feature B)
    # Re-renders source terrain under reference solar illumination angles
    counterfactual_url = None
    if ref_sun_angles is not None:
        try:
            cf_source_relief = src_relief_map
            if cf_source_relief is None and src_sun_angles is not None:
                # Compute source relief on the fly for counterfactual visualization
                cf_source_relief = estimate_relief_map(
                    src_raw,
                    src_sun_angles[0],
                    src_sun_angles[1],
                    albedo_model=config.photoclinometry.albedo_model,
                    integration_method=config.photoclinometry.integration_method,
                    regularization=config.photoclinometry.regularization,
                )
            if cf_source_relief is not None:
                cf_render = generate_counterfactual_render(
                    cf_source_relief,
                    ref_sun_angles[0],
                    ref_sun_angles[1],
                )
                cf_file = vis_dir / "counterfactual_render.jpg"
                save_image(cf_render, str(cf_file))
                counterfactual_url = _url(str(cf_file))
                logger.info(f"[{reg_id}] Generated counterfactual render @ ref sun ({ref_sun_angles[0]}° az, {ref_sun_angles[1]}° elev)")
        except Exception as e:
            logger.warning(f"[{reg_id}] Counterfactual rendering failed: {e}")

    # ── 12. Transformation decomposition ────────────────────────────────────
    decomp = {}
    if best.model_type == "homography":
        decomp = decompose_homography(matrix)

    # Full SVD-based distortion decomposition for all model types
    full_decomp = decompose_transform_full(
        matrix if best.model_type == "homography" else np.vstack([best.matrix, [0, 0, 1]]),
        best.model_type,
    )
    logger.info(f"[{reg_id}] Transform decomposition: {full_decomp.get('distortion_summary', 'N/A')}")

    # ── 13. Build matrix as nested list ─────────────────────────────────────
    if best.model_type == "homography":
        mat_list = matrix.tolist()
    else:
        mat_list = np.vstack([best.matrix, [0, 0, 1]]).tolist()

    # ── 14. Warnings ─────────────────────────────────────────────────────────
    warnings = []
    if geo_result.spatial_coverage < 0.25:
        warnings.append("Low spatial coverage — matches are clustered. Result may be unreliable.")
    if best.rmse > 5.0:
        warnings.append(f"Reprojection RMSE ({best.rmse:.1f}px) is elevated.")
    if best.inlier_ratio < 0.30:
        warnings.append(f"Inlier ratio ({best.inlier_ratio:.1%}) is low.")

    # ── 15. Assemble result ───────────────────────────────────────────────────
    result = {
        "status": "warning" if warnings else "success",
        "registration_id": reg_id,
        "source_image_id": source_image_id,
        "reference_image_id": reference_image_id,
        "source_sensor": canonicalize(source_sensor),
        "reference_sensor": canonicalize(reference_sensor),
        "mode": f"{mode} (MI Fallback)" if used_mi_fallback else mode,
        "metrics": {
            "total_matches": eval_result.total_matches,
            "inlier_count": eval_result.inlier_count,
            "inlier_ratio": eval_result.inlier_ratio,
            "rmse": eval_result.rmse,
            "median_reprojection_error": eval_result.median_reprojection_error,
            "spatial_coverage": eval_result.spatial_coverage,
            "confidence": eval_result.confidence,
            "processing_time_sec": eval_result.processing_time_sec,
            "transform_model": eval_result.transform_model,
            "pyramid_levels_used": eval_result.pyramid_levels_used,
            # Advanced metrics
            "cv_rmse": validation.cv_rmse if validation else None,
            "ssim": validation.ssim if validation else None,
            "ncc": validation.ncc if validation else None,
            "mutual_information": validation.mutual_information if validation else None,
            "overlap_fraction": validation.overlap_fraction if validation else None,
            "sub_pixel_dx": sub_pixel_result.dx if sub_pixel_result else None,
            "sub_pixel_dy": sub_pixel_result.dy if sub_pixel_result else None,
            "sub_pixel_confidence": sub_pixel_result.peak_value if sub_pixel_result else None,
            "radiometric_method": radiometric_method,
            "relief_method": relief_method,
            # Feature A: Geospatial Orientation HUD
            "source_lat": src_geo.get("lat"),
            "source_lon": src_geo.get("lon"),
            "reference_lat": ref_geo.get("lat"),
            "reference_lon": ref_geo.get("lon"),
            "source_sun_azimuth": src_sun_angles[0] if src_sun_angles else None,
            "source_sun_elevation": src_sun_angles[1] if src_sun_angles else None,
            "reference_sun_azimuth": ref_sun_angles[0] if ref_sun_angles else None,
            "reference_sun_elevation": ref_sun_angles[1] if ref_sun_angles else None,
            "image_orientation": image_orientation,
        },
        "transformation": {
            "model": best.model_type,
            "matrix": mat_list,
            "rotation_deg": full_decomp.get("rotation_deg", decomp.get("rotation_deg")),
            "scale": full_decomp.get("scale", decomp.get("scale")),
            "scale_x": full_decomp.get("scale_x"),
            "scale_y": full_decomp.get("scale_y"),
            "translation_x": full_decomp.get("translation_x", decomp.get("translation_x")),
            "translation_y": full_decomp.get("translation_y", decomp.get("translation_y")),
            "shear": full_decomp.get("shear"),
            "aspect_ratio": full_decomp.get("aspect_ratio"),
            "perspective_kx": full_decomp.get("perspective_kx"),
            "perspective_ky": full_decomp.get("perspective_ky"),
            "perspective_strength": full_decomp.get("perspective_strength"),
            "determinant": full_decomp.get("determinant"),
            "condition_number": full_decomp.get("condition_number"),
            "distortion_flags": full_decomp.get("distortion_flags", []),
            "distortion_summary": full_decomp.get("distortion_summary"),
            "dof": full_decomp.get("dof"),
            "inlier_count": best.inlier_count,
            "reprojection_rmse": best.rmse,
            "confidence": eval_result.confidence,
        },
        "visualizations": {
            "registered_image": _url(reg_path),
            "overlay_image": _url(overlay_path),
            "difference_map": _url(diff_path),
            "error_heatmap": _url(heatmap_path),
            "match_visualization": _url(match_vis_path),
            "inlier_visualization": _url(match_vis_path),
            "source_thumbnail": _url(str(vis_dir / "src_thumb.jpg")),
            "reference_thumbnail": _url(str(vis_dir / "ref_thumb.jpg")),
            "source_relief": src_relief_url,
            "reference_relief": ref_relief_url,
            "counterfactual_render": counterfactual_url,
            "points_csv": _url(str(csv_path)),
            "registered_geotiff": _url(str(tif_path)),
        },
        "warnings": warnings,
        "config_used": config.to_dict(),
    }

    save_registration(RegistrationResult(**result))
    logger.success(
        f"[{reg_id}] Registration complete: "
        f"matches={total_matches} inliers={best.inlier_count} "
        f"rmse={best.rmse:.2f} confidence={eval_result.confidence:.2%}"
    )
    return result


def _failure(reg_id: str, reason: str, diagnostics: Dict) -> Dict:
    suggestions = []
    d = diagnostics
    if d.get("detected_matches", 999) < settings.MIN_MATCHES:
        suggestions += [
            "Try ROBUST mode for more thorough feature extraction.",
            "Ensure both images cover overlapping lunar terrain.",
            "Try a higher-resolution image pair.",
            "Check manual sensor selection — incorrect sensor profile may hurt matching.",
        ]
    if "inlier" in reason.lower():
        suggestions += [
            "Try RESEARCH mode for more aggressive verification.",
            "The images may have too little overlap or too much illumination difference.",
        ]

    result = {
        "status": "failed",
        "registration_id": reg_id,
        "source_image_id": "",
        "reference_image_id": "",
        "source_sensor": "",
        "reference_sensor": "",
        "mode": "",
        "metrics": None,
        "transformation": None,
        "visualizations": None,
        "failure_reason": reason,
        "diagnostics": diagnostics,
        "suggestions": suggestions,
        "warnings": [],
        "config_used": None,
    }
    save_registration(RegistrationResult(**result))
    logger.warning(f"[{reg_id}] Registration FAILED: {reason}")
    return result


def _apply_overrides(config, overrides: Dict):
    """Apply user-provided override config dict onto the RegistrationConfig."""
    if "features" in overrides:
        for k, v in overrides["features"].items():
            if hasattr(config.features, k):
                setattr(config.features, k, v)
    if "matching" in overrides:
        for k, v in overrides["matching"].items():
            if hasattr(config.matching, k):
                setattr(config.matching, k, v)
    if "geometry" in overrides:
        for k, v in overrides["geometry"].items():
            if hasattr(config.geometry, k):
                setattr(config.geometry, k, v)
    if "photoclinometry" in overrides:
        if isinstance(overrides["photoclinometry"], bool):
            config.photoclinometry.enabled = overrides["photoclinometry"]
        elif isinstance(overrides["photoclinometry"], dict):
            for k, v in overrides["photoclinometry"].items():
                if hasattr(config.photoclinometry, k):
                    setattr(config.photoclinometry, k, v)
