# 🚗 NEPALI ANPR - Automatic Number Plate Recognition System

**A comprehensive, production-ready ANPR system for Nepali license plates with advanced AI detection, intelligent tracking, role-based access control, and comprehensive analytics.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)](https://pypi.org/project/PyQt5/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🌟 Key Highlights

- ✅ **Real-time Detection**: YOLOv8-powered vehicle and plate detection
- ✅ **Multi-Camera Support**: Built-in webcam, USB cameras, and DroidCam IP streaming
- ✅ **Intelligent Tracking**: ByteTrack algorithm for vehicle tracking across frames
- ✅ **Smart Entry/Exit**: Automatic toggle mode detection with fuzzy matching
- ✅ **Role-Based Access**: Complete RBAC system with user management
- ✅ **Advanced Analytics**: Comprehensive reporting with PDF/Excel export
- ✅ **Modern UI**: Professional PyQt5 interface with dark theme
- ✅ **Image Storage**: Automatic plate image capture and storage
- ✅ **Parking Management**: Duration tracking and revenue calculation

## 📁 Project Structure

```
NEPALI ANPR/
├── main.py                      # Main application entry point
├── init_unified_database.py     # Database initialization script
├── init_rbac_system.py          # RBAC system initialization
│
├── config/
│   ├── settings.py              # Global configuration settings
│   └── license_formats.py       # License plate format definitions
│
├── src/
│   ├── analytics/               # Analytics and reporting engine
│   │   ├── analytics_engine.py  # Data analysis and forecasting
│   │   └── export_utils.py      # PDF/Excel export utilities
│   │
│   ├── auth/                    # Authentication and authorization
│   │   ├── auth_manager.py      # User authentication manager
│   │   └── rbac_ui_controller.py # UI permission controller
│   │
│   ├── db/                      # Database layer
│   │   ├── database.py          # Database connection and operations
│   │   ├── models.py            # SQLAlchemy ORM models (14 tables)
│   │   └── toggle_manager.py    # Smart entry/exit detection logic
│   │
│   ├── detection/               # AI detection modules
│   │   ├── vehicle_detector.py  # YOLOv8 vehicle detection
│   │   └── plate_detector.py    # License plate detection
│   │
│   ├── ocr/                     # OCR processing
│   │   └── plate_reader.py      # EasyOCR with format validation
│   │
│   ├── threading/               # Multi-threading
│   │   └── frame_worker.py      # Parallel frame processing
│   │
│   ├── tracking/                # Vehicle tracking
│   │   └── ByteTrack/           # ByteTrack algorithm integration
│   │
│   ├── ui/                      # User interface
│   │   ├── main_window.py       # Main application window
│   │   ├── login_dialog.py      # Login authentication UI
│   │   ├── user_management_page.py # User management interface
│   │   ├── analytics_page.py    # Analytics dashboard
│   │   ├── search_plate_page.py # Vehicle search interface
│   │   ├── settings_page.py     # Settings configuration
│   │   ├── ui_styles.py         # Modern UI styling system
│   │   └── ui_components.py     # Reusable UI components
│   │
│   └── utils/                   # Utility modules
│       └── image_processor.py   # Image processing utilities
│
├── models/                      # AI models (auto-downloaded)
│   ├── yolov8n.pt              # YOLOv8 nano model
│   └── best.pt                 # Custom plate detection model
│
├── data/                        # Data storage
│   ├── anpr_system.db          # SQLite database
│   ├── plate_images/           # Captured plate images
│   └── reports/                # Generated reports
│
└── requirements.txt             # Python dependencies
```

## ✨ Features

### 🚗 **Advanced Vehicle Detection & Tracking**
- **YOLOv8 AI Detection**: State-of-the-art object detection with multiple model sizes
- **ByteTrack Algorithm**: Robust multi-object tracking with unique vehicle IDs
- **Real-time Processing**: Multi-threaded frame handling for smooth performance
- **GPU Acceleration**: CUDA support for enhanced processing speed
- **Smart Re-identification**: Handles occlusions and temporary disappearances

### 🔤 **Intelligent License Plate Recognition**
- **Dual Format Support**:
  - Format 1: `AA00AAA` (7 characters) - Standard Nepali format
  - Format 2: `AA 0101` (6 characters) - Compact format
  - Partial plate detection (4-digit minimum)
- **Enhanced OCR**: EasyOCR with format-specific validation
- **Confidence Filtering**: Multi-level confidence thresholds
- **Text Variation Matching**: Handles OCR inconsistencies
- **Image Capture**: Automatic plate image and thumbnail storage

### 🗄️ **Smart Database System**
- **14 Comprehensive Tables**: Complete data model with relationships
- **Toggle Mode Detection**: Intelligent ENTRY/EXIT logging
- **Fuzzy Matching**: 80% similarity threshold for plate matching
- **Duration Tracking**: Automatic parking duration calculation
- **Revenue Calculation**: Configurable hourly rate (NPR 50/hour default)
- **Plate Edit History**: Complete audit trail for all modifications
- **Image Storage**: Plate images with metadata (dimensions, size, paths)

### 👥 **Role-Based Access Control (RBAC)**
- **4 User Roles**: SUPERADMIN, ADMIN, OPERATOR, VIEWER
- **14 Granular Permissions**: Fine-grained access control
- **User Management**: Create, edit, delete users with role assignment
- **Session Management**: Secure login/logout with session tracking
- **Permission-Based UI**: Dynamic interface based on user permissions
- **Audit Logging**: Track all user actions and changes

### 📊 **Advanced Analytics & Reporting**
- **Dashboard Metrics**: Real-time entries, exits, occupancy, revenue
- **Trend Analysis**: Daily/weekly/monthly traffic patterns
- **Peak Hour Detection**: Identify busiest hours and days
- **Revenue Analytics**: Total, average, maximum revenue tracking
- **Demand Forecasting**: 7/14/30-day predictions using moving averages
- **Usage Patterns**: Average duration, exit rate, occupancy analysis
- **PDF Export**: Professional reports with charts and tables
- **Excel Export**: Multi-sheet workbooks with formatted data

### 🖥️ **Modern User Interface**
- **Professional Design**: Dark theme with modern color palette
- **7 Main Pages**: Dashboard, Vehicle Log, User Management, Analytics, Search, Settings, Logout
- **Responsive Layouts**: Scroll areas and adaptive sizing
- **Real-time Updates**: Live counters and statistics
- **Interactive Charts**: Matplotlib-powered visualizations
- **Search & Filter**: Advanced search with date range and filters
- **Plate Editing**: Double-click editing with permission checks

### 📹 **Multi-Camera Support**
- **Built-in Webcam**: Automatic detection of system cameras
- **USB Cameras**: Support for external USB webcams
- **DroidCam USB**: Dedicated support for DroidCam USB connections
- **DroidCam IP**: Wireless streaming from mobile devices
- **Camera Selection**: Dropdown with resolution and FPS info
- **Live Preview**: Real-time video feed with detection overlay

### 🔧 **Advanced Configuration**
- **Model Settings**: Choose YOLOv8 model size and plate detection model
- **Detection Thresholds**: Configurable confidence levels
- **OCR Settings**: OCR model and confidence threshold
- **Performance Tuning**: Thread count, GPU acceleration, batch size
- **Video Processing**: Frame skip and processing settings
- **Parking Fees**: Hourly rate and minimum charge configuration

## 🚀 Quick Start

### 📦 **Installation**

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd NEPALI-ANPR
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database** (First time only):
   ```bash
   python init_unified_database.py
   ```

4. **Initialize RBAC System** (First time only):
   ```bash
   python init_rbac_system.py
   ```
   This creates the default admin user:
   - **Username**: `admin`
   - **Password**: `admin123`
   - **Role**: SUPERADMIN

5. **Run Application**:
   ```bash
   python main.py
   ```

### 🎯 **First-Time Setup**

1. **Login**: Use default credentials (`admin` / `admin123`)
2. **Change Password**: Go to User Management and update admin password
3. **Create Users**: Add users with appropriate roles
4. **Configure Settings**: Adjust detection thresholds and parking rates
5. **Test Camera**: Try live camera or upload a test video

### 📹 **Usage Guide**

#### **Dashboard Operations**
1. **Upload Image**: Click "Upload Image" for single image processing
2. **Upload Video**: Click "Upload Video" for video file processing
3. **Live Camera**: Click "Start Live Camera" for real-time detection
4. **Playback Controls**: Use Play/Pause/Stop/Frame+/Frame- buttons
5. **Monitor Stats**: View real-time counters and detected plates

#### **Vehicle Log**
- View all detected vehicles with entry/exit records
- See plate images, timestamps, and durations
- Track parking fees and revenue
- Filter by date range and vehicle type

#### **User Management** (Admin/SuperAdmin only)
- Create new users with specific roles
- Edit user information and roles
- Delete users (except yourself)
- View last login times

#### **Analytics Dashboard**
- **Dashboard Tab**: Summary cards, peak hours, usage patterns
- **Trends Tab**: Daily/weekly/monthly traffic analysis
- **Revenue Tab**: Revenue breakdown and charts
- **Forecast Tab**: Demand and revenue predictions
- **Export**: Generate PDF or Excel reports

#### **Search Plate**
- Search by plate number (partial search supported)
- Filter by movement type (ENTRY/EXIT)
- Date range filtering
- View plate images and details
- Edit plate numbers (with permissions)

#### **Settings**
- **Model**: Choose YOLOv8 and plate detection models
- **Detection**: Adjust confidence thresholds
- **OCR**: Configure OCR settings
- **Performance**: Tune thread count and GPU settings
- **Video**: Set frame skip for performance
- **Parking Fees**: Configure hourly rates

## ⚙️ Configuration

### 📁 **Settings Files**
- `config/settings.py` - Main application settings
- `config/license_formats.py` - License plate format definitions

### 🔧 **Key Configuration Options**
```python
# Detection Settings
VEHICLE_CONFIDENCE_THRESHOLD = 0.5      # Vehicle detection confidence
PLATE_CONFIDENCE_THRESHOLD = 0.7        # Plate detection confidence  
OCR_CONFIDENCE_THRESHOLD = 0.8          # OCR text confidence
IMMEDIATE_FINALIZATION_THRESHOLD = 0.95 # Auto-finalize threshold

# Database Settings
TOGGLE_COOLDOWN_MINUTES = 2             # Cooldown between ENTRY/EXIT
EXIT_SIMILARITY_THRESHOLD = 0.8         # Fuzzy matching threshold
DATABASE_PATH = "data/anpr_system.db"   # SQLite database location

# Parking Fee Settings
PARKING_HOURLY_RATE = 50.0              # NPR per hour
MINIMUM_CHARGE_HOURS = 1.0              # Minimum billing period

# Performance Settings
FRAME_SKIP = 2                          # Process every Nth frame
MAX_WORKERS = 4                         # Thread pool size
BATCH_SIZE = 1                          # Detection batch size

# Image Storage
SAVE_PLATE_IMAGES = True                # Save detected plate images
IMAGE_STORAGE_PATH = "data/plate_images/"
THUMBNAIL_SIZE = (200, 100)             # Thumbnail dimensions

# Debug Options
DEBUG_OCR_VERBOSE = True                # Detailed OCR logging
DEBUG_SAVE_IMAGES = True                # Save debug images
```

## 🗄️ Database Schema

### 📊 **14 Comprehensive Tables**

#### **Core Tables**
1. **`vehicles`** - Vehicle registry with plate numbers
2. **`cameras`** - Camera information and locations  
3. **`raw_logs`** - All detections before filtering (with images)
4. **`vehicle_log`** - Filtered entry/exit records with toggle mode

#### **RBAC Tables**
5. **`users`** - User accounts with authentication
6. **`roles`** - Role definitions (SUPERADMIN, ADMIN, OPERATOR, VIEWER)
7. **`permissions`** - Permission definitions (14 permissions)
8. **`role_permissions`** - Role-permission mappings
9. **`user_roles`** - User-role assignments
10. **`user_sessions`** - Active user sessions
11. **`audit_logs`** - User action audit trail

#### **Additional Tables**
12. **`plate_edit_history`** - Plate number edit audit trail
13. **`vehicle_types`** - Vehicle classification
14. **`parking_sessions`** - Detailed parking session tracking

### 🔄 **Toggle Mode Logic**
- **ENTRY**: First detection or after EXIT with cooldown period
- **EXIT**: Detection after ENTRY with cooldown elapsed
- **Fuzzy Matching**: Links similar plates (80% similarity) for EXIT
- **Duration Calculation**: Automatic time difference calculation
- **Revenue Calculation**: Based on duration and hourly rate
- **Re-evaluation**: Handles OCR corrections and misreads

### 📸 **Image Storage**
- **Plate Images**: Full-resolution captured plates
- **Thumbnails**: Scaled-down versions for UI display
- **Metadata**: Width, height, file size, paths stored in database
- **Automatic Cleanup**: Old images can be archived/deleted

## 💻 System Requirements

### 🖥️ **Hardware**
- **CPU**: Multi-core processor (Intel i5+ or AMD Ryzen 5+)
- **RAM**: 8GB minimum, 16GB recommended for analytics
- **GPU**: NVIDIA GPU with CUDA support (optional but highly recommended)
- **Storage**: 5GB free space (models, database, images, reports)
- **Camera**: USB webcam or IP camera (for live detection)

### 🐍 **Software**
- **Python**: 3.8+ (3.9 or 3.10 recommended)
- **Operating System**: 
  - Windows 10/11 (tested)
  - macOS 10.14+ (compatible)
  - Linux Ubuntu 18.04+ (compatible)

## 📦 Dependencies

### **Core Dependencies**
```
PyQt5>=5.15.0                # GUI framework
ultralytics>=8.0.0           # YOLOv8 detection
easyocr>=1.6.0              # OCR engine
opencv-python>=4.5.0         # Computer vision
SQLAlchemy>=1.4.0           # ORM and database
bcrypt>=3.2.0               # Password hashing
```

### **Analytics Dependencies**
```
matplotlib>=3.5.0            # Charts and visualizations
numpy>=1.21.0               # Numerical computing
reportlab>=3.6.0            # PDF generation
openpyxl>=3.0.0             # Excel export
```

### **Additional Dependencies**
```
torch>=1.10.0               # PyTorch for AI models
torchvision>=0.11.0         # Vision utilities
Pillow>=8.0.0               # Image processing
difflib                     # Fuzzy string matching
```

## 🔧 Troubleshooting

### **Common Issues**

#### **Installation Issues**
- **Model Download Fails**: 
  - First run downloads YOLOv8 models (~500MB)
  - Ensure stable internet connection
  - Models stored in `models/` directory

- **Dependency Conflicts**:
  ```bash
  pip install --upgrade pip
  pip install -r requirements.txt --force-reinstall
  ```

#### **Runtime Issues**
- **GPU Not Detected**:
  - Install CUDA-compatible PyTorch: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`
  - Verify CUDA installation: `nvidia-smi`

- **Database Errors**:
  ```bash
  # Reset database
  python init_unified_database.py
  python init_rbac_system.py
  ```

- **OCR Issues**:
  - Ensure good lighting and plate visibility
  - Adjust OCR confidence threshold in settings
  - Check plate format matches configured formats

- **Camera Not Working**:
  - Check camera permissions
  - Try different camera indices (0, 1, 2...)
  - For DroidCam IP, ensure same network and correct IP/port

#### **Performance Issues**
- **Slow Processing**:
  - Increase frame skip in settings
  - Use smaller YOLO model (yolov8n)
  - Enable GPU acceleration
  - Reduce thread count if CPU overloaded

- **High Memory Usage**:
  - Reduce batch size
  - Lower video resolution
  - Clear old plate images periodically

#### **UI Issues**
- **Buttons Not Visible**:
  - Restart application
  - Check screen resolution (minimum 1280x720)
  - Maximize window for full view

- **Charts Not Displaying**:
  - Install matplotlib: `pip install matplotlib`
  - Check Analytics page for error messages

## 👥 User Roles & Permissions

### **Role Hierarchy**
1. **SUPERADMIN**: Full system access, cannot be deleted
2. **ADMIN**: User management, all features except SUPERADMIN deletion
3. **OPERATOR**: Detection, logging, search, analytics (no user management)
4. **VIEWER**: Read-only access to logs and analytics

### **Permission Matrix**
| Permission | SUPERADMIN | ADMIN | OPERATOR | VIEWER |
|------------|------------|-------|----------|--------|
| View Dashboard | ✅ | ✅ | ✅ | ✅ |
| View Logs | ✅ | ✅ | ✅ | ✅ |
| Edit Plates | ✅ | ✅ | ✅ | ❌ |
| Delete Logs | ✅ | ✅ | ❌ | ❌ |
| View Analytics | ✅ | ✅ | ✅ | ✅ |
| Export Data | ✅ | ✅ | ✅ | ❌ |
| Manage Users | ✅ | ✅ | ❌ | ❌ |
| Manage Roles | ✅ | ❌ | ❌ | ❌ |
| System Settings | ✅ | ✅ | ✅ | ❌ |
| View Audit Logs | ✅ | ✅ | ❌ | ❌ |

## 📈 Performance Optimization

### **Best Practices**
1. **Use GPU**: 5-10x faster than CPU-only processing
2. **Frame Skip**: Process every 2-3 frames for real-time performance
3. **Model Selection**: Use yolov8n for speed, yolov8x for accuracy
4. **Thread Count**: Set to CPU core count - 1
5. **Batch Processing**: Increase batch size for video files
6. **Image Cleanup**: Periodically archive old plate images

### **Recommended Settings**
```python
# For Real-time (Live Camera)
FRAME_SKIP = 2
MODEL_SIZE = "yolov8n"
BATCH_SIZE = 1
MAX_WORKERS = 4

# For Accuracy (Video Analysis)
FRAME_SKIP = 1
MODEL_SIZE = "yolov8m" or "yolov8l"
BATCH_SIZE = 4
MAX_WORKERS = 8
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

- **YOLOv8** by Ultralytics for object detection
- **EasyOCR** for optical character recognition
- **ByteTrack** for multi-object tracking
- **PyQt5** for the GUI framework
- **SQLAlchemy** for database ORM

## 📧 Support

For issues, questions, or suggestions, please open an issue on the repository.

---

**Made with ❤️ for Nepali ANPR Systems**
