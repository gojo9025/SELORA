"""
SELORA Complete Source Code Markdown Generator
Compiles all 86+ source code, configuration, test, and documentation files
into a single, clean, hyperlinked Markdown file for ChatGPT or offline audit.
"""

import os
import sys

# Structured categories and descriptions for all files
CATEGORY_RULES = [
    ("SELORA_PROJECT_FULL_DETAILS.txt", "Comprehensive Project Architecture & 11-Stage Pipeline Audit", "1. Architecture & Documentation"),
    ("README.md", "Repository Documentation & Quickstart Guide", "1. Architecture & Documentation"),
    ("frontend/README.md", "Frontend Overview & Setup Instructions", "1. Architecture & Documentation"),
    ("frontend/AGENTS.md", "Agent Instructions for Frontend", "1. Architecture & Documentation"),
    ("frontend/CLAUDE.md", "Claude Architecture Guide for Frontend", "1. Architecture & Documentation"),

    ("docker-compose.yml", "Multi-container Docker Compose Definition", "2. Infrastructure & Deployment"),
    ("docker/Dockerfile.backend", "FastAPI Backend Dockerfile", "2. Infrastructure & Deployment"),
    ("docker/Dockerfile.frontend", "Next.js Frontend Dockerfile", "2. Infrastructure & Deployment"),
    ("start.bat", "Windows Quick-Launch Script (Backend + Frontend)", "2. Infrastructure & Deployment"),
    ("main.py", "Unified App Server & Reverse Proxy (FastAPI + Static Frontend)", "2. Infrastructure & Deployment"),
    ("run.py", "FastAPI Application Launcher Driver", "2. Infrastructure & Deployment"),

    ("backend/requirements.txt", "Python Dependencies", "3. Backend Configuration & API Layer"),
    ("backend/config.py", "Backend Application Settings & Path Definitions", "3. Backend Configuration & API Layer"),
    ("backend/schemas.py", "Pydantic API Request/Response Data Contracts", "3. Backend Configuration & API Layer"),
    ("backend/main.py", "FastAPI Sub-App Initialization & CORS Middleware", "3. Backend Configuration & API Layer"),
    ("backend/__init__.py", "Backend Package Init", "3. Backend Configuration & API Layer"),
    ("backend/api/__init__.py", "Backend API Package Init", "3. Backend Configuration & API Layer"),
    ("backend/api/upload.py", "Image & GeoTIFF Ingestion Endpoints", "3. Backend Configuration & API Layer"),
    ("backend/api/registration.py", "Registration Execution & Polling Endpoints", "3. Backend Configuration & API Layer"),
    ("backend/api/benchmark.py", "Benchmarking Suite Endpoints & Method Configurations", "3. Backend Configuration & API Layer"),
    ("backend/api/evaluation.py", "Independent Metric Evaluation Endpoints", "3. Backend Configuration & API Layer"),

    ("backend/core/__init__.py", "Core Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/database.py", "SQLite Database & Job State Repository", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/pipeline.py", "Master Computer Vision Registration Pipeline (Stages 1–11)", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/sensors/__init__.py", "Sensors Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/sensors/profiles.py", "Lunar Sensor Optical Profiles & Registration Configurations", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/sensors/classifier.py", "Automated Sensor Modality Classifier", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/preprocessing/__init__.py", "Preprocessing Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/preprocessing/pipeline.py", "Adaptive Preprocessing Pipeline & Multi-Scale Pyramids", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/preprocessing/radiometric.py", "Radiometric Normalization & Wallis Filter", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/photoclinometry/__init__.py", "Photoclinometry Package Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/photoclinometry/shading.py", "Photometric Slope Inversion & Frankot-Chellappa Fourier Integrability", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/photoclinometry/metadata.py", "Solar Illumination Metadata Ingestion (PDS4, .lbl, .xml, .json)", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/features/__init__.py", "Features Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/features/extractors.py", "Classical Feature Extractors (SIFT, ORB, AKAZE)", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/features/learned.py", "Deep Learned Local Features (KeyNet + HardNet & LoFTR via Kornia)", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/matching/__init__.py", "Matching Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/matching/matcher.py", "Descriptor Matching with Cross-Check & Ratio Test", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/geometry/__init__.py", "Geometry Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/geometry/verification.py", "MAGSAC RANSAC Geometric Verification & Model Selection", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/registration/__init__.py", "Registration Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/registration/mutual_information.py", "Intensity-Based Mutual Information Direct Fallback", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/warping/__init__.py", "Warping Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/warping/warp.py", "High-Fidelity Perspective/Affine Image Warper", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/refinement/__init__.py", "Refinement Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/refinement/subpixel.py", "Fourier Phase Correlation Sub-Pixel Refinement", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/evaluation/__init__.py", "Evaluation Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/evaluation/metrics.py", "Photogrammetric Error Metrics (RMSE, SSIM, NCC, MI)", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/evaluation/validation.py", "Leave-K-Out Independent Cross-Validation Engine", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/visualization/__init__.py", "Visualization Module Init", "4. Backend Core Engine (11-Stage Pipeline)"),
    ("backend/core/visualization/visualizer.py", "Multi-Modal Diagnostic Visualizations & Checkerboards", "4. Backend Core Engine (11-Stage Pipeline)"),

    ("backend/datasets/__init__.py", "Datasets Module Init", "5. Datasets, Benchmarks & Test Suite"),
    ("backend/datasets/synthetic.py", "Synthetic Lunar Pair Generation Engine with Known Perturbations", "5. Datasets, Benchmarks & Test Suite"),
    ("backend/models/__init__.py", "Models Module Init", "5. Datasets, Benchmarks & Test Suite"),
    ("backend/tests/__init__.py", "Tests Module Init", "5. Datasets, Benchmarks & Test Suite"),
    ("backend/tests/test_pipeline.py", "Unit & Integration Tests for Core Pipeline Stages", "5. Datasets, Benchmarks & Test Suite"),
    ("backend/tests/test_advanced.py", "Advanced Mathematical, Validation & Edge Case Tests", "5. Datasets, Benchmarks & Test Suite"),
    ("backend/tests/test_photoclinometry.py", "Unit Tests for Stage 4c Photoclinometry & Metadata Parsing", "5. Datasets, Benchmarks & Test Suite"),
    ("data/benchmarks/ground_truth.json", "Lunar Benchmark Evaluation Dataset Registry", "5. Datasets, Benchmarks & Test Suite"),
    ("scripts/generate_demo_dataset.py", "Demo Lunar Dataset Synthesizer Script", "5. Datasets, Benchmarks & Test Suite"),
    ("scripts/test_e2e.py", "End-to-End Pipeline Smoke Test Script", "5. Datasets, Benchmarks & Test Suite"),

    ("frontend/package.json", "Frontend npm Package & Script Definitions", "6. Frontend Configuration & Library"),
    ("frontend/tsconfig.json", "TypeScript Compiler Configuration", "6. Frontend Configuration & Library"),
    ("frontend/next.config.ts", "Next.js App Router Configuration", "6. Frontend Configuration & Library"),
    ("frontend/postcss.config.mjs", "PostCSS & Tailwind Configuration", "6. Frontend Configuration & Library"),
    ("frontend/eslint.config.mjs", "ESLint Configuration", "6. Frontend Configuration & Library"),
    ("frontend/.env.local", "Frontend Environment Variables", "6. Frontend Configuration & Library"),
    ("frontend/.gitignore", "Frontend Git Ignore Rules", "6. Frontend Configuration & Library"),
    ("frontend/next-env.d.ts", "Next.js TypeScript Declaration Types", "6. Frontend Configuration & Library"),
    ("frontend/lib/types.ts", "Frontend TypeScript Data Contracts & Interfaces", "6. Frontend Configuration & Library"),
    ("frontend/lib/api.ts", "Frontend Axios/Fetch API Client", "6. Frontend Configuration & Library"),

    ("frontend/app/globals.css", "Global Dark-Space Theme, Glassmorphism & Cyberpunk Neon CSS", "7. Frontend UI & Pages"),
    ("frontend/app/layout.tsx", "Root HTML Layout & Font Providers", "7. Frontend UI & Pages"),
    ("frontend/app/page.tsx", "Landing Page: Hero, Feature Highlights & Mission Status", "7. Frontend UI & Pages"),
    ("frontend/app/workspace/page.tsx", "Workspace Page: Upload, Stage Configuration & Live Run", "7. Frontend UI & Pages"),
    ("frontend/app/benchmark/page.tsx", "Benchmark Page: Preset Selection & Algorithm Comparison", "7. Frontend UI & Pages"),
    ("frontend/app/benchmark/compare/page.tsx", "Comparative Matrix Runner: Live Multi-Preset Evaluation & Charts", "7. Frontend UI & Pages"),
    ("frontend/app/results/[id]/page.tsx", "Results Page Dynamic Route Server Component", "7. Frontend UI & Pages"),
    ("frontend/app/results/[id]/ResultsClient.tsx", "Interactive Telemetry Hub & Diagnostics Client Component", "7. Frontend UI & Pages"),

    ("frontend/components/three/MoonScene.tsx", "Three.js 3D Photorealistic Interactive Moon Canvas", "8. Frontend Components (Three.js 3D & UI)"),
    ("frontend/components/three/OrbitalRing.tsx", "Three.js Chandrayaan-2 Orbital Trajectory Ring", "8. Frontend Components (Three.js & UI)"),
    ("frontend/components/three/Starfield.tsx", "Three.js Dynamic Background Cosmic Starfield", "8. Frontend Components (Three.js & UI)"),
    ("frontend/components/ui/FloatingSpaceAssets.tsx", "Floating UI Elements & Orbital HUD Markers", "8. Frontend Components (Three.js & UI)"),
    ("frontend/components/ui/ImageSlider.tsx", "Interactive Split-Screen Before/After Swipe Slider", "8. Frontend Components (Three.js & UI)"),
    ("frontend/components/ui/LaunchAnimation.tsx", "Cyberpunk Mission Launch Sequence & Status Console", "8. Frontend Components (Three.js & UI)"),
    ("frontend/components/ui/TelemetryReport.tsx", "Detailed Telemetry Metrics Cards & Quality Gate Status", "8. Frontend Components (Three.js & UI)"),
]

def get_lang(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    base = os.path.basename(file_path).lower()
    if "dockerfile" in base:
        return "dockerfile"
    mapping = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".mjs": "javascript",
        ".json": "json",
        ".css": "css",
        ".html": "html",
        ".md": "markdown",
        ".txt": "text",
        ".bat": "batch",
        ".cmd": "batch",
        ".sh": "bash",
        ".yml": "yaml",
        ".yaml": "yaml",
    }
    return mapping.get(ext, "text")

def get_code_fence(content):
    max_ticks = 2
    cur_ticks = 0
    for ch in content:
        if ch == "`":
            cur_ticks += 1
            if cur_ticks > max_ticks:
                max_ticks = cur_ticks
        else:
            cur_ticks = 0
    return "`" * max(3, max_ticks + 1)

def slugify(text):
    return text.lower().replace("/", "-").replace("\\", "-").replace(".", "-").replace(" ", "-").replace("_", "-")

def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    out_path = os.path.join(root_dir, "SELORA_COMPLETE_SOURCE_CODE.md")

    # Discover any additional files not explicitly in CATEGORY_RULES
    known_paths = {rule[0].replace("\\", "/") for rule in CATEGORY_RULES}
    exclude_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", ".next", "out", ".pytest_cache", ".turbo", ".gemini"}
    exclude_files = {"package-lock.json", "selora.db", "SELORA_COMPLETE_SOURCE_CODE.md", "frontend/tsconfig.tsbuildinfo"}
    exclude_ext = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".ico", ".svg", ".gif", ".webp", ".bmp", ".mp4", ".avi", ".pdf", ".zip", ".tar", ".gz", ".npy", ".npz", ".pth", ".pt", ".onnx", ".bin"}

    all_items = list(CATEGORY_RULES)

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), root_dir).replace("\\", "/")
            if rel in exclude_files or rel.endswith(".tsbuildinfo"):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in exclude_ext:
                continue
            if rel not in known_paths:
                desc = f"Source/Config File: {rel}"
                cat = "9. Additional Project Assets & Scripts"
                all_items.append((rel, desc, cat))
                known_paths.add(rel)

    print(f"Compiling {len(all_items)} files into {out_path}...")

    total_bytes = 0
    total_lines = 0

    with open(out_path, "w", encoding="utf-8") as out:
        out.write("# SELORA: SENSOR-AWARE LUNAR IMAGE REGISTRATION & OPTICAL ALIGNMENT\n\n")
        out.write("> **INSTRUCTIONS FOR CHATGPT / AI ASSISTANTS**:\n")
        out.write("> - **Repository**: SELORA (Chandrayaan-2 Lunar Optical Alignment Engine)\n")
        out.write("> - **Problem Statement**: ISRO Smart India Hackathon (SIH) 2026 — Problem Statement 26166\n")
        out.write("> - **Purpose**: This single Markdown file contains the complete, unredacted source code, configurations, schemas, and architecture documentation for the entire project.\n")
        out.write("> - **How to use**: You can analyze algorithms across modules, explain the 11-stage photogrammetric registration pipeline, trace API workflows, explain frontend UI and Three.js 3D visualizations, debug issues, or provide architectural reviews.\n\n")

        out.write("## Mission Overview & Engineering Summary\n\n")
        out.write("SELORA solves the extreme challenge of registering multi-modal, heterogeneous lunar orbital imagery from India's **Chandrayaan-2** spacecraft. The payload instruments have vastly different spatial resolutions, spectral bands, and viewing angles:\n")
        out.write("- **OHRC (Orbiter High Resolution Camera)**: 0.25 m/pixel panchromatic (highest resolution lunar camera in orbit).\n")
        out.write("- **TMC-2 (Terrain Mapping Camera-2)**: 5.0 m/pixel stereo panchromatic, broad topographic mapping.\n")
        out.write("- **IIRS (Imaging Infrared Spectrometer)**: 80.0 m/pixel, 256 spectral bands (0.8–5.0 μm).\n")
        out.write("- **Core Algorithmic Innovations**:\n")
        out.write("  1. **Sensor-Aware Optical Profiling**: Automatic sensor classification, resolution ratio calculation, and adaptive Gaussian pyramid equalization.\n")
        out.write("  2. **Radiometric Normalization**: Wallis adaptive contrast enhancement + CDF histogram matching to overcome radical shadow changes across different lunar orbits.\n")
        out.write("  3. **Stage 4c Photoclinometry (Shape-from-Shading)**: Physics-based lunar reflectance inversion (McEwen Lunar-Lambert) + Frankot-Chellappa Fourier integrability projection (O(N log N)) to recover illumination-invariant relative topographic relief from directional shading.\n")
        out.write("  4. **Pluggable Feature Extraction**: SIFT, ORB, AKAZE, Deep Neural features (KeyNet + HardNet via PyTorch Kornia), and LoFTR learned transformer matcher.\n")
        out.write("  5. **USAC-MAGSAC Verification**: Dynamic model selection between Similarity, Affine, and Homography with spatial coverage scoring.\n")
        out.write("  6. **Direct Intensity Fallback**: Powell-optimized Mutual Information registration when feature detectors fail on low-contrast lunar regolith.\n")
        out.write("  7. **Fourier Phase Correlation Sub-Pixel Refinement**: Down to 0.1 pixel precision.\n")
        out.write("  8. **Leave-K-Out Independent Cross-Validation**: Non-circular CV-RMSE, SSIM, NCC, and Mutual Information quality metrics.\n\n")

        out.write("## 11-Stage Pipeline Architecture (with Stage 4c Photoclinometry)\n\n")
        out.write("```\n")
        out.write("+---------------------------------------------------------------------------------------------------+\n")
        out.write("|                           SELORA 11-STAGE REGISTRATION PIPELINE                                   |\n")
        out.write("+---------------------------------------------------------------------------------------------------+\n")
        out.write("  [Stage 1: Ingestion & GeoTIFF Handling]              -> Multi-spectral scaling + PDS4 solar angles\n")
        out.write("  [Stage 2: Sensor Classification & Optical Profile]   -> Metadata parser + visual aspect heuristic\n")
        out.write("  [Stage 3: Adaptive Preprocessing & Scale Pyramids]   -> Scale ratio downsampling / equalization\n")
        out.write("  [Stage 4: Radiometric Normalization]                 -> Wallis filter + CDF histogram matching\n")
        out.write("  [Stage 4c: Photoclinometry Relief Transform]         -> Shape-from-Shading (Lunar-Lambert / Frankot)\n")
        out.write("  [Stage 5: Pluggable Feature Extraction]              -> SIFT, ORB, AKAZE, KeyNet+HardNet, LoFTR\n")
        out.write("  [Stage 6: Descriptor Matching]                       -> Mutual Nearest Neighbor + Lowe's Ratio\n")
        out.write("  [Stage 7: Geometric Verification & Model Selection]  -> USAC-MAGSAC (Similarity / Affine / Homography)\n")
        out.write("  [Stage 8: Direct Mutual Information Fallback]        -> Powell optimization if inlier count < 15\n")
        out.write("  [Stage 9: High-Fidelity Perspective Warping]         -> Sub-pixel coordinate re-mapping\n")
        out.write("  [Stage 10: Sub-Pixel Refinement]                     -> Fourier Phase Correlation (0.1 px precision)\n")
        out.write("  [Stage 11: Non-Circular Independent Validation]      -> Leave-K-Out CV-RMSE, SSIM, NCC, MI\n")
        out.write("  ---------------------------------------------------------------------------------------------------\n")
        out.write("  Telemetry Outputs: Overlay Blend, Split Slider, Checkered Mosaic, Vector Error Field, JSON Metrics\n")
        out.write("```\n\n")

        out.write("## Table of Contents & File Index\n\n")
        out.write(f"Total Files: **{len(all_items)} files**.\n\n")

        current_category = None
        for idx, (fpath, fdesc, fcat) in enumerate(all_items, 1):
            if fcat != current_category:
                current_category = fcat
                out.write(f"\n### {current_category}\n\n")

            anchor = slugify(f"file-{idx}-{fpath}")
            out.write(f"- [{idx}. `{fpath}`](#{anchor}) — *{fdesc}*\n")

        out.write("\n---\n\n")

        # Code Contents
        for idx, (fpath, fdesc, fcat) in enumerate(all_items, 1):
            anchor = slugify(f"file-{idx}-{fpath}")
            full_p = os.path.join(root_dir, fpath)

            if not os.path.exists(full_p):
                print(f"Warning: file not found {full_p}")
                continue

            size = os.path.getsize(full_p)
            total_bytes += size

            with open(full_p, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()

            lines = len(content.splitlines())
            total_lines += lines
            lang = get_lang(fpath)
            fence = get_code_fence(content)

            out.write(f'<a id="{anchor}"></a>\n')
            out.write(f"## File #{idx}: `{fpath}`\n\n")
            out.write(f"- **Category**: {fcat}\n")
            out.write(f"- **Description**: {fdesc}\n")
            out.write(f"- **Path**: `{fpath}`\n")
            out.write(f"- **Size**: {size:,} bytes | **Lines**: {lines:,} lines | **Language**: `{lang}`\n\n")

            if size == 0:
                out.write(f"{fence}{lang}\n# (Empty Python __init__.py package marker file)\n{fence}\n\n")
            else:
                out.write(f"{fence}{lang}\n")
                out.write(content)
                if not content.endswith("\n"):
                    out.write("\n")
                out.write(f"{fence}\n\n")

            out.write("---\n\n")

    print(f"Done! Successfully wrote {total_bytes:,} bytes across {total_lines:,} lines into {out_path}.")

if __name__ == "__main__":
    main()
