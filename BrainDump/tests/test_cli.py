"""
test_cli.py
===========
Integration tests for the Typer CLI commands.

Strategy
--------
- Each test creates an isolated StorageManager backed by a tmp_path DB.
- We inject it via cli.set_storage() before invoking commands.
- Commands are invoked through Typer's CliRunner so we get real stdout/exit codes.
- We validate exit codes, stdout content, and actual DB state after each command.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli import app, set_storage
from app.models import BrainEntry
from app.storage import StorageManager
from app.constants import Category, Priority

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path):
    """
    Before every test: create a fresh StorageManager in tmp_path and inject
    it into the CLI.  Runs automatically for every test in this module.
    """
    db_path = tmp_path / "test_braindump.json"
    sm = StorageManager(db_path=db_path)
    set_storage(sm)
    yield sm
    # Teardown: nothing needed – tmp_path is cleaned by pytest


@pytest.fixture()
def storage_with_entries(isolated_storage: StorageManager) -> StorageManager:
    """Pre-populate storage with a few entries."""
    isolated_storage.add_entry(
        BrainEntry(
            text="Buy milk tomorrow",
            category=Category.SHOPPING,
            priority=Priority.MEDIUM,
        )
    )
    isolated_storage.add_entry(
        BrainEntry(
            text="Fix login bug by Friday",
            category=Category.CODING,
            priority=Priority.HIGH,
            deadline=datetime(2026, 8, 21, 23, 59),
        )
    )
    isolated_storage.add_entry(
        BrainEntry(
            text="Study for machine learning exam",
            category=Category.STUDY,
            priority=Priority.HIGH,
            deadline=datetime(2026, 9, 1, 10, 0),
        )
    )
    return isolated_storage


# ===========================================================================
# add
# ===========================================================================

class TestAddCommand:
    def test_add_basic(self, isolated_storage: StorageManager):
        result = runner.invoke(app, ["add", "Buy groceries"])
        assert result.exit_code == 0
        assert "Added" in result.output

        db = isolated_storage.load()
        assert len(db.entries) == 1
        assert db.entries[0].text == "Buy groceries"

    def test_add_with_priority(self, isolated_storage: StorageManager):
        result = runner.invoke(app, ["add", "Fix critical bug", "--priority", "High"])
        assert result.exit_code == 0
        db = isolated_storage.load()
        assert db.entries[0].priority == Priority.HIGH

    def test_add_with_category_override(self, isolated_storage: StorageManager):
        result = runner.invoke(app, ["add", "Random thought", "--category", "Personal"])
        assert result.exit_code == 0
        db = isolated_storage.load()
        assert db.entries[0].category == Category.PERSONAL

    def test_add_with_tags(self, isolated_storage: StorageManager):
        result = runner.invoke(app, ["add", "Ship feature", "--tags", "work,urgent"])
        assert result.exit_code == 0
        db = isolated_storage.load()
        assert "work" in db.entries[0].tags
        assert "urgent" in db.entries[0].tags

    def test_add_with_explicit_deadline(self, isolated_storage: StorageManager):
        result = runner.invoke(app, ["add", "Report", "--deadline", "tomorrow"])
        assert result.exit_code == 0
        db = isolated_storage.load()
        assert db.entries[0].deadline is not None

    def test_add_invalid_category_exits_1(self):
        result = runner.invoke(app, ["add", "Hello", "--category", "InvalidCat"])
        assert result.exit_code == 1

    def test_add_invalid_priority_exits_1(self):
        result = runner.invoke(app, ["add", "Hello", "--priority", "Urgent"])
        assert result.exit_code == 1

    def test_add_auto_detects_category(self, isolated_storage: StorageManager):
        runner.invoke(app, ["add", "Fix the authentication bug"])
        db = isolated_storage.load()
        assert db.entries[0].category == Category.CODING

    def test_add_shopping_auto_category(self, isolated_storage: StorageManager):
        runner.invoke(app, ["add", "Buy apples from the store"])
        db = isolated_storage.load()
        assert db.entries[0].category == Category.SHOPPING

    def test_add_shows_category_in_output(self):
        result = runner.invoke(app, ["add", "Buy milk"])
        assert "Shopping" in result.output or "Category" in result.output


# ===========================================================================
# list
# ===========================================================================

class TestListCommand:
    def test_list_empty(self):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No entries" in result.output

    def test_list_shows_entries(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # The table renders — check category names which are not truncated
        assert "Shopping" in result.output
        assert "Coding" in result.output

    def test_list_filter_by_category(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["list", "--category", "Coding"])
        assert result.exit_code == 0
        assert "Coding" in result.output
        assert "Shopping" not in result.output

    def test_list_filter_pending(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        storage_with_entries.complete_entry(db.entries[0].id)
        result = runner.invoke(app, ["list", "--pending"])
        assert result.exit_code == 0
        # After completing first entry (Shopping) only Coding + Study remain pending
        assert "Coding" in result.output or "Study" in result.output

    def test_list_filter_completed(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        storage_with_entries.complete_entry(db.entries[0].id)
        result = runner.invoke(app, ["list", "--completed"])
        assert result.exit_code == 0
        assert "Showing 1 entry" in result.output

    def test_list_filter_priority(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["list", "--priority", "High"])
        assert result.exit_code == 0
        # 2 High-priority entries in fixture
        assert "Showing 2 entries" in result.output

    def test_list_limit(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["list", "--limit", "1"])
        assert result.exit_code == 0
        assert "Showing 1 entry" in result.output

    def test_list_invalid_category_exits_1(self):
        result = runner.invoke(app, ["list", "--category", "Bogus"])
        assert result.exit_code == 1

    def test_list_filter_by_tag(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry = db.entries[0]
        entry.tags = ["mytag"]
        storage_with_entries.save(db)
        result = runner.invoke(app, ["list", "--tag", "mytag"])
        assert result.exit_code == 0
        assert "Showing 1 entry" in result.output


# ===========================================================================
# search
# ===========================================================================

class TestSearchCommand:
    def test_search_finds_match(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["search", "bug"])
        assert result.exit_code == 0
        assert "Coding" in result.output  # category confirms the right entry showed

    def test_search_no_results(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["search", "zzznomatch"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_search_case_insensitive(self, storage_with_entries: StorageManager):
        results_lower = runner.invoke(app, ["search", "bug"])
        results_upper = runner.invoke(app, ["search", "BUG"])
        # Both should succeed and find the same number of results
        assert results_lower.exit_code == 0
        assert results_upper.exit_code == 0
        assert "Coding" in results_lower.output
        assert "Coding" in results_upper.output

    def test_search_by_category(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["search", "shopping"])
        assert result.exit_code == 0
        assert "Shopping" in result.output

    def test_search_fuzzy_flag(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["search", "milkk", "--fuzzy"])
        assert result.exit_code == 0
        # fuzzy may or may not find it – just check no crash
        assert result.exit_code == 0


# ===========================================================================
# complete
# ===========================================================================

class TestCompleteCommand:
    def test_complete_by_short_id(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        short_id = db.entries[0].id[:8]
        result = runner.invoke(app, ["complete", short_id])
        assert result.exit_code == 0
        assert "complete" in result.output.lower()

        db2 = storage_with_entries.load()
        entry = db2.get_by_id(short_id)
        assert entry is not None
        assert entry.completed is True

    def test_complete_unknown_id(self):
        result = runner.invoke(app, ["complete", "deadbeef"])
        assert result.exit_code == 1
        assert "No entry" in result.output

    def test_complete_sets_completed_at(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        runner.invoke(app, ["complete", entry_id])
        db2 = storage_with_entries.load()
        assert db2.get_by_id(entry_id).completed_at is not None


# ===========================================================================
# delete + undo
# ===========================================================================

class TestDeleteCommand:
    def test_delete_with_force(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        result = runner.invoke(app, ["delete", entry_id, "--force"])
        assert result.exit_code == 0
        db2 = storage_with_entries.load()
        assert all(e.id != entry_id for e in db2.entries)

    def test_delete_unknown_id(self):
        result = runner.invoke(app, ["delete", "deadbeef", "--force"])
        assert result.exit_code == 1

    def test_delete_shows_undo_hint(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        result = runner.invoke(app, ["delete", entry_id, "--force"])
        assert "undo" in result.output.lower()

    def test_delete_cancel_on_prompt(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        # Answer "n" to the confirmation prompt
        result = runner.invoke(app, ["delete", entry_id], input="n\n")
        assert result.exit_code == 0
        db2 = storage_with_entries.load()
        assert any(e.id == entry_id for e in db2.entries)


class TestUndoCommand:
    def test_undo_restores_entry(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        runner.invoke(app, ["delete", entry_id, "--force"])
        result = runner.invoke(app, ["undo"])
        assert result.exit_code == 0
        assert "Restored" in result.output
        db2 = storage_with_entries.load()
        assert any(e.id == entry_id for e in db2.entries)

    def test_undo_empty_stack(self, isolated_storage: StorageManager):
        result = runner.invoke(app, ["undo"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "Nothing" in result.output


# ===========================================================================
# stats
# ===========================================================================

class TestStatsCommand:
    def test_stats_empty(self):
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "No entries" in result.output

    def test_stats_shows_totals(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Total" in result.output

    def test_stats_after_complete(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        storage_with_entries.complete_entry(db.entries[0].id)
        result = runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "Completed" in result.output


# ===========================================================================
# export
# ===========================================================================

class TestExportCommand:
    def test_export_json(self, storage_with_entries: StorageManager, tmp_path: Path):
        out = tmp_path / "out.json"
        result = runner.invoke(app, ["export", "json", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_export_csv(self, storage_with_entries: StorageManager, tmp_path: Path):
        out = tmp_path / "out.csv"
        result = runner.invoke(app, ["export", "csv", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_export_markdown(self, storage_with_entries: StorageManager, tmp_path: Path):
        out = tmp_path / "out.md"
        result = runner.invoke(app, ["export", "markdown", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_export_invalid_format(self):
        result = runner.invoke(app, ["export", "xml"])
        assert result.exit_code == 1
        assert "Unknown format" in result.output

    def test_export_default_filename(self, storage_with_entries: StorageManager, tmp_path: Path):
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(app, ["export", "json"])
            assert result.exit_code == 0
            assert (tmp_path / "braindump_export.json").exists()
        finally:
            os.chdir(old_cwd)


# ===========================================================================
# backup
# ===========================================================================

class TestBackupCommand:
    def test_backup_creates_file(self, storage_with_entries: StorageManager):
        result = runner.invoke(app, ["backup"])
        assert result.exit_code == 0
        assert "Backup saved" in result.output

    def test_backup_no_db_exits_1(self, isolated_storage: StorageManager):
        # Don't add any entries and delete the db file if it exists
        if isolated_storage._db_path.exists():
            isolated_storage._db_path.unlink()
        result = runner.invoke(app, ["backup"])
        assert result.exit_code == 1


# ===========================================================================
# info
# ===========================================================================

class TestInfoCommand:
    def test_info_shows_detail(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        result = runner.invoke(app, ["info", entry_id])
        assert result.exit_code == 0
        assert db.entries[0].text in result.output

    def test_info_unknown_id(self):
        result = runner.invoke(app, ["info", "deadbeef"])
        assert result.exit_code == 1


# ===========================================================================
# tags
# ===========================================================================

class TestTagsCommand:
    def test_add_tags(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        result = runner.invoke(app, ["tags", entry_id, "--add", "newtag"])
        assert result.exit_code == 0
        db2 = storage_with_entries.load()
        assert "newtag" in db2.get_by_id(entry_id).tags

    def test_remove_tags(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry = db.entries[0]
        entry.tags = ["removeme", "keep"]
        storage_with_entries.save(db)
        result = runner.invoke(app, ["tags", entry.id, "--remove", "removeme"])
        assert result.exit_code == 0
        db2 = storage_with_entries.load()
        updated = db2.get_by_id(entry.id)
        assert "removeme" not in updated.tags
        assert "keep" in updated.tags

    def test_tags_unknown_id(self):
        result = runner.invoke(app, ["tags", "deadbeef", "--add", "x"])
        assert result.exit_code == 1


# ===========================================================================
# priority
# ===========================================================================

class TestPriorityCommand:
    def test_set_priority_high(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        result = runner.invoke(app, ["priority", entry_id, "High"])
        assert result.exit_code == 0
        db2 = storage_with_entries.load()
        assert db2.get_by_id(entry_id).priority == Priority.HIGH

    def test_set_priority_invalid(self, storage_with_entries: StorageManager):
        db = storage_with_entries.load()
        entry_id = db.entries[0].id
        result = runner.invoke(app, ["priority", entry_id, "Critical"])
        assert result.exit_code == 1

    def test_set_priority_unknown_entry(self):
        result = runner.invoke(app, ["priority", "deadbeef", "Low"])
        assert result.exit_code == 1


# ===========================================================================
# version flag
# ===========================================================================

class TestVersionFlag:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output


# ===========================================================================
# remind
# ===========================================================================

class TestRemindCommand:
    def test_remind_no_items(self, isolated_storage: StorageManager):
        result = runner.invoke(app, ["remind"])
        assert result.exit_code == 0

    def test_remind_shows_overdue(self, isolated_storage: StorageManager):
        past_entry = BrainEntry(
            text="Overdue task",
            deadline=datetime(2020, 1, 1),
            completed=False,
        )
        isolated_storage.add_entry(past_entry)
        result = runner.invoke(app, ["remind"])
        assert result.exit_code == 0
        # Table renders with overdue marker
        assert "Overdue" in result.output

    def test_remind_shows_due_today(self, isolated_storage: StorageManager):
        today_entry = BrainEntry(
            text="Due today task",
            deadline=datetime.now().replace(hour=23, minute=59),
            completed=False,
        )
        isolated_storage.add_entry(today_entry)
        result = runner.invoke(app, ["remind"])
        assert result.exit_code == 0
        # "Due Today" heading or the entry's short id in the table
        assert "Due Today" in result.output or today_entry.short_id in result.output
