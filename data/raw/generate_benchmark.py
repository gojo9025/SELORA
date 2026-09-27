import cv2
import numpy as np
import shutil

def create_benchmark_pair():
    base_path = r"C:\Users\GOUSHIK\.gemini\antigravity-ide\brain\ca391017-2d9f-4dfd-b441-a898be25df17\lunar_surface_base_1790450267173.jpg"
    
    # Read the generated image
    img = cv2.imread(base_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("Failed to load image")
        return
        
    h, w = img.shape
    
    # Save OHRC (source)
    # We will crop the center 800x800 to avoid edges when warping the reference
    center_h, center_w = h // 2, w // 2
    ohrc = img[center_h - 400:center_h + 400, center_w - 400:center_w + 400]
    cv2.imwrite("OHRC_benchmark.png", ohrc)
    
    # Create LRO NAC (reference)
    # Apply a rotation of 15 degrees, scale of 0.8
    M = cv2.getRotationMatrix2D((center_w, center_h), 15, 0.8)
    warped = cv2.warpAffine(img, M, (w, h))
    
    # Crop the exact same area, but from the warped image, so it represents the same scene
    lro_nac = warped[center_h - 400:center_h + 400, center_w - 400:center_w + 400]
    
    # Change contrast/brightness to simulate different sensor
    lro_nac = cv2.convertScaleAbs(lro_nac, alpha=1.2, beta=-30)
    
    cv2.imwrite("LRO_NAC_benchmark.png", lro_nac)
    print("Successfully created OHRC_benchmark.png and LRO_NAC_benchmark.png")

if __name__ == "__main__":
    create_benchmark_pair()
