"""
Database operations for user invitation system
"""

from typing import Optional, List
from datetime import datetime
from .invitation_models import UserInvitation, PasswordResetToken


class InvitationDB:
    """Database operations for user invitations and password resets"""
    
    def __init__(self, session_factory):
        """
        Initialize invitation database manager
        
        Args:
            session_factory: SQLAlchemy session factory
        """
        self.session_factory = session_factory
    
    # ==================== USER INVITATIONS ====================
    
    def create_invitation(self, email: str, role: str, invited_by: int = None,
                         expiry_minutes: int = 5) -> Optional[UserInvitation]:
        """
        Create a new user invitation with OTP
        
        Args:
            email: User's email address
            role: User role (admin, operator, viewer)
            invited_by: User ID of admin who sent invitation
            expiry_minutes: Minutes until invitation expires (default 5)
            
        Returns:
            UserInvitation object or None if error
        """
        with self.session_factory() as session:
            try:
                # Check if there's already a pending invitation for this email
                existing = session.query(UserInvitation).filter_by(
                    email=email,
                    status='pending'
                ).first()
                
                if existing and existing.is_valid():
                    print(f"Active invitation already exists for {email}")
                    return None
                
                # Generate unique OTP
                otp = UserInvitation.generate_otp()
                otp_hash = UserInvitation.hash_otp(otp)
                
                # Ensure OTP hash is unique
                while session.query(UserInvitation).filter_by(otp_hash=otp_hash, status='pending').first():
                    otp = UserInvitation.generate_otp()
                    otp_hash = UserInvitation.hash_otp(otp)
                
                # Create invitation with hashed OTP
                invitation = UserInvitation(
                    email=email,
                    otp_hash=otp_hash,
                    role=role,
                    invited_by=invited_by,
                    expires_at=UserInvitation.get_expiry_time_minutes(expiry_minutes)
                )
                
                session.add(invitation)
                session.commit()
                session.refresh(invitation)
                
                # Store plain OTP temporarily for email sending
                invitation._plain_otp = otp
                
                session.expunge(invitation)
                
                print(f"✅ Created invitation for {email} (OTP hashed)")
                return invitation
                
            except Exception as e:
                print(f"Error creating invitation: {e}")
                session.rollback()
                return None
    
    def verify_otp(self, email: str, otp: str) -> Optional[UserInvitation]:
        """
        Verify OTP and email combination using hash comparison
        Marks invitation as 'verified' to prevent reuse
        
        Args:
            email: User's email address
            otp: One-time password (plain text)
            
        Returns:
            UserInvitation object if valid, None otherwise
        """
        with self.session_factory() as session:
            # Get all pending invitations for this email
            invitations = session.query(UserInvitation).filter_by(
                email=email,
                status='pending'
            ).all()
            
            # Hash the provided OTP
            otp_hash = UserInvitation.hash_otp(otp)
            
            # Find matching invitation by hash
            for invitation in invitations:
                if invitation.otp_hash == otp_hash:
                    # Check if expired
                    if invitation.is_expired():
                        invitation.status = 'expired'
                        session.commit()
                        print(f"Invitation for {email} has expired")
                        return None
                    
                    # Access all attributes BEFORE expunging to avoid DetachedInstanceError
                    invitation_id = invitation.id
                    invitation_email = invitation.email
                    invitation_role = invitation.role
                    invitation_status = invitation.status
                    invitation_created_at = invitation.created_at
                    invitation_expires_at = invitation.expires_at
                    invitation_otp_hash = invitation.otp_hash
                    
                    # Mark as 'verified' to prevent reuse
                    invitation.status = 'verified'
                    session.commit()
                    
                    # Refresh to get updated status
                    session.refresh(invitation)
                    
                    # Now expunge (detach from session)
                    session.expunge(invitation)
                    print(f"✅ OTP verified for {email} (marked as verified)")
                    return invitation
            
            print(f"❌ Invalid OTP for {email}")
            return None
    
    def complete_invitation(self, email: str, otp: str, username: str) -> bool:
        """
        Mark invitation as completed after successful registration
        Works with 'verified' status (set after OTP verification)
        
        Args:
            email: User's email address
            otp: One-time password (plain text)
            username: Username created during registration
            
        Returns:
            True if successful, False otherwise
        """
        with self.session_factory() as session:
            # Get invitations with 'verified' status (OTP already verified)
            invitations = session.query(UserInvitation).filter_by(
                email=email,
                status='verified'
            ).all()
            
            # Hash the provided OTP
            otp_hash = UserInvitation.hash_otp(otp)
            
            # Find matching invitation by hash
            for invitation in invitations:
                if invitation.otp_hash == otp_hash:
                    invitation.status = 'completed'
                    invitation.completed_at = datetime.utcnow()
                    invitation.completed_by_username = username
                    session.commit()
                    print(f"✅ Completed invitation for {email} -> {username}")
                    return True
            
            print(f"⚠️ No verified invitation found for {email}")
            return False
    
    def revoke_invitation(self, invitation_id: int) -> bool:
        """
        Revoke a pending invitation
        
        Args:
            invitation_id: Invitation ID
            
        Returns:
            True if successful, False otherwise
        """
        with self.session_factory() as session:
            invitation = session.query(UserInvitation).filter_by(id=invitation_id).first()
            
            if invitation and invitation.status == 'pending':
                invitation.status = 'revoked'
                session.commit()
                print(f"Revoked invitation for {invitation.email}")
                return True
            
            return False
    
    def get_pending_invitations(self) -> List[UserInvitation]:
        """
        Get all pending invitations
        
        Returns:
            List of pending UserInvitation objects
        """
        with self.session_factory() as session:
            invitations = session.query(UserInvitation).filter_by(
                status='pending'
            ).order_by(UserInvitation.created_at.desc()).all()
            
            # Expunge all to make accessible outside session
            for inv in invitations:
                session.expunge(inv)
            
            return invitations
    
    def get_all_invitations(self, limit=100) -> List[UserInvitation]:
        """
        Get all invitations (all statuses) for display in user management
        
        Args:
            limit: Maximum number of invitations to return (default 100)
        
        Returns:
            List of UserInvitation objects
        """
        with self.session_factory() as session:
            invitations = session.query(UserInvitation).order_by(
                UserInvitation.created_at.desc()
            ).limit(limit).all()
            
            # Access all attributes before expunging
            for inv in invitations:
                _ = inv.id
                _ = inv.email
                _ = inv.role
                _ = inv.status
                _ = inv.created_at
                _ = inv.expires_at
                _ = inv.completed_at
                _ = inv.invited_by
                _ = inv.completed_by_username
                session.expunge(inv)
            
            return invitations
    
    def get_invitation_by_email(self, email: str) -> Optional[UserInvitation]:
        """
        Get the most recent invitation for an email
        
        Args:
            email: Email address
            
        Returns:
            UserInvitation object or None
        """
        with self.session_factory() as session:
            invitation = session.query(UserInvitation).filter_by(
                email=email
            ).order_by(UserInvitation.created_at.desc()).first()
            
            if invitation:
                session.expunge(invitation)
            
            return invitation
    
    def cleanup_expired_invitations(self) -> int:
        """
        Mark expired invitations as expired
        
        Returns:
            Number of invitations marked as expired
        """
        with self.session_factory() as session:
            expired_invitations = session.query(UserInvitation).filter(
                UserInvitation.status == 'pending',
                UserInvitation.expires_at < datetime.utcnow()
            ).all()
            
            count = 0
            for invitation in expired_invitations:
                invitation.status = 'expired'
                count += 1
            
            session.commit()
            print(f"Marked {count} invitations as expired")
            return count
    
    # ==================== PASSWORD RESET ====================
    
    def create_password_reset_token(self, user_id: int, username: str, email: str,
                                    expiry_hours: int = 24) -> Optional[PasswordResetToken]:
        """
        Create a password reset token
        
        Args:
            user_id: User ID
            username: Username
            email: User's email address
            expiry_hours: Hours until token expires (default 24)
            
        Returns:
            PasswordResetToken object or None if error
        """
        with self.session_factory() as session:
            try:
                # Invalidate any existing pending tokens for this user
                existing_tokens = session.query(PasswordResetToken).filter_by(
                    user_id=user_id,
                    status='pending'
                ).all()
                
                for token in existing_tokens:
                    token.status = 'expired'
                
                # Generate unique token
                token_str = PasswordResetToken.generate_token()
                
                # Create reset token
                reset_token = PasswordResetToken(
                    user_id=user_id,
                    username=username,
                    email=email,
                    token=token_str,
                    expires_at=PasswordResetToken.get_expiry_time(expiry_hours)
                )
                
                session.add(reset_token)
                session.commit()
                session.refresh(reset_token)
                session.expunge(reset_token)
                
                print(f"Created password reset token for {username}")
                return reset_token
                
            except Exception as e:
                print(f"Error creating password reset token: {e}")
                session.rollback()
                return None
    
    def verify_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        """
        Verify password reset token
        
        Args:
            token: Reset token string
            
        Returns:
            PasswordResetToken object if valid, None otherwise
        """
        with self.session_factory() as session:
            reset_token = session.query(PasswordResetToken).filter_by(
                token=token,
                status='pending'
            ).first()
            
            if reset_token:
                # Check if expired
                if reset_token.is_expired():
                    reset_token.status = 'expired'
                    session.commit()
                    print(f"Reset token for {reset_token.username} has expired")
                    return None
                
                session.expunge(reset_token)
                return reset_token
            
            return None
    
    def use_reset_token(self, token: str) -> bool:
        """
        Mark reset token as used
        
        Args:
            token: Reset token string
            
        Returns:
            True if successful, False otherwise
        """
        with self.session_factory() as session:
            reset_token = session.query(PasswordResetToken).filter_by(
                token=token,
                status='pending'
            ).first()
            
            if reset_token and reset_token.is_valid():
                reset_token.status = 'used'
                reset_token.used_at = datetime.utcnow()
                session.commit()
                print(f"Used reset token for {reset_token.username}")
                return True
            
            return False
    
    def cleanup_expired_tokens(self) -> int:
        """
        Mark expired reset tokens as expired
        
        Returns:
            Number of tokens marked as expired
        """
        with self.session_factory() as session:
            expired_tokens = session.query(PasswordResetToken).filter(
                PasswordResetToken.status == 'pending',
                PasswordResetToken.expires_at < datetime.utcnow()
            ).all()
            
            count = 0
            for token in expired_tokens:
                token.status = 'expired'
                count += 1
            
            session.commit()
            print(f"Marked {count} reset tokens as expired")
            return count
