"""
test_storage.py
===============
Unit tests for app.storage.StorageManager.

All tests use a temporary directory so they never touch the real database.

Coverage targets
----------------
- load / save round-trip
- add_entry
- delete_entry + undo_delete
- complete_entry
- search (exact + fuzzy)
- backup
- export_json / export_csv / export_markdown
- error paths (corrupted file, missing entry)
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from app.models import BrainDumpDB, BrainEntry
from app.storage import EntryNotFoundError, StorageError, StorageManager
from app.constants import Category, Priority


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a path inside tmp_path for a test database."""
    return tmp_path / "test_braindump.json"


@pytest.fixture()
def storage(tmp_db: Path) -> StorageManager:
    """Return a StorageManager backed by a fresh temp file."""
    return StorageManager(db_path=tmp_db)


@pytest.fixture()
def sample_entry() -> BrainEntry:
    return BrainEntry(
        text="Buy milk tomorrow",
        category=Category.SHOPPING,
        priority=Priority.MEDIUM,
    )


@pytest.fixture()
def sample_entry_with_deadline() -> BrainEntry:
    return BrainEntry(
        text="Fix login bug by Friday",
        category=Category.CODING,
        priority=Priority.HIGH,
        deadline=datetime(2026, 8, 21, 23, 59, 0),
    )


@pytest.fixture()
def populated_storage(storage: StorageManager) -> StorageManager:
    """A StorageManager pre-loaded with 3 entries."""
    storage.add_entry(BrainEntry(text="Buy groceries", category=Category.SHOPPING))
    storage.add_entry(BrainEntry(text="Fix bug in auth module", category=Category.CODING))
    storage.add_entry(
        BrainEntry(
            text="Study for exam",
            category=Category.STUDY,
            deadline=datetime(2026, 9, 1, 10, 0),
        )
    )
    return storage


# ===========================================================================
# load / save
# ===========================================================================

class TestLoadSave:
    def test_load_creates_empty_db_when_missing(self, storage: StorageManager, tmp_db: Path):
        assert not tmp_db.exists() or tmp_db.stat().st_size == 0 or True
        db = storage.load()
        assert isinstance(db, BrainDumpDB)
        assert db.entries == []

    def test_load_creates_file_on_disk(self, storage: StorageManager, tmp_db: Path):
        storage.load()
        assert tmp_db.exists()

    def test_save_and_reload(self, storage: StorageManager, sample_entry: BrainEntry):
        db = storage.load()
        db.entries.append(sample_entry)
        storage.save(db)

        db2 = storage.load()
        assert len(db2.entries) == 1
        assert db2.entries[0].text == sample_entry.text

    def test_round_trip_preserves_all_fields(
        self, storage: StorageManager, sample_entry_with_deadline: BrainEntry
    ):
        db = storage.load()
        db.entries.append(sample_entry_with_deadline)
        storage.save(db)

        loaded = storage.load()
        e = loaded.entries[0]
        assert e.id == sample_entry_with_deadline.id
        assert e.text == sample_entry_with_deadline.text
        assert e.deadline == sample_entry_with_deadline.deadline
        assert e.category == sample_entry_with_deadline.category
        assert e.priority == sample_entry_with_deadline.priority
        assert e.completed is False

    def test_corrupted_json_raises_storage_error(self, tmp_db: Path):
        tmp_db.parent.mkdir(parents=True, exist_ok=True)
        tmp_db.write_text("{invalid json!!", encoding="utf-8")
        sm = StorageManager(db_path=tmp_db)
        with pytest.raises(StorageError, match="corrupted"):
            sm.load()

    def test_save_multiple_entries(self, storage: StorageManager):
        entries = [BrainEntry(text=f"Note {i}") for i in range(5)]
        db = storage.load()
        db.entries.extend(entries)
        storage.save(db)

        loaded = storage.load()
        assert len(loaded.entries) == 5


# ===========================================================================
# add_entry
# ===========================================================================

class TestAddEntry:
    def test_add_returns_entry(self, storage: StorageManager, sample_entry: BrainEntry):
        result = storage.add_entry(sample_entry)
        assert result.id == sample_entry.id

    def test_add_persists_to_disk(self, storage: StorageManager, sample_entry: BrainEntry):
        storage.add_entry(sample_entry)
        db = storage.load()
        assert len(db.entries) == 1

    def test_add_multiple(self, storage: StorageManager):
        for i in range(3):
            storage.add_entry(BrainEntry(text=f"Note {i}"))
        db = storage.load()
        assert len(db.entries) == 3

    def test_add_preserves_uuid(self, storage: StorageManager, sample_entry: BrainEntry):
        storage.add_entry(sample_entry)
        db = storage.load()
        assert db.entries[0].id == sample_entry.id


# ===========================================================================
# delete_entry + undo_delete
# ===========================================================================

class TestDeleteEntry:
    def test_delete_removes_entry(self, populated_storage: StorageManager):
        db = populated_storage.load()
        entry_id = db.entries[0].id
        populated_storage.delete_entry(entry_id)
        db2 = populated_storage.load()
        assert all(e.id != entry_id for e in db2.entries)

    def test_delete_returns_entry(self, populated_storage: StorageManager):
        db = populated_storage.load()
        entry = db.entries[0]
        deleted = populated_storage.delete_entry(entry.id)
        assert deleted.id == entry.id

    def test_delete_unknown_id_raises(self, storage: StorageManager):
        with pytest.raises(EntryNotFoundError):
            storage.delete_entry("nonexistent-id")

    def test_delete_pushes_to_undo_stack(self, populated_storage: StorageManager):
        db = populated_storage.load()
        entry_id = db.entries[0].id
        populated_storage.delete_entry(entry_id)
        db2 = populated_storage.load()
        assert len(db2.undo_stack) == 1
        assert db2.undo_stack[0].id == entry_id

    def test_delete_by_short_id(self, populated_storage: StorageManager):
        db = populated_storage.load()
        short_id = db.entries[0].id[:8]
        populated_storage.delete_entry(short_id)
        db2 = populated_storage.load()
        assert len(db2.entries) == 2

    def test_undo_restores_entry(self, populated_storage: StorageManager):
        db = populated_storage.load()
        original_id = db.entries[0].id
        populated_storage.delete_entry(original_id)
        restored = populated_storage.undo_delete()
        assert restored is not None
        assert restored.id == original_id
        db2 = populated_storage.load()
        assert any(e.id == original_id for e in db2.entries)

    def test_undo_empty_stack_returns_none(self, storage: StorageManager):
        result = storage.undo_delete()
        assert result is None

    def test_undo_stack_max_size(self, storage: StorageManager):
        from app.constants import MAX_UNDO_HISTORY
        # Add more entries than MAX_UNDO_HISTORY and delete them all
        entries = [BrainEntry(text=f"Note {i}") for i in range(MAX_UNDO_HISTORY + 3)]
        for e in entries:
            storage.add_entry(e)
        for e in entries:
            storage.delete_entry(e.id)
        db = storage.load()
        assert len(db.undo_stack) <= MAX_UNDO_HISTORY


# ===========================================================================
# complete_entry
# ===========================================================================

class TestCompleteEntry:
    def test_complete_sets_flag(self, populated_storage: StorageManager):
        db = populated_storage.load()
        entry_id = db.entries[0].id
        populated_storage.complete_entry(entry_id)
        db2 = populated_storage.load()
        entry = db2.get_by_id(entry_id)
        assert entry is not None
        assert entry.completed is True

    def test_complete_sets_completed_at(self, populated_storage: StorageManager):
        db = populated_storage.load()
        entry_id = db.entries[0].id
        populated_storage.complete_entry(entry_id)
        db2 = populated_storage.load()
        entry = db2.get_by_id(entry_id)
        assert entry.completed_at is not None

    def test_complete_unknown_id_raises(self, storage: StorageManager):
        with pytest.raises(EntryNotFoundError):
            storage.complete_entry("bad-id")

    def test_complete_returns_entry(self, populated_storage: StorageManager):
        db = populated_storage.load()
        entry_id = db.entries[0].id
        result = populated_storage.complete_entry(entry_id)
        assert result.id == entry_id
        assert result.completed is True


# ===========================================================================
# search
# ===========================================================================

class TestSearch:
    def test_exact_text_match(self, populated_storage: StorageManager):
        results = populated_storage.search("groceries")
        assert len(results) == 1
        assert "groceries" in results[0].text.lower()

    def test_category_match(self, populated_storage: StorageManager):
        results = populated_storage.search("coding")
        assert any(e.category == Category.CODING for e in results)

    def test_case_insensitive(self, populated_storage: StorageManager):
        results_lower = populated_storage.search("bug")
        results_upper = populated_storage.search("BUG")
        assert len(results_lower) == len(results_upper)

    def test_no_match_returns_empty(self, populated_storage: StorageManager):
        results = populated_storage.search("zzznomatchzzz")
        assert results == []

    def test_fuzzy_match(self, populated_storage: StorageManager):
        # "grocerie" is close enough to "groceries"
        results = populated_storage.search("grocerie", fuzzy=True)
        assert len(results) >= 1

    def test_tag_match(self, storage: StorageManager):
        entry = BrainEntry(text="Fix prod issue", tags=["urgent", "prod"])
        storage.add_entry(entry)
        results = storage.search("urgent")
        assert len(results) == 1


# ===========================================================================
# backup
# ===========================================================================

class TestBackup:
    def test_backup_creates_file(self, populated_storage: StorageManager, tmp_db: Path):
        backup_path = populated_storage.backup()
        assert backup_path.exists()

    def test_backup_has_timestamp_in_name(self, populated_storage: StorageManager):
        backup_path = populated_storage.backup()
        assert re.search(r"\d{8}_\d{6}", backup_path.name)

    def test_backup_content_matches_db(self, populated_storage: StorageManager):
        backup_path = populated_storage.backup()
        original = json.loads(populated_storage._db_path.read_text())
        backup = json.loads(backup_path.read_text())
        assert original == backup

    def test_backup_no_db_raises(self, tmp_path: Path):
        sm = StorageManager(db_path=tmp_path / "nonexistent.json")
        with pytest.raises(StorageError):
            sm.backup()


# ===========================================================================
# export
# ===========================================================================

class TestExportJson:
    def test_export_json_creates_file(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.json"
        populated_storage.export_json(out)
        assert out.exists()

    def test_export_json_valid_structure(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.json"
        populated_storage.export_json(out)
        data = json.loads(out.read_text())
        assert "entries" in data
        assert len(data["entries"]) == 3

    def test_export_json_roundtrip(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.json"
        populated_storage.export_json(out)
        raw = json.loads(out.read_text())
        db = BrainDumpDB.from_serializable(raw)
        assert len(db.entries) == 3


class TestExportCsv:
    def test_export_csv_creates_file(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.csv"
        populated_storage.export_csv(out)
        assert out.exists()

    def test_export_csv_has_header(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.csv"
        populated_storage.export_csv(out)
        with out.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert "id" in reader.fieldnames  # type: ignore[operator]
            assert "text" in reader.fieldnames  # type: ignore[operator]

    def test_export_csv_row_count(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.csv"
        populated_storage.export_csv(out)
        with out.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 3

    def test_export_csv_tags_joined(self, storage: StorageManager, tmp_path: Path):
        storage.add_entry(BrainEntry(text="Tagged entry", tags=["a", "b", "c"]))
        out = tmp_path / "export.csv"
        storage.export_csv(out)
        with out.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert rows[0]["tags"] == "a|b|c"


class TestExportMarkdown:
    def test_export_md_creates_file(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.md"
        populated_storage.export_markdown(out)
        assert out.exists()

    def test_export_md_has_title(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.md"
        populated_storage.export_markdown(out)
        content = out.read_text(encoding="utf-8")
        assert "# BrainDump Export" in content

    def test_export_md_has_categories(self, populated_storage: StorageManager, tmp_path: Path):
        out = tmp_path / "export.md"
        populated_storage.export_markdown(out)
        content = out.read_text(encoding="utf-8")
        assert "## Shopping" in content or "## Coding" in content or "## Study" in content

    def test_export_md_completed_checkmark(self, storage: StorageManager, tmp_path: Path):
        entry = BrainEntry(text="Done task", completed=True)
        entry.completed_at = datetime.now()
        db = storage.load()
        db.entries.append(entry)
        storage.save(db)
        out = tmp_path / "export.md"
        storage.export_markdown(out)
        content = out.read_text(encoding="utf-8")
        assert "✅" in content


# ===========================================================================
# BrainDumpDB helpers
# ===========================================================================

class TestBrainDumpDB:
    def test_get_by_id_full(self):
        e = BrainEntry(text="Test")
        db = BrainDumpDB(entries=[e])
        assert db.get_by_id(e.id) is e

    def test_get_by_id_short(self):
        e = BrainEntry(text="Test")
        db = BrainDumpDB(entries=[e])
        assert db.get_by_id(e.id[:8]) is e

    def test_get_by_id_unknown(self):
        db = BrainDumpDB()
        assert db.get_by_id("nope") is None

    def test_get_pending(self):
        e1 = BrainEntry(text="A", completed=False)
        e2 = BrainEntry(text="B", completed=True)
        db = BrainDumpDB(entries=[e1, e2])
        assert db.get_pending() == [e1]

    def test_get_completed(self):
        e1 = BrainEntry(text="A", completed=False)
        e2 = BrainEntry(text="B", completed=True)
        db = BrainDumpDB(entries=[e1, e2])
        assert db.get_completed() == [e2]

    def test_get_overdue(self):
        past = datetime(2020, 1, 1)
        future = datetime(2099, 1, 1)
        e1 = BrainEntry(text="Old", deadline=past, completed=False)
        e2 = BrainEntry(text="Future", deadline=future, completed=False)
        e3 = BrainEntry(text="Done", deadline=past, completed=True)
        db = BrainDumpDB(entries=[e1, e2, e3])
        overdue = db.get_overdue()
        assert e1 in overdue
        assert e2 not in overdue
        assert e3 not in overdue

    def test_sorted_entries_deadline_first(self):
        no_deadline = BrainEntry(text="No date")
        early = BrainEntry(text="Early", deadline=datetime(2026, 9, 1))
        late = BrainEntry(text="Late", deadline=datetime(2026, 12, 1))
        db = BrainDumpDB(entries=[no_deadline, late, early])
        sorted_e = db.sorted_entries()
        assert sorted_e[0].text == "Early"
        assert sorted_e[1].text == "Late"
        # no_deadline goes last
        assert sorted_e[-1].text == "No date"
