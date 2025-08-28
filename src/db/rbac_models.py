"""
Role-Based Access Control (RBAC) Database Models
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class User(Base):
    """System users table"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", foreign_keys="UserRole.user_id")
    created_users = relationship("User", remote_side=[user_id], foreign_keys="User.created_by")
    
    # ANPR-related relationships (imported from models.py)
    edited_logs = relationship("VehicleLog", back_populates="editor", foreign_keys="VehicleLog.edited_by")
    edit_history = relationship("PlateEditHistory", back_populates="editor")
    
    def __repr__(self):
        return f"<User(username='{self.username}', status='{self.status.value}')>"

class Role(Base):
    """System roles table"""
    __tablename__ = 'roles'
    
    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200), nullable=True)
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted if True
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Role(role_name='{self.role_name}')>"

class Permission(Base):
    """System permissions table"""
    __tablename__ = 'permissions'
    
    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    permission_name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(200), nullable=True)
    category = Column(String(50), nullable=True)  # Group related permissions
    is_system_permission = Column(Boolean, default=False)  # Cannot be deleted if True
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Permission(permission_name='{self.permission_name}')>"

class RolePermission(Base):
    """Role-Permission mapping table"""
    __tablename__ = 'role_permissions'
    
    rp_id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey('roles.role_id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permissions.permission_id', ondelete='CASCADE'), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    granter = relationship("User", foreign_keys=[granted_by])
    
    def __repr__(self):
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"

class UserRole(Base):
    """User-Role mapping table"""
    __tablename__ = 'user_roles'
    
    ur_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.role_id', ondelete='CASCADE'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional role expiration
    
    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"

class UserSession(Base):
    """Track user login sessions"""
    __tablename__ = 'user_sessions'
    
    session_id = Column(String(128), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    login_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    logout_time = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, active={self.is_active})>"

class AuditLog(Base):
    """Audit trail for security-sensitive operations"""
    __tablename__ = 'audit_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True)
    action = Column(String(100), nullable=False)  # LOGIN, LOGOUT, CREATE_USER, etc.
    resource_type = Column(String(50), nullable=True)  # USER, ROLE, PERMISSION, etc.
    resource_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)  # JSON details
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user_id={self.user_id})>"
