import cv2
import easyocr
import os
from config.settings import (OCR_LANGUAGES, OCR_GPU_ENABLED, OCR_CONFIDENCE_THRESHOLD, DEBUG_OCR_VERBOSE, DEBUG_SAVE_IMAGES,
                             OCR_FORMAT1_STANDARD_WIDTH_THS, OCR_FORMAT1_STANDARD_HEIGHT_THS, OCR_FORMAT1_STANDARD_MIN_SIZE,
                             OCR_FORMAT1_RELAXED_WIDTH_THS, OCR_FORMAT1_RELAXED_HEIGHT_THS, OCR_FORMAT1_RELAXED_MIN_SIZE,
                             OCR_FORMAT2_PARAGRAPH_WIDTH_THS, OCR_FORMAT2_PARAGRAPH_HEIGHT_THS,
                             OCR_FORMAT2_STANDARD_WIDTH_THS, OCR_FORMAT2_STANDARD_HEIGHT_THS, OCR_FORMAT2_STANDARD_MIN_SIZE,
                             OCR_FORMAT2_PERMISSIVE_WIDTH_THS, OCR_FORMAT2_PERMISSIVE_HEIGHT_THS, OCR_FORMAT2_PERMISSIVE_MIN_SIZE,
                             DEFAULT_LICENSE_FORMAT)
from src.utils.image_processing import resize_plate_for_ocr, preprocess_for_ocr
from src.utils.text_processing import flatten_text, validate_license_format, format_license_plate

class PlateReader:
    def __init__(self):
        self.ocr_reader = easyocr.Reader(OCR_LANGUAGES, gpu=OCR_GPU_ENABLED)
        self.frame_counter = 0
        # Optional directory to store debug images
        self.debug_dir = None
    
    def extract_plate_text(self, image, license_format=None):
        """Extract text from license plate image"""
        try:
            # Check image validity
            if image is None or image.size == 0:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: Invalid image for OCR")
                return None, None
            
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: Processing image of size {image.shape}")

            # Use default format from settings if not specified
            if license_format is None:
                license_format = DEFAULT_LICENSE_FORMAT
            
            # Automatic mode: try all formats
            if license_format == 'auto':
                for fmt in ('format3', 'format2', 'format1'):
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
                    # Format 2: AA 1111 - multiple strategies for spaced text
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
                elif license_format == 'format3':
                    # Format 3: A AA 1111 - similar to format2 but with 3 letters
                    strategies = [
                        # Strategy 1: Paragraph mode with relaxed parameters
                        {'img': processed_img, 'params': {'paragraph': True, 'width_ths': OCR_FORMAT2_PARAGRAPH_WIDTH_THS, 'height_ths': OCR_FORMAT2_PARAGRAPH_HEIGHT_THS}, 'name': 'Format3 paragraph'},
                        # Strategy 2: Standard mode with very relaxed parameters
                        {'img': processed_img, 'params': {'width_ths': OCR_FORMAT2_STANDARD_WIDTH_THS, 'height_ths': OCR_FORMAT2_STANDARD_HEIGHT_THS, 'min_size': OCR_FORMAT2_STANDARD_MIN_SIZE}, 'name': 'Format3 standard'},
                        # Strategy 3: Try on threshold image with paragraph mode
                        {'img': thresh, 'params': {'paragraph': True, 'width_ths': OCR_FORMAT2_PARAGRAPH_WIDTH_THS, 'height_ths': OCR_FORMAT2_PARAGRAPH_HEIGHT_THS}, 'name': 'Format3 thresh paragraph'},
                        # Strategy 4: Try on threshold image standard
                        {'img': thresh, 'params': {'width_ths': OCR_FORMAT2_STANDARD_WIDTH_THS, 'height_ths': OCR_FORMAT2_STANDARD_HEIGHT_THS, 'min_size': OCR_FORMAT2_STANDARD_MIN_SIZE}, 'name': 'Format3 thresh standard'},
                        # Strategy 5: Very permissive detection
                        {'img': processed_img, 'params': {'width_ths': OCR_FORMAT2_PERMISSIVE_WIDTH_THS, 'height_ths': OCR_FORMAT2_PERMISSIVE_HEIGHT_THS, 'min_size': OCR_FORMAT2_PERMISSIVE_MIN_SIZE}, 'name': 'Format3 permissive'}
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
                
                # Clean OCR artifacts and special characters
                import re
                # Remove common OCR artifacts and keep only alphanumeric and spaces
                cleaned_text = re.sub(r'[^A-Z0-9\s]', '', text)
                # Normalize multiple spaces to single space
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: Cleaned text: '{text}' -> '{cleaned_text}'")
                
                # Use cleaned text for processing
                text = cleaned_text
                
                # Handle text variations based on format
                if license_format in ['format2', 'format3']:
                    text_variations = [
                        text,  # Original text
                        text.replace(' ', ''),  # No spaces
                        text.replace('\n', ' '),  # Replace newlines with spaces
                        text.replace('\n', ''),  # Remove newlines
                        text.replace('  ', ' '),  # Normalize double spaces
                    ]
                    
                    # Try to extract meaningful parts from noisy text
                    words = text.split()
                    if len(words) >= 2:
                        # Try different combinations of words
                        for i in range(len(words)):
                            for j in range(i+1, len(words)+1):
                                candidate = ' '.join(words[i:j])
                                if len(candidate.replace(' ', '')) >= 4:  # Minimum meaningful length
                                    text_variations.append(candidate)
                    
                    # Add variation with spaces inserted based on format
                    no_space_text = text.replace(' ', '')
                    if license_format == 'format2' and len(no_space_text) >= 6:
                        # Format 2: AA 1111 - space after 2 characters
                        text_variations.append(f"{no_space_text[:2]} {no_space_text[2:]}")
                    elif license_format == 'format3' and len(no_space_text) >= 7:
                        # Format 3: A AA 1111 - spaces after 1st and 3rd characters
                        text_variations.append(f"{no_space_text[0]} {no_space_text[1:3]} {no_space_text[3:]}")
                        # Also try with just one space after 3 characters
                        text_variations.append(f"{no_space_text[:3]} {no_space_text[3:]}")
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
