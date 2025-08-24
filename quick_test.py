import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    print("Testing imports...")
    from src.db import Database, get_database
    print("✓ Database imports successful")
    
    print("Testing database creation...")
    db = get_database()
    db.create_tables()
    print("✓ Database tables created")
    
    print("Testing camera creation...")
    camera_id = db.get_or_create_camera("TEST_CAM", "Test Location")
    print(f"✓ Camera created with ID: {camera_id}")
    
    print("Testing raw log...")
    raw_id = db.add_raw_log(
        camera_id=camera_id,
        frame_id="test_frame",
        plate_text="TEST123",
        confidence=0.85
    )
    print(f"✓ Raw log created with ID: {raw_id}")
    
    print("\n🎉 Database setup successful!")
    print(f"Database file: {db.database_url}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
