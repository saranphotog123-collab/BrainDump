"""
widgets.py
==========
Reusable composite widgets for BrainDump GUI.

Classes
-------
SearchBar           – search input with fuzzy toggle and clear button
FilterSidebar       – left panel with category / priority / status / tag filters
StatusBadge         – inline coloured text badge
DeadlineDelegate    – QStyledItemDelegate for deadline column colouring
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, QRect, QSize
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QPalette
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWidgets import QStyle

from app.constants import ALL_CATEGORIES, ALL_PRIORITIES
from gui.styles import (
    CATEGORY_COLORS,
    CATEGORY_BG,
    PRIORITY_COLORS,
    PRIORITY_BG,
    Colors,
)


# ---------------------------------------------------------------------------
# SearchBar
# ---------------------------------------------------------------------------

class SearchBar(QWidget):
    """
    Search input with a fuzzy-match toggle and an X clear button.

    Signals
    -------
    searchChanged(str)  – emitted as user types
    fuzzyChanged(bool)  – emitted when fuzzy toggle changes
    """

    searchChanged = Signal(str)
    fuzzyChanged  = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Search icon prefix
        icon_lbl = QLabel("🔍")
        icon_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 14px;")
        layout.addWidget(icon_lbl)

        # Input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search thoughts, categories, tags…")
        self._input.setClearButtonEnabled(True)
        self._input.textChanged.connect(self.searchChanged)
        layout.addWidget(self._input, 1)

        # Fuzzy toggle button
        self._fuzzy_btn = QPushButton("Fuzzy")
        self._fuzzy_btn.setCheckable(True)
        self._fuzzy_btn.setObjectName("iconButton")
        self._fuzzy_btn.setFixedWidth(55)
        self._fuzzy_btn.setToolTip("Enable fuzzy matching")
        self._fuzzy_btn.toggled.connect(self.fuzzyChanged)
        layout.addWidget(self._fuzzy_btn)

    def text(self) -> str:
        return self._input.text()

    def is_fuzzy(self) -> bool:
        return self._fuzzy_btn.isChecked()

    def clear(self) -> None:
        self._input.clear()


# ---------------------------------------------------------------------------
# FilterSidebar
# ---------------------------------------------------------------------------

class FilterSidebar(QWidget):
    """
    Left panel widget with filter controls:
        • All / Status (Pending / Completed / Overdue)
        • Category quick-filter list
        • Priority quick-filter list

    Signals
    -------
    filterChanged()  – emitted whenever any filter changes; caller reads
                       .current_category, .current_priority, .current_status
    """

    filterChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setFixedWidth(200)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )

        self.current_category: str = ""
        self.current_priority: str = ""
        self.current_status:   str = ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 8)
        root.setSpacing(0)

        # --- Status section ---
        root.addWidget(self._section_header("STATUS"))
        status_items = [
            ("All",      "",          "○"),
            ("Pending",  "pending",   "○"),
            ("Completed","completed", "✓"),
            ("Overdue",  "overdue",   "⚡"),
        ]
        self._status_list = QListWidget()
        self._status_list.setFixedHeight(len(status_items) * 34 + 4)
        self._status_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        for label, value, icon in status_items:
            item = QListWidgetItem(f"  {icon}  {label}")
            item.setData(Qt.ItemDataRole.UserRole, value)
            self._status_list.addItem(item)
        self._status_list.setCurrentRow(0)
        self._status_list.currentItemChanged.connect(self._on_status_change)
        root.addWidget(self._status_list)

        root.addSpacing(8)
        root.addWidget(self._divider())
        root.addSpacing(8)

        # --- Category section ---
        root.addWidget(self._section_header("CATEGORY"))
        self._cat_list = QListWidget()
        cat_items = [("All Categories", "")] + [(c, c) for c in ALL_CATEGORIES]
        self._cat_list.setFixedHeight(len(cat_items) * 34 + 4)
        self._cat_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        for label, value in cat_items:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, value)
            if value:
                color = CATEGORY_COLORS.get(value, Colors.TEXT_PRIMARY)
                item.setText(f"  ●  {label}")
                item.setForeground(QColor(color))
            else:
                item.setText(f"  ○  {label}")
            self._cat_list.addItem(item)
        self._cat_list.setCurrentRow(0)
        self._cat_list.currentItemChanged.connect(self._on_cat_change)
        root.addWidget(self._cat_list)

        root.addSpacing(8)
        root.addWidget(self._divider())
        root.addSpacing(8)

        # --- Priority section ---
        root.addWidget(self._section_header("PRIORITY"))
        self._pri_list = QListWidget()
        pri_items = [("All Priorities", "")] + [(p, p) for p in ALL_PRIORITIES]
        self._pri_list.setFixedHeight(len(pri_items) * 34 + 4)
        self._pri_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        for label, value in pri_items:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, value)
            if value:
                color = PRIORITY_COLORS.get(value, Colors.TEXT_PRIMARY)
                item.setText(f"  ●  {label}")
                item.setForeground(QColor(color))
            else:
                item.setText(f"  ○  {label}")
            self._pri_list.addItem(item)
        self._pri_list.setCurrentRow(0)
        self._pri_list.currentItemChanged.connect(self._on_pri_change)
        root.addWidget(self._pri_list)

        root.addStretch()

    # -- Internal helpers --

    @staticmethod
    def _section_header(text: str) -> QLabel:
        lbl = QLabel(f"  {text}")
        lbl.setObjectName("sectionHeader")
        lbl.setContentsMargins(8, 4, 8, 4)
        return lbl

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {Colors.BORDER}; max-height: 1px;")
        return line

    # -- Slots --

    def _on_status_change(self, item: QListWidgetItem) -> None:
        if item:
            self.current_status = item.data(Qt.ItemDataRole.UserRole) or ""
            self.filterChanged.emit()

    def _on_cat_change(self, item: QListWidgetItem) -> None:
        if item:
            self.current_category = item.data(Qt.ItemDataRole.UserRole) or ""
            self.filterChanged.emit()

    def _on_pri_change(self, item: QListWidgetItem) -> None:
        if item:
            self.current_priority = item.data(Qt.ItemDataRole.UserRole) or ""
            self.filterChanged.emit()

    # -- Public --

    def reset(self) -> None:
        """Reset all filters to 'All'."""
        self._status_list.setCurrentRow(0)
        self._cat_list.setCurrentRow(0)
        self._pri_list.setCurrentRow(0)


# ---------------------------------------------------------------------------
# EntryCountLabel
# ---------------------------------------------------------------------------

class EntryCountLabel(QLabel):
    """Small status chip showing 'N entries' with live update."""

    def __init__(self, parent=None) -> None:
        super().__init__("0 entries", parent)
        self.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; padding: 0 4px;"
        )

    def set_count(self, visible: int, total: int) -> None:
        if visible == total:
            self.setText(f"{total} entr{'y' if total == 1 else 'ies'}")
        else:
            self.setText(f"{visible} of {total}")


# ---------------------------------------------------------------------------
# CategoryDelegate  (table cell delegate for Category / Priority columns)
# ---------------------------------------------------------------------------

class BadgeDelegate(QStyledItemDelegate):
    """
    Draws category or priority values as pill-shaped coloured badges
    instead of plain text.
    """

    def __init__(self, color_map: dict, bg_map: dict, parent=None):
        super().__init__(parent)
        self._color_map = color_map
        self._bg_map    = bg_map

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        fg   = self._color_map.get(text, Colors.TEXT_PRIMARY)
        bg   = self._bg_map.get(text, Colors.BG_CARD)

        painter.save()

        # Selection highlight
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if is_selected:
            painter.fillRect(option.rect, QColor(Colors.BG_SELECTED))

        # Badge pill
        r   = option.rect
        pad_h, pad_v = 10, 4
        badge_w = min(r.width() - 8, len(text) * 8 + pad_h * 2)
        badge_h = r.height() - pad_v * 2
        badge_x = r.x() + (r.width() - badge_w) // 2
        badge_y = r.y() + pad_v
        badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(bg)))
        painter.setPen(QPen(QColor(fg), 1))
        radius = badge_h // 2
        painter.drawRoundedRect(badge_rect, radius, radius)

        # Text
        painter.setPen(QColor(fg))
        font = QFont(option.font)
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(100, 32)


# ---------------------------------------------------------------------------
# StatusDelegate  (draws ○ / ✓ / ⚡ with colour)
# ---------------------------------------------------------------------------

class StatusDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if is_selected:
            painter.fillRect(option.rect, QColor(Colors.BG_SELECTED))

        color_map = {
            "✓":  Colors.SUCCESS,
            "⚡": Colors.DANGER,
            "○":  Colors.TEXT_MUTED,
        }
        fg = color_map.get(text, Colors.TEXT_MUTED)

        painter.save()
        painter.setPen(QColor(fg))
        font = QFont(option.font)
        font.setPointSize(14)
        painter.setFont(font)
        painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(36, 32)
