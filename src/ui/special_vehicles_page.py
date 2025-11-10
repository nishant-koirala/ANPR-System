"""
Special Vehicles Management Page
Handles Stolen Vehicles and Staff Vehicles with Alert System
Integrated with ANPR System - Matches existing UI style
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QDateEdit, QGroupBox,
    QMessageBox, QHeaderView, QTabWidget, QTextEdit, QSpinBox, QDialog,
    QScrollArea, QFrame, QFormLayout, QCheckBox, QDialogButtonBox, QMenu
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime, timedelta, date
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from src.db.database import get_database
    from src.db.special_vehicles_db import SpecialVehiclesDB
    from src.db.special_vehicles_models import StolenVehicle, StaffVehicle
except ImportError as e:
    print(f"Import error: {e}")
    SpecialVehiclesDB = None


class SpecialVehiclesPage(QWidget):
    """Main page for managing stolen and staff vehicles"""
    
    # Signals for alert system
    stolen_vehicle_detected = pyqtSignal(dict)
    alert_sent = pyqtSignal(str, str)
    
    def __init__(self, rbac_controller=None, parent=None):
        super().__init__(parent)
        self.rbac_controller = rbac_controller
        
        # Initialize database
        try:
            from src.db.database import get_database
            self.db = get_database()
            # Pass the session factory (get_session method), not a session instance
            self.special_db = SpecialVehiclesDB(self.db.get_session)
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.db = None
            self.special_db = None
        
        self.init_ui()
        self.load_data()
        
        # Setup auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_statistics)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Page Header
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)
        
        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #3498db;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                padding: 10px 20px;
                margin-right: 5px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
        """)
        
        # Create tabs
        self.stolen_vehicles_tab = self.create_stolen_vehicles_tab()
        self.staff_vehicles_tab = self.create_staff_vehicles_tab()
        self.alert_config_tab = self.create_alert_config_tab()
        
        self.tab_widget.addTab(self.stolen_vehicles_tab, "🚨 Stolen Vehicles")
        self.tab_widget.addTab(self.staff_vehicles_tab, "👥 Staff Vehicles")
        self.tab_widget.addTab(self.alert_config_tab, "⚙️ Alert Configuration")
        
        main_layout.addWidget(self.tab_widget)
        
    def create_header(self):
        """Create page header with title and quick stats"""
        header_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("🚗 Special Vehicles Management")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        header_layout.addWidget(title_label)
        
        # Quick Stats Cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.stolen_card = self.create_stat_card("Stolen Vehicles", "0", "#e74c3c", "🚨")
        self.staff_card = self.create_stat_card("Staff Vehicles", "0", "#27ae60", "👥")
        self.alerts_card = self.create_stat_card("Active Alerts", "0", "#f39c12", "⚠️")
        self.detections_card = self.create_stat_card("Recent Detections", "0", "#3498db", "📊")
        
        stats_layout.addWidget(self.stolen_card)
        stats_layout.addWidget(self.staff_card)
        stats_layout.addWidget(self.alerts_card)
        stats_layout.addWidget(self.detections_card)
        
        header_layout.addLayout(stats_layout)
        return header_layout
    
    def create_stat_card(self, title, value, color, icon):
        """Create a statistics card widget"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        card.setStyleSheet(f"""
            QFrame {{
                background: {color};
                border-radius: 10px;
                padding: 15px;
            }}
            QLabel {{
                color: white;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        top_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 24))
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 28, QFont.Bold))
        value_label.setObjectName("stat_value")
        top_layout.addWidget(icon_label)
        top_layout.addStretch()
        top_layout.addWidget(value_label)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 11))
        
        layout.addLayout(top_layout)
        layout.addWidget(title_label)
        
        return card
    
    def create_stolen_vehicles_tab(self):
        """Create the Stolen Vehicles tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Action Bar
        action_bar = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Stolen Vehicle")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        add_btn.clicked.connect(self.show_add_stolen_vehicle_dialog)
        
        self.stolen_search_input = QLineEdit()
        self.stolen_search_input.setPlaceholderText("🔍 Search by plate number or owner name...")
        self.stolen_search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 13px;
            }
        """)
        self.stolen_search_input.textChanged.connect(self.search_stolen_vehicles)
        
        self.stolen_filter_combo = QComboBox()
        self.stolen_filter_combo.addItems(["All Status", "Active", "Recovered", "Archived"])
        self.stolen_filter_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 13px;
            }
        """)
        self.stolen_filter_combo.currentTextChanged.connect(self.filter_stolen_vehicles)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        refresh_btn.clicked.connect(self.load_stolen_vehicles)
        
        action_bar.addWidget(add_btn)
        action_bar.addWidget(self.stolen_search_input, 2)
        action_bar.addWidget(self.stolen_filter_combo)
        action_bar.addWidget(refresh_btn)
        layout.addLayout(action_bar)
        
        # Table
        self.stolen_table = QTableWidget()
        self.stolen_table.setColumnCount(7)
        self.stolen_table.setHorizontalHeaderLabels([
            "ID", "Plate Number", "Owner Name", "Vehicle Type", 
            "Color", "Reported Date", "Status"
        ])
        
        self.stolen_table.setStyleSheet("""
            QTableWidget {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                background: white;
                gridline-color: #ecf0f1;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #e74c3c;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        self.stolen_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stolen_table.setAlternatingRowColors(True)
        self.stolen_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stolen_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.stolen_table.customContextMenuRequested.connect(self.show_stolen_context_menu)
        self.stolen_table.doubleClicked.connect(self.view_stolen_vehicle_details)
        
        # Hide ID column
        self.stolen_table.setColumnHidden(0, True)
        
        layout.addWidget(self.stolen_table)
        
        return tab
    
    def create_staff_vehicles_tab(self):
        """Create the Staff Vehicles tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Action Bar
        action_bar = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Staff Vehicle")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #229954; }
        """)
        add_btn.clicked.connect(self.show_add_staff_vehicle_dialog)
        
        self.staff_search_input = QLineEdit()
        self.staff_search_input.setPlaceholderText("🔍 Search by plate number, staff name, or department...")
        self.staff_search_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 13px;
            }
        """)
        self.staff_search_input.textChanged.connect(self.search_staff_vehicles)
        
        self.staff_filter_combo = QComboBox()
        self.staff_filter_combo.addItems(["All Departments", "Management", "Security", "Operations", "Maintenance", "IT", "HR"])
        self.staff_filter_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 13px;
            }
        """)
        self.staff_filter_combo.currentTextChanged.connect(self.filter_staff_vehicles)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        refresh_btn.clicked.connect(self.load_staff_vehicles)
        
        action_bar.addWidget(add_btn)
        action_bar.addWidget(self.staff_search_input, 2)
        action_bar.addWidget(self.staff_filter_combo)
        action_bar.addWidget(refresh_btn)
        layout.addLayout(action_bar)
        
        # Table
        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(10)
        self.staff_table.setHorizontalHeaderLabels([
            "ID", "Plate Number", "Staff Name", "Department", "Position",
            "Vehicle Type", "Color", "Valid From", "Valid Until", "Status"
        ])
        
        self.staff_table.setStyleSheet("""
            QTableWidget {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                background: white;
                gridline-color: #ecf0f1;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #27ae60;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        self.staff_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.staff_table.setAlternatingRowColors(True)
        self.staff_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.staff_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.staff_table.customContextMenuRequested.connect(self.show_staff_context_menu)
        self.staff_table.doubleClicked.connect(self.view_staff_vehicle_details)
        
        # Hide ID column
        self.staff_table.setColumnHidden(0, True)
        
        layout.addWidget(self.staff_table)
        
        return tab
    
    def create_alert_config_tab(self):
        """Create the Alert Configuration tab"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(20)
        
        # Dashboard Alerts
        dashboard_group = self.create_dashboard_alert_group()
        layout.addWidget(dashboard_group)
        
        # Email Alerts
        email_group = self.create_email_alert_group()
        layout.addWidget(email_group)
        
        # Priority Settings
        priority_group = self.create_priority_settings_group()
        layout.addWidget(priority_group)
        
        # Save Button
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                padding: 12px 30px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #229954; }
        """)
        save_btn.clicked.connect(self.save_alert_configuration)
        
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        save_layout.addWidget(save_btn)
        save_layout.addStretch()
        layout.addLayout(save_layout)
        
        layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        return tab
    
    def create_dashboard_alert_group(self):
        """Create dashboard alert settings group"""
        group = QGroupBox("📊 Dashboard Alert Settings")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QFormLayout()
        
        self.dashboard_alert_enabled = QCheckBox("Enable Dashboard Alerts")
        self.dashboard_alert_enabled.setChecked(True)
        
        self.dashboard_sound_enabled = QCheckBox("Enable Alert Sound")
        self.dashboard_sound_enabled.setChecked(True)
        
        self.dashboard_popup_enabled = QCheckBox("Show Popup Notification")
        self.dashboard_popup_enabled.setChecked(True)
        
        self.dashboard_highlight_duration = QSpinBox()
        self.dashboard_highlight_duration.setRange(5, 300)
        self.dashboard_highlight_duration.setValue(30)
        self.dashboard_highlight_duration.setSuffix(" seconds")
        
        layout.addRow("Alert Status:", self.dashboard_alert_enabled)
        layout.addRow("Sound Alert:", self.dashboard_sound_enabled)
        layout.addRow("Popup Alert:", self.dashboard_popup_enabled)
        layout.addRow("Highlight Duration:", self.dashboard_highlight_duration)
        
        group.setLayout(layout)
        return group
    
    def create_email_alert_group(self):
        """Create email alert settings group"""
        group = QGroupBox("📧 Email Alert Settings")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #e74c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QFormLayout()
        
        self.email_alert_enabled = QCheckBox("Enable Email Alerts")
        self.email_alert_enabled.setChecked(True)
        
        self.email_recipients = QTextEdit()
        self.email_recipients.setPlaceholderText(
            "Enter email addresses (one per line):\n"
            "security@example.com\n"
            "manager@example.com"
        )
        self.email_recipients.setMaximumHeight(100)
        self.email_recipients.setStyleSheet("""
            QTextEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                font-size: 13px;
            }
        """)
        
        self.email_include_image = QCheckBox("Include Plate Image in Email")
        self.email_include_image.setChecked(True)
        
        self.email_include_location = QCheckBox("Include Camera Location")
        self.email_include_location.setChecked(True)
        
        layout.addRow("Email Status:", self.email_alert_enabled)
        layout.addRow("Recipients:", self.email_recipients)
        layout.addRow("", self.email_include_image)
        layout.addRow("", self.email_include_location)
        
        group.setLayout(layout)
        return group
    
    def create_priority_settings_group(self):
        """Create priority settings group"""
        group = QGroupBox("⚡ Alert Priority Settings")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QFormLayout()
        
        self.stolen_vehicle_priority = QComboBox()
        self.stolen_vehicle_priority.addItems(["Critical", "High", "Medium", "Low"])
        self.stolen_vehicle_priority.setCurrentText("Critical")
        
        self.alert_cooldown = QSpinBox()
        self.alert_cooldown.setRange(1, 60)
        self.alert_cooldown.setValue(5)
        self.alert_cooldown.setSuffix(" minutes")
        
        self.auto_archive_days = QSpinBox()
        self.auto_archive_days.setRange(0, 365)
        self.auto_archive_days.setValue(30)
        self.auto_archive_days.setSuffix(" days")
        self.auto_archive_days.setSpecialValueText("Never")
        
        layout.addRow("Stolen Vehicle Priority:", self.stolen_vehicle_priority)
        layout.addRow("Alert Cooldown:", self.alert_cooldown)
        layout.addRow("Auto-Archive After:", self.auto_archive_days)
        
        group.setLayout(layout)
        return group
    
    # ==================== DATA LOADING ====================
    
    def load_data(self):
        """Load all data"""
        self.load_statistics()
        self.load_stolen_vehicles()
        self.load_staff_vehicles()
        self.load_alert_configuration()
    
    def load_statistics(self):
        """Load and update statistics cards"""
        if not self.special_db:
            return
        
        try:
            stats = self.special_db.get_statistics()
            
            # Update stat cards
            self.update_stat_card(self.stolen_card, str(stats.get('stolen_vehicles_count', 0)))
            self.update_stat_card(self.staff_card, str(stats.get('staff_vehicles_count', 0)))
            self.update_stat_card(self.alerts_card, str(stats.get('active_alerts_count', 0)))
            self.update_stat_card(self.detections_card, str(stats.get('recent_detections_count', 0)))
            
        except Exception as e:
            print(f"Error loading statistics: {e}")
    
    def update_stat_card(self, card, value):
        """Update stat card value"""
        value_label = card.findChild(QLabel, "stat_value")
        if value_label:
            value_label.setText(value)
    
    def load_stolen_vehicles(self):
        """Load stolen vehicles into table"""
        if not self.special_db:
            return
        
        try:
            vehicles = self.special_db.get_all_stolen_vehicles()
            self.populate_stolen_table(vehicles)
        except Exception as e:
            print(f"Error loading stolen vehicles: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load stolen vehicles: {e}")
    
    def populate_stolen_table(self, vehicles):
        """Populate stolen vehicles table"""
        self.stolen_table.setRowCount(0)
        
        for vehicle in vehicles:
            row = self.stolen_table.rowCount()
            self.stolen_table.insertRow(row)
            
            self.stolen_table.setItem(row, 0, QTableWidgetItem(str(vehicle.id)))
            self.stolen_table.setItem(row, 1, QTableWidgetItem(vehicle.plate_number or ""))
            self.stolen_table.setItem(row, 2, QTableWidgetItem(vehicle.owner_name or ""))
            self.stolen_table.setItem(row, 3, QTableWidgetItem(vehicle.vehicle_type or ""))
            self.stolen_table.setItem(row, 4, QTableWidgetItem(vehicle.vehicle_color or ""))
            self.stolen_table.setItem(row, 5, QTableWidgetItem(vehicle.reported_date.strftime("%Y-%m-%d") if vehicle.reported_date else ""))
            
            # Status with color
            status_item = QTableWidgetItem(vehicle.status)
            if vehicle.status == 'Active':
                status_item.setForeground(QColor('#e74c3c'))
                status_item.setFont(QFont("Arial", 10, QFont.Bold))
            elif vehicle.status == 'Recovered':
                status_item.setForeground(QColor('#27ae60'))
            self.stolen_table.setItem(row, 6, status_item)
    
    def load_staff_vehicles(self):
        """Load staff vehicles into table"""
        if not self.special_db:
            return
        
        try:
            vehicles = self.special_db.get_all_staff_vehicles()
            self.populate_staff_table(vehicles)
        except Exception as e:
            print(f"Error loading staff vehicles: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load staff vehicles: {e}")
    
    def populate_staff_table(self, vehicles):
        """Populate staff vehicles table"""
        self.staff_table.setRowCount(0)
        
        today = date.today()
        
        for vehicle in vehicles:
            row = self.staff_table.rowCount()
            self.staff_table.insertRow(row)
            
            self.staff_table.setItem(row, 0, QTableWidgetItem(str(vehicle.id)))
            self.staff_table.setItem(row, 1, QTableWidgetItem(vehicle.plate_number or ""))
            self.staff_table.setItem(row, 2, QTableWidgetItem(vehicle.staff_name or ""))
            self.staff_table.setItem(row, 3, QTableWidgetItem(vehicle.department or ""))
            self.staff_table.setItem(row, 4, QTableWidgetItem(vehicle.position or ""))
            self.staff_table.setItem(row, 5, QTableWidgetItem(vehicle.vehicle_type or ""))
            self.staff_table.setItem(row, 6, QTableWidgetItem(vehicle.vehicle_color or ""))
            self.staff_table.setItem(row, 7, QTableWidgetItem(vehicle.valid_from.strftime("%Y-%m-%d") if vehicle.valid_from else ""))
            
            # Valid until with expiry warning
            valid_until_item = QTableWidgetItem(vehicle.valid_until.strftime("%Y-%m-%d") if vehicle.valid_until else "")
            if vehicle.valid_until:
                days_until_expiry = (vehicle.valid_until - today).days
                if days_until_expiry < 0:
                    valid_until_item.setForeground(QColor('#e74c3c'))  # Expired - red
                elif days_until_expiry <= 30:
                    valid_until_item.setForeground(QColor('#f39c12'))  # Expiring soon - orange
            self.staff_table.setItem(row, 8, valid_until_item)
            
            # Status with color
            status_item = QTableWidgetItem(vehicle.status)
            if vehicle.status == 'Active':
                status_item.setForeground(QColor('#27ae60'))
                status_item.setFont(QFont("Arial", 10, QFont.Bold))
            elif vehicle.status == 'Expired':
                status_item.setForeground(QColor('#e74c3c'))
            self.staff_table.setItem(row, 9, status_item)
    
    def load_alert_configuration(self):
        """Load alert configuration"""
        if not self.special_db:
            return
        
        try:
            config = self.special_db.get_alert_config()
            if config:
                self.dashboard_alert_enabled.setChecked(config.dashboard_alert_enabled)
                self.dashboard_sound_enabled.setChecked(config.dashboard_sound_enabled)
                self.dashboard_popup_enabled.setChecked(config.dashboard_popup_enabled)
                self.dashboard_highlight_duration.setValue(config.dashboard_highlight_duration)
                
                self.email_alert_enabled.setChecked(config.email_alert_enabled)
                self.email_recipients.setPlainText(config.email_recipients or "")
                self.email_include_image.setChecked(config.email_include_image)
                self.email_include_location.setChecked(config.email_include_location)
                
                self.stolen_vehicle_priority.setCurrentText(config.stolen_vehicle_priority)
                self.alert_cooldown.setValue(config.alert_cooldown_minutes)
                self.auto_archive_days.setValue(config.auto_archive_days)
        except Exception as e:
            print(f"Error loading alert configuration: {e}")
    
    # ==================== SEARCH AND FILTER ====================
    
    def search_stolen_vehicles(self):
        """Search stolen vehicles"""
        if not self.special_db:
            return
        
        search_term = self.stolen_search_input.text().strip()
        status = self.stolen_filter_combo.currentText()
        if status == "All Status":
            status = None
        
        try:
            if search_term:
                vehicles = self.special_db.search_stolen_vehicles(search_term, status)
            else:
                vehicles = self.special_db.get_all_stolen_vehicles(status)
            self.populate_stolen_table(vehicles)
        except Exception as e:
            print(f"Error searching stolen vehicles: {e}")
    
    def filter_stolen_vehicles(self):
        """Filter stolen vehicles by status"""
        self.search_stolen_vehicles()
    
    def search_staff_vehicles(self):
        """Search staff vehicles"""
        if not self.special_db:
            return
        
        search_term = self.staff_search_input.text().strip()
        department = self.staff_filter_combo.currentText()
        if department == "All Departments":
            department = None
        
        try:
            if search_term:
                vehicles = self.special_db.search_staff_vehicles(search_term, department)
            else:
                vehicles = self.special_db.get_all_staff_vehicles(department)
            self.populate_staff_table(vehicles)
        except Exception as e:
            print(f"Error searching staff vehicles: {e}")
    
    def filter_staff_vehicles(self):
        """Filter staff vehicles by department"""
        self.search_staff_vehicles()
    
    def save_alert_configuration(self):
        """Save alert configuration"""
        if not self.special_db:
            QMessageBox.warning(self, "Error", "Database not initialized")
            return
        
        try:
            # Get current user ID if available
            user_id = None
            if self.rbac_controller and hasattr(self.rbac_controller, 'auth_manager'):
                user_id = self.rbac_controller.get_current_user_id()
            
            # Save configuration
            success = self.special_db.update_alert_config(
                dashboard_alert_enabled=self.dashboard_alert_enabled.isChecked(),
                dashboard_sound_enabled=self.dashboard_sound_enabled.isChecked(),
                dashboard_popup_enabled=self.dashboard_popup_enabled.isChecked(),
                dashboard_highlight_duration=self.dashboard_highlight_duration.value(),
                email_alert_enabled=self.email_alert_enabled.isChecked(),
                email_recipients=self.email_recipients.toPlainText().strip(),
                email_include_image=self.email_include_image.isChecked(),
                email_include_location=self.email_include_location.isChecked(),
                stolen_vehicle_priority=self.stolen_vehicle_priority.currentText(),
                alert_cooldown_minutes=self.alert_cooldown.value(),
                auto_archive_days=self.auto_archive_days.value(),
                updated_by=user_id
            )
            
            if success:
                QMessageBox.information(self, "Success", "Alert configuration saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save configuration")
                
        except Exception as e:
            print(f"Error saving alert configuration: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")
    
    # ==================== DIALOG METHODS ====================
    
    def show_add_stolen_vehicle_dialog(self):
        """Show dialog to add stolen vehicle"""
        dialog = AddStolenVehicleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.add_stolen_vehicle(data)
    
    def show_add_staff_vehicle_dialog(self):
        """Show dialog to add staff vehicle"""
        dialog = AddStaffVehicleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.add_staff_vehicle(data)
    
    def add_stolen_vehicle(self, data):
        """Add stolen vehicle to database"""
        if not self.special_db:
            QMessageBox.warning(self, "Error", "Database not initialized")
            return
        
        try:
            # Get current user ID
            user_id = None
            if self.rbac_controller and hasattr(self.rbac_controller, 'auth_manager'):
                user_id = self.rbac_controller.get_current_user_id()
            
            vehicle_id = self.special_db.add_stolen_vehicle(
                plate_number=data['plate_number'],
                owner_name=data.get('owner_name'),
                vehicle_type=data.get('vehicle_type'),
                vehicle_color=data.get('vehicle_color'),
                contact_number=data.get('contact_number'),
                notes=data.get('notes'),
                reported_date=data['reported_date'],
                enable_dashboard_alert=data.get('enable_dashboard_alert', True),
                enable_email_alert=data.get('enable_email_alert', True),
                enable_sound_alert=data.get('enable_sound_alert', True),
                email_recipients=data.get('email_recipients'),
                created_by=user_id
            )
            
            if vehicle_id:
                QMessageBox.information(self, "Success", f"Stolen vehicle '{data['plate_number']}' added successfully!")
                self.load_stolen_vehicles()
                self.load_statistics()
            else:
                QMessageBox.warning(self, "Error", "Failed to add stolen vehicle")
                
        except Exception as e:
            print(f"Error adding stolen vehicle: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add stolen vehicle: {e}")
    
    def add_staff_vehicle(self, data):
        """Add staff vehicle to database"""
        if not self.special_db:
            QMessageBox.warning(self, "Error", "Database not initialized")
            return
        
        try:
            # Get current user ID
            user_id = None
            if self.rbac_controller and hasattr(self.rbac_controller, 'auth_manager'):
                user_id = self.rbac_controller.get_current_user_id()
            
            vehicle_id = self.special_db.add_staff_vehicle(
                plate_number=data['plate_number'],
                staff_name=data['staff_name'],
                department=data.get('department'),
                position=data.get('position'),
                vehicle_type=data.get('vehicle_type'),
                vehicle_color=data.get('vehicle_color'),
                contact_number=data.get('contact_number'),
                notes=data.get('notes'),
                valid_from=data['valid_from'],
                valid_until=data['valid_until'],
                free_parking=data.get('free_parking', True),
                priority_access=data.get('priority_access', False),
                created_by=user_id
            )
            
            if vehicle_id:
                QMessageBox.information(self, "Success", f"Staff vehicle '{data['plate_number']}' added successfully!")
                self.load_staff_vehicles()
                self.load_statistics()
            else:
                QMessageBox.warning(self, "Error", "Failed to add staff vehicle")
                
        except Exception as e:
            print(f"Error adding staff vehicle: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add staff vehicle: {e}")
    
    # ==================== CONTEXT MENU ====================
    
    def show_stolen_context_menu(self, position):
        """Show context menu for stolen vehicles table"""
        if self.stolen_table.rowCount() == 0:
            return
        
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #bdc3c7;
            }
            QMenu::item {
                padding: 8px 25px;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        view_action = menu.addAction("👁️ View Details")
        edit_action = menu.addAction("✏️ Edit")
        menu.addSeparator()
        recover_action = menu.addAction("✅ Mark as Recovered")
        archive_action = menu.addAction("📦 Archive")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Delete")
        
        action = menu.exec_(self.stolen_table.viewport().mapToGlobal(position))
        
        if action == view_action:
            self.view_stolen_vehicle_details()
        elif action == edit_action:
            self.edit_stolen_vehicle()
        elif action == recover_action:
            self.mark_stolen_vehicle_recovered()
        elif action == archive_action:
            self.archive_stolen_vehicle()
        elif action == delete_action:
            self.delete_stolen_vehicle()
    
    def show_staff_context_menu(self, position):
        """Show context menu for staff vehicles table"""
        if self.staff_table.rowCount() == 0:
            return
        
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #bdc3c7;
            }
            QMenu::item {
                padding: 8px 25px;
            }
            QMenu::item:selected {
                background-color: #27ae60;
                color: white;
            }
        """)
        
        view_action = menu.addAction("👁️ View Details")
        edit_action = menu.addAction("✏️ Edit")
        menu.addSeparator()
        extend_action = menu.addAction("📅 Extend Validity")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Delete")
        
        action = menu.exec_(self.staff_table.viewport().mapToGlobal(position))
        
        if action == view_action:
            self.view_staff_vehicle_details()
        elif action == edit_action:
            self.edit_staff_vehicle()
        elif action == extend_action:
            self.extend_staff_vehicle_validity()
        elif action == delete_action:
            self.delete_staff_vehicle()
    
    def view_stolen_vehicle_details(self):
        """View stolen vehicle details"""
        selected_rows = self.stolen_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        vehicle_id = int(self.stolen_table.item(row, 0).text())
        
        # Get vehicle from database
        if not self.special_db:
            return
        
        try:
            vehicle = self.special_db.get_stolen_vehicle_by_plate(
                self.stolen_table.item(row, 1).text()
            )
            if vehicle:
                dialog = VehicleDetailDialog(vehicle, "stolen", self)
                dialog.exec_()
        except Exception as e:
            print(f"Error viewing stolen vehicle details: {e}")
    
    def view_staff_vehicle_details(self):
        """View staff vehicle details"""
        selected_rows = self.staff_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        vehicle_id = int(self.staff_table.item(row, 0).text())
        
        # Get vehicle from database
        if not self.special_db:
            return
        
        try:
            vehicle = self.special_db.get_staff_vehicle_by_plate(
                self.staff_table.item(row, 1).text()
            )
            if vehicle:
                dialog = VehicleDetailDialog(vehicle, "staff", self)
                dialog.exec_()
        except Exception as e:
            print(f"Error viewing staff vehicle details: {e}")
    
    def edit_stolen_vehicle(self):
        """Edit stolen vehicle"""
        if self.stolen_table.rowCount() == 0:
            return
        
        current_row = self.stolen_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a stolen vehicle to edit")
            return
        
        try:
            # Get vehicle ID from table
            vehicle_id = int(self.stolen_table.item(current_row, 0).text())
            
            # Get vehicle data from database
            vehicle = self.special_db.get_stolen_vehicle_by_id(vehicle_id)
            if not vehicle:
                QMessageBox.warning(self, "Error", "Vehicle not found")
                return
            
            # Prepare vehicle data for dialog
            vehicle_data = {
                'id': vehicle.id,
                'plate_number': vehicle.plate_number,
                'owner_name': vehicle.owner_name or '',
                'vehicle_type': vehicle.vehicle_type or 'Car',
                'vehicle_color': vehicle.vehicle_color or '',
                'contact_number': vehicle.contact_number or '',
                'notes': vehicle.notes or '',
                'reported_date': vehicle.reported_date,
                'enable_dashboard_alert': vehicle.enable_dashboard_alert,
                'enable_email_alert': vehicle.enable_email_alert,
                'enable_sound_alert': vehicle.enable_sound_alert,
                'email_recipients': vehicle.email_recipients or ''
            }
            
            # Show edit dialog
            dialog = EditStolenVehicleDialog(vehicle_data, self)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                self.update_stolen_vehicle(vehicle_id, data)
                
        except Exception as e:
            print(f"Error editing stolen vehicle: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to edit stolen vehicle: {e}")
    
    def update_stolen_vehicle(self, vehicle_id, data):
        """Update stolen vehicle in database"""
        if not self.special_db:
            QMessageBox.warning(self, "Error", "Database not initialized")
            return
        
        try:
            # Get current user ID
            user_id = None
            if self.rbac_controller and hasattr(self.rbac_controller, 'auth_manager'):
                user_id = self.rbac_controller.get_current_user_id()
            
            success = self.special_db.update_stolen_vehicle(
                vehicle_id=vehicle_id,
                plate_number=data['plate_number'],
                owner_name=data.get('owner_name'),
                vehicle_type=data.get('vehicle_type'),
                vehicle_color=data.get('vehicle_color'),
                contact_number=data.get('contact_number'),
                notes=data.get('notes'),
                reported_date=data['reported_date'],
                enable_dashboard_alert=data.get('enable_dashboard_alert', True),
                enable_email_alert=data.get('enable_email_alert', True),
                enable_sound_alert=data.get('enable_sound_alert', True),
                email_recipients=data.get('email_recipients'),
                updated_by=user_id
            )
            
            if success:
                QMessageBox.information(self, "Success", f"Stolen vehicle '{data['plate_number']}' updated successfully!")
                self.load_stolen_vehicles()
                self.load_statistics()
            else:
                QMessageBox.warning(self, "Error", "Failed to update stolen vehicle")
                
        except Exception as e:
            print(f"Error updating stolen vehicle: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to update stolen vehicle: {e}")
    
    def edit_staff_vehicle(self):
        """Edit staff vehicle"""
        QMessageBox.information(self, "Coming Soon", "Edit functionality will be implemented soon!")
    
    def mark_stolen_vehicle_recovered(self):
        """Mark stolen vehicle as recovered"""
        selected_rows = self.stolen_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        vehicle_id = int(self.stolen_table.item(row, 0).text())
        plate_number = self.stolen_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, "Confirm Recovery",
            f"Mark vehicle '{plate_number}' as recovered?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                user_id = None
                if self.rbac_controller and hasattr(self.rbac_controller, 'auth_manager'):
                    user_id = self.rbac_controller.get_current_user_id()
                
                success = self.special_db.mark_stolen_vehicle_recovered(vehicle_id, user_id)
                if success:
                    QMessageBox.information(self, "Success", "Vehicle marked as recovered!")
                    self.load_stolen_vehicles()
                    self.load_statistics()
                else:
                    QMessageBox.warning(self, "Error", "Failed to update vehicle status")
            except Exception as e:
                print(f"Error marking vehicle as recovered: {e}")
                QMessageBox.critical(self, "Error", f"Failed to update: {e}")
    
    def archive_stolen_vehicle(self):
        """Archive stolen vehicle"""
        selected_rows = self.stolen_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        vehicle_id = int(self.stolen_table.item(row, 0).text())
        plate_number = self.stolen_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, "Confirm Archive",
            f"Archive vehicle '{plate_number}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.special_db.update_stolen_vehicle(vehicle_id, status='Archived')
                if success:
                    QMessageBox.information(self, "Success", "Vehicle archived!")
                    self.load_stolen_vehicles()
                    self.load_statistics()
                else:
                    QMessageBox.warning(self, "Error", "Failed to archive vehicle")
            except Exception as e:
                print(f"Error archiving vehicle: {e}")
                QMessageBox.critical(self, "Error", f"Failed to archive: {e}")
    
    def delete_stolen_vehicle(self):
        """Delete stolen vehicle"""
        selected_rows = self.stolen_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        vehicle_id = int(self.stolen_table.item(row, 0).text())
        plate_number = self.stolen_table.item(row, 1).text()
        
        reply = QMessageBox.warning(
            self, "Confirm Delete",
            f"Permanently delete vehicle '{plate_number}'?\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.special_db.delete_stolen_vehicle(vehicle_id)
                if success:
                    QMessageBox.information(self, "Success", "Vehicle deleted!")
                    self.load_stolen_vehicles()
                    self.load_statistics()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete vehicle")
            except Exception as e:
                print(f"Error deleting vehicle: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def delete_staff_vehicle(self):
        """Delete staff vehicle"""
        selected_rows = self.staff_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        vehicle_id = int(self.staff_table.item(row, 0).text())
        plate_number = self.staff_table.item(row, 1).text()
        
        reply = QMessageBox.warning(
            self, "Confirm Delete",
            f"Permanently delete vehicle '{plate_number}'?\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.special_db.delete_staff_vehicle(vehicle_id)
                if success:
                    QMessageBox.information(self, "Success", "Vehicle deleted!")
                    self.load_staff_vehicles()
                    self.load_statistics()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete vehicle")
            except Exception as e:
                print(f"Error deleting vehicle: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def extend_staff_vehicle_validity(self):
        """Extend staff vehicle validity"""
        QMessageBox.information(self, "Coming Soon", "Extend validity functionality will be implemented soon!")


# ==================== DIALOG CLASSES ====================

class AddStolenVehicleDialog(QDialog):
    """Dialog for adding stolen vehicle"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Stolen Vehicle")
        self.setModal(True)
        self.resize(500, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("e.g., BA 1 PA 1234")
        
        self.owner_input = QLineEdit()
        self.owner_input.setPlaceholderText("Owner's full name")
        
        self.vehicle_type_combo = QComboBox()
        self.vehicle_type_combo.addItems(["Car", "Motorcycle", "Truck", "Van", "SUV", "Bus", "Other"])
        
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("e.g., Red, Blue, White")
        
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Contact number")
        
        self.reported_date = QDateEdit()
        self.reported_date.setDate(QDate.currentDate())
        self.reported_date.setCalendarPopup(True)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes or description...")
        self.notes_input.setMaximumHeight(100)
        
        # Alert settings
        self.dashboard_alert_check = QCheckBox("Enable Dashboard Alert")
        self.dashboard_alert_check.setChecked(True)
        
        self.email_alert_check = QCheckBox("Enable Email Alert")
        self.email_alert_check.setChecked(True)
        
        self.email_recipients_input = QTextEdit()
        self.email_recipients_input.setPlaceholderText("Enter email addresses (one per line or comma-separated)\ne.g.:\npolice@example.com\nsecurity@example.com")
        self.email_recipients_input.setMaximumHeight(80)
        
        self.sound_alert_check = QCheckBox("Enable Sound Alert")
        self.sound_alert_check.setChecked(True)
        
        form_layout.addRow("Plate Number:*", self.plate_input)
        form_layout.addRow("Owner Name:", self.owner_input)
        form_layout.addRow("Vehicle Type:", self.vehicle_type_combo)
        form_layout.addRow("Color:", self.color_input)
        form_layout.addRow("Contact Number:", self.contact_input)
        form_layout.addRow("Reported Date:*", self.reported_date)
        form_layout.addRow("Notes:", self.notes_input)
        form_layout.addRow("", self.dashboard_alert_check)
        form_layout.addRow("", self.email_alert_check)
        form_layout.addRow("Email Recipients:", self.email_recipients_input)
        form_layout.addRow("", self.sound_alert_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def validate_and_accept(self):
        if not self.plate_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Plate number is required!")
            return
        self.accept()
    
    def get_data(self):
        return {
            'plate_number': self.plate_input.text().strip().upper(),
            'owner_name': self.owner_input.text().strip(),
            'vehicle_type': self.vehicle_type_combo.currentText(),
            'vehicle_color': self.color_input.text().strip(),
            'contact_number': self.contact_input.text().strip(),
            'notes': self.notes_input.toPlainText().strip(),
            'reported_date': self.reported_date.date().toPyDate(),
            'enable_dashboard_alert': self.dashboard_alert_check.isChecked(),
            'enable_email_alert': self.email_alert_check.isChecked(),
            'enable_sound_alert': self.sound_alert_check.isChecked(),
            'email_recipients': self.email_recipients_input.toPlainText().strip()
        }


class EditStolenVehicleDialog(QDialog):
    """Dialog for editing stolen vehicle"""
    
    def __init__(self, vehicle_data, parent=None):
        super().__init__(parent)
        self.vehicle_data = vehicle_data
        self.setWindowTitle("Edit Stolen Vehicle")
        self.setModal(True)
        self.resize(500, 650)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("e.g., BA 1 PA 1234")
        
        self.owner_input = QLineEdit()
        self.owner_input.setPlaceholderText("Owner's full name")
        
        self.vehicle_type_combo = QComboBox()
        self.vehicle_type_combo.addItems(["Car", "Motorcycle", "Truck", "Van", "SUV", "Bus", "Other"])
        
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("e.g., Red, Blue, White")
        
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Contact number")
        
        self.reported_date = QDateEdit()
        self.reported_date.setDate(QDate.currentDate())
        self.reported_date.setCalendarPopup(True)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes or description...")
        self.notes_input.setMaximumHeight(100)
        
        # Alert settings
        self.dashboard_alert_check = QCheckBox("Enable Dashboard Alert")
        self.dashboard_alert_check.setChecked(True)
        
        self.email_alert_check = QCheckBox("Enable Email Alert")
        self.email_alert_check.setChecked(True)
        
        self.email_recipients_input = QTextEdit()
        self.email_recipients_input.setPlaceholderText("Enter email addresses (one per line or comma-separated)\ne.g.:\nnarutouj16@gmail.com\npolice@example.com")
        self.email_recipients_input.setMaximumHeight(80)
        
        self.sound_alert_check = QCheckBox("Enable Sound Alert")
        self.sound_alert_check.setChecked(True)
        
        form_layout.addRow("Plate Number:*", self.plate_input)
        form_layout.addRow("Owner Name:", self.owner_input)
        form_layout.addRow("Vehicle Type:", self.vehicle_type_combo)
        form_layout.addRow("Color:", self.color_input)
        form_layout.addRow("Contact Number:", self.contact_input)
        form_layout.addRow("Reported Date:*", self.reported_date)
        form_layout.addRow("Notes:", self.notes_input)
        form_layout.addRow("", self.dashboard_alert_check)
        form_layout.addRow("", self.email_alert_check)
        form_layout.addRow("Email Recipients:", self.email_recipients_input)
        form_layout.addRow("", self.sound_alert_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_data(self):
        """Load existing vehicle data into form"""
        self.plate_input.setText(self.vehicle_data.get('plate_number', ''))
        self.owner_input.setText(self.vehicle_data.get('owner_name', ''))
        
        # Set vehicle type
        vehicle_type = self.vehicle_data.get('vehicle_type', 'Car')
        index = self.vehicle_type_combo.findText(vehicle_type)
        if index >= 0:
            self.vehicle_type_combo.setCurrentIndex(index)
        
        self.color_input.setText(self.vehicle_data.get('vehicle_color', ''))
        self.contact_input.setText(self.vehicle_data.get('contact_number', ''))
        
        # Set reported date
        if self.vehicle_data.get('reported_date'):
            from datetime import datetime
            if isinstance(self.vehicle_data['reported_date'], str):
                date_obj = datetime.strptime(self.vehicle_data['reported_date'], '%Y-%m-%d').date()
            else:
                date_obj = self.vehicle_data['reported_date']
            self.reported_date.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
        
        self.notes_input.setPlainText(self.vehicle_data.get('notes', ''))
        
        # Set alert checkboxes
        self.dashboard_alert_check.setChecked(self.vehicle_data.get('enable_dashboard_alert', True))
        self.email_alert_check.setChecked(self.vehicle_data.get('enable_email_alert', True))
        self.sound_alert_check.setChecked(self.vehicle_data.get('enable_sound_alert', True))
        
        # Set email recipients
        self.email_recipients_input.setPlainText(self.vehicle_data.get('email_recipients', ''))
    
    def validate_and_accept(self):
        if not self.plate_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Plate number is required!")
            return
        self.accept()
    
    def get_data(self):
        return {
            'plate_number': self.plate_input.text().strip().upper(),
            'owner_name': self.owner_input.text().strip(),
            'vehicle_type': self.vehicle_type_combo.currentText(),
            'vehicle_color': self.color_input.text().strip(),
            'contact_number': self.contact_input.text().strip(),
            'notes': self.notes_input.toPlainText().strip(),
            'reported_date': self.reported_date.date().toPyDate(),
            'enable_dashboard_alert': self.dashboard_alert_check.isChecked(),
            'enable_email_alert': self.email_alert_check.isChecked(),
            'enable_sound_alert': self.sound_alert_check.isChecked(),
            'email_recipients': self.email_recipients_input.toPlainText().strip()
        }


class AddStaffVehicleDialog(QDialog):
    """Dialog for adding staff vehicle"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Staff Vehicle")
        self.setModal(True)
        self.resize(500, 650)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Form
        form_layout = QFormLayout()
        
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("e.g., BA 1 PA 1234")
        
        self.staff_name_input = QLineEdit()
        self.staff_name_input.setPlaceholderText("Staff member's full name")
        
        self.department_combo = QComboBox()
        self.department_combo.addItems(["Management", "Security", "Operations", "Maintenance", "IT", "HR", "Other"])
        
        self.position_input = QLineEdit()
        self.position_input.setPlaceholderText("Job position/title")
        
        self.vehicle_type_combo = QComboBox()
        self.vehicle_type_combo.addItems(["Car", "Motorcycle", "Truck", "Van", "SUV", "Bus", "Other"])
        
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("e.g., Red, Blue, White")
        
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Contact number")
        
        self.valid_from = QDateEdit()
        self.valid_from.setDate(QDate.currentDate())
        self.valid_from.setCalendarPopup(True)
        
        self.valid_until = QDateEdit()
        self.valid_until.setDate(QDate.currentDate().addYears(1))
        self.valid_until.setCalendarPopup(True)
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Additional notes...")
        self.notes_input.setMaximumHeight(80)
        
        # Privileges
        self.free_parking_check = QCheckBox("Free Parking")
        self.free_parking_check.setChecked(True)
        
        self.priority_access_check = QCheckBox("Priority Access")
        self.priority_access_check.setChecked(False)
        
        form_layout.addRow("Plate Number:*", self.plate_input)
        form_layout.addRow("Staff Name:*", self.staff_name_input)
        form_layout.addRow("Department:", self.department_combo)
        form_layout.addRow("Position:", self.position_input)
        form_layout.addRow("Vehicle Type:", self.vehicle_type_combo)
        form_layout.addRow("Color:", self.color_input)
        form_layout.addRow("Contact Number:", self.contact_input)
        form_layout.addRow("Valid From:*", self.valid_from)
        form_layout.addRow("Valid Until:*", self.valid_until)
        form_layout.addRow("Notes:", self.notes_input)
        form_layout.addRow("", self.free_parking_check)
        form_layout.addRow("", self.priority_access_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def validate_and_accept(self):
        if not self.plate_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Plate number is required!")
            return
        if not self.staff_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Staff name is required!")
            return
        if self.valid_from.date() > self.valid_until.date():
            QMessageBox.warning(self, "Validation Error", "Valid From date must be before Valid Until date!")
            return
        self.accept()
    
    def get_data(self):
        return {
            'plate_number': self.plate_input.text().strip().upper(),
            'staff_name': self.staff_name_input.text().strip(),
            'department': self.department_combo.currentText(),
            'position': self.position_input.text().strip(),
            'vehicle_type': self.vehicle_type_combo.currentText(),
            'vehicle_color': self.color_input.text().strip(),
            'contact_number': self.contact_input.text().strip(),
            'notes': self.notes_input.toPlainText().strip(),
            'valid_from': self.valid_from.date().toPyDate(),
            'valid_until': self.valid_until.date().toPyDate(),
            'free_parking': self.free_parking_check.isChecked(),
            'priority_access': self.priority_access_check.isChecked()
        }


class VehicleDetailDialog(QDialog):
    """Dialog for viewing vehicle details"""
    
    def __init__(self, vehicle, vehicle_type, parent=None):
        super().__init__(parent)
        self.vehicle = vehicle
        self.vehicle_type = vehicle_type
        self.setWindowTitle(f"Vehicle Details - {vehicle.plate_number}")
        self.setModal(True)
        self.resize(500, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"🚗 {self.vehicle.plate_number}")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        details_layout = QFormLayout(scroll_widget)
        
        if self.vehicle_type == "stolen":
            details_layout.addRow("Owner Name:", QLabel(self.vehicle.owner_name or "N/A"))
            details_layout.addRow("Vehicle Type:", QLabel(self.vehicle.vehicle_type or "N/A"))
            details_layout.addRow("Color:", QLabel(self.vehicle.vehicle_color or "N/A"))
            details_layout.addRow("Contact:", QLabel(self.vehicle.contact_number or "N/A"))
            details_layout.addRow("Reported Date:", QLabel(self.vehicle.reported_date.strftime("%Y-%m-%d") if self.vehicle.reported_date else "N/A"))
            details_layout.addRow("Status:", QLabel(self.vehicle.status))
            if self.vehicle.recovered_date:
                details_layout.addRow("Recovered Date:", QLabel(self.vehicle.recovered_date.strftime("%Y-%m-%d")))
            details_layout.addRow("Dashboard Alert:", QLabel("✅ Enabled" if self.vehicle.enable_dashboard_alert else "❌ Disabled"))
            details_layout.addRow("Email Alert:", QLabel("✅ Enabled" if self.vehicle.enable_email_alert else "❌ Disabled"))
            details_layout.addRow("Sound Alert:", QLabel("✅ Enabled" if self.vehicle.enable_sound_alert else "❌ Disabled"))
        else:  # staff
            details_layout.addRow("Staff Name:", QLabel(self.vehicle.staff_name))
            details_layout.addRow("Department:", QLabel(self.vehicle.department or "N/A"))
            details_layout.addRow("Position:", QLabel(self.vehicle.position or "N/A"))
            details_layout.addRow("Vehicle Type:", QLabel(self.vehicle.vehicle_type or "N/A"))
            details_layout.addRow("Color:", QLabel(self.vehicle.vehicle_color or "N/A"))
            details_layout.addRow("Contact:", QLabel(self.vehicle.contact_number or "N/A"))
            details_layout.addRow("Valid From:", QLabel(self.vehicle.valid_from.strftime("%Y-%m-%d") if self.vehicle.valid_from else "N/A"))
            details_layout.addRow("Valid Until:", QLabel(self.vehicle.valid_until.strftime("%Y-%m-%d") if self.vehicle.valid_until else "N/A"))
            details_layout.addRow("Status:", QLabel(self.vehicle.status))
            details_layout.addRow("Free Parking:", QLabel("✅ Yes" if self.vehicle.free_parking else "❌ No"))
            details_layout.addRow("Priority Access:", QLabel("✅ Yes" if self.vehicle.priority_access else "❌ No"))
        
        if self.vehicle.notes:
            notes_label = QLabel(self.vehicle.notes)
            notes_label.setWordWrap(True)
            details_layout.addRow("Notes:", notes_label)
        
        details_layout.addRow("Created:", QLabel(self.vehicle.created_at.strftime("%Y-%m-%d %H:%M") if self.vehicle.created_at else "N/A"))
        details_layout.addRow("Updated:", QLabel(self.vehicle.updated_at.strftime("%Y-%m-%d %H:%M") if self.vehicle.updated_at else "N/A"))
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ==================== STANDALONE TESTING ====================

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = SpecialVehiclesPage()
    window.show()
    sys.exit(app.exec_())
