"""
RBAC UI Controller - Manages UI permissions based on user roles
"""
from ..auth.auth_manager import AuthManager, Permissions, Roles

class RBACUIController:
    """Controls UI elements based on user permissions"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
    
    def get_current_user_id(self):
        """Get current user ID safely"""
        if not self.auth_manager.current_username:
            return None
        try:
            # Get fresh user from database using stored username
            with self.auth_manager.get_session() as session:
                from ..db.rbac_models import User
                user = session.query(User).filter(User.username == self.auth_manager.current_username).first()
                if user:
                    return user.user_id
            return None
        except Exception as e:
            print(f"Error getting current user ID: {e}")
            return None
    
    def get_current_roles(self):
        """Get current user's roles"""
        user_id = self.get_current_user_id()
        if not user_id:
            return []
        return self.auth_manager.get_user_roles(user_id)
    
    def get_current_permissions(self):
        """Get current user's permissions"""
        user_id = self.get_current_user_id()
        if not user_id:
            return []
        return self.auth_manager.get_user_permissions(user_id)
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if current user has specific permission"""
        user_id = self.get_current_user_id()
        if not user_id:
            return False
        return self.auth_manager.has_permission(user_id, permission_name)
    
    def has_role(self, role_name: str) -> bool:
        """Check if current user has specific role"""
        user_id = self.get_current_user_id()
        if not user_id:
            return False
        return self.auth_manager.has_role(user_id, role_name)
    
    def is_viewer(self) -> bool:
        """Check if user is Viewer (read-only)"""
        return self.has_role(Roles.VIEWER) and not self.has_role(Roles.OPERATOR) and not self.has_role(Roles.ADMIN) and not self.has_role(Roles.SUPERADMIN)
    
    def is_operator(self) -> bool:
        """Check if user is Operator or higher"""
        return self.has_role(Roles.OPERATOR) or self.has_role(Roles.ADMIN) or self.has_role(Roles.SUPERADMIN)
    
    def is_admin(self) -> bool:
        """Check if user is Admin or higher"""
        return self.has_role(Roles.ADMIN) or self.has_role(Roles.SUPERADMIN)
    
    def is_superadmin(self) -> bool:
        """Check if user is SuperAdmin"""
        return self.has_role(Roles.SUPERADMIN)
    
    def can_view_dashboard(self) -> bool:
        """Can view dashboard"""
        return self.has_permission(Permissions.VIEW_DASHBOARD)
    
    def can_view_vehicle_logs(self) -> bool:
        """Can view vehicle logs"""
        return self.has_permission(Permissions.VIEW_VEHICLE_LOGS)
    
    def can_view_database(self) -> bool:
        """Can view database"""
        return self.has_permission(Permissions.VIEW_DATABASE)
    
    def can_export_data(self) -> bool:
        """Can export data (Operator and above)"""
        return self.has_permission(Permissions.EXPORT_DATA)
    
    def can_edit_plates(self) -> bool:
        """Can edit plate numbers (Operator and above)"""
        return self.has_permission(Permissions.EDIT_PLATE_DATA)
    
    def can_delete_logs(self) -> bool:
        """Can delete vehicle logs (Admin and above)"""
        return self.has_permission(Permissions.DELETE_VEHICLE_LOGS)
    
    def can_manage_users(self) -> bool:
        """Can manage users (Admin and above)"""
        return self.has_permission(Permissions.MANAGE_USERS)
    
    def can_modify_settings(self) -> bool:
        """Can modify settings (Admin and above)"""
        return self.has_permission(Permissions.MODIFY_SETTINGS)
    
    def can_view_settings(self) -> bool:
        """Can view settings (Admin and above)"""
        return self.has_permission(Permissions.VIEW_SETTINGS)
    
    def can_view_analytics(self) -> bool:
        """Can view analytics (Operator and above)"""
        return self.has_permission(Permissions.VIEW_ANALYTICS)
    
    def get_accessible_pages(self):
        """Get list of pages user can access based on new role structure"""
        pages = []
        
        # Dashboard - Operator and above only
        if self.can_view_dashboard():
            pages.append("Dashboard")
        
        # Vehicle Log - Operator and above only
        if self.can_view_vehicle_logs():
            pages.append("Vehicle Log")
        
        # Analytics - Operator and above only
        if self.can_view_analytics():
            pages.append("Analytics")
        
        # Search Plate - ALL roles (including Viewer)
        if self.can_view_database():
            pages.append("Search Plate")
        
        # User Management - Admin and above only
        if self.can_manage_users():
            pages.append("User Management")
        
        # Settings - Admin and above only
        if self.can_view_settings():
            pages.append("Settings")
        
        return pages
    
    def configure_widget_permissions(self, widget, widget_type: str):
        """
        Configure widget based on user permissions
        
        Args:
            widget: The widget to configure
            widget_type: Type of widget ('export_button', 'edit_button', 'delete_button', etc.)
        """
        if widget_type == 'export_button':
            widget.setEnabled(self.can_export_data())
            if not self.can_export_data():
                widget.setToolTip("Export permission required (Operator role or higher)")
        
        elif widget_type == 'edit_button':
            widget.setEnabled(self.can_edit_plates())
            if not self.can_edit_plates():
                widget.setToolTip("Edit permission required (Operator role or higher)")
        
        elif widget_type == 'delete_button':
            widget.setEnabled(self.can_delete_logs())
            if not self.can_delete_logs():
                widget.setToolTip("Delete permission required (Admin role or higher)")
        
        elif widget_type == 'settings_modify':
            widget.setEnabled(self.can_modify_settings())
            if not self.can_modify_settings():
                widget.setToolTip("Modify settings permission required (Admin role or higher)")
        
        elif widget_type == 'user_management':
            widget.setEnabled(self.can_manage_users())
            if not self.can_manage_users():
                widget.setToolTip("User management permission required (Admin role or higher)")
    
    def get_role_display_name(self) -> str:
        """Get display name for current user's highest role"""
        if self.is_superadmin():
            return "SuperAdmin"
        elif self.is_admin():
            return "Admin"
        elif self.is_operator():
            return "Operator"
        elif self.is_viewer():
            return "Viewer"
        else:
            return "Guest"
    
    def show_permission_denied_message(self, parent, action: str):
        """Show permission denied message"""
        from PyQt5.QtWidgets import QMessageBox
        
        role = self.get_role_display_name()
        QMessageBox.warning(
            parent,
            "Permission Denied",
            f"You don't have permission to {action}.\n\n"
            f"Your current role: {role}\n"
            f"Required permission: Admin or higher"
        )
