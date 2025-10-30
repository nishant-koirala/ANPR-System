"""
Advanced image processing utilities for Phase 3 enhancements
Includes perspective correction and quality scoring
"""

import cv2
import numpy as np


def correct_plate_perspective(plate_img, max_angle=30):
    """
    Correct perspective distortion in plate image
    
    Args:
        plate_img: Input plate image
        max_angle: Maximum angle deviation to correct (degrees)
    
    Returns:
        Corrected plate image or original if correction fails
    """
    try:
        # Convert to grayscale
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return plate_img
        
        # Get largest contour (likely the plate border)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get minimum area rectangle
        rect = cv2.minAreaRect(largest_contour)
        angle = rect[2]
        
        # Normalize angle
        if angle < -45:
            angle = 90 + angle
        
        # Only correct if angle is significant but not too extreme
        if abs(angle) > 2 and abs(angle) < max_angle:
            # Get rotation matrix
            (h, w) = plate_img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Rotate image
            corrected = cv2.warpAffine(plate_img, M, (w, h),
                                      flags=cv2.INTER_CUBIC,
                                      borderMode=cv2.BORDER_REPLICATE)
            
            return corrected
        
        return plate_img
        
    except Exception:
        return plate_img


def calculate_plate_quality_score(plate_img, ocr_confidence=None):
    """
    Calculate comprehensive quality score for plate image
    
    Args:
        plate_img: Input plate image
        ocr_confidence: Optional OCR confidence score
    
    Returns:
        Quality score between 0.0 and 1.0
    """
    try:
        # Convert to grayscale if needed
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img
        
        scores = []
        
        # 1. Sharpness (Laplacian variance) - weight: 30%
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 500.0, 1.0)  # Normalize to 0-1
        scores.append(('sharpness', sharpness_score, 0.30))
        
        # 2. Contrast (standard deviation) - weight: 25%
        contrast = gray.std()
        contrast_score = min(contrast / 100.0, 1.0)  # Normalize to 0-1
        scores.append(('contrast', contrast_score, 0.25))
        
        # 3. Brightness (distance from ideal 128) - weight: 15%
        mean_brightness = gray.mean()
        brightness_score = 1.0 - abs(mean_brightness - 128) / 128.0
        brightness_score = max(0.0, brightness_score)
        scores.append(('brightness', brightness_score, 0.15))
        
        # 4. Size adequacy - weight: 10%
        height, width = gray.shape[:2]
        size_score = min((width * height) / (200 * 60), 1.0)  # Normalize based on ideal size
        scores.append(('size', size_score, 0.10))
        
        # 5. OCR confidence - weight: 20%
        if ocr_confidence is not None:
            ocr_score = float(ocr_confidence)
            scores.append(('ocr', ocr_score, 0.20))
        else:
            # Redistribute weight if no OCR confidence
            for i in range(len(scores)):
                name, score, weight = scores[i]
                scores[i] = (name, score, weight * 1.25)  # Increase other weights proportionally
        
        # Calculate weighted average
        total_score = sum(score * weight for _, score, weight in scores)
        
        return min(max(total_score, 0.0), 1.0)  # Clamp to 0-1
        
    except Exception:
        return 0.5  # Return neutral score on error


def detect_plate_angle(plate_img):
    """
    Detect the angle of plate rotation
    
    Args:
        plate_img: Input plate image
    
    Returns:
        Angle in degrees (positive = clockwise, negative = counter-clockwise)
    """
    try:
        # Convert to grayscale
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Hough line detection
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=50)
        
        if lines is None or len(lines) == 0:
            return 0.0
        
        # Calculate average angle from detected lines
        angles = []
        for line in lines[:10]:  # Use top 10 lines
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            
            # Normalize to -90 to 90 range
            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180
            
            # Only consider reasonable angles
            if abs(angle) < 45:
                angles.append(angle)
        
        if angles:
            return np.median(angles)
        
        return 0.0
        
    except Exception:
        return 0.0


def enhance_plate_for_ocr(plate_img):
    """
    Apply multiple enhancement techniques and return best result
    
    Args:
        plate_img: Input plate image
    
    Returns:
        List of enhanced images with their quality scores
    """
    enhanced_images = []
    
    try:
        # Original
        original_score = calculate_plate_quality_score(plate_img)
        enhanced_images.append(('original', plate_img, original_score))
        
        # Perspective corrected
        corrected = correct_plate_perspective(plate_img)
        corrected_score = calculate_plate_quality_score(corrected)
        enhanced_images.append(('perspective_corrected', corrected, corrected_score))
        
        # High contrast
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img
        
        # CLAHE enhancement
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        enhanced_score = calculate_plate_quality_score(enhanced)
        enhanced_images.append(('clahe_enhanced', enhanced, enhanced_score))
        
        # Bilateral filter (preserves edges while smoothing)
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        bilateral_score = calculate_plate_quality_score(bilateral)
        enhanced_images.append(('bilateral_filtered', bilateral, bilateral_score))
        
        # Sort by quality score
        enhanced_images.sort(key=lambda x: x[2], reverse=True)
        
        return enhanced_images
        
    except Exception:
        # Return original if enhancement fails
        return [('original', plate_img, 0.5)]


def is_plate_readable(plate_img, min_quality_score=0.3):
    """
    Quick check if plate is likely readable
    
    Args:
        plate_img: Input plate image
        min_quality_score: Minimum quality threshold
    
    Returns:
        (is_readable, quality_score, reason)
    """
    try:
        quality_score = calculate_plate_quality_score(plate_img)
        
        if quality_score < min_quality_score:
            return False, quality_score, "low_quality"
        
        # Convert to grayscale
        if len(plate_img.shape) == 3:
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = plate_img
        
        # Check dimensions
        height, width = gray.shape[:2]
        if width < 50 or height < 15:
            return False, quality_score, "too_small"
        
        # Check if too blurry
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 30:
            return False, quality_score, "too_blurry"
        
        # Check contrast
        if gray.std() < 15:
            return False, quality_score, "low_contrast"
        
        return True, quality_score, "ok"
        
    except Exception:
        return False, 0.0, "error"
