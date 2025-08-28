"""
RBAC Integration for Main ANPR Application
"""
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal
import sys

from ..auth.auth_manager import AuthManager, Permissions, AuthorizationError
from .login_dialog import LoginDialog
from .user_management_page import UserManagementPage

class RBACManager(QObject):
    """Manages RBAC integration throughout the application"""
    
    user_logged_in = pyqtSignal(dict)
    user_logged_out = pyqtSignal()
    permission_denied = pyqtSignal(str)
    
    def __init__(self, db_session_factory):
        super().__init__()
        self.auth_manager = AuthManager(db_session_factory)
        self.current_user = None
        
    def show_login_dialog(self, parent=None):
        """Show login dialog and handle authentication"""
        login_dialog = LoginDialog(self.auth_manager, parent)
        
        if login_dialog.exec_() == login_dialog.Accepted:
            self.current_user = login_dialog.get_user_info()
            self.user_logged_in.emit(self.current_user)
            return True
        
        return False
    
    def logout(self):
        """Logout current user"""
        if self.current_user:
            self.auth_manager.logout()
            self.current_user = None
            self.user_logged_out.emit()
    
    def check_permission(self, permission_name: str, show_message: bool = True) -> bool:
        """Check if current user has permission"""
        if not self.current_user:
            if show_message:
                QMessageBox.warning(None, "Authentication Required", 
                                  "Please login to access this feature")
            return False
        
        try:
            self.auth_manager.require_permission(permission_name)
            return True
        except AuthorizationError as e:
            if show_message:
                QMessageBox.warning(None, "Access Denied", str(e))
                self.permission_denied.emit(str(e))
            return False
    
    def get_current_user(self):
        """Get current authenticated user"""
        return self.current_user
    
    def has_permission(self, permission_name: str) -> bool:
        """Check permission without showing message"""
        return self.check_permission(permission_name, show_message=False)

def require_permission(permission_name: str):
    """Decorator to require permission for method calls"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'rbac_manager'):
                if not self.rbac_manager.check_permission(permission_name):
                    return None
            return func(self, *args, **kwargs)
        return wrapper
    return decorator

def integrate_rbac_with_main_window(main_window, rbac_manager):
    """Integrate RBAC with the main application window"""
    
    # Store RBAC manager reference
    main_window.rbac_manager = rbac_manager
    
    # Connect signals
    rbac_manager.user_logged_in.connect(lambda user: on_user_login(main_window, user))
    rbac_manager.user_logged_out.connect(lambda: on_user_logout(main_window))
    
    # Add user management to sidebar if user has permission
    def check_and_add_user_management():
        if rbac_manager.has_permission(Permissions.MANAGE_USERS):
            # Add user management page to the stack
            user_mgmt_page = UserManagementPage(rbac_manager.auth_manager)
            main_window.stack.addWidget(user_mgmt_page)
            
            # Add to sidebar
            main_window.sidebar.addItem("👥 Users")
            
            # Update sidebar handler to include user management
            original_handler = main_window.on_sidebar_changed
            def enhanced_sidebar_handler(index):
                if index == main_window.sidebar.count() - 2:  # Users tab (before logout)
                    main_window.stack.setCurrentWidget(user_mgmt_page)
                else:
                    original_handler(index)
            main_window.on_sidebar_changed = enhanced_sidebar_handler
    
    rbac_manager.user_logged_in.connect(lambda user: check_and_add_user_management())
    
    # Override existing methods with permission checks
    if hasattr(main_window, 'upload_video'):
        original_upload_video = main_window.upload_video
        def protected_upload_video():
            if rbac_manager.check_permission(Permissions.VIEW_DASHBOARD):
                return original_upload_video()
        main_window.upload_video = protected_upload_video
    
    # Protect database operations
    if hasattr(main_window, 'database_page'):
        original_refresh = main_window.database_page.refresh_all_data
        def protected_refresh():
            if rbac_manager.check_permission(Permissions.VIEW_DATABASE):
                return original_refresh()
        main_window.database_page.refresh_all_data = protected_refresh
    
    # Handle logout from sidebar
    def handle_sidebar_logout(index):
        # Check if logout was clicked (last item)
        if index == main_window.sidebar.count() - 1:
            rbac_manager.logout()
            return
        
        # Handle other sidebar items
        original_handler = getattr(main_window, '_original_sidebar_handler', main_window.on_sidebar_changed)
        original_handler(index)
    
    # Store original handler and replace
    main_window._original_sidebar_handler = main_window.on_sidebar_changed
    main_window.on_sidebar_changed = handle_sidebar_logout

def on_user_login(main_window, user_info):
    """Handle user login event"""
    # Update window title with user info
    original_title = main_window.windowTitle()
    main_window.setWindowTitle(f"{original_title} - {user_info['full_name'] or user_info['username']} ({', '.join(user_info['roles'])})")
    
    # Show welcome message
    from PyQt5.QtWidgets import QStatusBar
    if hasattr(main_window, 'statusBar'):
        main_window.statusBar().showMessage(f"Welcome, {user_info['full_name'] or user_info['username']}!", 5000)

def on_user_logout(main_window):
    """Handle user logout event"""
    # Reset window title
    title = main_window.windowTitle()
    if " - " in title:
        main_window.setWindowTitle(title.split(" - ")[0])
    
    # Show logout message
    if hasattr(main_window, 'statusBar'):
        main_window.statusBar().showMessage("Logged out successfully", 3000)
    
    # Remove user management from sidebar if exists
    for i in range(main_window.sidebar.count()):
        if "👥 Users" in main_window.sidebar.item(i).text():
            main_window.sidebar.takeItem(i)
            break
    
    # Close the application after logout
    from PyQt5.QtWidgets import QApplication
    QApplication.quit()
