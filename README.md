# NEPALI ANPR - Automatic Number Plate Recognition System

A professional ANPR system for Nepali license plates with modern UI and high accuracy detection.

## Project Structure

```
NEPALI ANPR/
├── main.py                 # Main application entry point
├── config/
│   └── settings.py         # Configuration settings
├── src/
│   ├── ui/
│   │   ├── __init__.py
│   │   └── main_window.py  # Main UI components
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── vehicle_detector.py  # Vehicle detection using YOLOv8
│   │   └── plate_detector.py    # License plate detection
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── plate_reader.py      # OCR text extraction
│   └── utils/
│       ├── __init__.py
│       ├── image_processing.py  # Image enhancement utilities
│       └── text_processing.py   # Text validation and formatting
├── models/
│   ├── best.pt             # Custom plate detection model
│   └── yolov8n.pt          # Vehicle detection model (auto-downloaded)
├── data/                   # Data storage directory
├── sort/                   # SORT tracking algorithm
└── requirements.txt        # Python dependencies
```

## Features

- **Dual License Plate Formats**:
  - Format 1: AA00AAA (7 characters)
  - Format 2: AA 0101 or AA\n0101 (6 characters)

- **High Accuracy Detection**:
  - YOLOv8 vehicle detection
  - Custom trained plate detection model
  - EasyOCR with format-specific validation

- **Real-time Processing**:
  - SORT multi-object tracking
  - GPU acceleration support
  - Optimized frame processing

- **Professional UI**:
  - Modern dashboard interface
  - Real-time statistics
  - Settings management
  - Results table with plate images

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Application**:
   ```bash
   python main.py
   ```

3. **Upload Video/Image**:
   - Click "Upload Video" or "Upload Image"
   - Select your media file
   - Click Play to start processing

## Configuration

Edit `config/settings.py` to customize:

- Detection thresholds
- OCR settings
- License plate formats
- Debug options

## Debug Mode

To enable debug output, set in `config/settings.py`:
```python
DEBUG_OCR_VERBOSE = True
DEBUG_SAVE_IMAGES = True
```

## Requirements

- Python 3.8+
- PyQt5
- OpenCV
- PyTorch
- Ultralytics YOLO
- EasyOCR
- NumPy

## License

MIT License - See LICENSE file for details.
