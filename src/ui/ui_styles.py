"""
Modern UI Styles for ANPR System
Centralized styling with professional design system
"""

# ===== COLOR PALETTE =====

class Colors:
    """Modern color palette"""
    # Primary Colors
    PRIMARY = "#2C3E50"           # Dark blue-gray
    PRIMARY_LIGHT = "#34495E"     # Lighter blue-gray
    PRIMARY_DARK = "#1A252F"      # Darker blue-gray
    
    ACCENT = "#3498DB"            # Bright blue
    ACCENT_HOVER = "#2980B9"      # Darker blue
    ACCENT_LIGHT = "#5DADE2"      # Lighter blue
    
    # Status Colors
    SUCCESS = "#27AE60"           # Green
    SUCCESS_LIGHT = "#2ECC71"     # Lighter green
    WARNING = "#E67E22"           # Orange
    WARNING_LIGHT = "#F39C12"     # Lighter orange
    DANGER = "#E74C3C"            # Red
    DANGER_LIGHT = "#EC7063"      # Lighter red
    INFO = "#1ABC9C"              # Cyan
    INFO_LIGHT = "#48C9B0"        # Lighter cyan
    
    # Neutral Colors
    BACKGROUND = "#ECF0F1"        # Light gray background
    CARD_BG = "#FFFFFF"           # White cards
    BORDER = "#BDC3C7"            # Gray borders
    BORDER_LIGHT = "#D5DBDB"      # Lighter borders
    
    TEXT_PRIMARY = "#2C3E50"      # Dark text
    TEXT_SECONDARY = "#7F8C8D"    # Gray text
    TEXT_LIGHT = "#95A5A6"        # Light gray text
    TEXT_WHITE = "#FFFFFF"        # White text
    
    HOVER = "#F8F9FA"             # Light hover
    SELECTED = "#E8F4F8"          # Light blue selected
    
    # Sidebar
    SIDEBAR_BG = "#2C3E50"
    SIDEBAR_HOVER = "#34495E"
    SIDEBAR_ACTIVE = "#3498DB"
    SIDEBAR_TEXT = "#ECF0F1"


# ===== TYPOGRAPHY =====

class Fonts:
    """Font settings"""
    FAMILY = "Segoe UI, Roboto, Arial, sans-serif"
    
    SIZE_TITLE = "24px"
    SIZE_HEADING = "18px"
    SIZE_SUBHEADING = "16px"
    SIZE_BODY = "13px"
    SIZE_SMALL = "11px"
    
    WEIGHT_LIGHT = "300"
    WEIGHT_NORMAL = "400"
    WEIGHT_MEDIUM = "500"
    WEIGHT_BOLD = "700"


# ===== SPACING =====

class Spacing:
    """Spacing constants"""
    XS = "4px"
    SM = "8px"
    MD = "16px"
    LG = "24px"
    XL = "32px"
    XXL = "48px"


# ===== EFFECTS =====

class Effects:
    """Visual effects"""
    BORDER_RADIUS = "8px"
    BORDER_RADIUS_SM = "4px"
    BORDER_RADIUS_LG = "12px"
    
    SHADOW_SM = "0 1px 3px rgba(0,0,0,0.12)"
    SHADOW_MD = "0 2px 8px rgba(0,0,0,0.15)"
    SHADOW_LG = "0 4px 16px rgba(0,0,0,0.2)"
    
    TRANSITION = "all 0.3s ease"
    TRANSITION_FAST = "all 0.15s ease"


# ===== GLOBAL STYLESHEET =====

def get_global_stylesheet():
    """Get the global application stylesheet"""
    return f"""
    /* ===== MAIN WINDOW ===== */
    QMainWindow {{
        background-color: {Colors.BACKGROUND};
        font-family: {Fonts.FAMILY};
        font-size: {Fonts.SIZE_BODY};
    }}
    
    QWidget {{
        font-family: {Fonts.FAMILY};
        color: {Colors.TEXT_PRIMARY};
        background-color: {Colors.BACKGROUND};
    }}
    
    /* Main window title bar styling */
    QMainWindow::title {{
        background-color: {Colors.PRIMARY};
        color: {Colors.TEXT_WHITE};
    }}
    
    /* ===== BUTTONS ===== */
    QPushButton {{
        background-color: {Colors.ACCENT};
        color: {Colors.TEXT_WHITE};
        border: none;
        border-radius: {Effects.BORDER_RADIUS};
        padding: 10px 20px;
        font-size: {Fonts.SIZE_BODY};
        font-weight: {Fonts.WEIGHT_MEDIUM};
        min-height: 40px;
        min-width: 80px;
    }}
    
    QPushButton:hover {{
        background-color: {Colors.ACCENT_HOVER};
    }}
    
    QPushButton:pressed {{
        background-color: {Colors.PRIMARY};
    }}
    
    QPushButton:disabled {{
        background-color: {Colors.BORDER};
        color: {Colors.TEXT_LIGHT};
    }}
    
    /* Success Button */
    QPushButton[class="success"] {{
        background-color: {Colors.SUCCESS};
    }}
    
    QPushButton[class="success"]:hover {{
        background-color: {Colors.SUCCESS_LIGHT};
    }}
    
    /* Danger Button */
    QPushButton[class="danger"] {{
        background-color: {Colors.DANGER};
    }}
    
    QPushButton[class="danger"]:hover {{
        background-color: {Colors.DANGER_LIGHT};
    }}
    
    /* Warning Button */
    QPushButton[class="warning"] {{
        background-color: {Colors.WARNING};
    }}
    
    QPushButton[class="warning"]:hover {{
        background-color: {Colors.WARNING_LIGHT};
    }}
    
    /* Secondary Button */
    QPushButton[class="secondary"] {{
        background-color: {Colors.CARD_BG};
        color: {Colors.TEXT_PRIMARY};
        border: 2px solid {Colors.BORDER};
    }}
    
    QPushButton[class="secondary"]:hover {{
        background-color: {Colors.HOVER};
        border-color: {Colors.ACCENT};
    }}
    
    /* ===== INPUTS ===== */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {Colors.CARD_BG};
        border: 2px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS_SM};
        padding: 8px 12px;
        font-size: {Fonts.SIZE_BODY};
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {Colors.ACCENT};
        background-color: {Colors.CARD_BG};
    }}
    
    QLineEdit:disabled, QTextEdit:disabled {{
        background-color: {Colors.BACKGROUND};
        color: {Colors.TEXT_LIGHT};
    }}
    
    /* ===== COMBOBOX ===== */
    QComboBox {{
        background-color: {Colors.CARD_BG};
        border: 2px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS_SM};
        padding: 8px 12px;
        font-size: {Fonts.SIZE_BODY};
        min-height: 36px;
    }}
    
    QComboBox:hover {{
        border-color: {Colors.ACCENT};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {Colors.TEXT_SECONDARY};
        margin-right: 10px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {Colors.CARD_BG};
        border: 1px solid {Colors.BORDER};
        selection-background-color: {Colors.SELECTED};
        selection-color: {Colors.TEXT_PRIMARY};
        padding: 4px;
    }}
    
    /* ===== TABLES ===== */
    QTableWidget {{
        background-color: {Colors.CARD_BG};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS};
        gridline-color: {Colors.BORDER_LIGHT};
        selection-background-color: {Colors.SELECTED};
        selection-color: {Colors.TEXT_PRIMARY};
    }}
    
    QTableWidget::item {{
        padding: 8px;
        border: none;
    }}
    
    QTableWidget::item:hover {{
        background-color: {Colors.HOVER};
    }}
    
    QTableWidget::item:selected {{
        background-color: {Colors.SELECTED};
    }}
    
    /* Fix corner button (top-left where rows/columns meet) */
    QTableWidget QTableCornerButton::section {{
        background-color: {Colors.PRIMARY};
        border: none;
        border-right: 1px solid {Colors.PRIMARY_LIGHT};
        border-bottom: 1px solid {Colors.PRIMARY_LIGHT};
    }}
    
    QHeaderView::section {{
        background-color: {Colors.PRIMARY};
        color: {Colors.TEXT_WHITE};
        padding: 12px 8px;
        border: none;
        border-right: 1px solid {Colors.PRIMARY_LIGHT};
        font-weight: {Fonts.WEIGHT_MEDIUM};
        font-size: {Fonts.SIZE_BODY};
    }}
    
    QHeaderView::section:hover {{
        background-color: {Colors.PRIMARY_LIGHT};
    }}
    
    /* Alternating row colors */
    QTableWidget::item:alternate {{
        background-color: {Colors.BACKGROUND};
    }}
    
    /* ===== TABS ===== */
    QTabWidget::pane {{
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS};
        background-color: {Colors.CARD_BG};
        top: -1px;
    }}
    
    QTabBar::tab {{
        background-color: {Colors.BACKGROUND};
        color: {Colors.TEXT_SECONDARY};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-bottom: none;
        border-top-left-radius: {Effects.BORDER_RADIUS_SM};
        border-top-right-radius: {Effects.BORDER_RADIUS_SM};
        padding: 10px 20px;
        margin-right: 2px;
        font-weight: {Fonts.WEIGHT_MEDIUM};
    }}
    
    QTabBar::tab:hover {{
        background-color: {Colors.HOVER};
        color: {Colors.TEXT_PRIMARY};
    }}
    
    QTabBar::tab:selected {{
        background-color: {Colors.CARD_BG};
        color: {Colors.ACCENT};
        border-bottom: 2px solid {Colors.ACCENT};
    }}
    
    /* ===== GROUP BOX ===== */
    QGroupBox {{
        background-color: {Colors.CARD_BG};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS};
        margin-top: 20px;
        padding: 20px 15px 15px 15px;
        font-weight: {Fonts.WEIGHT_MEDIUM};
        font-size: {Fonts.SIZE_BODY};
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 6px 12px;
        color: {Colors.PRIMARY};
        background-color: {Colors.CARD_BG};
        border-radius: {Effects.BORDER_RADIUS_SM};
        font-weight: {Fonts.WEIGHT_BOLD};
        font-size: {Fonts.SIZE_SUBHEADING};
    }}
    
    /* ===== LABELS ===== */
    QLabel {{
        color: {Colors.TEXT_PRIMARY};
        background-color: transparent;
    }}
    
    QLabel[class="title"] {{
        font-size: {Fonts.SIZE_TITLE};
        font-weight: {Fonts.WEIGHT_BOLD};
        color: {Colors.PRIMARY};
    }}
    
    QLabel[class="heading"] {{
        font-size: {Fonts.SIZE_HEADING};
        font-weight: {Fonts.WEIGHT_MEDIUM};
        color: {Colors.PRIMARY};
    }}
    
    QLabel[class="secondary"] {{
        color: {Colors.TEXT_SECONDARY};
        font-size: {Fonts.SIZE_SMALL};
    }}
    
    /* ===== SCROLLBAR ===== */
    QScrollBar:vertical {{
        background-color: {Colors.BACKGROUND};
        width: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {Colors.BORDER};
        border-radius: 6px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {Colors.TEXT_SECONDARY};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background-color: {Colors.BACKGROUND};
        height: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {Colors.BORDER};
        border-radius: 6px;
        min-width: 30px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {Colors.TEXT_SECONDARY};
    }}
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    
    /* ===== SPINBOX ===== */
    QSpinBox, QDoubleSpinBox {{
        background-color: {Colors.CARD_BG};
        border: 2px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS_SM};
        padding: 8px 12px;
        font-size: {Fonts.SIZE_BODY};
    }}
    
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {Colors.ACCENT};
    }}
    
    /* ===== DATE EDIT ===== */
    QDateEdit {{
        background-color: {Colors.CARD_BG};
        border: 2px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS_SM};
        padding: 8px 12px;
        font-size: {Fonts.SIZE_BODY};
        min-height: 36px;
    }}
    
    QDateEdit:focus {{
        border-color: {Colors.ACCENT};
    }}
    
    QDateEdit::drop-down {{
        border: none;
        width: 30px;
    }}
    
    /* ===== PROGRESS BAR ===== */
    QProgressBar {{
        background-color: {Colors.BACKGROUND};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS_SM};
        text-align: center;
        height: 24px;
    }}
    
    QProgressBar::chunk {{
        background-color: {Colors.ACCENT};
        border-radius: {Effects.BORDER_RADIUS_SM};
    }}
    
    /* ===== MENU ===== */
    QMenuBar {{
        background-color: {Colors.PRIMARY};
        color: {Colors.TEXT_WHITE};
        padding: 4px;
    }}
    
    QMenuBar::item {{
        background-color: transparent;
        padding: 8px 12px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {Colors.PRIMARY_LIGHT};
    }}
    
    QMenu {{
        background-color: {Colors.CARD_BG};
        border: 1px solid {Colors.BORDER};
        padding: 4px;
    }}
    
    QMenu::item {{
        padding: 8px 24px;
        border-radius: {Effects.BORDER_RADIUS_SM};
    }}
    
    QMenu::item:selected {{
        background-color: {Colors.SELECTED};
    }}
    
    /* ===== TOOLTIP ===== */
    QToolTip {{
        background-color: {Colors.PRIMARY};
        color: {Colors.TEXT_WHITE};
        border: none;
        padding: 8px 12px;
        border-radius: {Effects.BORDER_RADIUS_SM};
        font-size: {Fonts.SIZE_SMALL};
    }}
    
    /* ===== LIST WIDGET ===== */
    QListWidget {{
        background-color: {Colors.CARD_BG};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS};
        padding: 4px;
    }}
    
    QListWidget::item {{
        padding: 12px;
        border-radius: {Effects.BORDER_RADIUS_SM};
        margin: 2px;
    }}
    
    QListWidget::item:hover {{
        background-color: {Colors.HOVER};
    }}
    
    QListWidget::item:selected {{
        background-color: {Colors.SELECTED};
        color: {Colors.TEXT_PRIMARY};
    }}
    """


# ===== SIDEBAR STYLESHEET =====

def get_sidebar_stylesheet():
    """Get sidebar-specific stylesheet"""
    return f"""
    QListWidget {{
        background-color: {Colors.SIDEBAR_BG};
        border: none;
        padding: 8px 0px;
        outline: none;
    }}
    
    QListWidget::item {{
        color: {Colors.SIDEBAR_TEXT};
        padding: 16px 20px;
        border-left: 4px solid transparent;
        margin: 2px 0px;
        font-size: {Fonts.SIZE_BODY};
        font-weight: {Fonts.WEIGHT_MEDIUM};
    }}
    
    QListWidget::item:hover {{
        background-color: {Colors.SIDEBAR_HOVER};
        border-left-color: {Colors.ACCENT_LIGHT};
    }}
    
    QListWidget::item:selected {{
        background-color: {Colors.SIDEBAR_HOVER};
        border-left-color: {Colors.SIDEBAR_ACTIVE};
        color: {Colors.TEXT_WHITE};
    }}
    """


# ===== HELPER FUNCTIONS =====

def get_card_style(padding="16px"):
    """Get style for card-like containers"""
    return f"""
        background-color: {Colors.CARD_BG};
        border: 1px solid {Colors.BORDER_LIGHT};
        border-radius: {Effects.BORDER_RADIUS};
        padding: {padding};
    """


def get_button_style(color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER):
    """Get custom button style"""
    return f"""
        QPushButton {{
            background-color: {color};
            color: {Colors.TEXT_WHITE};
            border: none;
            border-radius: {Effects.BORDER_RADIUS};
            padding: 10px 20px;
            font-weight: {Fonts.WEIGHT_MEDIUM};
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
    """


def get_stat_card_style(color=Colors.ACCENT):
    """Get style for statistics cards"""
    return f"""
        QFrame {{
            background-color: {Colors.CARD_BG};
            border: 1px solid {Colors.BORDER_LIGHT};
            border-radius: {Effects.BORDER_RADIUS};
            border-left: 4px solid {color};
        }}
    """
