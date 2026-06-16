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

class PlateImageProcessor:
    """Handles plate image processing and storage"""

    def __init__(self, base_storage_path="plate_images"):
        self.base_storage_path = base_storage_path
        self.thumbnail_size = (150, 50)
        self._temp_dir = None  # set via set_temp_dir() before first detection
        # Create CLAHE once and reuse — cv2.createCLAHE() allocation is not free
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        # Cache the last daily directory to avoid os.makedirs on every save
        self._last_daily_dir = None
        self.setup_storage_directories()

    def set_temp_dir(self, path):
        """Point the processor at the session temp directory for candidate images."""
        self._temp_dir = path
        os.makedirs(path, exist_ok=True)

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
        Crop plate region from full frame.

        Args:
            frame: Full frame image (numpy array)
            bbox: Bounding box — [x1, y1, x2, y2] or [x, y, width, height]

        Returns:
            Cropped plate image (numpy array) or None
        """
        try:
            if frame is None or bbox is None or len(bbox) != 4:
                return None

            x1, y1, x2_or_w, y2_or_h = bbox

            # Detect format and normalise to x1, y1, x2, y2
            if x2_or_w > frame.shape[1] or y2_or_h > frame.shape[0] or x2_or_w < x1 or y2_or_h < y1:
                x1, y1, width, height = bbox
                x2, y2 = x1 + width, y1 + height
            else:
                x2, y2 = x2_or_w, y2_or_h

            if x2 <= x1 or y2 <= y1:
                return None

            padding = 5
            x_start = max(0, int(x1 - padding))
            y_start = max(0, int(y1 - padding))
            x_end   = min(frame.shape[1], int(x2 + padding))
            y_end   = min(frame.shape[0], int(y2 + padding))

            if x_start >= x_end or y_start >= y_end:
                return None

            plate_crop = frame[y_start:y_end, x_start:x_end]
            return plate_crop if plate_crop.size > 0 else None

        except Exception:
            return None

    def enhance_plate_image(self, plate_image):
        """
        Enhance plate image contrast and reduce noise.

        Args:
            plate_image: Cropped plate image

        Returns:
            Enhanced plate image
        """
        if plate_image is None or plate_image.size == 0:
            return None

        try:
            gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY) \
                   if len(plate_image.shape) == 3 else plate_image.copy()

            enhanced = self._clahe.apply(gray)

            # d=5 is 3× faster than d=9 (O(d²)) with no perceptible quality loss
            # on small plate crops
            filtered = cv2.bilateralFilter(enhanced, 5, 75, 75)

            return cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR) \
                   if len(plate_image.shape) == 3 else filtered

        except Exception as e:
            print(f"Error enhancing plate image: {e}")
            return plate_image

    def create_thumbnail(self, plate_image):
        """
        Create thumbnail image from plate image.

        Args:
            plate_image: Plate image to thumbnail

        Returns:
            Thumbnail image
        """
        if plate_image is None or plate_image.size == 0:
            return None

        try:
            if len(plate_image.shape) == 3:
                pil_image = Image.fromarray(cv2.cvtColor(plate_image, cv2.COLOR_BGR2RGB))
            else:
                pil_image = Image.fromarray(plate_image)

            pil_image.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)

            thumbnail_array = np.array(pil_image)
            return cv2.cvtColor(thumbnail_array, cv2.COLOR_RGB2BGR) \
                   if len(thumbnail_array.shape) == 3 else thumbnail_array

        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return plate_image

    def generate_filename(self, plate_text, timestamp, raw_id):
        """Generate unique filename for a plate image."""
        clean_plate = "".join(c for c in plate_text if c.isalnum()).upper()
        time_str = timestamp.strftime("%Y%m%d_%H%M%S")
        # 4 random bytes → 8 hex chars, faster than MD5 and equally unique
        unique_suffix = os.urandom(4).hex()
        return f"{clean_plate}_{time_str}_{unique_suffix}"

    def _get_daily_dir(self, base_path, timestamp):
        """Return the daily storage directory, creating it only when the date changes."""
        daily_dir = os.path.join(base_path, "daily", timestamp.strftime("%Y-%m-%d"))
        if daily_dir != self._last_daily_dir:
            os.makedirs(daily_dir, exist_ok=True)
            self._last_daily_dir = daily_dir
        return daily_dir

    def save_plate_images(self, frame, bbox, plate_text, timestamp, raw_id):
        """
        Save full plate image and thumbnail.

        Returns:
            Dictionary with image paths and metadata, or failure dict.
        """
        try:
            if frame is None:
                fallback = np.ones((100, 300, 3), dtype=np.uint8) * 255
                cv2.putText(fallback, plate_text, (10, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
                plate_crop = fallback
            else:
                plate_crop = self.crop_plate_from_frame(frame, bbox)
                if plate_crop is None:
                    raise ValueError("Failed to crop plate from frame")

            enhanced_plate = self.enhance_plate_image(plate_crop) if frame is not None else plate_crop
            if enhanced_plate is None:
                enhanced_plate = plate_crop

            thumbnail = self.create_thumbnail(enhanced_plate) or enhanced_plate

            filename_base = self.generate_filename(plate_text, timestamp, raw_id)
            daily_dir = self._get_daily_dir(self.base_storage_path, timestamp)

            full_image_path = os.path.join(daily_dir, f"{filename_base}_full.jpg")
            thumbnail_path  = os.path.join(daily_dir, f"{filename_base}_thumb.jpg")

            cv2.imwrite(full_image_path, enhanced_plate, [cv2.IMWRITE_JPEG_QUALITY, 95])
            cv2.imwrite(thumbnail_path,  thumbnail,      [cv2.IMWRITE_JPEG_QUALITY, 85])

            height, width = enhanced_plate.shape[:2]
            file_size = os.path.getsize(full_image_path)

            return {
                'plate_image_path': os.path.abspath(full_image_path),
                'thumbnail_path':   os.path.abspath(thumbnail_path),
                'image_width':  width,
                'image_height': height,
                'image_size':   file_size,
                'success': True
            }

        except Exception as e:
            print(f"Error saving plate images: {e}")
            return {
                'plate_image_path': None,
                'thumbnail_path':   None,
                'image_width':  None,
                'image_height': None,
                'image_size':   None,
                'success': False,
                'error': str(e)
            }

    def save_temp_plate_image(self, frame, bbox, plate_text, timestamp, raw_id):
        """Save candidate plate images to the session temp directory instead of permanent storage."""
        if self._temp_dir:
            original = self.base_storage_path
            self.base_storage_path = self._temp_dir
            result = self.save_plate_images(frame, bbox, plate_text, timestamp, raw_id)
            self.base_storage_path = original
            return result
        return self.save_plate_images(frame, bbox, plate_text, timestamp, raw_id)

    def promote_to_permanent(self, image_data):
        """
        Move the finalized plate images from temp to permanent storage.
        Returns updated image_data with the new permanent paths.
        """
        import shutil
        if not image_data or not image_data.get('success'):
            return image_data

        updated = dict(image_data)
        for key in ('plate_image_path', 'thumbnail_path'):
            src = image_data.get(key)
            if not src or not os.path.isfile(src):
                continue
            filename = os.path.basename(src)
            daily_dir = self._get_daily_dir(self.base_storage_path, datetime.now())
            dst = os.path.join(daily_dir, filename)
            try:
                shutil.move(src, dst)
                updated[key] = os.path.abspath(dst)
            except Exception as e:
                print(f"Could not promote image {src}: {e}")
        return updated

    def cleanup_old_images(self, days_to_keep=30):
        """Clean up old plate images to save disk space."""
        try:
            from datetime import timedelta
            import shutil
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            daily_dir = os.path.join(self.base_storage_path, "daily")
            if not os.path.exists(daily_dir):
                return
            deleted_count = 0
            for date_folder in os.listdir(daily_dir):
                try:
                    folder_date = datetime.strptime(date_folder, "%Y-%m-%d")
                    if folder_date < cutoff_date:
                        shutil.rmtree(os.path.join(daily_dir, date_folder))
                        deleted_count += 1
                except (ValueError, OSError):
                    continue
            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} old image folders")
        except Exception as e:
            print(f"Error during image cleanup: {e}")

    def get_image_info(self, image_path):
        """Get metadata for a stored image."""
        try:
            if not os.path.exists(image_path):
                return None
            img = cv2.imread(image_path)
            if img is None:
                return None
            height, width = img.shape[:2]
            return {
                'path': image_path,
                'width': width,
                'height': height,
                'size': os.path.getsize(image_path),
                'exists': True
            }
        except Exception as e:
            print(f"Error getting image info: {e}")
            return None

    def create_thumbnail_from_path(self, image_path, output_path=None):
        """Create a thumbnail from an existing image file."""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            thumbnail = self.create_thumbnail(img)
            if thumbnail is None:
                return None
            if output_path is None:
                base, ext = os.path.splitext(image_path)
                output_path = f"{base}_thumb{ext}"
            cv2.imwrite(output_path, thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return output_path
        except Exception as e:
            print(f"Error creating thumbnail from path: {e}")
            return None


def save_plate_image(frame, bbox, plate_text, timestamp, raw_id, storage_path="plate_images"):
    """Module-level convenience wrapper."""
    processor = PlateImageProcessor(base_storage_path=storage_path)
    return processor.save_plate_images(frame, bbox, plate_text, timestamp, raw_id)
