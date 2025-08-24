"""
Toggle Mode Manager for ANPR System
Handles the logic for determining ENTRY/EXIT toggle states based on vehicle detections
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import difflib

from .database import Database, get_database
from .models import ToggleMode, VehicleLog

logger = logging.getLogger(__name__)


class ToggleDecision(Enum):
    """Decision outcomes for toggle mode logic"""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    IGNORE = "IGNORE"  # Skip logging (too frequent, low confidence, etc.)


class ToggleManager:
    """
    Manages toggle mode logic for vehicle entry/exit detection
    Implements intelligent filtering to avoid duplicate entries
    """
    
    def __init__(self, database: Optional[Database] = None, 
                 min_confidence: float = 0.7,
                 cooldown_minutes: int = 5,
                 exit_similarity_threshold: float = 0.8):
        """
        Initialize toggle manager
        
        Args:
            database: Database instance
            min_confidence: Minimum confidence threshold for processing
            cooldown_minutes: Minimum time between same plate detections
            exit_similarity_threshold: Minimum similarity (0.8 = 80%) for EXIT matching
        """
        self.db = database or get_database()
        self.min_confidence = min_confidence
        self.cooldown_minutes = cooldown_minutes
        self.exit_similarity_threshold = exit_similarity_threshold
        
        # Cache for recent detections to avoid database queries
        self._recent_detections: Dict[str, Dict[str, Any]] = {}
    
    def calculate_plate_similarity(self, plate1: str, plate2: str) -> float:
        """
        Calculate similarity between two plate numbers using sequence matching
        
        Args:
            plate1: First plate number
            plate2: Second plate number
            
        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        # Normalize plates - remove spaces and convert to uppercase
        p1 = plate1.replace(' ', '').upper()
        p2 = plate2.replace(' ', '').upper()
        
        # Use difflib for sequence matching
        similarity = difflib.SequenceMatcher(None, p1, p2).ratio()
        
        logger.debug(f"Plate similarity: '{plate1}' vs '{plate2}' = {similarity:.2f}")
        return similarity
    
    def find_similar_entry_plate(self, plate_text: str) -> Optional[dict]:
        """
        Find the most recent ENTRY log with similar plate number
        
        Args:
            plate_text: Current detected plate
            
        Returns:
            Dictionary with entry log data if similar entry found, None otherwise
        """
        try:
            with self.db.get_session() as session:
                # Get recent ENTRY logs from last 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                entry_logs = session.query(VehicleLog).filter(
                    VehicleLog.toggle_mode == ToggleMode.ENTRY,
                    VehicleLog.captured_at >= cutoff_time
                ).order_by(VehicleLog.captured_at.desc()).limit(50).all()
                
                # Find best matching plate
                best_match_data = None
                best_similarity = 0.0
                
                for log in entry_logs:
                    similarity = self.calculate_plate_similarity(plate_text, log.plate_number)
                    if similarity >= self.exit_similarity_threshold and similarity > best_similarity:
                        best_similarity = similarity
                        best_match_data = {
                            'plate_number': log.plate_number,
                            'captured_at': log.captured_at,
                            'log_id': log.log_id
                        }
                
                if best_match_data:
                    logger.info(f"Found similar ENTRY plate: '{best_match_data['plate_number']}' "
                              f"(similarity: {best_similarity:.2f}) for EXIT: '{plate_text}'")
                
                return best_match_data
                
        except Exception as e:
            logger.error(f"Error finding similar entry plate: {e}")
            return None
    
    def process_detection(self, plate_text: str, confidence: float, 
                         raw_log_id: int, camera_id: int) -> ToggleDecision:
        """
        Process a new plate detection and determine toggle action
        
        Args:
            plate_text: Detected plate number (cleaned)
            confidence: Detection confidence
            raw_log_id: Reference to raw log entry
            camera_id: Camera that made the detection
            
        Returns:
            ToggleDecision indicating what action to take
        """
        # Filter by confidence threshold
        if confidence < self.min_confidence:
            logger.debug(f"Low confidence detection ignored: {plate_text} ({confidence})")
            return ToggleDecision.IGNORE
        
        # Check recent detections cache first
        if self._is_recent_detection(plate_text):
            logger.debug(f"Recent detection ignored: {plate_text}")
            return ToggleDecision.IGNORE
        
        # Get last vehicle log from database (exact match)
        last_log_data = self.db.get_last_vehicle_log_data(plate_text)
        
        # Determine toggle mode
        if last_log_data is None:
            # Check if this could be an EXIT for a similar plate (80% match)
            similar_entry = self.find_similar_entry_plate(plate_text)
            if similar_entry:
                # Check cooldown for the similar plate
                time_diff = datetime.utcnow() - similar_entry['captured_at']
                if time_diff >= timedelta(minutes=self.cooldown_minutes):
                    decision = ToggleDecision.EXIT
                    logger.info(f"EXIT matched to similar ENTRY: '{similar_entry['plate_number']}' -> '{plate_text}'")
                else:
                    decision = ToggleDecision.IGNORE
            else:
                # First time seeing this vehicle - assume ENTRY
                decision = ToggleDecision.ENTRY
        else:
            # Check time since last detection
            time_diff = datetime.utcnow() - last_log_data['captured_at']
            
            if time_diff < timedelta(minutes=self.cooldown_minutes):
                # Too recent, ignore
                decision = ToggleDecision.IGNORE
            else:
                # Toggle the mode
                if last_log_data['toggle_mode'] == ToggleMode.ENTRY:
                    decision = ToggleDecision.EXIT
                else:
                    decision = ToggleDecision.ENTRY
        
        # Update cache
        if decision != ToggleDecision.IGNORE:
            self._update_cache(plate_text, decision)
        
        logger.info(f"Toggle decision for {plate_text}: {decision.value}")
        return decision
    
    def log_vehicle_detection(self, plate_text: str, confidence: float,
                            raw_log_id: int, camera_id: int,
                            session_id: Optional[str] = None) -> Optional[int]:
        """
        Process detection and log to vehicle_log if appropriate
        
        Args:
            plate_text: Detected plate number
            confidence: Detection confidence
            raw_log_id: Reference to raw log entry
            camera_id: Camera ID
            session_id: Optional session identifier
            
        Returns:
            log_id if logged, None if ignored
        """
        decision = self.process_detection(plate_text, confidence, raw_log_id, camera_id)
        
        if decision == ToggleDecision.IGNORE:
            return None
        
        # Convert decision to ToggleMode
        toggle_mode = ToggleMode.ENTRY if decision == ToggleDecision.ENTRY else ToggleMode.EXIT
        
        # Get or create vehicle record
        vehicle_id = self.db.get_or_create_vehicle(plate_text)
        
        # Calculate duration for EXIT records
        duration_minutes = None
        if toggle_mode == ToggleMode.EXIT:
            last_entry_time = self._get_last_entry_time(plate_text)
            if last_entry_time:
                time_diff = datetime.utcnow() - last_entry_time
                duration_minutes = int(time_diff.total_seconds() / 60)
        
        # Create vehicle log entry with duration included
        log_id = self.db.add_vehicle_log(
            plate_number=plate_text,
            toggle_mode=toggle_mode,
            raw_ref=raw_log_id,
            vehicle_id=vehicle_id,
            session_id=session_id,
            duration_minutes=duration_minutes
        )
        
        logger.info(f"Vehicle logged: {plate_text} - {toggle_mode.value} (log_id: {log_id})")
        return log_id
    
    def _is_recent_detection(self, plate_text: str) -> bool:
        """Check if plate was recently detected using cache"""
        if plate_text not in self._recent_detections:
            return False
        
        last_time = self._recent_detections[plate_text]['timestamp']
        time_diff = datetime.utcnow() - last_time
        
        return time_diff < timedelta(minutes=self.cooldown_minutes)
    
    def _update_cache(self, plate_text: str, decision: ToggleDecision):
        """Update recent detections cache"""
        self._recent_detections[plate_text] = {
            'timestamp': datetime.utcnow(),
            'decision': decision
        }
        
        # Clean old entries from cache
        self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Remove old entries from cache"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.cooldown_minutes * 2)
        
        plates_to_remove = [
            plate for plate, data in self._recent_detections.items()
            if data['timestamp'] < cutoff_time
        ]
        
        for plate in plates_to_remove:
            del self._recent_detections[plate]
    
    def _get_last_entry_time(self, plate_text: str) -> Optional[datetime]:
        """Get the timestamp of the last ENTRY log for calculating duration"""
        with self.db.get_session() as session:
            result = session.query(VehicleLog.captured_at)\
                           .filter_by(plate_number=plate_text, toggle_mode=ToggleMode.ENTRY)\
                           .order_by(VehicleLog.captured_at.desc())\
                           .first()
            return result[0] if result else None
    
    def get_vehicle_status(self, plate_text: str) -> Dict[str, Any]:
        """
        Get current status of a vehicle
        
        Args:
            plate_text: Vehicle plate number
            
        Returns:
            Dictionary with vehicle status information
        """
        last_log = self.db.get_last_vehicle_log(plate_text)
        
        if not last_log:
            return {
                'status': 'UNKNOWN',
                'last_seen': None,
                'current_location': None
            }
        
        status = 'INSIDE' if last_log.toggle_mode == ToggleMode.ENTRY else 'OUTSIDE'
        
        return {
            'status': status,
            'last_seen': last_log.captured_at,
            'current_location': last_log.location_info,
            'last_toggle': last_log.toggle_mode.value
        }
