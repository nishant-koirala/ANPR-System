"""
Email sender for user invitations and password resets
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class InvitationEmailSender:
    """Send invitation and password reset emails"""
    
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, sender_password: str):
        """
        Initialize email sender
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port
            sender_email: Sender email address
            sender_password: Sender email password/app password
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
    
    def send_invitation_email(self, recipient_email: str, otp: str, role: str,
                             invited_by: str = "Admin", expiry_minutes: int = 5) -> bool:
        """
        Send user invitation email with OTP
        
        Args:
            recipient_email: Recipient's email address
            otp: One-time password
            role: User role (admin, operator, viewer)
            invited_by: Name of person who sent invitation
            expiry_minutes: Minutes until OTP expires (default 5)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = '🎉 You\'re Invited to NEPALI ANPR System'
            message['From'] = f"NEPALI ANPR System <{self.sender_email}>"
            message['To'] = recipient_email
            
            # Create HTML content
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .otp-box {{
            background: white;
            border: 3px dashed #667eea;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
            border-radius: 10px;
        }}
        .otp {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            letter-spacing: 5px;
            font-family: 'Courier New', monospace;
        }}
        .role-badge {{
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            text-transform: capitalize;
        }}
        .steps {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .step {{
            margin: 15px 0;
            padding-left: 30px;
            position: relative;
        }}
        .step-number {{
            position: absolute;
            left: 0;
            top: 0;
            background: #667eea;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-weight: bold;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            color: #6c757d;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎉 Welcome to NEPALI ANPR!</h1>
        <p>You've been invited to join our system</p>
    </div>
    
    <div class="content">
        <p>Hello!</p>
        
        <p><strong>{invited_by}</strong> has invited you to join the <strong>NEPALI ANPR System</strong> as a <span class="role-badge">{role}</span>.</p>
        
        <div class="otp-box">
            <p style="margin: 0; font-size: 14px; color: #6c757d;">Your One-Time Password (OTP)</p>
            <div class="otp">{otp}</div>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #6c757d;">Valid for {expiry_minutes} minutes</p>
        </div>
        
        <div class="steps">
            <h3 style="margin-top: 0;">📝 Complete Your Registration:</h3>
            
            <div class="step">
                <div class="step-number">1</div>
                <strong>Open the ANPR Application</strong><br>
                <span style="color: #6c757d;">Launch the NEPALI ANPR desktop application</span>
            </div>
            
            <div class="step">
                <div class="step-number">2</div>
                <strong>Click "Complete Registration"</strong><br>
                <span style="color: #6c757d;">On the login screen, select the registration option</span>
            </div>
            
            <div class="step">
                <div class="step-number">3</div>
                <strong>Enter Your Details</strong><br>
                <span style="color: #6c757d;">
                    • Email: <strong>{recipient_email}</strong><br>
                    • OTP: <strong>{otp}</strong><br>
                    • Choose your username<br>
                    • Create a secure password
                </span>
            </div>
            
            <div class="step">
                <div class="step-number">4</div>
                <strong>Start Using the System</strong><br>
                <span style="color: #6c757d;">Log in with your new credentials and explore!</span>
            </div>
        </div>
        
        <div class="warning">
            <strong>⚠️ Important:</strong>
            <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                <li>This OTP is valid for <strong>{expiry_minutes} minutes</strong></li>
                <li>It can only be used <strong>once</strong></li>
                <li>Keep it confidential - don't share with anyone</li>
                <li>If you didn't request this invitation, please ignore this email</li>
            </ul>
        </div>
        
        <p style="margin-top: 30px;">
            Need help? Contact your system administrator.<br>
            Looking forward to having you on board! 🚀
        </p>
    </div>
    
    <div class="footer">
        <p>This is an automated message from NEPALI ANPR System<br>
        Please do not reply to this email</p>
    </div>
</body>
</html>
            """
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            print(f"✅ Invitation email sent to {recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send invitation email to {recipient_email}: {e}")
            return False
    
    def send_password_reset_email(self, recipient_email: str, username: str,
                                  reset_token: str, expiry_hours: int = 24) -> bool:
        """
        Send password reset email
        
        Args:
            recipient_email: Recipient's email address
            username: User's username
            reset_token: Password reset token
            expiry_hours: Hours until token expires
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = '🔐 Password Reset Request - NEPALI ANPR'
            message['From'] = f"NEPALI ANPR System <{self.sender_email}>"
            message['To'] = recipient_email
            
            # Create HTML content
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .token-box {{
            background: white;
            border: 2px solid #f5576c;
            padding: 15px;
            margin: 20px 0;
            border-radius: 10px;
            word-break: break-all;
        }}
        .token {{
            font-size: 14px;
            font-family: 'Courier New', monospace;
            color: #f5576c;
            font-weight: bold;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            color: #6c757d;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔐 Password Reset Request</h1>
        <p>NEPALI ANPR System</p>
    </div>
    
    <div class="content">
        <p>Hello <strong>{username}</strong>,</p>
        
        <p>We received a request to reset your password. Use the reset token below to create a new password:</p>
        
        <div class="token-box">
            <p style="margin: 0 0 10px 0; font-size: 12px; color: #6c757d;">Your Reset Token:</p>
            <div class="token">{reset_token}</div>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #6c757d;">Valid for {expiry_hours} hours</p>
        </div>
        
        <p><strong>To reset your password:</strong></p>
        <ol>
            <li>Open the ANPR Application</li>
            <li>Click "Reset Password" on the login screen</li>
            <li>Enter your username and the reset token above</li>
            <li>Create a new secure password</li>
        </ol>
        
        <div class="warning">
            <strong>⚠️ Security Notice:</strong>
            <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                <li>This token expires in <strong>{expiry_hours} hours</strong></li>
                <li>It can only be used <strong>once</strong></li>
                <li>If you didn't request this reset, please contact your administrator immediately</li>
            </ul>
        </div>
        
        <p style="margin-top: 30px;">
            If you have any questions, please contact your system administrator.
        </p>
    </div>
    
    <div class="footer">
        <p>This is an automated message from NEPALI ANPR System<br>
        Please do not reply to this email</p>
    </div>
</body>
</html>
            """
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            print(f"✅ Password reset email sent to {recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send password reset email to {recipient_email}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test SMTP connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
            print("✅ SMTP connection successful")
            return True
        except Exception as e:
            print(f"❌ SMTP connection failed: {e}")
            return False
