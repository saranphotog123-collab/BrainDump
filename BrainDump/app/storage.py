"""
storage.py
==========
JSON persistence layer for BrainDump.

All disk I/O is isolated here so the rest of the app never touches the
file-system directly.

Public API
----------
StorageManager          - main class; inject path for testing
  .load()               -> BrainDumpDB
  .save(db)
  .add_entry(entry)     -> BrainEntry
  .delete_entry(id)     -> BrainEntry
  .complete_entry(id)   -> BrainEntry
  .undo_delete()        -> Optional[BrainEntry]
  .backup()             -> Path
  .export_json(path)
  .export_csv(path)
  .export_markdown(path)
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.constants import (
    BACKUP_DIR,
    BACKUP_TIMESTAMP_FORMAT,
    DB_FILE,
    DATETIME_FORMAT,
    DISPLAY_DATE_FORMAT,
    MAX_UNDO_HISTORY,
)
from app.models import BrainDumpDB, BrainEntry

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when a storage operation cannot be completed."""


class EntryNotFoundError(StorageError):
    """Raised when an entry ID does not match any stored entry."""


class StorageManager:
    """
    Manages reading, writing, and exporting BrainDump data.

    Parameters
    ----------
    db_path:
        Path to the JSON database file.  Defaults to the global ``DB_FILE``
        constant.  Pass a custom path in tests to avoid touching real data.
    """

    def __init__(self, db_path: Path = DB_FILE) -> None:
        self._db_path = db_path
        self._ensure_data_dir()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_data_dir(self) -> None:
        """Create parent directories if they do not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_json(self, path: Path, data: dict) -> None:
        """Atomically write *data* to *path* as pretty-printed JSON."""
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            raise StorageError(f"Failed to write {path}: {exc}") from exc

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self) -> BrainDumpDB:
        """
        Load the database from disk.

        Creates an empty database file if none exists.

        Returns
        -------
        BrainDumpDB
        """
        if not self._db_path.exists():
            logger.info("No database found at %s – creating empty DB.", self._db_path)
            db = BrainDumpDB()
            self.save(db)
            return db

        try:
            raw = json.loads(self._db_path.read_text(encoding="utf-8"))
            db = BrainDumpDB.from_serializable(raw)
            logger.debug("Loaded %d entries from %s.", len(db.entries), self._db_path)
            return db
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise StorageError(
                f"Database file is corrupted ({self._db_path}): {exc}"
            ) from exc

    def save(self, db: BrainDumpDB) -> None:
        """
        Persist *db* to disk.

        Parameters
        ----------
        db:
            The BrainDumpDB instance to serialise.
        """
        self._write_json(self._db_path, db.model_dump_serializable())
        logger.debug("Saved %d entries to %s.", len(db.entries), self._db_path)

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def add_entry(self, entry: BrainEntry) -> BrainEntry:
        """
        Append *entry* to the database and persist.

        Returns
        -------
        The saved BrainEntry.
        """
        db = self.load()
        db.entries.append(entry)
        self.save(db)
        logger.info("Added entry %s: %r", entry.short_id, entry.text)
        return entry

    def delete_entry(self, entry_id: str) -> BrainEntry:
        """
        Remove the entry matching *entry_id* and push it onto the undo stack.

        Parameters
        ----------
        entry_id:
            Full UUID or short-ID prefix.

        Returns
        -------
        The deleted BrainEntry.

        Raises
        ------
        EntryNotFoundError
        """
        db = self.load()
        entry = db.get_by_id(entry_id)
        if entry is None:
            raise EntryNotFoundError(f"No entry found with id '{entry_id}'.")

        db.entries.remove(entry)

        # Push to undo stack (cap size)
        db.undo_stack.append(entry)
        if len(db.undo_stack) > MAX_UNDO_HISTORY:
            db.undo_stack = db.undo_stack[-MAX_UNDO_HISTORY:]

        self.save(db)
        logger.info("Deleted entry %s.", entry.short_id)
        return entry

    def complete_entry(self, entry_id: str) -> BrainEntry:
        """
        Mark the entry matching *entry_id* as completed.

        Returns
        -------
        The updated BrainEntry.

        Raises
        ------
        EntryNotFoundError
        """
        db = self.load()
        entry = db.get_by_id(entry_id)
        if entry is None:
            raise EntryNotFoundError(f"No entry found with id '{entry_id}'.")

        entry.mark_complete()
        self.save(db)
        logger.info("Completed entry %s.", entry.short_id)
        return entry

    def undo_delete(self) -> Optional[BrainEntry]:
        """
        Restore the most recently deleted entry from the undo stack.

        Returns
        -------
        The restored BrainEntry, or ``None`` if the stack is empty.
        """
        db = self.load()
        if not db.undo_stack:
            return None
        entry = db.undo_stack.pop()
        db.entries.append(entry)
        self.save(db)
        logger.info("Restored entry %s via undo.", entry.short_id)
        return entry

    def search(self, query: str, fuzzy: bool = False) -> list[BrainEntry]:
        """
        Search entries by text and category.

        Parameters
        ----------
        query:
            Search string (case-insensitive substring match by default).
        fuzzy:
            If ``True``, use fuzzy matching via difflib.

        Returns
        -------
        List of matching BrainEntry objects.
        """
        db = self.load()
        q = query.lower().strip()

        if not fuzzy:
            return [
                e
                for e in db.entries
                if q in e.text.lower() or q in e.category.lower() or q in " ".join(e.tags).lower()
            ]

        # Fuzzy search using SequenceMatcher
        from difflib import SequenceMatcher
        from app.constants import FUZZY_SEARCH_THRESHOLD

        def _ratio(a: str, b: str) -> int:
            return int(SequenceMatcher(None, a, b).ratio() * 100)

        results: list[BrainEntry] = []
        for entry in db.entries:
            score = max(
                _ratio(q, entry.text.lower()),
                _ratio(q, entry.category.lower()),
            )
            if score >= FUZZY_SEARCH_THRESHOLD:
                results.append(entry)
        return results

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def backup(self) -> Path:
        """
        Copy the database file to a timestamped backup in ``data/backups/``.

        Returns
        -------
        Path to the backup file.

        Raises
        ------
        StorageError if the source database does not exist.
        """
        if not self._db_path.exists():
            raise StorageError("No database file to back up.")

        backup_dir = self._db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
        backup_path = backup_dir / f"braindump_backup_{timestamp}.json"
        shutil.copy2(self._db_path, backup_path)
        logger.info("Backup created at %s.", backup_path)
        return backup_path

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def export_json(self, output_path: Path) -> Path:
        """Export all entries as a pretty JSON file."""
        db = self.load()
        self._write_json(output_path, db.model_dump_serializable())
        logger.info("Exported JSON to %s.", output_path)
        return output_path

    def export_csv(self, output_path: Path) -> Path:
        """Export all entries as a CSV file."""
        db = self.load()
        fieldnames = [
            "id", "text", "category", "priority", "deadline",
            "created_at", "completed", "completed_at", "tags",
        ]

        try:
            with output_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for entry in db.sorted_entries():
                    row = entry.model_dump_serializable()
                    row["tags"] = "|".join(row["tags"])
                    # Keep only the columns we care about
                    filtered = {k: row.get(k, "") for k in fieldnames}
                    writer.writerow(filtered)
        except OSError as exc:
            raise StorageError(f"Failed to write CSV to {output_path}: {exc}") from exc

        logger.info("Exported CSV to %s.", output_path)
        return output_path

    def export_markdown(self, output_path: Path) -> Path:
        """Export all entries as a Markdown file."""
        db = self.load()
        lines: list[str] = [
            "# BrainDump Export",
            f"> Generated: {datetime.now().strftime(DISPLAY_DATE_FORMAT)}",
            "",
        ]

        by_category: dict[str, list[BrainEntry]] = {}
        for entry in db.sorted_entries():
            by_category.setdefault(entry.category, []).append(entry)

        for category, entries in sorted(by_category.items()):
            lines.append(f"## {category}")
            for e in entries:
                status = "✅" if e.completed else "⬜"
                deadline = (
                    e.deadline.strftime(DISPLAY_DATE_FORMAT) if e.deadline else "—"
                )
                tags = ", ".join(f"`{t}`" for t in e.tags) if e.tags else ""
                line = f"- {status} **{e.text}**"
                if deadline != "—":
                    line += f" _(⏰ {deadline})_"
                if tags:
                    line += f" {tags}"
                lines.append(line)
            lines.append("")

        try:
            output_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError as exc:
            raise StorageError(
                f"Failed to write Markdown to {output_path}: {exc}"
            ) from exc

        logger.info("Exported Markdown to %s.", output_path)
        return output_path
