# NEPALI ANPR - Automatic Number Plate Recognition System

A professional ANPR system for Nepali license plates with modern UI, database logging, and intelligent vehicle tracking.

## Project Structure

```
NEPALI ANPR/
├── main.py                 # Main application entry point
├── config/
│   ├── settings.py         # Configuration settings
│   └── license_formats.py  # License plate format definitions
├── src/
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py  # Main UI components
│   │   ├── dashboard_page.py  # Dashboard with statistics
│   │   ├── database_page.py   # Database viewer and management
│   │   ├── settings_page.py   # Settings configuration
│   │   └── components/        # UI components
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── vehicle_detector.py  # Vehicle detection using YOLOv8
│   │   └── plate_detector.py    # License plate detection
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── plate_reader.py      # Enhanced OCR with format validation
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py          # Database connection and operations
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── toggle_manager.py    # Smart entry/exit detection
│   │   └── schema.sql           # Database schema
│   └── threading/
│       └── frame_worker.py      # Multi-threaded frame processing
├── models/                 # YOLO model files (auto-downloaded)
├── tests/                  # Test files and utilities
└── requirements.txt        # Python dependencies
```

## Features

### 🚗 **Advanced Vehicle Detection & Tracking**
- **YOLOv8-powered detection** with multiple model sizes (n/m/l/x)
- **Multi-object tracking** with unique vehicle IDs
- **Real-time processing** with threaded frame handling
- **GPU acceleration** support for enhanced performance

### 🔤 **Intelligent License Plate Recognition**
- **Dual format support**:
  - Format 1: AA00AAA (7 characters) - Standard format
  - Format 2: AA 0101 (6 characters) - Compact format
- **Enhanced OCR** with EasyOCR and format-specific validation
- **Confidence-based filtering** and text variation matching
- **Debug mode** with plate image saving for analysis

### 🗄️ **Smart Database System**
- **SQLAlchemy ORM** with comprehensive data models
- **Toggle mode detection** - Automatic ENTRY/EXIT logging
- **Fuzzy matching** for similar plate numbers (80% similarity)
- **Session tracking** with duration calculations
- **Real-time statistics** and data visualization

### 🖥️ **Modern User Interface**
- **Multi-tab interface** with Dashboard, Database, and Settings
- **Real-time counters** and performance metrics
- **Database viewer** with filtering and search capabilities
- **Auto-refresh** functionality for live data updates
- **Responsive design** with professional styling

## Quick Start

### 🚀 **Installation**
1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd NEPALI-ANPR
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database**:
   ```bash
   python init_database.py
   ```

4. **Run Application**:
   ```bash
   python main.py
   ```

### 📹 **Usage**
1. **Upload Video**: Click "Upload Video" and select your video file
2. **Start Processing**: Click "Play" to begin vehicle detection and plate recognition
3. **Monitor Dashboard**: View real-time statistics and detection results
4. **Check Database**: Switch to Database tab to view logged vehicle entries/exits
5. **Configure Settings**: Adjust detection thresholds and OCR parameters in Settings tab

## Configuration

### 📁 **Settings Files**
- `config/settings.py` - Main application settings
- `config/license_formats.py` - License plate format definitions

### ⚙️ **Key Configuration Options**
```python
# Detection settings
VEHICLE_CONFIDENCE_THRESHOLD = 0.5
PLATE_CONFIDENCE_THRESHOLD = 0.7
OCR_CONFIDENCE_THRESHOLD = 0.8

# Database settings
TOGGLE_COOLDOWN_MINUTES = 2
EXIT_SIMILARITY_THRESHOLD = 0.8

# Debug options
DEBUG_OCR_VERBOSE = True
DEBUG_SAVE_IMAGES = True
```

## Database Schema

### 📊 **Core Tables**
- **`vehicles`** - Vehicle registry with plate numbers
- **`cameras`** - Camera information and locations
- **`raw_logs`** - All detections before filtering
- **`vehicle_log`** - Filtered entry/exit records with toggle mode

### 🔄 **Toggle Mode Logic**
- **ENTRY**: First detection or after EXIT with cooldown
- **EXIT**: Detection after ENTRY with cooldown period
- **Fuzzy Matching**: Links similar plates (80% similarity) for EXIT detection

## System Requirements

### 💻 **Hardware**
- **CPU**: Multi-core processor (Intel i5+ or AMD Ryzen 5+)
- **RAM**: 8GB minimum, 16GB recommended
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended)
- **Storage**: 2GB free space for models and logs

### 🐍 **Software**
- **Python**: 3.8+ (3.9+ recommended)
- **Operating System**: Windows 10+, macOS 10.14+, or Linux Ubuntu 18.04+

## Troubleshooting

### 🔧 **Common Issues**
- **Model Download**: First run downloads YOLO models (~500MB)
- **GPU Support**: Install CUDA-compatible PyTorch for GPU acceleration
- **Database Errors**: Run `python init_database.py` to reset database
- **OCR Issues**: Ensure proper lighting and plate visibility in videos

## License

MIT License - See LICENSE file for details.
