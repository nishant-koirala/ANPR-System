"""
Database models for Special Vehicles Management
Handles Stolen Vehicles and Staff Vehicles with Alert System
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from .rbac_models import Base


class StolenVehicle(Base):
    """Stolen vehicles table for alert system"""
    __tablename__ = 'stolen_vehicles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20), nullable=False, unique=True, index=True)
    owner_name = Column(String(100))
    vehicle_type = Column(String(50))  # Car, Motorcycle, SUV, Van, Truck, Bus
    vehicle_color = Column(String(50))
    contact_number = Column(String(20))
    notes = Column(Text)
    
    # Status and dates
    status = Column(String(20), default='Active', index=True)  # Active, Recovered, Archived
    reported_date = Column(Date, nullable=False)
    recovered_date = Column(Date)
    
    # Alert configuration
    enable_dashboard_alert = Column(Boolean, default=True)
    enable_email_alert = Column(Boolean, default=True)
    enable_sound_alert = Column(Boolean, default=True)
    
    # Timestamps and audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.user_id'))
    updated_by = Column(Integer, ForeignKey('users.user_id'))
    
    # Relationships
    alert_history = relationship("StolenVehicleAlert", back_populates="stolen_vehicle", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<StolenVehicle(id={self.id}, plate='{self.plate_number}', status='{self.status}')>"


class StaffVehicle(Base):
    """Staff vehicles table for access management"""
    __tablename__ = 'staff_vehicles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20), nullable=False, unique=True, index=True)
    staff_name = Column(String(100), nullable=False)
    department = Column(String(50))  # Management, Security, Operations, Maintenance, IT, HR
    position = Column(String(100))
    vehicle_type = Column(String(50))  # Car, Motorcycle, SUV, Van
    vehicle_color = Column(String(50))
    contact_number = Column(String(20))
    notes = Column(Text)
    
    # Validity period
    valid_from = Column(Date, nullable=False, index=True)
    valid_until = Column(Date, nullable=False, index=True)
    
    # Access settings
    free_parking = Column(Boolean, default=True)  # No parking charges
    priority_access = Column(Boolean, default=False)  # Priority entry/exit
    
    # Status
    status = Column(String(20), default='Active', index=True)  # Active, Expired, Suspended
    
    # Timestamps and audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.user_id'))
    updated_by = Column(Integer, ForeignKey('users.user_id'))
    
    def __repr__(self):
        return f"<StaffVehicle(id={self.id}, plate='{self.plate_number}', staff='{self.staff_name}')>"
    
    def is_valid(self, check_date=None):
        """Check if staff vehicle is currently valid"""
        if check_date is None:
            check_date = datetime.now().date()
        return self.valid_from <= check_date <= self.valid_until and self.status == 'Active'


class StolenVehicleAlert(Base):
    """Alert history for stolen vehicle detections"""
    __tablename__ = 'stolen_vehicle_alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stolen_vehicle_id = Column(Integer, ForeignKey('stolen_vehicles.id'), nullable=False, index=True)
    
    # Detection details
    detection_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey('cameras.camera_id'))
    raw_log_id = Column(Integer, ForeignKey('raw_logs.raw_id'))
    
    # Plate image
    plate_image_path = Column(String(500))
    
    # Alert status
    alert_sent_dashboard = Column(Boolean, default=False)
    alert_sent_email = Column(Boolean, default=False)
    alert_sent_sms = Column(Boolean, default=False)
    
    # Email details
    email_recipients = Column(Text)  # Comma-separated list
    email_sent_at = Column(DateTime)
    
    # Additional info
    confidence = Column(Float)
    notes = Column(Text)
    
    # Relationships
    stolen_vehicle = relationship("StolenVehicle", back_populates="alert_history")
    
    def __repr__(self):
        return f"<StolenVehicleAlert(id={self.id}, stolen_vehicle_id={self.stolen_vehicle_id}, time={self.detection_time})>"


class AlertConfiguration(Base):
    """Global alert configuration settings"""
    __tablename__ = 'alert_configuration'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Dashboard alert settings
    dashboard_alert_enabled = Column(Boolean, default=True)
    dashboard_sound_enabled = Column(Boolean, default=True)
    dashboard_popup_enabled = Column(Boolean, default=True)
    dashboard_highlight_duration = Column(Integer, default=30)  # seconds
    
    # Email alert settings
    email_alert_enabled = Column(Boolean, default=True)
    email_recipients = Column(Text)  # One email per line
    email_include_image = Column(Boolean, default=True)
    email_include_location = Column(Boolean, default=True)
    
    # SMS alert settings (future)
    sms_alert_enabled = Column(Boolean, default=False)
    sms_recipients = Column(Text)
    
    # Priority settings
    stolen_vehicle_priority = Column(String(20), default='Critical')  # Critical, High, Medium, Low
    alert_cooldown_minutes = Column(Integer, default=5)  # Prevent duplicate alerts
    auto_archive_days = Column(Integer, default=30)  # Auto-archive old records (0 = never)
    
    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey('users.user_id'))
    
    def __repr__(self):
        return f"<AlertConfiguration(id={self.id})>"
