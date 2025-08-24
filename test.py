# Test the database setup
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.db import Database, get_database
from src.db.models import ToggleMode
from src.db.toggle_manager import ToggleManager

# Initialize database
db = get_database()
db.create_tables()
print("✅ Database initialized successfully!")

# Test basic functionality
camera_id = db.get_or_create_camera("CAM_001", "Main Entrance")
raw_id = db.add_raw_log(camera_id, "frame_001", "BA12PA3456", 0.85)
print(f"✅ Test data created - Camera: {camera_id}, Raw Log: {raw_id}")