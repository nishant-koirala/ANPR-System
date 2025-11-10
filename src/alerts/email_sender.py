"""
Email Alert System for Stolen Vehicle Detection
Sends email notifications when stolen vehicles are detected
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
import os
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class EmailAlertSender:
    """Send email alerts for stolen vehicle detections"""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587,
                 sender_email: str = None, sender_password: str = None):
        """
        Initialize email sender
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port (587 for TLS)
            sender_email: Sender email address
            sender_password: App password for sender email
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        
    def send_stolen_vehicle_alert(self, 
                                  plate_number: str,
                                  owner_name: str = "Unknown",
                                  vehicle_type: str = "Unknown",
                                  vehicle_color: str = "Unknown",
                                  reported_date: str = "Unknown",
                                  detection_time: str = None,
                                  detection_location: str = "Camera Detection",
                                  recipients: List[str] = None,
                                  plate_image_path: str = None) -> bool:
        """
        Send stolen vehicle alert email
        
        Args:
            plate_number: Detected plate number
            owner_name: Vehicle owner name
            vehicle_type: Type of vehicle
            vehicle_color: Color of vehicle
            reported_date: Date vehicle was reported stolen
            detection_time: Time of detection
            detection_location: Location where detected
            recipients: List of email addresses to send to
            plate_image_path: Path to plate image (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not recipients or not self.sender_email or not self.sender_password:
            logger.warning("Email configuration incomplete - cannot send alert")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('related')
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"🚨 STOLEN VEHICLE ALERT - {plate_number}"
            
            # Detection time
            if not detection_time:
                detection_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create HTML email body
            html_body = self._create_html_body(
                plate_number=plate_number,
                owner_name=owner_name,
                vehicle_type=vehicle_type,
                vehicle_color=vehicle_color,
                reported_date=reported_date,
                detection_time=detection_time,
                detection_location=detection_location
            )
            
            # Attach HTML body
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            # Plain text version
            text_body = self._create_text_body(
                plate_number=plate_number,
                owner_name=owner_name,
                vehicle_type=vehicle_type,
                vehicle_color=vehicle_color,
                reported_date=reported_date,
                detection_time=detection_time,
                detection_location=detection_location
            )
            
            msg_alternative.attach(MIMEText(text_body, 'plain'))
            msg_alternative.attach(MIMEText(html_body, 'html'))
            
            # Attach plate image if available
            if plate_image_path and os.path.exists(plate_image_path):
                try:
                    with open(plate_image_path, 'rb') as img_file:
                        img_data = img_file.read()
                        image = MIMEImage(img_data, name=os.path.basename(plate_image_path))
                        image.add_header('Content-ID', '<plate_image>')
                        msg.attach(image)
                except Exception as img_error:
                    logger.warning(f"Could not attach image: {img_error}")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email alert sent successfully to {len(recipients)} recipient(s)")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Email authentication failed - check email/password")
            return False
        except smtplib.SMTPException as smtp_error:
            logger.error(f"❌ SMTP error: {smtp_error}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending email: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_html_body(self, plate_number: str, owner_name: str, vehicle_type: str,
                         vehicle_color: str, reported_date: str, detection_time: str,
                         detection_location: str) -> str:
        """Create HTML email body"""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #fff5f5;
                    border: 3px solid #e74c3c;
                    border-radius: 10px;
                }}
                .header {{
                    background-color: #e74c3c;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .alert-icon {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                .content {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                }}
                .info-row {{
                    padding: 10px;
                    border-bottom: 1px solid #eee;
                }}
                .info-row:last-child {{
                    border-bottom: none;
                }}
                .label {{
                    font-weight: bold;
                    color: #e74c3c;
                    display: inline-block;
                    width: 150px;
                }}
                .value {{
                    color: #333;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 2px solid #ffc107;
                    padding: 15px;
                    margin-top: 20px;
                    border-radius: 5px;
                    text-align: center;
                }}
                .warning strong {{
                    color: #e74c3c;
                }}
                .footer {{
                    margin-top: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                }}
                .plate-image {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .plate-image img {{
                    max-width: 100%;
                    border: 2px solid #e74c3c;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="alert-icon">🚨</div>
                    <h1>STOLEN VEHICLE DETECTED</h1>
                </div>
                
                <div class="content">
                    <h2 style="color: #e74c3c; margin-top: 0;">Alert Details</h2>
                    
                    <div class="info-row">
                        <span class="label">Plate Number:</span>
                        <span class="value"><strong style="font-size: 18px;">{plate_number}</strong></span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Owner Name:</span>
                        <span class="value">{owner_name}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Vehicle Type:</span>
                        <span class="value">{vehicle_type}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Vehicle Color:</span>
                        <span class="value">{vehicle_color}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Reported Date:</span>
                        <span class="value">{reported_date}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Detection Time:</span>
                        <span class="value">{detection_time}</span>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Detection Location:</span>
                        <span class="value">{detection_location}</span>
                    </div>
                </div>
                
                <div class="warning">
                    <strong>⚠️ IMMEDIATE ACTION REQUIRED</strong><br>
                    This vehicle has been reported as stolen. Please contact local authorities immediately.
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from the NEPALI ANPR System</p>
                    <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_body(self, plate_number: str, owner_name: str, vehicle_type: str,
                         vehicle_color: str, reported_date: str, detection_time: str,
                         detection_location: str) -> str:
        """Create plain text email body"""
        
        text = f"""
🚨 STOLEN VEHICLE ALERT 🚨
{'=' * 50}

ALERT DETAILS:
--------------
Plate Number:        {plate_number}
Owner Name:          {owner_name}
Vehicle Type:        {vehicle_type}
Vehicle Color:       {vehicle_color}
Reported Date:       {reported_date}
Detection Time:      {detection_time}
Detection Location:  {detection_location}

⚠️ IMMEDIATE ACTION REQUIRED
This vehicle has been reported as stolen.
Please contact local authorities immediately.

---
This is an automated alert from the NEPALI ANPR System
Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return text.strip()
    
    def test_connection(self) -> bool:
        """
        Test SMTP connection and authentication
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
            logger.info("✅ Email connection test successful")
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Email authentication failed")
            return False
        except Exception as e:
            logger.error(f"❌ Email connection test failed: {e}")
            return False
