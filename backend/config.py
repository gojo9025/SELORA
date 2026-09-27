"""SELORA Backend Configuration"""

from pathlib import Path
from pydantic_settings import BaseSettings


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DATA_ROOT = str(_PROJECT_ROOT / "data")


class Settings(BaseSettings):
    # Storage
    DATA_ROOT: str = _DEFAULT_DATA_ROOT
    UPLOAD_DIR: str = str(_PROJECT_ROOT / "data" / "raw")
    PROCESSED_DIR: str = str(_PROJECT_ROOT / "data" / "processed")
    RESULTS_DIR: str = str(_PROJECT_ROOT / "data" / "processed" / "results")
    VISUALIZATIONS_DIR: str = str(_PROJECT_ROOT / "data" / "processed" / "visualizations")
    DATABASE_PATH: str = str(_PROJECT_ROOT / "data" / "selora.db")
    SEED_DATA_DIR: str = str(_PROJECT_ROOT / "data" / "raw")

    # Browser access
    # Use a comma-separated value in deployment, for example:
    # CORS_ORIGINS=https://selora.vercel.app
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # Upload limits
    MAX_FILE_SIZE_MB: int = 200
    MAX_IMAGE_WIDTH: int = 8192
    MAX_IMAGE_HEIGHT: int = 8192
    ALLOWED_EXTENSIONS: list = ["png", "jpg", "jpeg", "tiff", "tif"]

    # Registration defaults
    DEFAULT_MODE: str = "robust"
    MAX_PROCESSING_TIME_SEC: int = 120

    # Quality gate thresholds
    MIN_MATCHES: int = 20
    MIN_INLIERS: int = 10
    MIN_INLIER_RATIO: float = 0.15
    MAX_RMSE_PIXELS: float = 20.0
    MIN_SPATIAL_COVERAGE: float = 0.15

    # SIFT defaults
    SIFT_N_FEATURES: int = 5000
    SIFT_N_OCTAVE_LAYERS: int = 3
    SIFT_CONTRAST_THRESHOLD: float = 0.04
    SIFT_EDGE_THRESHOLD: float = 10.0
    SIFT_SIGMA: float = 1.6

    # ORB defaults
    ORB_N_FEATURES: int = 5000

    # Matching
    RATIO_TEST_THRESHOLD: float = 0.75
    RANSAC_THRESHOLD: float = 3.0
    RANSAC_MAX_ITER: int = 2000

    class Config:
        env_file = ".env"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
