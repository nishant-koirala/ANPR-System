-- ANPR System Database Schema - Phase 1: Core Logging
-- This SQL file contains the raw SQL schema for reference and manual setup

-- Create cameras table
CREATE TABLE IF NOT EXISTS cameras (
    camera_id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_name VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create vehicles table
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number VARCHAR(20) UNIQUE NOT NULL,
    vehicle_type VARCHAR(50),
    owner_info TEXT,
    is_blacklisted INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create raw_logs table (every detection from camera/YOLO before filtering)
CREATE TABLE IF NOT EXISTS raw_logs (
    raw_id BIGINT PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL,
    frame_id VARCHAR(50) NOT NULL,
    plate_text VARCHAR(20) NOT NULL,
    confidence REAL NOT NULL,
    captured_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    image_path VARCHAR(255),
    bbox_x REAL,
    bbox_y REAL,
    bbox_width REAL,
    bbox_height REAL,
    processing_time REAL,
    FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
);

-- Create vehicle_log table (filtered, toggled entry/exit records)
CREATE TABLE IF NOT EXISTS vehicle_log (
    log_id BIGINT PRIMARY KEY AUTOINCREMENT,
    plate_number VARCHAR(20) NOT NULL,
    vehicle_id INTEGER,
    toggle_mode TEXT NOT NULL CHECK (toggle_mode IN ('ENTRY', 'EXIT')),
    captured_at DATETIME NOT NULL,
    raw_ref BIGINT NOT NULL,
    session_id VARCHAR(50),
    duration_minutes INTEGER,
    location_info VARCHAR(255),
    notes TEXT,
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    FOREIGN KEY (raw_ref) REFERENCES raw_logs(raw_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_raw_logs_camera_id ON raw_logs(camera_id);
CREATE INDEX IF NOT EXISTS idx_raw_logs_frame_id ON raw_logs(frame_id);
CREATE INDEX IF NOT EXISTS idx_raw_logs_plate_text ON raw_logs(plate_text);
CREATE INDEX IF NOT EXISTS idx_raw_logs_captured_at ON raw_logs(captured_at);
CREATE INDEX IF NOT EXISTS idx_raw_logs_camera_time ON raw_logs(camera_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_raw_logs_plate_time ON raw_logs(plate_text, captured_at);

CREATE INDEX IF NOT EXISTS idx_vehicle_log_plate_number ON vehicle_log(plate_number);
CREATE INDEX IF NOT EXISTS idx_vehicle_log_vehicle_id ON vehicle_log(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_log_toggle_mode ON vehicle_log(toggle_mode);
CREATE INDEX IF NOT EXISTS idx_vehicle_log_captured_at ON vehicle_log(captured_at);
CREATE INDEX IF NOT EXISTS idx_vehicle_log_plate_toggle ON vehicle_log(plate_number, toggle_mode);
CREATE INDEX IF NOT EXISTS idx_vehicle_log_time_toggle ON vehicle_log(captured_at, toggle_mode);

CREATE INDEX IF NOT EXISTS idx_vehicles_plate_number ON vehicles(plate_number);

-- Insert sample camera data
INSERT OR IGNORE INTO cameras (camera_name, location) VALUES 
('CAM_001', 'Main Entrance'),
('CAM_002', 'Exit Gate'),
('CAM_003', 'Parking Area A'),
('CAM_004', 'Parking Area B');

-- Create views for common queries
CREATE VIEW IF NOT EXISTS v_current_vehicle_status AS
SELECT 
    v.plate_number,
    v.vehicle_type,
    vl.toggle_mode as last_action,
    vl.captured_at as last_seen,
    c.camera_name as last_camera,
    c.location as last_location,
    CASE 
        WHEN vl.toggle_mode = 'ENTRY' THEN 'INSIDE'
        WHEN vl.toggle_mode = 'EXIT' THEN 'OUTSIDE'
        ELSE 'UNKNOWN'
    END as current_status
FROM vehicles v
LEFT JOIN vehicle_log vl ON v.vehicle_id = vl.vehicle_id
LEFT JOIN raw_logs rl ON vl.raw_ref = rl.raw_id
LEFT JOIN cameras c ON rl.camera_id = c.camera_id
WHERE vl.log_id = (
    SELECT MAX(log_id) 
    FROM vehicle_log vl2 
    WHERE vl2.vehicle_id = v.vehicle_id
);

-- View for daily vehicle counts
CREATE VIEW IF NOT EXISTS v_daily_vehicle_counts AS
SELECT 
    DATE(captured_at) as date,
    toggle_mode,
    COUNT(*) as count
FROM vehicle_log
GROUP BY DATE(captured_at), toggle_mode
ORDER BY date DESC, toggle_mode;

-- View for vehicle session durations
CREATE VIEW IF NOT EXISTS v_vehicle_sessions AS
SELECT 
    entry.plate_number,
    entry.captured_at as entry_time,
    exit.captured_at as exit_time,
    exit.duration_minutes,
    CASE 
        WHEN exit.captured_at IS NULL THEN 'ONGOING'
        ELSE 'COMPLETED'
    END as session_status
FROM vehicle_log entry
LEFT JOIN vehicle_log exit ON (
    entry.plate_number = exit.plate_number 
    AND exit.toggle_mode = 'EXIT'
    AND exit.captured_at > entry.captured_at
    AND exit.log_id = (
        SELECT MIN(log_id) 
        FROM vehicle_log vl3 
        WHERE vl3.plate_number = entry.plate_number 
        AND vl3.toggle_mode = 'EXIT' 
        AND vl3.captured_at > entry.captured_at
    )
)
WHERE entry.toggle_mode = 'ENTRY'
ORDER BY entry.captured_at DESC;
