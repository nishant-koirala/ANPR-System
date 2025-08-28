"""
Search Plate Page for ANPR System
Allows searching vehicle logs by plate number, date range, and other filters
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
                           QPushButton, QLineEdit, QComboBox, QDateEdit, QTableWidget, 
                           QTableWidgetItem, QHeaderView, QGroupBox, QSplitter, QProgressBar,
                           QMessageBox, QFileDialog, QMenu, QAction)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
import traceback
import os

# Import database models
try:
    from src.db.models import VehicleLog, RawLog, Camera, ToggleMode
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
                    search_results.append({
                        'log_id': log.log_id,
                        'plate_number': log.plate_number,
                        'original_plate_number': log.original_plate_number,
                        'is_edited': log.is_edited or False,
                        'edited_by': log.edited_by,
                        'edited_at': log.edited_at,
                        'edit_reason': log.edit_reason,
                        'toggle_mode': log.toggle_mode.value,
                        'captured_at': log.captured_at,
                        'camera_name': log.raw_log.camera.camera_name if log.raw_log and log.raw_log.camera else 'Unknown',
                        'duration_minutes': log.duration_minutes,
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
        headers = ['Image', 'Plate Number', 'Type', 'Date/Time', 'Camera', 'Duration (min)', 'Edited', 'Actions']
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
        self.results_table.setColumnWidth(0, 80)   # Image column
        self.results_table.setColumnWidth(1, 120)  # Plate Number
        self.results_table.setColumnWidth(2, 80)   # Type
        self.results_table.setColumnWidth(3, 150)  # Date/Time
        self.results_table.setColumnWidth(4, 100)  # Camera
        self.results_table.setColumnWidth(5, 80)   # Duration
        self.results_table.setColumnWidth(6, 80)   # Edited
        self.results_table.setColumnWidth(7, 100)  # Actions
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Log ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Plate Number
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Date/Time
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Camera
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Duration
        header.setSectionResizeMode(6, QHeaderView.Stretch)          # Location
        header.setSectionResizeMode(7, QHeaderView.Stretch)          # Notes
        
        # Style the table
        self.results_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: 1px solid #dee2e6;
                font-weight: bold;
            }
        """)
        
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
        
        # Enable export if we have results
        self.export_button.setEnabled(count > 0)
        
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
            
            # Duration
            duration = str(result['duration_minutes']) if result['duration_minutes'] else ''
            self.results_table.setItem(row, 5, QTableWidgetItem(duration))
            
            # Edited status
            edited_status = "Yes" if result.get('is_edited') else "No"
            edited_item = QTableWidgetItem(edited_status)
            if result.get('is_edited'):
                edited_item.setBackground(QColor('#fff3cd'))  # Light yellow
            self.results_table.setItem(row, 6, edited_item)
            
            # Actions button
            actions_widget = self.create_actions_widget(result)
            self.results_table.setCellWidget(row, 7, actions_widget)
    
    def create_actions_widget(self, result):
        """Create actions widget for table row"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # View details button
        view_btn = QPushButton("👁️")
        view_btn.setToolTip("View Details")
        view_btn.setMaximumSize(30, 30)
        view_btn.clicked.connect(lambda: self.view_details(result))
        
        # Edit button
        edit_btn = QPushButton("✏️")
        edit_btn.setToolTip("Edit Plate")
        edit_btn.setMaximumSize(30, 30)
        edit_btn.clicked.connect(lambda: self.edit_plate(result))
        
        layout.addWidget(view_btn)
        layout.addWidget(edit_btn)
        layout.addStretch()
        
        return widget
    
    def on_cell_double_clicked(self, row, column):
        """Handle double click on table cell"""
        if row < len(self.current_results):
            result = self.current_results[row]
            if column == 1:  # Plate number column
                self.edit_plate(result)
            else:
                self.view_details(result)
    
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
Duration: {result['duration_minutes']} minutes
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
    
    def edit_plate(self, result):
        """Edit plate number for a result"""
        from PyQt5.QtWidgets import QInputDialog
        
        current_plate = result['plate_number']
        new_plate, ok = QInputDialog.getText(
            self, 
            'Edit Plate Number', 
            f'Edit plate number for Log ID {result["log_id"]}:',
            text=current_plate
        )
        
        if ok and new_plate.strip() and new_plate.strip() != current_plate:
            # Here you would implement the database update logic
            QMessageBox.information(self, "Edit Plate", 
                                  f"Plate editing functionality needs to be connected to database.\n"
                                  f"Would change '{current_plate}' to '{new_plate.strip()}'")
            # TODO: Implement actual database update
            
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
                                'Duration (min)', 'Location', 'Notes']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for result in self.current_results:
                        writer.writerow({
                            'Log ID': result['log_id'],
                            'Plate Number': result['plate_number'],
                            'Type': result['toggle_mode'],
                            'Date/Time': result['captured_at'].strftime('%Y-%m-%d %H:%M:%S'),
                            'Camera': result['camera_name'],
                            'Duration (min)': result['duration_minutes'] or '',
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
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """
        elif button_type == "success":
            return """
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
                QPushButton:pressed {
                    background-color: #1e7e34;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                }
            """
        else:  # secondary
            return """
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                    padding: 10px 20px;
                }
                QPushButton:hover {
                    background-color: #545b62;
                }
                QPushButton:pressed {
                    background-color: #3d4142;
                }
            """
