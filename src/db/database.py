"""
Database connection and management for ANPR System
Provides database initialization, connection handling, and utility methods
"""

import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Optional, Generator
from datetime import datetime

from .models import Base, RawLog, VehicleLog, Camera, Vehicle, ToggleMode

logger = logging.getLogger(__name__)


class Database:
    """Database manager for ANPR System"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection
        
        Args:
            database_url: Database connection string. If None, uses SQLite default
        """
        if database_url is None:
            # Default to SQLite database in the project root
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'anpr_database.db')
            database_url = f"sqlite:///{os.path.abspath(db_path)}"
        
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """Setup database engine and session factory"""
        try:
            # Create engine with appropriate settings
            if self.database_url.startswith('sqlite'):
                # SQLite specific settings
                self.engine = create_engine(
                    self.database_url,
                    echo=False,  # Set to True for SQL debugging
                    pool_pre_ping=True,
                    connect_args={"check_same_thread": False}
                )
                
                # Enable WAL mode for better concurrency in SQLite
                @event.listens_for(self.engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA cache_size=10000")
                    cursor.execute("PRAGMA temp_store=MEMORY")
                    cursor.close()
            else:
                # For other databases (MySQL, PostgreSQL, etc.)
                self.engine = create_engine(
                    self.database_url,
                    echo=False,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
            
            # Create session factory
            self.SessionLocal = scoped_session(sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            ))
            
            logger.info(f"Database initialized: {self.database_url}")
            
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator:
        """
        Get database session with automatic cleanup
        
        Usage:
            with db.get_session() as session:
                # Use session here
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def add_raw_log(self, camera_id: int, frame_id: str, plate_text: str, 
                    confidence: float, image_path: Optional[str] = None,
                    bbox_coords: Optional[tuple] = None, processing_time: Optional[float] = None) -> int:
        """
        Add a new raw log entry
        
        Args:
            camera_id: Camera identifier
            frame_id: Frame identifier
            plate_text: OCR result (raw)
            confidence: Model confidence score
            image_path: Path to stored image
            bbox_coords: Bounding box coordinates (x, y, width, height)
            processing_time: Time taken for detection/OCR
            
        Returns:
            raw_id of the created record
        """
        with self.get_session() as session:
            raw_log = RawLog(
                camera_id=camera_id,
                frame_id=frame_id,
                plate_text=plate_text,
                confidence=confidence,
                captured_at=datetime.utcnow(),
                image_path=image_path,
                processing_time=processing_time
            )
            
            if bbox_coords:
                raw_log.bbox_x, raw_log.bbox_y, raw_log.bbox_width, raw_log.bbox_height = bbox_coords
            
            session.add(raw_log)
            session.flush()
            return raw_log.raw_id
    
    def add_vehicle_log(self, plate_number: str, toggle_mode: ToggleMode, 
                       raw_ref: int, vehicle_id: Optional[int] = None,
                       session_id: Optional[str] = None, location_info: Optional[str] = None,
                       duration_minutes: Optional[int] = None) -> int:
        """
        Add a new vehicle log entry with toggle mode
        
        Args:
            plate_number: Cleaned plate number
            toggle_mode: ENTRY or EXIT
            raw_ref: Reference to raw log ID
            vehicle_id: Vehicle ID if known
            session_id: Session identifier for grouping
            location_info: Additional location context
            duration_minutes: Duration for EXIT records
            
        Returns:
            log_id of the created record
        """
        with self.get_session() as session:
            vehicle_log = VehicleLog(
                plate_number=plate_number,
                vehicle_id=vehicle_id,
                toggle_mode=toggle_mode,
                captured_at=datetime.utcnow(),
                raw_ref=raw_ref,
                session_id=session_id,
                location_info=location_info,
                duration_minutes=duration_minutes
            )
            
            session.add(vehicle_log)
            session.commit()
            return vehicle_log.log_id
    
    def get_or_create_vehicle(self, plate_number: str, vehicle_type: Optional[str] = None) -> int:
        """
        Get existing vehicle or create new one
        
        Args:
            plate_number: Vehicle plate number
            vehicle_type: Type of vehicle
            
        Returns:
            vehicle_id
        """
        with self.get_session() as session:
            vehicle = session.query(Vehicle).filter_by(plate_number=plate_number).first()
            
            if not vehicle:
                vehicle = Vehicle(
                    plate_number=plate_number,
                    vehicle_type=vehicle_type,
                    created_at=datetime.utcnow()
                )
                session.add(vehicle)
                session.flush()
            
            return vehicle.vehicle_id
    
    def get_or_create_camera(self, camera_name: str, location: Optional[str] = None) -> int:
        """
        Get existing camera or create new one
        
        Args:
            camera_name: Camera identifier/name
            location: Camera location
            
        Returns:
            camera_id
        """
        with self.get_session() as session:
            camera = session.query(Camera).filter_by(camera_name=camera_name).first()
            
            if not camera:
                camera = Camera(
                    camera_name=camera_name,
                    location=location,
                    created_at=datetime.utcnow()
                )
                session.add(camera)
                session.flush()
            
            return camera.camera_id
    
    def get_last_vehicle_log_data(self, plate_number: str) -> Optional[dict]:
        """
        Get the last vehicle log data for a plate number
        
        Args:
            plate_number: Vehicle plate number
            
        Returns:
            Dictionary with log data or None
        """
        with self.get_session() as session:
            log = session.query(VehicleLog)\
                        .filter_by(plate_number=plate_number)\
                        .order_by(VehicleLog.captured_at.desc())\
                        .first()
            
            if log:
                return {
                    'log_id': log.log_id,
                    'plate_number': log.plate_number,
                    'toggle_mode': log.toggle_mode,
                    'captured_at': log.captured_at,
                    'duration_minutes': log.duration_minutes,
                    'session_id': log.session_id
                }
            return None
    
    def close(self):
        """Close database connections"""
        if self.SessionLocal:
            self.SessionLocal.remove()
        if self.engine:
            self.engine.dispose()
        logger.info("Database connections closed")


# Global database instance
db_instance = None

def get_database(database_url: Optional[str] = None) -> Database:
    """Get or create global database instance"""
    global db_instance
    if db_instance is None:
        db_instance = Database(database_url)
    return db_instance
