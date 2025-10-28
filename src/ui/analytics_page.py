"""
Analytics Page for ANPR System
Displays comprehensive analytics, reports, and forecasts with charts
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QComboBox, QTableWidget, QTableWidgetItem, QGroupBox,
                             QDateEdit, QMessageBox, QFileDialog, QTabWidget, QScrollArea,
                             QGridLayout, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from datetime import datetime, timedelta
import os

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from src.db.database import Database
from src.analytics.analytics_engine import AnalyticsEngine
from src.analytics.export_utils import ReportExporter


class AnalyticsWorker(QThread):
    """Background worker for analytics calculations"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, db_manager, analysis_type, params):
        super().__init__()
        self.db_manager = db_manager
        self.analysis_type = analysis_type
        self.params = params
    
    def run(self):
        try:
            engine = AnalyticsEngine(self.db_manager.get_session())
            
            if self.analysis_type == 'summary':
                result = engine.get_summary_stats(self.params['period'])
            elif self.analysis_type == 'daily_trends':
                result = engine.get_daily_trends(self.params['start_date'], self.params['end_date'])
            elif self.analysis_type == 'peak_hours':
                result = engine.get_peak_hours(self.params.get('date'))
            elif self.analysis_type == 'revenue':
                result = engine.get_revenue_summary(self.params['start_date'], self.params['end_date'])
            elif self.analysis_type == 'forecast':
                result = engine.forecast_parking_demand(self.params['days'])
            elif self.analysis_type == 'patterns':
                result = engine.identify_patterns(self.params['weeks'])
            else:
                result = {}
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class StatCard(QFrame):
    """Custom widget for displaying statistics"""
    
    def __init__(self, title, value, subtitle="", color="#1a237e"):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10))
        title_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Value - store reference for updating
        self.value_label = QLabel(str(value))
        self.value_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)
        
        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setFont(QFont("Arial", 8))
            subtitle_label.setStyleSheet("color: #666;")
            layout.addWidget(subtitle_label)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setMinimumHeight(120)
    
    def set_value(self, value):
        """Update the card value"""
        self.value_label.setText(str(value))


if MATPLOTLIB_AVAILABLE:
    class ChartWidget(QWidget):
        """Widget for displaying matplotlib charts"""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.figure = Figure(figsize=(8, 5))
            self.canvas = FigureCanvas(self.figure)
            
            layout = QVBoxLayout()
            layout.addWidget(self.canvas)
            self.setLayout(layout)
        
        def plot_line_chart(self, data, title, xlabel, ylabel):
            """Plot line chart"""
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            dates = list(data.keys())
            values = list(data.values())
            
            ax.plot(dates, values, marker='o', linewidth=2, color='#1a237e')
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45)
            
            self.figure.tight_layout()
            self.canvas.draw()
        
        def plot_bar_chart(self, data, title, xlabel, ylabel):
            """Plot bar chart"""
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            labels = list(data.keys())
            values = list(data.values())
            
            ax.bar(labels, values, color='#1a237e')
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.tick_params(axis='x', rotation=45)
            
            self.figure.tight_layout()
            self.canvas.draw()
        
        def plot_multi_line_chart(self, data_dict, title, xlabel, ylabel):
            """Plot multiple lines on same chart"""
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            colors = ['#1a237e', '#c62828', '#2e7d32', '#f57c00']
            
            for idx, (label, data) in enumerate(data_dict.items()):
                dates = list(data.keys())
                values = list(data.values())
                ax.plot(dates, values, marker='o', linewidth=2, 
                       color=colors[idx % len(colors)], label=label)
            
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45)
            
            self.figure.tight_layout()
            self.canvas.draw()
else:
    class ChartWidget(QWidget):
        """Placeholder widget when matplotlib is not available"""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout()
            label = QLabel("Matplotlib not available\nInstall with: pip install matplotlib")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            self.setLayout(layout)
        
        def plot_line_chart(self, data, title, xlabel, ylabel):
            pass
        
        def plot_bar_chart(self, data, title, xlabel, ylabel):
            pass
        
        def plot_multi_line_chart(self, data_dict, title, xlabel, ylabel):
            pass


class AnalyticsPage(QWidget):
    """Main analytics page with comprehensive reporting"""
    
    def __init__(self, db_manager: Database):
        super().__init__()
        print("DEBUG: AnalyticsPage.__init__ called")
        print(f"DEBUG: MATPLOTLIB_AVAILABLE = {MATPLOTLIB_AVAILABLE}")
        self.db_manager = db_manager
        self.exporter = ReportExporter()
        
        print("DEBUG: Initializing analytics UI...")
        self.init_ui()
        print("DEBUG: Loading dashboard data...")
        self.load_dashboard()
        print("DEBUG: Loading forecast data...")
        self.load_forecast()
        print("DEBUG: AnalyticsPage initialization complete")
    
    def _get_engine(self):
        """Get analytics engine with a new session - must be used in with statement"""
        # This returns a context manager that yields (session, engine)
        class EngineContext:
            def __init__(self, db_manager):
                self.db_manager = db_manager
                self.session_context = None
                self.session = None
                
            def __enter__(self):
                self.session_context = self.db_manager.get_session()
                self.session = self.session_context.__enter__()
                return AnalyticsEngine(self.session)
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.session_context:
                    return self.session_context.__exit__(exc_type, exc_val, exc_tb)
        
        return EngineContext(self.db_manager)
    
    def init_ui(self):
        """Initialize the UI"""
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("📊 Analytics & Reports")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #1a237e;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Period selector
        header_layout.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Today", "This Week", "This Month", "Custom"])
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        header_layout.addWidget(self.period_combo)
        
        # Date range for custom period
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.setVisible(False)
        header_layout.addWidget(QLabel("From:"))
        header_layout.addWidget(self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setVisible(False)
        header_layout.addWidget(QLabel("To:"))
        header_layout.addWidget(self.end_date)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_dashboard)
        header_layout.addWidget(refresh_btn)
        
        # Export buttons
        export_pdf_btn = QPushButton("📄 Export PDF")
        export_pdf_btn.clicked.connect(self.export_pdf)
        header_layout.addWidget(export_pdf_btn)
        
        export_excel_btn = QPushButton("📊 Export Excel")
        export_excel_btn.clicked.connect(self.export_excel)
        header_layout.addWidget(export_excel_btn)
        
        main_layout.addLayout(header_layout)
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        
        # Dashboard tab
        self.dashboard_tab = self.create_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "📈 Dashboard")
        
        # Trends tab
        self.trends_tab = self.create_trends_tab()
        self.tabs.addTab(self.trends_tab, "📉 Trends")
        
        # Revenue tab
        self.revenue_tab = self.create_revenue_tab()
        self.tabs.addTab(self.revenue_tab, "💰 Revenue")
        
        # Forecast tab
        self.forecast_tab = self.create_forecast_tab()
        self.tabs.addTab(self.forecast_tab, "🔮 Forecast")
        
        main_layout.addWidget(self.tabs)
        
        self.setLayout(main_layout)
    
    def create_dashboard_tab(self):
        """Create dashboard overview tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Summary cards
        cards_layout = QGridLayout()
        
        self.entries_card = StatCard("Total Entries", "0", color="#2e7d32")
        self.exits_card = StatCard("Total Exits", "0", color="#c62828")
        self.occupancy_card = StatCard("Current Occupancy", "0", color="#f57c00")
        self.revenue_card = StatCard("Total Revenue", "NPR 0", color="#1a237e")
        
        cards_layout.addWidget(self.entries_card, 0, 0)
        cards_layout.addWidget(self.exits_card, 0, 1)
        cards_layout.addWidget(self.occupancy_card, 0, 2)
        cards_layout.addWidget(self.revenue_card, 0, 3)
        
        layout.addLayout(cards_layout)
        
        # Charts section
        if MATPLOTLIB_AVAILABLE:
            charts_layout = QHBoxLayout()
            
            # Peak hours chart
            peak_hours_group = QGroupBox("Peak Hours")
            peak_hours_layout = QVBoxLayout()
            self.peak_hours_chart = ChartWidget()
            peak_hours_layout.addWidget(self.peak_hours_chart)
            peak_hours_group.setLayout(peak_hours_layout)
            charts_layout.addWidget(peak_hours_group)
            
            # Daily trends chart
            daily_trends_group = QGroupBox("Daily Trends")
            daily_trends_layout = QVBoxLayout()
            self.daily_trends_chart = ChartWidget()
            daily_trends_layout.addWidget(self.daily_trends_chart)
            daily_trends_group.setLayout(daily_trends_layout)
            charts_layout.addWidget(daily_trends_group)
            
            layout.addLayout(charts_layout)
        
        # Patterns section
        patterns_group = QGroupBox("Usage Patterns")
        patterns_layout = QVBoxLayout()
        self.patterns_table = QTableWidget()
        self.patterns_table.setColumnCount(2)
        self.patterns_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.patterns_table.horizontalHeader().setStretchLastSection(True)
        patterns_layout.addWidget(self.patterns_table)
        patterns_group.setLayout(patterns_layout)
        layout.addWidget(patterns_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_trends_tab(self):
        """Create trends analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        if MATPLOTLIB_AVAILABLE:
            # Trend type selector
            selector_layout = QHBoxLayout()
            selector_layout.addWidget(QLabel("View:"))
            
            self.trend_type_combo = QComboBox()
            self.trend_type_combo.addItems(["Daily", "Weekly", "Monthly"])
            self.trend_type_combo.currentTextChanged.connect(self.load_trends)
            selector_layout.addWidget(self.trend_type_combo)
            selector_layout.addStretch()
            
            layout.addLayout(selector_layout)
            
            # Chart
            self.trends_chart = ChartWidget()
            layout.addWidget(self.trends_chart)
        else:
            layout.addWidget(QLabel("Matplotlib not available. Install with: pip install matplotlib"))
        
        widget.setLayout(layout)
        return widget
    
    def create_revenue_tab(self):
        """Create revenue analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Revenue summary cards
        cards_layout = QGridLayout()
        
        self.total_revenue_card = StatCard("Total Revenue", "NPR 0", color="#1a237e")
        self.avg_revenue_card = StatCard("Average Revenue", "NPR 0", color="#2e7d32")
        self.max_revenue_card = StatCard("Maximum Revenue", "NPR 0", color="#f57c00")
        self.total_hours_card = StatCard("Total Hours", "0 hrs", color="#c62828")
        
        cards_layout.addWidget(self.total_revenue_card, 0, 0)
        cards_layout.addWidget(self.avg_revenue_card, 0, 1)
        cards_layout.addWidget(self.max_revenue_card, 0, 2)
        cards_layout.addWidget(self.total_hours_card, 0, 3)
        
        layout.addLayout(cards_layout)
        
        # Revenue chart
        if MATPLOTLIB_AVAILABLE:
            revenue_chart_group = QGroupBox("Daily Revenue")
            revenue_chart_layout = QVBoxLayout()
            self.revenue_chart = ChartWidget()
            revenue_chart_layout.addWidget(self.revenue_chart)
            revenue_chart_group.setLayout(revenue_chart_layout)
            layout.addWidget(revenue_chart_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_forecast_tab(self):
        """Create forecast tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Forecast controls
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Forecast Days:"))
        
        self.forecast_days_combo = QComboBox()
        self.forecast_days_combo.addItems(["7", "14", "30"])
        controls_layout.addWidget(self.forecast_days_combo)
        
        forecast_btn = QPushButton("Generate Forecast")
        forecast_btn.clicked.connect(self.load_forecast)
        controls_layout.addWidget(forecast_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Forecast table
        forecast_group = QGroupBox("Demand Forecast")
        forecast_layout = QVBoxLayout()
        
        self.forecast_table = QTableWidget()
        self.forecast_table.setColumnCount(3)
        self.forecast_table.setHorizontalHeaderLabels(["Date", "Predicted Entries", "Confidence"])
        self.forecast_table.horizontalHeader().setStretchLastSection(True)
        forecast_layout.addWidget(self.forecast_table)
        
        forecast_group.setLayout(forecast_layout)
        layout.addWidget(forecast_group)
        
        # Revenue forecast
        revenue_forecast_group = QGroupBox("Revenue Forecast")
        revenue_forecast_layout = QVBoxLayout()
        
        self.revenue_forecast_table = QTableWidget()
        self.revenue_forecast_table.setColumnCount(3)
        self.revenue_forecast_table.setHorizontalHeaderLabels(["Date", "Predicted Revenue (NPR)", "Confidence"])
        self.revenue_forecast_table.horizontalHeader().setStretchLastSection(True)
        revenue_forecast_layout.addWidget(self.revenue_forecast_table)
        
        revenue_forecast_group.setLayout(revenue_forecast_layout)
        layout.addWidget(revenue_forecast_group)
        
        widget.setLayout(layout)
        return widget
    
    def on_period_changed(self, period):
        """Handle period selection change"""
        is_custom = period == "Custom"
        self.start_date.setVisible(is_custom)
        self.end_date.setVisible(is_custom)
        
        if not is_custom:
            self.load_dashboard()
    
    def get_date_range(self):
        """Get current date range based on selection"""
        period = self.period_combo.currentText()
        now = datetime.now()
        
        if period == "Today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == "This Week":
            start = now - timedelta(days=7)
            end = now
        elif period == "This Month":
            start = now - timedelta(days=30)
            end = now
        else:  # Custom
            start = datetime.combine(self.start_date.date().toPyDate(), datetime.min.time())
            end = datetime.combine(self.end_date.date().toPyDate(), datetime.max.time())
        
        return start, end
    
    def load_dashboard(self):
        """Load dashboard data"""
        try:
            start_date, end_date = self.get_date_range()
            
            with self._get_engine() as engine:
                # Get summary stats
                period_map = {
                    "Today": "today",
                    "This Week": "week",
                    "This Month": "month"
                }
                period = period_map.get(self.period_combo.currentText(), "today")
                summary = engine.get_summary_stats(period)
                
                # Update cards
                self.entries_card.set_value(summary['total_entries'])
                self.exits_card.set_value(summary['total_exits'])
                self.occupancy_card.set_value(summary['current_occupancy'])
                self.revenue_card.set_value(f"NPR {summary['total_revenue']:.2f}")
                
                # Load peak hours
                if MATPLOTLIB_AVAILABLE:
                    peak_hours = engine.get_peak_hours()
                    hourly_data = peak_hours['hourly_data']
                    
                    if hourly_data:
                        totals = {f"{h}:00": data['total'] for h, data in hourly_data.items()}
                        self.peak_hours_chart.plot_bar_chart(totals, "Peak Hours", "Hour", "Total Vehicles")
                    
                    # Load daily trends
                    daily_trends = engine.get_daily_trends(start_date, end_date)
                    if daily_trends:
                        entries = {date: data['entries'] for date, data in daily_trends.items()}
                        exits = {date: data['exits'] for date, data in daily_trends.items()}
                        self.daily_trends_chart.plot_multi_line_chart(
                            {'Entries': entries, 'Exits': exits},
                            "Daily Trends", "Date", "Count"
                        )
                
                # Load patterns
                patterns = engine.identify_patterns()
                self.patterns_table.setRowCount(0)
                
                pattern_data = [
                    ("Average Duration", f"{patterns['avg_duration_hours']:.2f} hours"),
                    ("Peak Day", patterns['peak_day']['day']),
                    ("Exit Rate", f"{patterns['exit_rate']:.2f}%"),
                    ("Current Occupancy", str(patterns['current_occupancy']))
                ]
            
            for metric, value in pattern_data:
                row = self.patterns_table.rowCount()
                self.patterns_table.insertRow(row)
                self.patterns_table.setItem(row, 0, QTableWidgetItem(metric))
                self.patterns_table.setItem(row, 1, QTableWidgetItem(value))
            
            # Load revenue tab
            self.load_revenue()
            
        except Exception as e:
            print(f"DEBUG: Dashboard load error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to load dashboard: {str(e)}")
    
    def load_trends(self):
        """Load trends based on selection"""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        try:
            trend_type = self.trend_type_combo.currentText()
            
            with self._get_engine() as engine:
                if trend_type == "Daily":
                    start_date, end_date = self.get_date_range()
                    trends = engine.get_daily_trends(start_date, end_date)
                    entries = {date: data['entries'] for date, data in trends.items()}
                    exits = {date: data['exits'] for date, data in trends.items()}
                    self.trends_chart.plot_multi_line_chart(
                        {'Entries': entries, 'Exits': exits},
                        "Daily Trends", "Date", "Count"
                    )
                
                elif trend_type == "Weekly":
                    trends = engine.get_weekly_trends(weeks=8)
                    entries = {week: data['entries'] for week, data in trends.items()}
                    exits = {week: data['exits'] for week, data in trends.items()}
                    self.trends_chart.plot_multi_line_chart(
                        {'Entries': entries, 'Exits': exits},
                        "Weekly Trends", "Week", "Count"
                    )
                
                elif trend_type == "Monthly":
                    trends = engine.get_monthly_trends(months=12)
                    entries = {month: data['entries'] for month, data in trends.items()}
                    exits = {month: data['exits'] for month, data in trends.items()}
                    self.trends_chart.plot_multi_line_chart(
                        {'Entries': entries, 'Exits': exits},
                        "Monthly Trends", "Month", "Count"
                    )
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load trends: {str(e)}")
    
    def load_revenue(self):
        """Load revenue analysis"""
        try:
            start_date, end_date = self.get_date_range()
            
            with self._get_engine() as engine:
                # Get revenue summary
                revenue = engine.get_revenue_summary(start_date, end_date)
                
                # Update cards
                self.total_revenue_card.set_value(f"NPR {revenue['total_revenue']:.2f}")
                self.avg_revenue_card.set_value(f"NPR {revenue['avg_revenue']:.2f}")
                self.max_revenue_card.set_value(f"NPR {revenue['max_revenue']:.2f}")
                self.total_hours_card.set_value(f"{revenue['total_hours']:.2f} hrs")
                
                # Load revenue chart
                if MATPLOTLIB_AVAILABLE:
                    daily_revenue = engine.get_daily_revenue(start_date, end_date)
                    if daily_revenue:
                        revenue_data = {date: data['revenue'] for date, data in daily_revenue.items()}
                        self.revenue_chart.plot_line_chart(revenue_data, "Daily Revenue", "Date", "Revenue (NPR)")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load revenue: {str(e)}")
    
    def load_forecast(self):
        """Load forecast data"""
        try:
            days = int(self.forecast_days_combo.currentText())
            print(f"DEBUG: Loading forecast for {days} days")
            
            with self._get_engine() as engine:
                # Demand forecast
                demand_forecast = engine.forecast_parking_demand(days)
                print(f"DEBUG: Demand forecast returned: {demand_forecast}")
                print(f"DEBUG: Forecast items count: {len(demand_forecast.get('forecast', []))}")
                
                self.forecast_table.setRowCount(0)
                
                forecast_items = demand_forecast.get('forecast', [])
                if not forecast_items:
                    # Add a message row if no forecast data
                    self.forecast_table.insertRow(0)
                    self.forecast_table.setItem(0, 0, QTableWidgetItem("No forecast available"))
                    self.forecast_table.setItem(0, 1, QTableWidgetItem("Need at least 7 days of historical data"))
                    self.forecast_table.setItem(0, 2, QTableWidgetItem("N/A"))
                else:
                    for item in forecast_items:
                        row = self.forecast_table.rowCount()
                        self.forecast_table.insertRow(row)
                        self.forecast_table.setItem(row, 0, QTableWidgetItem(item['date']))
                        self.forecast_table.setItem(row, 1, QTableWidgetItem(str(item['predicted_entries'])))
                        self.forecast_table.setItem(row, 2, QTableWidgetItem(item['confidence'].capitalize()))
                        print(f"DEBUG: Added forecast row: {item['date']} - {item['predicted_entries']}")
                
                # Revenue forecast
                revenue_forecast = engine.forecast_revenue(days)
                print(f"DEBUG: Revenue forecast returned: {revenue_forecast}")
                
                self.revenue_forecast_table.setRowCount(0)
                
                revenue_items = revenue_forecast.get('forecast', [])
                if not revenue_items:
                    # Add a message row if no forecast data
                    self.revenue_forecast_table.insertRow(0)
                    self.revenue_forecast_table.setItem(0, 0, QTableWidgetItem("No forecast available"))
                    self.revenue_forecast_table.setItem(0, 1, QTableWidgetItem("Need at least 7 days of historical data"))
                    self.revenue_forecast_table.setItem(0, 2, QTableWidgetItem("N/A"))
                else:
                    for item in revenue_items:
                        row = self.revenue_forecast_table.rowCount()
                        self.revenue_forecast_table.insertRow(row)
                        self.revenue_forecast_table.setItem(row, 0, QTableWidgetItem(item['date']))
                        self.revenue_forecast_table.setItem(row, 1, QTableWidgetItem(f"{item['predicted_revenue']:.2f}"))
                        self.revenue_forecast_table.setItem(row, 2, QTableWidgetItem(item['confidence'].capitalize()))
            
            print(f"DEBUG: Forecast loaded successfully - {days} days")
            # Don't show message box on auto-load
            # QMessageBox.information(self, "Success", f"Forecast generated for next {days} days")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate forecast: {str(e)}")
    
    def export_pdf(self):
        """Export report to PDF"""
        try:
            start_date, end_date = self.get_date_range()
            
            # Ensure dates are datetime objects
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            with self._get_engine() as engine:
                # Gather all report data
                report_data = {
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'summary': engine.get_summary_stats(self.period_combo.currentText().lower().replace('this ', '')),
                    'revenue': engine.get_revenue_summary(start_date, end_date),
                    'peak_hours': engine.get_peak_hours()['peak_hours'],
                    'patterns': engine.identify_patterns(),
                    'daily_trends': engine.get_daily_trends(start_date, end_date),
                    'forecast': engine.forecast_parking_demand(7)
                }
            
            filepath = self.exporter.export_to_pdf(report_data)
            QMessageBox.information(self, "Success", f"Report exported to:\n{filepath}")
            
            # Open file location
            os.startfile(os.path.dirname(filepath))
        
        except ImportError as e:
            QMessageBox.warning(self, "Missing Dependency", 
                              "PDF export requires reportlab.\nInstall with: pip install reportlab")
        except Exception as e:
            print(f"DEBUG: PDF export error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to export PDF: {str(e)}")
    
    def export_excel(self):
        """Export report to Excel"""
        try:
            start_date, end_date = self.get_date_range()
            
            # Ensure dates are datetime objects
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
            
            with self._get_engine() as engine:
                # Gather all report data
                report_data = {
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'summary': engine.get_summary_stats(self.period_combo.currentText().lower().replace('this ', '')),
                    'revenue': engine.get_revenue_summary(start_date, end_date),
                    'peak_hours': engine.get_peak_hours()['peak_hours'],
                    'patterns': engine.identify_patterns(),
                    'daily_trends': engine.get_daily_trends(start_date, end_date),
                    'forecast': engine.forecast_parking_demand(7)
                }
            
            filepath = self.exporter.export_to_excel(report_data)
            QMessageBox.information(self, "Success", f"Report exported to:\n{filepath}")
            
            # Open file location
            os.startfile(os.path.dirname(filepath))
        
        except ImportError as e:
            QMessageBox.warning(self, "Missing Dependency", 
                              "Excel export requires openpyxl.\nInstall with: pip install openpyxl")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export Excel: {str(e)}")
