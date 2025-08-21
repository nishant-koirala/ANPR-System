import os
import cv2
import numpy as np
from datetime import datetime
from collections import defaultdict

from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QTableWidget,
    QTableWidgetItem, QScrollArea, QSlider, QComboBox, QCheckBox, QApplication
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QTimer

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.build_ui()

    def build_ui(self):
        """Build dashboard page"""
        content_layout = QVBoxLayout(self)

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

    def toggle_video(self):
        """Toggle video playback"""
        # Implemented in main_window.py
        pass

    def stop_video(self):
        """Stop video playback"""
        # Implemented in main_window.py
        pass

    def step_frame(self, step):
        """Step one frame forward or backward"""
        # Implemented in main_window.py
        pass

    def on_speed_changed(self, text):
        """Change playback speed"""
        # Implemented in main_window.py
        pass

    def on_slider_pressed(self):
        """Slider pressed event"""
        # Implemented in main_window.py
        pass

    def on_slider_released(self):
        """Slider released event"""
        # Implemented in main_window.py
        pass

    def on_slider_moved(self, position):
        """Slider moved event"""
        # Implemented in main_window.py
        pass

    def load_image(self):
        """Load an image file"""
        # Implemented in main_window.py
        pass

    def load_video(self):
        """Load a video file"""
        # Implemented in main_window.py
        pass
