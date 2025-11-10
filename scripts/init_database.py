#!/usr/bin/env python3
"""
Database Initialization Script for ANPR System
Run this script to set up the database with all required tables and initial data
"""

import os
import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db import Database, get_database
from src.db.models import Camera, Vehicle

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize the ANPR database"""
    try:
        logger.info("Starting ANPR Database initialization...")
        
        # Get database instance
        db = get_database()
        
        # Create all tables
        logger.info("Creating database tables...")
        db.create_tables()
        
        # Add initial camera data
        logger.info("Adding initial camera data...")
        cameras = [
            ("CAM_001", "Main Entrance"),
            ("CAM_002", "Exit Gate"),
            ("CAM_003", "Parking Area A"),
            ("CAM_004", "Parking Area B"),
        ]
        
        for camera_name, location in cameras:
            camera_id = db.get_or_create_camera(camera_name, location)
            logger.info(f"Camera created/found: {camera_name} (ID: {camera_id})")
        
        # Verify database setup
        with db.get_session() as session:
            camera_count = session.query(Camera).count()
            vehicle_count = session.query(Vehicle).count()
            
            logger.info(f"Database verification:")
            logger.info(f"  - Cameras: {camera_count}")
            logger.info(f"  - Vehicles: {vehicle_count}")
        
        logger.info("✅ Database initialization completed successfully!")
        logger.info(f"Database location: {db.database_url}")
        
        # Show next steps
        print("\n" + "="*60)
        print("🎉 ANPR Database Setup Complete!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run example usage: python src/db/example_usage.py")
        print("2. Integrate with your ANPR detection pipeline")
        print("3. Use ToggleManager for intelligent entry/exit logging")
        print("\nDatabase features:")
        print("✓ Raw detection logging (all YOLO/OCR results)")
        print("✓ Smart toggle mode (ENTRY/EXIT detection)")
        print("✓ Vehicle tracking with session management")
        print("✓ Confidence-based filtering")
        print("✓ Duplicate detection prevention")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
    finally:
        # Clean up
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    main()
