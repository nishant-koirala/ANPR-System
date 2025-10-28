"""
Modern Reusable UI Components for ANPR System
Professional widgets with consistent styling
"""

from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QWidget, QLineEdit, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

try:
    from .ui_styles import Colors, Fonts, Spacing, Effects
except ImportError:
    from ui_styles import Colors, Fonts, Spacing, Effects


class ModernCard(QFrame):
    """Modern card container with shadow"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setup_ui(title)
    
    def setup_ui(self, title):
        """Setup card UI"""
        self.setObjectName("modernCard")
        self.setStyleSheet(f"""
            QFrame#modernCard {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {Effects.BORDER_RADIUS};
                padding: {Spacing.MD};
            }}
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(12)
        
        # Title if provided
        if title:
            title_label = QLabel(title)
            title_label.setProperty("class", "heading")
            title_label.setStyleSheet(f"""
                font-size: {Fonts.SIZE_HEADING};
                font-weight: {Fonts.WEIGHT_MEDIUM};
                color: {Colors.PRIMARY};
                margin-bottom: {Spacing.SM};
            """)
            self.main_layout.addWidget(title_label)
    
    def add_widget(self, widget):
        """Add widget to card"""
        self.main_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Add layout to card"""
        self.main_layout.addLayout(layout)


class StatsCard(QFrame):
    """Statistics display card with icon and value"""
    
    def __init__(self, title, value, icon="", color=Colors.ACCENT, parent=None):
        super().__init__(parent)
        self.title = title
        self.value_text = value
        self.icon = icon
        self.color = color
        self.setup_ui()
    
    def setup_ui(self):
        """Setup stats card UI"""
        self.setObjectName("statsCard")
        self.setStyleSheet(f"""
            QFrame#statsCard {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER_LIGHT};
                border-radius: {Effects.BORDER_RADIUS};
                border-left: 4px solid {self.color};
                padding: {Spacing.MD};
                min-width: 200px;
                min-height: 120px;
            }}
            QFrame#statsCard:hover {{
                border-left-width: 6px;
                background-color: {Colors.HOVER};
            }}
        """)
        
        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        # Icon and title row
        header_layout = QHBoxLayout()
        
        if self.icon:
            icon_label = QLabel(self.icon)
            icon_label.setStyleSheet(f"""
                font-size: 24px;
                color: {self.color};
            """)
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet(f"""
            font-size: {Fonts.SIZE_SMALL};
            color: {Colors.TEXT_SECONDARY};
            font-weight: {Fonts.WEIGHT_MEDIUM};
            text-transform: uppercase;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Value
        self.value_label = QLabel(str(self.value_text))
        self.value_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: {Fonts.WEIGHT_BOLD};
            color: {Colors.TEXT_PRIMARY};
            margin-top: {Spacing.SM};
        """)
        layout.addWidget(self.value_label)
        
        layout.addStretch()
    
    def set_value(self, value):
        """Update the value"""
        self.value_label.setText(str(value))


class ModernButton(QPushButton):
    """Modern styled button with variants"""
    
    def __init__(self, text, variant="primary", icon="", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self.icon_text = icon
        self.setup_style()
    
    def setup_style(self):
        """Setup button style based on variant"""
        colors = {
            "primary": (Colors.ACCENT, Colors.ACCENT_HOVER),
            "success": (Colors.SUCCESS, Colors.SUCCESS_LIGHT),
            "danger": (Colors.DANGER, Colors.DANGER_LIGHT),
            "warning": (Colors.WARNING, Colors.WARNING_LIGHT),
            "secondary": (Colors.CARD_BG, Colors.HOVER),
        }
        
        bg_color, hover_color = colors.get(self.variant, colors["primary"])
        text_color = Colors.TEXT_WHITE if self.variant != "secondary" else Colors.TEXT_PRIMARY
        border = f"2px solid {Colors.BORDER}" if self.variant == "secondary" else "none"
        
        if self.icon_text:
            self.setText(f"{self.icon_text}  {self.text()}")
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: {border};
                border-radius: {Effects.BORDER_RADIUS};
                padding: 10px 24px;
                font-size: {Fonts.SIZE_BODY};
                font-weight: {Fonts.WEIGHT_MEDIUM};
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_LIGHT};
            }}
        """)
        
        self.setCursor(Qt.PointingHandCursor)


class SearchInput(QLineEdit):
    """Modern search input with icon"""
    
    def __init__(self, placeholder="Search...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(f"🔍 {placeholder}")
        self.setup_style()
    
    def setup_style(self):
        """Setup search input style"""
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.CARD_BG};
                border: 2px solid {Colors.BORDER_LIGHT};
                border-radius: {Effects.BORDER_RADIUS};
                padding: 10px 16px;
                font-size: {Fonts.SIZE_BODY};
                color: {Colors.TEXT_PRIMARY};
                min-height: 40px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.ACCENT};
                background-color: {Colors.CARD_BG};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_LIGHT};
            }}
        """)


class SectionHeader(QLabel):
    """Section header with underline"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setup_style()
    
    def setup_style(self):
        """Setup header style"""
        self.setStyleSheet(f"""
            QLabel {{
                font-size: {Fonts.SIZE_HEADING};
                font-weight: {Fonts.WEIGHT_BOLD};
                color: {Colors.PRIMARY};
                padding-bottom: {Spacing.SM};
                border-bottom: 3px solid {Colors.ACCENT};
                margin-bottom: {Spacing.MD};
            }}
        """)


class InfoBadge(QLabel):
    """Small info badge/tag"""
    
    def __init__(self, text, color=Colors.INFO, parent=None):
        super().__init__(text, parent)
        self.badge_color = color
        self.setup_style()
    
    def setup_style(self):
        """Setup badge style"""
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self.badge_color};
                color: {Colors.TEXT_WHITE};
                border-radius: {Effects.BORDER_RADIUS_SM};
                padding: 4px 12px;
                font-size: {Fonts.SIZE_SMALL};
                font-weight: {Fonts.WEIGHT_MEDIUM};
            }}
        """)
        self.setAlignment(Qt.AlignCenter)


class ActionButton(QPushButton):
    """Small action button for tables"""
    
    def __init__(self, text, icon="", tooltip="", variant="default", parent=None):
        display_text = f"{icon} {text}" if icon else text
        super().__init__(display_text, parent)
        self.variant = variant
        if tooltip:
            self.setToolTip(tooltip)
        
        # Set size policy to ensure button doesn't shrink
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        self.setup_style()
    
    def setup_style(self):
        """Setup action button style"""
        # Color based on variant
        if self.variant == "danger":
            bg_color = Colors.DANGER
            hover_color = Colors.DANGER_LIGHT
        elif self.variant == "success":
            bg_color = Colors.SUCCESS
            hover_color = Colors.SUCCESS_LIGHT
        elif self.variant == "warning":
            bg_color = Colors.WARNING
            hover_color = Colors.WARNING_LIGHT
        else:
            bg_color = Colors.ACCENT
            hover_color = Colors.ACCENT_HOVER
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {Colors.TEXT_WHITE};
                border: none;
                border-radius: {Effects.BORDER_RADIUS_SM};
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 80px;
                min-height: 36px;
                max-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)


class EmptyState(QWidget):
    """Empty state placeholder"""
    
    def __init__(self, icon="📭", title="No data", message="", parent=None):
        super().__init__(parent)
        self.setup_ui(icon, title, message)
    
    def setup_ui(self, icon, title, message):
        """Setup empty state UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 64px;
            color: {Colors.TEXT_LIGHT};
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {Fonts.SIZE_HEADING};
            font-weight: {Fonts.WEIGHT_MEDIUM};
            color: {Colors.TEXT_SECONDARY};
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Message
        if message:
            message_label = QLabel(message)
            message_label.setStyleSheet(f"""
                font-size: {Fonts.SIZE_BODY};
                color: {Colors.TEXT_LIGHT};
            """)
            message_label.setAlignment(Qt.AlignCenter)
            message_label.setWordWrap(True)
            layout.addWidget(message_label)


class LoadingSpinner(QLabel):
    """Simple loading indicator"""
    
    def __init__(self, parent=None):
        super().__init__("⏳ Loading...", parent)
        self.setup_style()
    
    def setup_style(self):
        """Setup loading style"""
        self.setStyleSheet(f"""
            QLabel {{
                font-size: {Fonts.SIZE_BODY};
                color: {Colors.TEXT_SECONDARY};
                padding: {Spacing.LG};
            }}
        """)
        self.setAlignment(Qt.AlignCenter)


class Divider(QFrame):
    """Horizontal divider line"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Plain)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BORDER_LIGHT};
                max-height: 1px;
                margin: {Spacing.MD} 0px;
            }}
        """)


class PageHeader(QWidget):
    """Page header with title and actions"""
    
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setup_ui(title, subtitle)
    
    def setup_ui(self, title, subtitle):
        """Setup page header"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(4)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {Fonts.SIZE_TITLE};
            font-weight: {Fonts.WEIGHT_BOLD};
            color: {Colors.PRIMARY};
        """)
        layout.addWidget(title_label)
        
        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(f"""
                font-size: {Fonts.SIZE_BODY};
                color: {Colors.TEXT_SECONDARY};
            """)
            layout.addWidget(subtitle_label)
