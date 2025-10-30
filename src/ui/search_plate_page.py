"""
Search Plate Page for ANPR System
Allows searching vehicle logs by plate number, date range, and other filters
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                           QLineEdit, QComboBox, QDateEdit, QTableWidget, QTableWidgetItem,
                           QGroupBox, QFormLayout, QMessageBox, QProgressBar, QHeaderView,
                           QAbstractItemView, QDialog, QTextEdit, QScrollArea, QFrame, QSplitter)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QColor, QFont
from datetime import datetime, timedelta
import os

# Import modern UI components
try:
    from .ui_components import ActionButton
    UI_COMPONENTS_AVAILABLE = True
except ImportError:
    UI_COMPONENTS_AVAILABLE = False

# Import database models
try:
    from src.db.models import VehicleLog, RawLog, Camera, ToggleMode
    from sqlalchemy import desc
except ImportError:
    print("Warning: Database models not available")

class SearchThread(QThread):
    """Background thread for database search operations"""
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    
    def __init__(self, session_factory, search_params):
        super().__init__()
        self.session_factory = session_factory
        self.search_params = search_params
    
    def run(self):
        try:
            with self.session_factory() as session:
                query = session.query(VehicleLog).join(RawLog).join(Camera)
                
                # Apply filters
                if self.search_params.get('plate_number'):
                    plate = self.search_params['plate_number'].strip().upper()
                    query = query.filter(VehicleLog.plate_number.ilike(f'%{plate}%'))
                
                if self.search_params.get('toggle_mode') and self.search_params['toggle_mode'] != 'ALL':
                    query = query.filter(VehicleLog.toggle_mode == ToggleMode(self.search_params['toggle_mode']))
                
                if self.search_params.get('date_from'):
                    query = query.filter(VehicleLog.captured_at >= self.search_params['date_from'])
                
                if self.search_params.get('date_to'):
                    # Add one day to include the full end date
                    end_date = self.search_params['date_to'] + timedelta(days=1)
                    query = query.filter(VehicleLog.captured_at < end_date)
                
                # Order by most recent first
                query = query.order_by(desc(VehicleLog.captured_at))
                
                # Limit results to prevent UI freeze
                results = query.limit(1000).all()
                
                # Convert to list of dictionaries for easier handling
                search_results = []
                for log in results:
                    # Get username from user ID if edited
                    edited_by_name = 'N/A'
                    if log.edited_by:
                        try:
                            from src.db.rbac_models import User
                            user = session.query(User).filter(User.user_id == log.edited_by).first()
                            if user:
                                edited_by_name = user.full_name or user.username
                        except:
                            edited_by_name = f'User ID: {log.edited_by}'
                    
                    search_results.append({
                        'log_id': log.log_id,
                        'plate_number': log.plate_number,
                        'original_plate_number': log.original_plate_number,
                        'is_edited': log.is_edited or False,
                        'edited_by': edited_by_name,  # Now shows username instead of ID
                        'edited_at': log.edited_at,
                        'edit_reason': log.edit_reason,
                        'toggle_mode': log.toggle_mode.value,
                        'captured_at': log.captured_at,
                        'camera_name': log.raw_log.camera.camera_name if log.raw_log and log.raw_log.camera else 'Unknown',
                        'duration_minutes': log.duration_minutes,
                        'duration_hours': log.duration_hours,
                        'amount': log.amount,
                        'session_id': log.session_id,
                        'location_info': log.location_info or '',
                        'notes': log.notes or '',
                        'confidence': log.raw_log.confidence if log.raw_log else None,
                        'plate_image_path': log.raw_log.plate_image_path if log.raw_log else None,
                        'thumbnail_path': log.raw_log.thumbnail_path if log.raw_log else None
                    })
                
                self.search_completed.emit(search_results)
                
        except Exception as e:
            self.search_failed.emit(str(e))


class SearchPlatePage(QWidget):
    """Search plate functionality page"""
    
    def __init__(self, session_factory, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.search_thread = None
        self.current_results = []
        self.rbac_controller = None  # Will be set by main window
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("🔍 Search Vehicle Plates")
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Create splitter for search form and results
        splitter = QSplitter(Qt.Vertical)
        
        # Search form section
        search_frame = self.create_search_form()
        splitter.addWidget(search_frame)
        
        # Results section
        results_frame = self.create_results_section()
        splitter.addWidget(results_frame)
        
        # Set splitter proportions (30% search form, 70% results)
        splitter.setSizes([200, 500])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
    def create_search_form(self):
        """Create the search form section"""
        group_box = QGroupBox("Search Filters")
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Plate number search
        self.plate_search_edit = QLineEdit()
        self.plate_search_edit.setPlaceholderText("Enter plate number (partial search supported)")
        self.plate_search_edit.setStyleSheet(self.get_input_style())
        self.plate_search_edit.setMinimumHeight(35)
        
        # Toggle mode filter
        self.toggle_mode_combo = QComboBox()
        self.toggle_mode_combo.addItems(['ALL', 'ENTRY', 'EXIT'])
        self.toggle_mode_combo.setStyleSheet(self.get_input_style())
        self.toggle_mode_combo.setMinimumHeight(35)
        
        # Date range filters
        self.date_from_edit = QDateEdit()
        self.date_from_edit.setDate(QDate.currentDate().addDays(-30))  # Default to last 30 days
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setStyleSheet(self.get_input_style())
        self.date_from_edit.setMinimumHeight(35)
        
        self.date_to_edit = QDateEdit()
        self.date_to_edit.setDate(QDate.currentDate())
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setStyleSheet(self.get_input_style())
        self.date_to_edit.setMinimumHeight(35)
        
        # Add form fields
        form_layout.addRow("Plate Number:", self.plate_search_edit)
        form_layout.addRow("Movement Type:", self.toggle_mode_combo)
        form_layout.addRow("Date From:", self.date_from_edit)
        form_layout.addRow("Date To:", self.date_to_edit)
        
        # Search buttons
        button_layout = QHBoxLayout()
        
        self.search_button = QPushButton("🔍 Search")
        self.search_button.setMinimumHeight(40)
        self.search_button.setStyleSheet(self.get_button_style("primary"))
        
        self.clear_button = QPushButton("🗑 Clear")
        self.clear_button.setMinimumHeight(40)
        self.clear_button.setStyleSheet(self.get_button_style("secondary"))
        
        self.export_button = QPushButton("📊 Export Results")
        self.export_button.setMinimumHeight(40)
        self.export_button.setStyleSheet(self.get_button_style("success"))
        self.export_button.setEnabled(False)
        
        # Check export permission
        if self.rbac_controller and not self.rbac_controller.can_export_data():
            self.export_button.setToolTip("Export permission required (Operator role or higher)")
            self.export_button.setEnabled(False)
            self.export_button.setStyleSheet(self.get_button_style("disabled"))
        
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.hide()
        
        # Add to form layout
        form_layout.addRow("", button_layout)
        form_layout.addRow("", self.progress_bar)
        
        group_box.setLayout(form_layout)
        return group_box
        
    def create_results_section(self):
        """Create the results display section"""
        group_box = QGroupBox("Search Results")
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        # Results info label
        self.results_info_label = QLabel("Enter search criteria and click Search to view results")
        self.results_info_label.setStyleSheet("color: #6c757d; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(self.results_info_label)
        
        # Results table
        self.results_table = QTableWidget()
        self.setup_results_table()
        layout.addWidget(self.results_table)
        
        group_box.setLayout(layout)
        return group_box
        
    def setup_results_table(self):
        """Setup the results table"""
        headers = ['Image', 'Plate Number', 'Type', 'Date/Time', 'Camera', 'Duration (hrs)', 'Amount (NPR)', 'Edited', 'Actions']
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        
        # Set table properties
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSortingEnabled(True)
        self.results_table.setRowHeight(0, 60)  # Set default row height for images
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(False)
        self.results_table.setColumnWidth(0, 100)  # Image
        self.results_table.setColumnWidth(1, 120)  # Plate Number
        self.results_table.setColumnWidth(2, 80)   # Type
        self.results_table.setColumnWidth(3, 150)  # Date/Time
        self.results_table.setColumnWidth(4, 100)  # Camera
        self.results_table.setColumnWidth(5, 80)   # Duration (hrs)
        self.results_table.setColumnWidth(6, 100)  # Amount (NPR)
        self.results_table.setColumnWidth(7, 80)   # Edited
        self.results_table.setColumnWidth(8, 100)  # Actions
        
        # Set column resize modes
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Image
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Plate Number
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Date/Time
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Camera
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Duration (hrs)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Amount (NPR)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Edited
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Actions
        
        # Use global stylesheet - no inline styling needed
        
    def setup_connections(self):
        """Setup signal connections"""
        self.search_button.clicked.connect(self.perform_search)
        self.clear_button.clicked.connect(self.clear_form)
        self.export_button.clicked.connect(self.export_results)
        self.results_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.plate_search_edit.returnPressed.connect(self.perform_search)
        
    def perform_search(self):
        """Perform the search operation"""
        # Validate inputs
        plate_number = self.plate_search_edit.text().strip()
        toggle_mode = self.toggle_mode_combo.currentText()
        date_from = self.date_from_edit.date().toPyDate()
        date_to = self.date_to_edit.date().toPyDate()
        
        if date_from > date_to:
            QMessageBox.warning(self, "Invalid Date Range", 
                              "Start date cannot be later than end date.")
            return
        
        # Prepare search parameters
        search_params = {
            'plate_number': plate_number,
            'toggle_mode': toggle_mode,
            'date_from': datetime.combine(date_from, datetime.min.time()),
            'date_to': datetime.combine(date_to, datetime.min.time())
        }
        
        # Start search in background thread
        self.start_search(search_params)
        
    def start_search(self, search_params):
        """Start search in background thread"""
        # Update UI state
        self.search_button.setEnabled(False)
        self.search_button.setText("Searching...")
        self.progress_bar.show()
        self.results_info_label.setText("Searching database...")
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.export_button.setEnabled(False)
        
        # Start search thread
        self.search_thread = SearchThread(self.session_factory, search_params)
        self.search_thread.search_completed.connect(self.on_search_completed)
        self.search_thread.search_failed.connect(self.on_search_failed)
        self.search_thread.start()
        
    def on_search_completed(self, results):
        """Handle search completion"""
        self.current_results = results
        
        # Update UI state
        self.search_button.setEnabled(True)
        self.search_button.setText("🔍 Search")
        self.progress_bar.hide()
        
        # Update results info
        count = len(results)
        if count == 0:
            self.results_info_label.setText("No results found matching your search criteria.")
        elif count == 1000:
            self.results_info_label.setText(f"Found {count}+ results (showing first 1000). Please refine your search for more specific results.")
        edited_count = sum(1 for r in results if r.get('is_edited'))
        self.results_info_label.setText(f"Found {len(results)} records ({edited_count} edited)")
        
        # Populate results table
        self.populate_results_table(results)
        
        # Enable export if we have results AND user has permission
        can_export = count > 0
        if self.rbac_controller:
            can_export = can_export and self.rbac_controller.can_export_data()
        self.export_button.setEnabled(can_export)
        
    def on_search_failed(self, error_message):
        """Handle search failure"""
        # Update UI state
        self.search_button.setEnabled(True)
        self.search_button.setText("🔍 Search")
        self.progress_bar.hide()
        
        # Show error message
        self.results_info_label.setText("Search failed. Please try again.")
        QMessageBox.critical(self, "Search Error", f"Search failed:\n{error_message}")
        
    def populate_results_table(self, results):
        """Populate the results table with search results"""
        self.current_results = results
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            # Set row height for images
            self.results_table.setRowHeight(row, 60)
            
            # Image thumbnail
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("border: 1px solid #ddd; background-color: #f8f9fa;")
            
            thumbnail_path = result.get('thumbnail_path')
            if thumbnail_path and os.path.exists(thumbnail_path):
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(70, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setText("No Image")
                    image_label.setStyleSheet("color: #6c757d; font-size: 10px;")
            else:
                image_label.setText("No Image")
                image_label.setStyleSheet("color: #6c757d; font-size: 10px;")
            
            self.results_table.setCellWidget(row, 0, image_label)
            
            # Plate Number (with edit indicator)
            plate_text = result['plate_number']
            if result.get('is_edited'):
                plate_text += " ✏️"
            plate_item = QTableWidgetItem(plate_text)
            if result.get('is_edited'):
                plate_item.setToolTip(f"Original: {result.get('original_plate_number', 'N/A')}\nEdited: {result.get('edited_at', 'N/A')}\nReason: {result.get('edit_reason', 'N/A')}")
            self.results_table.setItem(row, 1, plate_item)
            
            # Type (with color coding)
            type_item = QTableWidgetItem(result['toggle_mode'])
            if result['toggle_mode'] == 'ENTRY':
                type_item.setBackground(QColor('#d4edda'))  # Light green
            else:
                type_item.setBackground(QColor('#f8d7da'))  # Light red
            self.results_table.setItem(row, 2, type_item)
            
            # Date/Time
            date_str = result['captured_at'].strftime('%Y-%m-%d %H:%M:%S') if result['captured_at'] else ''
            self.results_table.setItem(row, 3, QTableWidgetItem(date_str))
            
            # Camera
            self.results_table.setItem(row, 4, QTableWidgetItem(result['camera_name']))
            
            # Duration in hours
            duration_text = ""
            if result['duration_hours'] is not None:
                duration_text = f"{result['duration_hours']:.2f}"
            elif result['duration_minutes'] is not None:
                duration_text = f"{(result['duration_minutes'] / 60.0):.2f}"
            self.results_table.setItem(row, 5, QTableWidgetItem(duration_text))
            
            # Amount
            amount_text = ""
            if result['amount'] is not None:
                amount_text = f"{result['amount']:.2f}"
            self.results_table.setItem(row, 6, QTableWidgetItem(amount_text))
            
            # Edited status
            edited_status = "Yes" if result.get('is_edited') else "No"
            edited_item = QTableWidgetItem(edited_status)
            if result.get('is_edited'):
                edited_item.setBackground(QColor('#fff3cd'))  # Light yellow
            self.results_table.setItem(row, 7, edited_item)
            
            # Actions button
            actions_widget = self.create_actions_widget(result)
            self.results_table.setCellWidget(row, 8, actions_widget)
    
    def create_actions_widget(self, result):
        """Create actions widget for table row"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        if UI_COMPONENTS_AVAILABLE:
            # Use modern ActionButton with text
            view_btn = ActionButton("View", icon="👁", variant="default", tooltip="View Details")
        else:
            # Fallback to regular buttons with text
            view_btn = QPushButton("👁 View")
            view_btn.setToolTip("View Details")
            view_btn.setStyleSheet("padding: 6px 12px; min-width: 60px; background-color: #3498DB; color: white; border-radius: 4px;")
        
        view_btn.clicked.connect(lambda: self.view_details(result))
        
        layout.addWidget(view_btn)
        # Edit button removed - editing only available in Vehicle Log page
        layout.addStretch()
        
        return widget
    
    def on_cell_double_clicked(self, row, column):
        """Handle double click on table cell"""
        if row < len(self.current_results):
            result = self.current_results[row]
            # Always view details on double-click (edit removed)
            self.view_details(result)
    
    def _format_duration(self, result):
        """Format duration for display"""
        if result['duration_hours'] is not None:
            return f"{result['duration_hours']:.2f}"
        elif result['duration_minutes'] is not None:
            return f"{(result['duration_minutes'] / 60.0):.2f}"
        else:
            return "N/A"
    
    def _format_amount(self, result):
        """Format amount for display"""
        if result['amount'] is not None:
            return f"{result['amount']:.2f}"
        else:
            return "N/A"
    
    def view_details(self, result):
        """View detailed information for a result"""
        details = f"""
Plate Details:
Log ID: {result['log_id']}
Plate Number: {result['plate_number']}
Original Plate: {result.get('original_plate_number', 'N/A')}
Type: {result['toggle_mode']}
Date/Time: {result['captured_at'].strftime('%Y-%m-%d %H:%M:%S') if result['captured_at'] else 'N/A'}
Camera: {result['camera_name']}
Duration: {self._format_duration(result)} hours
Amount: NPR {self._format_amount(result)}
Location: {result.get('location_info', 'N/A')}
Session ID: {result.get('session_id', 'N/A')}
Confidence: {result.get('confidence', 'N/A')}

Edit Information:
Edited: {'Yes' if result.get('is_edited') else 'No'}
Edited By: {result.get('edited_by', 'N/A')}
Edited At: {result.get('edited_at', 'N/A')}
Edit Reason: {result.get('edit_reason', 'N/A')}
        """
        
        QMessageBox.information(self, f"Details - {result['plate_number']}", details.strip())
    
    # Edit functionality removed from search page
    # Plate editing is only available in Vehicle Log page with proper permissions
            
    def clear_form(self):
        """Clear search form and results"""
        self.plate_search_edit.clear()
        self.toggle_mode_combo.setCurrentIndex(0)  # ALL
        self.date_from_edit.setDate(QDate.currentDate().addDays(-30))
        self.date_to_edit.setDate(QDate.currentDate())
        self.results_table.setRowCount(0)
        self.current_results = []
        self.results_info_label.setText("Enter search criteria and click Search to view results")
        self.export_button.setEnabled(False)
    
    def clear_search(self):
        """Legacy method - calls clear_form for compatibility"""
        self.clear_form()
        
    def export_results(self):
        """Export search results to CSV"""
        # Check permission
        if self.rbac_controller and not self.rbac_controller.can_export_data():
            QMessageBox.warning(
                self,
                "Permission Denied",
                f"You don't have permission to export data.\n\n"
                f"Your role: {self.rbac_controller.get_role_display_name()}\n"
                f"Required: Operator or higher"
            )
            return
        
        if not self.current_results:
            QMessageBox.information(self, "No Data", "No results to export.")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            import csv
            
            # Get save location
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Search Results", 
                f"plate_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )
            
            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Log ID', 'Plate Number', 'Type', 'Date/Time', 'Camera', 
                                'Duration (hrs)', 'Amount (NPR)', 'Location', 'Notes']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for result in self.current_results:
                        duration_hrs = ""
                        if result['duration_hours'] is not None:
                            duration_hrs = f"{result['duration_hours']:.2f}"
                        elif result['duration_minutes'] is not None:
                            duration_hrs = f"{(result['duration_minutes'] / 60.0):.2f}"
                        
                        amount_text = ""
                        if result['amount'] is not None:
                            amount_text = f"{result['amount']:.2f}"
                        
                        writer.writerow({
                            'Log ID': result['log_id'],
                            'Plate Number': result['plate_number'],
                            'Type': result['toggle_mode'],
                            'Date/Time': result['captured_at'].strftime('%Y-%m-%d %H:%M:%S'),
                            'Camera': result['camera_name'],
                            'Duration (hrs)': duration_hrs,
                            'Amount (NPR)': amount_text,
                            'Location': result['location_info'],
                            'Notes': result['notes']
                        })
                
                QMessageBox.information(self, "Export Successful", 
                                      f"Results exported successfully to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{str(e)}")
    
    def get_input_style(self):
        """Get stylesheet for input fields"""
        return """
            QLineEdit, QComboBox, QDateEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: white;
                color: #212529;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border-color: #007bff;
                outline: none;
            }
        """
    
    def get_button_style(self, button_type):
        """Get stylesheet for buttons"""
        if button_type == "primary":
            return """
                QPushButton {
                    background-color: #3498DB;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 12px 24px;
                    min-width: 100px;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background-color: #2980B9;
                }
                QPushButton:pressed {
                    background-color: #2C3E50;
                }
                QPushButton:disabled {
                    background-color: #95A5A6;
                }
            """
        elif button_type == "success":
            return """
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 12px 24px;
                    min-width: 120px;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
                QPushButton:pressed {
                    background-color: #1E8449;
                }
                QPushButton:disabled {
                    background-color: #95A5A6;
                }
            """
        elif button_type == "disabled":
            return """
                QPushButton {
                    background-color: #95A5A6;
                    color: #ECF0F1;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 12px 24px;
                    min-width: 120px;
                    min-height: 40px;
                }
            """
        else:  # secondary
            return """
                QPushButton {
                    background-color: #95A5A6;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    padding: 12px 24px;
                    min-width: 80px;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background-color: #7F8C8D;
                }
                QPushButton:pressed {
                    background-color: #2C3E50;
                }
            """
