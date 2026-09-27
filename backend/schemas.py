"""
Shared Pydantic models / schemas for SELORA API
"""

from __future__ import annotations
from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ─────────────────────────────────────────────
# Image
# ─────────────────────────────────────────────

class ImageInfo(BaseModel):
    image_id: str
    filename: str
    width: int
    height: int
    channels: int
    dtype: str
    file_size_bytes: int
    sensor: Optional[str] = None          # detected or provided
    has_geotiff_metadata: bool = False
    sun_azimuth: Optional[float] = None
    sun_elevation: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# Registration Request
# ─────────────────────────────────────────────

SensorType = Literal["OHRC", "TMC2", "IIRS", "Unknown", "auto"]
RegistrationMode = Literal["fast", "robust", "research", "deep", "auto"]
TransformModel = Literal["similarity", "affine", "homography"]


class RegistrationRequest(BaseModel):
    source_image_id: str
    reference_image_id: str
    source_sensor: SensorType = "auto"
    reference_sensor: SensorType = "auto"
    mode: RegistrationMode = "auto"
    source_sun_azimuth: Optional[float] = None
    source_sun_elevation: Optional[float] = None
    reference_sun_azimuth: Optional[float] = None
    reference_sun_elevation: Optional[float] = None
    override_config: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────
# Transformation
# ─────────────────────────────────────────────

class TransformationMatrix(BaseModel):
    model: TransformModel
    matrix: List[List[float]]
    rotation_deg: Optional[float] = None
    scale: Optional[float] = None
    scale_x: Optional[float] = None
    scale_y: Optional[float] = None
    translation_x: Optional[float] = None
    translation_y: Optional[float] = None
    shear: Optional[float] = None
    aspect_ratio: Optional[float] = None
    perspective_kx: Optional[float] = None
    perspective_ky: Optional[float] = None
    perspective_strength: Optional[float] = None
    determinant: Optional[float] = None
    condition_number: Optional[float] = None
    distortion_flags: Optional[List[str]] = None
    distortion_summary: Optional[str] = None
    dof: Optional[int] = None
    inlier_count: int
    reprojection_rmse: float
    confidence: float


# ─────────────────────────────────────────────
# Metrics & Validation
# ─────────────────────────────────────────────

class RegistrationMetrics(BaseModel):
    total_matches: int
    inlier_count: int
    inlier_ratio: float
    rmse: float
    median_reprojection_error: float
    spatial_coverage: float
    confidence: float
    processing_time_sec: float
    transform_model: TransformModel
    pyramid_levels_used: int = 1
    # Advanced validation metrics
    cv_rmse: Optional[float] = None             # Cross-validated RMSE
    ssim: Optional[float] = None                # Structural Similarity Index
    ncc: Optional[float] = None                 # Normalized Cross-Correlation
    mutual_information: Optional[float] = None  # Mutual Information (bits)
    overlap_fraction: Optional[float] = None    # Valid overlap ratio
    sub_pixel_dx: Optional[float] = None        # Sub-pixel refinement X shift
    sub_pixel_dy: Optional[float] = None        # Sub-pixel refinement Y shift
    sub_pixel_confidence: Optional[float] = None # Phase correlation peak value
    radiometric_method: Optional[str] = None    # Radiometric normalization used
    relief_method: Optional[str] = None         # Photoclinometry relief transform used
    # Geospatial Orientation HUD fields
    source_lat: Optional[float] = None
    source_lon: Optional[float] = None
    reference_lat: Optional[float] = None
    reference_lon: Optional[float] = None
    source_sun_azimuth: Optional[float] = None
    source_sun_elevation: Optional[float] = None
    reference_sun_azimuth: Optional[float] = None
    reference_sun_elevation: Optional[float] = None
    image_orientation: Optional[str] = "Unknown"


# ─────────────────────────────────────────────
# Visualizations
# ─────────────────────────────────────────────

class Visualizations(BaseModel):
    registered_image: Optional[str] = None   # URL path
    overlay_image: Optional[str] = None
    difference_map: Optional[str] = None
    error_heatmap: Optional[str] = None
    match_visualization: Optional[str] = None
    inlier_visualization: Optional[str] = None
    source_thumbnail: Optional[str] = None
    reference_thumbnail: Optional[str] = None
    source_relief: Optional[str] = None
    reference_relief: Optional[str] = None
    counterfactual_render: Optional[str] = None
    points_csv: Optional[str] = None
    registered_geotiff: Optional[str] = None


# ─────────────────────────────────────────────
# Registration Result
# ─────────────────────────────────────────────

class RegistrationResult(BaseModel):
    status: Literal["success", "failed", "warning"]
    registration_id: str
    source_image_id: str
    reference_image_id: str
    source_sensor: str
    reference_sensor: str
    mode: str
    metrics: Optional[RegistrationMetrics] = None
    transformation: Optional[TransformationMatrix] = None
    visualizations: Optional[Visualizations] = None
    failure_reason: Optional[str] = None
    warnings: List[str] = []
    config_used: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# Failure Response
# ─────────────────────────────────────────────

class RegistrationFailure(BaseModel):
    status: Literal["failed"] = "failed"
    registration_id: str
    reason: str
    diagnostics: Dict[str, Any] = {}
    suggestions: List[str] = []


# ─────────────────────────────────────────────
# Benchmark
# ─────────────────────────────────────────────

class BenchmarkMethod(BaseModel):
    name: str
    feature: str
    matcher: str
    config: Dict[str, Any] = {}


class BenchmarkRequest(BaseModel):
    source_image_id: str
    reference_image_id: str
    methods: List[str] = ["orb", "sift", "akaze", "deep", "loftr", "selora_same", "selora_cross"]
    synthetic_transforms: Optional[List[Dict[str, Any]]] = None


class BenchmarkRow(BaseModel):
    method: str
    matches: int
    inliers: int
    inlier_ratio: float
    rmse: float
    processing_time_sec: float
    coverage: float
    confidence: float


class BenchmarkResult(BaseModel):
    benchmark_id: str
    rows: List[BenchmarkRow]
    created_at: datetime = Field(default_factory=datetime.utcnow)
