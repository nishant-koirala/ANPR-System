import cv2
import easyocr
import os
from config.settings import (OCR_LANGUAGES, OCR_GPU_ENABLED, OCR_CONFIDENCE_THRESHOLD, DEBUG_OCR_VERBOSE, DEBUG_SAVE_IMAGES,
                             OCR_FORMAT1_STANDARD_WIDTH_THS, OCR_FORMAT1_STANDARD_HEIGHT_THS, OCR_FORMAT1_STANDARD_MIN_SIZE,
                             OCR_FORMAT1_RELAXED_WIDTH_THS, OCR_FORMAT1_RELAXED_HEIGHT_THS, OCR_FORMAT1_RELAXED_MIN_SIZE,
                             OCR_FORMAT2_PARAGRAPH_WIDTH_THS, OCR_FORMAT2_PARAGRAPH_HEIGHT_THS,
                             OCR_FORMAT2_STANDARD_WIDTH_THS, OCR_FORMAT2_STANDARD_HEIGHT_THS, OCR_FORMAT2_STANDARD_MIN_SIZE,
                             OCR_FORMAT2_PERMISSIVE_WIDTH_THS, OCR_FORMAT2_PERMISSIVE_HEIGHT_THS, OCR_FORMAT2_PERMISSIVE_MIN_SIZE,
                             DEFAULT_LICENSE_FORMAT, RECOGNITION_METHOD, TWO_STAGE_MIN_CHARS, TWO_STAGE_USE_PREPROCESSING, TWO_STAGE_MIN_CONFIDENCE)
from src.utils.image_processing import resize_plate_for_ocr, preprocess_for_ocr, is_plate_quality_sufficient
from src.utils.text_processing import flatten_text, validate_license_format, format_license_plate
from src.utils.advanced_processing import correct_plate_perspective, calculate_plate_quality_score

# Import two-stage recognizer
try:
    from src.ocr.character_recognizer import CharacterRecognizer
    TWO_STAGE_AVAILABLE = True
except ImportError as e:
    print(f"Two-stage recognizer not available: {e}")
    TWO_STAGE_AVAILABLE = False

class PlateReader:
    def __init__(self):
        # Initialize EasyOCR reader
        self.ocr_reader = easyocr.Reader(OCR_LANGUAGES, gpu=OCR_GPU_ENABLED)
        
        # Initialize two-stage recognizer if available
        self.two_stage_recognizer = None
        if TWO_STAGE_AVAILABLE:
            try:
                self.two_stage_recognizer = CharacterRecognizer()
                if self.two_stage_recognizer.is_available():
                    print("Two-stage character recognizer initialized successfully")
                else:
                    print("Two-stage recognizer initialization failed - models not loaded")
                    self.two_stage_recognizer = None
            except Exception as e:
                print(f"Failed to initialize two-stage recognizer: {e}")
                self.two_stage_recognizer = None
        
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
            
            # Quality check before processing
            is_quality_ok, quality_reason = is_plate_quality_sufficient(image)
            if not is_quality_ok:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: Plate quality insufficient: {quality_reason}")
                return None, None

            # Use default format from settings if not specified
            if license_format is None:
                license_format = DEFAULT_LICENSE_FORMAT
            
            # Route to appropriate recognition method
            if RECOGNITION_METHOD == "two_stage" and self.two_stage_recognizer is not None:
                if DEBUG_OCR_VERBOSE:
                    print("DEBUG: Using two-stage YOLO+CNN recognition")
                return self._extract_with_two_stage(image, license_format)
            else:
                if DEBUG_OCR_VERBOSE:
                    print("DEBUG: Using EasyOCR recognition")
                return self._extract_with_easyocr(image, license_format)
        except Exception as e:
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: OCR Exception: {e}")
            return None, None
    
    def _extract_with_two_stage(self, image, license_format):
        """Extract text using two-stage YOLO+CNN pipeline"""
        try:
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: [TWO-STAGE] Starting recognition on image shape: {image.shape}")
            
            # Minimal quality check - just reject obviously bad images
            h, w = image.shape[:2]
            
            # Only reject extremely small images
            if w < 40 or h < 15:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] ✗ Image too small: {w}x{h}")
                return None, None
            
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: [TWO-STAGE] ✓ Processing plate: {w}x{h}")
            
            # Optional preprocessing (can be disabled via TWO_STAGE_USE_PREPROCESSING)
            if TWO_STAGE_USE_PREPROCESSING:
                # Resize small plates for better recognition
                processed_img, was_resized, old_size, new_size = resize_plate_for_ocr(image)
                if was_resized and DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] Resized plate from {old_size[0]}x{old_size[1]} to {new_size[0]}x{new_size[1]}")
                
                # Apply perspective correction
                processed_img = correct_plate_perspective(processed_img)
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] Applied perspective correction")
            else:
                processed_img = image
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] Skipping preprocessing (TWO_STAGE_USE_PREPROCESSING=False)")
            
            # Save debug images if enabled
            if DEBUG_SAVE_IMAGES:
                target_dir = self.debug_dir if self.debug_dir and os.path.isdir(self.debug_dir) else "."
                debug_filename = os.path.join(target_dir, f"debug_plate_twostage_f{self.frame_counter}.jpg")
                cv2.imwrite(debug_filename, processed_img)
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] Saved plate image: {debug_filename}")
            
            # Recognize characters using two-stage pipeline
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: [TWO-STAGE] Calling character recognizer...")
            
            text, confidence = self.two_stage_recognizer.recognize_characters(processed_img)
            
            if text is None:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] Pipeline returned None - no characters detected")
                return None, None
            
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: [TWO-STAGE] Recognized: '{text}' (confidence: {confidence:.3f}, length: {len(text)})")
            
            # Two-stage pipeline outputs Nepali characters directly
            # Extract valid plate portion from RIGHT to LEFT (backwards)
            # Pattern: [optional: region] + [1-3 digits] + [1 vehicle letter] + [3-4 digits]
            
            # YOLO outputs compound characters as single units (बा, भे, मे, etc.)
            nepali_digits = '०१२३४५६७८९'
            vehicle_type_letters = 'कचपखजफगझबयघञ'  # Exact vehicle type letters
            region_codes = ['मे', 'को', 'स', 'ज', 'बा', 'ना', 'ग', 'लु', 'ध', 'रा', 'भे', 'क', 'से', 'म']
            
            # Convert text to list of characters for proper indexing
            text_chars = list(text)
            
            # Work backwards from the end
            extracted = []
            i = len(text) - 1
            
            # Step 1: Extract 3-4 digits from the end (MANDATORY)
            end_digits = 0
            while i >= 0 and end_digits < 4:
                if text[i] in nepali_digits:
                    extracted.insert(0, text[i])
                    end_digits += 1
                    i -= 1
                else:
                    break
            
            if end_digits < 3 or end_digits > 4:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] ✗ Need exactly 3-4 digits at end, found {end_digits}: '{text}'")
                return None, None
            
            # Step 2: Extract 1 vehicle type letter (MANDATORY)
            if i >= 0 and text[i] in vehicle_type_letters:
                extracted.insert(0, text[i])
                i -= 1
            else:
                if DEBUG_OCR_VERBOSE:
                    char = text[i] if i >= 0 else 'EOF'
                    print(f"DEBUG: [TWO-STAGE] ✗ Need vehicle type letter (क,च,प,ख,ज,फ,ग,झ,ब,य,घ,ञ), found '{char}': '{text}'")
                return None, None
            
            # Step 3: Extract 1-3 digits (MANDATORY)
            middle_digits = 0
            while i >= 0 and middle_digits < 3:
                if text[i] in nepali_digits:
                    extracted.insert(0, text[i])
                    middle_digits += 1
                    i -= 1
                else:
                    break
            
            if middle_digits < 1 or middle_digits > 3:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] ✗ Need 1-3 middle digits, found {middle_digits}: '{text}'")
                return None, None
            
            # Step 4: Extract optional region code (OPTIONAL)
            # YOLO outputs compound chars like 'बा' as ONE character
            # Check if the next character (before middle digits) is a valid region code
            
            if i >= 0:
                # Get the character before middle digits
                potential_region = text[i]
                
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] Checking for region: '{potential_region}' at position {i}")
                
                # Check if it's a valid region code
                if potential_region in region_codes:
                    extracted.insert(0, potential_region)
                    if DEBUG_OCR_VERBOSE:
                        print(f"DEBUG: [TWO-STAGE] ✓ Matched region: '{potential_region}'")
                else:
                    if DEBUG_OCR_VERBOSE:
                        print(f"DEBUG: [TWO-STAGE] ℹ '{potential_region}' is not a valid region code (optional, continuing)")
            
            # Build the extracted plate text
            plate_text = ''.join(extracted)
            
            # Validate minimum length
            if len(plate_text) < 5:  # Minimum: 1 digit + 1 letter + 3 digits = 5
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] ✗ Extracted text too short: '{plate_text}' (length: {len(plate_text)})")
                return None, None
            
            # Check confidence threshold
            if confidence < TWO_STAGE_MIN_CONFIDENCE:
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: [TWO-STAGE] ✗ Confidence too low: {confidence:.3f} < {TWO_STAGE_MIN_CONFIDENCE}")
                return None, None
            
            # Success!
            if DEBUG_OCR_VERBOSE:
                if plate_text != text:
                    print(f"DEBUG: [TWO-STAGE] ✓ Extracted valid portion: '{plate_text}' from '{text}' (conf:{confidence:.3f})")
                else:
                    print(f"DEBUG: [TWO-STAGE] ✓ Valid Nepali plate: '{plate_text}' (conf:{confidence:.3f})")
            
            return plate_text, confidence
                
        except Exception as e:
            if DEBUG_OCR_VERBOSE:
                print(f"DEBUG: [TWO-STAGE] Recognition error: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def _extract_with_easyocr(self, image, license_format):
        """Extract text using EasyOCR (original method)"""
        try:
            
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
            
            # Apply perspective correction for better OCR
            processed_img = correct_plate_perspective(processed_img)
            
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
                
                # PHASE 3: Try ALL strategies and collect results (not just first success)
                all_strategy_results = []
                for strategy in strategies:
                    try:
                        strategy_detections = self.ocr_reader.readtext(strategy['img'], **strategy['params'])
                        if DEBUG_OCR_VERBOSE:
                            print(f"DEBUG: {strategy['name']} found {len(strategy_detections)} detections")
                        if len(strategy_detections) > 0:
                            all_strategy_results.append((strategy['name'], strategy_detections))
                    except Exception as e:
                        if DEBUG_OCR_VERBOSE:
                            print(f"DEBUG: {strategy['name']} failed: {e}")
                        continue
                
                # Use detections from best strategy (or first if only one)
                if all_strategy_results:
                    # For now, use first successful strategy's detections
                    # Later we'll implement voting across all strategies
                    detections = all_strategy_results[0][1]
                        
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
                
                # Enhanced OCR artifact cleaning
                import re
                
                # Step 1: Common character substitutions (OCR mistakes)
                # Only include unambiguous substitutions — characters that are
                # never valid letters in Nepali plate district codes.
                # B, S, G are valid district-code prefix letters and must NOT
                # be substituted here; the format_text() position-based mapper
                # handles digit-position corrections downstream.
                char_substitutions = {
                    '|': 'I', '!': 'I',  # Vertical lines to I
                    '/': '7', '\\': '7', # Slashes to 7
                    'Q': 'O', '@': 'O',  # Similar to O
                    '&': '8',            # Ampersand to 8
                    'Z': '2',            # Similar to 2
                }
                
                # Apply substitutions for likely positions
                # (This is conservative - only obvious mistakes)
                for old_char, new_char in char_substitutions.items():
                    if old_char in text:
                        text = text.replace(old_char, new_char)
                
                # Step 2: Remove special characters and artifacts
                cleaned_text = re.sub(r'[^A-Z0-9\s]', '', text)
                
                # Step 3: Normalize multiple spaces
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                
                # Step 4: Remove isolated single characters that are likely noise
                words = cleaned_text.split()
                if len(words) > 2:
                    # Keep only words with 2+ chars or if it's the only word
                    words = [w for w in words if len(w) >= 2 or len(words) == 1]
                    cleaned_text = ' '.join(words)
                
                if DEBUG_OCR_VERBOSE:
                    print(f"DEBUG: Cleaned text: '{text}' -> '{cleaned_text}'")
                
                # Use cleaned text for processing
                text = cleaned_text
                
                # Skip if cleaned text is too short
                if len(text.replace(' ', '')) < 4:
                    if DEBUG_OCR_VERBOSE:
                        print(f"DEBUG: Text too short after cleaning: '{text}'")
                    continue
                
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
