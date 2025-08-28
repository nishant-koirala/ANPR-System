"""
User Management Page for RBAC System
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLineEdit, QComboBox,
                           QLabel, QMessageBox, QDialog, QFormLayout, QCheckBox,
                           QGroupBox, QScrollArea, QFrame, QHeaderView, QRadioButton,
                           QButtonGroup)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime
from ..auth.auth_manager import AuthManager, Permissions, Roles, AuthorizationError

class CreateUserDialog(QDialog):
    """Dialog for creating new users"""
    
    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        print(f"DEBUG: CreateUserDialog.__init__ called with auth_manager: {auth_manager}")
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
        roles_group = QGroupBox("Assign Role (Select One)")
        roles_layout = QVBoxLayout()
        
        self.role_button_group = QButtonGroup()
        self.role_buttons = {}
        
        for i, role in enumerate([Roles.VIEWER, Roles.OPERATOR, Roles.ADMIN, Roles.SUPERADMIN]):
            radio_button = QRadioButton(role)
            self.role_buttons[role] = radio_button
            self.role_button_group.addButton(radio_button, i)
            roles_layout.addWidget(radio_button)
        
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
            print("DEBUG: Starting user creation process...")
            
            username = self.username_edit.text().strip()
            password = self.password_edit.text()
            email = self.email_edit.text().strip()
            fullname = self.fullname_edit.text().strip()
            
            print(f"DEBUG: Form data - Username: '{username}', Email: '{email}', Full name: '{fullname}'")
            
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
            print(f"DEBUG: Selected role: {selected_role}")
            
            # Check if auth_manager is available
            if not self.auth_manager:
                QMessageBox.critical(self, "Error", "Authentication manager not available")
                return
            
            print("DEBUG: Calling auth_manager.create_user...")
            user_id = self.auth_manager.create_user(
                username=username,
                password=password,
                email=email,
                full_name=fullname if fullname else None,
                roles=selected_roles
            )
            
            print(f"DEBUG: User created successfully with ID: {user_id}")
            QMessageBox.information(self, "Success", 
                                  f"User '{username}' created successfully (ID: {user_id})")
            self.accept()
            
        except ValueError as ve:
            print(f"DEBUG: ValueError occurred: {str(ve)}")
            QMessageBox.critical(self, "Validation Error", str(ve))
        except Exception as e:
            print(f"DEBUG: Exception occurred: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
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
        self.create_user_btn = QPushButton("➕ Create User")
        self.create_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
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
        header_layout.addWidget(self.create_user_btn)
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
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Username", "Full Name", "Email", 
            "Roles", "Last Login", "Actions"
        ])
        
        # Set table properties
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        
        # Resize columns
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Username
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Full Name
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Email
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Roles
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Last Login
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Actions
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        
        # Add all components to layout
        layout.addLayout(header_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.users_table)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Connect signals
        self.create_user_btn.clicked.connect(self.create_user)
        self.refresh_btn.clicked.connect(self.load_users)
        self.search_edit.textChanged.connect(self.filter_users)
        self.status_filter.currentTextChanged.connect(self.filter_users)
        
    def check_permissions(self):
        """Check if current user has required permissions"""
        try:
            # If no current user is set, assume admin access for now
            if not self.auth_manager.current_user:
                return True
            
            self.auth_manager.require_permission(Permissions.MANAGE_USERS)
            return True
        except AuthorizationError:
            QMessageBox.warning(self, "Access Denied", 
                              "You don't have permission to manage users")
            return False
    
    def create_user(self):
        """Open create user dialog"""
        print("DEBUG: Create user button clicked!")
        
        if not self.check_permissions():
            print("DEBUG: Permission check failed")
            return
        
        print("DEBUG: Opening CreateUserDialog...")
        try:
            dialog = CreateUserDialog(self.auth_manager, self)
            print("DEBUG: Dialog created successfully")
            result = dialog.exec_()
            print(f"DEBUG: Dialog result: {result}")
            if result == QDialog.Accepted:
                print("DEBUG: Dialog accepted, reloading users...")
                self.load_users()
        except Exception as e:
            print(f"DEBUG: Exception creating dialog: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to open user creation dialog: {str(e)}")
    
    def load_users(self):
        """Load users from database"""
        try:
            # If no current user is set, assume admin access for now
            if self.auth_manager.current_user:
                self.auth_manager.require_permission(Permissions.VIEW_AUDIT_LOGS)
        except AuthorizationError:
            self.status_label.setText("Access denied - insufficient permissions")
            return
        
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
                    self.users_table.setItem(row, 4, QTableWidgetItem(roles_text))
                    
                    # Last login
                    last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
                    self.users_table.setItem(row, 5, QTableWidgetItem(last_login))
                    
                    # Action buttons
                    actions_widget = QWidget()
                    actions_layout = QHBoxLayout()
                    actions_layout.setContentsMargins(4, 4, 4, 4)
                    
                    edit_btn = QPushButton("✏️")
                    edit_btn.setToolTip("Edit User")
                    edit_btn.setMaximumSize(30, 30)
                    edit_btn.clicked.connect(lambda checked, uid=user.user_id: self.edit_user(uid))
                    
                    delete_btn = QPushButton("🗑️")
                    delete_btn.setToolTip("Delete User")
                    delete_btn.setMaximumSize(30, 30)
                    delete_btn.clicked.connect(lambda checked, uid=user.user_id: self.delete_user(uid))
                    
                    actions_layout.addWidget(edit_btn)
                    actions_layout.addWidget(delete_btn)
                    actions_layout.addStretch()
                    actions_widget.setLayout(actions_layout)
                    
                    self.users_table.setCellWidget(row, 6, actions_widget)
                
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
            
            # Status filter - removed since status column no longer exists
            
            self.users_table.setRowHidden(row, not show_row)
    
    def edit_user(self, user_id):
        """Edit user (placeholder)"""
        if not self.check_permissions():
            return
        QMessageBox.information(self, "Edit User", f"Edit user functionality for ID {user_id} - Coming soon!")
    
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
