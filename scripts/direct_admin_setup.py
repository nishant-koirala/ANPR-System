#!/usr/bin/env python3
"""
Direct Super Admin Setup - No Dependencies on Other Scripts
"""
import sys
import os
sys.path.insert(0, '.')

def create_admin_directly():
    """Create admin user directly without complex setup"""
    try:
        from src.db.database import get_database
        from src.db.rbac_models import Base, User, Role, Permission, UserRole, RolePermission, UserStatus
        from src.auth.auth_manager import Roles, Permissions
        import bcrypt
        from datetime import datetime
        
        print("🔐 Creating Super Admin Directly...")
        
        db = get_database()
        print("✅ Database connected")
        
        # Create tables
        Base.metadata.create_all(db.engine)
        print("✅ RBAC tables created")
        
        with db.get_session() as session:
            # Check if admin already exists
            existing_admin = session.query(User).filter(User.username == 'admin').first()
            if existing_admin:
                print("⚠️  Admin user already exists!")
                print(f"Username: {existing_admin.username}")
                print(f"Email: {existing_admin.email}")
                print("Password: admin123 (if not changed)")
                return True
            
            # Create SUPERADMIN role if it doesn't exist
            superadmin_role = session.query(Role).filter(Role.role_name == Roles.SUPERADMIN).first()
            if not superadmin_role:
                superadmin_role = Role(
                    role_name=Roles.SUPERADMIN,
                    description="Super Administrator with full system access",
                    is_system_role=True
                )
                session.add(superadmin_role)
                session.flush()  # Get the ID
                print("✅ SUPERADMIN role created")
            
            # Create essential permissions if they don't exist
            essential_permissions = [
                (Permissions.MANAGE_USERS, "Manage system users", "System"),
                (Permissions.MANAGE_ROLES, "Manage system roles", "System"),
                (Permissions.VIEW_DASHBOARD, "View main dashboard", "ANPR"),
                (Permissions.VIEW_DATABASE, "View database records", "Database")
            ]
            
            for perm_name, desc, category in essential_permissions:
                existing_perm = session.query(Permission).filter(Permission.permission_name == perm_name).first()
                if not existing_perm:
                    permission = Permission(
                        permission_name=perm_name,
                        description=desc,
                        category=category,
                        is_system_permission=True
                    )
                    session.add(permission)
                    session.flush()
                    
                    # Assign to SUPERADMIN role
                    role_perm = RolePermission(
                        role_id=superadmin_role.role_id,
                        permission_id=permission.permission_id
                    )
                    session.add(role_perm)
            
            print("✅ Essential permissions created and assigned")
            
            # Create admin user
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            admin_user = User(
                username="admin",
                password_hash=password_hash,
                email="admin@anpr.local",
                full_name="System Administrator",
                status=UserStatus.ACTIVE,
                created_at=datetime.utcnow()
            )
            session.add(admin_user)
            session.flush()  # Get the user ID
            
            # Assign SUPERADMIN role to admin user
            user_role = UserRole(
                user_id=admin_user.user_id,
                role_id=superadmin_role.role_id,
                assigned_at=datetime.utcnow()
            )
            session.add(user_role)
            
            session.commit()
            
            print("✅ Super Admin created successfully!")
            print("\n🎉 Setup Complete!")
            print("=" * 50)
            print("Super Admin Credentials:")
            print("Username: admin")
            print("Password: admin123")
            print("Email: admin@anpr.local")
            print("Role: SUPERADMIN")
            print("Status: ACTIVE")
            print("=" * 50)
            print("\n⚠️  SECURITY NOTICE:")
            print("Please change the default password after first login!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_admin_directly()
    if success:
        print("\n✅ You can now login to the ANPR system with the admin credentials!")
    else:
        print("\n❌ Failed to create super admin. Check the errors above.")
    
    input("\nPress Enter to exit...")  # Keep window open
