#!/usr/bin/env python3
"""
Script to check and update the database schema directly using SQLite
"""

import sqlite3
import os

def check_and_update_schema():
    """Check if image_path column exists and add it if missing"""
    try:
        print("🔍 Checking and updating database schema...")
        
        # Database file path
        db_path = os.path.join(os.path.dirname(__file__), 'anpr_database.db')
        abs_db_path = os.path.abspath(db_path)
        print(f"📁 Database file path: {abs_db_path}")
        
        # Connect to database
        conn = sqlite3.connect(abs_db_path)
        cursor = conn.cursor()
        
        # Check vehicle_log table schema
        cursor.execute("PRAGMA table_info(vehicle_log)")
        columns = cursor.fetchall()
        
        print(f"\n📋 Current vehicle_log table columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
            
        # Check if image_path column exists
        image_path_exists = any(col[1] == 'image_path' for col in columns)
        
        if image_path_exists:
            print("\n✅ SUCCESS: image_path column already exists in vehicle_log table")
        else:
            print("\n❌ image_path column is missing from vehicle_log table")
            print("\n🔄 Adding image_path column to vehicle_log table...")
            
            # Add the image_path column
            cursor.execute("ALTER TABLE vehicle_log ADD COLUMN image_path VARCHAR(255)")
            conn.commit()
            print("✅ image_path column added successfully!")
            
            # Verify the column was added
            cursor.execute("PRAGMA table_info(vehicle_log)")
            updated_columns = cursor.fetchall()
            
            print(f"\n📋 Updated vehicle_log table columns:")
            for col in updated_columns:
                print(f"  - {col[1]} ({col[2]})")
                
            # Check again if image_path column exists
            image_path_exists = any(col[1] == 'image_path' for col in updated_columns)
            if image_path_exists:
                print("\n✅ VERIFICATION: image_path column now exists in vehicle_log table")
            else:
                print("\n❌ VERIFICATION FAILED: image_path column still missing")
                
        return True
        
    except Exception as e:
        print(f"❌ Schema check/update failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = check_and_update_schema()
    if success:
        print("\n🎉 Schema check and update completed successfully!")
    else:
        print("\n💥 Schema check and update failed!")
        exit(1)
