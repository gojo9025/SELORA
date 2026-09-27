"""
SELORA Sensor Profile System
Defines per-sensor and per-sensor-pair registration configurations.
The SensorRegistry maps sensor pairs → pipeline configurations.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from core.preprocessing.pipeline import PreprocessingConfig


@dataclass
class FeatureConfig:
    method: str = "SIFT"              # SIFT | ORB | AKAZE | SUPERPOINT
    multi_scale: bool = True
    pyramid_levels: int = 3
    n_features: int = 5000


@dataclass
class MatchingConfig:
    matcher: str = "FLANN"            # BF | FLANN
    ratio_test: float = 0.75
    mutual_matching: bool = True
    cross_check: bool = False


@dataclass
class GeometryConfig:
    models: List[str] = field(
        default_factory=lambda: ["affine", "homography"]
    )
    ransac_threshold: float = 3.0
    ransac_max_iter: int = 2000
    min_inliers: int = 10


@dataclass
class PhotoclinometryConfig:
    enabled: bool = False
    albedo_model: str = "lunar_lambert"          # lunar_lambert | lambertian
    integration_method: str = "frankot_chellappa"  # frankot_chellappa | poisson
    regularization: float = 1e-4


@dataclass
class RegistrationConfig:
    """Complete pipeline configuration for a sensor pair."""
    sensor_pair: str
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    photoclinometry: PhotoclinometryConfig = field(default_factory=PhotoclinometryConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    geometry: GeometryConfig = field(default_factory=GeometryConfig)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_pair": self.sensor_pair,
            "preprocessing": asdict(self.preprocessing),
            "photoclinometry": asdict(self.photoclinometry),
            "features": asdict(self.features),
            "matching": asdict(self.matching),
            "geometry": asdict(self.geometry),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Sensor profile definitions
# ─────────────────────────────────────────────────────────────────────────────

def _ohrc_tmc2() -> RegistrationConfig:
    """
    OHRC (25cm) → TMC-2 (5m): large resolution difference.
    Use gradient representation + multi-scale + SIFT.
    """
    return RegistrationConfig(
        sensor_pair="OHRC_TMC2",
        description="High-res optical to medium-res optical — gradient + multi-scale",
        preprocessing=PreprocessingConfig(
            grayscale=True,
            normalize=True,
            clahe=True,
            gradient_representation=True,
            pyramid_levels=4,
        ),
        features=FeatureConfig(method="SIFT", multi_scale=True, pyramid_levels=4, n_features=8000),
        matching=MatchingConfig(matcher="FLANN", ratio_test=0.75, mutual_matching=True),
        geometry=GeometryConfig(
            models=["affine", "homography"],
            ransac_threshold=3.0,
        ),
    )


def _ohrc_iirs() -> RegistrationConfig:
    """
    OHRC (optical) → IIRS (spectral): very different modalities.
    Heavy gradient representation required.
    """
    return RegistrationConfig(
        sensor_pair="OHRC_IIRS",
        description="High-res optical to spectral imaging — strong gradient emphasis",
        preprocessing=PreprocessingConfig(
            grayscale=True,
            normalize=True,
            percentile_low=2.0,
            percentile_high=98.0,
            clahe=True,
            clahe_clip_limit=3.0,
            gradient_representation=True,
            pyramid_levels=4,
        ),
        photoclinometry=PhotoclinometryConfig(
            enabled=True,
            albedo_model="lunar_lambert",
            integration_method="frankot_chellappa",
        ),
        features=FeatureConfig(method="SIFT", multi_scale=True, pyramid_levels=4, n_features=6000),
        matching=MatchingConfig(matcher="FLANN", ratio_test=0.70, mutual_matching=True),
        geometry=GeometryConfig(
            models=["affine", "homography"],
            ransac_threshold=4.0,
        ),
    )


def _tmc2_iirs() -> RegistrationConfig:
    """TMC-2 (medium res) → IIRS (spectral)."""
    return RegistrationConfig(
        sensor_pair="TMC2_IIRS",
        description="Medium-res optical to spectral — gradient + multi-scale",
        preprocessing=PreprocessingConfig(
            grayscale=True,
            normalize=True,
            clahe=True,
            gradient_representation=True,
            pyramid_levels=3,
        ),
        features=FeatureConfig(method="SIFT", multi_scale=True, pyramid_levels=3, n_features=5000),
        matching=MatchingConfig(matcher="FLANN", ratio_test=0.75, mutual_matching=True),
        geometry=GeometryConfig(
            models=["similarity", "affine", "homography"],
            ransac_threshold=3.0,
        ),
    )


def _same_sensor_robust() -> RegistrationConfig:
    """Same sensor pair — standard SIFT registration."""
    return RegistrationConfig(
        sensor_pair="SAME_SENSOR",
        description="Same-sensor registration — standard SIFT",
        preprocessing=PreprocessingConfig(
            grayscale=True,
            normalize=True,
            clahe=True,
            gradient_representation=False,
            pyramid_levels=3,
        ),
        features=FeatureConfig(method="SIFT", multi_scale=True, pyramid_levels=3, n_features=5000),
        matching=MatchingConfig(matcher="FLANN", ratio_test=0.75, mutual_matching=True),
        geometry=GeometryConfig(
            models=["similarity", "affine", "homography"],
            ransac_threshold=3.0,
        ),
    )


def _generic_robust() -> RegistrationConfig:
    """Generic fallback for unknown sensor pairs."""
    return RegistrationConfig(
        sensor_pair="GENERIC",
        description="Generic robust — SIFT + gradient + multi-scale",
        preprocessing=PreprocessingConfig(
            grayscale=True,
            normalize=True,
            clahe=True,
            gradient_representation=True,
            pyramid_levels=3,
        ),
        features=FeatureConfig(method="SIFT", multi_scale=True, pyramid_levels=3, n_features=5000),
        matching=MatchingConfig(matcher="FLANN", ratio_test=0.75, mutual_matching=True),
        geometry=GeometryConfig(
            models=["affine", "homography"],
            ransac_threshold=3.5,
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mode overrides
# ─────────────────────────────────────────────────────────────────────────────

def apply_mode_override(config: RegistrationConfig, mode: str) -> RegistrationConfig:
    """Apply fast/robust/research mode overrides on top of sensor profile config."""
    if mode == "fast":
        config.features.method = "ORB"
        config.features.multi_scale = False
        config.features.pyramid_levels = 1
        config.features.n_features = 3000
        config.matching.matcher = "BF"
        config.matching.mutual_matching = False
        config.preprocessing.clahe = False
        config.preprocessing.gradient_representation = False
        config.geometry.models = ["affine"]
    elif mode == "robust":
        # Keep sensor defaults but ensure SIFT + FLANN
        config.features.method = "SIFT"
        config.matching.matcher = "FLANN"
        config.matching.mutual_matching = True
    elif mode == "research":
        config.features.method = "SIFT"
        config.features.n_features = 10000
        config.features.pyramid_levels = 4
        config.matching.matcher = "FLANN"
        config.matching.mutual_matching = True
        config.matching.ratio_test = 0.70
        config.preprocessing.gradient_representation = True
        config.geometry.models = ["similarity", "affine", "homography"]
        config.geometry.ransac_max_iter = 5000
    elif mode == "deep":
        config.features.method = "DEEP"
        config.features.n_features = 5000
        config.features.pyramid_levels = 1
        config.matching.matcher = "LIGHTGLUE"
        config.matching.mutual_matching = True
        config.matching.ratio_test = 0.85
        config.preprocessing.gradient_representation = False
        config.geometry.models = ["affine", "homography"]
        config.geometry.ransac_max_iter = 5000
    # "auto" → use sensor defaults
    return config


# ─────────────────────────────────────────────────────────────────────────────
# Sensor Registry
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL_NAMES = {
    "ohrc": "OHRC",
    "tmc2": "TMC2",
    "tmc-2": "TMC2",
    "iirs": "IIRS",
    "lro_nac": "LRO_NAC",
    "lronac": "LRO_NAC",
    "lro-nac": "LRO_NAC",
    "selene": "SELENE",
    "kaguya": "SELENE",
    "unknown": "Unknown",
    "auto": "Unknown",
    "other": "Unknown",
}


def canonicalize(sensor: str) -> str:
    return CANONICAL_NAMES.get(sensor.lower(), "Unknown")


class SensorRegistry:
    """Maps (source_sensor, reference_sensor) → RegistrationConfig."""

    _profiles: Dict[Tuple[str, str], RegistrationConfig] = {}

    @classmethod
    def _build(cls):
        ohrc = "OHRC"
        tmc2 = "TMC2"
        iirs = "IIRS"
        lro_nac = "LRO_NAC"
        selene = "SELENE"
        unk = "Unknown"

        cls._profiles = {
            (ohrc, tmc2): _ohrc_tmc2(),
            (tmc2, ohrc): _ohrc_tmc2(),       # symmetric
            (ohrc, iirs): _ohrc_iirs(),
            (iirs, ohrc): _ohrc_iirs(),
            (tmc2, iirs): _tmc2_iirs(),
            (iirs, tmc2): _tmc2_iirs(),
            (ohrc, lro_nac): _same_sensor_robust(),  # high-res to high-res
            (lro_nac, ohrc): _same_sensor_robust(),
            (tmc2, selene): _same_sensor_robust(),   # med-res to med-res
            (selene, tmc2): _same_sensor_robust(),
            (ohrc, ohrc): _same_sensor_robust(),
            (tmc2, tmc2): _same_sensor_robust(),
            (iirs, iirs): _same_sensor_robust(),
            (lro_nac, lro_nac): _same_sensor_robust(),
            (selene, selene): _same_sensor_robust(),
            (unk, unk): _generic_robust(),
            (ohrc, unk): _generic_robust(),
            (tmc2, unk): _generic_robust(),
            (iirs, unk): _generic_robust(),
            (lro_nac, unk): _generic_robust(),
            (selene, unk): _generic_robust(),
            (unk, ohrc): _generic_robust(),
            (unk, tmc2): _generic_robust(),
            (unk, iirs): _generic_robust(),
            (unk, lro_nac): _generic_robust(),
            (unk, selene): _generic_robust(),
        }

    @classmethod
    def get(
        cls,
        source_sensor: str,
        reference_sensor: str,
        mode: str = "auto",
    ) -> RegistrationConfig:
        if not cls._profiles:
            cls._build()

        src = canonicalize(source_sensor)
        ref = canonicalize(reference_sensor)
        key = (src, ref)

        if key not in cls._profiles:
            logger.warning(f"No profile for {key}, using generic robust")
            config = _generic_robust()
        else:
            # Return a copy to avoid mutation across requests
            import copy
            config = copy.deepcopy(cls._profiles[key])

        src_canon = canonicalize(source_sensor)
        ref_canon = canonicalize(reference_sensor)

        # Gradient representation is only beneficial for cross-modal pairs
        is_cross_modal = (src_canon != ref_canon) and \
                         (src_canon != "Unknown") and \
                         (ref_canon != "Unknown")

        config.preprocessing.gradient_representation = is_cross_modal

        logger.info(
            f"Gradient representation auto-set to {is_cross_modal} "
            f"for pair {src_canon}→{ref_canon}"
        )

        config = apply_mode_override(config, mode)
        logger.info(f"SensorRegistry: {src}→{ref} mode={mode} → {config.description}")
        return config
