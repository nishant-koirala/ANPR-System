"""
Database Page for ANPR UI
Provides database viewing, searching, and management functionality
"""

import sys
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QDateEdit, QGroupBox,
    QMessageBox, QHeaderView, QTabWidget, QTextEdit, QSpinBox
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont

# Add src to path for database imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from src.db import Database, get_database
    from src.db.models import RawLog, VehicleLog, Camera, Vehicle, ToggleMode
    from src.db.toggle_manager import ToggleManager
except ImportError as e:
    print(f"Database import error: {e}")
    # Fallback for when database is not available
    Database = None


class DatabasePage(QWidget):
    """Database management and viewing page"""
    
    def __init__(self):
        super().__init__()
        self.db = None
        self.init_database()
        self.setup_ui()
        self.setup_refresh_timer()
    
    def init_database(self):
        """Initialize database connection"""
        try:
            if Database:
                self.db = get_database()
                self.db.create_tables()  # Ensure tables exist
        except Exception as e:
            print(f"Database initialization error: {e}")
            self.db = None
    
    def setup_ui(self):
        """Setup the database page UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📈 Database Management")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Check if database is available
        if not self.db:
            error_label = QLabel("❌ Database not available. Please install dependencies:\npip install sqlalchemy")
            error_label.setStyleSheet("color: red; padding: 20px; font-size: 14px;")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
            return
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        
        # Vehicle Logs Tab
        self.vehicle_logs_tab = self.create_vehicle_logs_tab()
        self.tabs.addTab(self.vehicle_logs_tab, "🚗 Vehicle Logs")
        
        # Raw Logs Tab
        self.raw_logs_tab = self.create_raw_logs_tab()
        self.tabs.addTab(self.raw_logs_tab, "📊 Raw Detections")
        
        # Statistics Tab
        self.stats_tab = self.create_statistics_tab()
        self.tabs.addTab(self.stats_tab, "📈 Statistics")
        
        # Database Info Tab
        self.info_tab = self.create_info_tab()
        self.tabs.addTab(self.info_tab, "ℹ️ Database Info")
        
        layout.addWidget(self.tabs)
        
        # Refresh controls
        refresh_layout = QHBoxLayout()
        self.auto_refresh_btn = QPushButton("🔄 Auto Refresh: ON")
        self.auto_refresh_btn.clicked.connect(self.toggle_auto_refresh)
        self.auto_refresh_btn.setStyleSheet("padding: 8px; background: #00b894; color: white; border-radius: 4px;")
        
        manual_refresh_btn = QPushButton("🔄 Refresh Now")
        manual_refresh_btn.clicked.connect(self.refresh_all_data)
        manual_refresh_btn.setStyleSheet("padding: 8px; background: #0984e3; color: white; border-radius: 4px;")
        
        refresh_layout.addStretch()
        refresh_layout.addWidget(self.auto_refresh_btn)
        refresh_layout.addWidget(manual_refresh_btn)
        
        layout.addLayout(refresh_layout)
        
        # Load initial data
        self.refresh_all_data()
    
    def create_vehicle_logs_tab(self):
        """Create vehicle logs viewing tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search controls
        search_group = QGroupBox("Search & Filter")
        search_layout = QHBoxLayout(search_group)
        
        # Plate search
        search_layout.addWidget(QLabel("Plate:"))
        self.plate_search = QLineEdit()
        self.plate_search.setPlaceholderText("Enter plate number...")
        self.plate_search.textChanged.connect(self.filter_vehicle_logs)
        search_layout.addWidget(self.plate_search)
        
        # Toggle mode filter
        search_layout.addWidget(QLabel("Mode:"))
        self.mode_filter = QComboBox()
        self.mode_filter.addItems(["All", "ENTRY", "EXIT"])
        self.mode_filter.currentTextChanged.connect(self.filter_vehicle_logs)
        search_layout.addWidget(self.mode_filter)
        
        # Date filter
        search_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.dateChanged.connect(self.filter_vehicle_logs)
        search_layout.addWidget(self.date_from)
        
        layout.addWidget(search_group)
        
        # Vehicle logs table
        self.vehicle_table = QTableWidget()
        self.vehicle_table.setColumnCount(7)
        self.vehicle_table.setHorizontalHeaderLabels([
            "Log ID", "Plate Number", "Toggle Mode", "Captured At", 
            "Duration (min)", "Session ID", "Camera"
        ])
        
        # Make table sortable and resizable
        self.vehicle_table.setSortingEnabled(True)
        header = self.vehicle_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.vehicle_table)
        
        return widget
    
    def create_raw_logs_tab(self):
        """Create raw logs viewing tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search controls
        search_group = QGroupBox("Search Raw Detections")
        search_layout = QHBoxLayout(search_group)
        
        # Confidence filter
        search_layout.addWidget(QLabel("Min Confidence:"))
        self.confidence_filter = QSpinBox()
        self.confidence_filter.setRange(0, 100)
        self.confidence_filter.setValue(70)
        self.confidence_filter.setSuffix("%")
        self.confidence_filter.valueChanged.connect(self.filter_raw_logs)
        search_layout.addWidget(self.confidence_filter)
        
        # Plate search for raw logs
        search_layout.addWidget(QLabel("Plate:"))
        self.raw_plate_search = QLineEdit()
        self.raw_plate_search.setPlaceholderText("Search plate text...")
        self.raw_plate_search.textChanged.connect(self.filter_raw_logs)
        search_layout.addWidget(self.raw_plate_search)
        
        layout.addWidget(search_group)
        
        # Raw logs table
        self.raw_table = QTableWidget()
        self.raw_table.setColumnCount(6)
        self.raw_table.setHorizontalHeaderLabels([
            "Raw ID", "Frame ID", "Plate Text", "Confidence", 
            "Captured At", "Camera"
        ])
        
        self.raw_table.setSortingEnabled(True)
        header = self.raw_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.raw_table)
        
        return widget
    
    def create_statistics_tab(self):
        """Create statistics viewing tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.stats_text)
        
        return widget
    
    def create_info_tab(self):
        """Create database info tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Database info display
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.info_text)
        
        return widget
    
    def setup_refresh_timer(self):
        """Setup auto-refresh timer"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
        self.auto_refresh_enabled = True
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh on/off"""
        if self.auto_refresh_enabled:
            self.refresh_timer.stop()
            self.auto_refresh_btn.setText("🔄 Auto Refresh: OFF")
            self.auto_refresh_btn.setStyleSheet("padding: 8px; background: #d63031; color: white; border-radius: 4px;")
            self.auto_refresh_enabled = False
        else:
            self.refresh_timer.start(5000)
            self.auto_refresh_btn.setText("🔄 Auto Refresh: ON")
            self.auto_refresh_btn.setStyleSheet("padding: 8px; background: #00b894; color: white; border-radius: 4px;")
            self.auto_refresh_enabled = True
    
    def refresh_all_data(self):
        """Refresh all data in all tabs"""
        if not self.db:
            print("❌ Database not available for refresh")
            return
        
        try:
            print("🔄 Refreshing all database data...")
            self.load_vehicle_logs()
            self.load_raw_logs()
            self.load_statistics()
            self.load_database_info()
            print("✅ All data refreshed successfully")
        except Exception as e:
            print(f"❌ Error refreshing data: {e}")
            import traceback
            traceback.print_exc()
    
    def load_vehicle_logs(self):
        """Load vehicle logs data"""
        if not self.db:
            print("❌ Database not available")
            return
        
        try:
            print("🔄 Loading vehicle logs...")
            with self.db.get_session() as session:
                # Get recent vehicle logs (last 1000 records)
                logs = session.query(VehicleLog)\
                             .order_by(VehicleLog.captured_at.desc())\
                             .limit(1000)\
                             .all()
                
                print(f"📊 Found {len(logs)} vehicle logs")
                self.vehicle_table.setRowCount(len(logs))
                
                for row, log in enumerate(logs):
                    # Get camera info
                    camera_name = "Unknown"
                    try:
                        if hasattr(log, 'raw_log') and log.raw_log and hasattr(log.raw_log, 'camera') and log.raw_log.camera:
                            camera_name = log.raw_log.camera.camera_name
                    except Exception:
                        pass
                    
                    self.vehicle_table.setItem(row, 0, QTableWidgetItem(str(log.log_id)))
                    self.vehicle_table.setItem(row, 1, QTableWidgetItem(log.plate_number))
                    self.vehicle_table.setItem(row, 2, QTableWidgetItem(log.toggle_mode.value))
                    self.vehicle_table.setItem(row, 3, QTableWidgetItem(log.captured_at.strftime("%Y-%m-%d %H:%M:%S")))
                    self.vehicle_table.setItem(row, 4, QTableWidgetItem(str(log.duration_minutes or "")))
                    self.vehicle_table.setItem(row, 5, QTableWidgetItem(log.session_id or ""))
                    self.vehicle_table.setItem(row, 6, QTableWidgetItem(camera_name))
                
                print("✅ Vehicle logs loaded successfully")
                
        except Exception as e:
            print(f"❌ Error loading vehicle logs: {e}")
            import traceback
            traceback.print_exc()
    
    def load_raw_logs(self):
        """Load raw logs data"""
        if not self.db:
            return
        
        try:
            with self.db.get_session() as session:
                # Get recent raw logs (last 500 records)
                logs = session.query(RawLog)\
                             .order_by(RawLog.captured_at.desc())\
                             .limit(500)\
                             .all()
                
                self.raw_table.setRowCount(len(logs))
                
                for row, log in enumerate(logs):
                    camera_name = log.camera.camera_name if log.camera else "Unknown"
                    
                    self.raw_table.setItem(row, 0, QTableWidgetItem(str(log.raw_id)))
                    self.raw_table.setItem(row, 1, QTableWidgetItem(log.frame_id))
                    self.raw_table.setItem(row, 2, QTableWidgetItem(log.plate_text))
                    self.raw_table.setItem(row, 3, QTableWidgetItem(f"{log.confidence:.2f}"))
                    self.raw_table.setItem(row, 4, QTableWidgetItem(log.captured_at.strftime("%Y-%m-%d %H:%M:%S")))
                    self.raw_table.setItem(row, 5, QTableWidgetItem(camera_name))
                
        except Exception as e:
            print(f"Error loading raw logs: {e}")
    
    def load_statistics(self):
        """Load and display statistics"""
        if not self.db:
            return
        
        try:
            with self.db.get_session() as session:
                # Get various statistics
                total_vehicles = session.query(Vehicle).count()
                total_raw_logs = session.query(RawLog).count()
                total_vehicle_logs = session.query(VehicleLog).count()
                
                # Today's statistics
                today = datetime.now().date()
                today_entries = session.query(VehicleLog)\
                                     .filter(VehicleLog.toggle_mode == ToggleMode.ENTRY)\
                                     .filter(VehicleLog.captured_at >= today)\
                                     .count()
                
                today_exits = session.query(VehicleLog)\
                                   .filter(VehicleLog.toggle_mode == ToggleMode.EXIT)\
                                   .filter(VehicleLog.captured_at >= today)\
                                   .count()
                
                # Recent activity (last hour)
                one_hour_ago = datetime.now() - timedelta(hours=1)
                recent_activity = session.query(VehicleLog)\
                                        .filter(VehicleLog.captured_at >= one_hour_ago)\
                                        .count()
                
                # Camera statistics
                cameras = session.query(Camera).all()
                
                stats_text = f"""
📊 ANPR Database Statistics
{'='*50}

📈 Overall Statistics:
   • Total Vehicles Registered: {total_vehicles:,}
   • Total Raw Detections: {total_raw_logs:,}
   • Total Vehicle Logs: {total_vehicle_logs:,}

📅 Today's Activity:
   • Entries: {today_entries:,}
   • Exits: {today_exits:,}
   • Currently Inside: {today_entries - today_exits:,}

⏰ Recent Activity (Last Hour):
   • Vehicle Movements: {recent_activity:,}

📹 Camera Status:
"""
                
                for camera in cameras:
                    camera_logs = session.query(VehicleLog)\
                                        .join(RawLog)\
                                        .filter(RawLog.camera_id == camera.camera_id)\
                                        .filter(VehicleLog.captured_at >= today)\
                                        .count()
                    
                    stats_text += f"   • {camera.camera_name} ({camera.location}): {camera_logs:,} logs today\n"
                
                stats_text += f"\n🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.stats_text.setPlainText(stats_text)
                
        except Exception as e:
            self.stats_text.setPlainText(f"Error loading statistics: {e}")
    
    def load_database_info(self):
        """Load database information"""
        if not self.db:
            self.info_text.setPlainText("Database not available")
            return
        
        try:
            info_text = f"""
🗄️ Database Information
{'='*50}

📍 Database Location: {self.db.database_url}
🕒 Connection Status: Connected
📊 Database Type: SQLite

📋 Table Structure:
   • raw_logs: Stores all YOLO/OCR detections
   • vehicle_log: Filtered entry/exit records with toggle mode
   • cameras: Camera information and locations
   • vehicles: Vehicle registry with plate numbers

🔧 Features:
   ✓ Toggle Mode (ENTRY/EXIT detection)
   ✓ Confidence-based filtering
   ✓ Duplicate detection prevention
   ✓ Session tracking
   ✓ Real-time statistics

⚙️ Configuration:
   • Auto-refresh: {'ON' if self.auto_refresh_enabled else 'OFF'}
   • Refresh Interval: 5 seconds
   • Max Records Displayed: 1000 (vehicle logs), 500 (raw logs)

🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            self.info_text.setPlainText(info_text)
            
        except Exception as e:
            self.info_text.setPlainText(f"Error loading database info: {e}")
    
    def filter_vehicle_logs(self):
        """Filter vehicle logs based on search criteria"""
        if not self.db:
            return
        
        try:
            with self.db.get_session() as session:
                query = session.query(VehicleLog)
                
                # Filter by plate number
                plate_text = self.plate_search.text().strip().upper()
                if plate_text:
                    query = query.filter(VehicleLog.plate_number.ilike(f'%{plate_text}%'))
                
                # Filter by toggle mode
                mode_filter = self.mode_filter.currentText()
                if mode_filter != "All":
                    if mode_filter == "ENTRY":
                        query = query.filter(VehicleLog.toggle_mode == ToggleMode.ENTRY)
                    elif mode_filter == "EXIT":
                        query = query.filter(VehicleLog.toggle_mode == ToggleMode.EXIT)
                
                # Filter by date
                from_date = self.date_from.date().toPyDate()
                query = query.filter(VehicleLog.captured_at >= from_date)
                
                # Get filtered results
                logs = query.order_by(VehicleLog.captured_at.desc()).limit(100).all()
                
                # Update table with filtered results
                self.vehicle_table.setRowCount(len(logs))
                for i, log in enumerate(logs):
                    self.vehicle_table.setItem(i, 0, QTableWidgetItem(str(log.log_id)))
                    self.vehicle_table.setItem(i, 1, QTableWidgetItem(log.plate_number))
                    self.vehicle_table.setItem(i, 2, QTableWidgetItem(log.toggle_mode.value))
                    self.vehicle_table.setItem(i, 3, QTableWidgetItem(log.captured_at.strftime('%Y-%m-%d %H:%M:%S')))
                    duration = str(log.duration_minutes) if log.duration_minutes else "N/A"
                    self.vehicle_table.setItem(i, 4, QTableWidgetItem(duration))
                
        except Exception as e:
            print(f"Error filtering vehicle logs: {e}")
            self.load_vehicle_logs()  # Fallback to full reload
    
    def filter_raw_logs(self):
        """Filter raw logs based on search criteria"""
        if not self.db:
            return
        
        try:
            with self.db.get_session() as session:
                query = session.query(RawLog)
                
                # Filter by confidence
                min_confidence = self.confidence_filter.value() / 100.0
                query = query.filter(RawLog.confidence >= min_confidence)
                
                # Filter by plate text
                plate_text = self.raw_plate_search.text().strip().upper()
                if plate_text:
                    query = query.filter(RawLog.plate_text.ilike(f'%{plate_text}%'))
                
                # Get filtered results
                logs = query.order_by(RawLog.captured_at.desc()).limit(100).all()
                
                # Update table with filtered results
                self.raw_table.setRowCount(len(logs))
                for i, log in enumerate(logs):
                    self.raw_table.setItem(i, 0, QTableWidgetItem(str(log.raw_id)))
                    self.raw_table.setItem(i, 1, QTableWidgetItem(log.plate_text))
                    self.raw_table.setItem(i, 2, QTableWidgetItem(f"{log.confidence:.2f}"))
                    self.raw_table.setItem(i, 3, QTableWidgetItem(log.captured_at.strftime('%Y-%m-%d %H:%M:%S')))
                    self.raw_table.setItem(i, 4, QTableWidgetItem(str(log.frame_id)))
                
        except Exception as e:
            print(f"Error filtering raw logs: {e}")
            self.load_raw_logs()  # Fallback to full reload
