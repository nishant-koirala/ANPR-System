"""
Verify RBAC Database Setup
This script checks if the RBAC system is properly configured in the database
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import get_database
from src.db.rbac_models import User, Role, Permission, UserRole, RolePermission
from src.auth.auth_manager import AuthManager, Roles, Permissions as PermConsts

def verify_rbac_setup():
    """Verify RBAC database setup"""
    print("=" * 60)
    print("RBAC Database Verification")
    print("=" * 60)
    
    db = get_database()
    
    with db.get_session() as session:
        # Check roles
        print("\n📋 ROLES:")
        print("-" * 60)
        roles = session.query(Role).all()
        for role in roles:
            print(f"  ✓ {role.role_name}: {role.description}")
        
        if len(roles) < 4:
            print("  ⚠️  WARNING: Expected 4 roles (SUPERADMIN, ADMIN, OPERATOR, VIEWER)")
        
        # Check permissions
        print("\n🔐 PERMISSIONS:")
        print("-" * 60)
        permissions = session.query(Permission).all()
        for perm in permissions:
            print(f"  ✓ {perm.permission_name}: {perm.description}")
        
        # Check role-permission mappings
        print("\n🔗 ROLE-PERMISSION MAPPINGS:")
        print("-" * 60)
        for role in roles:
            role_perms = session.query(Permission).join(
                RolePermission, RolePermission.permission_id == Permission.permission_id
            ).filter(RolePermission.role_id == role.role_id).all()
            
            print(f"\n  {role.role_name} ({len(role_perms)} permissions):")
            for perm in role_perms:
                print(f"    • {perm.permission_name}")
            
            # Check critical permissions
            perm_names = [p.permission_name for p in role_perms]
            
            if role.role_name == Roles.SUPERADMIN:
                if PermConsts.MANAGE_USERS not in perm_names:
                    print(f"    ❌ MISSING: {PermConsts.MANAGE_USERS}")
                if PermConsts.MANAGE_ROLES not in perm_names:
                    print(f"    ❌ MISSING: {PermConsts.MANAGE_ROLES}")
            
            elif role.role_name == Roles.ADMIN:
                if PermConsts.MANAGE_USERS not in perm_names:
                    print(f"    ❌ MISSING: {PermConsts.MANAGE_USERS}")
                if PermConsts.MANAGE_DATABASE not in perm_names:
                    print(f"    ❌ MISSING: {PermConsts.MANAGE_DATABASE}")
            
            elif role.role_name == Roles.OPERATOR:
                if PermConsts.EXPORT_DATA not in perm_names:
                    print(f"    ❌ MISSING: {PermConsts.EXPORT_DATA}")
        
        # Check users
        print("\n👥 USERS:")
        print("-" * 60)
        users = session.query(User).all()
        for user in users:
            user_roles = session.query(Role).join(
                UserRole, UserRole.role_id == Role.role_id
            ).filter(UserRole.user_id == user.user_id).all()
            
            role_names = [r.role_name for r in user_roles]
            print(f"  ✓ {user.username} ({user.email})")
            print(f"    Status: {user.status.value if hasattr(user.status, 'value') else user.status}")
            print(f"    Roles: {', '.join(role_names) if role_names else 'NONE'}")
            
            if not role_names:
                print(f"    ⚠️  WARNING: User has no roles assigned!")
        
        # Test admin user login
        print("\n🔑 TESTING ADMIN LOGIN:")
        print("-" * 60)
        auth_manager = AuthManager(db.get_session)
        
        try:
            # Try to login with default admin credentials
            user_data = auth_manager.login("admin", "admin123")
            print(f"  ✓ Login successful: {user_data['username']}")
            
            # Check permissions
            user_id = user_data['user_id']
            user_roles = auth_manager.get_user_roles(user_id)
            user_perms = auth_manager.get_user_permissions(user_id)
            
            print(f"  ✓ Roles: {', '.join(user_roles)}")
            print(f"  ✓ Permissions: {len(user_perms)} total")
            
            # Check critical permissions
            critical_perms = [
                PermConsts.MANAGE_USERS,
                PermConsts.VIEW_DASHBOARD,
                PermConsts.VIEW_VEHICLE_LOGS,
                PermConsts.EXPORT_DATA,
                PermConsts.MANAGE_DATABASE
            ]
            
            print("\n  Critical Permissions Check:")
            for perm in critical_perms:
                has_perm = auth_manager.has_permission(user_id, perm)
                status = "✓" if has_perm else "❌"
                print(f"    {status} {perm}")
            
            # Test RBAC UI Controller
            print("\n  RBAC UI Controller Check:")
            from src.ui.rbac_ui_controller import RBACUIController
            rbac = RBACUIController(auth_manager)
            
            print(f"    • can_manage_users: {rbac.can_manage_users()}")
            print(f"    • can_edit_plates: {rbac.can_edit_plates()}")
            print(f"    • can_export_data: {rbac.can_export_data()}")
            print(f"    • can_modify_settings: {rbac.can_modify_settings()}")
            print(f"    • is_superadmin: {rbac.is_superadmin()}")
            print(f"    • Role display: {rbac.get_role_display_name()}")
            
            if not rbac.can_manage_users():
                print("\n    ❌ ERROR: SuperAdmin cannot manage users!")
                print("    This will prevent User Management from showing in sidebar.")
            
            auth_manager.logout()
            
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)

if __name__ == "__main__":
    verify_rbac_setup()
