# Configuration settings for NEPALI ANPR system

# ===== Model Configuration =====
# Model paths
PLATE_MODEL_PATH = "models/best.pt"
VEHICLE_MODEL_TYPE = "yolov8m"  # Available: yolov8n, yolov8s, yolov8m, yolov8l, yolov8x
VEHICLE_MODEL_PATH = "yolov8m.pt"

# Available plate detection models
AVAILABLE_PLATE_MODELS = ["best.pt"]

# License plate format selection
DEFAULT_LICENSE_FORMAT = "format2"  # Options: format1, format2, format3, auto
AVAILABLE_LICENSE_FORMATS = {
    "format1": "Format 1: AA00AAA (7 characters)",
    "format2": "Format 2: AA 1111 (6 characters)", 
    "format3": "Format 3: A AA 1111 (7 characters)",
    "auto": "Automatic: Try all formats"
}

# Model inference settings
MODEL_IMAGE_SIZE = 416  # YOLO model input size - balanced for speed and accuracy (416 is 1.6x faster than 640)
MODEL_VERBOSE = False   # YOLO model verbose output

# ===== Detection Settings =====
# Confidence thresholds (BALANCED FOR ACCURACY & COVERAGE)
VEHICLE_CONFIDENCE_THRESHOLD = 0.20  # Minimum confidence to detect a vehicle (balanced)
PLATE_CONFIDENCE_THRESHOLD = 0.30    # Minimum confidence to detect a license plate (lowered to catch more)
OCR_CONFIDENCE_THRESHOLD = 0.50      # Minimum confidence for OCR text recognition (lowered to catch more)

# Vehicle classes and their confidence thresholds
VEHICLE_CLASSES = {
    2: 0.4,   # car
    3: 0.25,  # motorcycle
    5: 0.4,   # bus
    7: 0.4,   # truck
    1: 0.3    # bicycle
}

# ===== Video Processing Settings =====
# Frame processing (OPTIMIZED FOR SPEED)
DEFAULT_FRAME_SKIP = 1             # Process every 2nd frame (2x faster, minimal accuracy loss at 30 FPS)
DEFAULT_DETECTION_INTERVAL = 1     # Run detection every N processed frames
FRAME_SKIP_OPTIONS = [1, 2, 3, 4, 5, 10]  # Available frame skip options for UI
VIDEO_FPS = 30                     # Target frames per second for video processing
MAX_FRAME_WIDTH = 1280             # Maximum width for processing (maintains aspect ratio)
MAX_FRAME_HEIGHT = 720             # Maximum height for processing (maintains aspect ratio)

# ===== Tracking Settings =====
# Phase 3: Optimized tracker settings for better vehicle persistence
TRACKER_MAX_AGE = 30               # Keep tracking for 30 frames (~1 sec at 30 FPS) - increased from 5
TRACKER_MIN_HITS = 2               # Require 2 detections before confirming track - increased from 1
TRACKER_IOU_THRESHOLD = 0.3        # IOU threshold for tracking - increased from 0.2 for better matching
TRACKER_TYPE = 'BYTETRACK'         # Default tracker: 'SORT', 'DEEPSORT', or 'BYTETRACK'

# ByteTrack specific defaults
BYTETRACK_TRACK_THRESH = 0.25
BYTETRACK_MATCH_THRESH = 0.8
BYTETRACK_TRACK_BUFFER = 30

# ===== OCR Settings =====
OCR_LANGUAGES = ['en', 'ne']        # Languages for OCR (English and Nepali only)
AVAILABLE_OCR_LANGUAGES = ['en', 'ne']  # Available language options
OCR_GPU_ENABLED = True              # Enable/disable GPU acceleration for OCR
OCR_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"  # Allowed characters in license plates

# ===== Image Processing Settings =====
# Plate detection parameters (BALANCED FOR DETECTION & ACCURACY)
MIN_PLATE_WIDTH = 120              # Minimum width of a license plate in pixels (lowered to catch distant plates)
MIN_PLATE_HEIGHT = 40              # Minimum height of a license plate in pixels (lowered to catch distant plates)
PLATE_RESIZE_SCALE = 3.5           # Scale factor for resizing plates before OCR (increased from 2.0)

# Image enhancement settings (OPTIMIZED FOR PLATE CONTRAST)
ENHANCE_SCALE_FACTOR = 2.0         # Scale factor for image enhancement
CLAHE_CLIP_LIMIT = 3.0             # Contrast Limited Adaptive Histogram Equalization clip limit (increased from 2.0)
CLAHE_TILE_GRID_SIZE = (4, 4)      # Grid size for CLAHE (smaller tiles for better local enhancement)
MORPHOLOGY_KERNEL_SIZE = (1, 1)    # Kernel size for morphological operations
MORPHOLOGY_ITERATIONS = 1          # Number of iterations for morphological operations

# ===== Performance Settings =====
USE_GPU = True                     # Enable/disable GPU acceleration
THREAD_COUNT = 4                   # Number of worker threads for parallel processing
QUEUE_SIZE = 8                     # Maximum size of the processing queue (reduced to prevent overflow)

# ===== UI Settings =====
SHOW_DEBUG_INFO = False            # Show debug information on the UI (reduced verbosity)
DRAW_DETECTIONS = True             # Draw detection bounding boxes
DRAW_TRACKS = True                 # Draw tracking information
DRAW_PLATE_TEXT = True             # Draw recognized plate text

# OCR preprocessing settings
THRESHOLD_VALUE = 64
THRESHOLD_MAX_VALUE = 255
THRESHOLD_TYPE = 'THRESH_BINARY_INV'

# OCR Strategy Parameters
# Format 1 (AA00AAA) OCR parameters
OCR_FORMAT1_STANDARD_WIDTH_THS = 0.1
OCR_FORMAT1_STANDARD_HEIGHT_THS = 0.1
OCR_FORMAT1_STANDARD_MIN_SIZE = 5

OCR_FORMAT1_RELAXED_WIDTH_THS = 0.05
OCR_FORMAT1_RELAXED_HEIGHT_THS = 0.05
OCR_FORMAT1_RELAXED_MIN_SIZE = 3

# Format 2 (AA 0101) OCR parameters
OCR_FORMAT2_PARAGRAPH_WIDTH_THS = 0.05
OCR_FORMAT2_PARAGRAPH_HEIGHT_THS = 0.05

OCR_FORMAT2_STANDARD_WIDTH_THS = 0.05
OCR_FORMAT2_STANDARD_HEIGHT_THS = 0.05
OCR_FORMAT2_STANDARD_MIN_SIZE = 3

OCR_FORMAT2_PERMISSIVE_WIDTH_THS = 0.01
OCR_FORMAT2_PERMISSIVE_HEIGHT_THS = 0.01
OCR_FORMAT2_PERMISSIVE_MIN_SIZE = 1

# Plate finalization settings (BALANCED FOR ACCURACY & COVERAGE)
MIN_DETECTIONS_FOR_FINAL = 1       # Require at least 1 detection (lowered to catch more vehicles)
CONFIDENCE_THRESHOLD_FINAL = 0.55  # Final plate must have 55%+ confidence (lowered to catch more)
IMMEDIATE_FINALIZATION_THRESHOLD = 0.70  # High confidence plates finalized immediately (lowered to catch more)

# Performance settings (OPTIMIZED FOR SPEED)
MAX_HISTORY_FRAMES = 8             # Reduced from 10 for faster processing
MAX_CANDIDATES_PER_VEHICLE = 8     # Increased from 5 for better consensus (more samples)

# Debug settings (disable in production for better performance)
DEBUG_SAVE_IMAGES = False  # Set to True only for debugging OCR issues
DEBUG_OCR_VERBOSE = False  # Set to True only for debugging OCR issues

# ===== Parking Fee Settings =====
# Hourly rate for parking fee calculation (in NPR)
PARKING_HOURLY_RATE = 50.0  # 50 NPR per hour
MINIMUM_CHARGE_HOURS = 1.0  # Minimum charge for 1 hour even for shorter durations
