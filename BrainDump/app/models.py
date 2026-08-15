"""
models.py
=========
Pydantic data models for BrainDump.

Classes
-------
BrainEntry   - a single saved thought / reminder / task
BrainDumpDB  - the top-level database object (list of entries + metadata)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.constants import (
    Category,
    Priority,
    DATETIME_FORMAT,
    ALL_CATEGORIES,
    ALL_PRIORITIES,
)


# ---------------------------------------------------------------------------
# BrainEntry
# ---------------------------------------------------------------------------

class BrainEntry(BaseModel):
    """Represents a single BrainDump entry."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier (UUID4).",
    )
    text: str = Field(..., min_length=1, description="The raw thought text.")
    deadline: Optional[datetime] = Field(
        default=None,
        description="Parsed deadline datetime; None if no date was detected.",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the entry was created.",
    )
    completed: bool = Field(default=False, description="Whether the entry is done.")
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the entry was marked completed.",
    )
    category: str = Field(
        default=Category.GENERAL,
        description="Auto-detected or user-specified category.",
    )
    priority: str = Field(
        default=Priority.MEDIUM,
        description="Priority level: High / Medium / Low.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional user-defined tags.",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in ALL_CATEGORIES:
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {ALL_CATEGORIES}"
            )
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in ALL_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{v}'. Must be one of: {ALL_PRIORITIES}"
            )
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Entry text cannot be empty or whitespace only.")
        return stripped

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_overdue(self) -> bool:
        """Return True if the deadline has passed and entry is not completed."""
        if self.deadline is None or self.completed:
            return False
        return datetime.now() > self.deadline

    @property
    def short_id(self) -> str:
        """Return the first 8 characters of the UUID for display."""
        return self.id[:8]

    def mark_complete(self) -> None:
        """Mark this entry as completed and record the timestamp."""
        self.completed = True
        self.completed_at = datetime.now()

    def model_dump_serializable(self) -> dict:
        """Return a JSON-serializable dict (datetimes as ISO strings)."""
        data = self.model_dump()
        for key in ("deadline", "created_at", "completed_at"):
            if data[key] is not None:
                data[key] = data[key].strftime(DATETIME_FORMAT)
        return data

    @classmethod
    def from_serializable(cls, data: dict) -> "BrainEntry":
        """Reconstruct a BrainEntry from a serialised dict (strings → datetimes)."""
        for key in ("deadline", "created_at", "completed_at"):
            if data.get(key) is not None:
                data[key] = datetime.strptime(data[key], DATETIME_FORMAT)
        return cls(**data)

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        deadline_str = (
            self.deadline.strftime("%d %b %Y %I:%M %p")
            if self.deadline
            else "—"
        )
        return (
            f"[{status}] [{self.short_id}] {self.text} "
            f"| {self.category} | {self.priority} | ⏰ {deadline_str}"
        )


# ---------------------------------------------------------------------------
# BrainDumpDB
# ---------------------------------------------------------------------------

class BrainDumpDB(BaseModel):
    """Top-level database model that wraps the list of entries."""

    version: str = Field(default="1.0.0", description="Schema version.")
    entries: list[BrainEntry] = Field(default_factory=list)
    undo_stack: list[BrainEntry] = Field(
        default_factory=list,
        description="Recently deleted entries for undo support.",
    )

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def get_by_id(self, entry_id: str) -> Optional[BrainEntry]:
        """Find an entry by full UUID or short-ID prefix."""
        for entry in self.entries:
            if entry.id == entry_id or entry.id.startswith(entry_id):
                return entry
        return None

    def get_pending(self) -> list[BrainEntry]:
        return [e for e in self.entries if not e.completed]

    def get_completed(self) -> list[BrainEntry]:
        return [e for e in self.entries if e.completed]

    def get_overdue(self) -> list[BrainEntry]:
        return [e for e in self.entries if e.is_overdue]

    def get_by_category(self, category: str) -> list[BrainEntry]:
        return [e for e in self.entries if e.category.lower() == category.lower()]

    def sorted_entries(self) -> list[BrainEntry]:
        """Sort by deadline (None last), then by created_at descending."""
        with_deadline = sorted(
            [e for e in self.entries if e.deadline],
            key=lambda e: e.deadline,  # type: ignore[arg-type]
        )
        without_deadline = sorted(
            [e for e in self.entries if not e.deadline],
            key=lambda e: e.created_at,
            reverse=True,
        )
        return with_deadline + without_deadline

    def model_dump_serializable(self) -> dict:
        """Return JSON-safe dict for persistence."""
        return {
            "version": self.version,
            "entries": [e.model_dump_serializable() for e in self.entries],
            "undo_stack": [e.model_dump_serializable() for e in self.undo_stack],
        }

    @classmethod
    def from_serializable(cls, data: dict) -> "BrainDumpDB":
        """Rebuild from a raw JSON dict."""
        entries = [BrainEntry.from_serializable(e) for e in data.get("entries", [])]
        undo_stack = [
            BrainEntry.from_serializable(e) for e in data.get("undo_stack", [])
        ]
        return cls(
            version=data.get("version", "1.0.0"),
            entries=entries,
            undo_stack=undo_stack,
        )
