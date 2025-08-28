#!/usr/bin/env python3
"""
Quick Super Admin Setup for ANPR RBAC System
"""
import sys
import os
sys.path.insert(0, '.')

def setup_admin():
    """Setup super admin with default credentials"""
    try:
        from src.db.database import get_database
        from src.db.rbac_models import Base
        from src.db.rbac_setup import initialize_rbac_system, create_sample_users
        
        print("🔐 Setting up RBAC System and Super Admin...")
        
        # Get database connection
        db = get_database()
        print("✅ Database connected")
        
        # Create RBAC tables
        Base.metadata.create_all(db.engine)
        print("✅ RBAC tables created")
        
        # Initialize RBAC system with default admin
        initialize_rbac_system(db.get_session)
        print("✅ RBAC system initialized")
        
        # Create sample users including admin
        create_sample_users(db.get_session)
        print("✅ Sample users created")
        
        print("\n🎉 Super Admin Setup Complete!")
        print("=" * 40)
        print("Default Super Admin Credentials:")
        print("Username: admin")
        print("Password: admin123")
        print("Role: SUPERADMIN")
        print("Access: Full system control")
        print("=" * 40)
        print("\n⚠️  IMPORTANT: Change the default password after first login!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_admin()
    if success:
        print("\n✅ You can now login with username 'admin' and password 'admin123'")
    else:
        print("\n❌ Setup failed. Check the error messages above.")
