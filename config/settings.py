# Configuration settings for NEPALI ANPR system

# ===== Model Configuration =====
# Model paths
PLATE_MODEL_PATH = "models/best.pt"
VEHICLE_MODEL_TYPE = "yolov8m"  # Available: yolov8n, yolov8s, yolov8m, yolov8l, yolov8x
VEHICLE_MODEL_PATH = "yolov8m.pt"

# Model inference settings
MODEL_IMAGE_SIZE = 320  # YOLO model input image size (reduced for faster inference)
MODEL_VERBOSE = False   # YOLO model verbose output

# ===== Detection Settings =====
# Confidence thresholds
VEHICLE_CONFIDENCE_THRESHOLD = 0.15  # Minimum confidence to detect a vehicle
PLATE_CONFIDENCE_THRESHOLD = 0.15    # Minimum confidence to detect a license plate
OCR_CONFIDENCE_THRESHOLD = 0.05      # Minimum confidence for OCR text recognition

# Vehicle classes and their confidence thresholds
VEHICLE_CLASSES = {
    2: 0.4,   # car
    3: 0.25,  # motorcycle
    5: 0.4,   # bus
    7: 0.4,   # truck
    1: 0.3    # bicycle
}

# ===== Video Processing Settings =====
# Frame processing
DEFAULT_FRAME_SKIP = 1             # Process every N frames to improve performance
DEFAULT_DETECTION_INTERVAL = 1     # Run detection every N processed frames
VIDEO_FPS = 30                     # Target frames per second for video processing
MAX_FRAME_WIDTH = 1280             # Maximum width for processing (maintains aspect ratio)
MAX_FRAME_HEIGHT = 720             # Maximum height for processing (maintains aspect ratio)

# ===== Tracking Settings =====
TRACKER_MAX_AGE = 5                # Number of frames to keep a tracker alive without detection
TRACKER_MIN_HITS = 1               # Minimum number of detections before a track is confirmed
TRACKER_IOU_THRESHOLD = 0.2       # IOU threshold for tracking (lower for more sensitive matching)
TRACKER_TYPE = 'BYTETRACK'         # Default tracker: 'SORT', 'DEEPSORT', or 'BYTETRACK'

# ByteTrack specific defaults
BYTETRACK_TRACK_THRESH = 0.25
BYTETRACK_MATCH_THRESH = 0.8
BYTETRACK_TRACK_BUFFER = 30
MIN_DETECTIONS_FOR_FINAL = 3       # Minimum number of detections before considering a plate as final
CONFIDENCE_THRESHOLD_FINAL = 0.7   # Minimum confidence threshold to consider a plate as final

# ===== OCR Settings =====
OCR_LANGUAGES = ['en']              # Languages for OCR
OCR_GPU_ENABLED = True              # Enable/disable GPU acceleration for OCR
OCR_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"  # Allowed characters in license plates

# ===== Image Processing Settings =====
# Plate detection parameters
MIN_PLATE_WIDTH = 100              # Minimum width of a license plate in pixels
MIN_PLATE_HEIGHT = 30              # Minimum height of a license plate in pixels
PLATE_RESIZE_SCALE = 2.0           # Scale factor for resizing plates before OCR

# Image enhancement settings
ENHANCE_SCALE_FACTOR = 2.0         # Scale factor for image enhancement
CLAHE_CLIP_LIMIT = 2.0             # Contrast Limited Adaptive Histogram Equalization clip limit
CLAHE_TILE_GRID_SIZE = (8, 8)      # Grid size for CLAHE
MORPHOLOGY_KERNEL_SIZE = (1, 1)    # Kernel size for morphological operations
MORPHOLOGY_ITERATIONS = 1          # Number of iterations for morphological operations

# ===== Performance Settings =====
USE_GPU = True                     # Enable/disable GPU acceleration
THREAD_COUNT = 4                   # Number of worker threads for parallel processing
QUEUE_SIZE = 32                    # Maximum size of the processing queue

# ===== UI Settings =====
SHOW_DEBUG_INFO = True             # Show debug information on the UI
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

# Plate finalization settings
MIN_DETECTIONS_FOR_FINAL = 1
CONFIDENCE_THRESHOLD_FINAL = 0.1
IMMEDIATE_FINALIZATION_THRESHOLD = 0.1

# Performance settings
MAX_HISTORY_FRAMES = 10
MAX_CANDIDATES_PER_VEHICLE = 5

# Debug settings
DEBUG_SAVE_IMAGES = True
DEBUG_OCR_VERBOSE = True
