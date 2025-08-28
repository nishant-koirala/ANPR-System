#!/usr/bin/env python3
"""
Plate Edit Dialog for ANPR System
Allows operators to correct OCR mistakes with visual verification
"""

import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
                           QGroupBox, QMessageBox, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QFont, QPalette
from datetime import datetime

from ..db.models import VehicleLog, PlateEditHistory, User
from ..auth.auth_manager import AuthManager


class PlateEditThread(QThread):
    """Background thread for saving plate edits"""
    edit_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, session_factory, edit_data):
        super().__init__()
        self.session_factory = session_factory
        self.edit_data = edit_data
    
    def run(self):
        try:
            with self.session_factory() as session:
                # Get the vehicle log record
                vehicle_log = session.query(VehicleLog).filter_by(
                    log_id=self.edit_data['log_id']
                ).first()
                
                if not vehicle_log:
                    self.edit_completed.emit(False, "Vehicle log not found")
                    return
                
                # Store original value if not already stored
                if not vehicle_log.original_plate_number:
                    vehicle_log.original_plate_number = vehicle_log.plate_number
                
                # Create audit trail entry
                edit_history = PlateEditHistory(
                    log_id=vehicle_log.log_id,
                    old_plate_number=vehicle_log.plate_number,
                    new_plate_number=self.edit_data['new_plate_number'],
                    edited_by=self.edit_data['edited_by'],
                    edit_reason=self.edit_data['edit_reason'],
                    ip_address=self.edit_data.get('ip_address'),
                    user_agent=self.edit_data.get('user_agent')
                )
                session.add(edit_history)
                
                # Update vehicle log
                vehicle_log.plate_number = self.edit_data['new_plate_number']
                vehicle_log.is_edited = True
                vehicle_log.edited_by = self.edit_data['edited_by']
                vehicle_log.edited_at = datetime.now()
                vehicle_log.edit_reason = self.edit_data['edit_reason']
                
                session.commit()
                self.edit_completed.emit(True, "Plate number updated successfully")
                
        except Exception as e:
            self.edit_completed.emit(False, f"Error saving edit: {str(e)}")


class PlateEditDialog(QDialog):
    """Dialog for editing plate numbers with image verification"""
    
    plate_updated = pyqtSignal(dict)  # Emitted when plate is successfully updated
    
    def __init__(self, session_factory, auth_manager, vehicle_log_data, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.auth_manager = auth_manager
        self.vehicle_log_data = vehicle_log_data
        self.edit_thread = None
        
        self.setWindowTitle("Edit Plate Number")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Edit Plate Number")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - Image display
        image_group = self.create_image_section()
        content_layout.addWidget(image_group, 1)
        
        # Right side - Edit form
        edit_group = self.create_edit_section()
        content_layout.addWidget(edit_group, 1)
        
        layout.addLayout(content_layout)
        
        # Buttons
        button_layout = self.create_button_section()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Apply styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f8f9fa;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ced4da;
                border-radius: 4px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            QTextEdit {
                padding: 8px;
                border: 2px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#save_button {
                background-color: #28a745;
                color: white;
            }
            QPushButton#save_button:hover {
                background-color: #218838;
            }
            QPushButton#cancel_button {
                background-color: #6c757d;
                color: white;
            }
            QPushButton#cancel_button:hover {
                background-color: #545b62;
            }
        """)
    
    def create_image_section(self):
        """Create the image display section"""
        group_box = QGroupBox("Plate Image")
        layout = QVBoxLayout()
        
        # Image display area
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setMinimumHeight(300)
        self.image_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
        """)
        
        self.image_label = QLabel("Loading image...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 20px;
                color: #6c757d;
            }
        """)
        
        self.image_scroll.setWidget(self.image_label)
        layout.addWidget(self.image_scroll)
        
        # Image info
        self.image_info_label = QLabel("")
        self.image_info_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        layout.addWidget(self.image_info_label)
        
        group_box.setLayout(layout)
        return group_box
    
    def create_edit_section(self):
        """Create the edit form section"""
        group_box = QGroupBox("Edit Information")
        layout = QVBoxLayout()
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Current plate number (read-only)
        self.current_plate_label = QLabel("")
        self.current_plate_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #e9ecef;
                border: 2px solid #ced4da;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        form_layout.addRow("Current Plate:", self.current_plate_label)
        
        # New plate number input
        self.new_plate_edit = QLineEdit()
        self.new_plate_edit.setPlaceholderText("Enter corrected plate number")
        self.new_plate_edit.textChanged.connect(self.validate_input)
        form_layout.addRow("New Plate:", self.new_plate_edit)
        
        # Confidence display
        self.confidence_label = QLabel("")
        self.confidence_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        form_layout.addRow("OCR Confidence:", self.confidence_label)
        
        # Edit reason
        self.reason_combo = QComboBox()
        self.reason_combo.addItems([
            "OCR Error - Wrong Characters",
            "OCR Error - Missing Characters", 
            "OCR Error - Extra Characters",
            "Poor Image Quality",
            "Partial Plate Visible",
            "Manual Verification",
            "Other"
        ])
        self.reason_combo.currentTextChanged.connect(self.on_reason_changed)
        form_layout.addRow("Reason:", self.reason_combo)
        
        # Custom reason text
        self.custom_reason_edit = QTextEdit()
        self.custom_reason_edit.setMaximumHeight(80)
        self.custom_reason_edit.setPlaceholderText("Enter custom reason (optional)")
        self.custom_reason_edit.hide()
        form_layout.addRow("Details:", self.custom_reason_edit)
        
        layout.addLayout(form_layout)
        
        # Record info
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        self.record_info_label = QLabel("")
        self.record_info_label.setStyleSheet("color: #1976d2; font-size: 12px;")
        info_layout.addWidget(self.record_info_label)
        
        layout.addWidget(info_frame)
        
        group_box.setLayout(layout)
        return group_box
    
    def create_button_section(self):
        """Create the button section"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        # Save button
        self.save_button = QPushButton("Save Changes")
        self.save_button.setObjectName("save_button")
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)
        
        return layout
    
    def load_data(self):
        """Load data into the dialog"""
        # Set current plate number
        current_plate = self.vehicle_log_data.get('plate_number', '')
        self.current_plate_label.setText(current_plate)
        self.new_plate_edit.setText(current_plate)
        
        # Set confidence
        confidence = self.vehicle_log_data.get('confidence')
        if confidence is not None:
            self.confidence_label.setText(f"{confidence:.1%}")
        else:
            self.confidence_label.setText("N/A")
        
        # Set record info
        captured_at = self.vehicle_log_data.get('captured_at', '')
        camera_name = self.vehicle_log_data.get('camera_name', 'Unknown')
        toggle_mode = self.vehicle_log_data.get('toggle_mode', '')
        
        info_text = f"Captured: {captured_at}\nCamera: {camera_name}\nType: {toggle_mode}"
        self.record_info_label.setText(info_text)
        
        # Load plate image
        self.load_plate_image()
    
    def load_plate_image(self):
        """Load and display the plate image"""
        try:
            # Try to get image path from raw_log data
            image_path = None
            
            # First try plate_image_path (cropped plate)
            if 'plate_image_path' in self.vehicle_log_data:
                image_path = self.vehicle_log_data['plate_image_path']
            
            # Fallback to thumbnail_path
            elif 'thumbnail_path' in self.vehicle_log_data:
                image_path = self.vehicle_log_data['thumbnail_path']
            
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Scale image to fit while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(400, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.image_label.setPixmap(scaled_pixmap)
                    
                    # Update image info
                    file_size = os.path.getsize(image_path) / 1024  # KB
                    self.image_info_label.setText(f"Size: {pixmap.width()}x{pixmap.height()}, {file_size:.1f} KB")
                    return
            
            # No image available
            self.image_label.setText("No plate image available")
            self.image_info_label.setText("Image not found")
            
        except Exception as e:
            self.image_label.setText(f"Error loading image: {str(e)}")
            self.image_info_label.setText("Image load error")
    
    def on_reason_changed(self, reason):
        """Handle reason selection change"""
        if reason == "Other":
            self.custom_reason_edit.show()
        else:
            self.custom_reason_edit.hide()
    
    def validate_input(self):
        """Validate the input and enable/disable save button"""
        new_plate = self.new_plate_edit.text().strip().upper()
        current_plate = self.current_plate_label.text().strip().upper()
        
        # Enable save button only if plate number changed and is not empty
        is_valid = len(new_plate) > 0 and new_plate != current_plate
        self.save_button.setEnabled(is_valid)
        
        # Update the text to uppercase
        if self.new_plate_edit.text() != new_plate:
            cursor_pos = self.new_plate_edit.cursorPosition()
            self.new_plate_edit.setText(new_plate)
            self.new_plate_edit.setCursorPosition(cursor_pos)
    
    def save_changes(self):
        """Save the plate number changes"""
        # Check permissions
        try:
            self.auth_manager.require_permission("EDIT_PLATES")
        except Exception as e:
            QMessageBox.warning(self, "Permission Denied", str(e))
            return
        
        # Get form data
        new_plate = self.new_plate_edit.text().strip().upper()
        reason = self.reason_combo.currentText()
        
        if reason == "Other":
            custom_reason = self.custom_reason_edit.toPlainText().strip()
            if custom_reason:
                reason = f"Other: {custom_reason}"
        
        # Confirm the change
        current_plate = self.current_plate_label.text()
        reply = QMessageBox.question(
            self, 
            "Confirm Edit",
            f"Change plate number from '{current_plate}' to '{new_plate}'?\n\nReason: {reason}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Prepare edit data
        edit_data = {
            'log_id': self.vehicle_log_data['log_id'],
            'new_plate_number': new_plate,
            'edit_reason': reason,
            'edited_by': self.auth_manager.current_user.user_id if self.auth_manager.current_user else 1,
            'ip_address': '127.0.0.1',  # Could be enhanced to get real IP
            'user_agent': 'ANPR Desktop Application'
        }
        
        # Disable UI during save
        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        
        # Start save thread
        self.edit_thread = PlateEditThread(self.session_factory, edit_data)
        self.edit_thread.edit_completed.connect(self.on_edit_completed)
        self.edit_thread.start()
    
    def on_edit_completed(self, success, message):
        """Handle edit completion"""
        # Re-enable UI
        self.save_button.setText("Save Changes")
        
        if success:
            QMessageBox.information(self, "Success", message)
            
            # Emit signal with updated data
            updated_data = self.vehicle_log_data.copy()
            updated_data['plate_number'] = self.new_plate_edit.text().strip().upper()
            updated_data['is_edited'] = True
            updated_data['edited_at'] = datetime.now()
            
            self.plate_updated.emit(updated_data)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", message)
            self.save_button.setEnabled(True)
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if self.edit_thread and self.edit_thread.isRunning():
            self.edit_thread.quit()
            self.edit_thread.wait()
        event.accept()
