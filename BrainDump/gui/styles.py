"""
styles.py
=========
Dark-theme QSS stylesheet and Qt-compatible colour constants for BrainDump GUI.

Usage
-----
    from gui.styles import STYLESHEET, CATEGORY_COLORS, PRIORITY_COLORS, Colors
    app.setStyleSheet(STYLESHEET)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Palette – base colours
# ---------------------------------------------------------------------------
class Colors:
    # Backgrounds
    BG_DARKEST   = "#0d0f12"
    BG_DARK      = "#13161b"
    BG_MID       = "#1a1e25"
    BG_PANEL     = "#1f2430"
    BG_CARD      = "#252b38"
    BG_HOVER     = "#2e3546"
    BG_SELECTED  = "#2a3f5f"

    # Borders
    BORDER       = "#2e3546"
    BORDER_FOCUS = "#4a90d9"

    # Text
    TEXT_PRIMARY   = "#e8eaf0"
    TEXT_SECONDARY = "#8892a4"
    TEXT_MUTED     = "#555f6e"
    TEXT_DISABLED  = "#3d4555"

    # Accent
    ACCENT        = "#4a90d9"
    ACCENT_HOVER  = "#5ba3f5"
    ACCENT_PRESS  = "#3a7ac8"

    # Status colours
    SUCCESS  = "#4caf7d"
    WARNING  = "#f0a04b"
    DANGER   = "#e05c5c"
    INFO     = "#5bc0de"

    # Overdue / deadline
    OVERDUE  = "#e05c5c"
    DUE_SOON = "#f0a04b"
    ON_TRACK = "#4caf7d"


# ---------------------------------------------------------------------------
# Category → Qt colour (hex) — mirrors constants.py Rich colours
# ---------------------------------------------------------------------------
CATEGORY_COLORS: dict[str, str] = {
    "Work":     "#4a90d9",   # blue
    "Study":    "#4caf7d",   # green
    "Personal": "#b57bee",   # magenta/purple
    "Shopping": "#f0c04b",   # yellow
    "Health":   "#e05c5c",   # red
    "Finance":  "#4dd0e1",   # cyan
    "Coding":   "#5ba3f5",   # bright blue
    "General":  "#8892a4",   # grey
}

# Category → subtle background badge colour (10% alpha of the main colour)
CATEGORY_BG: dict[str, str] = {
    "Work":     "#1a2a40",
    "Study":    "#1a3028",
    "Personal": "#2a1e40",
    "Shopping": "#3a3010",
    "Health":   "#3a1c1c",
    "Finance":  "#1a3035",
    "Coding":   "#1a2540",
    "General":  "#20242e",
}

# ---------------------------------------------------------------------------
# Priority → Qt colour
# ---------------------------------------------------------------------------
PRIORITY_COLORS: dict[str, str] = {
    "High":   "#e05c5c",
    "Medium": "#f0a04b",
    "Low":    "#4caf7d",
}

PRIORITY_BG: dict[str, str] = {
    "High":   "#3a1c1c",
    "Medium": "#3a2e10",
    "Low":    "#1a3028",
}

# ---------------------------------------------------------------------------
# QSS Stylesheet
# ---------------------------------------------------------------------------
STYLESHEET = f"""
/* ===== Global ===== */
* {{
    font-family: "Segoe UI", "SF Pro Display", "Inter", sans-serif;
    font-size: 13px;
    color: {Colors.TEXT_PRIMARY};
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {Colors.BG_DARK};
}}

QWidget {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_PRIMARY};
}}

/* ===== Menu Bar ===== */
QMenuBar {{
    background-color: {Colors.BG_DARKEST};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 2px 4px;
    spacing: 2px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}}

QMenuBar::item:selected, QMenuBar::item:pressed {{
    background-color: {Colors.BG_HOVER};
}}

QMenu {{
    background-color: {Colors.BG_PANEL};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px 0;
}}

QMenu::item {{
    padding: 6px 28px 6px 14px;
    border-radius: 4px;
    margin: 1px 4px;
}}

QMenu::item:selected {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}

QMenu::item:disabled {{
    color: {Colors.TEXT_DISABLED};
}}

QMenu::separator {{
    height: 1px;
    background: {Colors.BORDER};
    margin: 4px 10px;
}}

/* ===== Tool Bar ===== */
QToolBar {{
    background-color: {Colors.BG_DARKEST};
    border-bottom: 1px solid {Colors.BORDER};
    padding: 4px 8px;
    spacing: 4px;
}}

QToolBar::separator {{
    width: 1px;
    background: {Colors.BORDER};
    margin: 4px 6px;
}}

QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 10px;
    color: {Colors.TEXT_PRIMARY};
    font-size: 12px;
}}

QToolButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.BORDER};
}}

QToolButton:pressed {{
    background-color: {Colors.BG_SELECTED};
}}

QToolButton:checked {{
    background-color: {Colors.BG_SELECTED};
    border-color: {Colors.ACCENT};
    color: {Colors.ACCENT};
}}

/* ===== Status Bar ===== */
QStatusBar {{
    background-color: {Colors.BG_DARKEST};
    border-top: 1px solid {Colors.BORDER};
    color: {Colors.TEXT_SECONDARY};
    font-size: 12px;
    padding: 2px 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* ===== Splitter ===== */
QSplitter::handle {{
    background-color: {Colors.BORDER};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

/* ===== Scroll Bars ===== */
QScrollBar:vertical {{
    background: {Colors.BG_DARK};
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {Colors.BORDER};
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Colors.TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {Colors.BG_DARK};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {Colors.BORDER};
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {Colors.TEXT_MUTED};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ===== Table View ===== */
QTableView {{
    background-color: {Colors.BG_DARK};
    alternate-background-color: {Colors.BG_MID};
    gridline-color: {Colors.BORDER};
    border: none;
    selection-background-color: {Colors.BG_SELECTED};
    selection-color: {Colors.TEXT_PRIMARY};
}}

QTableView::item {{
    padding: 6px 8px;
    border: none;
}}

QTableView::item:selected {{
    background-color: {Colors.BG_SELECTED};
    color: {Colors.TEXT_PRIMARY};
}}

QTableView::item:hover {{
    background-color: {Colors.BG_HOVER};
}}

QHeaderView {{
    background-color: {Colors.BG_DARKEST};
    border: none;
}}

QHeaderView::section {{
    background-color: {Colors.BG_DARKEST};
    color: {Colors.TEXT_SECONDARY};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid {Colors.BORDER};
    border-bottom: 1px solid {Colors.BORDER};
}}

QHeaderView::section:hover {{
    background-color: {Colors.BG_MID};
    color: {Colors.TEXT_PRIMARY};
}}

QHeaderView::section:last {{
    border-right: none;
}}

/* ===== Push Buttons ===== */
QPushButton {{
    background-color: {Colors.BG_CARD};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.ACCENT};
    color: {Colors.ACCENT_HOVER};
}}

QPushButton:pressed {{
    background-color: {Colors.BG_SELECTED};
    border-color: {Colors.ACCENT_PRESS};
}}

QPushButton:disabled {{
    background-color: {Colors.BG_MID};
    color: {Colors.TEXT_DISABLED};
    border-color: {Colors.BORDER};
}}

QPushButton#primaryButton {{
    background-color: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
    color: white;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: {Colors.ACCENT_HOVER};
    border-color: {Colors.ACCENT_HOVER};
    color: white;
}}

QPushButton#primaryButton:pressed {{
    background-color: {Colors.ACCENT_PRESS};
}}

QPushButton#dangerButton {{
    background-color: transparent;
    border-color: {Colors.DANGER};
    color: {Colors.DANGER};
}}

QPushButton#dangerButton:hover {{
    background-color: {Colors.DANGER};
    color: white;
}}

QPushButton#successButton {{
    background-color: transparent;
    border-color: {Colors.SUCCESS};
    color: {Colors.SUCCESS};
}}

QPushButton#successButton:hover {{
    background-color: {Colors.SUCCESS};
    color: white;
}}

QPushButton#iconButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 8px;
    min-width: 28px;
    font-size: 15px;
}}

QPushButton#iconButton:hover {{
    background-color: {Colors.BG_HOVER};
    border-color: {Colors.BORDER};
}}

/* ===== Line Edit ===== */
QLineEdit {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.BG_SELECTED};
}}

QLineEdit:focus {{
    border-color: {Colors.ACCENT};
    background-color: {Colors.BG_PANEL};
}}

QLineEdit:disabled {{
    background-color: {Colors.BG_MID};
    color: {Colors.TEXT_DISABLED};
}}

QLineEdit::placeholder {{
    color: {Colors.TEXT_MUTED};
}}

/* ===== Text Edit ===== */
QPlainTextEdit, QTextEdit {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 8px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.BG_SELECTED};
}}

QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {Colors.ACCENT};
}}

/* ===== Combo Box ===== */
QComboBox {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    color: {Colors.TEXT_PRIMARY};
    min-width: 100px;
}}

QComboBox:focus {{
    border-color: {Colors.ACCENT};
}}

QComboBox:hover {{
    border-color: {Colors.ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {Colors.TEXT_SECONDARY};
    width: 0;
    height: 0;
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_PANEL};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    selection-background-color: {Colors.BG_HOVER};
    selection-color: {Colors.TEXT_PRIMARY};
    padding: 4px;
}}

/* ===== Check Box ===== */
QCheckBox {{
    color: {Colors.TEXT_PRIMARY};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {Colors.BORDER};
    background-color: {Colors.BG_CARD};
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.ACCENT};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
}}

/* ===== Date/Time Edit ===== */
QDateTimeEdit {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 7px 10px;
    color: {Colors.TEXT_PRIMARY};
}}

QDateTimeEdit:focus {{
    border-color: {Colors.ACCENT};
}}

QDateTimeEdit::drop-down {{
    border: none;
    width: 24px;
}}

QCalendarWidget {{
    background-color: {Colors.BG_PANEL};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
}}

QCalendarWidget QAbstractItemView {{
    background-color: {Colors.BG_PANEL};
    selection-background-color: {Colors.ACCENT};
}}

/* ===== Label ===== */
QLabel {{
    background: transparent;
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#sectionHeader {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {Colors.TEXT_MUTED};
    text-transform: uppercase;
    padding: 2px 0;
}}

QLabel#titleLabel {{
    font-size: 18px;
    font-weight: 700;
    color: {Colors.TEXT_PRIMARY};
}}

QLabel#subtitleLabel {{
    font-size: 12px;
    color: {Colors.TEXT_SECONDARY};
}}

QLabel#statNumber {{
    font-size: 28px;
    font-weight: 700;
    color: {Colors.ACCENT};
}}

QLabel#statLabel {{
    font-size: 11px;
    color: {Colors.TEXT_SECONDARY};
}}

/* ===== Frames / Panels ===== */
QFrame#sidebarFrame {{
    background-color: {Colors.BG_DARKEST};
    border-right: 1px solid {Colors.BORDER};
}}

QFrame#cardFrame {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
}}

QFrame#statsCard {{
    background-color: {Colors.BG_CARD};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 8px;
}}

QFrame#separator {{
    background-color: {Colors.BORDER};
    max-height: 1px;
    min-height: 1px;
}}

/* ===== Group Box ===== */
QGroupBox {{
    background-color: {Colors.BG_PANEL};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
    color: {Colors.TEXT_SECONDARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {Colors.TEXT_SECONDARY};
    font-size: 11px;
    letter-spacing: 0.5px;
}}

/* ===== Tab Widget ===== */
QTabWidget::pane {{
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    background-color: {Colors.BG_PANEL};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 7px 16px;
    margin-right: 2px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {Colors.BG_PANEL};
    color: {Colors.TEXT_PRIMARY};
    border-bottom-color: {Colors.BG_PANEL};
}}

QTabBar::tab:hover:!selected {{
    background-color: {Colors.BG_MID};
    color: {Colors.TEXT_PRIMARY};
}}

/* ===== Progress Bar ===== */
QProgressBar {{
    background-color: {Colors.BG_MID};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    font-size: 10px;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 4px;
}}

/* ===== List Widget ===== */
QListWidget {{
    background-color: {Colors.BG_DARK};
    border: none;
    outline: none;
}}

QListWidget::item {{
    padding: 6px 10px;
    border-radius: 6px;
    margin: 1px 4px;
    color: {Colors.TEXT_PRIMARY};
}}

QListWidget::item:selected {{
    background-color: {Colors.BG_SELECTED};
    color: {Colors.ACCENT};
}}

QListWidget::item:hover:!selected {{
    background-color: {Colors.BG_HOVER};
}}

/* ===== Tooltip ===== */
QToolTip {{
    background-color: {Colors.BG_PANEL};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ===== Splitter Handle ===== */
QSplitter::handle:pressed {{
    background-color: {Colors.ACCENT};
}}

/* ===== Dialogs ===== */
QDialog {{
    background-color: {Colors.BG_DARK};
}}

QDialogButtonBox QPushButton {{
    min-width: 90px;
}}
"""
