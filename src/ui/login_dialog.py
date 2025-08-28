"""
Login Dialog for RBAC Authentication
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLineEdit, QPushButton, QLabel, QFrame, QCheckBox,
                           QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon
import sys
import os

class LoginThread(QThread):
    """Background thread for login authentication"""
    login_success = pyqtSignal(dict)
    login_failed = pyqtSignal(str)
    
    def __init__(self, auth_manager, username, password, ip_address=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.username = username
        self.password = password
        self.ip_address = ip_address
    
    def run(self):
        try:
            user_info = self.auth_manager.login(self.username, self.password, self.ip_address)
            self.login_success.emit(user_info)
        except Exception as e:
            self.login_failed.emit(str(e))

class LoginDialog(QDialog):
    """Professional login dialog with RBAC authentication"""
    
    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.user_info = None
        self.login_thread = None
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ANPR System - Login")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)
        
        # Header section
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        
        # Logo/Title
        title_label = QLabel("🚗 NEPALI ANPR")
        title_font = QFont("Arial", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        
        subtitle_label = QLabel("Automatic Number Plate Recognition System")
        subtitle_font = QFont("Arial", 10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #7f8c8d; margin-bottom: 20px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        
        # Login form section
        form_frame = QFrame()
        form_frame.setFrameStyle(QFrame.Box)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Username field
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter username")
        self.username_edit.setStyleSheet(self.get_input_style())
        self.username_edit.setMinimumHeight(35)
        
        # Password field
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet(self.get_input_style())
        self.password_edit.setMinimumHeight(35)
        
        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setStyleSheet("color: #495057;")
        
        form_layout.addRow("Username:", self.username_edit)
        form_layout.addRow("Password:", self.password_edit)
        form_layout.addRow("", self.remember_checkbox)
        
        form_frame.setLayout(form_layout)
        
        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.hide()
        
        # Buttons section
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.login_button = QPushButton("Login")
        self.login_button.setMinimumHeight(40)
        self.login_button.setStyleSheet(self.get_button_style("primary"))
        self.login_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setStyleSheet(self.get_button_style("secondary"))
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.login_button)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        self.status_label.hide()
        
        # Footer
        footer_label = QLabel("Enter your credentials to access the system")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #6c757d; font-size: 10px; margin-top: 10px;")
        
        # Add all sections to main layout
        main_layout.addLayout(header_layout)
        main_layout.addWidget(form_frame)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(footer_label)
        
        self.setLayout(main_layout)
        
        # Set focus to username field
        self.username_edit.setFocus()
        
    def get_input_style(self):
        """Get stylesheet for input fields"""
        return """
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: white;
                color: #212529;
            }
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """
    
    def get_button_style(self, button_type):
        """Get stylesheet for buttons"""
        if button_type == "primary":
            return """
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """
        else:  # secondary
            return """
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background-color: #545b62;
                }
                QPushButton:pressed {
                    background-color: #3d4142;
                }
            """
    
    def setup_connections(self):
        """Setup signal connections"""
        self.login_button.clicked.connect(self.handle_login)
        self.cancel_button.clicked.connect(self.reject)
        self.password_edit.returnPressed.connect(self.handle_login)
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)
        
    def handle_login(self):
        """Handle login button click"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not username or not password:
            self.show_error("Please enter both username and password")
            return
        
        # Disable UI during login
        self.set_login_state(True)
        
        # Start login in background thread
        self.login_thread = LoginThread(self.auth_manager, username, password, "127.0.0.1")
        self.login_thread.login_success.connect(self.on_login_success)
        self.login_thread.login_failed.connect(self.on_login_failed)
        self.login_thread.start()
        
    def set_login_state(self, logging_in):
        """Set UI state during login process"""
        self.login_button.setEnabled(not logging_in)
        self.cancel_button.setEnabled(not logging_in)
        self.username_edit.setEnabled(not logging_in)
        self.password_edit.setEnabled(not logging_in)
        
        if logging_in:
            self.login_button.setText("Logging in...")
            self.progress_bar.show()
            self.status_label.hide()
        else:
            self.login_button.setText("Login")
            self.progress_bar.hide()
    
    def on_login_success(self, user_info):
        """Handle successful login"""
        self.user_info = user_info
        self.set_login_state(False)
        
        # Show success message briefly
        self.status_label.setText(f"Welcome, {user_info['full_name'] or user_info['username']}!")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        self.status_label.show()
        
        # Close dialog after brief delay
        QTimer.singleShot(1000, self.accept)
    
    def on_login_failed(self, error_message):
        """Handle failed login"""
        self.set_login_state(False)
        self.show_error(error_message)
        
        # Clear password field
        self.password_edit.clear()
        self.password_edit.setFocus()
    
    def show_error(self, message):
        """Show error message"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        self.status_label.show()
        
        # Hide error after 5 seconds
        QTimer.singleShot(5000, self.status_label.hide)
    
    def get_user_info(self):
        """Get authenticated user information"""
        return self.user_info
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        if self.login_thread and self.login_thread.isRunning():
            self.login_thread.terminate()
            self.login_thread.wait()
        event.accept()
