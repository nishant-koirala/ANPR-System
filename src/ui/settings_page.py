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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.build_ui()

    def build_ui(self):
        """Build settings page"""
        content_layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        # Tabs
        tabs = QTabWidget()
        
        # Model Settings
        model_tab = QWidget()
        model_tab_layout = QVBoxLayout(model_tab)
        model_tab_layout.addWidget(self.create_model_settings())
        tabs.addTab(model_tab, "Model")
        
        # Detection Settings
        detection_tab = QWidget()
        detection_tab_layout = QVBoxLayout(detection_tab)
        detection_tab_layout.addWidget(self.create_detection_settings())
        tabs.addTab(detection_tab, "Detection")
        
        # OCR Settings
        ocr_tab = QWidget()
        ocr_tab_layout = QVBoxLayout(ocr_tab)
        ocr_tab_layout.addWidget(self.create_ocr_settings())
        tabs.addTab(ocr_tab, "OCR")
        
        # Performance Settings
        perf_tab = QWidget()
        perf_tab_layout = QVBoxLayout(perf_tab)
        perf_tab_layout.addWidget(self.create_performance_settings())
        tabs.addTab(perf_tab, "Performance")
        
        content_layout.addWidget(tabs)

        # Save and Apply buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("padding: 10px; background-color: #27ae60; color: white; border-radius: 5px;")
        apply_btn = QPushButton("Apply Settings")
        apply_btn.clicked.connect(self.apply_runtime_settings)
        apply_btn.setStyleSheet("padding: 10px; background-color: #2980b9; color: white; border-radius: 5px;")
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(apply_btn)
        content_layout.addLayout(btn_layout)

    def create_model_settings(self):
        """Create model settings group"""
        group = QGroupBox("Model Settings")
        layout = QVBoxLayout(group)
        
        # Vehicle model selector
        vehicle_layout = QHBoxLayout()
        vehicle_layout.addWidget(QLabel("Vehicle Detection Model:"))
        self.vehicle_model_combo = QComboBox()
        self.vehicle_model_combo.addItems(["YOLOv8n", "YOLOv8m", "YOLOv8l"])
        vehicle_layout.addWidget(self.vehicle_model_combo)
        layout.addLayout(vehicle_layout)
        
        # Plate model selector
        plate_layout = QHBoxLayout()
        plate_layout.addWidget(QLabel("Plate Detection Model:"))
        self.plate_model_combo = QComboBox()
        self.plate_model_combo.addItems(["YOLOv8n", "YOLOv8m", "YOLOv8l"])
        plate_layout.addWidget(self.plate_model_combo)
        layout.addLayout(plate_layout)
        
        # OCR model selector
        ocr_layout = QHBoxLayout()
        ocr_layout.addWidget(QLabel("OCR Model:"))
        self.ocr_model_combo = QComboBox()
        self.ocr_model_combo.addItems(["EasyOCR", "Tesseract", "Custom CRNN"])
        ocr_layout.addWidget(self.ocr_model_combo)
        layout.addLayout(ocr_layout)
        
        return group

    def create_detection_settings(self):
        """Create detection settings group"""
        group = QGroupBox("Detection Settings")
        layout = QVBoxLayout(group)
        
        # Confidence threshold
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Confidence Threshold:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.1, 0.99)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.5)
        conf_layout.addWidget(self.conf_spin)
        layout.addLayout(conf_layout)
        
        # IOU threshold
        iou_layout = QHBoxLayout()
        iou_layout.addWidget(QLabel("IOU Threshold:"))
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.1, 0.99)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(0.7)
        iou_layout.addWidget(self.iou_spin)
        layout.addLayout(iou_layout)
        
        # Tracking method
        track_layout = QHBoxLayout()
        track_layout.addWidget(QLabel("Tracking Method:"))
        self.track_combo = QComboBox()
        self.track_combo.addItems(["ByteTrack", "SORT", "DeepSORT", "Custom"])
        track_layout.addWidget(self.track_combo)
        layout.addLayout(track_layout)
        
        return group

    def create_ocr_settings(self):
        """Create OCR settings group"""
        group = QGroupBox("OCR Settings")
        layout = QVBoxLayout(group)
        
        # OCR language
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["en", "ne", "hi", "custom"])
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
        
        # Character whitelist
        whitelist_layout = QHBoxLayout()
        whitelist_layout.addWidget(QLabel("Character Whitelist:"))
        self.whitelist_edit = QLineEdit("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        whitelist_layout.addWidget(self.whitelist_edit)
        layout.addLayout(whitelist_layout)
        
        # Post-processing
        post_layout = QHBoxLayout()
        self.post_check = QCheckBox("Enable Post-processing")
        self.post_check.setChecked(True)
        post_layout.addWidget(self.post_check)
        layout.addLayout(post_layout)
        
        return group

    def create_performance_settings(self):
        """Create performance settings group"""
        group = QGroupBox("Performance Settings")
        layout = QVBoxLayout(group)
        
        # Thread count
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("Thread Count:"))
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 8)
        self.thread_spin.setValue(4)
        thread_layout.addWidget(self.thread_spin)
        layout.addLayout(thread_layout)
        
        # GPU acceleration
        gpu_layout = QHBoxLayout()
        self.gpu_check = QCheckBox("Enable GPU Acceleration")
        self.gpu_check.setChecked(True)
        gpu_layout.addWidget(self.gpu_check)
        layout.addLayout(gpu_layout)
        
        # Batch size
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch Size:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 16)
        self.batch_spin.setValue(1)
        batch_layout.addWidget(self.batch_spin)
        layout.addLayout(batch_layout)
        
        return group

    def save_settings(self):
        """Save settings to config module"""
        # This method will be implemented in the main window
        pass

    def apply_runtime_settings(self):
        """Apply settings to the running application"""
        # This method will be implemented in the main window
        pass
