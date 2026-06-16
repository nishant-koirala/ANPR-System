"""
Database operations for Special Vehicles Management
CRUD operations for stolen vehicles, staff vehicles, and alerts
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Tuple
from .special_vehicles_models import StolenVehicle, StaffVehicle, StolenVehicleAlert, AlertConfiguration


class SpecialVehiclesDB:
    """Database operations for special vehicles management"""
    
    def __init__(self, session_factory):
        """
        Initialize with session factory
        
        Args:
            session_factory: SQLAlchemy session factory function
        """
        self.session_factory = session_factory
    
    # ==================== STOLEN VEHICLES ====================
    
    def add_stolen_vehicle(self, plate_number: str, owner_name: str = None,
                          vehicle_type: str = None, vehicle_color: str = None,
                          contact_number: str = None, notes: str = None,
                          reported_date: date = None,
                          enable_dashboard_alert: bool = True,
                          enable_email_alert: bool = True,
                          enable_sound_alert: bool = True,
                          email_recipients: str = None,
                          created_by: int = None) -> Optional[StolenVehicle]:
        """
        Add a new stolen vehicle
        
        Args:
            plate_number: Vehicle plate number (required)
            owner_name: Owner name
            vehicle_type: Type of vehicle
            vehicle_color: Vehicle color
            contact_number: Contact number
            notes: Additional notes
            reported_date: Date reported stolen
            enable_dashboard_alert: Enable dashboard alerts
            enable_email_alert: Enable email alerts
            enable_sound_alert: Enable sound alerts
            email_recipients: Email addresses for alerts (comma or newline separated)
            created_by: User ID who created the record
            
        Returns:
            StolenVehicle object or None if error
        """
        with self.session_factory() as session:
            # Check if already exists
            existing = session.query(StolenVehicle).filter_by(plate_number=plate_number).first()
            if existing:
                print(f"Stolen vehicle {plate_number} already exists")
                return None
            
            stolen_vehicle = StolenVehicle(
                plate_number=plate_number.upper(),
                owner_name=owner_name,
                vehicle_type=vehicle_type,
                vehicle_color=vehicle_color,
                contact_number=contact_number,
                notes=notes,
                reported_date=reported_date or datetime.now().date(),
                enable_dashboard_alert=enable_dashboard_alert,
                enable_email_alert=enable_email_alert,
                enable_sound_alert=enable_sound_alert,
                email_recipients=email_recipients,
                status='Active',
                created_by=created_by
            )
            
            session.add(stolen_vehicle)
            session.commit()
            session.refresh(stolen_vehicle)
            
            # Expunge to make accessible outside session
            session.expunge(stolen_vehicle)
            
            print(f"Added stolen vehicle: {plate_number}")
            return stolen_vehicle
    
    def get_stolen_vehicle_by_id(self, vehicle_id: int) -> Optional[StolenVehicle]:
        """Get stolen vehicle by ID"""
        with self.session_factory() as session:
            vehicle = session.query(StolenVehicle).filter_by(id=vehicle_id).first()
            if vehicle:
                session.expunge(vehicle)
            return vehicle
    
    def get_stolen_vehicle_by_plate(self, plate_number: str) -> Optional[StolenVehicle]:
        """Get stolen vehicle by plate number"""
        with self.session_factory() as session:
            vehicle = session.query(StolenVehicle).filter_by(
                plate_number=plate_number.upper()
            ).first()
            if vehicle:
                session.expunge(vehicle)
            return vehicle
    
    def get_all_stolen_vehicles(self, status: str = None) -> List[StolenVehicle]:
        """
        Get all stolen vehicles, optionally filtered by status
        
        Args:
            status: Filter by status (Active, Recovered, Archived) or None for all
            
        Returns:
            List of StolenVehicle objects
        """
        with self.session_factory() as session:
            query = session.query(StolenVehicle)
            if status:
                query = query.filter_by(status=status)
            results = query.order_by(StolenVehicle.reported_date.desc()).all()
            # Expunge all objects to make them accessible outside session
            for obj in results:
                session.expunge(obj)
            return results
    
    def search_stolen_vehicles(self, search_term: str, status: str = None) -> List[StolenVehicle]:
        """
        Search stolen vehicles by plate number, owner name
        
        Args:
            search_term: Search term
            status: Optional status filter
            
        Returns:
            List of matching StolenVehicle objects
        """
        with self.session_factory() as session:
            search_pattern = f"%{search_term}%"
            query = session.query(StolenVehicle).filter(
                or_(
                    StolenVehicle.plate_number.like(search_pattern),
                    StolenVehicle.owner_name.like(search_pattern)
                )
            )
            if status:
                query = query.filter_by(status=status)
            results = query.order_by(StolenVehicle.reported_date.desc()).all()
            # Expunge all objects to make them accessible outside session
            for obj in results:
                session.expunge(obj)
            return results
    
    def update_stolen_vehicle(self, vehicle_id: int, **kwargs) -> bool:
        """
        Update stolen vehicle details
        
        Args:
            vehicle_id: Stolen vehicle ID
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        with self.session_factory() as session:
            vehicle = session.query(StolenVehicle).filter_by(id=vehicle_id).first()
            if not vehicle:
                return False
            
            for key, value in kwargs.items():
                if hasattr(vehicle, key):
                    setattr(vehicle, key, value)
            
            vehicle.updated_at = datetime.utcnow()
            session.commit()
            return True
    def mark_stolen_vehicle_recovered(self, vehicle_id: int, updated_by: int = None) -> bool:
        """Mark stolen vehicle as recovered"""
        return self.update_stolen_vehicle(
            vehicle_id,
            status='Recovered',
            recovered_date=datetime.now().date(),
            updated_by=updated_by
        )
    
    def delete_stolen_vehicle(self, vehicle_id: int) -> bool:
        """Delete stolen vehicle"""
        with self.session_factory() as session:
            vehicle = session.query(StolenVehicle).filter_by(id=vehicle_id).first()
            if vehicle:
                session.delete(vehicle)
                session.commit()
                return True
            return False
    def check_if_stolen(self, plate_number: str) -> Optional[StolenVehicle]:
        """
        Check if a plate number is in stolen vehicles list (Active only)
        
        Args:
            plate_number: Plate number to check
            
        Returns:
            StolenVehicle object if found and active, None otherwise
        """
        with self.session_factory() as session:
            result = session.query(StolenVehicle).filter(
                and_(
                    StolenVehicle.plate_number == plate_number.upper(),
                    StolenVehicle.status == 'Active'
                )
            ).first()
            if result:
                session.expunge(result)
            return result
    
    # ==================== STAFF VEHICLES ====================
    
    def add_staff_vehicle(self, plate_number: str, staff_name: str,
                         department: str = None, position: str = None,
                         vehicle_type: str = None, vehicle_color: str = None,
                         contact_number: str = None, notes: str = None,
                         valid_from: date = None, valid_until: date = None,
                         free_parking: bool = True, priority_access: bool = False,
                         created_by: int = None) -> Optional[StaffVehicle]:
        """
        Add a new staff vehicle
        
        Args:
            plate_number: Vehicle plate number (required)
            staff_name: Staff member name (required)
            department: Department
            position: Job position
            vehicle_type: Type of vehicle
            vehicle_color: Vehicle color
            contact_number: Contact number
            notes: Additional notes
            valid_from: Valid from date
            valid_until: Valid until date
            free_parking: Enable free parking
            priority_access: Enable priority access
            created_by: User ID who created the record
            
        Returns:
            StaffVehicle object or None if error
        """
        with self.session_factory() as session:
            # Check if already exists
            existing = session.query(StaffVehicle).filter_by(plate_number=plate_number).first()
            if existing:
                print(f"Staff vehicle {plate_number} already exists")
                return None
            
            # Default validity: 1 year from today
            if not valid_from:
                valid_from = datetime.now().date()
            if not valid_until:
                valid_until = valid_from + timedelta(days=365)
            
            staff_vehicle = StaffVehicle(
                plate_number=plate_number.upper(),
                staff_name=staff_name,
                department=department,
                position=position,
                vehicle_type=vehicle_type,
                vehicle_color=vehicle_color,
                contact_number=contact_number,
                notes=notes,
                valid_from=valid_from,
                valid_until=valid_until,
                free_parking=free_parking,
                priority_access=priority_access,
                status='Active',
                created_by=created_by
            )
            
            session.add(staff_vehicle)
            session.commit()
            session.refresh(staff_vehicle)
            
            # Expunge to make accessible outside session
            session.expunge(staff_vehicle)
            
            print(f"Added staff vehicle: {plate_number} for {staff_name}")
            return staff_vehicle
    def get_staff_vehicle_by_id(self, vehicle_id: int) -> Optional[StaffVehicle]:
        """Get staff vehicle by ID"""
        with self.session_factory() as session:
            vehicle = session.query(StaffVehicle).filter_by(id=vehicle_id).first()
            if vehicle:
                session.expunge(vehicle)
            return vehicle
    
    def get_staff_vehicle_by_plate(self, plate_number: str) -> Optional[StaffVehicle]:
        """Get staff vehicle by plate number"""
        with self.session_factory() as session:
            vehicle = session.query(StaffVehicle).filter_by(
                plate_number=plate_number.upper()
            ).first()
            if vehicle:
                session.expunge(vehicle)
            return vehicle
    
    def get_all_staff_vehicles(self, department: str = None) -> List[StaffVehicle]:
        """
        Get all staff vehicles, optionally filtered by department
        
        Args:
            department: Filter by department or None for all
            
        Returns:
            List of StaffVehicle objects
        """
        with self.session_factory() as session:
            query = session.query(StaffVehicle)
            if department:
                query = query.filter_by(department=department)
            results = query.order_by(StaffVehicle.created_at.desc()).all()
            # Expunge all objects to make them accessible outside session
            for obj in results:
                session.expunge(obj)
            return results
    
    def search_staff_vehicles(self, search_term: str, department: str = None) -> List[StaffVehicle]:
        """
        Search staff vehicles by plate number, staff name, or department
        
        Args:
            search_term: Search term
            department: Optional department filter
            
        Returns:
            List of matching StaffVehicle objects
        """
        with self.session_factory() as session:
            search_pattern = f"%{search_term}%"
            query = session.query(StaffVehicle).filter(
                or_(
                    StaffVehicle.plate_number.like(search_pattern),
                    StaffVehicle.staff_name.like(search_pattern),
                    StaffVehicle.department.like(search_pattern)
                )
            )
            if department:
                query = query.filter_by(department=department)
            results = query.order_by(StaffVehicle.created_at.desc()).all()
            # Expunge all objects to make them accessible outside session
            for obj in results:
                session.expunge(obj)
            return results
    
    def update_staff_vehicle(self, vehicle_id: int, **kwargs) -> bool:
        """
        Update staff vehicle details
        
        Args:
            vehicle_id: Staff vehicle ID
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        with self.session_factory() as session:
            vehicle = session.query(StaffVehicle).filter_by(id=vehicle_id).first()
            if not vehicle:
                return False
            
            for key, value in kwargs.items():
                if hasattr(vehicle, key):
                    setattr(vehicle, key, value)
            
            vehicle.updated_at = datetime.utcnow()
            session.commit()
            return True
    def delete_staff_vehicle(self, vehicle_id: int) -> bool:
        """Delete staff vehicle"""
        with self.session_factory() as session:
            vehicle = session.query(StaffVehicle).filter_by(id=vehicle_id).first()
            if vehicle:
                session.delete(vehicle)
                session.commit()
                return True
            return False
    def check_if_staff(self, plate_number: str) -> Optional[StaffVehicle]:
        """
        Check if a plate number is a staff vehicle (Active and valid)
        
        Args:
            plate_number: Plate number to check
            
        Returns:
            StaffVehicle object if found and valid, None otherwise
        """
        with self.session_factory() as session:
            today = datetime.now().date()
            result = session.query(StaffVehicle).filter(
                and_(
                    StaffVehicle.plate_number == plate_number.upper(),
                    StaffVehicle.status == 'Active',
                    StaffVehicle.valid_from <= today,
                    StaffVehicle.valid_until >= today
                )
            ).first()
            if result:
                session.expunge(result)
            return result
    
    # ==================== ALERT HISTORY ====================
    
    def log_stolen_vehicle_alert(self, stolen_vehicle_id: int, camera_id: int = None,
                                 raw_log_id: int = None, plate_image_path: str = None,
                                 confidence: float = None,
                                 alert_sent_dashboard: bool = False,
                                 alert_sent_email: bool = False,
                                 email_recipients: str = None) -> Optional[StolenVehicleAlert]:
        """
        Log a stolen vehicle alert
        
        Args:
            stolen_vehicle_id: ID of stolen vehicle
            camera_id: Camera that detected the vehicle
            raw_log_id: Raw log ID
            plate_image_path: Path to plate image
            confidence: Detection confidence
            alert_sent_dashboard: Dashboard alert sent
            alert_sent_email: Email alert sent
            email_recipients: Email recipients (comma-separated)
            
        Returns:
            StolenVehicleAlert object or None if error
        """
        with self.session_factory() as session:
            alert = StolenVehicleAlert(
                stolen_vehicle_id=stolen_vehicle_id,
                detection_time=datetime.utcnow(),
                camera_id=camera_id,
                raw_log_id=raw_log_id,
                plate_image_path=plate_image_path,
                confidence=confidence,
                alert_sent_dashboard=alert_sent_dashboard,
                alert_sent_email=alert_sent_email,
                email_recipients=email_recipients,
                email_sent_at=datetime.utcnow() if alert_sent_email else None
            )
            
            session.add(alert)
            session.commit()
            session.refresh(alert)
            
            # Expunge to make accessible outside session
            session.expunge(alert)
            
            print(f"Logged stolen vehicle alert for vehicle ID {stolen_vehicle_id}")
            return alert
    def get_recent_alerts(self, limit: int = 10) -> List[StolenVehicleAlert]:
        """Get recent stolen vehicle alerts"""
        with self.session_factory() as session:
            results = session.query(StolenVehicleAlert).order_by(
                StolenVehicleAlert.detection_time.desc()
            ).limit(limit).all()
            for obj in results:
                session.expunge(obj)
            return results
    
    def get_alerts_for_vehicle(self, stolen_vehicle_id: int) -> List[StolenVehicleAlert]:
        """Get all alerts for a specific stolen vehicle"""
        with self.session_factory() as session:
            results = session.query(StolenVehicleAlert).filter_by(
                stolen_vehicle_id=stolen_vehicle_id
            ).order_by(StolenVehicleAlert.detection_time.desc()).all()
            for obj in results:
                session.expunge(obj)
            return results
    
    def check_alert_cooldown(self, stolen_vehicle_id: int, cooldown_minutes: int = 5) -> bool:
        """
        Check if alert cooldown period has passed
        
        Args:
            stolen_vehicle_id: Stolen vehicle ID
            cooldown_minutes: Cooldown period in minutes
            
        Returns:
            True if cooldown passed (can send alert), False otherwise
        """
        with self.session_factory() as session:
            cutoff_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
            recent_alert = session.query(StolenVehicleAlert).filter(
                and_(
                    StolenVehicleAlert.stolen_vehicle_id == stolen_vehicle_id,
                    StolenVehicleAlert.detection_time > cutoff_time
                )
            ).first()
            
            return recent_alert is None  # True if no recent alert (cooldown passed)
    
    # ==================== ALERT CONFIGURATION ====================
    
    def get_alert_config(self) -> Optional[AlertConfiguration]:
        """Get alert configuration (creates default if not exists)"""
        with self.session_factory() as session:
            config = session.query(AlertConfiguration).first()
            if not config:
                # Create default configuration
                config = AlertConfiguration()
                session.add(config)
                session.commit()
                session.refresh(config)
            
            # Make object accessible outside session by expunging
            if config:
                session.expunge(config)
            return config
    
    def update_alert_config(self, **kwargs) -> bool:
        """
        Update alert configuration
        
        Args:
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        with self.session_factory() as session:
            config = session.query(AlertConfiguration).first()
            if not config:
                config = AlertConfiguration()
                session.add(config)
            
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = datetime.utcnow()
            session.commit()
            return True
    # ==================== STATISTICS ====================
    
    def get_statistics(self) -> Dict:
        """Get statistics for dashboard"""
        with self.session_factory() as session:
            stats = {
                'stolen_vehicles_count': session.query(StolenVehicle).filter_by(status='Active').count(),
                'staff_vehicles_count': session.query(StaffVehicle).filter_by(status='Active').count(),
                'active_alerts_count': session.query(StolenVehicleAlert).filter(
                    StolenVehicleAlert.detection_time > datetime.utcnow() - timedelta(hours=24)
                ).count(),
                'recent_detections_count': session.query(StolenVehicleAlert).filter(
                    StolenVehicleAlert.detection_time > datetime.utcnow() - timedelta(hours=1)
                ).count()
            }
            return stats
