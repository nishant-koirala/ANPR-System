"""
Invite User Dialog for email-based user invitations
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame,
                             QRadioButton, QButtonGroup, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import re


class InviteUserDialog(QDialog):
    """Dialog for inviting new users via email"""
    
    invitation_sent = pyqtSignal(str, str)  # email, role
    
    def __init__(self, invitation_db, email_sender, current_user_id=None, parent=None):
        super().__init__(parent)
        self.invitation_db = invitation_db
        self.email_sender = email_sender
        self.current_user_id = current_user_id
        
        self.setWindowTitle("Invite New User - NEPALI ANPR")
        self.setModal(True)
        self.setFixedWidth(500)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header_label = QLabel("📧 Invite New User")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)
        
        # Subtitle
        subtitle = QLabel("Send an email invitation with OTP for secure registration")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6c757d; font-size: 12px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Email input
        email_label = QLabel("Email Address:*")
        email_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com")
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        layout.addWidget(self.email_input)
        
        # Role selection
        role_label = QLabel("Assign Role:*")
        role_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
        layout.addWidget(role_label)
        
        # Role radio buttons
        role_frame = QFrame()
        role_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        role_layout = QVBoxLayout(role_frame)
        role_layout.setSpacing(10)
        
        self.role_group = QButtonGroup(self)
        
        # Viewer role
        self.viewer_radio = QRadioButton("👁️ Viewer - Read-only access")
        self.viewer_radio.setStyleSheet("font-size: 13px;")
        self.role_group.addButton(self.viewer_radio, 1)
        role_layout.addWidget(self.viewer_radio)
        
        # Operator role
        self.operator_radio = QRadioButton("⚙️ Operator - Can edit and manage data")
        self.operator_radio.setStyleSheet("font-size: 13px;")
        self.operator_radio.setChecked(True)  # Default
        self.role_group.addButton(self.operator_radio, 2)
        role_layout.addWidget(self.operator_radio)
        
        # Admin role
        self.admin_radio = QRadioButton("👤 Admin - Full system access")
        self.admin_radio.setStyleSheet("font-size: 13px;")
        self.role_group.addButton(self.admin_radio, 3)
        role_layout.addWidget(self.admin_radio)
        
        # SuperAdmin role
        self.superadmin_radio = QRadioButton("⭐ SuperAdmin - Complete control")
        self.superadmin_radio.setStyleSheet("font-size: 13px;")
        self.role_group.addButton(self.superadmin_radio, 4)
        role_layout.addWidget(self.superadmin_radio)
        
        layout.addWidget(role_frame)
        
        # Full name (optional)
        fullname_label = QLabel("Full Name: (optional)")
        fullname_label.setStyleSheet("font-size: 13px; margin-top: 10px;")
        layout.addWidget(fullname_label)
        
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("John Doe")
        self.fullname_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667eea;
            }
        """)
        layout.addWidget(self.fullname_input)
        
        # Info box
        info_box = QLabel(
            "ℹ️ The user will receive:\n"
            "  • A 6-digit OTP via email\n"
            "  • Instructions to complete registration\n"
            "  • OTP valid for 48 hours"
        )
        info_box.setStyleSheet("""
            background-color: #e3f2fd;
            color: #1976d2;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #1976d2;
            font-size: 12px;
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
        
        self.send_btn = QPushButton("📧 Send Invitation")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                border: none;
                padding: 12px 30px;
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
        """)
        self.send_btn.clicked.connect(self.send_invitation)
        button_layout.addWidget(self.send_btn)
        
        layout.addLayout(button_layout)
    
    def get_selected_role(self):
        """Get the selected role"""
        if self.viewer_radio.isChecked():
            return "viewer"
        elif self.operator_radio.isChecked():
            return "operator"
        elif self.admin_radio.isChecked():
            return "admin"
        elif self.superadmin_radio.isChecked():
            return "superadmin"
        return "viewer"  # Default
    
    def is_valid_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def send_invitation(self):
        """Send invitation email"""
        email = self.email_input.text().strip()
        role = self.get_selected_role()
        full_name = self.fullname_input.text().strip()
        
        # Validation
        if not email:
            QMessageBox.warning(self, "Validation Error", "Please enter an email address")
            self.email_input.setFocus()
            return
        
        if not self.is_valid_email(email):
            QMessageBox.warning(
                self,
                "Invalid Email",
                "Please enter a valid email address.\n\nExample: user@example.com"
            )
            self.email_input.setFocus()
            return
        
        # Confirm invitation
        confirm = QMessageBox.question(
            self,
            "Confirm Invitation",
            f"Send invitation to:\n\n"
            f"Email: {email}\n"
            f"Role: {role.capitalize()}\n"
            f"Full Name: {full_name or 'Not provided'}\n\n"
            f"The user will receive an OTP via email to complete registration.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Create invitation in database
            invitation = self.invitation_db.create_invitation(
                email=email,
                role=role,
                invited_by=self.current_user_id
            )
            
            if not invitation:
                QApplication.restoreOverrideCursor()
                QMessageBox.warning(
                    self,
                    "Invitation Failed",
                    f"An active invitation already exists for {email}.\n\n"
                    f"Please wait for the user to complete registration or revoke the existing invitation."
                )
                return
            
            # Send email with plain OTP (stored temporarily)
            plain_otp = getattr(invitation, '_plain_otp', None)
            if not plain_otp:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to retrieve OTP for email. Please try again."
                )
                return
            
            success = self.email_sender.send_invitation_email(
                recipient_email=email,
                otp=plain_otp,
                role=role,
                invited_by=full_name or "Admin"
            )
            
            QApplication.restoreOverrideCursor()
            
            if success:
                QMessageBox.information(
                    self,
                    "✅ Invitation Sent",
                    f"Invitation sent successfully!\n\n"
                    f"Email: {email}\n"
                    f"Role: {role.capitalize()}\n\n"
                    f"The user will receive a 6-digit OTP via email.\n"
                    f"The OTP is valid for 48 hours.\n\n"
                    f"🔒 For security, the OTP is not shown to administrators."
                )
                
                # Emit signal
                self.invitation_sent.emit(email, role)
                
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Email Send Failed",
                    f"Failed to send invitation email to {email}.\n\n"
                    f"Please check:\n"
                    f"• Email configuration in settings\n"
                    f"• Internet connection\n"
                    f"• Email address is correct\n\n"
                    f"The invitation was created but the user cannot complete registration without the email."
                )
        
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while sending invitation:\n{str(e)}"
            )
            print(f"Invitation error: {e}")
            import traceback
            traceback.print_exc()
