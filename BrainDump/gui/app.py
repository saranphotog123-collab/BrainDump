"""
app.py
======
PySide6 application entry point for BrainDump.

Usage
-----
    python -m gui.app
    # or, after pip install -e .:
    braindump-gui
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import QApplication

from app.storage import StorageManager
from gui.main_window import MainWindow
from gui.styles import STYLESHEET, Colors

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


def _configure_palette(app: QApplication) -> None:
    """Force a dark base palette so native widgets inherit the right colours."""
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(Colors.BG_DARK))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base,            QColor(Colors.BG_CARD))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(Colors.BG_MID))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(Colors.BG_PANEL))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Text,            QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button,          QColor(Colors.BG_CARD))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Link,            QColor(Colors.ACCENT))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(Colors.BG_SELECTED))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.TEXT_PRIMARY))
    app.setPalette(palette)


def run() -> int:
    """Create the QApplication, apply styling, show the window, enter event loop."""
    # Hi-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("BrainDump")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BrainDump")

    # Font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Dark palette + QSS
    _configure_palette(app)
    app.setStyleSheet(STYLESHEET)

    # Storage (uses default data/braindump.json)
    storage = StorageManager()

    # Main window
    window = MainWindow(storage=storage)
    window.show()

    return app.exec()


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
