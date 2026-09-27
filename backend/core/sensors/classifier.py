import numpy as np
import cv2
from loguru import logger

class SensorClassifier:
    """
    Automated Sensor Classification.
    Uses image heuristics (resolution, histogram, frequency) as a robust baseline
    that can easily be swapped with a PyTorch CNN when trained weights are available.
    """

    @staticmethod
    def predict(img: np.ndarray) -> str:
        """
        Returns 'OHRC', 'TMC2', 'IIRS', or 'Unknown' based on image characteristics.
        """
        # 1. Resolution checks
        h, w = img.shape[:2]
        
        # 2. Histogram and frequency characteristics
        # Convert to grayscale if it's BGR
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        mean_val = np.mean(gray)
        std_val = np.std(gray)
        
        # OHRC typically has very high resolution and high contrast/sharpness
        # TMC-2 has medium resolution and distinct lighting
        # For our demo/synthetic datasets:
        
        # We can use simple heuristics for now
        # High contrast and sharp images -> OHRC
        # Smoother / lower resolution -> TMC2
        
        # Calculate Laplacian variance (sharpness)
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        logger.debug(f"SensorClassifier heuristics: shape={w}x{h}, mean={mean_val:.1f}, std={std_val:.1f}, lap_var={lap_var:.1f}")
        
        # Simple heuristic rule for demo purposes
        if lap_var > 1500 or w >= 1024:
            return "OHRC"
        elif 500 <= lap_var <= 1500:
            return "TMC2"
        else:
            return "IIRS"
