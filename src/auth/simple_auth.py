"""
Simple Authentication Manager for ANPR System
Works with basic user table without complex RBAC
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session

class SimpleAuthManager:
    """Simplified authentication manager for basic user management"""
    
    def __init__(self, db_session_factory):
        self.get_session = db_session_factory
        self.current_user = None
        self.sessions = {}  # Simple in-memory session storage
        
    def hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    def generate_session_id(self) -> str:
        """Generate secure session ID"""
        return secrets.token_urlsafe(32)
    
    def login(self, username: str, password: str) -> Dict:
        """
        Authenticate user and create session
        
        Returns:
            dict: User data with session info if successful
            None: If authentication failed
        """
        try:
            from ..db.models import User
            
            with self.get_session() as session:
                user = session.query(User).filter(
                    User.username == username
                ).first()
                
                if not user:
                    return None
                
                if not self.verify_password(password, user.password_hash):
                    return None
                
                # Update last login
                user.last_login = datetime.utcnow()
                session.commit()
                
                # Create session
                session_id = self.generate_session_id()
                session_data = {
                    'user_id': user.user_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'email': user.email,
                    'session_id': session_id,
                    'login_time': datetime.utcnow(),
                    'is_admin': user.username == 'admin'  # Simple admin check
                }
                
                self.sessions[session_id] = session_data
                self.current_user = user
                
                return session_data
                
        except Exception as e:
            print(f"Login error: {e}")
            return None
    
    def logout(self, session_id: str = None):
        """Logout user and invalidate session"""
        if session_id and session_id in self.sessions:
            del self.sessions[session_id]
        self.current_user = None
    
    def get_current_user(self, session_id: str = None) -> Optional[Dict]:
        """Get current user data from session"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return None
    
    def is_authenticated(self, session_id: str = None) -> bool:
        """Check if user is authenticated"""
        return session_id and session_id in self.sessions
    
    def is_admin(self, session_id: str = None) -> bool:
        """Check if user has admin privileges"""
        user_data = self.get_current_user(session_id)
        return user_data and user_data.get('is_admin', False)
    
    def can_edit_plates(self, session_id: str = None) -> bool:
        """Check if user can edit plate data"""
        # For now, only admin can edit plates
        return self.is_admin(session_id)
    
    def create_user(self, username: str, password: str, email: str, full_name: str = None) -> bool:
        """Create new user (admin only)"""
        try:
            from ..db.models import User
            
            with self.get_session() as session:
                # Check if user already exists
                existing = session.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first()
                
                if existing:
                    return False
                
                # Create new user
                new_user = User(
                    username=username,
                    email=email,
                    password_hash=self.hash_password(password),
                    full_name=full_name,
                    created_at=datetime.utcnow()
                )
                
                session.add(new_user)
                session.commit()
                return True
                
        except Exception as e:
            print(f"Create user error: {e}")
            return False
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            from ..db.models import User
            
            with self.get_session() as session:
                user = session.query(User).filter(User.username == username).first()
                
                if not user or not self.verify_password(old_password, user.password_hash):
                    return False
                
                user.password_hash = self.hash_password(new_password)
                session.commit()
                return True
                
        except Exception as e:
            print(f"Change password error: {e}")
            return False
