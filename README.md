# SELORA

**Sensor-Aware Lunar Image Registration & Optical Alignment**  
SIH Problem Statement 26166 · Space Technology / Computer Vision / Lunar Science

---

SELORA is a full-stack AI-assisted registration platform for Chandrayaan-2 lunar imagery.  
It dynamically adapts its pipeline to differences in sensor modality, scale, and illumination between OHRC, TMC-2, IIRS, and reference payloads like LRO NAC and SELENE (Kaguya) — producing geometrically verified, aligned imagery with quantitative confidence metrics.

## Features

- **Sensor-Aware Pipeline**: Per-sensor-pair preprocessing and feature strategy (OHRC↔TMC-2↔IIRS)
- **Multi-Scale Registration**: Gaussian image pyramids for cross-resolution matching
- **Pluggable Feature Engine**: SIFT, ORB, AKAZE (SuperPoint/LoFTR ready)
- **Multi-Model Geometry**: Similarity / Affine / Homography with automatic selection
- **USAC-MAGSAC RANSAC**: Robust outlier rejection
- **Uniform Distribution**: Spatial Grid Bucketing (ANMS) to prevent keypoint clustering
- **Quantitative Confidence**: RMSE, inlier ratio, spatial coverage, confidence score
- **Interactive UI**: Overlay slider, match visualization, transformation matrix display
- **Exporting Capabilities**: Export Registered Images (GeoTIFF) and Match Points (CSV)
- **Benchmark Module**: Side-by-side comparison of all methods
- **Explainability**: "Why did SELORA trust this registration?"

---

## Quick Start

### Option 1: Single Unified Application (Easiest) 🚀

Run the entire application (Next.js Interactive UI + FastAPI Vision Engine) in a **single unified server** on port 8000:

```bash
# Directly from project root:
python run.py
# or
python -m uvicorn main:app --reload --port 8000
```

- **Full Application UI:** http://localhost:8000
- **Interactive Registration Workspace:** http://localhost:8000/workspace
- **Automated Benchmark Suite:** http://localhost:8000/benchmark
- **Swagger API Docs:** http://localhost:8000/docs

---

### Option 2: Docker

```bash
docker-compose up --build
```

### Option 3: Separate Dev Servers (Frontend + Backend)

**Backend**
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Generate Demo Images

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # or source .venv/bin/activate
pip install -r requirements.txt
cd ..
python scripts/generate_demo_dataset.py
```

This creates synthetic lunar image pairs in `data/raw/`:

| File | Description |
|------|-------------|
| `demo_same_source.png` | Same-sensor pair (source) |
| `demo_same_reference.png` | Same-sensor pair (reference) |
| `demo_ohrc_source.png` | OHRC simulation (source) |
| `demo_tmc2_reference.png` | TMC-2 simulation (reference) |
| `demo_hard_source.png` | Challenging: 15° rotation + illumination |
| `demo_hard_reference.png` | Reference for hard pair |

### Generate Curated Real Benchmark Pair

To generate a curated real benchmark pair (Chandrayaan-2 OHRC vs LRO NAC) for live demonstrations:

```bash
cd data/raw
python generate_benchmark.py
```
This generates `OHRC_benchmark.png` and `LRO_NAC_benchmark.png`.

---

## Run Tests

```bash
cd backend
.venv\Scripts\activate
pytest tests/ -v
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/images/upload` | POST | Upload an image |
| `/api/images/{id}` | GET | Get image metadata |
| `/api/register` | POST | Run registration pipeline |
| `/api/registration/{id}` | GET | Get full result |
| `/api/registration/{id}/metrics` | GET | Get metrics |
| `/api/registration/{id}/transform` | GET | Get transformation matrix |
| `/api/registration/{id}/visualizations` | GET | Get image URLs |
| `/api/registration/{id}/download/{artifact}` | GET | Download artifact |
| `/api/benchmark/run` | POST | Run method comparison |
| `/api/benchmark/{id}` | GET | Get benchmark results |
| `/api/health` | GET | Health check |

Interactive docs: http://localhost:8000/docs

---

## Registration Modes

| Mode | Features | Matcher | RANSAC | Target Time |
|------|----------|---------|--------|-------------|
| FAST | ORB | BFMatcher | Standard | < 5s |
| ROBUST | SIFT | FLANN | USAC_MAGSAC | < 15s |
| RESEARCH | SIFT + multi-scale | FLANN | USAC_MAGSAC | < 60s |
| AUTO | Sensor-determined | — | — | — |

---

## Sensor Profiles

| Pair | GSD Difference | Strategy |
|------|---------------|----------|
| OHRC → TMC-2 | 25cm vs 5m | Gradient + multi-scale SIFT + 4-level pyramid |
| OHRC → IIRS | 25cm vs 80m | Strong gradient + lower ratio threshold |
| TMC-2 → IIRS | 5m vs 80m | Gradient + 3-level pyramid |
| Reference → OHRC | High-res to High-res (LRO NAC) | Standard SIFT |
| Same sensor | — | Standard SIFT, no gradient needed |

---

## Directory Structure

```
selora/
├── frontend/          Next.js frontend
├── backend/
│   ├── main.py        FastAPI entry
│   ├── config.py      Settings
│   ├── schemas.py     Pydantic models
│   ├── api/           API routes
│   └── core/
│       ├── preprocessing/  Normalize, CLAHE, pyramid
│       ├── sensors/        Sensor profiles & registry
│       ├── features/       SIFT, ORB, AKAZE extractors
│       ├── matching/       BFMatcher, FLANN, ratio test
│       ├── geometry/       RANSAC, model comparison
│       ├── warping/        warpPerspective
│       ├── evaluation/     RMSE, coverage, confidence
│       └── visualization/  Match viz, diff map, overlay
├── data/              Image storage
├── scripts/           Dataset generators
├── docker/            Dockerfiles
└── docker-compose.yml One-command startup
```

---

## Confidence Formula

```
confidence = 0.35 × clamp(inlier_ratio / 0.8)
           + 0.25 × clamp(1 - rmse / 20)
           + 0.25 × clamp(spatial_coverage / 0.8)
           + 0.15 × clamp(inlier_count / 500)
```

This is an **engineering quality score**, not a calibrated statistical probability.

---

## Quality Gates

| Gate | Threshold | Action |
|------|-----------|--------|
| Total matches | < 20 | FAIL |
| RANSAC inliers | < 10 | FAIL |
| Inlier ratio | < 15% | FAIL |
| Inlier ratio | < 30% | WARNING |
| Reprojection RMSE | > 20px | FAIL |
| Spatial coverage | < 15% | WARNING |

---

## SIH 2026 — Problem Statement 26166

Built for the Smart India Hackathon 2026 under the Space Technology domain.  
Addresses multi-modal, sun-angle and scale-invariant image registration for Chandrayaan-2 OHRC, TMC-2, and IIRS imagery.
