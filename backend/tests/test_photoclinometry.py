"""
Unit tests for SELORA Stage 4c Photoclinometry (Shape-from-Shading) System:
- Photometric slope inversion & Frankot-Chellappa Fourier integration
- Lunar-Lambert & Lambertian reflectance models
- Solar metadata extraction (PDS4, .lbl, .json, and preset fallbacks)
- Pipeline integration test with photoclinometry toggle
"""

import numpy as np
import cv2
import pytest
from pathlib import Path
import tempfile
import os

from core.photoclinometry.shading import estimate_relief_map, _frankot_chellappa, _poisson_solve
from core.photoclinometry.metadata import extract_sun_angles, PRESET_SUN_ANGLES
from core.sensors.profiles import RegistrationConfig, PhotoclinometryConfig, _ohrc_iirs


class TestPhotoclinometryShading:
    def test_estimate_relief_map_basic(self):
        # Create a synthetic crater-like surface
        img = np.zeros((128, 128), dtype=np.uint8)
        cv2.circle(img, (64, 64), 30, 200, -1)
        cv2.circle(img, (64, 64), 20, 60, -1)
        img = cv2.GaussianBlur(img, (9, 9), 2.0)

        relief = estimate_relief_map(img, sun_azimuth=45.0, sun_elevation=30.0)
        assert relief.shape == img.shape
        assert relief.dtype == np.uint8
        # Output should span reasonable range
        assert relief.max() > relief.min()

    def test_estimate_relief_map_models(self):
        img = np.random.randint(40, 220, (100, 100), dtype=np.uint8)
        # Lunar-Lambert model
        r_ll = estimate_relief_map(img, sun_azimuth=90.0, sun_elevation=45.0, albedo_model="lunar_lambert")
        assert r_ll.shape == (100, 100)

        # Lambertian model
        r_lam = estimate_relief_map(img, sun_azimuth=90.0, sun_elevation=45.0, albedo_model="lambertian")
        assert r_lam.shape == (100, 100)

    def test_frankot_chellappa_integrability(self):
        # Create integrable slope fields p = cos(x), q = -sin(y)
        x = np.linspace(0, 2 * np.pi, 64)
        y = np.linspace(0, 2 * np.pi, 64)
        X, Y = np.meshgrid(x, y)
        p = np.cos(X).astype(np.float32)
        q = (-np.sin(Y)).astype(np.float32)

        z = _frankot_chellappa(p, q, eps=1e-4)
        assert z.shape == (64, 64)
        assert not np.isnan(z).any()
        assert not np.isinf(z).any()

    def test_poisson_solver(self):
        p = np.ones((64, 64), dtype=np.float32) * 0.1
        q = np.ones((64, 64), dtype=np.float32) * -0.1
        z = _poisson_solve(p, q)
        assert z.shape == (64, 64)
        assert not np.isnan(z).any()


class TestMetadataIngestion:
    def test_extract_from_override_config(self):
        override = {
            "source_sun_azimuth": 42.5,
            "source_sun_elevation": 33.0,
            "reference_sun_azimuth": 210.0,
            "reference_sun_elevation": 55.0,
        }
        src_angles = extract_sun_angles(None, override, role="source")
        ref_angles = extract_sun_angles(None, override, role="reference")
        assert src_angles == (42.5, 33.0)
        assert ref_angles == (210.0, 55.0)

    def test_extract_from_pds_lbl_file(self):
        content = """
        PDS_VERSION_ID = PDS3
        SOLAR_AZIMUTH_ANGLE = 78.4
        INCIDENCE_ANGLE = 40.0
        END
        """
        with tempfile.NamedTemporaryFile(suffix=".lbl", delete=False, mode="w", encoding="utf-8") as f:
            f.write(content)
            lbl_name = f.name

        img_path = Path(lbl_name).with_suffix(".png")
        try:
            angles = extract_sun_angles(img_path)
            assert angles is not None
            az, elev = angles
            assert abs(az - 78.4) < 1e-3
            assert abs(elev - 50.0) < 1e-3  # 90 - 40 = 50
        finally:
            if os.path.exists(lbl_name):
                os.unlink(lbl_name)

    def test_extract_preset_fallbacks(self):
        p_src = Path("data/raw/demo_hard_source.png")
        p_ref = Path("data/raw/demo_hard_reference.png")
        src_angles = extract_sun_angles(p_src)
        ref_angles = extract_sun_angles(p_ref)
        assert src_angles == (45.0, 30.0)
        assert ref_angles == (225.0, 60.0)


class TestPhotoclinometryProfiles:
    def test_photoclinometry_config_in_profile(self):
        cfg = _ohrc_iirs()
        assert cfg.photoclinometry.enabled is True
        assert cfg.photoclinometry.albedo_model == "lunar_lambert"
        d = cfg.to_dict()
        assert "photoclinometry" in d
        assert d["photoclinometry"]["enabled"] is True


class TestCounterfactualRenderer:
    def test_render_at_sun_angle_basic(self):
        from core.photoclinometry.render import render_at_sun_angle
        # Create a synthetic relief map
        relief = np.random.uniform(0, 255, (64, 64)).astype(np.uint8)
        rendered = render_at_sun_angle(relief, target_azimuth=45.0, target_elevation=30.0)
        assert rendered.shape == (64, 64)
        assert rendered.dtype == np.uint8
        assert rendered.min() >= 0
        assert rendered.max() <= 255

    def test_render_at_sun_angle_azimuth_variation(self):
        from core.photoclinometry.render import render_at_sun_angle
        # Relief with a slope along x
        y, x = np.mgrid[0:64, 0:64]
        relief = (x * 4.0).astype(np.float32)
        r1 = render_at_sun_angle(relief, target_azimuth=0.0, target_elevation=45.0)
        r2 = render_at_sun_angle(relief, target_azimuth=180.0, target_elevation=45.0)
        # Opposing illumination directions should produce different shading
        assert not np.array_equal(r1, r2)
        assert np.abs(r1.astype(float) - r2.astype(float)).mean() > 5.0

    def test_render_at_sun_angle_invalid_input(self):
        import pytest
        from core.photoclinometry.render import render_at_sun_angle
        with pytest.raises(ValueError):
            render_at_sun_angle(None, 45.0, 30.0)
        with pytest.raises(ValueError):
            render_at_sun_angle(np.zeros((10, 10, 3)), 45.0, 30.0)


class TestGeospatialMetadataAndOrientation:
    def test_extract_geospatial_metadata_override(self):
        from core.photoclinometry.metadata import extract_geospatial_metadata
        override = {"source_lat": -18.45, "source_lon": 45.67}
        geo = extract_geospatial_metadata(None, override, role="source")
        assert geo["lat"] == -18.45
        assert geo["lon"] == 45.67

    def test_extract_geospatial_metadata_missing_returns_none(self):
        from core.photoclinometry.metadata import extract_geospatial_metadata
        geo = extract_geospatial_metadata(Path("non_existent_image.png"), None, role="source")
        # Must return None, never fabricate
        assert geo["lat"] is None
        assert geo["lon"] is None

    def test_compute_image_orientation_compass(self):
        from core.photoclinometry.metadata import compute_image_orientation
        # Due North
        assert compute_image_orientation(10.0, 0.0, 0.0, 0.0) == "N"
        # Due South
        assert compute_image_orientation(0.0, 0.0, 10.0, 0.0) == "S"
        # Due East
        assert compute_image_orientation(0.0, 10.0, 0.0, 0.0) == "E"
        # Due West
        assert compute_image_orientation(0.0, 0.0, 0.0, 10.0) == "W"
        # Missing coordinates return Unknown
        assert compute_image_orientation(None, 0.0, 0.0, 0.0) == "Unknown"
        assert compute_image_orientation(10.0, 0.0, None, None) == "Unknown"


class TestPipelineIntegrationFeaturesAB:
    def test_pipeline_with_geospatial_and_counterfactual(self):
        from core.pipeline import run_registration
        from config import settings
        import shutil

        demo_src = Path(settings.DATA_ROOT) / "raw" / "demo_same_source.png"
        demo_ref = Path(settings.DATA_ROOT) / "raw" / "demo_same_reference.png"
        if not demo_src.exists() or not demo_ref.exists():
            return

        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        test_src_id = "test_geo_src"
        test_ref_id = "test_geo_ref"
        shutil.copy(demo_src, upload_dir / f"{test_src_id}.png")
        shutil.copy(demo_ref, upload_dir / f"{test_ref_id}.png")

        override = {
            "source_lat": -12.34,
            "source_lon": 56.78,
            "reference_lat": -12.44,
            "reference_lon": 56.78,
            "source_sun_azimuth": 45.0,
            "source_sun_elevation": 30.0,
            "reference_sun_azimuth": 225.0,
            "reference_sun_elevation": 60.0,
        }

        result = run_registration(
            source_image_id=test_src_id,
            reference_image_id=test_ref_id,
            source_sensor="OHRC",
            reference_sensor="OHRC",
            mode="fast",
            override_config=override,
        )

        assert result["status"] in ["success", "warning"]
        m = result["metrics"]
        assert m["source_lat"] == -12.34
        assert m["source_lon"] == 56.78
        assert m["reference_lat"] == -12.44
        assert m["reference_lon"] == 56.78
        assert m["source_sun_azimuth"] == 45.0
        assert m["source_sun_elevation"] == 30.0
        assert m["reference_sun_azimuth"] == 225.0
        assert m["reference_sun_elevation"] == 60.0
        assert m["image_orientation"] == "N"

        vis = result["visualizations"]
        assert vis["counterfactual_render"] is not None


