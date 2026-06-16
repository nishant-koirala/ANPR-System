"""
Registration completion dialog for email-based user invitations
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame,
                             QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import re


class RegistrationDialog(QDialog):
    """Dialog for completing user registration with OTP"""
    
    registration_completed = pyqtSignal(str, str, str)  # username, password, role
    
    def __init__(self, invitation_db, auth_manager, parent=None):
        super().__init__(parent)
        self.invitation_db = invitation_db
        self.auth_manager = auth_manager
        self.verified_invitation = None
        self.verified_otp = None  # Store OTP temporarily after verification
        
        self.setWindowTitle("Complete Registration - NEPALI ANPR")
        self.setModal(True)
        self.setFixedWidth(500)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_label = QLabel("🎉 Complete Your Registration")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Subtitle
        subtitle = QLabel("Enter the OTP sent to your email to create your account")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        layout.addWidget(subtitle)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Step 1: Email & OTP Verification
        step1_label = QLabel("📧 Step 1: Verify Your Email")
        step1_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #667eea;")
        layout.addWidget(step1_label)
        
        # Email input
        email_label = QLabel("Email Address:")
        layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email address")
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        layout.addWidget(self.email_input)
        
        # OTP input
        otp_label = QLabel("One-Time Password (OTP):")
        layout.addWidget(otp_label)
        
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter 6-digit OTP from email")
        self.otp_input.setMaxLength(6)
        self.otp_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 3px;
                font-family: 'Courier New';
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        layout.addWidget(self.otp_input)
        
        # Verify button
        self.verify_btn = QPushButton("🔍 Verify OTP")
        self.verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5568d3;
            }
            QPushButton:pressed {
                background-color: #4451b8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.verify_btn.clicked.connect(self.verify_otp)
        layout.addWidget(self.verify_btn)
        
        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)
        
        # Step 2: Create Account (initially disabled)
        step2_label = QLabel("👤 Step 2: Create Your Account")
        step2_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #667eea;")
        layout.addWidget(step2_label)
        
        self.account_frame = QFrame()
        account_layout = QVBoxLayout(self.account_frame)
        account_layout.setContentsMargins(0, 0, 0, 0)
        
        # Full Name input
        fullname_label = QLabel("Full Name:")
        account_layout.addWidget(fullname_label)
        
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Enter your full name")
        self.fullname_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        account_layout.addWidget(self.fullname_input)
        
        # Username input
        username_label = QLabel("Username:")
        account_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username (3-50 characters)")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        account_layout.addWidget(self.username_input)
        
        # Password input
        password_label = QLabel("Password:")
        account_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Create a strong password (min 8 characters)")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        account_layout.addWidget(self.password_input)
        
        # Confirm password input
        confirm_label = QLabel("Confirm Password:")
        account_layout.addWidget(confirm_label)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Re-enter your password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        account_layout.addWidget(self.confirm_input)
        
        # Role display
        self.role_label = QLabel("")
        self.role_label.setStyleSheet("""
            background-color: #e8f5e9;
            color: #2e7d32;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
            margin-top: 10px;
        """)
        self.role_label.setAlignment(Qt.AlignCenter)
        self.role_label.hide()
        account_layout.addWidget(self.role_label)
        
        layout.addWidget(self.account_frame)
        self.account_frame.setEnabled(False)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
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
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.register_btn = QPushButton("✅ Complete Registration")
        self.register_btn.setStyleSheet("""
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
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.register_btn.clicked.connect(self.complete_registration)
        self.register_btn.setEnabled(False)
        button_layout.addWidget(self.register_btn)
        
        layout.addLayout(button_layout)
        
        # Info text
        info_label = QLabel("💡 Tip: Check your email spam folder if you haven't received the OTP")
        info_label.setStyleSheet("color: #6c757d; font-size: 11px; margin-top: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
    
    def verify_otp(self):
        """Verify OTP and email"""
        email = self.email_input.text().strip()
        otp = self.otp_input.text().strip()
        
        # Validation
        if not email:
            QMessageBox.warning(self, "Validation Error", "Please enter your email address")
            self.email_input.setFocus()
            return
        
        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address")
            self.email_input.setFocus()
            return
        
        if not otp:
            QMessageBox.warning(self, "Validation Error", "Please enter the OTP")
            self.otp_input.setFocus()
            return
        
        if len(otp) != 6 or not otp.isdigit():
            QMessageBox.warning(self, "Validation Error", "OTP must be 6 digits")
            self.otp_input.setFocus()
            return
        
        # Verify with database
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Verify OTP
            invitation = self.invitation_db.verify_otp(email, otp)
            
            if invitation:
                self.verified_invitation = invitation
                self.verified_otp = otp  # Store plain OTP for later use
                
                # Enable account creation
                self.account_frame.setEnabled(True)
                self.register_btn.setEnabled(True)
                self.verify_btn.setEnabled(False)
                self.email_input.setEnabled(False)
                self.otp_input.setEnabled(False)
                
                # Show role
                role_display = invitation.role.capitalize()
                self.role_label.setText(f"✅ Verified! You will be registered as: {role_display}")
                self.role_label.show()
                
                # Focus on username
                self.username_input.setFocus()
                
                QMessageBox.information(
                    self,
                    "✅ Verification Successful",
                    f"Your email has been verified!\n\n"
                    f"Role: {role_display}\n\n"
                    f"Please create your username and password to complete registration."
                )
            else:
                QMessageBox.critical(
                    self,
                    "❌ Verification Failed",
                    "Invalid OTP or email address.\n\n"
                    "Please check:\n"
                    "• Email address is correct\n"
                    "• OTP is correct (6 digits)\n"
                    "• OTP hasn't expired (valid for 48 hours)\n\n"
                    "If you need a new invitation, please contact your administrator."
                )
                self.otp_input.clear()
                self.otp_input.setFocus()
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred during verification:\n{str(e)}"
            )
            print(f"OTP verification error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            QApplication.restoreOverrideCursor()
    
    def complete_registration(self):
        """Complete user registration"""
        if not self.verified_invitation:
            QMessageBox.warning(self, "Error", "Please verify your OTP first")
            return
        
        # Get input values
        full_name = self.fullname_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        # Validation
        if not full_name:
            QMessageBox.warning(self, "Validation Error", "Please enter your full name")
            self.fullname_input.setFocus()
            return
        
        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Please fill in all fields")
            self.username_input.setFocus()
            return
        
        if len(username) < 3 or len(username) > 50:
            QMessageBox.warning(self, "Validation Error", "Username must be 3-50 characters")
            self.username_input.setFocus()
            return
        
        if not username.replace('_', '').replace('-', '').isalnum():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
            self.username_input.setFocus()
            return
        
        if not password:
            QMessageBox.warning(self, "Validation Error", "Please enter a password")
            self.password_input.setFocus()
            return
        
        if len(password) < 8:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 8 characters")
            self.password_input.setFocus()
            return
        
        if password != confirm:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match")
            self.confirm_input.clear()
            self.confirm_input.setFocus()
            return
        
        # Check if username already exists
        if self.auth_manager.get_user_by_username(username):
            QMessageBox.warning(
                self,
                "Username Taken",
                f"The username '{username}' is already taken.\n\nPlease choose a different username."
            )
            self.username_input.clear()
            self.username_input.setFocus()
            return
        
        # Create user account
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Register user
            success = self.auth_manager.register_user(
                username=username,
                password=password,
                role=self.verified_invitation.role,
                email=self.verified_invitation.email,
                full_name=full_name
            )
            
            if success:
                # Mark invitation as completed using stored OTP
                completed = self.invitation_db.complete_invitation(
                    email=self.verified_invitation.email,
                    otp=self.verified_otp,  # Use stored plain OTP
                    username=username
                )
                
                if not completed:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        "Account created but invitation could not be marked as completed."
                    )
                
                QMessageBox.information(
                    self,
                    "✅ Registration Complete!",
                    f"Your account has been created successfully!\n\n"
                    f"Username: {username}\n"
                    f"Role: {self.verified_invitation.role.capitalize()}\n\n"
                    f"You can now log in with your credentials."
                )
                
                # Emit signal
                self.registration_completed.emit(
                    username,
                    password,
                    self.verified_invitation.role
                )
                
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Registration Failed",
                    "Failed to create user account.\n\nPlease try again or contact your administrator."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred during registration:\n{str(e)}"
            )
            print(f"Registration error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            QApplication.restoreOverrideCursor()
    
    def is_valid_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
