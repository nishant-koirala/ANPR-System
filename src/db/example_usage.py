"""
Example usage of the ANPR Database System
Demonstrates how to use the Phase 1 core logging functionality
"""

import logging
from datetime import datetime
from src.db import Database, get_database
from src.db.models import ToggleMode
from src.db.toggle_manager import ToggleManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize the database and create tables"""
    db = get_database()
    db.create_tables()
    logger.info("Database initialized and tables created")
    return db


def example_raw_detection_logging(db: Database):
    """Example of logging raw detections from YOLO/OCR"""
    
    # Get or create camera
    camera_id = db.get_or_create_camera("CAM_001", "Main Entrance")
    
    # Simulate raw detections
    detections = [
        {"frame_id": "frame_001", "plate_text": "BA12PA3456", "confidence": 0.85},
        {"frame_id": "frame_002", "plate_text": "BA12PA3456", "confidence": 0.82},  # Same plate, different frame
        {"frame_id": "frame_003", "plate_text": "GA01AA1234", "confidence": 0.91},
        {"frame_id": "frame_004", "plate_text": "BA12PA3456", "confidence": 0.78},  # Low confidence
        {"frame_id": "frame_005", "plate_text": "KA02BB5678", "confidence": 0.89},
    ]
    
    raw_log_ids = []
    for detection in detections:
        raw_id = db.add_raw_log(
            camera_id=camera_id,
            frame_id=detection["frame_id"],
            plate_text=detection["plate_text"],
            confidence=detection["confidence"],
            bbox_coords=(100, 50, 200, 100),  # Example bounding box
            processing_time=0.15
        )
        raw_log_ids.append(raw_id)
        logger.info(f"Raw detection logged: {detection['plate_text']} (ID: {raw_id})")
    
    return raw_log_ids


def example_toggle_mode_processing(db: Database, raw_log_ids: list):
    """Example of processing detections with toggle mode logic"""
    
    # Initialize toggle manager
    toggle_manager = ToggleManager(
        database=db,
        min_confidence=0.8,  # Only process detections with 80%+ confidence
        cooldown_minutes=5   # 5-minute cooldown between same plate detections
    )
    
    # Simulate processing the raw detections
    test_detections = [
        {"plate": "BA12PA3456", "confidence": 0.85, "raw_id": raw_log_ids[0]},
        {"plate": "BA12PA3456", "confidence": 0.82, "raw_id": raw_log_ids[1]},  # Should be ignored (recent)
        {"plate": "GA01AA1234", "confidence": 0.91, "raw_id": raw_log_ids[2]},
        {"plate": "BA12PA3456", "confidence": 0.78, "raw_id": raw_log_ids[3]},  # Should be ignored (low confidence)
        {"plate": "KA02BB5678", "confidence": 0.89, "raw_id": raw_log_ids[4]},
    ]
    
    for detection in test_detections:
        log_id = toggle_manager.log_vehicle_detection(
            plate_text=detection["plate"],
            confidence=detection["confidence"],
            raw_log_id=detection["raw_id"],
            camera_id=1,
            session_id="session_001"
        )
        
        if log_id:
            logger.info(f"Vehicle logged with toggle mode: {detection['plate']} (log_id: {log_id})")
        else:
            logger.info(f"Detection ignored: {detection['plate']}")


def example_vehicle_status_queries(db: Database):
    """Example of querying vehicle status and logs"""
    
    toggle_manager = ToggleManager(database=db)
    
    # Check status of specific vehicles
    test_plates = ["BA12PA3456", "GA01AA1234", "KA02BB5678"]
    
    for plate in test_plates:
        status = toggle_manager.get_vehicle_status(plate)
        logger.info(f"Vehicle {plate} status: {status}")
    
    # Query recent vehicle logs
    with db.get_session() as session:
        from src.db.models import VehicleLog
        
        recent_logs = session.query(VehicleLog)\
                            .order_by(VehicleLog.captured_at.desc())\
                            .limit(10)\
                            .all()
        
        logger.info("Recent vehicle logs:")
        for log in recent_logs:
            logger.info(f"  {log.plate_number} - {log.toggle_mode.value} at {log.captured_at}")


def simulate_entry_exit_cycle(db: Database):
    """Simulate a complete entry-exit cycle for a vehicle"""
    
    toggle_manager = ToggleManager(database=db, cooldown_minutes=1)  # Short cooldown for demo
    camera_id = db.get_or_create_camera("CAM_001", "Main Entrance")
    
    plate = "TEST123"
    
    # Simulate ENTRY
    logger.info(f"\n--- Simulating ENTRY for {plate} ---")
    raw_id_entry = db.add_raw_log(
        camera_id=camera_id,
        frame_id="entry_frame",
        plate_text=plate,
        confidence=0.92
    )
    
    log_id_entry = toggle_manager.log_vehicle_detection(
        plate_text=plate,
        confidence=0.92,
        raw_log_id=raw_id_entry,
        camera_id=camera_id
    )
    
    # Wait a moment and simulate EXIT
    import time
    time.sleep(2)  # Short wait for demo
    
    logger.info(f"\n--- Simulating EXIT for {plate} ---")
    raw_id_exit = db.add_raw_log(
        camera_id=camera_id,
        frame_id="exit_frame",
        plate_text=plate,
        confidence=0.88
    )
    
    log_id_exit = toggle_manager.log_vehicle_detection(
        plate_text=plate,
        confidence=0.88,
        raw_log_id=raw_id_exit,
        camera_id=camera_id
    )
    
    # Check final status
    status = toggle_manager.get_vehicle_status(plate)
    logger.info(f"Final status for {plate}: {status}")


def main():
    """Main example function"""
    logger.info("=== ANPR Database System Example ===")
    
    try:
        # Initialize database
        db = initialize_database()
        
        # Example 1: Raw detection logging
        logger.info("\n1. Raw Detection Logging Example")
        raw_log_ids = example_raw_detection_logging(db)
        
        # Example 2: Toggle mode processing
        logger.info("\n2. Toggle Mode Processing Example")
        example_toggle_mode_processing(db, raw_log_ids)
        
        # Example 3: Vehicle status queries
        logger.info("\n3. Vehicle Status Queries Example")
        example_vehicle_status_queries(db)
        
        # Example 4: Complete entry-exit cycle
        logger.info("\n4. Entry-Exit Cycle Simulation")
        simulate_entry_exit_cycle(db)
        
        logger.info("\n=== Example completed successfully ===")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise
    finally:
        # Clean up
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    main()
