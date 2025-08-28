#!/usr/bin/env python3
"""
Initialize RBAC System for ANPR Application
"""
import sys
import os
sys.path.insert(0, '.')

from src.db.database import get_database
from src.db.rbac_models import Base
from src.db.rbac_setup import initialize_rbac_system, create_sample_users, get_user_permissions_summary

def main():
    """Initialize the RBAC system"""
    print("🔐 Initializing RBAC System for ANPR Application")
    print("=" * 50)
    
    try:
        # Get database instance
        db = get_database()
        print("✅ Database connection established")
        
        # Create RBAC tables
        print("📊 Creating RBAC database tables...")
        Base.metadata.create_all(db.engine)
        print("✅ RBAC tables created successfully")
        
        # Initialize RBAC system with default data
        print("🚀 Setting up default roles, permissions, and admin user...")
        initialize_rbac_system(db.get_session)
        
        # Create sample users for testing
        print("\n👥 Creating sample users...")
        create_sample_users(db.get_session)
        
        print("\n" + "=" * 50)
        print("🎉 RBAC System initialized successfully!")
        print("\n📋 Default Users Created:")
        print("  • admin / admin123 (SUPERADMIN)")
        print("  • john_operator / operator123 (OPERATOR)")
        print("  • jane_viewer / viewer123 (VIEWER)")
        print("  • mike_admin / admin123 (ADMIN)")
        
        print("\n🔑 Default Roles & Permissions:")
        print("  • SUPERADMIN: Full system access")
        print("  • ADMIN: Administrative access (no system management)")
        print("  • OPERATOR: Operational access (view, export)")
        print("  • VIEWER: Read-only access")
        
        print("\n⚠️  SECURITY NOTICE:")
        print("  Please change default passwords after first login!")
        
        # Show detailed permissions for admin
        print("\n" + "=" * 50)
        get_user_permissions_summary(db.get_session, "admin")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing RBAC system: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
