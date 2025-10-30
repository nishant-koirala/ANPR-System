import cv2
import numpy as np
from config.settings import MIN_PLATE_WIDTH, MIN_PLATE_HEIGHT, PLATE_RESIZE_SCALE, CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE

def enhance_for_ocr(image):
    """Enhance image for better OCR results"""
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    kernel = np.ones((1, 1), np.uint8)
    enhanced = cv2.dilate(enhanced, kernel, iterations=1)
    enhanced = cv2.erode(enhanced, kernel, iterations=1)
    return enhanced

def resize_plate_for_ocr(plate_img):
    """Resize small plates for better OCR"""
    height, width = plate_img.shape[:2]
    if width < MIN_PLATE_WIDTH or height < MIN_PLATE_HEIGHT:
        scale_factor = max(MIN_PLATE_WIDTH/width, MIN_PLATE_HEIGHT/height, PLATE_RESIZE_SCALE)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        plate_img = cv2.resize(plate_img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        return plate_img, True, (width, height), (new_width, new_height)
    return plate_img, False, (width, height), (width, height)

def preprocess_for_ocr(image):
    """Enhanced preprocessing for OCR with denoising, sharpening, and adaptive thresholding"""
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Step 1: Denoise to remove noise artifacts
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # Step 2: Adaptive histogram equalization for better contrast
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID_SIZE)
    enhanced = clahe.apply(denoised)
    
    # Step 3: Sharpen to enhance character edges
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(enhanced, -1, kernel_sharpen)
    
    # Step 4: Adaptive thresholding (better than fixed threshold)
    thresh = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Step 5: Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return cleaned


def is_plate_quality_sufficient(plate_img):
    """Check if plate image quality is good enough for OCR (RELAXED for better coverage)"""
    try:
        # Convert to grayscale if needed
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img
        
        # Check 1: Brightness (avoid too dark or too bright) - RELAXED
        mean_brightness = np.mean(gray)
        if mean_brightness < 20 or mean_brightness > 235:  # Wider range
            return False, "brightness"
        
        # Check 2: Blur detection using Laplacian variance - RELAXED
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 30:  # Lowered from 50 to accept slightly blurry
            return False, "blur"
        
        # Check 3: Contrast (standard deviation) - RELAXED
        contrast = gray.std()
        if contrast < 15:  # Lowered from 20
            return False, "contrast"
        
        # Check 4: Size check - RELAXED
        height, width = gray.shape[:2]
        if width < 40 or height < 12:  # Smaller minimum
            return False, "size"
        
        return True, "ok"
    except Exception:
        return False, "error"


def expand_plate_roi(x1, y1, x2, y2, img_width, img_height, expand_ratio=0.15):
    """Expand plate bounding box to avoid cutting off characters"""
    width = x2 - x1
    height = y2 - y1
    
    # Expand by ratio
    expand_w = width * expand_ratio
    expand_h = height * expand_ratio
    
    # Apply expansion with boundary checks
    x1_new = max(0, int(x1 - expand_w))
    y1_new = max(0, int(y1 - expand_h))
    x2_new = min(img_width, int(x2 + expand_w))
    y2_new = min(img_height, int(y2 + expand_h))
    
    return x1_new, y1_new, x2_new, y2_new
