#!/usr/bin/env python3
"""
Create Super Admin User for ANPR RBAC System
"""
import sys
import os
sys.path.insert(0, '.')

def create_superadmin():
    """Create a super admin user"""
    try:
        from src.db.database import get_database
        from src.db.rbac_models import Base, User, Role, UserRole, UserStatus
        from src.auth.auth_manager import AuthManager, Roles
        
        print("🔐 Creating Super Admin User...")
        
        # Get database connection
        db = get_database()
        print("✅ Database connected")
        
        # Create RBAC tables if they don't exist
        Base.metadata.create_all(db.engine)
        print("✅ RBAC tables ready")
        
        # Get user input
        username = input("Enter username (default: admin): ").strip() or "admin"
        password = input("Enter password (default: admin123): ").strip() or "admin123"
        email = input("Enter email (default: admin@anpr.local): ").strip() or "admin@anpr.local"
        full_name = input("Enter full name (default: System Administrator): ").strip() or "System Administrator"
        
        with db.get_session() as session:
            # Check if user already exists
            existing_user = session.query(User).filter(User.username == username).first()
            if existing_user:
                print(f"⚠️  User '{username}' already exists!")
                
                # Ask if they want to make existing user a superadmin
                choice = input("Make this user a SUPERADMIN? (y/n): ").lower()
                if choice == 'y':
                    # Find SUPERADMIN role
                    superadmin_role = session.query(Role).filter(Role.role_name == Roles.SUPERADMIN).first()
                    if not superadmin_role:
                        # Create SUPERADMIN role
                        from src.db.rbac_setup import initialize_rbac_system
                        initialize_rbac_system(db.get_session, username, password)
                        superadmin_role = session.query(Role).filter(Role.role_name == Roles.SUPERADMIN).first()
                    
                    # Check if user already has SUPERADMIN role
                    existing_role = session.query(UserRole).filter(
                        UserRole.user_id == existing_user.user_id,
                        UserRole.role_id == superadmin_role.role_id
                    ).first()
                    
                    if not existing_role:
                        # Assign SUPERADMIN role
                        user_role = UserRole(
                            user_id=existing_user.user_id,
                            role_id=superadmin_role.role_id
                        )
                        session.add(user_role)
                        session.commit()
                        print(f"✅ User '{username}' is now a SUPERADMIN!")
                    else:
                        print(f"✅ User '{username}' already has SUPERADMIN role!")
                
                return
            
            # Initialize RBAC system first (creates roles and permissions)
            from src.db.rbac_setup import initialize_rbac_system
            initialize_rbac_system(db.get_session, username, password)
            
            print(f"✅ Super Admin created successfully!")
            print(f"📝 Username: {username}")
            print(f"🔑 Password: {password}")
            print(f"📧 Email: {email}")
            print(f"🎭 Role: SUPERADMIN")
            print(f"🔐 Full system access granted")
            
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_superadmin()
