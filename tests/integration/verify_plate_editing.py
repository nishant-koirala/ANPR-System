#!/usr/bin/env python3
"""
Test script to verify plate number editing functionality with history tracking
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import get_database
from src.db.models import VehicleLog, PlateEditHistory

def test_plate_editing():
    """Test plate number editing functionality"""
    try:
        # Get database instance
        db = get_database()
        print("✅ Database connection successful")
        
        # Add a test vehicle log entry
        log_id = db.add_vehicle_log(
            plate_number="TEST999",
            toggle_mode="ENTRY",
            raw_ref=1,
            image_path="test_image.jpg"
        )
        print(f"✅ Added test vehicle log with ID: {log_id}")
        
        # Verify the log was added
        with db.get_session() as session:
            log = session.query(VehicleLog).filter_by(log_id=log_id).first()
            if log:
                print(f"✅ Verified log entry: {log.plate_number}")
            else:
                print("❌ Could not find the added log entry")
                return False
                
        # Test updating plate number (this should create edit history)
        success = db.update_plate_number(log_id, "TEST888", "test_user", "Testing edit functionality")
        if success:
            print(f"✅ Updated plate number for log ID {log_id}")
        else:
            print(f"❌ Failed to update plate number for log ID {log_id}")
            return False
            
        # Verify the update and check edit history
        with db.get_session() as session:
            # Check updated log
            updated_log = session.query(VehicleLog).filter_by(log_id=log_id).first()
            if updated_log and updated_log.plate_number == "TEST888":
                print(f"✅ Verified updated plate number: {updated_log.plate_number}")
            else:
                print("❌ Plate number was not updated correctly")
                return False
                
            # Check edit history
            edit_history = session.query(PlateEditHistory).filter_by(log_id=log_id).all()
            if len(edit_history) > 0:
                print(f"✅ Found {len(edit_history)} edit history records")
                for record in edit_history:
                    print(f"   - Edit ID: {record.edit_id}, Old: {record.old_plate_number}, New: {record.new_plate_number}, By: {record.edited_by}")
            else:
                print("❌ No edit history records found")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Plate editing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing plate number editing functionality...")
    success = test_plate_editing()
    if success:
        print("\n🎉 All plate editing tests passed!")
    else:
        print("\n💥 Plate editing tests failed!")
