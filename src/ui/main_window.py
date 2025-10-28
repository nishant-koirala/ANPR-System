import sys
import os
import cv2
import numpy as np
import traceback
import shutil
from datetime import datetime
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, QHBoxLayout,
    QVBoxLayout, QListWidget, QTableWidget, QTableWidgetItem, QScrollArea,
    QGridLayout, QStackedWidget, QGroupBox, QRadioButton, QLineEdit,
    QComboBox, QMessageBox, QSpinBox, QDoubleSpinBox, QTabWidget, QCheckBox,
    QSlider
)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

from sort.sort import Sort
from config import settings
from config.license_formats import FORMAT_DISPLAY_NAMES
from .rbac_ui_controller import RBACUIController

class PlateDetectorDashboard(QWidget):
    trackerTypeChanged = pyqtSignal(str)
    def __init__(self, auth_manager=None):
        super().__init__()
        self.setWindowTitle("ANPR - Entry Gate System")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize auth manager and RBAC controller
        self.auth_manager = auth_manager  # Use provided auth_manager if available
        self.rbac_controller = None
        print(f"DEBUG PlateDetectorDashboard.__init__: auth_manager provided={auth_manager is not None}, username={auth_manager.current_username if auth_manager else 'None'}")
        self.initialize_auth()

        # Initialize components
        # Ensure tracker_type is available before models are set up
        self.tracker_type = getattr(settings, 'TRACKER_TYPE', 'SORT')
        self.setup_models()
        self.setup_tracking()
        self.setup_ui_state()
        
        # Initialize settings
        self.current_settings = {}
        self.load_settings()
        
        # Initialize webcam variables
        self.webcam = None
        self.webcam_timer = None
        self.is_live_active = False
        self.available_cameras = []
        self.selected_camera_index = 0
        
        # Prepare temp directories for this session
        self.setup_temp_dirs()
        
        # Detect available cameras
        self.detect_cameras()
        
        # Build UI
        self.build_ui()

    def setup_models(self):
        """Initialize detection models and OCR"""
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")

        # Initialize tracker based on settings
        self.init_tracker()

    def setup_tracking(self):
        """Initialize tracking variables"""
        self.vehicle_final_plates = {}
        self.plate_ownership = {}
        self.vehicle_plate_candidates = defaultdict(list)
        self.min_detections_for_final = settings.MIN_DETECTIONS_FOR_FINAL
        self.confidence_threshold_final = settings.CONFIDENCE_THRESHOLD_FINAL
        
        self.unique_vehicles = set()
        self.cached_detections = []
        self.vehicle_id_map = {}
        self.detected_plates = []

    def setup_ui_state(self):
        """Initialize UI state variables"""
        self.timer = QTimer()
        try:
            # Use a precise timer to avoid coalesced ticks affecting stepping behavior
            self.timer.setTimerType(Qt.PreciseTimer)
        except Exception:
            pass
        self.video_path = None
        self.cap = None
        self.playing = False
        self.frame_counter = 0
        self.frame_preview_index = 0
        self.seeking = False
        self.loop_enabled = False
        self.playback_speed = 1.0
        self.video_fps = None
        self.total_frames = 0
        self.base_interval_ms = None
        self.suppress_slider_update = False
        self.stepping_in_progress = False
        
        # Settings
        self.license_format = 'auto'
        self.frame_skip = settings.DEFAULT_FRAME_SKIP
        self.hide_bboxes = False
        self.camera_source = "video"
        self.log_file_path = os.path.expanduser("~")
        self.manual_export_mode = "Manual Export"
        self.auto_backup_interval = "Daily"
        self.tracker_type = getattr(settings, 'TRACKER_TYPE', 'SORT')
        
        # Counters for dashboard cards
        self.total_tracked = 0
        self.unique_plates_detected = 0
        self.valid_plates_count = 0
        self.missed_plates_count = 0
        self.all_detected_plates = []  # Store all plate detections for display
        
        # Connect timer
        self.timer.timeout.connect(self.read_frame)
    
    def initialize_auth(self):
        """Initialize authentication manager and RBAC controller"""
        try:
            from ..auth.auth_manager import AuthManager
            from ..db.database import get_database
            
            # Only create new auth_manager if one wasn't provided
            if not self.auth_manager:
                # Get database instance and use its session factory
                db = get_database()
                self.auth_manager = AuthManager(db.get_session)
                print("DEBUG: Created new auth manager")
            else:
                print(f"DEBUG: Using provided auth manager (user: {self.auth_manager.current_username})")
            
            # Always create RBAC controller with the auth manager
            self.rbac_controller = RBACUIController(self.auth_manager)
            print("DEBUG: RBAC controller initialized")
            
            # Rebuild sidebar to reflect current login state
            if hasattr(self, 'sidebar'):
                self.rebuild_sidebar()
        except Exception as e:
            print(f"DEBUG: Failed to initialize auth manager: {e}")
            import traceback
            traceback.print_exc()

    def setup_temp_dirs(self):
        """Create session temp directories and configure debug saving"""
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            logs_dir = os.path.join(project_root, 'logs')
            tmp_root = os.path.join(logs_dir, 'tmp')
            os.makedirs(tmp_root, exist_ok=True)
            session_name = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.session_temp_dir = os.path.join(tmp_root, f'session_{session_name}')
            os.makedirs(self.session_temp_dir, exist_ok=True)
            # Configure OCR debug directory
            if getattr(settings, 'DEBUG_SAVE_IMAGES', False):
                self.debug_dir = os.path.join(self.session_temp_dir, 'ocr_debug')
                os.makedirs(self.debug_dir, exist_ok=True)
                if hasattr(self, 'plate_reader'):
                    self.plate_reader.set_debug_dir(self.debug_dir)
        except Exception as e:
            print(f"Failed to create temp dirs: {e}")

    def load_settings(self):
        """Load settings from config module"""
        for setting in dir(settings):
            if setting.isupper():
                self.current_settings[setting] = getattr(settings, setting)

    def create_detection_settings(self, parent_layout):
        """Create detection settings group"""
        group = QGroupBox("Detection Settings")
        layout = QGridLayout()
        
        # Vehicle Detection
        layout.addWidget(QLabel("Vehicle Confidence:"), 0, 0)
        self.vehicle_conf_spin = QDoubleSpinBox()
        self.vehicle_conf_spin.setRange(0.01, 1.0)
        self.vehicle_conf_spin.setSingleStep(0.01)
        self.vehicle_conf_spin.setValue(self.current_settings.get('VEHICLE_CONFIDENCE_THRESHOLD', 0.15))
        layout.addWidget(self.vehicle_conf_spin, 0, 1)
        
        # Plate Detection
        layout.addWidget(QLabel("Plate Confidence:"), 1, 0)
        self.plate_conf_spin = QDoubleSpinBox()
        self.plate_conf_spin.setRange(0.01, 1.0)
        self.plate_conf_spin.setSingleStep(0.01)
        self.plate_conf_spin.setValue(self.current_settings.get('PLATE_CONFIDENCE_THRESHOLD', 0.15))
        layout.addWidget(self.plate_conf_spin, 1, 1)
        
        # OCR Confidence
        layout.addWidget(QLabel("OCR Confidence:"), 2, 0)
        self.ocr_conf_spin = QDoubleSpinBox()
        self.ocr_conf_spin.setRange(0.01, 1.0)
        self.ocr_conf_spin.setSingleStep(0.01)
        self.ocr_conf_spin.setValue(self.current_settings.get('OCR_CONFIDENCE_THRESHOLD', 0.05))
        layout.addWidget(self.ocr_conf_spin, 2, 1)
        
        # Min Plate Width
        layout.addWidget(QLabel("Min Plate Width (px):"), 3, 0)
        self.min_width_spin = QSpinBox()
        self.min_width_spin.setRange(10, 500)
        self.min_width_spin.setValue(self.current_settings.get('MIN_PLATE_WIDTH', 100))
        layout.addWidget(self.min_width_spin, 3, 1)
        
        # Min Plate Height
        layout.addWidget(QLabel("Min Plate Height (px):"), 4, 0)
        self.min_height_spin = QSpinBox()
        self.min_height_spin.setRange(10, 500)
        self.min_height_spin.setValue(self.current_settings.get('MIN_PLATE_HEIGHT', 30))
        layout.addWidget(self.min_height_spin, 4, 1)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_model_settings(self, parent_layout):
        """Create model selection settings group"""
        group = QGroupBox("Model Settings")
        layout = QGridLayout()
        
        # Vehicle Model Selection
        layout.addWidget(QLabel("Vehicle Detection Model:"), 0, 0)
        self.vehicle_model_combo = QComboBox()
        self.vehicle_model_combo.addItems(["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"])
        # Set current selection
        current_model = self.current_settings.get('VEHICLE_MODEL_TYPE', 'yolov8m')
        if current_model in ["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"]:
            self.vehicle_model_combo.setCurrentText(current_model)
        layout.addWidget(self.vehicle_model_combo, 0, 1)
        
        # Model info label
        model_info = QLabel("n=fastest, s=small, m=medium, l=large, x=extra large")
        model_info.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(model_info, 1, 0, 1, 2)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_ocr_settings(self, parent_layout):
        """Create OCR settings group"""
        group = QGroupBox("OCR Settings")
        layout = QGridLayout()
        
        # OCR Whitelist
        layout.addWidget(QLabel("Allowed Characters:"), 0, 0)
        self.ocr_whitelist_edit = QLineEdit()
        self.ocr_whitelist_edit.setText(self.current_settings.get('OCR_WHITELIST', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'))
        layout.addWidget(self.ocr_whitelist_edit, 0, 1, 1, 2)
        
        # OCR Preprocessing
        layout.addWidget(QLabel("Image Enhancement:"), 1, 0)
        self.enhance_scale = QDoubleSpinBox()
        self.enhance_scale.setRange(0.1, 5.0)
        self.enhance_scale.setSingleStep(0.1)
        self.enhance_scale.setValue(self.current_settings.get('ENHANCE_SCALE_FACTOR', 2.0))
        layout.addWidget(self.enhance_scale, 1, 1)
        
        # CLAHE Clip Limit
        layout.addWidget(QLabel("Contrast Limit:"), 2, 0)
        self.clahe_clip = QDoubleSpinBox()
        self.clahe_clip.setRange(0.1, 10.0)
        self.clahe_clip.setSingleStep(0.1)
        self.clahe_clip.setValue(self.current_settings.get('CLAHE_CLIP_LIMIT', 2.0))
        layout.addWidget(self.clahe_clip, 2, 1)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_performance_settings(self, parent_layout):
        """Create performance settings group"""
        group = QGroupBox("Performance Settings")
        layout = QGridLayout()
        
        # Frame Rate
        layout.addWidget(QLabel("Target FPS:"), 0, 0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(self.current_settings.get('VIDEO_FPS', 30))
        layout.addWidget(self.fps_spin, 0, 1)
        
        # Frame Skip
        layout.addWidget(QLabel("Frame Skip:"), 1, 0)
        self.frame_skip_spin = QSpinBox()
        self.frame_skip_spin.setRange(0, 10)
        self.frame_skip_spin.setValue(self.current_settings.get('DEFAULT_FRAME_SKIP', 2))
        layout.addWidget(self.frame_skip_spin, 1, 1)
        
        # Detection Interval
        layout.addWidget(QLabel("Detection Interval:"), 2, 0)
        self.det_interval_spin = QSpinBox()
        self.det_interval_spin.setRange(1, 10)
        self.det_interval_spin.setValue(self.current_settings.get('DEFAULT_DETECTION_INTERVAL', 2))
        layout.addWidget(self.det_interval_spin, 2, 1)
        
        # Max Frame Width
        layout.addWidget(QLabel("Max Width (px):"), 3, 0)
        self.max_width_spin = QSpinBox()
        self.max_width_spin.setRange(320, 3840)
        self.max_width_spin.setValue(self.current_settings.get('MAX_FRAME_WIDTH', 1280))
        layout.addWidget(self.max_width_spin, 3, 1)
        
        # Thread Count
        layout.addWidget(QLabel("Threads:"), 4, 0)
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 32)
        self.thread_spin.setValue(self.current_settings.get('THREAD_COUNT', 4))
        layout.addWidget(self.thread_spin, 4, 1)
        
        # GPU Acceleration
        self.gpu_check = QCheckBox("Use GPU Acceleration")
        self.gpu_check.setChecked(self.current_settings.get('USE_GPU', True))
        layout.addWidget(self.gpu_check, 5, 0, 1, 2)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def save_settings(self):
        """Save settings to config module"""
        # Update current settings from UI
        selected_model = self.vehicle_model_combo.currentText()
        self.current_settings.update({
            'VEHICLE_MODEL_TYPE': selected_model,
            'VEHICLE_MODEL_PATH': f"{selected_model}.pt",
            'VEHICLE_CONFIDENCE_THRESHOLD': self.vehicle_conf_spin.value(),
            'PLATE_CONFIDENCE_THRESHOLD': self.plate_conf_spin.value(),
            'OCR_CONFIDENCE_THRESHOLD': self.ocr_conf_spin.value(),
            'MIN_PLATE_WIDTH': self.min_width_spin.value(),
            'MIN_PLATE_HEIGHT': self.min_height_spin.value(),
            'OCR_WHITELIST': self.ocr_whitelist_edit.text(),
            'ENHANCE_SCALE_FACTOR': self.enhance_scale.value(),
            'CLAHE_CLIP_LIMIT': self.clahe_clip.value(),
            'VIDEO_FPS': self.fps_spin.value(),
            'DEFAULT_FRAME_SKIP': self.frame_skip_spin.value(),
            'DEFAULT_DETECTION_INTERVAL': self.det_interval_spin.value(),
            'MAX_FRAME_WIDTH': self.max_width_spin.value(),
            'THREAD_COUNT': self.thread_spin.value(),
            'USE_GPU': self.gpu_check.isChecked(),
            'TRACKER_TYPE': (
                'DEEPSORT' if self.tracker_combo.currentText() == 'Deep SORT' else
                'BYTETRACK' if self.tracker_combo.currentText() == 'ByteTrack' else
                'SORT'
            )
        })
        
        # Check if model changed BEFORE updating settings
        old_model_path = getattr(settings, 'VEHICLE_MODEL_PATH', None)
        new_model_path = self.current_settings.get('VEHICLE_MODEL_PATH')
        model_changed = old_model_path != new_model_path
        
        # If model changed, check if file exists
        if model_changed:
            models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'models')
            model_file = f"{selected_model}.pt"
            model_path = os.path.join(models_dir, model_file)
            
            if not os.path.exists(model_path):
                # Ask for download confirmation
                reply = QMessageBox.question(
                    self, 
                    "Model Not Found",
                    f"The model '{model_file}' is not downloaded. Download now?",
                    QMessageBox.Ok | QMessageBox.Cancel
                )
                
                if reply == QMessageBox.Ok:
                    from src.utils.downloader import download_model
                    # Download model with progress dialog
                    downloaded = download_model(model_file, models_dir, self)
                    if not downloaded:
                        # Download failed, revert selection
                        self.vehicle_model_combo.setCurrentText(old_model_path.split('.')[0])
                        return
                else:
                    # User canceled download, revert selection
                    self.vehicle_model_combo.setCurrentText(old_model_path.split('.')[0])
                    return
        
        # Update config module
        for setting, value in self.current_settings.items():
            if hasattr(settings, setting):
                setattr(settings, setting, value)
        
        # Show progress dialog for model loading
        if model_changed:
            from PyQt5.QtWidgets import QProgressDialog
            # Create and store progress dialog for main handler updates
            self.model_progress_dialog = QProgressDialog("Loading model...", "Cancel", 0, 0, self)
            self.model_progress_dialog.setWindowTitle("Model Download")
            self.model_progress_dialog.setModal(True)
            self.model_progress_dialog.show()

            print(f"DEBUG: Model changed from '{old_model_path}' to '{new_model_path}'")

            # Apply other runtime settings (timer/GPU/tracker). Avoid blocking model reload on UI.
            try:
                self.apply_runtime_settings()
            except Exception:
                pass

            # Request background reload via ANPRApplication signal if available
            try:
                if hasattr(self, 'reloadRequested'):
                    self.reloadRequested.emit(new_model_path)
                else:
                    # Fallback: try local synchronous reload if available (not typical)
                    try:
                        update_progress = lambda m: (self.model_progress_dialog.setLabelText(str(m)), QApplication.processEvents())
                        # If UI has a vehicle_detector (rare), reload it synchronously
                        if hasattr(self, 'vehicle_detector'):
                            self.vehicle_detector.reload_model(new_model_path, getattr(self, 'device', 'cpu'), update_progress)
                        # Notify completion via dialog; final message boxes handled in main if signal existed
                        if hasattr(self, 'model_progress_dialog') and self.model_progress_dialog is not None:
                            self.model_progress_dialog.close()
                            self.model_progress_dialog = None
                            QMessageBox.information(self, "Settings Saved", "Settings have been saved and model loaded successfully!")
                    except Exception as e:
                        if hasattr(self, 'model_progress_dialog') and self.model_progress_dialog is not None:
                            self.model_progress_dialog.close()
                            self.model_progress_dialog = None
                        QMessageBox.warning(self, "Model Loading Error", f"Settings saved but model loading failed: {e}")
            except Exception as e:
                # On unexpected error, ensure dialog is closed
                try:
                    if hasattr(self, 'model_progress_dialog') and self.model_progress_dialog is not None:
                        self.model_progress_dialog.close()
                        self.model_progress_dialog = None
                except Exception:
                    pass
                QMessageBox.warning(self, "Model Loading Error", f"Failed to request background reload: {e}")
        else:
            # Apply settings to running processes if needed
            self.apply_runtime_settings()
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully!")
    
    def apply_runtime_settings(self, progress_callback=None):
        """Apply settings that can be changed at runtime"""
        # Update frame timer interval based on FPS
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.setInterval(1000 // self.current_settings['VIDEO_FPS'])
        
        # Update GPU usage if changed
        if hasattr(self, 'device'):
            import torch
            if self.current_settings['USE_GPU'] and torch.cuda.is_available():
                self.device = 'cuda'
            else:
                self.device = 'cpu'
            print(f"Device set to: {self.device}")

        # Reinitialize models if vehicle model changed
        if hasattr(self, 'vehicle_detector'):
            try:
                # Reload the model in the existing detector instead of creating new instance
                self.vehicle_detector.reload_model(
                    self.current_settings.get('VEHICLE_MODEL_PATH'), 
                    self.device, 
                    progress_callback
                )
                print(f"Reloaded vehicle detector with model: {self.current_settings.get('VEHICLE_MODEL_PATH')}")
            except Exception as e:
                print(f"Failed to reload vehicle detector: {e}")
                # Fallback: create new detector
                try:
                    from src.detection.vehicle_detector import VehicleDetector
                    if progress_callback:
                        progress_callback("Creating new vehicle detector...")
                    self.vehicle_detector = VehicleDetector(self.device, self.current_settings.get('VEHICLE_MODEL_PATH'))
                except Exception as e2:
                    print(f"Failed to create new vehicle detector: {e2}")
                    raise e2

        # Update worker thread model if changed
        if hasattr(self, 'frame_worker'):
            try:
                if progress_callback:
                    progress_callback("Updating worker thread model...")
                self.frame_worker.reload_vehicle_model(self.current_settings.get('VEHICLE_MODEL_PATH'))
            except Exception as e:
                print(f"Failed to update worker model: {e}")

        # Reinitialize tracker if type changed
        if self.tracker_type != self.current_settings.get('TRACKER_TYPE', self.tracker_type):
            self.tracker_type = self.current_settings['TRACKER_TYPE']
            self.init_tracker()
            # Clear tracking state to avoid mixing track IDs
            self.setup_tracking()

    def build_ui(self):
        """Build the main UI"""
        main_layout = QHBoxLayout(self)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(150)
        
        # Stack widget - build first
        self.stack = QStackedWidget()
        
        # Build sidebar items and add pages to stack dynamically
        self.sidebar_items = []
        self.sidebar_pages = []  # Map sidebar index to stack page index
        
        # Dashboard - all users
        self.sidebar_items.append("▶ Dashboard")
        self.dashboard_page = self.build_dashboard_page()
        self.sidebar_pages.append(self.stack.addWidget(self.dashboard_page))
        
        # Vehicle Log - all users
        self.sidebar_items.append("🚗 Vehicle Log")
        self.vehicle_log_page = self.build_database()
        self.sidebar_pages.append(self.stack.addWidget(self.vehicle_log_page))
        
        # User Management - Admin and above only
        if self.rbac_controller and self.rbac_controller.can_manage_users():
            self.sidebar_items.append("👥 User Management")
            self.user_management_page = self.build_user_management()
            self.sidebar_pages.append(self.stack.addWidget(self.user_management_page))
        
        # Analytics - all users
        self.sidebar_items.append("📊 Analytics")
        self.analytics_page = self.build_analytics_page()
        self.sidebar_pages.append(self.stack.addWidget(self.analytics_page))
        
        # Search Plate - all users
        self.sidebar_items.append("🔍 Search Plate")
        self.search_plate_page = self.build_search_plate()
        self.sidebar_pages.append(self.stack.addWidget(self.search_plate_page))
        
        # Settings - all users (view-only for Viewer/Operator)
        if self.rbac_controller and self.rbac_controller.can_view_settings():
            self.sidebar_items.append("⚙ Settings")
            self.settings_page = self.build_settings_page()
            self.sidebar_pages.append(self.stack.addWidget(self.settings_page))
        
        # Logout - all users
        self.sidebar_items.append("🚪 Logout")
        self.sidebar_pages.append(-1)  # Special case for logout
        
        self.sidebar.addItems(self.sidebar_items)
        self.sidebar.setCurrentRow(0)
        self.sidebar.setStyleSheet(
            "QListWidget { background-color: #f5f6fa; font-size: 14px; } "
            "QListWidget::item { padding: 20px; }"
        )
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

    def build_database(self):
        """Build database page"""
        try:
            from .database_page import DatabasePage
            return DatabasePage(rbac_controller=self.rbac_controller)
        except ImportError as e:
            # Fallback if database page can't be imported
            page = QWidget()
            layout = QVBoxLayout(page)
            error_label = QLabel(f"Database page unavailable: {e}")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return page

    def build_user_management(self):
        """Build user management page"""
        try:
            from .user_management_page import UserManagementPage
            from ..auth.auth_manager import AuthManager
            from ..db.database import get_database
            
            # Auth manager should already be initialized in __init__
            # If not, initialize it now
            if not self.auth_manager:
                db = get_database()
                self.auth_manager = AuthManager(db.get_session)
                self.rbac_controller = RBACUIController(self.auth_manager)
            
            # Check if user is logged in and has proper permissions
            if not self.auth_manager.current_username:
                # Create a login prompt page
                page = QWidget()
                layout = QVBoxLayout(page)
                
                login_label = QLabel("🔐 Authentication Required")
                login_label.setFont(QFont("Arial", 16, QFont.Bold))
                login_label.setAlignment(Qt.AlignCenter)
                
                message_label = QLabel("Please log in to access User Management")
                message_label.setAlignment(Qt.AlignCenter)
                
                login_button = QPushButton("Login")
                login_button.clicked.connect(self.show_login_dialog)
                
                layout.addStretch()
                layout.addWidget(login_label)
                layout.addWidget(message_label)
                layout.addWidget(login_button)
                layout.addStretch()
                
                return page
            
            return UserManagementPage(self.auth_manager)
        except ImportError as e:
            # Fallback if user management page can't be imported
            page = QWidget()
            layout = QVBoxLayout(page)
            error_label = QLabel(f"User Management unavailable: {e}")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return page
        except Exception as e:
            # Fallback for any other errors
            page = QWidget()
            layout = QVBoxLayout(page)
            error_label = QLabel(f"User Management error: {e}")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            print(f"DEBUG: User Management build error: {e}")
            import traceback
            traceback.print_exc()
            return page

    def build_analytics_page(self):
        """Build analytics page"""
        print("DEBUG: build_analytics_page called")
        try:
            print("DEBUG: Importing AnalyticsPage...")
            from .analytics_page import AnalyticsPage
            from ..db.database import get_database
            
            print("DEBUG: Getting database instance...")
            db = get_database()
            print(f"DEBUG: Database instance: {db}")
            
            print("DEBUG: Creating AnalyticsPage...")
            page = AnalyticsPage(db)
            print("DEBUG: AnalyticsPage created successfully")
            return page
        except ImportError as e:
            # Fallback if analytics page can't be imported
            print(f"DEBUG: ImportError in analytics page: {e}")
            import traceback
            traceback.print_exc()
            page = QWidget()
            layout = QVBoxLayout(page)
            error_label = QLabel(f"Analytics page unavailable: {e}\n\nInstall required packages:\npip install matplotlib reportlab openpyxl")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            return page
        except Exception as e:
            # Fallback for any other errors
            print(f"DEBUG: Exception in analytics page: {e}")
            import traceback
            traceback.print_exc()
            page = QWidget()
            layout = QVBoxLayout(page)
            error_label = QLabel(f"Analytics page error: {e}\n\nCheck console for details")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
            return page

    def build_dashboard_page(self):
        """Build dashboard page"""
        page = QWidget()
        content_layout = QVBoxLayout(page)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("⚡ Entry Gate System")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        support = QPushButton("Help & Support")
        user = QPushButton("Hi, User")
        support.setStyleSheet("padding: 6px; background-color: #6ab04c; color: white; border-radius: 5px;")
        user.setStyleSheet("padding: 6px; background-color: #2980b9; color: white; border-radius: 5px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(support)
        header_layout.addWidget(user)
        content_layout.addLayout(header_layout)

        # Dynamic Cards with counters
        cards_layout = QHBoxLayout()
        
        # Total Tracked Vehicles
        self.tracked_card = QLabel("Total Tracked\n0")
        self.tracked_card.setStyleSheet("background-color: #00b894; color: white; border-radius: 10px; padding: 20px;")
        self.tracked_card.setAlignment(Qt.AlignCenter)
        self.tracked_card.setFont(QFont("Arial", 11, QFont.Bold))
        self.tracked_card.setFixedSize(200, 100)
        
        # Unique Plates Detected
        self.unique_plates_card = QLabel("Unique Plates\n0")
        self.unique_plates_card.setStyleSheet("background-color: #fdcb6e; color: white; border-radius: 10px; padding: 20px;")
        self.unique_plates_card.setAlignment(Qt.AlignCenter)
        self.unique_plates_card.setFont(QFont("Arial", 11, QFont.Bold))
        self.unique_plates_card.setFixedSize(200, 100)
        
        # Valid Plates
        self.valid_plates_card = QLabel("Valid Plates\n0")
        self.valid_plates_card.setStyleSheet("background-color: #74b9ff; color: white; border-radius: 10px; padding: 20px;")
        self.valid_plates_card.setAlignment(Qt.AlignCenter)
        self.valid_plates_card.setFont(QFont("Arial", 11, QFont.Bold))
        self.valid_plates_card.setFixedSize(200, 100)
        
        # Missed/Failed Plates
        self.missed_plates_card = QLabel("Missed Plates\n0")
        self.missed_plates_card.setStyleSheet("background-color: #e17055; color: white; border-radius: 10px; padding: 20px;")
        self.missed_plates_card.setAlignment(Qt.AlignCenter)
        self.missed_plates_card.setFont(QFont("Arial", 11, QFont.Bold))
        self.missed_plates_card.setFixedSize(200, 100)
        
        cards_layout.addWidget(self.tracked_card)
        cards_layout.addWidget(self.unique_plates_card)
        cards_layout.addWidget(self.valid_plates_card)
        cards_layout.addWidget(self.missed_plates_card)
        content_layout.addLayout(cards_layout)

        # Preview + controls
        preview_layout = QVBoxLayout()
        self.image_label = QLabel("Preview")
        self.image_label.setFixedSize(700, 400)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background-color: black")
        self.image_label.setAlignment(Qt.AlignCenter)

        # Controls
        controls_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.toggle_video)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_video)
        self.step_back_btn = QPushButton("⏮ Frame-")
        self.step_back_btn.clicked.connect(lambda: self.step_frame(-1))
        self.step_fwd_btn = QPushButton("⏭ Frame+")
        self.step_fwd_btn.clicked.connect(lambda: self.step_frame(1))
        # Defensive: ensure step buttons do not auto-repeat on press-and-hold
        try:
            self.step_back_btn.setAutoRepeat(False)
            self.step_fwd_btn.setAutoRepeat(False)
            # Avoid accidental activation via Enter key focus defaults
            self.step_back_btn.setAutoDefault(False)
            self.step_fwd_btn.setAutoDefault(False)
        except Exception:
            pass
        # Prevent keyboard focus from causing repeated activations
        try:
            self.step_back_btn.setFocusPolicy(Qt.NoFocus)
            self.step_fwd_btn.setFocusPolicy(Qt.NoFocus)
        except Exception:
            pass

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.step_back_btn)
        controls_layout.addWidget(self.step_fwd_btn)

        # Speed selector
        controls_layout.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self.on_speed_changed)
        controls_layout.addWidget(self.speed_combo)

        # Loop checkbox
        self.loop_checkbox = QCheckBox("Loop")
        self.loop_checkbox.stateChanged.connect(lambda s: setattr(self, 'loop_enabled', self.loop_checkbox.isChecked()))
        controls_layout.addWidget(self.loop_checkbox)

        # Progress slider and time label
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(0)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        self.time_label = QLabel("00:00 / 00:00")

        preview_layout.addWidget(self.image_label)
        preview_layout.addWidget(self.progress_slider)
        preview_layout.addWidget(self.time_label)
        preview_layout.addLayout(controls_layout)

        # Plate Detection Preview Panel
        plates_panel = QGroupBox("Detected Plates (All)")
        plates_panel.setFixedSize(400, 400)
        plates_panel_layout = QVBoxLayout(plates_panel)
        
        # Scrollable area for plate images
        self.plates_scroll_area = QScrollArea()
        self.plates_container = QWidget()
        self.plates_layout = QVBoxLayout(self.plates_container)
        self.plates_layout.setAlignment(Qt.AlignTop)
        self.plates_scroll_area.setWidgetResizable(True)
        self.plates_scroll_area.setWidget(self.plates_container)
        plates_panel_layout.addWidget(self.plates_scroll_area)

        preview_hbox = QHBoxLayout()
        preview_hbox.addLayout(preview_layout)
        preview_hbox.addWidget(plates_panel)
        content_layout.addLayout(preview_hbox)

        # Upload and Live buttons
        upload_btns = QHBoxLayout()
        image_btn = QPushButton("Upload Image")
        image_btn.clicked.connect(self.load_image)
        video_btn = QPushButton("Upload Video")
        video_btn.clicked.connect(self.load_video)
        # Camera selection and live button layout
        camera_layout = QHBoxLayout()
        
        # Camera selection dropdown
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(200)
        self.populate_camera_combo()
        camera_layout.addWidget(QLabel("Camera:"))
        camera_layout.addWidget(self.camera_combo)
        
        # IP Camera input
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("DroidCam IP (e.g., 192.168.1.100:4747)")
        self.ip_input.setMinimumWidth(200)
        camera_layout.addWidget(QLabel("IP:"))
        camera_layout.addWidget(self.ip_input)
        
        # Refresh cameras button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setMaximumWidth(30)
        refresh_btn.setToolTip("Refresh camera list")
        refresh_btn.clicked.connect(self.refresh_cameras)
        camera_layout.addWidget(refresh_btn)
        
        live_btn = QPushButton("Start Live Camera")
        live_btn.clicked.connect(self.toggle_live_camera)
        camera_layout.addWidget(live_btn)
        
        for btn in [image_btn, video_btn]:
            btn.setStyleSheet("padding: 10px; background-color: #0984e3; color: white; border-radius: 5px;")
            upload_btns.addWidget(btn)
        
        live_btn.setStyleSheet("padding: 10px; background-color: #27ae60; color: white; border-radius: 5px;")
        upload_btns.addLayout(camera_layout)
        self.live_btn = live_btn  # Store reference for updating text
        content_layout.addLayout(upload_btns)

        # Vehicle counter
        counter_layout = QHBoxLayout()
        self.vehicle_counter_label = QLabel("Vehicles: 0 | Finalized Plates: 0 | Unique Plates: 0")
        self.vehicle_counter_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.vehicle_counter_label.setStyleSheet("color: #2980b9; padding: 10px; background-color: #ecf0f1; border-radius: 5px;")
        counter_layout.addWidget(self.vehicle_counter_label)
        counter_layout.addStretch()
        content_layout.addLayout(counter_layout)
        
        # Vehicle Log Table
        vehicle_log_group = QGroupBox("🚗 Vehicle Status Log")
        vehicle_log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin: 10px 0px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        vehicle_log_layout = QVBoxLayout(vehicle_log_group)
        
        # Create vehicle log table
        self.vehicle_log_table = QTableWidget()
        self.vehicle_log_table.setColumnCount(4)
        self.vehicle_log_table.setHorizontalHeaderLabels(["ID", "Plate Image", "Plate Number", "Status"])
        self.vehicle_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.vehicle_log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.vehicle_log_table.setAlternatingRowColors(True)
        self.vehicle_log_table.setFixedHeight(200)
        
        # Set column widths
        self.vehicle_log_table.setColumnWidth(0, 60)   # ID column
        self.vehicle_log_table.setColumnWidth(1, 120)  # Image column
        self.vehicle_log_table.setColumnWidth(2, 150)  # Plate number column
        self.vehicle_log_table.setColumnWidth(3, 100)  # Status column
        
        # Style the table
        self.vehicle_log_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        vehicle_log_layout.addWidget(self.vehicle_log_table)
        content_layout.addWidget(vehicle_log_group)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["S.no", "Plate Image", "Plate No. (Vehicle ID)", "Type", "Date", "TimeStamp", "Site (Confidence)"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        return page

    def add_vehicle_to_log(self, vehicle_id, plate_text, plate_img, status="PRESENT"):
        """Add or update vehicle in the vehicle log table"""
        try:
            # Check if vehicle already exists in table
            for row in range(self.vehicle_log_table.rowCount()):
                id_item = self.vehicle_log_table.item(row, 0)
                if id_item and id_item.text() == f"V{vehicle_id}":
                    # Update existing vehicle
                    self.update_vehicle_log_entry(row, vehicle_id, plate_text, plate_img, status)
                    return
            
            # Add new vehicle to table
            self.create_vehicle_log_entry(vehicle_id, plate_text, plate_img, status)
        except Exception as e:
            print(f"Error adding vehicle to log: {e}")

    def create_vehicle_log_entry(self, vehicle_id, plate_text, plate_img, status):
        """Create a new vehicle log entry in the table"""
        try:
            row = self.vehicle_log_table.rowCount()
            self.vehicle_log_table.insertRow(row)
            self.vehicle_log_table.setRowHeight(row, 60)
            
            # Column 0: Vehicle ID
            id_item = QTableWidgetItem(f"V{vehicle_id}")
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.vehicle_log_table.setItem(row, 0, id_item)
            
            # Column 1: Plate Image
            plate_label = QLabel()
            if plate_img is not None:
                try:
                    plate_rgb = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB)
                    h, w, ch = plate_rgb.shape
                    bytes_per_line = ch * w
                    qt_img = QImage(plate_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    plate_pixmap = QPixmap.fromImage(qt_img).scaled(100, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    plate_label.setPixmap(plate_pixmap)
                except:
                    plate_label.setText("No Image")
                    plate_label.setStyleSheet("background-color: #f8f9fa; color: #6c757d;")
            else:
                plate_label.setText("No Image")
                plate_label.setStyleSheet("background-color: #f8f9fa; color: #6c757d;")
            
            plate_label.setAlignment(Qt.AlignCenter)
            self.vehicle_log_table.setCellWidget(row, 1, plate_label)
            
            # Column 2: Plate Number
            plate_item = QTableWidgetItem(plate_text if plate_text else "Unknown")
            plate_item.setTextAlignment(Qt.AlignCenter)
            plate_item.setFont(QFont("Arial", 10))
            self.vehicle_log_table.setItem(row, 2, plate_item)
            
            # Column 3: Status
            status_label = QLabel()
            if status == "PRESENT":
                status_label.setText("🟢 PRESENT")
                status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            else:
                status_label.setText("🔴 EXITED")
                status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            status_label.setAlignment(Qt.AlignCenter)
            self.vehicle_log_table.setCellWidget(row, 3, status_label)
            
        except Exception as e:
            print(f"Error creating vehicle log entry: {e}")

    def update_vehicle_log_entry(self, row, vehicle_id, plate_text, plate_img, status):
        """Update an existing vehicle log entry in the table"""
        try:
            # Update plate image
            plate_label = self.vehicle_log_table.cellWidget(row, 1)
            if plate_label and plate_img is not None:
                try:
                    plate_rgb = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB)
                    h, w, ch = plate_rgb.shape
                    bytes_per_line = ch * w
                    qt_img = QImage(plate_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    plate_pixmap = QPixmap.fromImage(qt_img).scaled(100, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    plate_label.setPixmap(plate_pixmap)
                except:
                    pass
            
            # Update plate text
            plate_item = self.vehicle_log_table.item(row, 2)
            if plate_item:
                plate_item.setText(plate_text if plate_text else "Unknown")
            
            # Update status
            status_label = self.vehicle_log_table.cellWidget(row, 3)
            if status_label:
                if status == "PRESENT":
                    status_label.setText("🟢 PRESENT")
                    status_label.setStyleSheet("color: #28a745; font-weight: bold;")
                else:
                    status_label.setText("🔴 EXITED")
                    status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                    
        except Exception as e:
            print(f"Error updating vehicle log entry: {e}")

    def clear_vehicle_log(self):
        """Clear all vehicles from the log table"""
        try:
            self.vehicle_log_table.setRowCount(0)
        except Exception as e:
            print(f"Error clearing vehicle log: {e}")

    def build_search_plate(self):
        """Build search plate page"""
        try:
            from .search_plate_page import SearchPlatePage
            # Use db.get_session if available, otherwise create a fallback
            if hasattr(self, 'db') and self.db:
                session_factory = self.db.get_session
            else:
                # Fallback: try to get database instance
                from ..db.database import get_database
                db = get_database()
                session_factory = db.get_session
            
            # Pass auth_manager and rbac_controller to enable editing functionality
            search_page = SearchPlatePage(session_factory)
            if hasattr(self, 'auth_manager'):
                search_page.auth_manager = self.auth_manager
            elif hasattr(self, 'simple_auth'):
                search_page.auth_manager = self.simple_auth
            
            # Pass RBAC controller for permission checks
            if hasattr(self, 'rbac_controller'):
                search_page.rbac_controller = self.rbac_controller
            
            return search_page
        except ImportError as e:
            # Fallback if search plate page can't be imported
            page = QWidget()
            layout = QVBoxLayout(page)
            error_label = QLabel(f"Search Plate unavailable: {e}")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return page
        except Exception as e:
            # Fallback for any other errors
            page = QWidget()
            layout = QVBoxLayout(page)
            error_label = QLabel(f"Search Plate error: {e}")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return page

    def build_settings_page(self):
        """Build settings page"""
        try:
            from .settings_page import SettingsPage
            return SettingsPage(parent=self, rbac_controller=self.rbac_controller)
        except ImportError as e:
            # Fallback to simple settings page
            page = QWidget()
            main_layout = QVBoxLayout(page)

            title = QLabel("Settings")
            title.setFont(QFont("Arial", 18, QFont.Bold))
            main_layout.addWidget(title)

            # Create scroll area for settings
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_content = QWidget()
            layout = QVBoxLayout(scroll_content)

        # Camera Source
        cam_group = QGroupBox("Camera Source")
        cam_layout = QVBoxLayout()
        self.rb_upload_image = QRadioButton("Upload Image")
        self.rb_upload_video = QRadioButton("Upload Video")
        self.rb_live = QRadioButton("Live Camera Feed")
        cam_layout.addWidget(self.rb_upload_image)
        cam_layout.addWidget(self.rb_upload_video)
        cam_layout.addWidget(self.rb_live)
        cam_group.setLayout(cam_layout)
        layout.addWidget(cam_group)

        if self.camera_source == "image":
            self.rb_upload_image.setChecked(True)
        elif self.camera_source == "video":
            self.rb_upload_video.setChecked(True)
        else:
            self.rb_live.setChecked(True)

        # License Plate Format
        lp_group = QGroupBox("License Plate Format")
        lp_layout = QHBoxLayout()
        self.lp_format_combo = QComboBox()
        self.lp_format_combo.addItems(list(FORMAT_DISPLAY_NAMES.values()))
        self.lp_format_combo.currentTextChanged.connect(self.change_license_format)
        # Preselect to current license_format
        try:
            current_display = FORMAT_DISPLAY_NAMES.get(self.license_format, FORMAT_DISPLAY_NAMES.get('format1'))
            if current_display:
                self.lp_format_combo.setCurrentText(current_display)
        except Exception:
            pass
        lp_layout.addWidget(self.lp_format_combo)
        lp_group.setLayout(lp_layout)
        layout.addWidget(lp_group)

        # Tracking Algorithm
        track_group = QGroupBox("Tracking Algorithm")
        track_layout = QHBoxLayout()
        self.tracker_combo = QComboBox()
        self.tracker_combo.addItems(["SORT", "Deep SORT", "ByteTrack"])
        # Preselect
        try:
            tt = str(self.tracker_type).upper()
            preselect = "Deep SORT" if tt == 'DEEPSORT' else ("ByteTrack" if tt == 'BYTETRACK' else "SORT")
            self.tracker_combo.setCurrentText(preselect)
        except Exception:
            pass
        self.tracker_combo.currentTextChanged.connect(self.change_tracker_type)
        track_layout.addWidget(self.tracker_combo)
        track_group.setLayout(track_layout)
        layout.addWidget(track_group)

        # Add comprehensive settings groups
        self.create_model_settings(layout)
        self.create_detection_settings(layout)
        self.create_ocr_settings(layout)
        self.create_performance_settings(layout)

        # Save button
        btns = QHBoxLayout()
        save_btn = QPushButton("Save / Apply")
        save_btn.setStyleSheet("padding: 8px; background:#0984e3; color:#fff; border-radius:4px;")
        save_btn.clicked.connect(self.apply_settings)
        
        # Add new comprehensive save button
        save_all_btn = QPushButton("Save All Settings")
        save_all_btn.setStyleSheet("padding: 8px; background:#00b894; color:#fff; border-radius:4px;")
        save_all_btn.clicked.connect(self.save_settings)
        
        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(save_all_btn)
        layout.addLayout(btns)

        layout.addStretch()
        scroll_content.setLayout(layout)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        return page

    def on_sidebar_changed(self, index):
        """Handle sidebar navigation"""
        print(f"DEBUG: Sidebar changed to index: {index}")
        
        if index < 0 or index >= len(self.sidebar_pages):
            print(f"DEBUG: Invalid sidebar index {index}")
            return
        
        page_index = self.sidebar_pages[index]
        
        # Special case for logout
        if page_index == -1:
            print("DEBUG: Logout option selected")
            self.logout()
            return
        
        # Special case for login
        if page_index == -2:
            print("DEBUG: Login option selected")
            self.show_login_dialog()
            return
        
        # Navigate to the page (permissions already checked during sidebar build)
        self.stack.setCurrentIndex(page_index)
        print(f"DEBUG: Navigated to page index {page_index}")

    def logout(self):
        """Handle user logout"""
        print("DEBUG: Logout method called")
        
        reply = QMessageBox.question(self, "Logout", 
                                   "Are you sure you want to logout?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            print("DEBUG: User confirmed logout")
            if hasattr(self, 'auth_manager') and self.auth_manager:
                try:
                    self.auth_manager.logout()
                    print("DEBUG: Auth manager logout successful")
                except Exception as e:
                    print(f"DEBUG: Auth manager logout error: {e}")
            
            # Close the main window and restart to show login screen
            print("DEBUG: Closing window and restarting for login...")
            self.close()
            
            # Exit with code 1 to trigger restart in main.py
            from PyQt5.QtWidgets import QApplication
            QApplication.instance().exit(1)
        else:
            print("DEBUG: User cancelled logout")
            # Reset sidebar selection to previous item
            self.sidebar.setCurrentRow(0)
    
    def show_login_dialog(self):
        """Show login dialog for authentication"""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Login - ANPR System")
        dialog.setFixedSize(350, 200)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        username_edit = QLineEdit()
        username_edit.setPlaceholderText("Enter username")
        
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setPlaceholderText("Enter password")
        
        form_layout.addRow("Username:", username_edit)
        form_layout.addRow("Password:", password_edit)
        
        button_layout = QHBoxLayout()
        login_btn = QPushButton("Login")
        cancel_btn = QPushButton("Cancel")
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(login_btn)
        
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        def attempt_login():
            username = username_edit.text().strip()
            password = password_edit.text()
            
            if not username or not password:
                QMessageBox.warning(dialog, "Error", "Please enter both username and password")
                return
            
            try:
                user_data = self.auth_manager.login(username, password)
                QMessageBox.information(dialog, "Success", f"Welcome, {user_data['full_name'] or username}!")
                dialog.accept()
                # Rebuild sidebar to show/hide menu items based on permissions
                self.rebuild_sidebar()
                # Force rebuild of User Management page
                self.rebuild_user_management_page()
            except Exception as e:
                QMessageBox.critical(dialog, "Login Failed", str(e))
        
        login_btn.clicked.connect(attempt_login)
        cancel_btn.clicked.connect(dialog.reject)
        
        # Allow Enter key to login
        username_edit.returnPressed.connect(attempt_login)
        password_edit.returnPressed.connect(attempt_login)
        
        dialog.exec_()
    
    def refresh_current_page(self):
        """Refresh the current page after login"""
        current_index = self.stack.currentIndex()
        if current_index >= 0:
            # Get current sidebar selection and refresh that page
            current_row = self.sidebar.currentRow()
            if current_row >= 0:
                self.on_sidebar_changed(current_row)
    
    def rebuild_sidebar(self):
        """Rebuild sidebar menu based on current user permissions"""
        try:
            # Check if user is logged in
            is_logged_in = self.auth_manager and self.auth_manager.current_username
            print(f"DEBUG: Rebuilding sidebar (logged_in={is_logged_in}, username={self.auth_manager.current_username if self.auth_manager else 'None'})")
            
            # Store current selection
            current_row = self.sidebar.currentRow()
            
            # Clear sidebar
            self.sidebar.clear()
            self.sidebar_items = []
            
            # Rebuild sidebar items to match stack pages (which are already built)
            # The stack was built in build_ui() with dynamic indices
            # We need to rebuild the sidebar items list to match those indices
            
            # Count actual pages in stack to determine correct mapping
            stack_count = self.stack.count()
            print(f"DEBUG: Stack has {stack_count} pages")
            
            # Rebuild sidebar_pages list based on what's actually in the stack
            self.sidebar_pages = []
            
            # Dashboard - always at index 0
            self.sidebar_items.append("▶ Dashboard")
            self.sidebar_pages.append(0)
            
            # Vehicle Log - always at index 1
            self.sidebar_items.append("🚗 Vehicle Log")
            self.sidebar_pages.append(1)
            
            # User Management - conditionally at index 2
            if is_logged_in and self.rbac_controller and self.rbac_controller.can_manage_users():
                self.sidebar_items.append("👥 User Management")
                self.sidebar_pages.append(2)
                print("DEBUG: User Management added to sidebar at index 2")
                
                # Analytics - at index 3 when User Management exists
                self.sidebar_items.append("📊 Analytics")
                self.sidebar_pages.append(3)
                
                # Search Plate - at index 4 when User Management exists
                self.sidebar_items.append("🔍 Search Plate")
                self.sidebar_pages.append(4)
                
                # Settings - at index 5 when User Management exists (if has permission)
                if self.rbac_controller and self.rbac_controller.can_view_settings():
                    self.sidebar_items.append("⚙ Settings")
                    self.sidebar_pages.append(5)
            else:
                # Analytics - at index 2 when User Management doesn't exist
                self.sidebar_items.append("📊 Analytics")
                self.sidebar_pages.append(2)
                
                # Search Plate - at index 3 when User Management doesn't exist
                self.sidebar_items.append("🔍 Search Plate")
                self.sidebar_pages.append(3)
                
                # Settings - at index 4 when User Management doesn't exist (if has permission)
                if self.rbac_controller and self.rbac_controller.can_view_settings():
                    self.sidebar_items.append("⚙ Settings")
                    self.sidebar_pages.append(4)
            
            # Login/Logout based on login status
            if is_logged_in:
                self.sidebar_items.append("🚪 Logout")
                self.sidebar_pages.append(-1)  # Logout
            else:
                self.sidebar_items.append("🔐 Login")
                self.sidebar_pages.append(-2)  # Login
            
            # Add items to sidebar
            self.sidebar.addItems(self.sidebar_items)
            
            # Restore selection or go to dashboard
            if current_row >= 0 and current_row < len(self.sidebar_items):
                self.sidebar.setCurrentRow(current_row)
            else:
                self.sidebar.setCurrentRow(0)
            
            print(f"DEBUG: Sidebar rebuilt with {len(self.sidebar_items)} items")
            print(f"DEBUG: Sidebar pages mapping: {self.sidebar_pages}")
            
        except Exception as e:
            print(f"DEBUG: Error rebuilding sidebar: {e}")
            import traceback
            traceback.print_exc()
    
    def rebuild_user_management_page(self):
        """Rebuild User Management page after login"""
        try:
            # Remove the old page at index 2 (User Management)
            old_widget = self.stack.widget(2)
            if old_widget:
                self.stack.removeWidget(old_widget)
                old_widget.deleteLater()
            
            # Build new User Management page
            user_management_page = self.build_user_management()
            self.stack.insertWidget(2, user_management_page)
            
            # Switch to User Management page
            self.sidebar.setCurrentRow(2)
            self.stack.setCurrentIndex(2)
            
            print("DEBUG: User Management page rebuilt after login")
            
        except Exception as e:
            print(f"DEBUG: Error rebuilding User Management page: {e}")
            import traceback
            traceback.print_exc()

    def apply_settings(self):
        """Apply settings changes"""
        QMessageBox.information(self, "Settings", "Settings applied successfully!")

    def change_license_format(self, text):
        """Change license plate format"""
        from config.license_formats import FORMAT_DISPLAY_NAMES
        if text == FORMAT_DISPLAY_NAMES.get('format1'):
            self.license_format = 'format1'
        elif text == FORMAT_DISPLAY_NAMES.get('format2'):
            self.license_format = 'format2'
        elif text == FORMAT_DISPLAY_NAMES.get('auto'):
            self.license_format = 'auto'
        else:
            # Fallback to format1
            self.license_format = 'format1'
        
        # Clear existing plate data when format changes
        self.vehicle_final_plates.clear()
        self.plate_ownership.clear()
        self.vehicle_plate_candidates.clear()

    def change_tracker_type(self, text):
        """Handle tracker type change from UI"""
        if text == 'Deep SORT':
            new_type = 'DEEPSORT'
        elif text == 'ByteTrack':
            new_type = 'BYTETRACK'
        else:
            new_type = 'SORT'
        if new_type != self.tracker_type:
            self.tracker_type = new_type
            settings.TRACKER_TYPE = new_type
            self.init_tracker()
            # Reset tracking state
            self.setup_tracking()
            try:
                # Notify background worker (connected in ANPRApplication)
                self.trackerTypeChanged.emit(new_type)
            except Exception:
                pass

    def init_tracker(self):
        """Initialize underlying tracker based on current tracker_type"""
        try:
            # Fallback to settings if attribute not yet present
            local_tracker_type = getattr(self, 'tracker_type', getattr(settings, 'TRACKER_TYPE', 'SORT'))
            if str(local_tracker_type).upper() == 'DEEPSORT':
                try:
                    from deep_sort_realtime.deepsort_tracker import DeepSort
                except ImportError:
                    QMessageBox.warning(self, "Deep SORT Missing", "deep-sort-realtime not installed. Falling back to SORT.")
                    self.tracker_type = 'SORT'
                    settings.TRACKER_TYPE = 'SORT'
                
                if str(getattr(self, 'tracker_type', 'SORT')).upper() == 'DEEPSORT':
                    # Initialize DeepSort with approximate mapping of settings
                    self.tracker = DeepSort(
                        max_age=getattr(settings, 'TRACKER_MAX_AGE', 50),
                        n_init=getattr(settings, 'TRACKER_MIN_HITS', 1),
                        max_iou_distance=getattr(settings, 'TRACKER_IOU_THRESHOLD', 0.4),
                    )
                    print("Initialized tracker: Deep SORT")
                    return
            elif str(local_tracker_type).upper() == 'BYTETRACK':
                try:
                    # Ensure local ByteTrack repo is importable (adds '<project>/ByteTrack' to sys.path)
                    try:
                        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                        bt_root = os.path.join(project_root, 'ByteTrack')
                        if os.path.isdir(bt_root) and bt_root not in sys.path:
                            sys.path.insert(0, bt_root)
                        if getattr(settings, 'SHOW_DEBUG_INFO', False):
                            print(f"DEBUG UI: ByteTrack bt_root={bt_root}, exists={os.path.isdir(bt_root)}")
                            try:
                                byte_file = os.path.join(bt_root, 'yolox', 'tracker', 'byte_tracker.py')
                                print(f"DEBUG UI: ByteTrack byte_tracker.py exists={os.path.exists(byte_file)}")
                            except Exception:
                                pass
                    except Exception:
                        pass
                    import_err1 = None
                    import_err2 = None
                    try:
                        from yolox.tracker.byte_tracker import BYTETracker
                    except Exception as e:
                        import_err1 = e
                        BYTETracker = None
                    if BYTETracker is None:
                        try:
                            from bytetrack.byte_tracker import BYTETracker
                        except Exception as e:
                            import_err2 = e
                            BYTETracker = None
                    if BYTETracker is None:
                        raise ImportError(f"BYTETracker not installed. yolox err: {import_err1}; bytetrack err: {import_err2}")

                    from types import SimpleNamespace
                    bt_args = SimpleNamespace(
                        track_thresh=getattr(settings, 'BYTETRACK_TRACK_THRESH', 0.25),
                        match_thresh=getattr(settings, 'BYTETRACK_MATCH_THRESH', 0.8),
                        track_buffer=getattr(settings, 'BYTETRACK_TRACK_BUFFER', 30),
                        mot20=False,
                    )
                    fps = getattr(settings, 'VIDEO_FPS', 30)
                    try:
                        self.tracker = BYTETracker(bt_args, frame_rate=fps)
                    except TypeError:
                        self.tracker = BYTETracker(bt_args, fps)
                    print("Initialized tracker: ByteTrack")
                    return
                except Exception as e:
                    try:
                        msg = f"ByteTrack not installed. Falling back to SORT. Details: {e}"
                    except Exception:
                        msg = "ByteTrack not installed. Falling back to SORT."
                    QMessageBox.warning(self, "ByteTrack Missing", msg)
                    self.tracker_type = 'SORT'
                    settings.TRACKER_TYPE = 'SORT'
            # Default: SORT
            self.tracker = Sort(
                max_age=settings.TRACKER_MAX_AGE,
                min_hits=settings.TRACKER_MIN_HITS,
                iou_threshold=settings.TRACKER_IOU_THRESHOLD
            )
            print("Initialized tracker: SORT")
        except Exception as e:
            print(f"Tracker initialization error: {e}")
            # Fallback to SORT
            self.tracker = Sort(
                max_age=settings.TRACKER_MAX_AGE,
                min_hits=settings.TRACKER_MIN_HITS,
                iou_threshold=settings.TRACKER_IOU_THRESHOLD
            )

    def update_tracker(self, detections, frame=None):
        """Unified tracker update that returns [[x1,y1,x2,y2,track_id], ...]"""
        try:
            # Normalize detections to numpy array of shape (N, 5): [x1,y1,x2,y2,conf]
            if detections is None:
                det_arr = np.empty((0, 5), dtype=float)
            else:
                # Guard against accidental scalar values
                if isinstance(detections, (int, float, np.integer, np.floating)):
                    det_arr = np.empty((0, 5), dtype=float)
                else:
                    det_arr = np.asarray(detections)
                    if det_arr.size == 0:
                        det_arr = np.empty((0, 5), dtype=float)
                    elif det_arr.ndim == 1:
                        # Single detection vector or scalar
                        if det_arr.size >= 4:
                            # If only 4 coords, append conf=1.0
                            if det_arr.size == 4:
                                det_arr = np.hstack([det_arr.astype(float), [1.0]])
                            det_arr = det_arr.reshape(1, -1)
                        else:
                            det_arr = np.empty((0, 5), dtype=float)
                    elif det_arr.ndim == 2:
                        # Ensure we have 5 columns
                        if det_arr.shape[1] == 4:
                            conf_col = np.ones((det_arr.shape[0], 1), dtype=float)
                            det_arr = np.hstack([det_arr.astype(float), conf_col])
                        elif det_arr.shape[1] >= 5:
                            det_arr = det_arr[:, :5].astype(float)
                        else:
                            det_arr = np.empty((0, 5), dtype=float)
                    else:
                        det_arr = np.empty((0, 5), dtype=float)

            ttype = str(self.tracker_type).upper()
            if not hasattr(self, 'tracker') or self.tracker is None:
                return np.empty((0, 5))

            if ttype == 'DEEPSORT':
                # Convert detections to DeepSort expected format: ([x, y, w, h], conf, class)
                det_list = []
                for d in det_arr:
                    x1, y1, x2, y2, conf = float(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4])
                    w = max(0.0, x2 - x1)
                    h = max(0.0, y2 - y1)
                    det_list.append(([x1, y1, w, h], conf, 0))
                tracks = self.tracker.update_tracks(det_list, frame=frame)
                out = []
                for t in tracks:
                    try:
                        if hasattr(t, 'is_confirmed') and not t.is_confirmed():
                            continue
                        bb = t.to_tlbr() if hasattr(t, 'to_tlbr') else None
                        tid = t.track_id if hasattr(t, 'track_id') else None
                        if bb is not None and tid is not None:
                            out.append([bb[0], bb[1], bb[2], bb[3], int(tid)])
                    except Exception:
                        continue
                return np.array(out) if len(out) > 0 else np.empty((0, 5))
            elif ttype == 'BYTETRACK':
                # Prepare Nx5 [x1,y1,x2,y2,score]
                if det_arr.shape[1] < 5:
                    conf_col = np.ones((det_arr.shape[0], 1), dtype=float)
                    det5 = np.hstack([det_arr[:, :4].astype(float), conf_col])
                else:
                    det5 = det_arr[:, :5].astype(float)

                # Determine image size if available
                try:
                    img_h, img_w = (frame.shape[0], frame.shape[1]) if frame is not None else (0, 0)
                except Exception:
                    img_h, img_w = (0, 0)

                # Call update with flexible signatures across versions
                try:
                    tracks = self.tracker.update(det5, (img_h, img_w), (img_h, img_w))
                except TypeError:
                    try:
                        tracks = self.tracker.update(det5, (img_h, img_w))
                    except Exception:
                        return np.empty((0, 5))

                out = []
                for t in tracks:
                    try:
                        # Common YOLOX STrack interface
                        if hasattr(t, 'tlbr'):
                            bb = t.tlbr() if callable(t.tlbr) else t.tlbr
                        elif hasattr(t, 'to_tlbr'):
                            bb = t.to_tlbr()
                        else:
                            bb = None
                        tid = int(t.track_id) if hasattr(t, 'track_id') else None
                        if bb is not None and tid is not None:
                            out.append([bb[0], bb[1], bb[2], bb[3], tid])
                    except Exception:
                        continue
                return np.array(out) if len(out) > 0 else np.empty((0, 5))
            else:
                # Default: SORT expects Nx5 [x1,y1,x2,y2,score]
                return self.tracker.update(det_arr)
        except Exception as e:
            try:
                desc = f"type(detections)={type(detections)}"
            except Exception:
                desc = "diagnostic_unavailable"
            print(f"Tracker update error: {e} | {desc}")
            try:
                print(traceback.format_exc())
            except Exception:
                pass
            # Fallback no tracks
            return np.empty((0, 5))

    def load_image(self):
        """Load and process single image"""
        # Stop live camera if active
        if self.is_live_active:
            self.stop_live_camera()
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            # For single image, request processed overlay to be shown
            self.process_frame(file_path, preview=True)

    def load_video(self):
        """Load video file"""
        # Stop live camera if active
        if self.is_live_active:
            self.stop_live_camera()
            
        self.video_path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.avi *.mov)")
        if self.video_path:
            self.cap = cv2.VideoCapture(self.video_path)
            self.play_btn.setText("▶ Play")
            self.playing = False
            self.frame_counter = 0
            # Initialize playback metrics
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_fps = fps if fps and fps > 0 else self.current_settings.get('VIDEO_FPS', settings.VIDEO_FPS)
            self.total_frames = frame_count if frame_count and frame_count > 0 else 0
            self.base_interval_ms = int(1000 / max(self.video_fps, 1))
            # Setup slider
            self.progress_slider.setMaximum(max(self.total_frames - 1, 0))
            self.progress_slider.setValue(0)
            self.update_time_label(0)

    def toggle_video(self):
        """Toggle video playback"""
        if not self.cap:
            return
        if self.playing:
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                print("DEBUG UI: toggle_video -> stop")
            self.timer.stop()
            self.play_btn.setText("▶ Play")
        else:
            # Use actual video FPS if available
            if not self.video_fps:
                fps_guess = self.cap.get(cv2.CAP_PROP_FPS)
                self.video_fps = fps_guess if fps_guess and fps_guess > 0 else self.current_settings.get('VIDEO_FPS', settings.VIDEO_FPS)
                self.base_interval_ms = int(1000 / max(self.video_fps, 1))
            interval_ms = int(self.base_interval_ms / max(self.playback_speed, 0.01))
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                print(f"DEBUG UI: toggle_video -> start, interval_ms={interval_ms}, speed={self.playback_speed}, fps={self.video_fps}")
            self.timer.start(interval_ms)
            self.play_btn.setText("⏸ Pause")
        self.playing = not self.playing

    def read_frame(self):
        """Read and process video frame"""
        if not self.cap:
            return
        # Do not advance frames unless actively playing
        if not self.playing:
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                print("DEBUG UI: read_frame tick -> skipped (not playing)")
            return
        # If user is actively seeking via slider, skip timer-driven reads to prevent clashes
        if getattr(settings, 'SHOW_DEBUG_INFO', False):
            try:
                pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            except Exception:
                pos = -1
            print(f"DEBUG UI: read_frame tick -> seeking={self.seeking}, stepping={getattr(self, 'stepping_in_progress', False)}, counter={self.frame_counter}, pos={pos}")
        if getattr(self, 'seeking', False) or getattr(self, 'stepping_in_progress', False):
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                print("DEBUG UI: read_frame skipped due to seeking/stepping")
            return
        ret, frame = self.cap.read()
        if not ret:
            # End of video: loop or stop
            if self.loop_enabled and self.total_frames > 0:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    self.timer.stop()
                    self.playing = False
                    self.play_btn.setText("▶ Play")
                    return
            else:
                self.timer.stop()
                self.playing = False
                self.play_btn.setText("▶ Play")
                return

        self.frame_counter += 1
        
        # Debug message showing frame counter
        if getattr(settings, 'SHOW_DEBUG_INFO', False):
            print(f"FRAME COUNTER: {self.frame_counter}")

        # Display current frame once using latest cached overlay to avoid flicker
        self.show_frame_with_cached_detections(frame)

        # Process frame through worker for real-time tracking
        self.process_frame(frame, preview=False)

        # Update progress UI
        self.update_progress_ui()

    def show_plain_frame(self, frame):
        """Display frame without annotations"""
        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img).scaled(700, 400, Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)
    
    def show_frame_with_cached_detections(self, frame):
        """Show frame with cached bounding boxes"""
        show_img = frame.copy()
        
        if not self.hide_bboxes and hasattr(self, 'cached_detections'):
            for detection in self.cached_detections:
                x1, y1, x2, y2, track_id, label = detection
                # Use different colors: blue for tracking, green for finalized plates
                color = (0, 255, 0) if ':' in label else (255, 0, 0)  # Green if has plate, blue if tracking only
                cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(show_img, label, (int(x1), max(10, int(y1-10))), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        self.show_plain_frame(show_img)

    def stop_video(self):
        """Stop playback and reset to start"""
        if not self.cap:
            return
        if getattr(settings, 'SHOW_DEBUG_INFO', False):
            print("DEBUG UI: stop_video -> stop and reset")
        self.timer.stop()
        self.playing = False
        self.play_btn.setText("▶ Play")
        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if ret:
                self.show_plain_frame(frame)
                self.frame_counter = 0
                self.update_progress_ui(force_index=0)
        except Exception as e:
            print(f"Stop error: {e}")

    def on_speed_changed(self, text):
        """Handle playback speed change"""
        try:
            self.playback_speed = float(text.replace('x',''))
        except Exception:
            self.playback_speed = 1.0
        if self.playing and self.base_interval_ms is not None:
            self.timer.stop()
            interval_ms = int(self.base_interval_ms / max(self.playback_speed, 0.01))
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                print(f"DEBUG UI: on_speed_changed -> restart timer, interval_ms={interval_ms}, speed={self.playback_speed}")
            self.timer.start(interval_ms)
        else:
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                try:
                    print(f"DEBUG UI: on_speed_changed -> ignored (playing={self.playing}, base_interval_ms={self.base_interval_ms})")
                except Exception:
                    print("DEBUG UI: on_speed_changed -> ignored")

    def on_slider_pressed(self):
        self.seeking = True
        if getattr(settings, 'SHOW_DEBUG_INFO', False):
            print("DEBUG UI: slider_pressed")

    def on_slider_released(self):
        # Keep seeking flag True until seek completes to block timer-driven reads
        if getattr(settings, 'SHOW_DEBUG_INFO', False):
            try:
                val = self.progress_slider.value()
            except Exception:
                val = None
            print(f"DEBUG UI: slider_released -> target={val}")
        self.seek_to_frame(self.progress_slider.value())
        self.seeking = False

    def on_slider_moved(self, value):
        # live update time label while dragging
        self.update_time_label(value)

    def seek_to_frame(self, index):
        if not self.cap or self.total_frames == 0:
            return
        index = max(0, min(index, self.total_frames - 1))
        try:
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                try:
                    curr = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                except Exception:
                    curr = -1
                print(f"DEBUG UI: seek_to_frame -> request={index}, current={curr}, total={self.total_frames}, playing={self.playing}")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ret, frame = self.cap.read()
            if ret:
                # Adjust because after read(), internal pos moves forward by one
                current_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                if getattr(settings, 'SHOW_DEBUG_INFO', False):
                    print(f"DEBUG UI: seek_to_frame -> read ok, new_index={current_idx}")
                self.frame_counter += 1
                # Display with cached overlay to avoid flicker
                self.show_frame_with_cached_detections(frame)
                # Queue background processing at interval
                if self.frame_counter % settings.DEFAULT_DETECTION_INTERVAL == 0:
                    self.process_frame(frame, preview=False)
                # Update UI
                self.update_progress_ui(force_index=current_idx)
        except Exception as e:
            print(f"Seek error: {e}")

    def step_frame(self, delta):
        if not self.cap or self.total_frames == 0:
            return
        # Prevent re-entrant stepping
        if getattr(self, 'stepping_in_progress', False):
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                print("DEBUG UI: step_frame -> ignored (step already in progress)")
            return
        self.stepping_in_progress = True
        # Always stop timer before stepping to avoid unintended continuous playback
        try:
            # Ensure UI reflects paused state immediately to block any queued ticks
            self.playing = False
            try:
                self.play_btn.setText("▶ Play")
            except Exception:
                pass
            try:
                if hasattr(self, 'timer') and self.timer.isActive():
                    self.timer.stop()
            except Exception:
                pass
            # Determine current index safely
            try:
                current_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            except Exception:
                current_idx = 0
            target = current_idx + delta
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                print(f"DEBUG UI: step_frame -> delta={delta}, current={current_idx}, target={target}, timer_active={self.timer.isActive() if hasattr(self,'timer') else None}")
            # Fast path for +1 to avoid re-seek overhead and reduce backend quirks
            if delta == 1:
                ret, frame = self.cap.read()
                if not ret:
                    # End of video behavior
                    if self.loop_enabled and self.total_frames > 0:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.cap.read()
                    if not ret:
                        return
                self.frame_counter += 1
                self.show_frame_with_cached_detections(frame)
                if self.frame_counter % settings.DEFAULT_DETECTION_INTERVAL == 0:
                    self.process_frame(frame, preview=False)
                try:
                    new_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                except Exception:
                    new_idx = target
                self.update_progress_ui(force_index=max(0, min(new_idx, self.total_frames - 1)))
            else:
                self.seek_to_frame(target)
        finally:
            # Enforce paused state and ensure timer stays stopped after stepping
            try:
                if hasattr(self, 'timer') and self.timer.isActive():
                    self.timer.stop()
            except Exception:
                pass
            self.playing = False
            try:
                self.play_btn.setText("▶ Play")
            except Exception:
                pass
            if getattr(settings, 'SHOW_DEBUG_INFO', False):
                try:
                    print("DEBUG UI: step_frame -> finalize: playing=False, timer stopped")
                except Exception:
                    pass
            self.stepping_in_progress = False

    def update_progress_ui(self, force_index=None):
        if not self.cap or self.total_frames == 0:
            return
        if force_index is not None:
            idx = force_index
        else:
            idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        idx = max(0, min(idx, self.total_frames - 1))
        # Avoid signal feedback
        self.suppress_slider_update = True
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(idx)
        self.progress_slider.blockSignals(False)
        self.suppress_slider_update = False
        self.update_time_label(idx)

    def update_time_label(self, frame_index):
        if not self.video_fps or self.video_fps <= 0:
            self.time_label.setText("--:-- / --:--")
            return
        current_sec = frame_index / self.video_fps
        total_sec = (self.total_frames / self.video_fps) if self.total_frames else 0
        self.time_label.setText(f"{self.format_time(current_sec)} / {self.format_time(total_sec)}")

    @staticmethod
    def format_time(seconds):
        seconds = int(max(0, seconds))
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def update_dashboard_cards(self):
        """Update dashboard cards with current statistics"""
        self.tracked_card.setText(f"Total Tracked\n{self.total_tracked}")
        self.unique_plates_card.setText(f"Unique Plates\n{self.unique_plates_detected}")
        self.valid_plates_card.setText(f"Valid Plates\n{self.valid_plates_count}")
        self.missed_plates_card.setText(f"Missed Plates\n{self.missed_plates_count}")
    
    def add_plate_to_preview(self, plate_img, vehicle_id, ocr_text, confidence, is_valid):
        """Add detected plate to the preview panel"""
        try:
            # Create plate preview widget
            plate_widget = QWidget()
            plate_widget.setFixedHeight(100)
            plate_widget.setStyleSheet("border: 1px solid #ccc; margin: 5px; border-radius: 5px;")
            
            plate_layout = QHBoxLayout(plate_widget)
            
            # Plate image
            plate_label = QLabel()
            if plate_img is not None and plate_img.size > 0:
                # Convert to QPixmap
                if len(plate_img.shape) == 3:
                    plate_rgb = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB)
                    h, w, ch = plate_rgb.shape
                    bytes_per_line = ch * w
                    qt_img = QImage(plate_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    plate_pixmap = QPixmap.fromImage(qt_img).scaled(120, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    plate_label.setPixmap(plate_pixmap)
                else:
                    plate_label.setText("Invalid Image")
            else:
                plate_label.setText("No Image")
            
            plate_label.setFixedSize(120, 60)
            plate_label.setAlignment(Qt.AlignCenter)
            plate_label.setStyleSheet("border: 1px solid #ddd;")
            
            # Plate info
            info_label = QLabel()
            status = "✅ VALID" if is_valid else "❌ INVALID"
            text_display = ocr_text if ocr_text else "No Text"
            conf_display = f"{confidence:.2f}" if confidence else "0.00"
            
            info_text = f"Vehicle: {vehicle_id}\nText: '{text_display}'\nConf: {conf_display}\nStatus: {status}"
            info_label.setText(info_text)
            info_label.setFont(QFont("Arial", 9))
            info_label.setStyleSheet("padding: 5px;")
            
            plate_layout.addWidget(plate_label)
            plate_layout.addWidget(info_label)
            
            # Add to plates layout (at top)
            self.plates_layout.insertWidget(0, plate_widget)
            
            # Keep only last 20 plates to avoid memory issues
            if self.plates_layout.count() > 20:
                old_widget = self.plates_layout.itemAt(20).widget()
                if old_widget:
                    old_widget.setParent(None)
            
        except Exception as e:
            print(f"Error adding plate to preview: {e}")

    def closeEvent(self, event):
        """Cleanup temp files and release resources on close"""
        try:
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            if hasattr(self, 'cap') and self.cap:
                self.cap.release()
            # Remove session temp directory (including debug images)
            if hasattr(self, 'session_temp_dir') and os.path.isdir(self.session_temp_dir):
                shutil.rmtree(self.session_temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"Cleanup error on close: {e}")
        super().closeEvent(event)
    
    # Process frame method will be in the main application file
    def process_frame(self, frame_path, preview=False, source="file"):
        """This method will be implemented in the main application"""
        pass

    def toggle_live_camera(self):
        """Toggle live camera feed"""
        if not self.is_live_active:
            self.start_live_camera()
        else:
            self.stop_live_camera()
    
    def start_live_camera(self):
        """Start live camera feed"""
        try:
            # Get selected camera index
            self.selected_camera_index = self.camera_combo.currentData()
            if self.selected_camera_index is None:
                QMessageBox.warning(self, "Camera Error", "No camera selected. Please select a camera from the dropdown.")
                return
            
            # Handle IP camera
            if self.selected_camera_index == 'ip_camera':
                ip_address = self.ip_input.text().strip()
                if not ip_address:
                    QMessageBox.warning(self, "IP Camera Error", "Please enter DroidCam IP address (e.g., 192.168.1.100:4747)")
                    return
                
                # Clean up IP address - remove http:// if user added it
                if ip_address.startswith('http://'):
                    ip_address = ip_address[7:]
                elif ip_address.startswith('https://'):
                    ip_address = ip_address[8:]
                
                # Try different DroidCam URL formats
                urls_to_try = [
                    f"http://{ip_address}/video",
                    f"http://{ip_address}/mjpegfeed?640x480",
                    f"http://{ip_address}/cam/1/stream"
                ]
                
                # If no port specified, also try with :4747
                if ':' not in ip_address:
                    urls_to_try.extend([
                        f"http://{ip_address}:4747/video",
                        f"http://{ip_address}:4747/mjpegfeed?640x480"
                    ])
                
                self.webcam = None
                for url in urls_to_try:
                    try:
                        print(f"Trying to connect to: {url}")
                        self.webcam = cv2.VideoCapture(url)
                        if self.webcam.isOpened():
                            # Test if we can read a frame
                            ret, frame = self.webcam.read()
                            if ret and frame is not None:
                                print(f"✅ Successfully connected to DroidCam at: {url}")
                                break
                            else:
                                self.webcam.release()
                                self.webcam = None
                        else:
                            if self.webcam:
                                self.webcam.release()
                            self.webcam = None
                    except Exception as e:
                        print(f"Failed to connect to {url}: {e}")
                        if self.webcam:
                            self.webcam.release()
                        self.webcam = None
                
                if self.webcam is None or not self.webcam.isOpened():
                    QMessageBox.warning(self, "IP Camera Error", 
                                      f"Could not connect to DroidCam at {ip_address}.\n\n"
                                      f"Make sure:\n"
                                      f"1. DroidCam app is running on your phone\n"
                                      f"2. WiFi IP is enabled in DroidCam\n"
                                      f"3. Both devices are on same network\n"
                                      f"4. IP address is correct (check DroidCam app)")
                    return
            else:
                # Regular camera by index
                if isinstance(self.selected_camera_index, str):
                    self.webcam = cv2.VideoCapture(self.selected_camera_index, cv2.CAP_DSHOW)
                    if not self.webcam.isOpened():
                        self.webcam = cv2.VideoCapture(self.selected_camera_index)
                else:
                    self.webcam = cv2.VideoCapture(self.selected_camera_index, cv2.CAP_DSHOW)
                    if not self.webcam.isOpened():
                        self.webcam = cv2.VideoCapture(self.selected_camera_index)
                
                if not self.webcam.isOpened():
                    QMessageBox.warning(self, "Camera Error", f"Could not access camera {self.selected_camera_index}. Please check if camera is connected and not being used by another application.")
                    return
            
            # Set camera properties for better performance
            self.webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.webcam.set(cv2.CAP_PROP_FPS, 30)
            
            # Start timer for frame capture
            self.webcam_timer = QTimer()
            self.webcam_timer.timeout.connect(self.capture_webcam_frame)
            self.webcam_timer.start(33)  # ~30 FPS
            
            # Update UI
            self.is_live_active = True
            self.live_btn.setText("Stop Live Camera")
            self.live_btn.setStyleSheet("padding: 10px; background-color: #e74c3c; color: white; border-radius: 5px;")
            
            print("Live camera started successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Camera Error", f"Failed to start camera: {str(e)}")
            print(f"Error starting camera: {e}")
    
    def stop_live_camera(self):
        """Stop live camera feed"""
        try:
            # Stop timer
            if self.webcam_timer:
                self.webcam_timer.stop()
                self.webcam_timer = None
            
            # Release webcam
            if self.webcam:
                self.webcam.release()
                self.webcam = None
            
            # Update UI
            self.is_live_active = False
            self.live_btn.setText("Start Live Camera")
            self.live_btn.setStyleSheet("padding: 10px; background-color: #27ae60; color: white; border-radius: 5px;")
            
            print("Live camera stopped")
            
        except Exception as e:
            print(f"Error stopping camera: {e}")
    
    def capture_webcam_frame(self):
        """Capture and process frame from webcam"""
        if not self.webcam or not self.webcam.isOpened():
            return
            
        ret, frame = self.webcam.read()
        if not ret:
            return
        
        # Display webcam feed in the video player area
        self.display_webcam_frame(frame)
            
        # Apply frame skip for performance
        if not hasattr(self, 'webcam_frame_count'):
            self.webcam_frame_count = 0
            
        # Skip frames based on settings for processing (not display)
        frame_skip = getattr(settings, 'DEFAULT_FRAME_SKIP', 2)
        
        self.webcam_frame_count += 1
        if self.webcam_frame_count % frame_skip != 0:
            return
        
        # Convert frame to the format expected by process_frame
        # Save frame temporarily and process it
        temp_path = os.path.join(self.session_temp_dir, f"webcam_frame_{self.webcam_frame_count}.jpg")
        cv2.imwrite(temp_path, frame)
        
        # Process frame using existing pipeline with preview disabled (we're already showing live feed)
        self.process_frame(temp_path, preview=False)
        
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass
    
    def display_webcam_frame(self, frame):
        """Display webcam frame in the video player area"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            # Create QImage and QPixmap
            qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img).scaled(700, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Display in the video player area
            self.image_label.setPixmap(pixmap)
        except Exception as e:
            print(f"Error displaying webcam frame: {e}")
    
    def detect_cameras(self):
        """Detect available camera devices"""
        self.available_cameras = []
        
        print("Scanning for cameras...")
        
        # Add IP Camera option
        self.available_cameras.append({
            'index': 'ip_camera',
            'name': 'DroidCam IP Stream',
            'resolution': 'Variable',
            'fps': 30,
            'backend': 'HTTP/RTSP'
        })
        
        # Test camera indices 0-5 for regular cameras
        for i in range(6):
            try:
                camera_found = False
                camera_info = None
                
                backends = [
                    (cv2.CAP_DSHOW, "DSHOW"),
                    (-1, "DEFAULT")
                ]
                
                for backend_id, backend_name in backends:
                    try:
                        if backend_id == -1:
                            cap = cv2.VideoCapture(i)
                        else:
                            cap = cv2.VideoCapture(i, backend_id)
                        
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                fps = int(cap.get(cv2.CAP_PROP_FPS))
                                
                                camera_info = {
                                    'index': i,
                                    'name': f"Camera {i} (Built-in)" if i == 0 else f"Camera {i}",
                                    'resolution': f"{width}x{height}",
                                    'fps': fps,
                                    'backend': backend_name
                                }
                                
                                camera_found = True
                                print(f"Found camera {i}: {camera_info['name']} - {width}x{height} @ {fps}fps ({backend_name})")
                                break
                        
                        cap.release()
                        
                    except Exception:
                        if 'cap' in locals():
                            cap.release()
                        continue
                
                if camera_found and camera_info:
                    self.available_cameras.append(camera_info)
                    
            except Exception:
                continue
        
        if len(self.available_cameras) == 1:  # Only IP camera option
            print("No local cameras detected, IP camera option available")
        
        print(f"Camera detection complete. Found {len(self.available_cameras)} camera option(s).")
    
    def get_droidcam_device_names(self):
        """Get DroidCam device names for direct access"""
        device_names = []
        try:
            import subprocess
            
            # Get all video devices from Windows
            result = subprocess.run(['wmic', 'path', 'win32_pnpentity', 'where', 'name like "%video%"', 'get', 'name'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    line = line.strip()
                    if 'DroidCam' in line:
                        device_names.append(line)
                        print(f"Found DroidCam device: {line}")
            
            # Also try common DroidCam device names
            common_names = [
                "DroidCam Video",
                "DroidCam Source 3",
                "DroidCam Source 2", 
                "DroidCam Source 1",
                "DroidCam"
            ]
            
            for name in common_names:
                if name not in device_names:
                    device_names.append(name)
                    
        except Exception as e:
            print(f"Could not get DroidCam device names: {e}")
            
        return device_names
    
    def populate_camera_combo(self):
        """Populate camera selection combo box"""
        self.camera_combo.clear()
        
        for camera in self.available_cameras:
            display_text = f"{camera['name']} ({camera['resolution']})"
            if camera['fps'] > 0:
                display_text += f" @ {camera['fps']}fps"
            
            self.camera_combo.addItem(display_text, camera['index'])
        
        # Set default selection to first available camera
        if self.available_cameras and self.available_cameras[0]['fps'] > 0:
            self.camera_combo.setCurrentIndex(0)
    
    def refresh_cameras(self):
        """Refresh camera list and update combo box"""
        self.detect_cameras()
        self.populate_camera_combo()
