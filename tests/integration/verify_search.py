#!/usr/bin/env python3
"""
Test script for search plate functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.db import get_database
from src.db.models import VehicleLog, RawLog, Camera, ToggleMode
from datetime import datetime
from sqlalchemy.orm import sessionmaker

def test_search_functionality():
    """Test the search functionality directly"""
    try:
        # Initialize database
        db = get_database()
        print(f"✅ Database connected: {db.database_url}")
        
        # Create session factory
        SessionLocal = sessionmaker(bind=db.engine)
        
        # Test creating some sample data if database is empty
        with db.get_session() as session:
            count = session.query(VehicleLog).count()
            print(f"📊 Current vehicle logs in database: {count}")
            
            if count == 0:
                print("📝 Creating test data...")
                # Create a test camera
                camera = Camera(camera_name="TEST_CAM", location="Test Location")
                session.add(camera)
                session.commit()
                camera_id = camera.camera_id
                
                # Create a test raw log
                raw_log = RawLog(
                    camera_id=camera_id,
                    frame_id=1,
                    plate_number="TEST123",
                    confidence=0.95,
                    processed_at=datetime.now()
                )
                session.add(raw_log)
                session.commit()
                raw_id = raw_log.raw_id
                
                # Create a test vehicle log
                vehicle_log = VehicleLog(
                    plate_number="TEST123",
                    toggle_mode=ToggleMode.ENTRY,
                    captured_at=datetime.now(),
                    raw_ref=raw_id
                )
                session.add(vehicle_log)
                session.commit()
                print("✅ Test data created successfully")
            
            # Test search functionality
            print("🔍 Testing search functionality...")
            with db.get_session() as session:
                query = session.query(VehicleLog).filter(VehicleLog.plate_number.ilike('%TEST%'))
                results = query.all()
                print(f"🔍 Search results for 'TEST': {len(results)} records found")
                
                for log in results:
                    print(f"   - Plate: {log.plate_number}, Type: {log.toggle_mode.value}, Time: {log.captured_at}")
        
        print("✅ Search test completed successfully")
        
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_functionality()
