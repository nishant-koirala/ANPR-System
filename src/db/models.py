"""
Database models for ANPR System Phase 1: Core Logging
Implements raw_logs and vehicle_log tables with toggle mode functionality
"""

from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.dialects.sqlite import INTEGER
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# Import the shared Base from rbac_models to ensure consistency
from .rbac_models import Base


class ToggleMode(enum.Enum):
    """Enum for vehicle movement toggle mode"""
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class Camera(Base):
    """Camera information table"""
    __tablename__ = 'cameras'
    
    camera_id = Column(Integer, primary_key=True, autoincrement=True)
    camera_name = Column(String(100), nullable=False)
    location = Column(String(255))
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    raw_logs = relationship("RawLog", back_populates="camera")


class Vehicle(Base):
    """Vehicle information table"""
    __tablename__ = 'vehicles'
    
    vehicle_id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20), unique=True, nullable=False, index=True)
    vehicle_type = Column(String(50))  # car, truck, motorcycle, etc.
    owner_info = Column(Text)  # JSON or text field for owner details
    is_blacklisted = Column(Integer, default=0)  # 0 for normal, 1 for blacklisted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    vehicle_logs = relationship("VehicleLog", back_populates="vehicle")


class RawLog(Base):
    """
    Raw logs table - stores every detection from camera/YOLO before filtering
    This is the foundation table that captures all raw detections
    """
    __tablename__ = 'raw_logs'
    
    raw_id = Column(INTEGER, primary_key=True, autoincrement=True)
    camera_id = Column(Integer, ForeignKey('cameras.camera_id'), nullable=False, index=True)
    frame_id = Column(String(50), nullable=False, index=True)
    plate_text = Column(String(20), nullable=False, index=True)  # OCR result (raw, may be noisy)
    confidence = Column(Float, nullable=False)  # Model confidence score
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    image_path = Column(String(255))  # Stored image snapshot (optional)
    
    # Plate image storage fields
    plate_image_path = Column(String(500))  # Cropped plate image path
    thumbnail_path = Column(String(500))    # Thumbnail image path
    image_width = Column(Integer)           # Plate image width
    image_height = Column(Integer)          # Plate image height
    image_size = Column(Integer)            # File size in bytes
    
    # Additional metadata fields
    bbox_x = Column(Float)  # Bounding box coordinates
    bbox_y = Column(Float)
    bbox_width = Column(Float)
    bbox_height = Column(Float)
    processing_time = Column(Float)  # Time taken for detection/OCR
    
    # Relationships
    camera = relationship("Camera", back_populates="raw_logs")
    vehicle_logs = relationship("VehicleLog", back_populates="raw_log")
    
    def __repr__(self):
        return f"<RawLog(raw_id={self.raw_id}, plate_text='{self.plate_text}', confidence={self.confidence})>"


# User model moved to rbac_models.py to avoid conflicts
# Import User from rbac_models when needed


class PlateEditHistory(Base):
    """Audit trail for plate number edits"""
    __tablename__ = 'plate_edit_history'
    
    edit_id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer, ForeignKey('vehicle_log.log_id'), nullable=False, index=True)
    old_plate_number = Column(String(20), nullable=False)
    new_plate_number = Column(String(20), nullable=False)
    edited_by = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    edited_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    edit_reason = Column(Text)
    ip_address = Column(String(45))  # Support IPv4 and IPv6
    user_agent = Column(Text)
    
    # Relationships
    vehicle_log = relationship("VehicleLog", back_populates="edit_history")
    editor = relationship("User", back_populates="edit_history")
    
    def __repr__(self):
        return f"<PlateEditHistory(edit_id={self.edit_id}, old='{self.old_plate_number}', new='{self.new_plate_number}')>"


class VehicleLog(Base):
    """
    Vehicle log table - filtered, toggled entry/exit records
    This table contains the processed and filtered records with toggle mode functionality
    """
    __tablename__ = 'vehicle_log'
    
    log_id = Column(INTEGER, primary_key=True, autoincrement=True)
    plate_number = Column(String(20), nullable=False, index=True)  # Cleaned plate number
    vehicle_id = Column(Integer, ForeignKey('vehicles.vehicle_id'), nullable=True, index=True)
    toggle_mode = Column(Enum(ToggleMode), nullable=False, index=True)  # ENTRY or EXIT
    captured_at = Column(DateTime, nullable=False, index=True)  # Time of toggle record
    raw_ref = Column(INTEGER, ForeignKey('raw_logs.raw_id'), nullable=False)  # Reference to raw log
    
    # Additional tracking fields
    session_id = Column(String(50))  # To group related entry/exit events
    duration_minutes = Column(Integer)  # For EXIT records, duration since ENTRY
    duration_hours = Column(Float)  # For EXIT records, duration in hours (calculated from minutes)
    amount = Column(Float)  # Calculated amount based on duration and hourly rate
    location_info = Column(String(255))  # Additional location context
    notes = Column(Text)  # Any additional notes or flags
    
    # Plate editing fields
    original_plate_number = Column(String(20))  # Original OCR result before editing
    is_edited = Column(Boolean, default=False)  # Flag indicating if plate was edited
    edited_by = Column(Integer, ForeignKey('users.user_id'), nullable=True)  # User who edited
    edited_at = Column(DateTime, nullable=True)  # When the edit was made
    edit_reason = Column(Text)  # Reason for the edit
    
    # Plate image fields
    plate_image_path = Column(String(500))  # Path to full plate image
    thumbnail_path = Column(String(500))  # Path to thumbnail image
    image_width = Column(Integer)  # Image width in pixels
    image_height = Column(Integer)  # Image height in pixels
    image_size = Column(Integer)  # File size in bytes
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="vehicle_logs")
    raw_log = relationship("RawLog", back_populates="vehicle_logs")
    editor = relationship("User", back_populates="edited_logs", foreign_keys=[edited_by])
    edit_history = relationship("PlateEditHistory", back_populates="vehicle_log")
    
    def __repr__(self):
        return f"<VehicleLog(log_id={self.log_id}, plate_number='{self.plate_number}', toggle_mode={self.toggle_mode.value})>"


# Index definitions for better query performance
from sqlalchemy import Index

# Composite indexes for common queries
Index('idx_raw_logs_camera_time', RawLog.camera_id, RawLog.captured_at)
Index('idx_raw_logs_plate_time', RawLog.plate_text, RawLog.captured_at)
Index('idx_vehicle_log_plate_toggle', VehicleLog.plate_number, VehicleLog.toggle_mode)
Index('idx_vehicle_log_time_toggle', VehicleLog.captured_at, VehicleLog.toggle_mode)

# New indexes for enhanced functionality
Index('idx_raw_logs_plate_image', RawLog.plate_image_path)
Index('idx_vehicle_log_edited', VehicleLog.is_edited)
Index('idx_vehicle_log_editor', VehicleLog.edited_by)
Index('idx_edit_history_log', PlateEditHistory.log_id)
Index('idx_edit_history_user', PlateEditHistory.edited_by)
Index('idx_edit_history_date', PlateEditHistory.edited_at)
# User index moved to rbac_models.py
