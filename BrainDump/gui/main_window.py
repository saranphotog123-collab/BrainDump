"""
main_window.py
==============
BrainDump MainWindow – the root widget that wires everything together.

Layout
------
  QMainWindow
  ├── MenuBar
  ├── ToolBar
  ├── Central widget  (QSplitter)
  │   ├── FilterSidebar  (fixed 200 px)
  │   └── Right pane  (QVBoxLayout)
  │       ├── SearchBar
  │       ├── EntryCountLabel
  │       └── QTableView  (EntryTableModel + EntryFilterProxyModel)
  └── StatusBar
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.models import BrainEntry
from app.storage import EntryNotFoundError, StorageError, StorageManager
from gui.dialogs import (
    AddEntryDialog,
    ConfirmDialog,
    EntryDetailDialog,
    ExportDialog,
    StatsDialog,
)
from gui.models import (
    COLUMN_WIDTHS,
    COL_CATEGORY,
    COL_PRIORITY,
    COL_STATUS,
    EntryFilterProxyModel,
    EntryTableModel,
)
from gui.styles import Colors
from gui.widgets import (
    BadgeDelegate,
    EntryCountLabel,
    FilterSidebar,
    SearchBar,
    StatusDelegate,
    CATEGORY_COLORS,
    CATEGORY_BG,
    PRIORITY_COLORS,
    PRIORITY_BG,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Root application window."""

    def __init__(self, storage: Optional[StorageManager] = None) -> None:
        super().__init__()
        self._storage = storage or StorageManager()
        self._setup_window()
        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._connect_signals()
        self._apply_shortcuts()
        self.refresh()

    # ------------------------------------------------------------------
    # Window chrome
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle("BrainDump")
        self.setMinimumSize(1100, 650)
        self.resize(1280, 760)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # -- File --
        file_menu = mb.addMenu("&File")

        self._act_new = QAction("&New Entry", self)
        self._act_new.setShortcut(QKeySequence("Ctrl+N"))
        file_menu.addAction(self._act_new)

        file_menu.addSeparator()

        self._act_export = QAction("&Export…", self)
        self._act_export.setShortcut(QKeySequence("Ctrl+E"))
        file_menu.addAction(self._act_export)

        self._act_backup = QAction("&Backup Database", self)
        self._act_backup.setShortcut(QKeySequence("Ctrl+B"))
        file_menu.addAction(self._act_backup)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(QApplication.quit)
        file_menu.addAction(act_quit)

        # -- Edit --
        edit_menu = mb.addMenu("&Edit")

        self._act_undo = QAction("&Undo Delete", self)
        self._act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(self._act_undo)

        edit_menu.addSeparator()

        self._act_complete = QAction("Mark &Complete", self)
        self._act_complete.setShortcut(QKeySequence("Space"))
        edit_menu.addAction(self._act_complete)

        self._act_edit = QAction("&Edit Entry", self)
        self._act_edit.setShortcut(QKeySequence("F2"))
        edit_menu.addAction(self._act_edit)

        self._act_delete = QAction("&Delete Entry", self)
        self._act_delete.setShortcut(QKeySequence("Delete"))
        edit_menu.addAction(self._act_delete)

        # -- View --
        view_menu = mb.addMenu("&View")

        self._act_stats = QAction("&Statistics", self)
        self._act_stats.setShortcut(QKeySequence("Ctrl+I"))
        view_menu.addAction(self._act_stats)

        self._act_remind = QAction("&Reminders", self)
        self._act_remind.setShortcut(QKeySequence("Ctrl+R"))
        view_menu.addAction(self._act_remind)

        view_menu.addSeparator()

        self._act_refresh = QAction("Re&fresh", self)
        self._act_refresh.setShortcut(QKeySequence("F5"))
        view_menu.addAction(self._act_refresh)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        def _tool(icon: str, text: str, action: QAction) -> None:
            action.setIcon(self.style().standardIcon(
                self.style().StandardPixmap.SP_FileIcon  # placeholder
            ))
            # We'll label via text instead of icons for portability
            action.setText(f"{icon}  {text}")
            tb.addAction(action)

        _tool("＋", "New", self._act_new)
        tb.addSeparator()
        _tool("✓", "Complete", self._act_complete)
        _tool("✎", "Edit", self._act_edit)
        _tool("✕", "Delete", self._act_delete)
        tb.addSeparator()
        _tool("↩", "Undo", self._act_undo)
        tb.addSeparator()
        _tool("📊", "Stats", self._act_stats)
        _tool("⏰", "Remind", self._act_remind)
        tb.addSeparator()
        _tool("⬆", "Export", self._act_export)
        _tool("💾", "Backup", self._act_backup)

    # ------------------------------------------------------------------
    # Central widget
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # --- Sidebar ---
        self._sidebar = FilterSidebar()
        splitter.addWidget(self._sidebar)

        # --- Right pane ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 10, 12, 8)
        right_layout.setSpacing(8)

        # Search + count row
        top_row = QHBoxLayout()
        self._search_bar = SearchBar()
        top_row.addWidget(self._search_bar, 1)
        top_row.addSpacing(12)
        self._count_lbl = EntryCountLabel()
        top_row.addWidget(self._count_lbl)
        right_layout.addLayout(top_row)

        # Table
        self._source_model = EntryTableModel()
        self._proxy_model  = EntryFilterProxyModel()
        self._proxy_model.setSourceModel(self._source_model)

        self._table = QTableView()
        self._table.setModel(self._proxy_model)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._table.doubleClicked.connect(self._on_row_double_click)

        # Column widths
        hh = self._table.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i, w in enumerate(COLUMN_WIDTHS):
            self._table.setColumnWidth(i, w)
        # Stretch the Thought column
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Row height
        self._table.verticalHeader().setDefaultSectionSize(36)

        # Delegates
        self._table.setItemDelegateForColumn(
            COL_STATUS, StatusDelegate(self._table)
        )
        self._table.setItemDelegateForColumn(
            COL_CATEGORY,
            BadgeDelegate(CATEGORY_COLORS, CATEGORY_BG, self._table),
        )
        self._table.setItemDelegateForColumn(
            COL_PRIORITY,
            BadgeDelegate(PRIORITY_COLORS, PRIORITY_BG, self._table),
        )

        right_layout.addWidget(self._table)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_statusbar(self) -> None:
        self._status_bar = self.statusBar()
        self._status_lbl = QLabel("Ready")
        self._status_bar.addWidget(self._status_lbl)

    def _set_status(self, msg: str, duration_ms: int = 4000) -> None:
        self._status_lbl.setText(msg)
        if duration_ms > 0:
            QTimer.singleShot(duration_ms, lambda: self._status_lbl.setText("Ready"))

    # ------------------------------------------------------------------
    # Signal / slot wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        # Menu / toolbar actions
        self._act_new.triggered.connect(self._on_add)
        self._act_edit.triggered.connect(self._on_edit)
        self._act_complete.triggered.connect(self._on_complete)
        self._act_delete.triggered.connect(self._on_delete)
        self._act_undo.triggered.connect(self._on_undo)
        self._act_stats.triggered.connect(self._on_stats)
        self._act_remind.triggered.connect(self._on_remind)
        self._act_export.triggered.connect(self._on_export)
        self._act_backup.triggered.connect(self._on_backup)
        self._act_refresh.triggered.connect(self.refresh)

        # Sidebar filters
        self._sidebar.filterChanged.connect(self._apply_filters)

        # Search bar
        self._search_bar.searchChanged.connect(self._on_search)

        # Checkbox toggle from model
        self._source_model.entryToggled.connect(self._on_toggle_complete)

        # Row selection changes
        self._table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

    def _apply_shortcuts(self) -> None:
        # Extra shortcut: Ctrl+F focuses search
        sc = QShortcut(QKeySequence("Ctrl+F"), self)
        sc.activated.connect(self._search_bar._input.setFocus)

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload everything from disk and update the model + count."""
        try:
            db  = self._storage.load()
            entries = db.sorted_entries()
            self._source_model.refresh(entries)
            self._update_count()
            self._set_status(
                f"Loaded {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}",
                3000,
            )
        except StorageError as e:
            self._error(str(e))

    def _update_count(self) -> None:
        total   = self._source_model.rowCount()
        visible = self._proxy_model.rowCount()
        self._count_lbl.set_count(visible, total)

    # ------------------------------------------------------------------
    # Filter application
    # ------------------------------------------------------------------

    def _apply_filters(self) -> None:
        self._proxy_model.set_category(self._sidebar.current_category)
        self._proxy_model.set_priority(self._sidebar.current_priority)
        self._proxy_model.set_status(self._sidebar.current_status)
        self._update_count()

    def _on_search(self, text: str) -> None:
        self._proxy_model.set_search(text)
        self._update_count()

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _selected_entry_id(self) -> Optional[str]:
        """Return the full entry.id of the currently selected row, or None."""
        idx = self._table.selectionModel().currentIndex()
        if not idx.isValid():
            return None
        source_idx = self._proxy_model.mapToSource(idx)
        return self._source_model.data(source_idx, Qt.ItemDataRole.UserRole)

    def _on_selection_changed(self) -> None:
        has_sel = bool(self._selected_entry_id())
        self._act_complete.setEnabled(has_sel)
        self._act_edit.setEnabled(has_sel)
        self._act_delete.setEnabled(has_sel)

    # ------------------------------------------------------------------
    # CRUD actions
    # ------------------------------------------------------------------

    @Slot()
    def _on_add(self) -> None:
        dlg = AddEntryDialog(self)
        if dlg.exec() == AddEntryDialog.DialogCode.Accepted and dlg.entry:
            try:
                self._storage.add_entry(dlg.entry)
                self.refresh()
                self._set_status(f"Added: {dlg.entry.text[:50]}")
                # Select the new row
                self._select_entry(dlg.entry.id)
            except StorageError as e:
                self._error(str(e))

    @Slot()
    def _on_edit(self) -> None:
        entry_id = self._selected_entry_id()
        if not entry_id:
            return
        try:
            db    = self._storage.load()
            entry = db.get_by_id(entry_id)
            if not entry:
                self._error("Entry not found.")
                return
            dlg = AddEntryDialog(self, existing=entry)
            if dlg.exec() == AddEntryDialog.DialogCode.Accepted and dlg.entry:
                self._storage.save(db)
                self.refresh()
                self._set_status(f"Updated: {entry.text[:50]}")
                self._select_entry(entry.id)
        except StorageError as e:
            self._error(str(e))

    @Slot()
    def _on_complete(self) -> None:
        entry_id = self._selected_entry_id()
        if not entry_id:
            return
        try:
            entry = self._storage.complete_entry(entry_id)
            self.refresh()
            self._set_status(f"Completed: {entry.text[:50]}")
        except (EntryNotFoundError, StorageError) as e:
            self._error(str(e))

    @Slot(str)
    def _on_toggle_complete(self, entry_id: str) -> None:
        """Called when the checkbox in COL_STATUS is clicked."""
        try:
            db    = self._storage.load()
            entry = db.get_by_id(entry_id)
            if entry:
                if entry.completed:
                    # Un-complete: just toggle the flag
                    entry.completed    = False
                    entry.completed_at = None
                    self._storage.save(db)
                    self._set_status(f"Marked pending: {entry.text[:50]}")
                else:
                    self._storage.complete_entry(entry_id)
                    self._set_status(f"Completed: {entry.text[:50]}")
                self.refresh()
        except (EntryNotFoundError, StorageError) as e:
            self._error(str(e))

    @Slot()
    def _on_delete(self) -> None:
        entry_id = self._selected_entry_id()
        if not entry_id:
            return
        try:
            db    = self._storage.load()
            entry = db.get_by_id(entry_id)
            if not entry:
                return
        except StorageError as e:
            self._error(str(e))
            return

        dlg = ConfirmDialog(
            message=f"Delete this entry?",
            title="Delete Entry",
            detail=f'"{entry.text}"',
            danger=True,
            parent=self,
        )
        if dlg.exec() == ConfirmDialog.DialogCode.Accepted:
            try:
                self._storage.delete_entry(entry_id)
                self.refresh()
                self._set_status("Entry deleted.  Press Ctrl+Z to undo.")
            except (EntryNotFoundError, StorageError) as e:
                self._error(str(e))

    @Slot()
    def _on_undo(self) -> None:
        try:
            entry = self._storage.undo_delete()
            if entry:
                self.refresh()
                self._set_status(f"Restored: {entry.text[:50]}")
                self._select_entry(entry.id)
            else:
                self._set_status("Nothing to undo.")
        except StorageError as e:
            self._error(str(e))

    # ------------------------------------------------------------------
    # Stats / Remind
    # ------------------------------------------------------------------

    @Slot()
    def _on_stats(self) -> None:
        try:
            db = self._storage.load()
            StatsDialog(db, self).exec()
        except StorageError as e:
            self._error(str(e))

    @Slot()
    def _on_remind(self) -> None:
        """Show reminders: overdue + due today."""
        try:
            db = self._storage.load()
        except StorageError as e:
            self._error(str(e))
            return

        from datetime import datetime
        today = datetime.now().date()
        due_today = [
            e for e in db.entries
            if not e.completed and e.deadline and e.deadline.date() == today
        ]
        overdue = db.get_overdue()

        if not due_today and not overdue:
            QMessageBox.information(self, "Reminders", "🎉  You're all caught up!")
            return

        lines = []
        if overdue:
            lines.append(f"<b style='color:{Colors.DANGER}'>⚡ Overdue ({len(overdue)})</b>")
            for e in overdue[:5]:
                lines.append(f"  • {e.text[:60]}")
            if len(overdue) > 5:
                lines.append(f"  … and {len(overdue)-5} more")
        if due_today:
            lines.append(f"<b style='color:{Colors.WARNING}'>⏰ Due Today ({len(due_today)})</b>")
            for e in due_today[:5]:
                lines.append(f"  • {e.text[:60]}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Reminders")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText("<br>".join(lines))
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    # ------------------------------------------------------------------
    # Export / Backup
    # ------------------------------------------------------------------

    @Slot()
    def _on_export(self) -> None:
        dlg = ExportDialog(self)
        if dlg.exec() != ExportDialog.DialogCode.Accepted:
            return
        fmt  = dlg.selected_format
        path = dlg.selected_path
        if not path:
            return
        try:
            if fmt == "json":
                self._storage.export_json(path)
            elif fmt == "csv":
                self._storage.export_csv(path)
            else:
                self._storage.export_markdown(path)
            self._set_status(f"Exported to {path.name}")
            QMessageBox.information(
                self, "Export Complete", f"Data exported to:\n{path}"
            )
        except StorageError as e:
            self._error(str(e))

    @Slot()
    def _on_backup(self) -> None:
        try:
            path = self._storage.backup()
            self._set_status(f"Backup saved: {path.name}")
            QMessageBox.information(
                self, "Backup Created", f"Backup saved to:\n{path}"
            )
        except StorageError as e:
            self._error(str(e))

    # ------------------------------------------------------------------
    # Double-click → detail
    # ------------------------------------------------------------------

    @Slot(QModelIndex)
    def _on_row_double_click(self, index: QModelIndex) -> None:
        source_idx = self._proxy_model.mapToSource(index)
        entry_id   = self._source_model.data(source_idx, Qt.ItemDataRole.UserRole)
        if not entry_id:
            return
        try:
            db    = self._storage.load()
            entry = db.get_by_id(entry_id)
            if entry:
                EntryDetailDialog(entry, self).exec()
        except StorageError as e:
            self._error(str(e))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _select_entry(self, entry_id: str) -> None:
        """Highlight and scroll to the row matching entry_id."""
        for row in range(self._proxy_model.rowCount()):
            proxy_idx  = self._proxy_model.index(row, 0)
            source_idx = self._proxy_model.mapToSource(proxy_idx)
            eid        = self._source_model.data(source_idx, Qt.ItemDataRole.UserRole)
            if eid == entry_id:
                self._table.selectRow(row)
                self._table.scrollTo(proxy_idx)
                break

    def _error(self, message: str) -> None:
        logger.error(message)
        QMessageBox.critical(self, "Error", message)
        self._set_status(f"Error: {message[:60]}", 6000)
