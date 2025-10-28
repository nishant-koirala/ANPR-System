import os
import cv2
import numpy as np
from datetime import datetime
from collections import defaultdict

from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QTableWidget,
    QTableWidgetItem, QScrollArea, QSlider, QComboBox, QCheckBox, QApplication, QGroupBox,
    QRadioButton, QLineEdit, QSpinBox, QDoubleSpinBox, QTabWidget, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QTimer

class SettingsPage(QWidget):
    def __init__(self, parent=None, rbac_controller=None):
        super().__init__(parent)
        self.parent = parent
        self.rbac_controller = rbac_controller
        self.build_ui()
        self.apply_permissions()

    def build_ui(self):
        """Build settings page"""
        content_layout = QVBoxLayout(self)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
                min-width: 100px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)
        
        # Model Settings
        model_tab = QWidget()
        model_tab_layout = QVBoxLayout(model_tab)
        model_tab_layout.setSpacing(10)
        model_tab_layout.setContentsMargins(10, 10, 10, 10)
        model_tab_layout.addWidget(self.create_model_settings())
        model_tab_layout.addStretch()
        tabs.addTab(model_tab, "Model")
        
        # Detection Settings
        detection_tab = QWidget()
        detection_tab_layout = QVBoxLayout(detection_tab)
        detection_tab_layout.setSpacing(10)
        detection_tab_layout.setContentsMargins(10, 10, 10, 10)
        detection_tab_layout.addWidget(self.create_detection_settings())
        detection_tab_layout.addStretch()
        tabs.addTab(detection_tab, "Detection")
        
        # OCR Settings
        ocr_tab = QWidget()
        ocr_tab_layout = QVBoxLayout(ocr_tab)
        ocr_tab_layout.setSpacing(10)
        ocr_tab_layout.setContentsMargins(10, 10, 10, 10)
        ocr_tab_layout.addWidget(self.create_ocr_settings())
        ocr_tab_layout.addStretch()
        tabs.addTab(ocr_tab, "OCR")
        
        # Performance Settings
        perf_tab = QWidget()
        perf_tab_layout = QVBoxLayout(perf_tab)
        perf_tab_layout.setSpacing(10)
        perf_tab_layout.setContentsMargins(10, 10, 10, 10)
        perf_tab_layout.addWidget(self.create_performance_settings())
        perf_tab_layout.addStretch()
        tabs.addTab(perf_tab, "Performance")
        
        # Video Processing Settings
        video_tab = QWidget()
        video_tab_layout = QVBoxLayout(video_tab)
        video_tab_layout.setSpacing(10)
        video_tab_layout.setContentsMargins(10, 10, 10, 10)
        video_tab_layout.addWidget(self.create_video_settings())
        video_tab_layout.addStretch()
        tabs.addTab(video_tab, "Video Processing")
        
        # Parking Fee Settings
        parking_tab = QWidget()
        parking_tab_layout = QVBoxLayout(parking_tab)
        parking_tab_layout.setSpacing(10)
        parking_tab_layout.setContentsMargins(10, 10, 10, 10)
        parking_tab_layout.addWidget(self.create_parking_settings())
        parking_tab_layout.addStretch()
        tabs.addTab(parking_tab, "Parking Fees")
        
        content_layout.addWidget(tabs)

        # Save and Apply buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setStyleSheet("padding: 10px; background-color: #27ae60; color: white; border-radius: 5px;")
        self.apply_btn = QPushButton("Apply Settings")
        self.apply_btn.clicked.connect(self.apply_runtime_settings)
        self.apply_btn.setStyleSheet("padding: 10px; background-color: #2980b9; color: white; border-radius: 5px;")
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.apply_btn)
        content_layout.addLayout(btn_layout)

    def create_model_settings(self):
        """Create model settings group"""
        group = QGroupBox("Model Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Vehicle model selector
        vehicle_layout = QHBoxLayout()
        vehicle_layout.setSpacing(10)
        vehicle_label = QLabel("Vehicle Detection Model:")
        vehicle_label.setMinimumWidth(150)
        vehicle_layout.addWidget(vehicle_label)
        self.vehicle_model_combo = QComboBox()
        self.vehicle_model_combo.addItems(["YOLOv8n", "YOLOv8m", "YOLOv8l"])
        self.vehicle_model_combo.setMaximumWidth(200)
        vehicle_layout.addWidget(self.vehicle_model_combo)
        vehicle_layout.addStretch()
        layout.addLayout(vehicle_layout)
        
        # Plate model selector
        plate_layout = QHBoxLayout()
        plate_layout.setSpacing(10)
        plate_label = QLabel("Plate Detection Model:")
        plate_label.setMinimumWidth(150)
        plate_layout.addWidget(plate_label)
        self.plate_model_combo = QComboBox()
        self.plate_model_combo.addItems(["best.pt"])
        self.plate_model_combo.setMaximumWidth(200)
        plate_layout.addWidget(self.plate_model_combo)
        plate_layout.addStretch()
        layout.addLayout(plate_layout)
        
        # OCR model selector
        ocr_layout = QHBoxLayout()
        ocr_layout.setSpacing(10)
        ocr_label = QLabel("OCR Model:")
        ocr_label.setMinimumWidth(150)
        ocr_layout.addWidget(ocr_label)
        self.ocr_model_combo = QComboBox()
        self.ocr_model_combo.addItems(["EasyOCR", "Tesseract", "Custom CRNN"])
        self.ocr_model_combo.setMaximumWidth(200)
        ocr_layout.addWidget(self.ocr_model_combo)
        ocr_layout.addStretch()
        layout.addLayout(ocr_layout)
        
        return group

    def create_detection_settings(self):
        """Create detection settings group"""
        group = QGroupBox("Detection Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Confidence threshold
        conf_layout = QHBoxLayout()
        conf_layout.setSpacing(10)
        conf_label = QLabel("Confidence Threshold:")
        conf_label.setMinimumWidth(150)
        conf_layout.addWidget(conf_label)
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 0.99)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.5)
        self.conf_spin.setMaximumWidth(100)
        conf_layout.addWidget(self.conf_spin)
        conf_layout.addStretch()
        layout.addLayout(conf_layout)
        
        # IOU threshold
        iou_layout = QHBoxLayout()
        iou_layout.setSpacing(10)
        iou_label = QLabel("IOU Threshold:")
        iou_label.setMinimumWidth(150)
        iou_layout.addWidget(iou_label)
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.1, 0.99)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(0.7)
        self.iou_spin.setMaximumWidth(100)
        iou_layout.addWidget(self.iou_spin)
        iou_layout.addStretch()
        layout.addLayout(iou_layout)
        
        # Tracking method
        track_layout = QHBoxLayout()
        track_layout.setSpacing(10)
        track_label = QLabel("Tracking Method:")
        track_label.setMinimumWidth(150)
        track_layout.addWidget(track_label)
        self.track_combo = QComboBox()
        self.track_combo.addItems(["ByteTrack", "SORT", "DeepSORT", "Custom"])
        self.track_combo.setMaximumWidth(200)
        track_layout.addWidget(self.track_combo)
        track_layout.addStretch()
        layout.addLayout(track_layout)
        
        return group

    def create_ocr_settings(self):
        """Create OCR settings group"""
        group = QGroupBox("OCR Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # OCR language
        lang_layout = QHBoxLayout()
        lang_layout.setSpacing(10)
        lang_label = QLabel("Language:")
        lang_label.setMinimumWidth(120)
        lang_layout.addWidget(lang_label)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["en", "ne"])
        self.lang_combo.setMaximumWidth(200)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # License plate format selector
        format_layout = QHBoxLayout()
        format_layout.setSpacing(10)
        format_label = QLabel("License Format:")
        format_label.setMinimumWidth(120)
        format_layout.addWidget(format_label)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Automatic: Try all formats", "Format 1: AA00AAA (7 characters)", "Format 2: AA 1111 (6 characters)", "Format 3: A AA 1111 (7 characters)"])
        self.format_combo.setMaximumWidth(300)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Character whitelist
        whitelist_layout = QHBoxLayout()
        whitelist_layout.setSpacing(10)
        whitelist_label = QLabel("Character Whitelist:")
        whitelist_label.setMinimumWidth(120)
        whitelist_layout.addWidget(whitelist_label)
        self.whitelist_edit = QLineEdit("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.whitelist_edit.setMaximumWidth(400)
        whitelist_layout.addWidget(self.whitelist_edit)
        whitelist_layout.addStretch()
        layout.addLayout(whitelist_layout)
        
        # Post-processing
        post_layout = QHBoxLayout()
        post_layout.setSpacing(10)
        self.post_check = QCheckBox("Enable Post-processing")
        self.post_check.setChecked(True)
        post_layout.addWidget(self.post_check)
        post_layout.addStretch()
        layout.addLayout(post_layout)
        
        return group

    def create_performance_settings(self):
        """Create performance settings group"""
        group = QGroupBox("Performance Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Thread count
        thread_layout = QHBoxLayout()
        thread_layout.setSpacing(10)
        thread_label = QLabel("Thread Count:")
        thread_label.setMinimumWidth(150)
        thread_layout.addWidget(thread_label)
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 8)
        self.thread_spin.setValue(4)
        self.thread_spin.setMaximumWidth(100)
        thread_layout.addWidget(self.thread_spin)
        thread_layout.addStretch()
        layout.addLayout(thread_layout)
        
        # GPU acceleration
        gpu_layout = QHBoxLayout()
        gpu_layout.setSpacing(10)
        self.gpu_check = QCheckBox("Enable GPU Acceleration")
        self.gpu_check.setChecked(True)
        gpu_layout.addWidget(self.gpu_check)
        gpu_layout.addStretch()
        layout.addLayout(gpu_layout)
        
        # Batch size
        batch_layout = QHBoxLayout()
        batch_layout.setSpacing(10)
        batch_label = QLabel("Batch Size:")
        batch_label.setMinimumWidth(150)
        batch_layout.addWidget(batch_label)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 16)
        self.batch_spin.setValue(1)
        self.batch_spin.setMaximumWidth(100)
        batch_layout.addWidget(self.batch_spin)
        batch_layout.addStretch()
        layout.addLayout(batch_layout)
        
        return group
    
    def create_video_settings(self):
        """Create video processing settings group"""
        group = QGroupBox("Video Processing Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Frame skip setting
        frame_skip_layout = QHBoxLayout()
        frame_skip_layout.setSpacing(10)
        frame_skip_label = QLabel("Frame Skip:")
        frame_skip_label.setMinimumWidth(150)
        frame_skip_layout.addWidget(frame_skip_label)
        self.frame_skip_combo = QComboBox()
        self.frame_skip_combo.addItems(["1 (Process every frame)", "2 (Skip 1 frame)", "3 (Skip 2 frames)", "4 (Skip 3 frames)", "5 (Skip 4 frames)", "10 (Skip 9 frames)"])
        self.frame_skip_combo.setCurrentIndex(1)  # Default to 2
        self.frame_skip_combo.setMaximumWidth(200)
        frame_skip_layout.addWidget(self.frame_skip_combo)
        frame_skip_layout.addStretch()
        layout.addLayout(frame_skip_layout)
        
        # Detection interval setting
        detection_interval_layout = QHBoxLayout()
        detection_interval_layout.setSpacing(10)
        detection_interval_label = QLabel("Detection Interval:")
        detection_interval_label.setMinimumWidth(150)
        detection_interval_layout.addWidget(detection_interval_label)
        self.detection_interval_spin = QSpinBox()
        self.detection_interval_spin.setRange(1, 10)
        self.detection_interval_spin.setValue(2)
        self.detection_interval_spin.setMaximumWidth(100)
        detection_interval_layout.addWidget(self.detection_interval_spin)
        detection_interval_layout.addStretch()
        layout.addLayout(detection_interval_layout)
        
        # Load current settings
        self.load_video_settings()
        
        return group

    def create_parking_settings(self):
        """Create parking fee settings group"""
        group = QGroupBox("Parking Fee Configuration")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Hourly rate
        rate_layout = QHBoxLayout()
        rate_layout.setSpacing(10)
        rate_label = QLabel("Hourly Rate (NPR):")
        rate_label.setMinimumWidth(150)
        rate_layout.addWidget(rate_label)
        self.hourly_rate_spin = QDoubleSpinBox()
        self.hourly_rate_spin.setRange(1.0, 1000.0)
        self.hourly_rate_spin.setSingleStep(5.0)
        self.hourly_rate_spin.setValue(50.0)  # Default value
        self.hourly_rate_spin.setDecimals(2)
        self.hourly_rate_spin.setMaximumWidth(120)
        rate_layout.addWidget(self.hourly_rate_spin)
        rate_layout.addStretch()
        layout.addLayout(rate_layout)
        
        # Minimum charge hours
        min_layout = QHBoxLayout()
        min_layout.setSpacing(10)
        min_label = QLabel("Minimum Charge (Hours):")
        min_label.setMinimumWidth(150)
        min_layout.addWidget(min_label)
        self.min_hours_spin = QDoubleSpinBox()
        self.min_hours_spin.setRange(0.25, 24.0)
        self.min_hours_spin.setSingleStep(0.25)
        self.min_hours_spin.setValue(1.0)  # Default value
        self.min_hours_spin.setDecimals(2)
        self.min_hours_spin.setMaximumWidth(120)
        min_layout.addWidget(self.min_hours_spin)
        min_layout.addStretch()
        layout.addLayout(min_layout)
        
        # Preview calculation
        preview_group = QGroupBox("Rate Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setSpacing(5)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet(
            "background-color: #f8f9fa; "
            "padding: 10px; "
            "border-radius: 5px; "
            "border: 1px solid #dee2e6;"
        )
        self.update_preview()
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)
        
        # Connect signals to update preview
        self.hourly_rate_spin.valueChanged.connect(self.update_preview)
        self.min_hours_spin.valueChanged.connect(self.update_preview)
        
        # Load current settings
        self.load_parking_settings()
        self.load_format_settings()
        
        return group
    
    def update_preview(self):
        """Update the parking rate preview"""
        rate = self.hourly_rate_spin.value()
        min_hours = self.min_hours_spin.value()
        
        preview_text = f"""
• 30 minutes: NPR {max(0.5, min_hours) * rate:.2f}
• 1 hour: NPR {max(1.0, min_hours) * rate:.2f}
• 2 hours: NPR {max(2.0, min_hours) * rate:.2f}
• 4 hours: NPR {max(4.0, min_hours) * rate:.2f}
        """.strip()
        
        self.preview_label.setText(preview_text)
        self.preview_label.setStyleSheet("background-color: #f8f9fa; padding: 10px; border-radius: 5px;")
    
    def load_parking_settings(self):
        """Load current parking settings from config"""
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from config.settings import PARKING_HOURLY_RATE, MINIMUM_CHARGE_HOURS
            
            self.hourly_rate_spin.setValue(PARKING_HOURLY_RATE)
            self.min_hours_spin.setValue(MINIMUM_CHARGE_HOURS)
            self.update_preview()
        except ImportError:
            pass  # Use default values

    def save_settings(self):
        """Save settings to config module"""
        # Check permission
        if self.rbac_controller and not self.rbac_controller.can_modify_settings():
            QMessageBox.warning(
                self,
                "Permission Denied",
                f"You don't have permission to modify settings.\n\n"
                f"Your role: {self.rbac_controller.get_role_display_name()}\n"
                f"Required: Admin or higher"
            )
            return
        
        try:
            self.save_parking_settings()
            self.save_format_settings()
            self.save_video_settings()
            QMessageBox.information(self, "Settings Saved", 
                                  "Settings have been saved successfully!\nRestart the application for all changes to take effect.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings:\n{str(e)}")
    
    def save_parking_settings(self):
        """Save parking settings to config file"""
        import os
        
        # Read current config file
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'settings.py')
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Update parking fee settings
        new_rate = self.hourly_rate_spin.value()
        new_min_hours = self.min_hours_spin.value()
        
        # Replace the values in the config file
        import re
        content = re.sub(r'PARKING_HOURLY_RATE = [\d.]+', 
                        f'PARKING_HOURLY_RATE = {new_rate}', content)
        content = re.sub(r'MINIMUM_CHARGE_HOURS = [\d.]+', 
                        f'MINIMUM_CHARGE_HOURS = {new_min_hours}', content)
        
        # Write back to file
        with open(config_path, 'w') as f:
            f.write(content)
        
        # Update runtime values if possible
        try:
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            import config.settings as settings
            settings.PARKING_HOURLY_RATE = new_rate
            settings.MINIMUM_CHARGE_HOURS = new_min_hours
        except:
            pass

    def save_format_settings(self):
        """Save license format settings to config file"""
        import os
        
        # Read current config file
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'settings.py')
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Map combo box selection to format key
        format_mapping = {
            "Automatic: Try all formats": "auto",
            "Format 1: AA00AAA (7 characters)": "format1",
            "Format 2: AA 1111 (6 characters)": "format2",
            "Format 3: A AA 1111 (7 characters)": "format3"
        }
        
        selected_format = format_mapping.get(self.format_combo.currentText(), "auto")
        
        # Update format setting in config file
        import re
        content = re.sub(r'DEFAULT_LICENSE_FORMAT = "[^"]*"', 
                        f'DEFAULT_LICENSE_FORMAT = "{selected_format}"', content)
        
        # Write back to file
        with open(config_path, 'w') as f:
            f.write(content)
        
        # Update runtime values if possible
        try:
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            import config.settings as settings
            settings.DEFAULT_LICENSE_FORMAT = selected_format
        except:
            pass
    
    def load_format_settings(self):
        """Load current format settings from config"""
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from config.settings import DEFAULT_LICENSE_FORMAT
            
            # Map format key to combo box text
            format_mapping = {
                "auto": "Automatic: Try all formats",
                "format1": "Format 1: AA00AAA (7 characters)",
                "format2": "Format 2: AA 1111 (6 characters)",
                "format3": "Format 3: A AA 1111 (7 characters)"
            }
            
            display_text = format_mapping.get(DEFAULT_LICENSE_FORMAT, "Automatic: Try all formats")
            index = self.format_combo.findText(display_text)
            if index >= 0:
                self.format_combo.setCurrentIndex(index)
        except ImportError:
            pass  # Use default selection

    def save_video_settings(self):
        """Save video processing settings to config file"""
        import os
        
        # Read current config file
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'settings.py')
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Get frame skip value from combo box
        frame_skip_text = self.frame_skip_combo.currentText()
        frame_skip_value = int(frame_skip_text.split(' ')[0])
        
        # Get detection interval value
        detection_interval_value = self.detection_interval_spin.value()
        
        # Update settings in config file
        import re
        content = re.sub(r'DEFAULT_FRAME_SKIP = \d+', 
                        f'DEFAULT_FRAME_SKIP = {frame_skip_value}', content)
        content = re.sub(r'DEFAULT_DETECTION_INTERVAL = \d+', 
                        f'DEFAULT_DETECTION_INTERVAL = {detection_interval_value}', content)
        
        # Write back to file
        with open(config_path, 'w') as f:
            f.write(content)
        
        # Update runtime values if possible
        try:
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            import config.settings as settings
            settings.DEFAULT_FRAME_SKIP = frame_skip_value
            settings.DEFAULT_DETECTION_INTERVAL = detection_interval_value
        except:
            pass
    
    def load_video_settings(self):
        """Load current video settings from config"""
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
            from config.settings import DEFAULT_FRAME_SKIP, DEFAULT_DETECTION_INTERVAL
            
            # Set frame skip combo box
            frame_skip_mapping = {
                1: "1 (Process every frame)",
                2: "2 (Skip 1 frame)",
                3: "3 (Skip 2 frames)",
                4: "4 (Skip 3 frames)",
                5: "5 (Skip 4 frames)",
                10: "10 (Skip 9 frames)"
            }
            
            display_text = frame_skip_mapping.get(DEFAULT_FRAME_SKIP, "2 (Skip 1 frame)")
            index = self.frame_skip_combo.findText(display_text)
            if index >= 0:
                self.frame_skip_combo.setCurrentIndex(index)
            
            # Set detection interval
            self.detection_interval_spin.setValue(DEFAULT_DETECTION_INTERVAL)
        except ImportError:
            pass  # Use default values

    def apply_runtime_settings(self):
        """Apply settings to the running application"""
        # This method will be implemented in the main window
        pass
    
    def apply_permissions(self):
        """Apply RBAC permissions to settings page"""
        if not self.rbac_controller:
            return
        
        # Check if user can modify settings
        can_modify = self.rbac_controller.can_modify_settings()
        
        if not can_modify:
            # Disable save and apply buttons
            if hasattr(self, 'save_btn'):
                self.save_btn.setEnabled(False)
                self.save_btn.setToolTip("Modify settings permission required (Admin role or higher)")
                self.save_btn.setStyleSheet("padding: 10px; background-color: #6c757d; color: #adb5bd; border-radius: 5px;")
            
            if hasattr(self, 'apply_btn'):
                self.apply_btn.setEnabled(False)
                self.apply_btn.setToolTip("Modify settings permission required (Admin role or higher)")
                self.apply_btn.setStyleSheet("padding: 10px; background-color: #6c757d; color: #adb5bd; border-radius: 5px;")
            
            # Disable all input widgets
            self.set_widgets_readonly(self, True)
    
    def set_widgets_readonly(self, parent_widget, readonly=True):
        """Recursively set all input widgets to readonly/disabled"""
        for child in parent_widget.findChildren(QWidget):
            if isinstance(child, (QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton)):
                child.setEnabled(not readonly)
            elif isinstance(child, QLineEdit):
                child.setReadOnly(readonly)
