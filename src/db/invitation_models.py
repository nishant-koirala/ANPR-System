"""
Database models for user invitation system with OTP verification
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime, timedelta
from .rbac_models import Base
import secrets
import string
import hashlib


class UserInvitation(Base):
    """User invitation with OTP for secure registration"""
    __tablename__ = 'user_invitations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of OTP
    role = Column(String(50), nullable=False)  # admin, operator, viewer
    
    # Status tracking
    status = Column(String(20), default='pending', index=True)  # pending, completed, expired, revoked
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    
    # Audit
    invited_by = Column(Integer)  # User ID who sent the invitation
    completed_by_username = Column(String(50))  # Username created during registration
    
    def __repr__(self):
        return f"<UserInvitation(email='{self.email}', role='{self.role}', status='{self.status}')>"
    
    def is_valid(self):
        """Check if invitation is still valid"""
        return (
            self.status == 'pending' and
            datetime.utcnow() < self.expires_at
        )
    
    def is_expired(self):
        """Check if invitation has expired"""
        return datetime.utcnow() >= self.expires_at
    
    @staticmethod
    def generate_otp(length=6):
        """Generate a random numeric OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def hash_otp(otp):
        """Hash OTP using SHA-256"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    def verify_otp(self, otp):
        """Verify OTP against stored hash"""
        return self.otp_hash == self.hash_otp(otp)
    
    @staticmethod
    def get_expiry_time(hours=48):
        """Get expiry timestamp (default 48 hours from now)"""
        return datetime.utcnow() + timedelta(hours=hours)
    
    @staticmethod
    def get_expiry_time_minutes(minutes=5):
        """Get expiry timestamp in minutes (default 5 minutes from now)"""
        return datetime.utcnow() + timedelta(minutes=minutes)


class PasswordResetToken(Base):
    """Password reset tokens for existing users"""
    __tablename__ = 'password_reset_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    token = Column(String(100), nullable=False, unique=True, index=True)
    
    # Status
    status = Column(String(20), default='pending', index=True)  # pending, used, expired
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)
    
    def __repr__(self):
        return f"<PasswordResetToken(username='{self.username}', status='{self.status}')>"
    
    def is_valid(self):
        """Check if token is still valid"""
        return (
            self.status == 'pending' and
            datetime.utcnow() < self.expires_at
        )
    
    def is_expired(self):
        """Check if token has expired"""
        return datetime.utcnow() >= self.expires_at
    
    @staticmethod
    def generate_token(length=32):
        """Generate a secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def get_expiry_time(hours=24):
        """Get expiry timestamp (default 24 hours from now)"""
        return datetime.utcnow() + timedelta(hours=hours)
