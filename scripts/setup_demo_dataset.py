"""
SELORA Demo Setup Script — Real Lunar Dataset
================================================================
Creates curated benchmark pairs for SIH 2026 live demonstration.

Generates realistic simulated pairs that mimic:
  1. OHRC <-> LRO NAC  (same-scale cross-mission, ~0.25m vs ~0.5m)
  2. OHRC <-> TMC-2    (20x scale gap)
  3. OHRC <-> IIRS     (320x scale gap, simulated IR signature)
  4. Illumination Shift (same sensor, opposing shadows)

Each pair is pre-labeled with ground-truth affine parameters for
automated regression testing and jury demonstration.

Usage:
    python scripts/setup_demo_dataset.py
"""

import sys
import os
import json
import cv2
import numpy as np
from pathlib import Path

# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_RAW.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = DATA_RAW / "demo_manifest.json"


def _make_lunar_texture(size: int = 1024, seed: int = 42) -> np.ndarray:
    """
    Generate a realistic-looking grayscale lunar surface texture.
    Uses a blend of Perlin-like multi-octave noise + synthetic crater stamps.
    """
    rng = np.random.RandomState(seed)
    img = np.zeros((size, size), dtype=np.float64)

    # Multi-octave Gaussian noise
    for octave in range(6):
        scale = 2 ** octave
        freq = size // scale
        if freq < 2:
            break
        noise = rng.randn(freq, freq)
        upscaled = cv2.resize(noise, (size, size), interpolation=cv2.INTER_CUBIC)
        img += upscaled * (0.5 ** octave)

    # Normalize to 0-255
    img -= img.min()
    img = img / (img.max() + 1e-8) * 200 + 30

    # Stamp synthetic craters
    n_craters = rng.randint(15, 35)
    for _ in range(n_craters):
        cx, cy = rng.randint(50, size - 50, size=2)
        radius = rng.randint(8, min(80, size // 8))
        # Dark interior + bright rim
        y, x = np.ogrid[-cy:size - cy, -cx:size - cx]
        dist = np.sqrt(x * x + y * y).astype(np.float64)
        # Crater profile
        rim = np.clip(1.0 - np.abs(dist - radius) / (radius * 0.3), 0, 1) * 60
        interior = np.clip(1.0 - dist / radius, 0, 1) * 40
        shadow_angle = rng.uniform(0, 2 * np.pi)
        shadow = np.clip(
            (x * np.cos(shadow_angle) + y * np.sin(shadow_angle)) / (radius + 1e-8),
            -1, 1
        ) * 25 * np.clip(1.0 - dist / radius, 0, 1)
        img += rim - interior + shadow

    return np.clip(img, 0, 255).astype(np.uint8)


def _apply_transform(img: np.ndarray, rotation_deg: float, scale: float,
                      tx: float = 0, ty: float = 0) -> np.ndarray:
    """Apply a known affine transformation."""
    h, w = img.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, rotation_deg, scale)
    M[0, 2] += tx
    M[1, 2] += ty
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)


def _simulate_illumination_shift(img: np.ndarray, direction: str = "east") -> np.ndarray:
    """Simulate opposing illumination by directional gradient emphasis."""
    h, w = img.shape[:2]
    if direction == "east":
        kx, ky = np.array([[0, 0, 0], [-1, 0, 1], [0, 0, 0]], dtype=np.float64), None
    else:  # west
        kx, ky = np.array([[0, 0, 0], [1, 0, -1], [0, 0, 0]], dtype=np.float64), None

    gradient = cv2.filter2D(img.astype(np.float64), -1, kx)
    result = img.astype(np.float64) + gradient * 0.6
    return np.clip(result, 0, 255).astype(np.uint8)


def _simulate_ir_band(img: np.ndarray) -> np.ndarray:
    """Simulate an infrared mineral absorption signature (non-linear intensity)."""
    # Invert, gamma-correct, heavy blur to simulate 80m GSD
    inv = 255 - img.astype(np.float64)
    gamma = np.power(inv / 255.0, 1.8) * 255
    blurred = cv2.GaussianBlur(gamma, (31, 31), 12)
    noisy = blurred + np.random.randn(*blurred.shape) * 8
    return np.clip(noisy, 0, 255).astype(np.uint8)


def generate_all_pairs():
    """Generate all benchmark pairs and save manifest."""
    print("=" * 60)
    print("SELORA Demo Dataset Generator")
    print("=" * 60)

    base = _make_lunar_texture(1024, seed=2026)
    manifest = {"pairs": [], "generated_by": "SELORA setup_demo_dataset.py"}

    # ── Pair 1: OHRC <-> LRO NAC (cross-mission, similar scale) ──
    print("\n[1/5] OHRC <-> LRO NAC (cross-mission registration)...")
    ohrc_src = base[100:612, 100:612].copy()  # 512x512 crop
    lro_ref = _apply_transform(base[80:632, 80:632], rotation_deg=8.5, scale=0.92, tx=5, ty=-3)
    lro_ref = cv2.convertScaleAbs(lro_ref, alpha=1.15, beta=-20)  # different sensor response
    cv2.imwrite(str(DATA_RAW / "demo_ohrc_lro_source.png"), ohrc_src)
    cv2.imwrite(str(DATA_RAW / "demo_ohrc_lro_reference.png"), lro_ref)
    manifest["pairs"].append({
        "name": "OHRC <-> LRO NAC",
        "source": "demo_ohrc_lro_source.png",
        "reference": "demo_ohrc_lro_reference.png",
        "source_sensor": "OHRC",
        "reference_sensor": "LRO_NAC",
        "ground_truth": {"rotation_deg": 8.5, "scale": 0.92, "tx": 5, "ty": -3},
        "difficulty": "medium",
        "description": "Cross-mission registration: Chandrayaan-2 OHRC vs NASA LRO Narrow Angle Camera"
    })

    # ── Pair 2: OHRC <-> TMC-2 (20x scale gap) ──
    print("[2/5] OHRC <-> TMC-2 (20x scale gap)...")
    ohrc_full = base.copy()
    tmc2_ref = cv2.resize(base, (base.shape[1] // 4, base.shape[0] // 4), interpolation=cv2.INTER_AREA)
    tmc2_ref = _apply_transform(tmc2_ref, rotation_deg=3.2, scale=1.0)
    tmc2_ref = cv2.GaussianBlur(tmc2_ref, (5, 5), 2)  # blur to simulate lower resolution
    cv2.imwrite(str(DATA_RAW / "demo_ohrc_tmc2_source.png"), ohrc_full)
    cv2.imwrite(str(DATA_RAW / "demo_ohrc_tmc2_reference.png"), tmc2_ref)
    manifest["pairs"].append({
        "name": "OHRC <-> TMC-2",
        "source": "demo_ohrc_tmc2_source.png",
        "reference": "demo_ohrc_tmc2_reference.png",
        "source_sensor": "OHRC",
        "reference_sensor": "TMC2",
        "ground_truth": {"rotation_deg": 3.2, "scale": 0.25},
        "difficulty": "hard",
        "description": "Cross-resolution: 0.25m OHRC vs 5m TMC-2 (20x GSD ratio)"
    })

    # ── Pair 3: OHRC <-> IIRS (320x scale gap, IR modality) ──
    print("[3/5] OHRC <-> IIRS (320x scale + IR modality)...")
    iirs_ref = cv2.resize(base, (base.shape[1] // 16, base.shape[0] // 16), interpolation=cv2.INTER_AREA)
    iirs_ref = _simulate_ir_band(iirs_ref)
    cv2.imwrite(str(DATA_RAW / "demo_ohrc_iirs_source.png"), ohrc_full)
    cv2.imwrite(str(DATA_RAW / "demo_ohrc_iirs_reference.png"), iirs_ref)
    manifest["pairs"].append({
        "name": "OHRC <-> IIRS",
        "source": "demo_ohrc_iirs_source.png",
        "reference": "demo_ohrc_iirs_reference.png",
        "source_sensor": "OHRC",
        "reference_sensor": "IIRS",
        "ground_truth": {"rotation_deg": 0, "scale": 0.0625},
        "difficulty": "extreme",
        "description": "Cross-modal: 0.25m panchromatic OHRC vs 80m hyperspectral IIRS (320x GSD ratio)"
    })

    # ── Pair 4: Illumination Shift (opposing shadows) ──
    print("[4/5] Illumination shift (opposing shadows)...")
    illum_east = _simulate_illumination_shift(base[50:562, 50:562], "east")
    illum_west = _simulate_illumination_shift(base[50:562, 50:562], "west")
    illum_west = _apply_transform(illum_west, rotation_deg=2.0, scale=1.0, tx=3, ty=-2)
    cv2.imwrite(str(DATA_RAW / "demo_illumination_east.png"), illum_east)
    cv2.imwrite(str(DATA_RAW / "demo_illumination_west.png"), illum_west)
    manifest["pairs"].append({
        "name": "Illumination Shift",
        "source": "demo_illumination_east.png",
        "reference": "demo_illumination_west.png",
        "source_sensor": "OHRC",
        "reference_sensor": "OHRC",
        "ground_truth": {"rotation_deg": 2.0, "scale": 1.0, "tx": 3, "ty": -2},
        "difficulty": "hard",
        "description": "Same-sensor opposing illumination: East vs West solar azimuth"
    })

    # ── Pair 5: Easy same-sensor (validation baseline) ──
    print("[5/5] Same-sensor easy pair (validation baseline)...")
    easy_src = base[100:612, 100:612].copy()
    easy_ref = _apply_transform(base[100:612, 100:612], rotation_deg=1.5, scale=1.02, tx=2, ty=1)
    cv2.imwrite(str(DATA_RAW / "demo_easy_source.png"), easy_src)
    cv2.imwrite(str(DATA_RAW / "demo_easy_reference.png"), easy_ref)
    manifest["pairs"].append({
        "name": "Same-Sensor Easy",
        "source": "demo_easy_source.png",
        "reference": "demo_easy_reference.png",
        "source_sensor": "OHRC",
        "reference_sensor": "OHRC",
        "ground_truth": {"rotation_deg": 1.5, "scale": 1.02, "tx": 2, "ty": 1},
        "difficulty": "easy",
        "description": "Same-sensor baseline: small rotation + translation for regression testing"
    })

    # ── Save manifest ──
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"[OK] Generated {len(manifest['pairs'])} benchmark pairs in {DATA_RAW}")
    print(f"[OK] Manifest saved to {MANIFEST_PATH}")
    print(f"{'=' * 60}")

    # Summary table
    print(f"\n{'Name':<30} {'Difficulty':<12} {'Sensors':<20} {'Files'}")
    print("-" * 90)
    for p in manifest["pairs"]:
        print(f"{p['name']:<30} {p['difficulty']:<12} {p['source_sensor']}->{p['reference_sensor']:<13} {p['source']}, {p['reference']}")

    return manifest


if __name__ == "__main__":
    generate_all_pairs()
