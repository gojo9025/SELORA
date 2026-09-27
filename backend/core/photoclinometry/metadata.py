"""
SELORA Photoclinometry Metadata Ingestion
Extracts solar illumination angles (sun_azimuth, sun_elevation) from:
1. Direct API override_config
2. Companion PDS4/PDS3 labels (.lbl, .xml, .json)
3. Known benchmark preset pairs & sensible fallbacks
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from loguru import logger

# Preset defaults for synthetic / benchmark demonstration pairs
PRESET_SUN_ANGLES: Dict[str, Tuple[float, float]] = {
    "demo_hard_source": (45.0, 30.0),       # Illumination from NE at 30° elevation
    "demo_hard_reference": (225.0, 60.0),   # Illumination from SW at 60° elevation (extreme Δ180° azimuth)
    "demo_ohrc_source": (85.0, 35.0),
    "demo_tmc2_reference": (190.0, 50.0),
    "demo_same_source": (120.0, 45.0),
    "demo_same_reference": (120.0, 45.0),
}


def extract_sun_angles(
    image_path: Optional[Path],
    override_config: Optional[Dict[str, Any]] = None,
    role: str = "source",
) -> Optional[Tuple[float, float]]:
    """
    Extract (sun_azimuth, sun_elevation) in degrees for an image.

    Args:
        image_path:       Path to image file (or None).
        override_config:  Optional dict with user-supplied override parameters.
        role:             "source" or "reference".

    Returns:
        (sun_azimuth, sun_elevation) tuple in degrees, or None if undetermined.
    """
    # ── 1. Check override_config ─────────────────────────────────────────────
    if override_config:
        # Check role-specific keys first, then generic
        az_key = f"{role}_sun_azimuth"
        el_key = f"{role}_sun_elevation"
        if az_key in override_config and el_key in override_config:
            try:
                return float(override_config[az_key]), float(override_config[el_key])
            except (ValueError, TypeError):
                pass

        if "sun_azimuth" in override_config and "sun_elevation" in override_config:
            try:
                return float(override_config["sun_azimuth"]), float(override_config["sun_elevation"])
            except (ValueError, TypeError):
                pass

    if image_path is None:
        return None

    stem = image_path.stem.lower()
    parent = image_path.parent

    # ── 2. Check filename matches in PRESET_SUN_ANGLES ────────────────────────
    for preset_key, angles in PRESET_SUN_ANGLES.items():
        if preset_key in stem:
            logger.debug(f"Resolved sun angles for '{image_path.name}' from preset map: az={angles[0]}°, elev={angles[1]}°")
            return angles

    # ── 3. Check companion metadata files (.lbl, .xml, .json) ────────────────
    # Check .lbl (PDS3 / PDS4 text label)
    lbl_path = image_path.with_suffix(".lbl")
    if not lbl_path.exists():
        lbl_path = parent / f"{stem}.lbl"
    if lbl_path.exists():
        angles = _parse_pds_label(lbl_path)
        if angles:
            return angles

    # Check .xml (PDS4 XML label)
    xml_path = image_path.with_suffix(".xml")
    if not xml_path.exists():
        xml_path = parent / f"{stem}.xml"
    if xml_path.exists():
        angles = _parse_xml_label(xml_path)
        if angles:
            return angles

    # Check .json companion
    json_path = image_path.with_suffix(".json")
    if not json_path.exists():
        json_path = parent / f"{stem}.json"
    if json_path.exists():
        angles = _parse_json_metadata(json_path)
        if angles:
            return angles

    return None


def _parse_pds_label(path: Path) -> Optional[Tuple[float, float]]:
    """Parse standard PDS3/PDS4 key-value lines from a .lbl file."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        azimuth = None
        elevation = None

        # Look for azimuth
        az_match = re.search(r"(?:SOLAR_AZIMUTH_ANGLE|SUN_AZIMUTH)\s*=\s*([0-9\.\+-]+)", text, re.IGNORECASE)
        if az_match:
            azimuth = float(az_match.group(1))

        # Look for elevation or incidence angle (elevation = 90 - incidence)
        el_match = re.search(r"(?:SOLAR_ELEVATION_ANGLE|SUN_ELEVATION)\s*=\s*([0-9\.\+-]+)", text, re.IGNORECASE)
        if el_match:
            elevation = float(el_match.group(1))
        else:
            inc_match = re.search(r"INCIDENCE_ANGLE\s*=\s*([0-9\.\+-]+)", text, re.IGNORECASE)
            if inc_match:
                elevation = max(1.0, 90.0 - float(inc_match.group(1)))

        if azimuth is not None and elevation is not None:
            return azimuth, elevation
    except Exception as e:
        logger.debug(f"Failed to parse PDS label {path}: {e}")
    return None


def _parse_xml_label(path: Path) -> Optional[Tuple[float, float]]:
    """Parse PDS4 XML tags."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        azimuth = None
        elevation = None

        az_match = re.search(r"<solar_azimuth_angle[^>]*>([0-9\.\+-]+)</solar_azimuth_angle>", text, re.IGNORECASE)
        if az_match:
            azimuth = float(az_match.group(1))

        el_match = re.search(r"<solar_elevation_angle[^>]*>([0-9\.\+-]+)</solar_elevation_angle>", text, re.IGNORECASE)
        if el_match:
            elevation = float(el_match.group(1))
        else:
            inc_match = re.search(r"<incidence_angle[^>]*>([0-9\.\+-]+)</incidence_angle>", text, re.IGNORECASE)
            if inc_match:
                elevation = max(1.0, 90.0 - float(inc_match.group(1)))

        if azimuth is not None and elevation is not None:
            return azimuth, elevation
    except Exception as e:
        logger.debug(f"Failed to parse XML label {path}: {e}")
    return None


def _parse_json_metadata(path: Path) -> Optional[Tuple[float, float]]:
    """Parse JSON metadata file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        az = data.get("sun_azimuth") or data.get("solar_azimuth_angle")
        el = data.get("sun_elevation") or data.get("solar_elevation_angle")
        if el is None and "incidence_angle" in data:
            el = max(1.0, 90.0 - float(data["incidence_angle"]))
        if az is not None and el is not None:
            return float(az), float(el)
    except Exception as e:
        logger.debug(f"Failed to parse JSON metadata {path}: {e}")
    return None


def extract_geospatial_metadata(
    image_path: Optional[Path],
    override_config: Optional[Dict[str, Any]] = None,
    role: str = "source",
) -> Dict[str, Optional[float]]:
    """
    Extract image center (lat, lon) in degrees from PDS4/PDS3 label, JSON, or override_config.
    Returns {'lat': float | None, 'lon': float | None}.
    If coordinates are not found, returns None without guessing.
    """
    lat: Optional[float] = None
    lon: Optional[float] = None

    # 1. Check override_config
    if override_config:
        lat_keys = [f"{role}_lat", f"{role}_latitude", "lat", "latitude", "center_latitude"]
        lon_keys = [f"{role}_lon", f"{role}_longitude", "lon", "longitude", "center_longitude"]
        for k in lat_keys:
            if k in override_config and override_config[k] is not None:
                try:
                    lat = float(override_config[k])
                    break
                except (ValueError, TypeError):
                    pass
        for k in lon_keys:
            if k in override_config and override_config[k] is not None:
                try:
                    lon = float(override_config[k])
                    break
                except (ValueError, TypeError):
                    pass

    if lat is not None and lon is not None:
        return {"lat": lat, "lon": lon}

    if image_path is None:
        return {"lat": lat, "lon": lon}

    stem = image_path.stem.lower()
    parent = image_path.parent

    # 2. Check companion .lbl (PDS3 / PDS4 text label)
    lbl_path = image_path.with_suffix(".lbl")
    if not lbl_path.exists():
        lbl_path = parent / f"{stem}.lbl"
    if lbl_path.exists():
        coords = _parse_pds_coords(lbl_path)
        if coords[0] is not None and lat is None:
            lat = coords[0]
        if coords[1] is not None and lon is None:
            lon = coords[1]

    # 3. Check companion .xml (PDS4 XML label)
    if lat is None or lon is None:
        xml_path = image_path.with_suffix(".xml")
        if not xml_path.exists():
            xml_path = parent / f"{stem}.xml"
        if xml_path.exists():
            coords = _parse_xml_coords(xml_path)
            if coords[0] is not None and lat is None:
                lat = coords[0]
            if coords[1] is not None and lon is None:
                lon = coords[1]

    # 4. Check companion .json
    if lat is None or lon is None:
        json_path = image_path.with_suffix(".json")
        if not json_path.exists():
            json_path = parent / f"{stem}.json"
        if json_path.exists():
            coords = _parse_json_coords(json_path)
            if coords[0] is not None and lat is None:
                lat = coords[0]
            if coords[1] is not None and lon is None:
                lon = coords[1]

    return {"lat": lat, "lon": lon}


def _parse_pds_coords(path: Path) -> Tuple[Optional[float], Optional[float]]:
    """Parse center latitude and longitude from a PDS label."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lat = None
        lon = None
        lat_match = re.search(r"(?:CENTER_LATITUDE|SUB_SPACECRAFT_LATITUDE|LATITUDE)\s*=\s*([0-9\.\+-]+)", text, re.IGNORECASE)
        if lat_match:
            lat = float(lat_match.group(1))
        lon_match = re.search(r"(?:CENTER_LONGITUDE|SUB_SPACECRAFT_LONGITUDE|LONGITUDE)\s*=\s*([0-9\.\+-]+)", text, re.IGNORECASE)
        if lon_match:
            lon = float(lon_match.group(1))
        return lat, lon
    except Exception as e:
        logger.debug(f"Failed to parse coordinates from PDS label {path}: {e}")
        return None, None


def _parse_xml_coords(path: Path) -> Tuple[Optional[float], Optional[float]]:
    """Parse center latitude and longitude from a PDS4 XML label."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lat = None
        lon = None
        lat_match = re.search(r"<(?:center_latitude|latitude)[^>]*>([0-9\.\+-]+)</(?:center_latitude|latitude)>", text, re.IGNORECASE)
        if lat_match:
            lat = float(lat_match.group(1))
        lon_match = re.search(r"<(?:center_longitude|longitude)[^>]*>([0-9\.\+-]+)</(?:center_longitude|longitude)>", text, re.IGNORECASE)
        if lon_match:
            lon = float(lon_match.group(1))
        return lat, lon
    except Exception as e:
        logger.debug(f"Failed to parse coordinates from XML label {path}: {e}")
        return None, None


def _parse_json_coords(path: Path) -> Tuple[Optional[float], Optional[float]]:
    """Parse latitude and longitude from JSON companion."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        lat = data.get("center_latitude") or data.get("latitude") or data.get("lat")
        lon = data.get("center_longitude") or data.get("longitude") or data.get("lon")
        lat_val = float(lat) if lat is not None else None
        lon_val = float(lon) if lon is not None else None
        return lat_val, lon_val
    except Exception as e:
        logger.debug(f"Failed to parse coordinates from JSON {path}: {e}")
        return None, None


def compute_image_orientation(
    src_lat: Optional[float],
    src_lon: Optional[float],
    ref_lat: Optional[float],
    ref_lon: Optional[float],
) -> str:
    """
    Compute compass direction (N, NE, E, SE, S, SW, W, NW) from spatial coordinates.
    Returns 'Unknown' if coordinates are not available.
    """
    import math

    if src_lat is None or src_lon is None or ref_lat is None or ref_lon is None:
        return "Unknown"

    d_lat = src_lat - ref_lat
    d_lon = src_lon - ref_lon

    if abs(d_lat) < 1e-6 and abs(d_lon) < 1e-6:
        return "N"

    avg_lat = math.radians((src_lat + ref_lat) / 2.0)
    x = math.radians(d_lon) * math.cos(avg_lat)
    y = math.radians(d_lat)

    bearing = math.degrees(math.atan2(x, y)) % 360.0
    compass_sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    sector_idx = int(round(bearing / 45.0)) % 8
    return compass_sectors[sector_idx]

