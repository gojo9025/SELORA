#!/usr/bin/env python3
"""
SELORA Demo Dataset Generator
Creates synthetic lunar image pairs for demonstration and testing.
Run from the project root:
    python scripts/generate_demo_dataset.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import cv2
import numpy as np
from pathlib import Path
from datasets.synthetic import create_synthetic_pair, create_cross_modal_pair

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save(img, name):
    path = OUTPUT_DIR / name
    cv2.imwrite(str(path), img)
    print(f"  Saved: {path} ({img.shape[1]}x{img.shape[0]})")


print("SELORA Demo Dataset Generator")
print("=" * 50)

# ── Pair 1: Simple rotation + translation (simulates same sensor) ──────────
print("\n[1] Generating: Same-sensor pair (5° rotation, translation)")
p1 = create_synthetic_pair(rotation_deg=5.0, scale=0.98, tx=20.0, ty=-12.0, noise_std=4.0, size=512)
save(p1.source, "demo_same_source.png")
save(p1.reference, "demo_same_reference.png")

# ── Pair 2: Cross-modal (simulates OHRC → TMC-2) ────────────────────────────
print("\n[2] Generating: Cross-modal pair (OHRC->TMC2 simulation, 0.5x resolution)")
p2 = create_cross_modal_pair(resolution_ratio=0.5, rotation_deg=3.0, tx=10.0, ty=-5.0, size=512)
save(p2.source, "demo_ohrc_source.png")
save(p2.reference, "demo_tmc2_reference.png")

# ── Pair 3: Large rotation + illumination (harder test) ─────────────────────
print("\n[3] Generating: Challenging pair (15° rotation, illumination shift)")
p3 = create_synthetic_pair(
    rotation_deg=15.0, scale=0.92, tx=30.0, ty=-20.0,
    noise_std=8.0, brightness_shift=40.0, size=512,
)
save(p3.source, "demo_hard_source.png")
save(p3.reference, "demo_hard_reference.png")

# ── Pair 4: Large 1024×1024 pair ────────────────────────────────────────────
print("\n[4] Generating: Large 1024×1024 pair")
p4 = create_synthetic_pair(rotation_deg=8.0, scale=0.96, tx=40.0, ty=15.0, size=1024, seed=99)
save(p4.source, "demo_large_source.png")
save(p4.reference, "demo_large_reference.png")

print("\n✓ Demo dataset generated successfully")
print(f"  Location: {OUTPUT_DIR}")
print("\nUpload these files in the SELORA workspace:")
print("  Source:    demo_ohrc_source.png  (sensor: OHRC)")
print("  Reference: demo_tmc2_reference.png  (sensor: TMC2)")
print("  Mode:      AUTO or ROBUST")

# ── Save ground truth metadata ───────────────────────────────────────────────
import json
gt = {
    "pairs": [
        {
            "source": "demo_same_source.png",
            "reference": "demo_same_reference.png",
            "description": "Same-sensor, 5° rotation",
            "ground_truth": p1.transform_params,
        },
        {
            "source": "demo_ohrc_source.png",
            "reference": "demo_tmc2_reference.png",
            "description": "Cross-modal OHRC→TMC2 simulation",
            "ground_truth": p2.transform_params,
        },
        {
            "source": "demo_hard_source.png",
            "reference": "demo_hard_reference.png",
            "description": "Challenging: 15° rotation + illumination shift",
            "ground_truth": p3.transform_params,
        },
    ]
}
gt_path = Path(__file__).parent.parent / "data" / "benchmarks" / "ground_truth.json"
gt_path.parent.mkdir(parents=True, exist_ok=True)
gt_path.write_text(json.dumps(gt, indent=2))
print(f"\n  Ground truth metadata: {gt_path}")
