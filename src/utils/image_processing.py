import cv2
import numpy as np
from config.settings import MIN_PLATE_WIDTH, MIN_PLATE_HEIGHT, PLATE_RESIZE_SCALE

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
    """Preprocess image for OCR using reference system method"""
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, thresh = cv2.threshold(gray, 64, 255, cv2.THRESH_BINARY_INV)
    return thresh
