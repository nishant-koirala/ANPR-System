import cv2
import easyocr
import os
from config.settings import (OCR_LANGUAGES, OCR_GPU_ENABLED, OCR_CONFIDENCE_THRESHOLD, DEBUG_OCR_VERBOSE, DEBUG_SAVE_IMAGES,
                             OCR_FORMAT1_STANDARD_WIDTH_THS, OCR_FORMAT1_STANDARD_HEIGHT_THS, OCR_FORMAT1_STANDARD_MIN_SIZE,
                             OCR_FORMAT1_RELAXED_WIDTH_THS, OCR_FORMAT1_RELAXED_HEIGHT_THS, OCR_FORMAT1_RELAXED_MIN_SIZE,
                             OCR_FORMAT2_PARAGRAPH_WIDTH_THS, OCR_FORMAT2_PARAGRAPH_HEIGHT_THS,
                             OCR_FORMAT2_STANDARD_WIDTH_THS, OCR_FORMAT2_STANDARD_HEIGHT_THS, OCR_FORMAT2_STANDARD_MIN_SIZE,
                             OCR_FORMAT2_PERMISSIVE_WIDTH_THS, OCR_FORMAT2_PERMISSIVE_HEIGHT_THS, OCR_FORMAT2_PERMISSIVE_MIN_SIZE)
from src.utils.image_processing import resize_plate_for_ocr, preprocess_for_ocr
from src.utils.text_processing import flatten_text, validate_license_format, format_license_plate

class PlateReader:
    def __init__(self):
        self.ocr_reader = easyocr.Reader(OCR_LANGUAGES, gpu=OCR_GPU_ENABLED)
        self.frame_counter = 0
        # Optional directory to store debug images
        self.debug_dir = None
    
    def extract_plate_text(self, image, license_format='format1'):
        """Extract text from license plate image"""
        try:
            # Check image validity
            if image is None or image.size == 0:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: Invalid image for OCR")
                return None, None
            
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: Processing image of size {image.shape}")

            # Automatic mode: try both formats
            if license_format == 'auto':
                for fmt in ('format2', 'format1'):
                    if DEBUG_OCR_VERBOSE:
                        print(f"DEBUG: Auto mode - trying {fmt}")
                    t, s = self.extract_plate_text(image, fmt)
                    if t is not None:
                        return t, s
                return None, None
            
            # Resize small plates for better OCR
            processed_img, was_resized, old_size, new_size = resize_plate_for_ocr(image)
            if was_resized and DEBUG_OCR_VERBOSE:
                print(f"DEBUG: Resized plate from {old_size[0]}x{old_size[1]} to {new_size[0]}x{new_size[1]}")
            
            # Save debug images if enabled
            if DEBUG_SAVE_IMAGES:
                # Determine target directory for debug images
                target_dir = self.debug_dir if self.debug_dir and os.path.isdir(self.debug_dir) else "."
                debug_filename = os.path.join(target_dir, f"debug_plate_f{self.frame_counter}.jpg")
                cv2.imwrite(debug_filename, processed_img)
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: Saved plate image: {debug_filename}")
            
            # Preprocess for OCR
            thresh = preprocess_for_ocr(processed_img)
            
            # Save preprocessed image for debugging
            if DEBUG_SAVE_IMAGES:
                target_dir = self.debug_dir if self.debug_dir and os.path.isdir(self.debug_dir) else "."
                cv2.imwrite(os.path.join(target_dir, f"debug_thresh_{self.frame_counter}.jpg"), thresh)
            
            # Try OCR with multiple strategies for better detection
            try:
                detections = []
                strategies = []
                
                if license_format == 'format2':
                    # Format 2: AA 0101 - multiple strategies for spaced text
                    strategies = [
                        # Strategy 1: Paragraph mode with relaxed parameters
                        {'img': processed_img, 'params': {'paragraph': True, 'width_ths': OCR_FORMAT2_PARAGRAPH_WIDTH_THS, 'height_ths': OCR_FORMAT2_PARAGRAPH_HEIGHT_THS}, 'name': 'Format2 paragraph'},
                        # Strategy 2: Standard mode with very relaxed parameters
                        {'img': processed_img, 'params': {'width_ths': OCR_FORMAT2_STANDARD_WIDTH_THS, 'height_ths': OCR_FORMAT2_STANDARD_HEIGHT_THS, 'min_size': OCR_FORMAT2_STANDARD_MIN_SIZE}, 'name': 'Format2 standard'},
                        # Strategy 3: Try on threshold image with paragraph mode
                        {'img': thresh, 'params': {'paragraph': True, 'width_ths': OCR_FORMAT2_PARAGRAPH_WIDTH_THS, 'height_ths': OCR_FORMAT2_PARAGRAPH_HEIGHT_THS}, 'name': 'Format2 thresh paragraph'},
                        # Strategy 4: Try on threshold image standard
                        {'img': thresh, 'params': {'width_ths': OCR_FORMAT2_STANDARD_WIDTH_THS, 'height_ths': OCR_FORMAT2_STANDARD_HEIGHT_THS, 'min_size': OCR_FORMAT2_STANDARD_MIN_SIZE}, 'name': 'Format2 thresh standard'},
                        # Strategy 5: Very permissive detection
                        {'img': processed_img, 'params': {'width_ths': OCR_FORMAT2_PERMISSIVE_WIDTH_THS, 'height_ths': OCR_FORMAT2_PERMISSIVE_HEIGHT_THS, 'min_size': OCR_FORMAT2_PERMISSIVE_MIN_SIZE}, 'name': 'Format2 permissive'}
                    ]
                else:
                    # Format 1: AA00AAA - standard strategies
                    strategies = [
                        # Strategy 1: Standard detection
                        {'img': processed_img, 'params': {'width_ths': OCR_FORMAT1_STANDARD_WIDTH_THS, 'height_ths': OCR_FORMAT1_STANDARD_HEIGHT_THS, 'min_size': OCR_FORMAT1_STANDARD_MIN_SIZE}, 'name': 'Format1 standard'},
                        # Strategy 2: Relaxed detection
                        {'img': processed_img, 'params': {'width_ths': OCR_FORMAT1_RELAXED_WIDTH_THS, 'height_ths': OCR_FORMAT1_RELAXED_HEIGHT_THS, 'min_size': OCR_FORMAT1_RELAXED_MIN_SIZE}, 'name': 'Format1 relaxed'},
                        # Strategy 3: Threshold image
                        {'img': thresh, 'params': {'width_ths': OCR_FORMAT1_STANDARD_WIDTH_THS, 'height_ths': OCR_FORMAT1_STANDARD_HEIGHT_THS, 'min_size': OCR_FORMAT1_STANDARD_MIN_SIZE}, 'name': 'Format1 thresh'}
                    ]
                
                # Try each strategy until we get detections
                for strategy in strategies:
                    try:
                        detections = self.ocr_reader.readtext(strategy['img'], **strategy['params'])
                        if DEBUG_OCR_VERBOSE:
                            print(f"DEBUG: {strategy['name']} found {len(detections)} detections")
                        if len(detections) > 0:
                            break
                    except Exception as e:
                        if DEBUG_OCR_VERBOSE:
                            print(f"DEBUG: {strategy['name']} failed: {e}")
                        continue
                        
            except Exception as e:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: OCR detection failed: {e}")
                detections = []
            
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: EasyOCR found {len(detections)} detections")
            
            for detection in detections:
                # Handle different EasyOCR return formats
                if len(detection) == 3:
                    bbox, text, score = detection
                elif len(detection) == 2:
                    # For 2-element tuple, check which format it is
                    if isinstance(detection[0], str):
                        # Format: (text, score)
                        text, score = detection
                        bbox = None
                    else:
                        # Format: (bbox, text) or other - extract text from second element
                        bbox, text = detection
                        score = 1.0  # Default score if not provided
                else:
                    if DEBUG_OCR_VERBOSE:
                        print(f"DEBUG: Unexpected detection format: {detection}")
                    continue
                
                # Handle text being returned as list or string (including nested lists)
                text = flatten_text(text)
                
                # Clean and normalize text
                text = str(text).upper().strip()
                
                # For Format 2, try multiple text variations to handle OCR inconsistencies
                if license_format == 'format2':
                    text_variations = [
                        text,  # Original text
                        text.replace(' ', ''),  # No spaces
                        text.replace('\n', ' '),  # Replace newlines with spaces
                        text.replace('\n', ''),  # Remove newlines
                        text.replace('  ', ' '),  # Normalize double spaces
                    ]
                    # Add variation with space inserted after 2 characters if no space exists
                    if ' ' not in text and len(text) >= 3:
                        text_variations.append(f"{text[:2]} {text[2:]}")
                else:
                    # For Format 1, just remove all spaces
                    text_variations = [text.replace(' ', '').replace('\n', '')]
                
                # Debug raw OCR text
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: Raw OCR text: '{text}', score: {score}, format: {license_format}")
                    print(f"DEBUG: Text variations: {text_variations}")
                
                # Try validation with each text variation
                for variation in text_variations:
                    if validate_license_format(variation, license_format):
                        formatted_text = format_license_plate(variation, license_format)
                        if DEBUG_OCR_VERBOSE:
                            print(f"DEBUG: Valid plate found: '{formatted_text}' (from variation: '{variation}'), score: {score}")
                        return formatted_text, score
                
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: No valid variations found for text '{text}'")
            
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: No valid plates found in OCR detections")
            return None, None
        except Exception as e:
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: OCR Exception: {e}")
            return None, None
    
    def set_frame_counter(self, frame_counter):
        """Set frame counter for debug image naming"""
        self.frame_counter = frame_counter

    def set_debug_dir(self, debug_dir):
        """Set directory to save debug images. Directory must exist."""
        self.debug_dir = debug_dir
