# SELORA — TECHNOLOGY STACK

## 1. Executive Summary
The SELORA project employs a modern, decoupled client-server architecture designed for high-performance lunar image registration. It utilizes a Next.js (React) frontend for interactive visualizations and 3D rendering, backed by a FastAPI Python server that handles heavy computer vision workloads, numerical computing, and deep-learning-based feature extraction. Local SQLite handles metadata storage while raw and processed images are managed via the local file system. The entire application is containerized for consistent deployment using Docker and Docker Compose.

## 2. Programming Languages

| Language | Version | Usage | Evidence |
|---|---|---|---|
| Python | 3.x | Backend API, image registration pipeline, numerical computation, and machine learning models. | `backend/main.py`, `backend/core/pipeline.py` |
| TypeScript | 5.x | Frontend application logic, React components, and type definitions. | `frontend/tsconfig.json`, `frontend/package.json` |
| JavaScript | ES6+ | Frontend configuration files (Tailwind, ESLint). | `frontend/eslint.config.mjs`, `frontend/postcss.config.mjs` |
| HTML/CSS | 5 / 3 | UI markup and styling (via Tailwind CSS). | Implied by Next.js and `tailwindcss` in `frontend/package.json` |

## 3. Frontend
YES, SELORA has a dedicated frontend framework.

- **Framework:** Next.js (16.3.3)
- **Language:** TypeScript
- **UI libraries:** `lucide-react`, `framer-motion`, `react-compare-slider`, `recharts`, `@react-three/drei`, `@react-three/fiber`, `three`
- **Styling technology:** Tailwind CSS (v4)
- **Build tool:** Next.js internal builder (Webpack/Turbopack)
- **Major frontend dependencies:** `react` (19.2.8), `framer-motion` (13.2.0), `html2canvas`, `jspdf`, `three`
- **Entry points:** `frontend/package.json`, `frontend/app` directory

## 4. Backend
YES, SELORA has a dedicated backend/API server.

- **Backend framework:** FastAPI
- **Programming language:** Python
- **API framework:** FastAPI
- **Server/runtime:** Uvicorn (`uvicorn[standard]`)
- **API endpoints:** Mounted in `backend/main.py` (`/api/images`, `/api`, `/api/benchmark`)
- **Middleware:** CORS Middleware (`fastapi.middleware.cors.CORSMiddleware`)
- **Major backend dependencies:** `fastapi`, `pydantic`, `loguru`, `python-multipart`, `numpy`, `opencv-python-headless`
- **Entry point:** `backend/main.py`

## 5. Database & Storage

- **Name:** SQLite
- **Type:** Relational Database
- **Purpose:** Stores registration history, metadata, metrics, and JSON data.
- **Evidence:** `selora.db` file in the project root and `backend/core/database.py`.

- **Name:** Local File System
- **Type:** File Storage
- **Purpose:** Stores raw uploaded images, processed images, visualizations, and results.
- **Evidence:** Managed via configurations in `backend/config.py` (`UPLOAD_DIR`, `PROCESSED_DIR`, etc.) and mapped via Docker volumes (`./data:/app/data`).

## 6. Computer Vision / Image Processing

| Library | Version | Actual usage | Relevant files |
|---|---|---|---|
| OpenCV (`opencv-python-headless`) | Latest | Core image I/O, transformation, keypoint extraction (SIFT, ORB, AKAZE), RANSAC geometry estimation. | `backend/core/features/extractors.py`, `backend/core/geometry/verification.py` |
| scikit-image | Latest | Advanced image processing utilities (likely used in metrics/validation). | `backend/requirements.txt` |
| Pillow | Latest | Image decoding and manipulation. | `backend/requirements.txt` |
| rasterio | Optional | Used as a fallback for loading GeoTIFF formats. | `backend/core/pipeline.py` (Lines 71-78) |

## 7. Scientific / Numerical Computing
- **NumPy:** Used heavily for matrix operations, tensor manipulation, and 2D Fourier transforms (FFT).
- **SciPy:** Used for optimization techniques, specifically Nelder-Mead in Mutual Information registration.
Evidence: `backend/requirements.txt`, `backend/core/photoclinometry/shading.py` (`np.fft`), `backend/core/registration/mutual_information.py` (`scipy.optimize.minimize`).

## 8. Feature Detection & Image Registration

| Algorithm | Library/API | Purpose | Actual implementation file |
|---|---|---|---|
| SIFT | OpenCV (`cv2.SIFT_create`) | Baseline cross-modal scale-invariant feature extraction. | `backend/core/features/extractors.py` |
| ORB | OpenCV (`cv2.ORB_create`) | Fast, binary feature extraction for real-time applications. | `backend/core/features/extractors.py` |
| AKAZE | OpenCV (`cv2.AKAZE_create`) | Robust binary feature extraction. | `backend/core/features/extractors.py` |
| Mutual Information | SciPy Optimization | Fallback cross-modal intensity-based registration. | `backend/core/registration/mutual_information.py` |
| USAC-MAGSAC | OpenCV (`cv2.findHomography`) | Robust outlier rejection and homography fitting. | `backend/core/geometry/verification.py` |
| Photoclinometry | Custom / NumPy (Frankot-Chellappa) | Shape-from-shading illumination-invariant relief estimation. | `backend/core/photoclinometry/shading.py` |

## 9. Machine Learning / AI
YES, SELORA uses Machine Learning for feature extraction and matching.

- **PyTorch (`torch`):** Core deep learning tensor execution framework.
- **Kornia:** Deep feature extraction using KeyNet + HardNet, and neural matching using LightGlue and LoFTR.
- **Evidence:** `backend/core/features/learned.py` imports `torch` and `kornia.feature`.

## 10. Visualization & Reporting
- **recharts:** Interactive charting in the React frontend.
- **react-compare-slider:** Interactive before/after image comparison in the frontend.
- **three / @react-three/fiber:** 3D visualization components on the frontend.
- **html2canvas & jspdf:** Generating downloadable PDF reports on the frontend.
- **OpenCV:** Generating difference maps, error heatmaps, and inlier visualizations on the backend (`backend/core/visualization/visualizer.py`).
Evidence: `frontend/package.json` and `backend/core/visualization/visualizer.py`.

## 11. Development Tools
- **Docker / Docker Compose:** Container orchestration (`docker-compose.yml`).
- **pytest:** Backend testing framework (`backend/requirements.txt`).
- **ESLint:** Frontend linting (`frontend/eslint.config.mjs`).
- **Git:** Version control (`.git` directory).

## 12. Containerization
DOCKER IS ACTUALLY USED.
- **Evidence:** `docker-compose.yml` configures `backend` and `frontend` services pointing to `docker/Dockerfile.backend` and `docker/Dockerfile.frontend`.

## 13. Deployment & Infrastructure
LOCAL DEVELOPMENT / EXECUTION (using Docker).
- **Evidence:** `docker-compose.yml` binds to localhost ports (8000, 3000) and mounts local volumes (`./data`). No explicit cloud deployment configuration (AWS, GCP, etc.) was found in the repository root.

## 14. Dependency Summary

| Technology | Category | Version | Purpose | Evidence |
|---|---|---|---|---|
| Next.js | Frontend | 16.3.3 | React framework. | `frontend/package.json` |
| Tailwind CSS | Frontend | ^4 | Styling. | `frontend/package.json` |
| Three.js | Frontend | ^0.185.1 | 3D visual rendering. | `frontend/package.json` |
| FastAPI | Backend | Latest | Python API server. | `backend/requirements.txt` |
| OpenCV Headless | Backend | Latest | Image processing & CV algorithms. | `backend/requirements.txt` |
| PyTorch / Kornia | Backend | Latest | Neural feature matching (LightGlue, LoFTR). | `backend/requirements.txt`, `learned.py` |
| SQLite | Database | Native | Relational metadata storage. | `backend/core/database.py` |

---

## 15. Final PPT-Ready Technology Stack

### PROGRAMMING
Python • TypeScript

### FRONTEND
Next.js (React) • Tailwind CSS • Three.js

### BACKEND & DATABASE
FastAPI • SQLite

### COMPUTER VISION
OpenCV • scikit-image • Pillow

### NUMERICAL & SCIENTIFIC
NumPy • SciPy

### ROBUST REGISTRATION & AI
SIFT / ORB / AKAZE • USAC-MAGSAC • Kornia (LightGlue / LoFTR) • PyTorch

### DEPLOYMENT & TOOLS
Docker • Docker Compose • Git

---

## 16. Evidence & Verification

- **Python & FastAPI:** Verified in `backend/main.py` where the API is instantiated (`app = FastAPI(...)`).
- **TypeScript & Next.js:** Verified in `frontend/package.json` and `frontend/tsconfig.json`. Next version `16.3.3`.
- **Tailwind CSS & Three.js:** Listed under dependencies in `frontend/package.json`.
- **SQLite:** Implemented via `sqlite3` built-in module in `backend/core/database.py`, with `.db` file at root.
- **OpenCV & scikit-image:** Listed in `backend/requirements.txt` and imported heavily in `backend/core/features/extractors.py`.
- **NumPy & SciPy:** Used for matrix transformations (`verification.py`) and Nelder-Mead optimization (`mutual_information.py`).
- **USAC-MAGSAC:** Specifically hardcoded as the RANSAC method in `backend/core/geometry/verification.py` line 49.
- **Kornia / PyTorch / LightGlue:** Implemented in `backend/core/features/learned.py` using `torch` and `kornia.feature`.
- **Docker / Docker Compose:** Present in the root `docker-compose.yml` mapping `frontend` and `backend` services.

## 17. Technologies NOT Found
- Flask / Django / Express — Not found
- PostgreSQL / MySQL / MongoDB — Not found
- AWS / GCP / Azure deployment configs — Not found
- Vue / Angular — Not found
- TensorFlow / Keras — Not found
- Redis / Memcached — Not found
