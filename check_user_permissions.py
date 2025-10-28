"""
Check permissions for user 'nish'
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import get_database
from src.auth.auth_manager import AuthManager

print("Checking user 'nish' permissions...")

db = get_database()
auth = AuthManager(db.get_session)

# Get user info
with db.get_session() as session:
    from src.db.rbac_models import User
    user = session.query(User).filter(User.username == 'nish').first()
    
    if not user:
        print("❌ User 'nish' not found!")
    else:
        print(f"\n✓ User found:")
        print(f"  User ID: {user.user_id}")
        print(f"  Username: {user.username}")
        print(f"  Full Name: {user.full_name}")
        print(f"  Email: {user.email}")
        print(f"  Status: {user.status}")
        
        # Get roles
        roles = auth.get_user_roles(user.user_id)
        print(f"\n✓ Roles ({len(roles)}):")
        for role in roles:
            print(f"  • {role}")
        
        # Get permissions
        perms = auth.get_user_permissions(user.user_id)
        print(f"\n✓ Permissions ({len(perms)}):")
        for perm in sorted(perms):
            print(f"  • {perm}")
        
        # Check specific permissions
        print(f"\n✓ Permission Checks:")
        print(f"  MANAGE_USERS: {auth.has_permission(user.user_id, 'MANAGE_USERS')}")
        print(f"  MANAGE_DATABASE: {auth.has_permission(user.user_id, 'MANAGE_DATABASE')}")
        print(f"  VIEW_DASHBOARD: {auth.has_permission(user.user_id, 'VIEW_DASHBOARD')}")
        print(f"  EXPORT_DATA: {auth.has_permission(user.user_id, 'EXPORT_DATA')}")
        
        if not auth.has_permission(user.user_id, 'MANAGE_USERS'):
            print(f"\n❌ User 'nish' does NOT have MANAGE_USERS permission!")
            print(f"   This is why User Management doesn't appear in sidebar.")
            print(f"\n   Current role(s): {', '.join(roles) if roles else 'NONE'}")
            print(f"   Need role: ADMIN or SUPERADMIN")
            
            print(f"\n💡 To fix this, you need to:")
            print(f"   1. Login as admin (username: admin, password: admin123)")
            print(f"   2. Go to User Management")
            print(f"   3. Edit user 'nish'")
            print(f"   4. Assign role: ADMIN or SUPERADMIN")
        else:
            print(f"\n✓ User 'nish' has MANAGE_USERS permission!")
