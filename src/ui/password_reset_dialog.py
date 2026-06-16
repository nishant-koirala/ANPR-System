"""
Password reset dialogs for email-based password recovery
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame,
                             QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import re


class PasswordResetRequestDialog(QDialog):
    """Dialog for requesting password reset"""
    
    def __init__(self, invitation_db, auth_manager, email_sender, parent=None):
        super().__init__(parent)
        self.invitation_db = invitation_db
        self.auth_manager = auth_manager
        self.email_sender = email_sender
        
        self.setWindowTitle("Reset Password - NEPALI ANPR")
        self.setModal(True)
        self.setFixedWidth(450)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_label = QLabel("🔐 Reset Your Password")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Subtitle
        subtitle = QLabel("Enter your username or email to receive a password reset link")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Username/Email input
        input_label = QLabel("Username or Email:")
        layout.addWidget(input_label)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter your username or email address")
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #f5576c;
            }
        """)
        layout.addWidget(self.input_field)
        
        # Info box
        info_box = QLabel(
            "📧 A password reset token will be sent to your registered email address.\n\n"
            "The token will be valid for 24 hours."
        )
        info_box.setStyleSheet("""
            background-color: #e3f2fd;
            color: #1976d2;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #1976d2;
        """)
        info_box.setWordWrap(True)
        layout.addWidget(info_box)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        self.send_btn = QPushButton("📧 Send Reset Link")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5576c;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e04555;
            }
            QPushButton:pressed {
                background-color: #c93d4d;
            }
        """)
        self.send_btn.clicked.connect(self.send_reset_link)
        button_layout.addWidget(self.send_btn)
        
        layout.addLayout(button_layout)
    
    def send_reset_link(self):
        """Send password reset link"""
        identifier = self.input_field.text().strip()
        
        if not identifier:
            QMessageBox.warning(self, "Validation Error", "Please enter your username or email")
            self.input_field.setFocus()
            return
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Find user by username or email
            user = None
            if '@' in identifier:
                # Email provided
                user = self.auth_manager.get_user_by_email(identifier)
            else:
                # Username provided
                user = self.auth_manager.get_user_by_username(identifier)
            
            if not user:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(
                    self,
                    "User Not Found",
                    "No account found with that username or email.\n\n"
                    "Please check your input and try again."
                )
                return
            
            # Check if user has email
            if not hasattr(user, 'email') or not user.email:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(
                    self,
                    "No Email Registered",
                    f"The account '{user.username}' does not have a registered email address.\n\n"
                    "Please contact your administrator for password reset assistance."
                )
                return
            
            # Create reset token
            reset_token = self.invitation_db.create_password_reset_token(
                user_id=user.user_id,
                username=user.username,
                email=user.email
            )
            
            if not reset_token:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to create password reset token.\n\nPlease try again."
                )
                return
            
            # Send email
            success = self.email_sender.send_password_reset_email(
                recipient_email=user.email,
                username=user.username,
                reset_token=reset_token.token
            )
            
            QApplication.restoreOverrideCursor()
            
            if success:
                QMessageBox.information(
                    self,
                    "✅ Reset Link Sent",
                    f"A password reset token has been sent to:\n{user.email}\n\n"
                    f"Please check your email and follow the instructions.\n\n"
                    f"The token will expire in 24 hours."
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Email Send Failed",
                    "Failed to send password reset email.\n\n"
                    "Please check your internet connection and try again."
                )
        
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred:\n{str(e)}"
            )
            print(f"Password reset request error: {e}")
            import traceback
            traceback.print_exc()


class PasswordResetCompleteDialog(QDialog):
    """Dialog for completing password reset with token"""
    
    def __init__(self, invitation_db, auth_manager, parent=None):
        super().__init__(parent)
        self.invitation_db = invitation_db
        self.auth_manager = auth_manager
        self.verified_token = None
        
        self.setWindowTitle("Complete Password Reset - NEPALI ANPR")
        self.setModal(True)
        self.setFixedWidth(500)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_label = QLabel("🔑 Create New Password")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Subtitle
        subtitle = QLabel("Enter your reset token and create a new password")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        layout.addWidget(subtitle)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Step 1: Token Verification
        step1_label = QLabel("📧 Step 1: Verify Reset Token")
        step1_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #f5576c;")
        layout.addWidget(step1_label)
        
        # Token input
        token_label = QLabel("Reset Token (from email):")
        layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste the reset token from your email")
        self.token_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 12px;
                font-family: 'Courier New';
            }
            QLineEdit:focus {
                border-color: #f5576c;
            }
        """)
        layout.addWidget(self.token_input)
        
        # Verify button
        self.verify_btn = QPushButton("🔍 Verify Token")
        self.verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5576c;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e04555;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.verify_btn.clicked.connect(self.verify_token)
        layout.addWidget(self.verify_btn)
        
        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)
        
        # Step 2: New Password (initially disabled)
        step2_label = QLabel("🔐 Step 2: Create New Password")
        step2_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #f5576c;")
        layout.addWidget(step2_label)
        
        self.password_frame = QFrame()
        password_layout = QVBoxLayout(self.password_frame)
        password_layout.setContentsMargins(0, 0, 0, 0)
        
        # Username display
        self.username_label = QLabel("")
        self.username_label.setStyleSheet("""
            background-color: #e8f5e9;
            color: #2e7d32;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        """)
        self.username_label.setAlignment(Qt.AlignCenter)
        self.username_label.hide()
        password_layout.addWidget(self.username_label)
        
        # New password input
        new_password_label = QLabel("New Password:")
        password_layout.addWidget(new_password_label)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("Enter new password (min 8 characters)")
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #f5576c;
            }
        """)
        password_layout.addWidget(self.new_password_input)
        
        # Confirm password input
        confirm_label = QLabel("Confirm New Password:")
        password_layout.addWidget(confirm_label)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Re-enter new password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #f5576c;
            }
        """)
        password_layout.addWidget(self.confirm_input)
        
        layout.addWidget(self.password_frame)
        self.password_frame.setEnabled(False)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        
        self.reset_btn = QPushButton("✅ Reset Password")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_password)
        self.reset_btn.setEnabled(False)
        button_layout.addWidget(self.reset_btn)
        
        layout.addLayout(button_layout)
    
    def verify_token(self):
        """Verify reset token"""
        token = self.token_input.text().strip()
        
        if not token:
            QMessageBox.warning(self, "Validation Error", "Please enter the reset token")
            self.token_input.setFocus()
            return
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            reset_token = self.invitation_db.verify_reset_token(token)
            
            if reset_token:
                self.verified_token = reset_token
                
                # Enable password fields
                self.password_frame.setEnabled(True)
                self.reset_btn.setEnabled(True)
                self.verify_btn.setEnabled(False)
                self.token_input.setEnabled(False)
                
                # Show username
                self.username_label.setText(f"✅ Token verified for: {reset_token.username}")
                self.username_label.show()
                
                # Focus on new password
                self.new_password_input.setFocus()
                
                QApplication.restoreOverrideCursor()
                
                QMessageBox.information(
                    self,
                    "✅ Token Verified",
                    f"Reset token verified successfully!\n\n"
                    f"Username: {reset_token.username}\n\n"
                    f"Please enter your new password."
                )
            else:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self,
                    "❌ Invalid Token",
                    "The reset token is invalid or has expired.\n\n"
                    "Please check:\n"
                    "• Token is correct (copy from email)\n"
                    "• Token hasn't expired (valid for 24 hours)\n"
                    "• Token hasn't been used already\n\n"
                    "If needed, request a new password reset."
                )
                self.token_input.clear()
                self.token_input.setFocus()
        
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred during verification:\n{str(e)}"
            )
            print(f"Token verification error: {e}")
            import traceback
            traceback.print_exc()
    
    def reset_password(self):
        """Reset password"""
        if not self.verified_token:
            QMessageBox.warning(self, "Error", "Please verify your reset token first")
            return
        
        new_password = self.new_password_input.text()
        confirm = self.confirm_input.text()
        
        # Validation
        if not new_password:
            QMessageBox.warning(self, "Validation Error", "Please enter a new password")
            self.new_password_input.setFocus()
            return
        
        if len(new_password) < 8:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters")
            self.new_password_input.setFocus()
            return
        
        if new_password != confirm:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match")
            self.confirm_input.clear()
            self.confirm_input.setFocus()
            return
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Update password
            success = self.auth_manager.update_password(
                self.verified_token.username,
                new_password
            )
            
            if success:
                # Mark token as used
                self.invitation_db.use_reset_token(self.verified_token.token)
                
                QApplication.restoreOverrideCursor()
                
                QMessageBox.information(
                    self,
                    "✅ Password Reset Complete",
                    f"Your password has been reset successfully!\n\n"
                    f"Username: {self.verified_token.username}\n\n"
                    f"You can now log in with your new password."
                )
                
                self.accept()
            else:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self,
                    "Reset Failed",
                    "Failed to reset password.\n\nPlease try again or contact your administrator."
                )
        
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred during password reset:\n{str(e)}"
            )
            print(f"Password reset error: {e}")
            import traceback
            traceback.print_exc()
