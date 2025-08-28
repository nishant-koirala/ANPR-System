#!/usr/bin/env python3
"""
Database migration script to add image_path column to vehicle_log table
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.db.database import get_database
from sqlalchemy import text

def migrate_database():
    """Add image_path column to existing vehicle_log table"""
    try:
        print("🔄 Starting database migration...")
        
        # Get database instance
        db = get_database()
        print(f"✅ Database connected: {db.database_url}")
        
        # Add image_path column to vehicle_log table
        with db.get_session() as session:
            # SQLite ALTER TABLE syntax
            try:
                session.execute(text("ALTER TABLE vehicle_log ADD COLUMN image_path VARCHAR(255)"))
                session.commit()
                print("✅ image_path column added successfully to vehicle_log table")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("✅ image_path column already exists in vehicle_log table")
                else:
                    print(f"❌ Error adding column: {e}")
                    raise e
        
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate_database()
    if not success:
        sys.exit(1)
