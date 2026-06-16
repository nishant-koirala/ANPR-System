"""
Toggle Mode Manager for ANPR System
Handles the logic for determining ENTRY/EXIT toggle states based on vehicle detections
"""

import logging
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, Any, Optional
from enum import Enum

from src.db.database import Database, get_database
from src.db.models import VehicleLog, ToggleMode
from src.db.special_vehicles_db import SpecialVehiclesDB

logger = logging.getLogger(__name__)

# Email alert imports
try:
    from src.alerts.email_sender import EmailAlertSender
    from config.settings import (EMAIL_ENABLED, SMTP_SERVER, SMTP_PORT,
                                 EMAIL_SENDER, EMAIL_APP_PASSWORD)
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logger.warning("Email alert system not available")


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
        
        # Initialize special vehicles database
        try:
            self.special_db = SpecialVehiclesDB(self.db.get_session)
        except Exception as e:
            logger.warning(f"Special vehicles database not available: {e}")
            self.special_db = None
        
        # Initialize email alert sender
        self.email_sender = None
        if EMAIL_AVAILABLE and EMAIL_ENABLED:
            try:
                self.email_sender = EmailAlertSender(
                    smtp_server=SMTP_SERVER,
                    smtp_port=SMTP_PORT,
                    sender_email=EMAIL_SENDER,
                    sender_password=EMAIL_APP_PASSWORD
                )
                logger.info("✅ Email alert system initialized")
            except Exception as e:
                logger.warning(f"Could not initialize email sender: {e}")
        
        # Cache for recent detections to avoid database queries
        self._recent_detections: Dict[str, Dict[str, Any]] = {}
        
        # Store last stolen vehicle alert for UI pickup
        self._last_stolen_alert = None
    
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
        similarity = SequenceMatcher(None, p1, p2).ratio()
        
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
                            session_id: Optional[str] = None,
                            image_data: Optional[Dict] = None) -> Optional[int]:
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
        duration_hours = None
        amount = None
        if toggle_mode == ToggleMode.EXIT:
            last_entry_time = self._get_last_entry_time(plate_text)
            if last_entry_time:
                time_diff = datetime.utcnow() - last_entry_time
                duration_minutes = int(time_diff.total_seconds() / 60)
                duration_hours = round(duration_minutes / 60.0, 2)  # Convert to hours with 2 decimal places
                
                # Calculate amount based on hourly rate
                from config.settings import PARKING_HOURLY_RATE, MINIMUM_CHARGE_HOURS
                charge_hours = max(duration_hours, MINIMUM_CHARGE_HOURS)  # Minimum 1 hour charge
                amount = round(charge_hours * PARKING_HOURLY_RATE, 2)
        
        # Create vehicle log entry with duration and image data included
        log_id = self.db.add_vehicle_log(
            plate_number=plate_text,
            toggle_mode=toggle_mode,
            raw_ref=raw_log_id,
            vehicle_id=vehicle_id,
            session_id=session_id,
            duration_minutes=duration_minutes,
            duration_hours=duration_hours,
            amount=amount,
            image_data=image_data
        )
        
        logger.info(f"Vehicle logged: {plate_text} - {toggle_mode.value} (log_id: {log_id})")
        
        # Check if this is a stolen vehicle
        self._check_stolen_vehicle(plate_text, raw_log_id)
        
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
    
    def _check_stolen_vehicle(self, plate_text: str, raw_log_id: int):
        """
        Check if detected plate is a stolen vehicle and log alert
        
        Args:
            plate_text: Detected plate number
            raw_log_id: Raw log ID for reference
        """
        if not self.special_db:
            logger.debug("Special vehicles DB not available")
            return
        
        try:
            logger.debug(f"Checking if {plate_text} is stolen...")
            # Check if this plate is in stolen vehicles database
            stolen_vehicle = self.special_db.check_if_stolen(plate_text)
            logger.debug(f"Stolen vehicle check result: {stolen_vehicle}")
            
            if stolen_vehicle:
                # Check alert cooldown to avoid spam
                config = self.special_db.get_alert_config()
                cooldown_minutes = config.alert_cooldown_minutes if config else 5
                
                if self.special_db.check_alert_cooldown(stolen_vehicle.id, cooldown_minutes):
                    # Log the alert
                    alert = self.special_db.log_stolen_vehicle_alert(
                        stolen_vehicle_id=stolen_vehicle.id,
                        raw_log_id=raw_log_id,
                        alert_sent_dashboard=True
                    )
                    
                    if alert:
                        logger.warning(f"🚨 STOLEN VEHICLE DETECTED: {plate_text} (Owner: {stolen_vehicle.owner_name})")
                        
                        # Store alert data for UI to pick up
                        self._last_stolen_alert = {
                            'plate_number': plate_text,
                            'owner_name': stolen_vehicle.owner_name or 'Unknown',
                            'vehicle_type': stolen_vehicle.vehicle_type or 'Unknown',
                            'reported_date': stolen_vehicle.reported_date.strftime('%Y-%m-%d') if stolen_vehicle.reported_date else 'Unknown',
                            'alert_id': alert.id,
                            'timestamp': datetime.utcnow()
                        }
                        
                        # Send email alert if enabled
                        if stolen_vehicle.enable_email_alert and stolen_vehicle.email_recipients:
                            self._send_email_alert(stolen_vehicle, plate_text, raw_log_id)
                else:
                    logger.info(f"Stolen vehicle {plate_text} detected but alert in cooldown period")
        except Exception as e:
            logger.error(f"Error checking stolen vehicle: {e}")
    
    def _send_email_alert(self, stolen_vehicle, plate_text: str, raw_log_id: int):
        """
        Send email alert for stolen vehicle detection
        
        Args:
            stolen_vehicle: StolenVehicle object
            plate_text: Detected plate number
            raw_log_id: Raw log ID
        """
        if not self.email_sender:
            logger.debug("Email sender not initialized")
            return
        
        try:
            # Parse email recipients (comma or newline separated)
            recipients = []
            if stolen_vehicle.email_recipients:
                for email in stolen_vehicle.email_recipients.replace('\n', ',').split(','):
                    email = email.strip()
                    if email:
                        recipients.append(email)
            
            if not recipients:
                logger.warning("No email recipients configured for stolen vehicle")
                return
            
            # Get plate image path if available
            plate_image_path = None
            try:
                with self.db.get_session() as session:
                    from src.db.models import RawLog
                    raw_log = session.query(RawLog).filter(RawLog.raw_id == raw_log_id).first()
                    if raw_log and raw_log.plate_image_path:
                        plate_image_path = raw_log.plate_image_path
            except Exception as img_error:
                logger.debug(f"Could not get plate image: {img_error}")
            
            # Send email
            success = self.email_sender.send_stolen_vehicle_alert(
                plate_number=plate_text,
                owner_name=stolen_vehicle.owner_name or 'Unknown',
                vehicle_type=stolen_vehicle.vehicle_type or 'Unknown',
                vehicle_color=stolen_vehicle.vehicle_color or 'Unknown',
                reported_date=stolen_vehicle.reported_date.strftime('%Y-%m-%d') if stolen_vehicle.reported_date else 'Unknown',
                detection_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                detection_location='Camera Detection',
                recipients=recipients,
                plate_image_path=plate_image_path
            )
            
            if success:
                logger.info(f"📧 Email alert sent to {len(recipients)} recipient(s)")
                
                # Update alert record with email sent status
                try:
                    with self.db.get_session() as session:
                        from src.db.special_vehicles_models import StolenVehicleAlert
                        alert = session.query(StolenVehicleAlert).filter(
                            StolenVehicleAlert.stolen_vehicle_id == stolen_vehicle.id
                        ).order_by(StolenVehicleAlert.detection_time.desc()).first()
                        
                        if alert:
                            alert.alert_sent_email = True
                            alert.email_recipients = ', '.join(recipients)
                            alert.email_sent_at = datetime.utcnow()
                            session.commit()
                except Exception as update_error:
                    logger.debug(f"Could not update alert record: {update_error}")
            else:
                logger.warning("Failed to send email alert")
                
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            import traceback
            traceback.print_exc()
    
    def get_and_clear_stolen_alert(self):
        """
        Get the last stolen vehicle alert and clear it
        
        Returns:
            Dictionary with alert data or None
        """
        alert = self._last_stolen_alert
        self._last_stolen_alert = None
        return alert
