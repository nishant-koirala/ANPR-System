#!/usr/bin/env python3
"""
Script to check database schema and verify the image_path column in vehicle_log table
"""

import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def check_database():
    """Check database schema and verify image_path column"""
    try:
        print("🔍 Checking database schema...")
        
        # Database file path
        db_path = os.path.join(os.path.dirname(__file__), 'anpr_database.db')
        abs_db_path = os.path.abspath(db_path)
        print(f"📁 Database file path: {abs_db_path}")
        
        # Check if database file exists
        if os.path.exists(abs_db_path):
            print("✅ Database file exists")
        else:
            print("❌ Database file does not exist")
            return False
            
        # Connect to database
        conn = sqlite3.connect(abs_db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n📋 Database tables:")
        for table in tables:
            print(f"  - {table[0]}")
            
        # Check if vehicle_log table exists
        vehicle_log_exists = any(table[0] == 'vehicle_log' for table in tables)
        if vehicle_log_exists:
            print("\n✅ vehicle_log table exists")
        else:
            print("\n❌ vehicle_log table does not exist")
            return False
            
        # Check vehicle_log table schema
        cursor.execute("PRAGMA table_info(vehicle_log)")
        columns = cursor.fetchall()
        
        print(f"\n📋 Vehicle log table columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
            
        # Check if image_path column exists
        image_path_exists = any(col[1] == 'image_path' for col in columns)
        
        if image_path_exists:
            print("\n✅ SUCCESS: image_path column exists in vehicle_log table")
            return True
        else:
            print("\n❌ FAILURE: image_path column is missing from vehicle_log table")
            print("\n🔄 Attempting to add image_path column...")
            
            try:
                cursor.execute("ALTER TABLE vehicle_log ADD COLUMN image_path VARCHAR(255)")
                conn.commit()
                print("✅ image_path column added successfully")
                return True
            except Exception as e:
                print(f"❌ Failed to add image_path column: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = check_database()
    if not success:
        sys.exit(1)
    else:
        print("\n🎉 Database check completed successfully!")
