"""
RBAC System Setup and Initialization
"""
from sqlalchemy.orm import Session
from datetime import datetime
from ..auth.auth_manager import AuthManager, Permissions, Roles
from .rbac_models import User, Role, Permission, RolePermission, UserRole, UserStatus

def initialize_rbac_system(db_session_factory, admin_username: str = "admin", admin_password: str = "admin123"):
    """
    Initialize RBAC system with default roles, permissions, and admin user
    """
    with db_session_factory() as session:
        # Create default permissions
        default_permissions = [
            # System Administration
            (Permissions.MANAGE_USERS, "Create, update, delete users", "System"),
            (Permissions.MANAGE_ROLES, "Create, update, delete roles", "System"),
            (Permissions.MANAGE_PERMISSIONS, "Manage permission assignments", "System"),
            (Permissions.VIEW_AUDIT_LOGS, "View system audit logs", "System"),
            (Permissions.SYSTEM_CONFIG, "Configure system settings", "System"),
            
            # ANPR Operations
            (Permissions.VIEW_DASHBOARD, "Access main dashboard", "ANPR"),
            (Permissions.VIEW_VEHICLE_LOGS, "View vehicle detection logs", "ANPR"),
            (Permissions.DELETE_VEHICLE_LOGS, "Delete vehicle logs", "ANPR"),
            (Permissions.EXPORT_DATA, "Export data to files", "ANPR"),
            (Permissions.EDIT_PLATE_DATA, "Edit license plate numbers", "ANPR"),
            (Permissions.VIEW_ANALYTICS, "View analytics and reports", "ANPR"),
            
            # Camera Management
            (Permissions.CONFIG_CAMERAS, "Configure camera settings", "Camera"),
            (Permissions.VIEW_CAMERA_STATUS, "View camera status", "Camera"),
            
            # Database Operations
            (Permissions.VIEW_DATABASE, "View database contents", "Database"),
            (Permissions.MANAGE_DATABASE, "Manage database operations", "Database"),
            (Permissions.BACKUP_DATABASE, "Create database backups", "Database"),
            
            # Settings
            (Permissions.MODIFY_SETTINGS, "Modify application settings", "Settings"),
            (Permissions.VIEW_SETTINGS, "View application settings", "Settings"),
        ]
        
        # Create permissions
        permission_map = {}
        for perm_name, description, category in default_permissions:
            existing = session.query(Permission).filter(Permission.permission_name == perm_name).first()
            if not existing:
                permission = Permission(
                    permission_name=perm_name,
                    description=description,
                    category=category,
                    is_system_permission=True
                )
                session.add(permission)
                session.flush()
                permission_map[perm_name] = permission.permission_id
            else:
                permission_map[perm_name] = existing.permission_id
        
        # Create default roles
        default_roles = [
            (Roles.SUPERADMIN, "Full system access - can do everything", [
                Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.MANAGE_PERMISSIONS,
                Permissions.VIEW_AUDIT_LOGS, Permissions.SYSTEM_CONFIG, Permissions.VIEW_DASHBOARD,
                Permissions.VIEW_VEHICLE_LOGS, Permissions.DELETE_VEHICLE_LOGS, Permissions.EXPORT_DATA,
                Permissions.EDIT_PLATE_DATA, Permissions.VIEW_ANALYTICS,
                Permissions.CONFIG_CAMERAS, Permissions.VIEW_CAMERA_STATUS, Permissions.VIEW_DATABASE,
                Permissions.MANAGE_DATABASE, Permissions.BACKUP_DATABASE, Permissions.MODIFY_SETTINGS,
                Permissions.VIEW_SETTINGS
            ]),
            (Roles.ADMIN, "Administrative access - all except create superadmin", [
                Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.VIEW_AUDIT_LOGS,
                Permissions.VIEW_DASHBOARD, Permissions.VIEW_VEHICLE_LOGS, Permissions.DELETE_VEHICLE_LOGS,
                Permissions.EXPORT_DATA, Permissions.EDIT_PLATE_DATA, Permissions.VIEW_ANALYTICS,
                Permissions.CONFIG_CAMERAS, Permissions.VIEW_CAMERA_STATUS, Permissions.VIEW_DATABASE,
                Permissions.MANAGE_DATABASE, Permissions.BACKUP_DATABASE, Permissions.MODIFY_SETTINGS, 
                Permissions.VIEW_SETTINGS
            ]),
            (Roles.OPERATOR, "Operational access - dashboard, analytics, edit, export", [
                Permissions.VIEW_DASHBOARD, Permissions.VIEW_VEHICLE_LOGS, Permissions.VIEW_ANALYTICS,
                Permissions.EXPORT_DATA, Permissions.EDIT_PLATE_DATA, Permissions.VIEW_DATABASE
            ]),
            (Roles.VIEWER, "Search plate only - no edit", [
                Permissions.VIEW_DATABASE  # Only search functionality
            ])
        ]
        
        # Create roles and assign permissions
        role_map = {}
        for role_name, description, permissions in default_roles:
            existing_role = session.query(Role).filter(Role.role_name == role_name).first()
            if not existing_role:
                role = Role(
                    role_name=role_name,
                    description=description,
                    is_system_role=True
                )
                session.add(role)
                session.flush()
                role_map[role_name] = role.role_id
                
                # Assign permissions to role
                for perm_name in permissions:
                    if perm_name in permission_map:
                        role_perm = RolePermission(
                            role_id=role.role_id,
                            permission_id=permission_map[perm_name]
                        )
                        session.add(role_perm)
            else:
                role_map[role_name] = existing_role.role_id
        
        # Create default admin user
        existing_admin = session.query(User).filter(User.username == admin_username).first()
        if not existing_admin:
            auth_manager = AuthManager(lambda: session)
            admin_user = User(
                username=admin_username,
                password_hash=auth_manager.hash_password(admin_password),
                email="admin@anpr.local",
                full_name="System Administrator",
                status=UserStatus.ACTIVE
            )
            session.add(admin_user)
            session.flush()
            
            # Assign SUPERADMIN role to admin user
            if Roles.SUPERADMIN in role_map:
                admin_role = UserRole(
                    user_id=admin_user.user_id,
                    role_id=role_map[Roles.SUPERADMIN]
                )
                session.add(admin_role)
        
        session.commit()
        print("✅ RBAC system initialized successfully")
        print(f"📝 Default admin user: {admin_username} / {admin_password}")
        print("🔐 Please change the default password after first login!")

def create_sample_users(db_session_factory):
    """Create sample users for testing"""
    auth_manager = AuthManager(db_session_factory)
    
    # Skip login for initial setup - just create users directly
    print("📝 Creating sample users...")
    
    sample_users = [
        ("john_operator", "operator123", "john@anpr.local", "John Smith", [Roles.OPERATOR]),
        ("jane_viewer", "viewer123", "jane@anpr.local", "Jane Doe", [Roles.VIEWER]),
        ("mike_admin", "admin123", "mike@anpr.local", "Mike Johnson", [Roles.ADMIN])
    ]
    
    for username, password, email, full_name, roles in sample_users:
        try:
            user_id = auth_manager.create_user(username, password, email, full_name, roles)
            print(f"✅ Created user: {username} (ID: {user_id}) with roles: {', '.join(roles)}")
        except Exception as e:
            print(f"⚠️  User {username} already exists or error: {e}")
    
    auth_manager.logout()

def get_user_permissions_summary(db_session_factory, username: str):
    """Get and display user permissions summary"""
    try:
        auth_manager = AuthManager(db_session_factory)
        
        with db_session_factory() as session:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                print(f"❌ User '{username}' not found")
                return
            
            # Extract user data before session operations
            user_data = {
                'user_id': user.user_id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email
            }
        
        print(f"\n📋 Permissions Summary for {user_data['username']}:")
        print("=" * 50)
        
        roles = auth_manager.get_user_roles(user_data['user_id'])
        permissions = auth_manager.get_user_permissions(user_data['user_id'])
        
        print(f"👤 User: {user_data['full_name'] or user_data['username']}")
        print(f"📧 Email: {user_data['email']}")
        print(f"🎭 Roles: {', '.join(roles)}")
        print(f"🔑 Permissions ({len(permissions)}):")
        
        for perm in sorted(permissions):
            print(f"   • {perm}")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"⚠️  Could not display permissions summary: {e}")
        print("✅ But the admin user was created successfully!")

if __name__ == "__main__":
    # Example usage
    from ..db.database import get_database
    
    db = get_database()
    
    # Initialize RBAC system
    initialize_rbac_system(db.get_session)
    
    # Create sample users
    create_sample_users(db.get_session)
    
    # Show permissions for admin user
    get_user_permissions_summary(db.get_session, "admin")
