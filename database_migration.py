#!/usr/bin/env python3
"""
Database Migration Script for ANPR System
Enhanced with secure password storage, normalized image table, 
and robust audit trail handling.
"""

import sys
import os
import sqlite3
from datetime import datetime
import bcrypt

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def backup_database(db_path):
    """Create a backup of the current database"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Failed to backup database: {e}")
        return None

def run_migration():
    """Run the database migration"""
    print("🔄 ANPR Database Migration")
    print("=" * 40)

    db_path = None
    possible_paths = ['anpr_database.db', os.path.join('src', 'anpr_database.db')]

    for path in possible_paths:
        if os.path.exists(path):
            db_path = os.path.abspath(path)
            break

    if not db_path:
        print("❌ Database file not found. Creating new database with enhanced schema...")
        create_new_database()
        return

    print(f"📊 Found database: {db_path}")

    backup_path = backup_database(db_path)
    if not backup_path:
        print("⚠️ Proceeding without backup (risky!)")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("🚀 Applying migrations...")
        apply_migrations(cursor, conn)
        print("✅ Migration completed successfully!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if backup_path:
            print(f"💡 Restore from backup: {backup_path}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def apply_migrations(cursor, conn):
    """Apply migrations with normalized schema"""

    # 1. Users table
    print("1️⃣ Creating users table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role VARCHAR(20) NOT NULL DEFAULT 'OPERATOR',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    """)
    print("   ✅ Users table ready")

    # 2. Plate Images table
    print("2️⃣ Creating plate_images table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plate_images (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER NOT NULL,
            log_type TEXT NOT NULL CHECK(log_type IN ('RAW', 'VEHICLE')),
            image_path VARCHAR(500),
            thumbnail_path VARCHAR(500),
            width INTEGER,
            height INTEGER,
            size INTEGER,
            FOREIGN KEY (log_id) REFERENCES vehicle_log(log_id) ON DELETE CASCADE
        )
    """)
    print("   ✅ Plate images table ready")

    # 3. Vehicle log table edits
    print("3️⃣ Adding editing fields to vehicle_log...")
    editing_fields = [
        "ALTER TABLE vehicle_log ADD COLUMN original_plate_number VARCHAR(20)",
        "ALTER TABLE vehicle_log ADD COLUMN is_edited BOOLEAN DEFAULT 0",
        "ALTER TABLE vehicle_log ADD COLUMN edited_by INTEGER",
        "ALTER TABLE vehicle_log ADD COLUMN edited_at DATETIME",
        "ALTER TABLE vehicle_log ADD COLUMN edit_reason TEXT"
    ]
    for field in editing_fields:
        try:
            cursor.execute(field)
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ℹ️ Field already exists")
            else:
                raise
    print("   ✅ Editing fields added")

    # 4. Audit trail table
    print("4️⃣ Creating audit trail table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plate_edit_history (
            edit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER NOT NULL,
            old_plate_number VARCHAR(20) NOT NULL,
            new_plate_number VARCHAR(20) NOT NULL,
            edited_by INTEGER NOT NULL,
            editor_role VARCHAR(20),
            edited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            edit_reason TEXT,
            ip_address VARCHAR(45),
            user_agent TEXT,
            FOREIGN KEY (log_id) REFERENCES vehicle_log(log_id),
            FOREIGN KEY (edited_by) REFERENCES users(user_id)
        )
    """)
    print("   ✅ Audit trail table ready")

    # 5. Indexes
    print("5️⃣ Creating performance indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_vehicle_log_edited ON vehicle_log(is_edited)",
        "CREATE INDEX IF NOT EXISTS idx_vehicle_log_editor ON vehicle_log(edited_by)",
        "CREATE INDEX IF NOT EXISTS idx_edit_history_log ON plate_edit_history(log_id)",
        "CREATE INDEX IF NOT EXISTS idx_edit_history_user ON plate_edit_history(edited_by)",
        "CREATE INDEX IF NOT EXISTS idx_edit_history_date ON plate_edit_history(edited_at)",
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
    ]
    for index_sql in indexes:
        cursor.execute(index_sql)
    print("   ✅ Performance indexes created")

    # 6. Default admin user
    print("6️⃣ Creating default admin user...")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    if user_count == 0:
        default_password = b"admin123"
        password_hash = bcrypt.hashpw(default_password, bcrypt.gensalt()).decode()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("admin", "admin@anpr.local", password_hash, "System Administrator", "ADMIN"))
        print("   ✅ Default admin user created (username: admin, password: admin123)")
        print("   ⚠️ IMPORTANT: Change this password immediately!")
    else:
        print("   ℹ️ Admin user already exists")

    conn.commit()
    print("💾 All changes committed to database")

def create_new_database():
    """Create new database with enhanced schema"""
    print("🆕 Creating fresh database...")
    conn = sqlite3.connect("anpr_database.db")
    cursor = conn.cursor()
    apply_migrations(cursor, conn)
    conn.close()
    print("✅ New database created successfully")

if __name__ == "__main__":
    try:
        run_migration()
        print("\n" + "="*50)
        print("🎉 DATABASE MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*50)
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        sys.exit(1)
