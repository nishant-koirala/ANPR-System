"""
User Management Page for RBAC System
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLineEdit, QComboBox,
                           QLabel, QMessageBox, QDialog, QFormLayout, QCheckBox,
                           QGroupBox, QScrollArea, QFrame, QHeaderView, QRadioButton,
                           QButtonGroup, QTabWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime
from ..auth.auth_manager import AuthManager, Permissions, Roles, AuthorizationError
from .invite_user_dialog import InviteUserDialog
from ..db.invitation_db import InvitationDB
from ..alerts.invitation_email import InvitationEmailSender
from config.settings import SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_APP_PASSWORD

# Import modern UI components
try:
    from .ui_components import ActionButton
    UI_COMPONENTS_AVAILABLE = True
except ImportError:
    UI_COMPONENTS_AVAILABLE = False

class CreateUserDialog(QDialog):
    """Dialog for creating new users"""
    
    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Create New User")
        self.setFixedSize(500, 600)
        
        layout = QVBoxLayout()
        
        # User details form
        form_layout = QFormLayout()
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter username")
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Enter password")
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("user@example.com")
        
        self.fullname_edit = QLineEdit()
        self.fullname_edit.setPlaceholderText("Full Name")
        
        form_layout.addRow("Username*:", self.username_edit)
        form_layout.addRow("Password*:", self.password_edit)
        form_layout.addRow("Email*:", self.email_edit)
        form_layout.addRow("Full Name:", self.fullname_edit)
        
        # Role selection (single role only)
        # NEW RBAC: ADMIN cannot create SUPERADMIN
        roles_group = QGroupBox("Assign Role (Select One)")
        roles_layout = QVBoxLayout()
        
        self.role_button_group = QButtonGroup()
        self.role_buttons = {}
        
        # Check if current user is SUPERADMIN
        from ..ui.rbac_ui_controller import RBACUIController
        rbac = RBACUIController(self.auth_manager)
        is_superadmin = rbac.is_superadmin()
        
        # Show all roles for SUPERADMIN, exclude SUPERADMIN for ADMIN
        available_roles = [Roles.VIEWER, Roles.OPERATOR, Roles.ADMIN]
        if is_superadmin:
            available_roles.append(Roles.SUPERADMIN)
        
        for i, role in enumerate(available_roles):
            radio_button = QRadioButton(role)
            self.role_buttons[role] = radio_button
            self.role_button_group.addButton(radio_button, i)
            roles_layout.addWidget(radio_button)
        
        # Add note for ADMIN users
        if not is_superadmin:
            note_label = QLabel("Note: Only SUPERADMIN can create SUPERADMIN users")
            note_label.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
            roles_layout.addWidget(note_label)
        
        # Set VIEWER as default
        self.role_buttons[Roles.VIEWER].setChecked(True)
        
        roles_group.setLayout(roles_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.create_button = QPushButton("Create User")
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.create_button)
        
        # Add to main layout
        layout.addLayout(form_layout)
        layout.addWidget(roles_group)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connections
        self.create_button.clicked.connect(self.create_user)
        self.cancel_button.clicked.connect(self.reject)
        
    def create_user(self):
        try:
            username = self.username_edit.text().strip()
            password = self.password_edit.text()
            email = self.email_edit.text().strip()
            fullname = self.fullname_edit.text().strip()
            
            # Validate required fields
            if not username:
                QMessageBox.warning(self, "Error", "Username is required")
                return
            if not password:
                QMessageBox.warning(self, "Error", "Password is required")
                return
            if not email:
                QMessageBox.warning(self, "Error", "Email is required")
                return
            
            # Basic email validation
            if '@' not in email or '.' not in email:
                QMessageBox.warning(self, "Error", "Please enter a valid email address")
                return
            
            # Get selected role (only one can be selected)
            selected_role = None
            for role, radio_button in self.role_buttons.items():
                if radio_button.isChecked():
                    selected_role = role
                    break
            
            if not selected_role:
                QMessageBox.warning(self, "Error", "Please select a role for the user")
                return
            
            selected_roles = [selected_role]
            
            # Check if auth_manager is available
            if not self.auth_manager:
                QMessageBox.critical(self, "Error", "Authentication manager not available")
                return
            
            user_id = self.auth_manager.create_user(
                username=username,
                password=password,
                email=email,
                full_name=fullname if fullname else None,
                roles=selected_roles
            )
            
            QMessageBox.information(self, "Success", 
                                  f"User '{username}' created successfully (ID: {user_id})")
            self.accept()
            
        except ValueError as ve:
            QMessageBox.critical(self, "Validation Error", str(ve))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create user: {str(e)}\n\nType: {type(e).__name__}")

class UserManagementPage(QWidget):
    """User management interface for RBAC system"""
    
    def __init__(self, auth_manager):
        super().__init__()
        self.auth_manager = auth_manager
        self.init_ui()
        self.load_users()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_users)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("👥 User Management")
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        
        # Action buttons
        self.invite_user_btn = QPushButton("📧 Invite User")
        self.invite_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5568d3;
            }
        """)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.invite_user_btn)
        header_layout.addWidget(self.refresh_btn)
        
        # Search/Filter section
        filter_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search users...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
        """)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Status", "ACTIVE", "INACTIVE", "SUSPENDED"])
        self.status_filter.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-width: 120px;
            }
        """)
        
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addStretch()
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(8)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Username", "Full Name", "Email", 
            "Status", "Roles", "Last Login", "Actions"
        ])
        
        # Set table properties
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.horizontalHeader().setStretchLastSection(True)
        # Use global stylesheet - no inline styling needed
        
        # Resize columns
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Username
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Full Name
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Email
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # Roles
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Last Login
        header.setSectionResizeMode(7, QHeaderView.Fixed)             # Actions
        
        # Set minimum width for Actions column to show buttons properly
        self.users_table.setColumnWidth(7, 250)  # Wide enough for Edit + Delete buttons with text
        
        # Invitations section (collapsible)
        self.invitations_frame = QFrame()
        invitations_layout = QVBoxLayout(self.invitations_frame)
        invitations_layout.setContentsMargins(0, 10, 0, 0)
        
        # Toggle button for invitations
        self.toggle_invitations_btn = QPushButton("▼ Show Sent Invitations")
        self.toggle_invitations_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #212529;
                border: 1px solid #dee2e6;
                padding: 10px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                color: #000000;
            }
        """)
        self.toggle_invitations_btn.clicked.connect(self.toggle_invitations)
        invitations_layout.addWidget(self.toggle_invitations_btn)
        
        # Invitations table (initially hidden)
        self.invitations_table = QTableWidget()
        self.invitations_table.setColumnCount(7)
        self.invitations_table.setHorizontalHeaderLabels([
            "Email", "Role", "Status", "Created", "Expires", "Completed By", "Actions"
        ])
        self.invitations_table.setAlternatingRowColors(True)
        self.invitations_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.invitations_table.horizontalHeader().setStretchLastSection(True)
        self.invitations_table.hide()  # Initially hidden
        
        # Resize invitation columns
        inv_header = self.invitations_table.horizontalHeader()
        inv_header.setSectionResizeMode(0, QHeaderView.Stretch)  # Email
        inv_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Role
        inv_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        inv_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Created
        inv_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Expires
        inv_header.setSectionResizeMode(5, QHeaderView.Stretch)  # Completed By
        inv_header.setSectionResizeMode(6, QHeaderView.Fixed)  # Actions
        self.invitations_table.setColumnWidth(6, 150)
        
        invitations_layout.addWidget(self.invitations_table)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        
        # Add all components to layout
        layout.addLayout(header_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.users_table)
        layout.addWidget(self.invitations_frame)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Connect signals
        self.invite_user_btn.clicked.connect(self.invite_user)
        self.refresh_btn.clicked.connect(self.load_users)
        self.search_edit.textChanged.connect(self.filter_users)
        self.status_filter.currentTextChanged.connect(self.filter_users)
        
    def check_permissions(self):
        """Check if current user has required permissions"""
        try:
            # Require authentication - no anonymous access
            if not self.auth_manager.current_user:
                QMessageBox.warning(self, "Authentication Required", 
                                  "Please log in to access user management")
                return False
            
            # Get user ID safely using current_username
            try:
                if not self.auth_manager.current_username:
                    QMessageBox.warning(self, "Not Logged In",
                                      "Please log in to access user management")
                    return False
                
                # Get user ID from username
                with self.auth_manager.get_session() as session:
                    from ..db.rbac_models import User
                    user = session.query(User).filter(User.username == self.auth_manager.current_username).first()
                    if not user:
                        return False
                    user_id = user.user_id
                
                if not self.auth_manager.has_permission(user_id, Permissions.MANAGE_USERS):
                    QMessageBox.warning(self, "Access Denied", 
                                      "You don't have permission to manage users")
                    print(f"DEBUG: Permission denied for user ID: {user_id}")
                    return False
                
                print(f"DEBUG: Permission check passed for user ID: {user_id}")
                return True
            except Exception as e:
                print(f"DEBUG: Permission check error: {e}")
                return False
                
        except Exception as e:
            print(f"DEBUG: General permission check error: {e}")
            return False
    
    def invite_user(self):
        """Invite new user via email"""
        print("📧 Invite user button clicked!")
        
        if not self.check_permissions():
            print("⚠️ Permission check failed")
            return
        
        try:
            # Get current user ID
            current_user_id = None
            if self.auth_manager.current_username:
                user = self.auth_manager.get_user_by_username(self.auth_manager.current_username)
                if user:
                    current_user_id = user.user_id
            
            # Initialize invitation system if not already done
            if not hasattr(self, 'invitation_db'):
                self.invitation_db = InvitationDB(self.auth_manager.get_session)
            if not hasattr(self, 'email_sender'):
                self.email_sender = InvitationEmailSender(
                    SMTP_SERVER, SMTP_PORT,
                    EMAIL_SENDER, EMAIL_APP_PASSWORD
                )
            
            # Open invite dialog
            dialog = InviteUserDialog(
                self.invitation_db,
                self.email_sender,
                current_user_id,
                self
            )
            
            # Connect signal
            dialog.invitation_sent.connect(self.on_invitation_sent)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open invitation dialog:\n{str(e)}"
            )
            print(f"❌ Invite user error: {e}")
            import traceback
            traceback.print_exc()
    
    def on_invitation_sent(self, email, role):
        """Handle invitation sent signal"""
        print(f"✅ Invitation sent to {email} as {role}")
        QMessageBox.information(
            self,
            "Invitation Sent",
            f"Invitation successfully sent to:\n{email}\n\nRole: {role.capitalize()}\n\n⏱️ OTP expires in 5 minutes!"
        )
        # Refresh invitations if visible
        if self.invitations_table.isVisible():
            self.load_invitations()
    
    def load_users(self):
        """Load users from database"""
        try:
            # Check permissions if user is logged in
            if self.auth_manager.current_username:
                try:
                    # Get user ID from username
                    with self.auth_manager.get_session() as session:
                        from ..db.rbac_models import User
                        current_user = session.query(User).filter(
                            User.username == self.auth_manager.current_username
                        ).first()
                        
                        if current_user and not self.auth_manager.has_permission(current_user.user_id, Permissions.VIEW_AUDIT_LOGS):
                            self.status_label.setText("Access denied - insufficient permissions")
                            return
                except Exception as perm_error:
                    print(f"DEBUG: Permission check error: {perm_error}")
                    # Skip permission check if there's an error - allow access for now
                    pass
        except Exception as e:
            print(f"DEBUG: General permission error: {e}")
            # Skip permission check if there's an error - allow access for now
            pass
        
        self.status_label.setText("Loading users...")
        
        try:
            with self.auth_manager.get_session() as session:
                from ..db.rbac_models import User, UserRole, Role
                
                # Get all users with their roles
                users = session.query(User).all()
                
                self.users_table.setRowCount(len(users))
                
                for row, user in enumerate(users):
                    # Get user roles
                    user_roles = session.query(Role.role_name).join(UserRole).filter(
                        UserRole.user_id == user.user_id
                    ).all()
                    roles_text = ", ".join([role[0] for role in user_roles])
                    
                    # Populate table
                    self.users_table.setItem(row, 0, QTableWidgetItem(str(user.user_id)))
                    self.users_table.setItem(row, 1, QTableWidgetItem(user.username))
                    self.users_table.setItem(row, 2, QTableWidgetItem(user.full_name or ""))
                    self.users_table.setItem(row, 3, QTableWidgetItem(user.email))
                    
                    # Status with color coding
                    status_item = QTableWidgetItem(user.status.value)
                    if user.status.value == "ACTIVE":
                        status_item.setForeground(Qt.darkGreen)
                    elif user.status.value == "SUSPENDED":
                        status_item.setForeground(Qt.red)
                    else:
                        status_item.setForeground(Qt.gray)
                    self.users_table.setItem(row, 4, status_item)
                    
                    self.users_table.setItem(row, 5, QTableWidgetItem(roles_text))
                    
                    # Last login
                    last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
                    self.users_table.setItem(row, 6, QTableWidgetItem(last_login))
                    
                    # Action buttons - Use direct QPushButton for reliability
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout()
                    actions_layout.setContentsMargins(4, 4, 4, 4)
                    actions_layout.setSpacing(4)
                    
                    # Edit button
                    edit_btn = QPushButton("✏ Edit")
                    edit_btn.setToolTip("Edit User")
                    edit_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3498DB;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 8px 16px;
                            font-size: 13px;
                            font-weight: 600;
                            min-width: 70px;
                            min-height: 32px;
                        }
                        QPushButton:hover {
                            background-color: #2980B9;
                        }
                    """)
                    
                    # Delete button
                    delete_btn = QPushButton("🗑 Delete")
                    delete_btn.setToolTip("Delete User")
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #E74C3C;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 8px 16px;
                            font-size: 13px;
                            font-weight: 600;
                            min-width: 70px;
                            min-height: 32px;
                        }
                        QPushButton:hover {
                            background-color: #C0392B;
                        }
                    """)
                    
                    edit_btn.clicked.connect(lambda checked, uid=user.user_id: self.edit_user(uid))
                    delete_btn.clicked.connect(lambda checked, uid=user.user_id: self.delete_user(uid))
                    
                    actions_layout.addWidget(edit_btn)
                    actions_layout.addWidget(delete_btn)
                    
                    actions_widget.setLayout(actions_layout)
                    self.users_table.setCellWidget(row, 7, actions_widget)
                
                self.status_label.setText(f"Loaded {len(users)} users")
                
        except Exception as e:
            self.status_label.setText(f"Error loading users: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(e)}")
    
    def filter_users(self):
        """Filter users based on search and status"""
        search_text = self.search_edit.text().lower()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.users_table.rowCount()):
            show_row = True
            
            # Search filter
            if search_text:
                username = self.users_table.item(row, 1).text().lower()
                fullname = self.users_table.item(row, 2).text().lower()
                email = self.users_table.item(row, 3).text().lower()
                
                if not any(search_text in field for field in [username, fullname, email]):
                    show_row = False
            
            # Status filter (column 4)
            if status_filter != "All Status":
                status = self.users_table.item(row, 4).text()
                if status != status_filter:
                    show_row = False
            
            self.users_table.setRowHidden(row, not show_row)
    
    def edit_user(self, user_id):
        """Edit user - Change status and reset failed attempts"""
        if not self.check_permissions():
            return
        
        try:
            from ..db.rbac_models import User, UserStatus
            
            # Get user info first (extract all data before session closes)
            with self.auth_manager.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    QMessageBox.warning(self, "Error", "User not found")
                    return
                
                # Extract all needed data while session is active
                username = user.username
                email = user.email
                current_status = user.status.value
                failed_attempts = user.failed_login_attempts
            
            # Create edit dialog (outside session context)
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit User: {username}")
            dialog.setFixedSize(400, 300)
            
            layout = QVBoxLayout()
            
            # User info
            info_label = QLabel(f"<b>Username:</b> {username}<br>"
                               f"<b>Email:</b> {email}<br>"
                               f"<b>Current Status:</b> {current_status}<br>"
                               f"<b>Failed Attempts:</b> {failed_attempts}")
            layout.addWidget(info_label)
            
            # Status selection
            status_group = QGroupBox("Change Status")
            status_layout = QVBoxLayout()
            
            status_combo = QComboBox()
            status_combo.addItems(["ACTIVE", "SUSPENDED", "INACTIVE"])
            status_combo.setCurrentText(current_status)
            status_layout.addWidget(QLabel("Status:"))
            status_layout.addWidget(status_combo)
            
            status_group.setLayout(status_layout)
            layout.addWidget(status_group)
            
            # Reset failed attempts checkbox
            reset_attempts_cb = QCheckBox("Reset failed login attempts to 0")
            if failed_attempts > 0:
                reset_attempts_cb.setChecked(True)
            layout.addWidget(reset_attempts_cb)
            
            # Buttons
            button_layout = QHBoxLayout()
            save_btn = QPushButton("Save Changes")
            cancel_btn = QPushButton("Cancel")
            
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(save_btn)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # Connect buttons
            def save_changes():
                try:
                    # Open new session for saving
                    with self.auth_manager.get_session() as save_session:
                        user = save_session.query(User).filter(User.user_id == user_id).first()
                        if not user:
                            QMessageBox.warning(self, "Error", "User not found")
                            return
                        
                        new_status = status_combo.currentText()
                        user.status = UserStatus[new_status]
                        
                        if reset_attempts_cb.isChecked():
                            user.failed_login_attempts = 0
                        
                        save_session.commit()
                    
                    QMessageBox.information(self, "Success", 
                                          f"User '{username}' updated successfully!")
                    dialog.accept()
                    self.load_users()
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)}")
            
            save_btn.clicked.connect(save_changes)
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec_()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit user: {str(e)}")
    
    def delete_user(self, user_id):
        """Delete user"""
        if not self.check_permissions():
            return
        
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   "Are you sure you want to delete this user?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                with self.auth_manager.get_session() as session:
                    from ..db.rbac_models import User
                    user = session.query(User).filter(User.user_id == user_id).first()
                    if user:
                        session.delete(user)
                        session.commit()
                        QMessageBox.information(self, "Success", "User deleted successfully")
                        self.load_users()
                    else:
                        QMessageBox.warning(self, "Error", "User not found")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {str(e)}")
    
    def toggle_invitations(self):
        """Toggle invitations table visibility"""
        if self.invitations_table.isVisible():
            self.invitations_table.hide()
            self.toggle_invitations_btn.setText("▼ Show Sent Invitations")
        else:
            self.invitations_table.show()
            self.toggle_invitations_btn.setText("▲ Hide Sent Invitations")
            self.load_invitations()
    
    def load_invitations(self):
        """Load all sent invitations"""
        try:
            # Initialize invitation_db if not already done
            if not hasattr(self, 'invitation_db'):
                self.invitation_db = InvitationDB(self.auth_manager.get_session)
            
            # Get all invitations
            invitations = self.invitation_db.get_all_invitations(limit=100)
            
            # Clear table
            self.invitations_table.setRowCount(0)
            
            # Populate table
            for inv in invitations:
                row = self.invitations_table.rowCount()
                self.invitations_table.insertRow(row)
                
                # Email
                self.invitations_table.setItem(row, 0, QTableWidgetItem(inv.email))
                
                # Role
                role_item = QTableWidgetItem(inv.role.capitalize())
                self.invitations_table.setItem(row, 1, role_item)
                
                # Status with color
                status_item = QTableWidgetItem(inv.status.upper())
                if inv.status == 'pending':
                    status_item.setForeground(Qt.darkYellow)
                elif inv.status == 'verified':
                    status_item.setForeground(Qt.blue)
                elif inv.status == 'completed':
                    status_item.setForeground(Qt.darkGreen)
                elif inv.status == 'expired':
                    status_item.setForeground(Qt.red)
                else:  # revoked
                    status_item.setForeground(Qt.gray)
                self.invitations_table.setItem(row, 2, status_item)
                
                # Created
                created_str = inv.created_at.strftime("%Y-%m-%d %H:%M") if inv.created_at else ""
                self.invitations_table.setItem(row, 3, QTableWidgetItem(created_str))
                
                # Expires (show time remaining)
                if inv.expires_at:
                    from datetime import datetime
                    now = datetime.utcnow()
                    if now < inv.expires_at:
                        delta = inv.expires_at - now
                        minutes = int(delta.total_seconds() / 60)
                        if minutes < 60:
                            expires_str = f"{minutes}m left"
                        else:
                            hours = int(minutes / 60)
                            expires_str = f"{hours}h left"
                    else:
                        expires_str = "Expired"
                else:
                    expires_str = ""
                self.invitations_table.setItem(row, 4, QTableWidgetItem(expires_str))
                
                # Completed By
                completed_by = inv.completed_by_username or ""
                self.invitations_table.setItem(row, 5, QTableWidgetItem(completed_by))
                
                # Actions
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                
                if inv.status == 'pending':
                    # Revoke button for pending invitations
                    revoke_btn = QPushButton("Revoke")
                    revoke_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #dc3545;
                            color: white;
                            border: none;
                            padding: 4px 8px;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #c82333;
                        }
                    """)
                    revoke_btn.clicked.connect(lambda checked, inv_id=inv.id: self.revoke_invitation(inv_id))
                    actions_layout.addWidget(revoke_btn)
                
                self.invitations_table.setCellWidget(row, 6, actions_widget)
            
            # Update button text with count
            pending_count = sum(1 for inv in invitations if inv.status == 'pending')
            if self.invitations_table.isVisible():
                self.toggle_invitations_btn.setText(f"▲ Hide Sent Invitations ({len(invitations)} total, {pending_count} pending)")
            else:
                self.toggle_invitations_btn.setText(f"▼ Show Sent Invitations ({len(invitations)} total, {pending_count} pending)")
            
            print(f"✅ Loaded {len(invitations)} invitations ({pending_count} pending)")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load invitations:\n{str(e)}")
            print(f"❌ Error loading invitations: {e}")
            import traceback
            traceback.print_exc()
    
    def revoke_invitation(self, invitation_id):
        """Revoke a pending invitation"""
        reply = QMessageBox.question(
            self,
            "Revoke Invitation",
            "Are you sure you want to revoke this invitation?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if not hasattr(self, 'invitation_db'):
                    self.invitation_db = InvitationDB(self.auth_manager.get_session)
                
                success = self.invitation_db.revoke_invitation(invitation_id)
                
                if success:
                    QMessageBox.information(self, "Success", "Invitation revoked successfully")
                    self.load_invitations()
                else:
                    QMessageBox.warning(self, "Failed", "Could not revoke invitation")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to revoke invitation:\n{str(e)}")
