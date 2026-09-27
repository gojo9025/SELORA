"""
SELORA Photoclinometry (Shape-from-Shading) Module
Recovers illumination-invariant relative elevation/relief maps
from single-view lunar imagery under known or estimated solar illumination.
"""

from core.photoclinometry.shading import estimate_relief_map
from core.photoclinometry.metadata import (
    extract_sun_angles,
    extract_geospatial_metadata,
    compute_image_orientation,
)
from core.photoclinometry.render import render_at_sun_angle

__all__ = [
    "estimate_relief_map",
    "extract_sun_angles",
    "extract_geospatial_metadata",
    "compute_image_orientation",
    "render_at_sun_angle",
]

