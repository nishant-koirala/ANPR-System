#!/usr/bin/env python3
"""
Populate database with test data and test search functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.db import get_database
from src.db.models import VehicleLog, RawLog, Camera, ToggleMode
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc

def populate_test_data():
    """Add some test data to the database"""
    try:
        print("📝 Populating test data...")
        
        # Initialize database
        db = get_database()
        
        with db.get_session() as session:
            # Check if we already have test data
            existing_logs = session.query(VehicleLog).filter(
                VehicleLog.plate_number.ilike('%TEST%')
            ).count()
            
            if existing_logs > 0:
                print("✅ Test data already exists")
                return True
            
            # Create a test camera
            camera = Camera(camera_name="MAIN_CAM", location="Main Entrance")
            session.add(camera)
            session.commit()
            camera_id = camera.camera_id
            print(f"✅ Created camera with ID: {camera_id}")
            
            # Create test raw logs
            raw_logs_data = [
                {"plate_number": "TEST123", "confidence": 0.95},
                {"plate_number": "TEST456", "confidence": 0.87},
                {"plate_number": "ABC123", "confidence": 0.92},
                {"plate_number": "XYZ789", "confidence": 0.78}
            ]
            
            raw_ids = []
            for i, raw_data in enumerate(raw_logs_data):
                raw_log = RawLog(
                    camera_id=camera_id,
                    frame_id=i+1,
                    plate_number=raw_data["plate_number"],
                    confidence=raw_data["confidence"],
                    processed_at=datetime.now() - timedelta(minutes=i*30)
                )
                session.add(raw_log)
                session.commit()
                raw_ids.append(raw_log.raw_id)
                print(f"✅ Created raw log: {raw_data['plate_number']} (ID: {raw_log.raw_id})")
            
            # Create test vehicle logs
            vehicle_logs_data = [
                {"plate_number": "TEST123", "toggle_mode": ToggleMode.ENTRY, "raw_ref": raw_ids[0]},
                {"plate_number": "TEST456", "toggle_mode": ToggleMode.EXIT, "raw_ref": raw_ids[1]},
                {"plate_number": "ABC123", "toggle_mode": ToggleMode.ENTRY, "raw_ref": raw_ids[2]},
                {"plate_number": "XYZ789", "toggle_mode": ToggleMode.EXIT, "raw_ref": raw_ids[3]}
            ]
            
            for log_data in vehicle_logs_data:
                vehicle_log = VehicleLog(
                    plate_number=log_data["plate_number"],
                    toggle_mode=log_data["toggle_mode"],
                    captured_at=datetime.now() - timedelta(hours=1),
                    raw_ref=log_data["raw_ref"]
                )
                session.add(vehicle_log)
                print(f"✅ Created vehicle log: {log_data['plate_number']} ({log_data['toggle_mode'].value})")
            
            session.commit()
            print("✅ Test data populated successfully")
            return True
            
    except Exception as e:
        print(f"❌ Failed to populate test data: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search():
    """Test the search functionality"""
    try:
        print("🔍 Testing search functionality...")
        
        # Initialize database
        db = get_database()
        
        # Test search with context manager like SearchThread does
        with db.get_session() as session:
            # Test basic query with joins
            query = session.query(VehicleLog).join(RawLog).join(Camera)
            print("✅ Basic query with joins works")
            
            # Test search for plates containing "TEST"
            plate_query = query.filter(VehicleLog.plate_number.ilike('%TEST%'))
            plate_results = plate_query.limit(1000).all()
            print(f"🔍 Found {len(plate_results)} plates containing 'TEST'")
            
            # Test search for ENTRY mode
            entry_query = query.filter(VehicleLog.toggle_mode == ToggleMode.ENTRY)
            entry_results = entry_query.limit(1000).all()
            print(f"🔍 Found {len(entry_results)} ENTRY records")
            
            # Test search for EXIT mode
            exit_query = query.filter(VehicleLog.toggle_mode == ToggleMode.EXIT)
            exit_results = exit_query.limit(1000).all()
            print(f"🔍 Found {len(exit_results)} EXIT records")
            
            # Test date range search
            date_from = datetime.now() - timedelta(days=2)
            date_to = datetime.now()
            
            date_query = query.filter(
                and_(
                    VehicleLog.captured_at >= date_from,
                    VehicleLog.captured_at <= date_to
                )
            )
            date_results = date_query.limit(1000).all()
            print(f"📅 Found {len(date_results)} records in date range")
            
            print("✅ All search tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("🧪 Database Population and Search Test")
    print("=" * 40)
    
    # Populate test data
    if populate_test_data():
        # Test search functionality
        test_search()

if __name__ == "__main__":
    main()
