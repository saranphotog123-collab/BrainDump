"""
models.py  (gui layer)
======================
QAbstractTableModel that wraps a list[BrainEntry] so the main QTableView
can display, sort and update entries without touching storage directly.

Columns
-------
  0  Status      checkbox icon  (completed / overdue / pending)
  1  ID          short_id (8 chars)
  2  Thought     entry.text
  3  Category    badge
  4  Priority    badge
  5  Deadline    formatted datetime or "—"
  6  Tags        comma-joined
  7  Created     formatted created_at
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QFont

from app.constants import DISPLAY_DATE_FORMAT
from app.models import BrainEntry
from gui.styles import CATEGORY_COLORS, CATEGORY_BG, PRIORITY_COLORS, PRIORITY_BG, Colors

# ---------------------------------------------------------------------------
# Column constants
# ---------------------------------------------------------------------------
COL_STATUS   = 0
COL_ID       = 1
COL_TEXT     = 2
COL_CATEGORY = 3
COL_PRIORITY = 4
COL_DEADLINE = 5
COL_TAGS     = 6
COL_CREATED  = 7

HEADERS = ["", "ID", "Thought", "Category", "Priority", "Deadline", "Tags", "Created"]
COLUMN_WIDTHS = [36, 90, 360, 100, 90, 170, 130, 150]


class EntryTableModel(QAbstractTableModel):
    """
    Read/write table model over a list of BrainEntry objects.

    The model owns the display list only — actual persistence is done by the
    caller (MainWindow) which calls storage methods then refreshes the model.
    """

    # Emitted after in-model mutations (complete toggled via checkbox)
    entryToggled = Signal(str)   # entry.id

    def __init__(self, entries: Optional[list[BrainEntry]] = None, parent=None):
        super().__init__(parent)
        self._entries: list[BrainEntry] = entries or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, entries: list[BrainEntry]) -> None:
        """Replace the displayed entries and notify views."""
        self.beginResetModel()
        self._entries = list(entries)
        self.endResetModel()

    def entry_at(self, row: int) -> Optional[BrainEntry]:
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def row_of(self, entry_id: str) -> int:
        """Return the row index for an entry id, or -1."""
        for i, e in enumerate(self._entries):
            if e.id == entry_id or e.id.startswith(entry_id):
                return i
        return -1

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return HEADERS[section]
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        return None

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return None

        entry = self._entries[index.row()]
        col   = index.column()

        # ---- Display ----
        if role == Qt.ItemDataRole.DisplayRole:
            return self._display(entry, col)

        # ---- Decoration (status icon column only) ----
        if role == Qt.ItemDataRole.DecorationRole and col == COL_STATUS:
            return None   # drawn by delegate

        # ---- Foreground ----
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._foreground(entry, col)

        # ---- Background ----
        if role == Qt.ItemDataRole.BackgroundRole:
            return self._background(entry, col)

        # ---- Font ----
        if role == Qt.ItemDataRole.FontRole:
            font = QFont()
            if entry.completed:
                font.setStrikeOut(True)
            if col == COL_TEXT:
                font.setPointSize(13)
            return font

        # ---- Alignment ----
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == COL_STATUS:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        # ---- Tooltip ----
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(entry, col)

        # ---- UserRole: store the full entry.id for external use ----
        if role == Qt.ItemDataRole.UserRole:
            return entry.id

        # ---- CheckState for status column ----
        if role == Qt.ItemDataRole.CheckStateRole and col == COL_STATUS:
            return Qt.CheckState.Checked if entry.completed else Qt.CheckState.Unchecked

        return None

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Allow toggling completion via the checkbox in COL_STATUS."""
        if (
            index.isValid()
            and index.column() == COL_STATUS
            and role == Qt.ItemDataRole.CheckStateRole
        ):
            entry = self._entries[index.row()]
            # Emit signal; caller does actual storage update
            self.entryToggled.emit(entry.id)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == COL_STATUS:
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return base

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _display(self, entry: BrainEntry, col: int) -> str:
        if col == COL_STATUS:
            if entry.completed:
                return "✓"
            if entry.is_overdue:
                return "⚡"
            return "○"
        if col == COL_ID:
            return entry.short_id
        if col == COL_TEXT:
            return entry.text
        if col == COL_CATEGORY:
            return entry.category
        if col == COL_PRIORITY:
            return entry.priority
        if col == COL_DEADLINE:
            if entry.deadline:
                return entry.deadline.strftime(DISPLAY_DATE_FORMAT)
            return "—"
        if col == COL_TAGS:
            return ", ".join(entry.tags) if entry.tags else "—"
        if col == COL_CREATED:
            return entry.created_at.strftime("%d %b %Y")
        return ""

    def _foreground(self, entry: BrainEntry, col: int) -> Optional[QBrush]:
        if entry.completed:
            return QBrush(QColor(Colors.TEXT_MUTED))
        if col == COL_CATEGORY:
            return QBrush(QColor(CATEGORY_COLORS.get(entry.category, Colors.TEXT_PRIMARY)))
        if col == COL_PRIORITY:
            return QBrush(QColor(PRIORITY_COLORS.get(entry.priority, Colors.TEXT_PRIMARY)))
        if col == COL_DEADLINE and entry.is_overdue:
            return QBrush(QColor(Colors.OVERDUE))
        if col == COL_STATUS:
            if entry.completed:
                return QBrush(QColor(Colors.SUCCESS))
            if entry.is_overdue:
                return QBrush(QColor(Colors.DANGER))
        return None

    def _background(self, entry: BrainEntry, col: int) -> Optional[QBrush]:
        if col == COL_CATEGORY:
            bg = CATEGORY_BG.get(entry.category)
            if bg:
                return QBrush(QColor(bg))
        if col == COL_PRIORITY:
            bg = PRIORITY_BG.get(entry.priority)
            if bg:
                return QBrush(QColor(bg))
        return None

    def _tooltip(self, entry: BrainEntry, col: int) -> str:
        if col == COL_TEXT:
            return entry.text
        if col == COL_DEADLINE:
            if entry.deadline:
                if entry.is_overdue:
                    return f"⚡ Overdue — {entry.deadline.strftime(DISPLAY_DATE_FORMAT)}"
                return entry.deadline.strftime(DISPLAY_DATE_FORMAT)
            return "No deadline"
        if col == COL_TAGS:
            return ", ".join(entry.tags) if entry.tags else "No tags"
        if col == COL_STATUS:
            if entry.completed:
                ts = entry.completed_at
                return f"Completed{' on ' + ts.strftime(DISPLAY_DATE_FORMAT) if ts else ''}"
            if entry.is_overdue:
                return "Overdue!"
            return "Pending"
        return ""


# ---------------------------------------------------------------------------
# Proxy model for live filtering + sorting
# ---------------------------------------------------------------------------

class EntryFilterProxyModel(QSortFilterProxyModel):
    """
    Proxy that applies category / priority / status filters on top of
    EntryTableModel without modifying the source data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._category: str = ""       # "" = all
        self._priority: str = ""       # "" = all
        self._status:   str = ""       # "" | "pending" | "completed" | "overdue"
        self._tag:      str = ""       # "" = all
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(COL_TEXT)   # default search column

    # -- Filter setters (call invalidateFilter() to refresh) --

    def set_category(self, value: str) -> None:
        self._category = value
        self.invalidateFilter()

    def set_priority(self, value: str) -> None:
        self._priority = value
        self.invalidateFilter()

    def set_status(self, value: str) -> None:
        self._status = value
        self.invalidateFilter()

    def set_tag(self, value: str) -> None:
        self._tag = value.strip().lower()
        self.invalidateFilter()

    def set_search(self, text: str) -> None:
        """Search across text + category + tags."""
        self._search = text.strip().lower()
        self.invalidateFilter()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._category: str = ""
        self._priority: str = ""
        self._status:   str = ""
        self._tag:      str = ""
        self._search:   str = ""
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source: EntryTableModel = self.sourceModel()
        entry = source.entry_at(source_row)
        if entry is None:
            return False

        # Search filter
        if self._search:
            haystack = (
                entry.text.lower()
                + " " + entry.category.lower()
                + " " + " ".join(entry.tags).lower()
            )
            if self._search not in haystack:
                return False

        # Category filter
        if self._category and entry.category != self._category:
            return False

        # Priority filter
        if self._priority and entry.priority != self._priority:
            return False

        # Status filter
        if self._status == "pending" and entry.completed:
            return False
        if self._status == "completed" and not entry.completed:
            return False
        if self._status == "overdue" and not entry.is_overdue:
            return False

        # Tag filter
        if self._tag:
            if not any(self._tag in t.lower() for t in entry.tags):
                return False

        return True
