#!/usr/bin/env python3
"""
Script to verify that the image_path column was added to the vehicle_log table
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import get_database
from sqlalchemy import text

def verify_migration():
    """Check if image_path column exists in vehicle_log table"""
    try:
        print("🔍 Verifying database migration...")
        
        # Get database instance
        db = get_database()
        print(f"✅ Database connected: {db.database_url}")
        
        # Check if database file exists
        db_file = db.database_url.replace('sqlite:///', '')
        print(f"📁 Database file path: {db_file}")
        if os.path.exists(db_file):
            print("✅ Database file exists")
        else:
            print("❌ Database file does not exist")
            return False
        
        # Check table schema
        with db.get_session() as session:
            result = session.execute(text("PRAGMA table_info(vehicle_log)"))
            columns = result.fetchall()
            
            print("\n📋 Vehicle log table columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Check if image_path column exists
            image_path_exists = any(col[1] == 'image_path' for col in columns)
            
            if image_path_exists:
                print("\n✅ SUCCESS: image_path column exists in vehicle_log table")
                return True
            else:
                print("\n❌ FAILURE: image_path column is missing from vehicle_log table")
                return False
                
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_migration()
    if not success:
        sys.exit(1)
