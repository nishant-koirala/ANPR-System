"""
Authentication and Authorization Manager for RBAC System
"""
import hashlib
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json

from ..db.rbac_models import User, Role, Permission, UserRole, RolePermission, UserSession, AuditLog, UserStatus

class AuthenticationError(Exception):
    """Authentication related errors"""
    pass

class AuthorizationError(Exception):
    """Authorization related errors"""
    pass

class AuthManager:
    """Centralized authentication and authorization manager"""
    
    def __init__(self, db_session_factory):
        self.get_session = db_session_factory
        self.current_user = None
        self.current_session = None
        
    # Authentication Methods
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def generate_session_id(self) -> str:
        """Generate secure session ID"""
        return secrets.token_urlsafe(64)
    
    def login(self, username: str, password: str, ip_address: str = None, user_agent: str = None) -> Dict:
        """
        Authenticate user and create session
        
        Returns:
            Dict with user info and session details
        """
        with self.get_session() as session:
            # Find user
            user = session.query(User).filter(
                User.username == username,
                User.status == UserStatus.ACTIVE
            ).first()
            
            if not user:
                self._log_audit(None, "LOGIN_FAILED", details=f"Username not found: {username}", 
                              ip_address=ip_address, success=False)
                raise AuthenticationError("Invalid username or password")
            
            # Check password
            if not self.verify_password(password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts += 1
                session.commit()
                
                self._log_audit(user.user_id, "LOGIN_FAILED", details="Invalid password", 
                              ip_address=ip_address, success=False)
                
                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.status = UserStatus.SUSPENDED
                    session.commit()
                    self._log_audit(user.user_id, "ACCOUNT_SUSPENDED", 
                                  details="Too many failed login attempts", ip_address=ip_address)
                
                raise AuthenticationError("Invalid username or password")
            
            # Check if account is suspended
            if user.status == UserStatus.SUSPENDED:
                self._log_audit(user.user_id, "LOGIN_DENIED", details="Account suspended", 
                              ip_address=ip_address, success=False)
                raise AuthenticationError("Account is suspended")
            
            # Create session
            session_id = self.generate_session_id()
            user_session = UserSession(
                session_id=session_id,
                user_id=user.user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.add(user_session)
            
            # Extract user data before session operations
            user_data = {
                'user_id': user.user_id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email,
                'session_id': session_id
            }
            
            # Update user login info
            user.last_login = datetime.utcnow()
            user.failed_login_attempts = 0
            session.commit()
            session.refresh(user)  # Refresh to keep object bound
            
            # Set current user and session
            self.current_user = user
            self.current_session = user_session
            
            # Log successful login
            self._log_audit(user_data['user_id'], "LOGIN_SUCCESS", ip_address=ip_address)
            
            # Get roles and permissions with fresh session
            user_data['roles'] = self.get_user_roles(user_data['user_id'])
            user_data['permissions'] = self.get_user_permissions(user_data['user_id'])
            
            return user_data
    
    def logout(self, session_id: str = None) -> bool:
        """Logout user and invalidate session"""
        if not session_id and self.current_session:
            session_id = self.current_session.session_id
        
        if not session_id:
            return False
        
        with self.get_session() as session:
            user_session = session.query(UserSession).filter(
                UserSession.session_id == session_id,
                UserSession.is_active == True
            ).first()
            
            if user_session:
                user_session.logout_time = datetime.utcnow()
                user_session.is_active = False
                session.commit()
                
                self._log_audit(user_session.user_id, "LOGOUT_SUCCESS")
                
                # Clear current user/session
                self.current_user = None
                self.current_session = None
                
                return True
        
        return False
    
    def validate_session(self, session_id: str) -> Optional[Dict]:
        """Validate session and return user info"""
        with self.get_session() as session:
            user_session = session.query(UserSession).join(User).filter(
                UserSession.session_id == session_id,
                UserSession.is_active == True,
                User.status == UserStatus.ACTIVE
            ).first()
            
            if user_session:
                # Check if session is not too old (24 hours)
                if datetime.utcnow() - user_session.login_time > timedelta(hours=24):
                    user_session.is_active = False
                    session.commit()
                    return None
                
                user = user_session.user
                self.current_user = user
                self.current_session = user_session
                
                return {
                    'user_id': user.user_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'email': user.email,
                    'roles': self.get_user_roles(user.user_id),
                    'permissions': self.get_user_permissions(user.user_id)
                }
        
        return None
    
    # Authorization Methods
    
    def get_user_roles(self, user_id: int) -> List[str]:
        """Get all roles assigned to a user"""
        with self.get_session() as session:
            roles = session.query(Role.role_name).join(UserRole).filter(
                UserRole.user_id == user_id,
                or_(UserRole.expires_at.is_(None), UserRole.expires_at > datetime.utcnow())
            ).all()
            
            return [role[0] for role in roles]
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user through their roles"""
        with self.get_session() as session:
            permissions = session.query(Permission.permission_name).join(
                RolePermission
            ).join(Role).join(UserRole).filter(
                UserRole.user_id == user_id,
                or_(UserRole.expires_at.is_(None), UserRole.expires_at > datetime.utcnow())
            ).distinct().all()
            
            return [perm[0] for perm in permissions]
    
    def has_permission(self, user_id: int, permission_name: str) -> bool:
        """Check if user has specific permission"""
        permissions = self.get_user_permissions(user_id)
        return permission_name in permissions
    
    def has_role(self, user_id: int, role_name: str) -> bool:
        """Check if user has specific role"""
        roles = self.get_user_roles(user_id)
        return role_name in roles
    
    def require_permission(self, permission_name: str):
        """Decorator/method to require specific permission"""
        if not self.current_user:
            raise AuthorizationError("Not authenticated")
        
        if not self.has_permission(self.current_user.user_id, permission_name):
            self._log_audit(self.current_user.user_id, "ACCESS_DENIED", 
                          details=f"Missing permission: {permission_name}", success=False)
            raise AuthorizationError(f"Permission denied: {permission_name}")
    
    def require_role(self, role_name: str):
        """Decorator/method to require specific role"""
        if not self.current_user:
            raise AuthorizationError("Not authenticated")
        
        if not self.has_role(self.current_user.user_id, role_name):
            self._log_audit(self.current_user.user_id, "ACCESS_DENIED", 
                          details=f"Missing role: {role_name}", success=False)
            raise AuthorizationError(f"Role required: {role_name}")
    
    # User Management Methods
    
    def create_user(self, username: str, password: str, email: str, full_name: str = None, 
                   roles: List[str] = None, status: str = "ACTIVE") -> int:
        """Create new user with optional roles and status"""
        # Skip permission check if no current user (initial setup)
        if self.current_user:
            self.require_permission("MANAGE_USERS")
        
        with self.get_session() as session:
            # Check if username/email already exists
            existing = session.query(User).filter(
                or_(User.username == username, User.email == email)
            ).first()
            
            if existing:
                raise ValueError("Username or email already exists")
            
            # Convert status string to enum
            from ..db.rbac_models import UserStatus
            try:
                user_status = UserStatus(status)
            except ValueError:
                user_status = UserStatus.ACTIVE  # Default fallback
            
            # Create new user
            password_hash = self.hash_password(password)
            new_user = User(
                username=username,
                password_hash=password_hash,
                email=email,
                full_name=full_name,
                status=user_status,
                created_by=self.current_user.user_id if self.current_user else None
            )
            session.add(new_user)
            session.flush()
            
            # Assign roles
            if roles:
                for role_name in roles:
                    role = session.query(Role).filter(Role.role_name == role_name).first()
                    if role:
                        user_role = UserRole(
                            user_id=user.user_id,
                            role_id=role.role_id,
                            assigned_by=self.current_user.user_id if self.current_user else None
                        )
                        session.add(user_role)
            
            session.commit()
            
            self._log_audit(self.current_user.user_id if self.current_user else None, 
                          "CREATE_USER", "USER", str(user.user_id), 
                          details=f"Created user: {username}")
            
            return user.user_id
    
    def _log_audit(self, user_id: int, action: str, resource_type: str = None, 
                  resource_id: str = None, details: str = None, ip_address: str = None, 
                  success: bool = True):
        """Log audit trail"""
        with self.get_session() as session:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                success=success
            )
            session.add(audit_log)
            session.commit()

# Permission Constants
class Permissions:
    """Centralized permission definitions"""
    
    # System Administration
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_ROLES = "MANAGE_ROLES"
    MANAGE_PERMISSIONS = "MANAGE_PERMISSIONS"
    VIEW_AUDIT_LOGS = "VIEW_AUDIT_LOGS"
    SYSTEM_CONFIG = "SYSTEM_CONFIG"
    
    # ANPR Operations
    VIEW_DASHBOARD = "VIEW_DASHBOARD"
    VIEW_VEHICLE_LOGS = "VIEW_VEHICLE_LOGS"
    DELETE_VEHICLE_LOGS = "DELETE_VEHICLE_LOGS"
    EXPORT_DATA = "EXPORT_DATA"
    
    # Camera Management
    CONFIG_CAMERAS = "CONFIG_CAMERAS"
    VIEW_CAMERA_STATUS = "VIEW_CAMERA_STATUS"
    
    # Database Operations
    VIEW_DATABASE = "VIEW_DATABASE"
    MANAGE_DATABASE = "MANAGE_DATABASE"
    BACKUP_DATABASE = "BACKUP_DATABASE"
    
    # Settings
    MODIFY_SETTINGS = "MODIFY_SETTINGS"
    VIEW_SETTINGS = "VIEW_SETTINGS"

# Role Constants
class Roles:
    """Centralized role definitions"""
    
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"
