#!/usr/bin/env python3
"""
Unified Database Initialization Script for ANPR System
Handles both RBAC system and ANPR core functionality with corrected model structure
"""

import sys
import os
import sqlite3
from datetime import datetime
import bcrypt

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def create_unified_database():
    """Create unified database with both RBAC and ANPR models"""
    print("🔄 Creating Unified ANPR Database")
    print("=" * 40)
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'anpr_database.db')
    database_url = f"sqlite:///{os.path.abspath(db_path)}"
    
    try:
        # Create engine
        engine = create_engine(database_url, echo=False)
        
        # Import all models to ensure they're registered
        from src.db.rbac_models import Base, User, Role, Permission, RolePermission, UserRole, UserSession, AuditLog, UserStatus
        from src.db.models import Camera, Vehicle, RawLog, VehicleLog, PlateEditHistory, ToggleMode
        
        print("📋 Creating all database tables...")
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("✅ Database tables created successfully")
        
        # Create session for data initialization
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Initialize RBAC system
            initialize_rbac_data(session)
            
            # Initialize sample ANPR data
            initialize_sample_anpr_data(session)
            
            session.commit()
            print("💾 All data committed successfully")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Data initialization failed: {e}")
            raise
        finally:
            session.close()
            
        print(f"✅ Unified database created at: {db_path}")
        
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        raise

def initialize_rbac_data(session):
    """Initialize RBAC system with default roles, permissions, and admin user"""
    from src.db.rbac_models import User, Role, Permission, RolePermission, UserRole, UserStatus
    from src.auth.auth_manager import Permissions, Roles
    
    print("1️⃣ Initializing RBAC system...")
    
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
        (Roles.SUPERADMIN, "Full system access", [
            Permissions.MANAGE_USERS, Permissions.MANAGE_ROLES, Permissions.MANAGE_PERMISSIONS,
            Permissions.VIEW_AUDIT_LOGS, Permissions.SYSTEM_CONFIG, Permissions.VIEW_DASHBOARD,
            Permissions.VIEW_VEHICLE_LOGS, Permissions.DELETE_VEHICLE_LOGS, Permissions.EXPORT_DATA,
            Permissions.CONFIG_CAMERAS, Permissions.VIEW_CAMERA_STATUS, Permissions.VIEW_DATABASE,
            Permissions.MANAGE_DATABASE, Permissions.BACKUP_DATABASE, Permissions.MODIFY_SETTINGS,
            Permissions.VIEW_SETTINGS
        ]),
        (Roles.ADMIN, "Administrative access", [
            Permissions.MANAGE_USERS, Permissions.VIEW_AUDIT_LOGS, Permissions.VIEW_DASHBOARD,
            Permissions.VIEW_VEHICLE_LOGS, Permissions.DELETE_VEHICLE_LOGS, Permissions.EXPORT_DATA,
            Permissions.CONFIG_CAMERAS, Permissions.VIEW_CAMERA_STATUS, Permissions.VIEW_DATABASE,
            Permissions.BACKUP_DATABASE, Permissions.MODIFY_SETTINGS, Permissions.VIEW_SETTINGS
        ]),
        (Roles.OPERATOR, "Operational access", [
            Permissions.VIEW_DASHBOARD, Permissions.VIEW_VEHICLE_LOGS, Permissions.EXPORT_DATA,
            Permissions.VIEW_CAMERA_STATUS, Permissions.VIEW_DATABASE, Permissions.VIEW_SETTINGS
        ]),
        (Roles.VIEWER, "Read-only access", [
            Permissions.VIEW_DASHBOARD, Permissions.VIEW_VEHICLE_LOGS, Permissions.VIEW_CAMERA_STATUS,
            Permissions.VIEW_DATABASE, Permissions.VIEW_SETTINGS
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
    existing_admin = session.query(User).filter(User.username == "admin").first()
    if not existing_admin:
        # Hash password using bcrypt
        password = "admin123"
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        admin_user = User(
            username="admin",
            password_hash=password_hash,
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
    
    print("   ✅ RBAC system initialized")

def initialize_sample_anpr_data(session):
    """Initialize sample ANPR data for testing"""
    from src.db.models import Camera, Vehicle
    
    print("2️⃣ Initializing sample ANPR data...")
    
    # Create sample cameras
    cameras_data = [
        ("Main Gate Camera", "Main Entrance Gate"),
        ("Exit Gate Camera", "Exit Gate"),
        ("Parking Lot Camera", "Parking Area")
    ]
    
    for camera_name, location in cameras_data:
        existing = session.query(Camera).filter(Camera.camera_name == camera_name).first()
        if not existing:
            camera = Camera(
                camera_name=camera_name,
                location=location,
                is_active=1
            )
            session.add(camera)
    
    # Create sample vehicles
    vehicles_data = [
        ("BA-1-PA-1234", "car"),
        ("BA-2-CHA-5678", "motorcycle"),
        ("BA-3-KHA-9012", "truck")
    ]
    
    for plate_number, vehicle_type in vehicles_data:
        existing = session.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
        if not existing:
            vehicle = Vehicle(
                plate_number=plate_number,
                vehicle_type=vehicle_type,
                is_blacklisted=0
            )
            session.add(vehicle)
    
    print("   ✅ Sample ANPR data initialized")

if __name__ == "__main__":
    try:
        create_unified_database()
        print("\n" + "="*50)
        print("🎉 UNIFIED DATABASE CREATION COMPLETED SUCCESSFULLY!")
        print("="*50)
        print("📝 Default admin user: admin / admin123")
        print("🔐 Please change the default password after first login!")
        print("📊 Sample cameras and vehicles have been created")
        print("🚀 System is ready for use!")
    except Exception as e:
        print(f"\n❌ UNIFIED DATABASE CREATION FAILED: {e}")
        sys.exit(1)
