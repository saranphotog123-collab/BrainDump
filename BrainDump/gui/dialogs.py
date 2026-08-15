"""
dialogs.py
==========
All modal dialogs for BrainDump GUI.

Classes
-------
AddEntryDialog      – create / edit a BrainEntry
EntryDetailDialog   – read-only detail view with edit/complete/delete actions
StatsDialog         – statistics overview
ExportDialog        – pick format + output path
ConfirmDialog       – generic Yes/No confirmation
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.constants import (
    ALL_CATEGORIES,
    ALL_PRIORITIES,
    DISPLAY_DATE_FORMAT,
    EXPORT_FORMATS,
    Category,
    Priority,
)
from app.models import BrainDumpDB, BrainEntry
from app.parser import detect_category, parse_deadline
from gui.styles import (
    CATEGORY_COLORS,
    PRIORITY_COLORS,
    Colors,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label(text: str, color: str = Colors.TEXT_SECONDARY, bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    style = f"color: {color};"
    if bold:
        style += " font-weight: 700;"
    lbl.setStyleSheet(style)
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background: {Colors.BORDER}; max-height: 1px;")
    return line


def _badge_label(text: str, fg: str, bg: str) -> QLabel:
    lbl = QLabel(f"  {text}  ")
    lbl.setStyleSheet(
        f"color: {fg}; background: {bg}; border-radius: 8px;"
        f" padding: 2px 8px; font-size: 11px; font-weight: 600;"
    )
    lbl.setFixedHeight(22)
    return lbl


# ---------------------------------------------------------------------------
# AddEntryDialog
# ---------------------------------------------------------------------------

class AddEntryDialog(QDialog):
    """
    Dialog for creating a new entry or editing an existing one.

    After exec(), check ``dialog.result() == QDialog.Accepted`` then
    read ``dialog.entry`` for the constructed BrainEntry.
    """

    def __init__(
        self,
        parent=None,
        existing: Optional[BrainEntry] = None,
    ) -> None:
        super().__init__(parent)
        self._existing = existing
        self.entry: Optional[BrainEntry] = None
        self._setup_ui()
        if existing:
            self._populate(existing)

    def _setup_ui(self) -> None:
        title = "Edit Entry" if self._existing else "New Entry"
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 20, 24, 20)

        # --- Header ---
        header = QLabel(title)
        header.setObjectName("titleLabel")
        root.addWidget(header)
        root.addWidget(_separator())

        # --- Thought text ---
        root.addWidget(_label("Thought *"))
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(
            'e.g. "Fix login bug by Friday"  •  "Buy milk tomorrow"'
        )
        self._text_edit.setFixedHeight(80)
        self._text_edit.textChanged.connect(self._on_text_changed)
        root.addWidget(self._text_edit)

        # --- Auto-detect row ---
        detect_row = QHBoxLayout()
        self._deadline_preview = _label("⏰  No deadline detected", Colors.TEXT_MUTED)
        self._category_preview = _label("📂  —", Colors.TEXT_MUTED)
        detect_row.addWidget(self._deadline_preview)
        detect_row.addStretch()
        detect_row.addWidget(self._category_preview)
        root.addLayout(detect_row)

        # --- Form fields ---
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Category
        self._cat_combo = QComboBox()
        self._cat_combo.addItem("Auto-detect", "")
        for cat in ALL_CATEGORIES:
            self._cat_combo.addItem(cat, cat)
        form.addRow("Category:", self._cat_combo)

        # Priority
        self._pri_combo = QComboBox()
        for p in ALL_PRIORITIES:
            self._pri_combo.addItem(p, p)
        self._pri_combo.setCurrentText(Priority.MEDIUM)
        form.addRow("Priority:", self._pri_combo)

        # Tags
        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("work, urgent, personal  (comma-separated)")
        form.addRow("Tags:", self._tags_edit)

        # Deadline override
        deadline_row = QHBoxLayout()
        self._deadline_check = QCheckBox("Override deadline")
        self._deadline_check.toggled.connect(self._on_deadline_toggle)
        self._deadline_dt = QDateTimeEdit()
        self._deadline_dt.setDisplayFormat("dd MMM yyyy  hh:mm AP")
        self._deadline_dt.setDateTime(QDateTime.currentDateTime())
        self._deadline_dt.setEnabled(False)
        self._deadline_dt.setCalendarPopup(True)
        deadline_row.addWidget(self._deadline_check)
        deadline_row.addWidget(self._deadline_dt)
        deadline_row.addStretch()
        form.addRow("Deadline:", deadline_row)

        root.addLayout(form)
        root.addWidget(_separator())

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn = QPushButton("Save Entry")
        self._save_btn.setObjectName("primaryButton")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._save_btn)
        root.addLayout(btn_row)

    def _populate(self, entry: BrainEntry) -> None:
        """Pre-fill the form with an existing entry."""
        self._text_edit.setPlainText(entry.text)
        idx = self._cat_combo.findData(entry.category)
        if idx >= 0:
            self._cat_combo.setCurrentIndex(idx)
        self._pri_combo.setCurrentText(entry.priority)
        self._tags_edit.setText(", ".join(entry.tags))
        if entry.deadline:
            self._deadline_check.setChecked(True)
            self._deadline_dt.setDateTime(
                QDateTime(
                    entry.deadline.year,
                    entry.deadline.month,
                    entry.deadline.day,
                    entry.deadline.hour,
                    entry.deadline.minute,
                )
            )

    def _on_text_changed(self) -> None:
        text = self._text_edit.toPlainText().strip()
        self._save_btn.setEnabled(bool(text))
        if not text:
            self._deadline_preview.setText("⏰  No deadline detected")
            self._deadline_preview.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            self._category_preview.setText("📂  —")
            return

        # Live auto-detect
        dl = parse_deadline(text)
        cat = detect_category(text)

        if dl:
            self._deadline_preview.setText(f"⏰  {dl.strftime(DISPLAY_DATE_FORMAT)}")
            self._deadline_preview.setStyleSheet(f"color: {Colors.SUCCESS};")
        else:
            self._deadline_preview.setText("⏰  No deadline detected")
            self._deadline_preview.setStyleSheet(f"color: {Colors.TEXT_MUTED};")

        cat_col = CATEGORY_COLORS.get(cat, Colors.TEXT_PRIMARY)
        self._category_preview.setText(f"📂  {cat}")
        self._category_preview.setStyleSheet(f"color: {cat_col}; font-weight: 600;")

        # Update auto-detect combo if it's still on "Auto-detect"
        if self._cat_combo.currentData() == "":
            idx = self._cat_combo.findText(cat)  # visual update only, don't change selection

    def _on_deadline_toggle(self, checked: bool) -> None:
        self._deadline_dt.setEnabled(checked)

    def _on_save(self) -> None:
        text = self._text_edit.toPlainText().strip()
        if not text:
            return

        # Resolve category
        cat_data = self._cat_combo.currentData()
        if cat_data:
            category = cat_data
        else:
            category = detect_category(text)

        # Resolve priority
        priority = self._pri_combo.currentData() or Priority.MEDIUM

        # Resolve tags
        raw_tags = self._tags_edit.text()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

        # Resolve deadline
        if self._deadline_check.isChecked():
            qdt = self._deadline_dt.dateTime()
            deadline: Optional[datetime] = datetime(
                qdt.date().year(),
                qdt.date().month(),
                qdt.date().day(),
                qdt.time().hour(),
                qdt.time().minute(),
            )
        else:
            deadline = parse_deadline(text)

        if self._existing:
            # Mutate the existing entry in-place
            self._existing.text = text
            self._existing.category = category
            self._existing.priority = priority
            self._existing.tags = tags
            self._existing.deadline = deadline
            self.entry = self._existing
        else:
            self.entry = BrainEntry(
                text=text,
                category=category,
                priority=priority,
                tags=tags,
                deadline=deadline,
            )

        self.accept()


# ---------------------------------------------------------------------------
# EntryDetailDialog
# ---------------------------------------------------------------------------

class EntryDetailDialog(QDialog):
    """Read-only detail view for a single entry."""

    def __init__(self, entry: BrainEntry, parent=None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle("Entry Detail")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        e = self.entry
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 20, 24, 20)

        # Title
        lbl = QLabel("Entry Detail")
        lbl.setObjectName("titleLabel")
        root.addWidget(lbl)
        root.addWidget(_separator())

        # Text
        text_lbl = QLabel(e.text)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {Colors.TEXT_PRIMARY}; "
            f"padding: 4px 0;"
        )
        root.addWidget(text_lbl)

        # Badges row
        badge_row = QHBoxLayout()
        cat_col = CATEGORY_COLORS.get(e.category, Colors.TEXT_PRIMARY)
        from gui.styles import CATEGORY_BG, PRIORITY_BG
        cat_bg  = CATEGORY_BG.get(e.category, Colors.BG_CARD)
        pri_col = PRIORITY_COLORS.get(e.priority, Colors.TEXT_PRIMARY)
        pri_bg  = PRIORITY_BG.get(e.priority, Colors.BG_CARD)

        badge_row.addWidget(_badge_label(e.category, cat_col, cat_bg))
        badge_row.addSpacing(8)
        badge_row.addWidget(_badge_label(e.priority, pri_col, pri_bg))
        badge_row.addStretch()
        root.addLayout(badge_row)

        root.addWidget(_separator())

        # Details grid
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(0, 100)

        rows = [
            ("ID",         e.id),
            ("Created",    e.created_at.strftime(DISPLAY_DATE_FORMAT)),
            ("Deadline",   e.deadline.strftime(DISPLAY_DATE_FORMAT) if e.deadline else "—"),
            ("Status",     "✓ Completed" if e.completed else ("⚡ Overdue" if e.is_overdue else "○ Pending")),
            ("Tags",       ", ".join(e.tags) if e.tags else "—"),
        ]
        if e.completed and e.completed_at:
            rows.append(("Completed at", e.completed_at.strftime(DISPLAY_DATE_FORMAT)))

        for r, (key, val) in enumerate(rows):
            key_lbl = _label(key + ":", Colors.TEXT_MUTED)
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_lbl = QLabel(val)
            val_lbl.setWordWrap(True)
            # Colour status
            if key == "Status":
                if e.completed:
                    val_lbl.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: 600;")
                elif e.is_overdue:
                    val_lbl.setStyleSheet(f"color: {Colors.DANGER}; font-weight: 600;")
            elif key == "Deadline" and e.is_overdue:
                val_lbl.setStyleSheet(f"color: {Colors.DANGER};")
            grid.addWidget(key_lbl, r, 0)
            grid.addWidget(val_lbl, r, 1)

        root.addLayout(grid)
        root.addWidget(_separator())

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)


# ---------------------------------------------------------------------------
# StatsDialog
# ---------------------------------------------------------------------------

class StatsDialog(QDialog):
    """Statistics overview dialog."""

    def __init__(self, db: BrainDumpDB, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Statistics")
        self.setMinimumWidth(540)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        db = self._db
        total     = len(db.entries)
        completed = len(db.get_completed())
        pending   = len(db.get_pending())
        overdue   = len(db.get_overdue())
        pct       = int(completed / total * 100) if total else 0

        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 20, 24, 20)

        # Header
        hdr = QLabel("Statistics")
        hdr.setObjectName("titleLabel")
        root.addWidget(hdr)
        root.addWidget(_separator())

        # --- Summary cards row ---
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        stats_data = [
            ("Total",     str(total),     Colors.ACCENT),
            ("Completed", str(completed), Colors.SUCCESS),
            ("Pending",   str(pending),   Colors.WARNING),
            ("Overdue",   str(overdue),   Colors.DANGER),
        ]
        for label, value, color in stats_data:
            card = QFrame()
            card.setObjectName("statsCard")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)
            card_layout.setContentsMargins(12, 12, 12, 12)
            num = QLabel(value)
            num.setObjectName("statNumber")
            num.setStyleSheet(f"font-size: 28px; font-weight: 700; color: {color};")
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl = QLabel(label)
            lbl.setObjectName("statLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(num)
            card_layout.addWidget(lbl)
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        # --- Completion progress ---
        prog_label = QHBoxLayout()
        prog_label.addWidget(_label("Completion Rate", Colors.TEXT_SECONDARY))
        prog_label.addStretch()
        prog_label.addWidget(_label(f"{pct}%", Colors.ACCENT, bold=True))
        root.addLayout(prog_label)

        bar = QProgressBar()
        bar.setValue(pct)
        bar.setTextVisible(False)
        bar.setFixedHeight(10)
        if pct >= 75:
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {Colors.SUCCESS}; border-radius: 4px; }}")
        elif pct >= 40:
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {Colors.WARNING}; border-radius: 4px; }}")
        else:
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {Colors.DANGER}; border-radius: 4px; }}")
        root.addWidget(bar)
        root.addWidget(_separator())

        # --- Category breakdown ---
        cat_hdr = QLabel("Notes by Category")
        cat_hdr.setObjectName("sectionHeader")
        root.addWidget(cat_hdr)

        from app.constants import ALL_CATEGORIES
        from gui.styles import CATEGORY_COLORS as CC
        for cat in ALL_CATEGORIES:
            count = len(db.get_by_category(cat))
            if count == 0:
                continue
            pct_cat = int(count / total * 100) if total else 0
            row = QHBoxLayout()
            cat_lbl = QLabel(cat)
            cat_lbl.setFixedWidth(90)
            cat_lbl.setStyleSheet(
                f"color: {CC.get(cat, Colors.TEXT_PRIMARY)}; font-weight: 600;"
            )
            cnt_lbl = QLabel(str(count))
            cnt_lbl.setFixedWidth(30)
            cnt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            cnt_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
            cat_bar = QProgressBar()
            cat_bar.setValue(pct_cat)
            cat_bar.setTextVisible(False)
            cat_bar.setFixedHeight(6)
            cat_bar.setStyleSheet(
                f"QProgressBar {{ background: {Colors.BG_MID}; border-radius: 3px; }}"
                f"QProgressBar::chunk {{ background: {CC.get(cat, Colors.ACCENT)}; border-radius: 3px; }}"
            )
            row.addWidget(cat_lbl)
            row.addWidget(cnt_lbl)
            row.addWidget(cat_bar)
            root.addLayout(row)

        root.addWidget(_separator())
        root.addStretch()

        # Close
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)


# ---------------------------------------------------------------------------
# ExportDialog
# ---------------------------------------------------------------------------

class ExportDialog(QDialog):
    """Pick export format and output path."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Data")
        self.setMinimumWidth(420)
        self.setModal(True)
        self.selected_format: str = "json"
        self.selected_path: Optional[Path] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 20, 24, 20)

        hdr = QLabel("Export Data")
        hdr.setObjectName("titleLabel")
        root.addWidget(hdr)
        root.addWidget(_separator())

        form = QFormLayout()
        form.setSpacing(10)

        # Format picker
        self._fmt_combo = QComboBox()
        for fmt in EXPORT_FORMATS:
            self._fmt_combo.addItem(fmt.upper(), fmt)
        self._fmt_combo.currentIndexChanged.connect(self._update_ext)
        form.addRow("Format:", self._fmt_combo)

        # Output path
        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("braindump_export.json")
        self._path_edit.setText("braindump_export.json")
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self._path_edit)
        path_row.addWidget(browse_btn)
        form.addRow("Output file:", path_row)

        root.addLayout(form)
        root.addWidget(_separator())

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        export_btn = QPushButton("Export")
        export_btn.setObjectName("primaryButton")
        export_btn.clicked.connect(self._on_export)
        btn_row.addWidget(cancel)
        btn_row.addWidget(export_btn)
        root.addLayout(btn_row)

    def _update_ext(self) -> None:
        fmt = self._fmt_combo.currentData()
        ext = "md" if fmt == "markdown" else fmt
        current = self._path_edit.text()
        # Replace extension
        base = current.rsplit(".", 1)[0] if "." in current else current
        self._path_edit.setText(f"{base}.{ext}")

    def _browse(self) -> None:
        fmt = self._fmt_combo.currentData()
        ext = "md" if fmt == "markdown" else fmt
        filter_map = {
            "json":     "JSON Files (*.json)",
            "csv":      "CSV Files (*.csv)",
            "markdown": "Markdown Files (*.md)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to…",
            self._path_edit.text(),
            filter_map.get(fmt, "All Files (*)"),
        )
        if path:
            self._path_edit.setText(path)

    def _on_export(self) -> None:
        self.selected_format = self._fmt_combo.currentData()
        path_str = self._path_edit.text().strip()
        if not path_str:
            return
        self.selected_path = Path(path_str)
        self.accept()


# ---------------------------------------------------------------------------
# ConfirmDialog
# ---------------------------------------------------------------------------

class ConfirmDialog(QDialog):
    """Generic confirmation dialog."""

    def __init__(
        self,
        message: str,
        title: str = "Confirm",
        detail: str = "",
        danger: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 20, 24, 20)

        icon = "⚠️" if danger else "❓"
        msg_lbl = QLabel(f"{icon}  {message}")
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600; "
            f"color: {Colors.DANGER if danger else Colors.TEXT_PRIMARY};"
        )
        root.addWidget(msg_lbl)

        if detail:
            det_lbl = QLabel(detail)
            det_lbl.setWordWrap(True)
            det_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
            root.addWidget(det_lbl)

        root.addWidget(_separator())

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        confirm = QPushButton("Delete" if danger else "Confirm")
        if danger:
            confirm.setObjectName("dangerButton")
        else:
            confirm.setObjectName("primaryButton")
        confirm.clicked.connect(self.accept)

        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        root.addLayout(btn_row)
