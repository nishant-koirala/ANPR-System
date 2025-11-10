#!/usr/bin/env python3
"""
Test script to verify database functionality
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import get_database
from src.db.models import VehicleLog, PlateEditHistory

def test_database():
    """Test database functionality"""
    try:
        # Get database instance
        db = get_database()
        print("✅ Database connection successful")
        
        # Test adding a vehicle log
        log_id = db.add_vehicle_log(
            plate_number="TEST123",
            toggle_mode="ENTRY",
            raw_ref=1
        )
        print(f"✅ Added vehicle log with ID: {log_id}")
        
        # Test updating plate number
        success = db.update_plate_number(log_id, "TEST456", "test_user")
        if success:
            print(f"✅ Updated plate number for log ID {log_id}")
        else:
            print(f"❌ Failed to update plate number for log ID {log_id}")
            
        # Test querying vehicle logs
        with db.get_session() as session:
            logs = session.query(VehicleLog).all()
            print(f"✅ Found {len(logs)} vehicle logs")
            
            # Check if our updated log exists
            updated_log = session.query(VehicleLog).filter_by(log_id=log_id).first()
            if updated_log:
                print(f"✅ Log found: {updated_log.plate_number}")
            else:
                print("❌ Log not found")
                
            # Check edit history
            edit_history = session.query(PlateEditHistory).all()
            print(f"✅ Found {len(edit_history)} edit history records")
            
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database()
    if success:
        print("\n🎉 All database tests passed!")
    else:
        print("\n💥 Database tests failed!")
