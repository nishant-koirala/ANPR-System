#!/usr/bin/env python3
"""
Image Processing Utilities for ANPR System
Handles plate image cropping, thumbnail generation, and storage
"""

import os
import cv2
import numpy as np
from datetime import datetime
from PIL import Image
import hashlib

class PlateImageProcessor:
    """Handles plate image processing and storage"""
    
    def __init__(self, base_storage_path="plate_images"):
        """
        Initialize the image processor
        
        Args:
            base_storage_path: Base directory for storing plate images
        """
        self.base_storage_path = base_storage_path
        self.thumbnail_size = (150, 50)  # Standard thumbnail size
        
        # Create storage directories
        self.setup_storage_directories()
    
    def setup_storage_directories(self):
        """Create necessary storage directories"""
        directories = [
            self.base_storage_path,
            os.path.join(self.base_storage_path, "full"),
            os.path.join(self.base_storage_path, "thumbnails"),
            os.path.join(self.base_storage_path, "daily")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def crop_plate_from_frame(self, frame, bbox):
        """
        Crop plate region from full frame
        
        Args:
            frame: Full frame image (numpy array)
            bbox: Bounding box - can be [x1, y1, x2, y2] or [x, y, width, height]
            
        Returns:
            Cropped plate image (numpy array)
        """
        try:
            if frame is None:
                print("DEBUG: Frame is None in crop_plate_from_frame")
                return None
            
            if bbox is None or len(bbox) != 4:
                print(f"DEBUG: Invalid bbox: {bbox}")
                return None
            
            # Handle both bbox formats: [x1, y1, x2, y2] and [x, y, width, height]
            x1, y1, x2_or_w, y2_or_h = bbox
            
            # Detect format and convert to x1, y1, x2, y2
            if x2_or_w > frame.shape[1] or y2_or_h > frame.shape[0] or x2_or_w < x1 or y2_or_h < y1:
                # Likely [x, y, width, height] format
                x1, y1, width, height = bbox
                x2, y2 = x1 + width, y1 + height
                print(f"DEBUG: Detected [x, y, w, h] format: ({x1}, {y1}, {width}, {height})")
            else:
                # Likely [x1, y1, x2, y2] format
                x2, y2 = x2_or_w, y2_or_h
                print(f"DEBUG: Detected [x1, y1, x2, y2] format: ({x1}, {y1}, {x2}, {y2})")
            
            # Validate coordinates
            if x2 <= x1 or y2 <= y1:
                print(f"DEBUG: Invalid bbox coordinates: ({x1}, {y1}, {x2}, {y2})")
                return None
            
            # Add some padding around the plate
            padding = 5
            x_start = max(0, int(x1 - padding))
            y_start = max(0, int(y1 - padding))
            x_end = min(frame.shape[1], int(x2 + padding))
            y_end = min(frame.shape[0], int(y2 + padding))
            
            # Validate crop coordinates
            if x_start >= x_end or y_start >= y_end:
                print(f"DEBUG: Invalid crop coordinates: ({x_start}, {y_start}) to ({x_end}, {y_end})")
                return None
            
            # Crop the plate region
            plate_crop = frame[y_start:y_end, x_start:x_end]
            
            # Ensure we have a valid crop
            if plate_crop.size == 0:
                print("DEBUG: Cropped plate has zero size")
                return None
                
            print(f"DEBUG: Successfully cropped plate: {plate_crop.shape}")
            return plate_crop
            
        except Exception as e:
            print(f"DEBUG: Error in crop_plate_from_frame: {e}")
            return None
    
    def enhance_plate_image(self, plate_image):
        """
        Enhance plate image for better OCR
        
        Args:
            plate_image: Cropped plate image
            
        Returns:
            Enhanced plate image
        """
        if plate_image is None or plate_image.size == 0:
            return None
            
        try:
            # Convert to grayscale if needed
            if len(plate_image.shape) == 3:
                gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = plate_image.copy()
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Apply bilateral filter to reduce noise while keeping edges sharp
            filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
            
            # Convert back to BGR for consistency
            if len(plate_image.shape) == 3:
                enhanced_bgr = cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)
            else:
                enhanced_bgr = filtered
            
            return enhanced_bgr
        except Exception as e:
            print(f"Error enhancing plate image: {e}")
            return plate_image  # Return original if enhancement fails
    
    def create_thumbnail(self, plate_image):
        """
        Create thumbnail from plate image
        
        Args:
            plate_image: Full plate image
            
        Returns:
            Thumbnail image
        """
        if plate_image is None or plate_image.size == 0:
            return None
            
        try:
            # Convert to PIL Image for better resizing
            if len(plate_image.shape) == 3:
                pil_image = Image.fromarray(cv2.cvtColor(plate_image, cv2.COLOR_BGR2RGB))
            else:
                pil_image = Image.fromarray(plate_image)
        
            # Create thumbnail maintaining aspect ratio
            pil_image.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            # Convert back to OpenCV format
            thumbnail_array = np.array(pil_image)
            if len(thumbnail_array.shape) == 3:
                thumbnail_cv = cv2.cvtColor(thumbnail_array, cv2.COLOR_RGB2BGR)
            else:
                thumbnail_cv = thumbnail_array
            
            return thumbnail_cv
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return plate_image  # Return original if thumbnail creation fails
    
    def generate_filename(self, plate_text, timestamp, raw_id):
        """
        Generate unique filename for plate image
        
        Args:
            plate_text: Detected plate text
            timestamp: Detection timestamp
            raw_id: Raw log ID for uniqueness
            
        Returns:
            Unique filename
        """
        # Clean plate text for filename
        clean_plate = "".join(c for c in plate_text if c.isalnum()).upper()
        
        # Generate timestamp string
        time_str = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Create unique identifier
        unique_str = f"{clean_plate}_{time_str}_{raw_id}"
        hash_suffix = hashlib.md5(unique_str.encode()).hexdigest()[:8]
        
        return f"{clean_plate}_{time_str}_{hash_suffix}"
    
    def save_plate_images(self, frame, bbox, plate_text, timestamp, raw_id):
        """
        Save full plate image and thumbnail
        
        Args:
            frame: Full frame image
            bbox: Plate bounding box
            plate_text: Detected plate text
            timestamp: Detection timestamp
            raw_id: Raw log ID
            
        Returns:
            Dictionary with image paths and metadata
        """
        try:
            # Import required modules at the top
            import cv2
            import numpy as np
            
            # Debug bbox information
            print(f"DEBUG: save_plate_images called with bbox: {bbox}")
            print(f"DEBUG: Frame shape: {frame.shape if frame is not None else 'None'}")
            
            # If frame is None, create a fallback approach
            if frame is None:
                print("DEBUG: Frame is None, using fallback approach")
                # Create a simple placeholder image with the plate text
                fallback_img = np.ones((100, 300, 3), dtype=np.uint8) * 255  # White background
                cv2.putText(fallback_img, plate_text, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                plate_crop = fallback_img
            else:
                # Crop plate from frame
                plate_crop = self.crop_plate_from_frame(frame, bbox)
                if plate_crop is None:
                    print("DEBUG: crop_plate_from_frame returned None")
                    raise ValueError("Failed to crop plate from frame")
            
            # Enhance the plate image (skip if using fallback)
            if frame is not None:
                enhanced_plate = self.enhance_plate_image(plate_crop)
                if enhanced_plate is None:
                    enhanced_plate = plate_crop  # Fallback to original crop
            else:
                enhanced_plate = plate_crop  # Use fallback image as-is
            
            # Create thumbnail
            thumbnail = self.create_thumbnail(enhanced_plate)
            if thumbnail is None:
                thumbnail = enhanced_plate  # Fallback to enhanced plate
            
            # Generate filename
            filename_base = self.generate_filename(plate_text, timestamp, raw_id)
            
            # Create daily subdirectory
            daily_dir = os.path.join(self.base_storage_path, "daily", timestamp.strftime("%Y-%m-%d"))
            os.makedirs(daily_dir, exist_ok=True)
            
            # Save full plate image
            full_image_path = os.path.join(daily_dir, f"{filename_base}_full.jpg")
            cv2.imwrite(full_image_path, enhanced_plate, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Save thumbnail
            thumbnail_path = os.path.join(daily_dir, f"{filename_base}_thumb.jpg")
            cv2.imwrite(thumbnail_path, thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Get image metadata
            height, width = enhanced_plate.shape[:2]
            file_size = os.path.getsize(full_image_path)
            
            return {
                'plate_image_path': os.path.abspath(full_image_path),
                'thumbnail_path': os.path.abspath(thumbnail_path),
                'image_width': width,
                'image_height': height,
                'image_size': file_size,
                'success': True
            }
            
        except Exception as e:
            print(f"Error saving plate images: {e}")
            return {
                'plate_image_path': None,
                'thumbnail_path': None,
                'image_width': None,
                'image_height': None,
                'image_size': None,
                'success': False,
                'error': str(e)
            }
    
    def cleanup_old_images(self, days_to_keep=30):
        """
        Clean up old plate images to save disk space
        
        Args:
            days_to_keep: Number of days to keep images
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            daily_dir = os.path.join(self.base_storage_path, "daily")
            if not os.path.exists(daily_dir):
                return
            
            deleted_count = 0
            for date_folder in os.listdir(daily_dir):
                try:
                    folder_date = datetime.strptime(date_folder, "%Y-%m-%d")
                    if folder_date < cutoff_date:
                        folder_path = os.path.join(daily_dir, date_folder)
                        import shutil
                        shutil.rmtree(folder_path)
                        deleted_count += 1
                except (ValueError, OSError):
                    continue
            
            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} old image folders")
                
        except Exception as e:
            print(f"Error during image cleanup: {e}")
    
    def get_image_info(self, image_path):
        """
        Get information about a stored image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with image information
        """
        try:
            if not os.path.exists(image_path):
                return None
            
            # Read image to get dimensions
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            height, width = image.shape[:2]
            file_size = os.path.getsize(image_path)
            
            return {
                'width': width,
                'height': height,
                'size': file_size,
                'exists': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'exists': False
            }


# Utility functions for easy access
def save_plate_image(frame, bbox, plate_text, timestamp, raw_id, storage_path="plate_images"):
    """
    Convenience function to save plate image
    
    Args:
        frame: Full frame image
        bbox: Plate bounding box (x, y, width, height)
        plate_text: Detected plate text
        timestamp: Detection timestamp
        raw_id: Raw log ID
        storage_path: Base storage path
        
    Returns:
        Dictionary with image paths and metadata
    """
    processor = PlateImageProcessor(storage_path)
    return processor.save_plate_images(frame, bbox, plate_text, timestamp, raw_id)

def create_plate_thumbnail(image_path, thumbnail_path=None):
    """
    Create thumbnail from existing plate image
    
    Args:
        image_path: Path to full plate image
        thumbnail_path: Output path for thumbnail (optional)
        
    Returns:
        Path to created thumbnail
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        processor = PlateImageProcessor()
        thumbnail = processor.create_thumbnail(image)
        
        if thumbnail_path is None:
            base_name = os.path.splitext(image_path)[0]
            thumbnail_path = f"{base_name}_thumb.jpg"
        
        cv2.imwrite(thumbnail_path, thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return thumbnail_path
        
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None
