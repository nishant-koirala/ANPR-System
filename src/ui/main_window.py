import sys
import os
import cv2
import numpy as np
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
from src.detection.vehicle_detector import VehicleDetector
from src.detection.plate_detector import PlateDetector
from src.ocr.plate_reader import PlateReader

class PlateDetectorDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ANPR - Entry Gate System")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize components
        self.setup_models()
        self.setup_tracking()
        self.setup_ui_state()
        
        # Initialize settings
        self.current_settings = {}
        self.load_settings()
        
        # Prepare temp directories for this session
        self.setup_temp_dirs()
        
        # Build UI
        self.build_ui()

    def setup_models(self):
        """Initialize detection models and OCR"""
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")
        
        self.vehicle_detector = VehicleDetector(self.device)
        self.plate_detector = PlateDetector(self.device)
        self.plate_reader = PlateReader()
        
        # SORT tracker
        self.tracker = Sort(
            max_age=settings.TRACKER_MAX_AGE, 
            min_hits=settings.TRACKER_MIN_HITS, 
            iou_threshold=settings.TRACKER_IOU_THRESHOLD
        )

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
        
        # Settings
        self.license_format = 'auto'
        self.frame_skip = settings.DEFAULT_FRAME_SKIP
        self.hide_bboxes = False
        self.camera_source = "video"
        self.log_file_path = os.path.expanduser("~")
        self.manual_export_mode = "Manual Export"
        self.auto_backup_interval = "Daily"
        
        # Counters for dashboard cards
        self.total_tracked = 0
        self.unique_plates_detected = 0
        self.valid_plates_count = 0
        self.missed_plates_count = 0
        self.all_detected_plates = []  # Store all plate detections for display
        
        # Connect timer
        self.timer.timeout.connect(self.read_frame)

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
        self.current_settings.update({
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
            'USE_GPU': self.gpu_check.isChecked()
        })
        
        # Update config module
        for setting, value in self.current_settings.items():
            if hasattr(settings, setting):
                setattr(settings, setting, value)
        
        # Show confirmation
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully!")
        
        # Apply settings to running processes if needed
        self.apply_runtime_settings()
    
    def apply_runtime_settings(self):
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

    def build_ui(self):
        """Build the main UI"""
        main_layout = QHBoxLayout(self)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(150)
        self.sidebar.addItems([
            "▶ Dashboard",
            "📈 Database", 
            "🔍 Search Plate",
            "⚙ Settings",
            "🚪 Logout"
        ])
        self.sidebar.setCurrentRow(0)
        self.sidebar.setStyleSheet(
            "QListWidget { background-color: #f5f6fa; font-size: 14px; } "
            "QListWidget::item { padding: 20px; }"
        )
        self.sidebar.currentRowChanged.connect(self.on_sidebar_changed)

        # Stack (Dashboard + Settings)
        self.stack = QStackedWidget()
        self.dashboard_page = self.build_dashboard_page()
        self.settings_page = self.build_settings_page()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

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

        # Upload buttons
        upload_btns = QHBoxLayout()
        image_btn = QPushButton("Upload Image")
        image_btn.clicked.connect(self.load_image)
        video_btn = QPushButton("Upload Video")
        video_btn.clicked.connect(self.load_video)
        for btn in [image_btn, video_btn]:
            btn.setStyleSheet("padding: 10px; background-color: #0984e3; color: white; border-radius: 5px;")
            upload_btns.addWidget(btn)
        content_layout.addLayout(upload_btns)

        # Vehicle counter
        counter_layout = QHBoxLayout()
        self.vehicle_counter_label = QLabel("Vehicles: 0 | Finalized Plates: 0 | Unique Plates: 0")
        self.vehicle_counter_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.vehicle_counter_label.setStyleSheet("color: #2980b9; padding: 10px; background-color: #ecf0f1; border-radius: 5px;")
        counter_layout.addWidget(self.vehicle_counter_label)
        counter_layout.addStretch()
        content_layout.addLayout(counter_layout)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["S.no", "Plate Image", "Plate No. (Vehicle ID)", "Type", "Date", "TimeStamp", "Site (Confidence)"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFixedHeight(200)
        self.table.setColumnWidth(1, 120)
        self.table.setRowHeight(0, 80)
        content_layout.addWidget(self.table)

        return page

    def build_settings_page(self):
        """Build comprehensive settings page"""
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

        # Add comprehensive settings groups
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
        if index == 3:  # Settings
            self.stack.setCurrentIndex(1)
        else:  # Dashboard
            self.stack.setCurrentIndex(0)

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

    def load_image(self):
        """Load and process single image"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.process_frame(file_path, preview=False)

    def load_video(self):
        """Load video file"""
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
            self.timer.stop()
            self.play_btn.setText("▶ Play")
        else:
            # Use actual video FPS if available
            if not self.video_fps:
                fps_guess = self.cap.get(cv2.CAP_PROP_FPS)
                self.video_fps = fps_guess if fps_guess and fps_guess > 0 else self.current_settings.get('VIDEO_FPS', settings.VIDEO_FPS)
                self.base_interval_ms = int(1000 / max(self.video_fps, 1))
            interval_ms = int(self.base_interval_ms / max(self.playback_speed, 0.01))
            self.timer.start(interval_ms)
            self.play_btn.setText("⏸ Pause")
        self.playing = not self.playing

    def read_frame(self):
        """Read and process video frame"""
        if not self.cap:
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

        # Show preview
        if self.hide_bboxes:
            self.show_plain_frame(frame)
        else:
            self.show_plain_frame(frame)

        # Run detection every 2nd frame
        if self.frame_counter % settings.DEFAULT_DETECTION_INTERVAL == 0:
            self.process_frame(frame, preview=True)
        else:
            self.show_frame_with_cached_detections(frame)

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
                cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(show_img, f'{label} {track_id}', (int(x1), int(y1-10)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        self.show_plain_frame(show_img)

    def stop_video(self):
        """Stop playback and reset to start"""
        if not self.cap:
            return
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
            self.timer.start(interval_ms)

    def on_slider_pressed(self):
        self.seeking = True

    def on_slider_released(self):
        self.seeking = False
        self.seek_to_frame(self.progress_slider.value())

    def on_slider_moved(self, value):
        # live update time label while dragging
        self.update_time_label(value)

    def seek_to_frame(self, index):
        if not self.cap or self.total_frames == 0:
            return
        index = max(0, min(index, self.total_frames - 1))
        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ret, frame = self.cap.read()
            if ret:
                # Adjust because after read(), internal pos moves forward by one
                current_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                self.frame_counter += 1
                # Display
                if self.frame_counter % settings.DEFAULT_DETECTION_INTERVAL == 0:
                    self.process_frame(frame, preview=True)
                else:
                    self.show_frame_with_cached_detections(frame)
                # Update UI
                self.update_progress_ui(force_index=current_idx)
        except Exception as e:
            print(f"Seek error: {e}")

    def step_frame(self, delta):
        if not self.cap or self.total_frames == 0:
            return
        # Pause if playing
        if self.playing:
            self.toggle_video()
        current_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        target = current_idx + delta
        self.seek_to_frame(target)

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
    def process_frame(self, file_path, preview=False):
        """This method will be implemented in the main application"""
        pass
