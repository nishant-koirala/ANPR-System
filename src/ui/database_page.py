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
    QMessageBox, QHeaderView, QTabWidget, QTextEdit, QSpinBox, QDialog,
    QScrollArea
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont, QPixmap
import cv2

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


class PlateEditDialog(QDialog):
    """Custom dialog for editing plate numbers with image display"""
    
    def __init__(self, parent, log_id, current_plate, image_path):
        super().__init__(parent)
        self.log_id = log_id
        self.current_plate = current_plate
        self.image_path = image_path
        self.new_plate_text = current_plate
        
        self.setup_ui()
        self.load_plate_image()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle(f"Edit Plate Number - Log ID {self.log_id}")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"Edit Plate Number for Log ID {self.log_id}")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - Image display
        image_group = QGroupBox("Plate Image")
        image_layout = QVBoxLayout(image_group)
        
        # Scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumSize(300, 200)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: white;")
        self.image_label.setScaledContents(False)
        
        self.scroll_area.setWidget(self.image_label)
        image_layout.addWidget(self.scroll_area)
        
        # Image controls
        image_controls = QHBoxLayout()
        self.zoom_in_btn = QPushButton("🔍 Zoom In")
        self.zoom_out_btn = QPushButton("🔍 Zoom Out")
        self.reset_zoom_btn = QPushButton("↻ Reset")
        
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        
        image_controls.addWidget(self.zoom_in_btn)
        image_controls.addWidget(self.zoom_out_btn)
        image_controls.addWidget(self.reset_zoom_btn)
        image_layout.addLayout(image_controls)
        
        content_layout.addWidget(image_group)
        
        # Right side - Edit controls
        edit_group = QGroupBox("Edit Plate Number")
        edit_layout = QVBoxLayout(edit_group)
        
        # Current plate display
        current_label = QLabel("Current Plate:")
        current_label.setFont(QFont("Arial", 10, QFont.Bold))
        edit_layout.addWidget(current_label)
        
        self.current_plate_display = QLabel(self.current_plate)
        self.current_plate_display.setStyleSheet("""
            padding: 8px; 
            background: #f8f9fa; 
            border: 1px solid #dee2e6; 
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
        """)
        edit_layout.addWidget(self.current_plate_display)
        
        edit_layout.addWidget(QLabel(""))  # Spacer
        
        # New plate input
        new_label = QLabel("New Plate Number:")
        new_label.setFont(QFont("Arial", 10, QFont.Bold))
        edit_layout.addWidget(new_label)
        
        self.plate_input = QLineEdit(self.current_plate)
        self.plate_input.setStyleSheet("""
            padding: 8px; 
            border: 2px solid #007bff; 
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
        """)
        self.plate_input.textChanged.connect(self.on_text_changed)
        edit_layout.addWidget(self.plate_input)
        
        # Validation message
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #dc3545; font-size: 12px;")
        edit_layout.addWidget(self.validation_label)
        
        edit_layout.addStretch()
        
        content_layout.addWidget(edit_group)
        layout.addLayout(content_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #28a745; 
                color: white; 
                padding: 10px 20px; 
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        self.save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d; 
                color: white; 
                padding: 10px 20px; 
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        # Set focus to input field
        self.plate_input.setFocus()
        self.plate_input.selectAll()
        
        # Initialize zoom
        self.zoom_factor = 1.0
        self.original_pixmap = None
    
    def load_plate_image(self):
        """Load and display the plate image"""
        try:
            if not self.image_path or not os.path.exists(self.image_path):
                # Show placeholder if no image
                self.image_label.setText("No plate image available")
                self.image_label.setStyleSheet("""
                    border: 2px dashed #ccc; 
                    background: #f8f9fa; 
                    color: #6c757d;
                    font-size: 14px;
                    min-height: 100px;
                """)
                return
            
            # Load image using OpenCV for better handling
            image = cv2.imread(self.image_path)
            if image is None:
                self.image_label.setText("Failed to load plate image")
                return
            
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Convert to QPixmap
            height, width, channel = image_rgb.shape
            bytes_per_line = 3 * width
            from PyQt5.QtGui import QImage
            q_image = QImage(image_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            self.original_pixmap = QPixmap.fromImage(q_image)
            self.update_image_display()
            
        except Exception as e:
            print(f"Error loading plate image: {e}")
            self.image_label.setText(f"Error loading image: {e}")
    
    def update_image_display(self):
        """Update image display with current zoom"""
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.original_pixmap.size() * self.zoom_factor,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.resize(scaled_pixmap.size())
    
    def zoom_in(self):
        """Zoom in on the image"""
        self.zoom_factor = min(self.zoom_factor * 1.5, 5.0)
        self.update_image_display()
    
    def zoom_out(self):
        """Zoom out on the image"""
        self.zoom_factor = max(self.zoom_factor / 1.5, 0.2)
        self.update_image_display()
    
    def reset_zoom(self):
        """Reset zoom to original size"""
        self.zoom_factor = 1.0
        self.update_image_display()
    
    def on_text_changed(self, text):
        """Handle text input changes"""
        self.new_plate_text = text.strip()
        
        # Basic validation
        if not self.new_plate_text:
            self.validation_label.setText("⚠️ Plate number cannot be empty")
            self.save_btn.setEnabled(False)
        elif self.new_plate_text == self.current_plate:
            self.validation_label.setText("ℹ️ No changes made")
            self.save_btn.setEnabled(False)
        else:
            self.validation_label.setText("✅ Ready to save")
            self.save_btn.setEnabled(True)
    
    def get_new_plate_text(self):
        """Get the new plate text"""
        return self.new_plate_text


class DatabasePage(QWidget):
    """Database management and viewing page"""
    
    def __init__(self, rbac_controller=None):
        super().__init__()
        self.db = None
        self.rbac_controller = rbac_controller
        
        # Pagination settings
        self.current_page = 1
        self.records_per_page = 50  # Show 50 records per page
        self.total_records = 0
        self.total_pages = 1
        
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
        
        # Pagination controls
        pagination_layout = QHBoxLayout()
        
        self.first_page_btn = QPushButton("⏮ First")
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.first_page_btn.setMaximumWidth(80)
        
        self.prev_page_btn = QPushButton("◀ Prev")
        self.prev_page_btn.clicked.connect(self.go_to_prev_page)
        self.prev_page_btn.setMaximumWidth(80)
        
        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; padding: 5px;")
        
        self.next_page_btn = QPushButton("Next ▶")
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.next_page_btn.setMaximumWidth(80)
        
        self.last_page_btn = QPushButton("Last ⏭")
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.last_page_btn.setMaximumWidth(80)
        
        self.records_per_page_combo = QComboBox()
        self.records_per_page_combo.addItems(["25", "50", "100", "200"])
        self.records_per_page_combo.setCurrentText("50")
        self.records_per_page_combo.currentTextChanged.connect(self.change_records_per_page)
        self.records_per_page_combo.setMaximumWidth(80)
        
        self.records_info_label = QLabel("Showing 0-0 of 0")
        self.records_info_label.setStyleSheet("padding: 5px;")
        
        pagination_layout.addWidget(self.first_page_btn)
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_btn)
        pagination_layout.addWidget(self.last_page_btn)
        pagination_layout.addStretch()
        pagination_layout.addWidget(QLabel("Records per page:"))
        pagination_layout.addWidget(self.records_per_page_combo)
        pagination_layout.addWidget(self.records_info_label)
        
        layout.addLayout(pagination_layout)
        
        # Vehicle logs table
        self.vehicle_table = QTableWidget()
        self.vehicle_table.setColumnCount(9)
        self.vehicle_table.setHorizontalHeaderLabels([
            "Log ID", "Plate Image", "Plate Number", "Toggle Mode", "Captured At", 
            "Duration (hrs)", "Amount (NPR)", "Session ID", "Camera"
        ])
        
        # Set row height for images
        self.vehicle_table.setRowHeight(0, 80)  # Will be set for each row with image
        
        # Make table sortable and resizable
        self.vehicle_table.setSortingEnabled(True)
        header = self.vehicle_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Enable editing on double-click for plate number column
        self.vehicle_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
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
        """Load vehicle logs data with pagination"""
        if not self.db:
            print("❌ Database not available")
            return
        
        try:
            print(f"🔄 Loading vehicle logs (Page {self.current_page})...")
            with self.db.get_session() as session:
                # Get total count for pagination
                self.total_records = session.query(VehicleLog).count()
                self.total_pages = max(1, (self.total_records + self.records_per_page - 1) // self.records_per_page)
                
                # Calculate offset
                offset = (self.current_page - 1) * self.records_per_page
                
                # Get paginated vehicle logs
                logs = session.query(VehicleLog)\
                             .order_by(VehicleLog.captured_at.desc())\
                             .limit(self.records_per_page)\
                             .offset(offset)\
                             .all()
                
                print(f"📊 Found {len(logs)} vehicle logs (Total: {self.total_records})")
                self.vehicle_table.setRowCount(len(logs))
                
                # Update pagination controls
                self.update_pagination_controls()
                
                for row, log in enumerate(logs):
                    # Get camera info
                    camera_name = "Unknown"
                    try:
                        if hasattr(log, 'raw_log') and log.raw_log and hasattr(log.raw_log, 'camera') and log.raw_log.camera:
                            camera_name = log.raw_log.camera.camera_name
                    except Exception:
                        pass
                    
                    # Set row height for image display
                    self.vehicle_table.setRowHeight(row, 80)
                    
                    self.vehicle_table.setItem(row, 0, QTableWidgetItem(str(log.log_id)))
                    
                    # Add plate image in column 1
                    image_widget = self.create_image_widget(log)
                    self.vehicle_table.setCellWidget(row, 1, image_widget)
                    
                    self.vehicle_table.setItem(row, 2, QTableWidgetItem(log.plate_number))
                    self.vehicle_table.setItem(row, 3, QTableWidgetItem(log.toggle_mode.value))
                    self.vehicle_table.setItem(row, 4, QTableWidgetItem(log.captured_at.strftime("%Y-%m-%d %H:%M:%S")))
                    
                    # Display duration in hours
                    duration_text = ""
                    if log.duration_hours is not None:
                        duration_text = f"{log.duration_hours:.2f}"
                    elif log.duration_minutes is not None:
                        # Fallback for old records without duration_hours
                        duration_text = f"{(log.duration_minutes / 60.0):.2f}"
                    self.vehicle_table.setItem(row, 5, QTableWidgetItem(duration_text))
                    
                    # Display amount
                    amount_text = ""
                    if log.amount is not None:
                        amount_text = f"{log.amount:.2f}"
                    self.vehicle_table.setItem(row, 6, QTableWidgetItem(amount_text))
                    
                    self.vehicle_table.setItem(row, 7, QTableWidgetItem(log.session_id or ""))
                    self.vehicle_table.setItem(row, 8, QTableWidgetItem(camera_name))
                
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
                    # Set row height for image display
                    self.vehicle_table.setRowHeight(i, 80)
                    
                    self.vehicle_table.setItem(i, 0, QTableWidgetItem(str(log.log_id)))
                    
                    # Add plate image in column 1
                    image_widget = self.create_image_widget(log)
                    self.vehicle_table.setCellWidget(i, 1, image_widget)
                    
                    self.vehicle_table.setItem(i, 2, QTableWidgetItem(log.plate_number))
                    self.vehicle_table.setItem(i, 3, QTableWidgetItem(log.toggle_mode.value))
                    self.vehicle_table.setItem(i, 4, QTableWidgetItem(log.captured_at.strftime('%Y-%m-%d %H:%M:%S')))
                    
                    # Display duration in hours
                    duration_text = ""
                    if log.duration_hours is not None:
                        duration_text = f"{log.duration_hours:.2f}"
                    elif log.duration_minutes is not None:
                        duration_text = f"{(log.duration_minutes / 60.0):.2f}"
                    else:
                        duration_text = "N/A"
                    self.vehicle_table.setItem(i, 5, QTableWidgetItem(duration_text))
                    
                    # Display amount
                    amount_text = ""
                    if log.amount is not None:
                        amount_text = f"{log.amount:.2f}"
                    else:
                        amount_text = "N/A"
                    self.vehicle_table.setItem(i, 6, QTableWidgetItem(amount_text))
                
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
    
    def create_image_widget(self, log):
        """Create a widget with plate image for table cell"""
        try:
            # Check if log has plate image path
            image_path = None
            if hasattr(log, 'plate_image_path') and log.plate_image_path:
                image_path = log.plate_image_path
            elif hasattr(log, 'thumbnail_path') and log.thumbnail_path:
                image_path = log.thumbnail_path
            
            # Create a label widget
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("border: 1px solid #ddd; background: white; margin: 2px;")
            image_label.setFixedSize(70, 70)
            
            if image_path and os.path.exists(image_path):
                # Load and scale the image
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    # Scale image to fit in label (65x65 pixels with margin)
                    scaled_pixmap = pixmap.scaled(65, 65, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_label.setPixmap(scaled_pixmap)
                    image_label.setToolTip(f"Plate image: {os.path.basename(image_path)}")
                else:
                    image_label.setText("Invalid\nImage")
                    image_label.setStyleSheet("border: 1px solid #ddd; background: #f8f8f8; color: #666; font-size: 10px;")
            else:
                image_label.setText("No\nImage")
                image_label.setStyleSheet("border: 1px solid #ddd; background: #f8f8f8; color: #666; font-size: 10px;")
            
            return image_label
            
        except Exception as e:
            print(f"Error creating image widget: {e}")
            error_label = QLabel("Error")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("border: 1px solid #red; background: #ffe6e6; color: red; font-size: 10px;")
            error_label.setFixedSize(70, 70)
            return error_label
    
    def on_item_double_clicked(self, item):
        """Handle double-click on table items for editing"""
        if not item:
            return
        
        # Check permissions before allowing edit
        if self.rbac_controller and not self.rbac_controller.can_edit_plates():
            QMessageBox.warning(
                self,
                "Permission Denied",
                f"You don't have permission to edit plate numbers.\n\n"
                f"Your role: {self.rbac_controller.get_role_display_name()}\n"
                f"Required: Admin or higher"
            )
            return
            
        row = item.row()
        col = item.column()
        
        # Only allow editing of plate number column (column 2)
        if col == 2:
            self.edit_plate_number(row)
    
    def edit_plate_number(self, row):
        """Edit plate number for the selected row with image display"""
        # Double-check permissions
        if self.rbac_controller and not self.rbac_controller.can_edit_plates():
            QMessageBox.warning(
                self,
                "Permission Denied",
                "You don't have permission to edit plate numbers."
            )
            return
        
        try:
            # Get log_id from the first column
            log_id_item = self.vehicle_table.item(row, 0)
            if not log_id_item:
                return
                
            log_id = int(log_id_item.text())
            
            # Get current plate number
            plate_item = self.vehicle_table.item(row, 2)
            if not plate_item:
                return
                
            current_plate = plate_item.text()
            
            # Get plate image path from database
            plate_image_path = self.get_plate_image_path(log_id)
            
            # Show custom dialog with image and text input
            dialog = PlateEditDialog(self, log_id, current_plate, plate_image_path)
            if dialog.exec_() == QDialog.Accepted:
                new_plate = dialog.get_new_plate_text()
                if new_plate and new_plate.strip() != current_plate:
                    self.update_plate_number(log_id, current_plate, new_plate.strip(), row)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit plate number: {e}")
    
    def get_plate_image_path(self, log_id):
        """Get plate image path for the given log_id"""
        try:
            if not self.db:
                return None
                
            with self.db.get_session() as session:
                vehicle_log = session.query(VehicleLog).filter(VehicleLog.log_id == log_id).first()
                if vehicle_log and vehicle_log.plate_image_path:
                    return vehicle_log.plate_image_path
                    
                # If no image in vehicle_log, try raw_log
                if vehicle_log and vehicle_log.raw_ref:
                    raw_log = session.query(RawLog).filter(RawLog.raw_id == vehicle_log.raw_ref).first()
                    if raw_log and raw_log.plate_image_path:
                        return raw_log.plate_image_path
                        
        except Exception as e:
            print(f"Error getting plate image path: {e}")
            
        return None
    
    def update_plate_number(self, log_id, old_plate, new_plate, row):
        """Update plate number in database and table"""
        if not self.db:
            QMessageBox.warning(self, "Warning", "Database not available")
            return
            
        try:
            # Get current user ID BEFORE opening session
            current_user_id = None
            if self.rbac_controller:
                current_user_id = self.rbac_controller.get_current_user_id()
            
            with self.db.get_session() as session:
                # Get the vehicle log record
                vehicle_log = session.query(VehicleLog).filter(VehicleLog.log_id == log_id).first()
                if not vehicle_log:
                    QMessageBox.warning(self, "Warning", "Vehicle log not found")
                    return
                
                # Update the plate number
                vehicle_log.original_plate_number = old_plate if not vehicle_log.original_plate_number else vehicle_log.original_plate_number
                vehicle_log.plate_number = new_plate
                vehicle_log.is_edited = True
                vehicle_log.edited_at = datetime.now()
                vehicle_log.edited_by = current_user_id if current_user_id else 1  # Save user ID to vehicle_log
                vehicle_log.edit_reason = "Manual edit via database page"
                
                # Flush to ensure vehicle_log changes are persisted
                session.flush()
                
                # Commit vehicle_log changes first
                try:
                    session.commit()
                    print(f"Successfully updated vehicle_log for plate '{old_plate}' to '{new_plate}'")
                except Exception as commit_error:
                    print(f"Error committing vehicle_log changes: {commit_error}")
                    import traceback
                    traceback.print_exc()
                    session.rollback()
                    raise
            
            # Create audit trail in separate session to avoid conflicts
            try:
                with self.db.get_session() as audit_session:
                    from src.db.models import PlateEditHistory
                    
                    edit_history = PlateEditHistory(
                        log_id=log_id,
                        old_plate_number=old_plate,
                        new_plate_number=new_plate,
                        edited_by=current_user_id if current_user_id else 1,
                        edit_reason="Manual edit via database page"
                    )
                    audit_session.add(edit_history)
                    audit_session.commit()
                    print("Audit trail created successfully")
            except Exception as audit_error:
                print(f"Warning: Could not create audit trail: {audit_error}")
                import traceback
                traceback.print_exc()
                # Continue - the main edit already succeeded
            
            # Update the table display (outside session context)
            self.vehicle_table.item(row, 2).setText(new_plate)
            
            # Show success message (outside session context)
            QMessageBox.information(
                self, 
                "Success", 
                f"Plate number updated from '{old_plate}' to '{new_plate}'"
            )
                
        except Exception as e:
            # Convert exception to string immediately to avoid session issues
            error_msg = str(e)
            QMessageBox.critical(self, "Error", f"Failed to update plate number: {error_msg}")
            import traceback
            traceback.print_exc()
    
    # ===== Pagination Methods =====
    
    def update_pagination_controls(self):
        """Update pagination control states and labels"""
        # Update page label
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        
        # Update records info
        start_record = (self.current_page - 1) * self.records_per_page + 1
        end_record = min(self.current_page * self.records_per_page, self.total_records)
        self.records_info_label.setText(f"Showing {start_record}-{end_record} of {self.total_records}")
        
        # Enable/disable navigation buttons
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)
    
    def go_to_first_page(self):
        """Go to first page"""
        if self.current_page != 1:
            self.current_page = 1
            self.load_vehicle_logs()
    
    def go_to_prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_vehicle_logs()
    
    def go_to_next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_vehicle_logs()
    
    def go_to_last_page(self):
        """Go to last page"""
        if self.current_page != self.total_pages:
            self.current_page = self.total_pages
            self.load_vehicle_logs()
    
    def change_records_per_page(self, value):
        """Change number of records per page"""
        try:
            new_records_per_page = int(value)
            if new_records_per_page != self.records_per_page:
                self.records_per_page = new_records_per_page
                self.current_page = 1  # Reset to first page
                self.load_vehicle_logs()
        except ValueError:
            pass
