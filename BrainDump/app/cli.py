"""
cli.py
======
Typer-based CLI definitions for BrainDump.

Commands
--------
add       – add a new thought
list      – list all thoughts (with filters)
search    – search by text / category
complete  – mark an entry as done
delete    – remove an entry
undo      – restore the last deleted entry
stats     – display statistics
export    – export to JSON / CSV / Markdown
backup    – create a timestamped backup
info      – show detail for one entry
tags      – add tags to an entry
priority  – change priority of an entry
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.prompt import Confirm

from app.constants import (
    ALL_CATEGORIES,
    ALL_PRIORITIES,
    EXPORT_FORMATS,
    APP_NAME,
    APP_VERSION,
    DB_FILE,
    Category,
    Priority,
)
from app.models import BrainEntry
from app.parser import detect_category, parse_deadline
from app.storage import EntryNotFoundError, StorageError, StorageManager
from app.utils import (
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
    render_entries_table,
    render_entry_detail,
    render_stats,
    print_app_banner,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------
app = typer.Typer(
    name="braindump",
    help=(
        f"[bold cyan]{APP_NAME}[/bold cyan] v{APP_VERSION} – "
        "Capture thoughts, reminders & tasks right from your terminal."
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

# Shared storage instance (swapped out in tests via dependency injection)
_storage = StorageManager()


def _get_storage() -> StorageManager:
    """Return the active StorageManager (allows test injection)."""
    return _storage


def set_storage(manager: StorageManager) -> None:
    """Override the storage manager – used in tests."""
    global _storage
    _storage = manager


# ---------------------------------------------------------------------------
# Version callback
# ---------------------------------------------------------------------------

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]{APP_NAME}[/bold cyan] v[bold]{APP_VERSION}[/bold]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging."),
) -> None:
    """BrainDump – your terminal thought-capture tool."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if ctx.invoked_subcommand is None:
        print_app_banner()
        console.print(ctx.get_help())


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

@app.command("add")
def add_entry(
    text: str = typer.Argument(..., help="The thought, reminder, or task to save."),
    category: Optional[str] = typer.Option(
        None,
        "--category", "-c",
        help=f"Override auto-detected category. Choices: {ALL_CATEGORIES}",
    ),
    priority: str = typer.Option(
        Priority.MEDIUM,
        "--priority", "-p",
        help="Priority level (High/Medium/Low).",
    ),
    tags: Optional[str] = typer.Option(
        None,
        "--tags", "-t",
        help="Comma-separated tags, e.g. 'work,urgent'.",
    ),
    deadline: Optional[str] = typer.Option(
        None,
        "--deadline", "-d",
        help="Override deadline with an explicit date string.",
    ),
) -> None:
    """Add a new thought / reminder / task.

    BrainDump automatically detects deadlines and categories from your text.

    Examples:

        braindump add "Buy milk tomorrow"

        braindump add "Fix login bug by Friday" --priority High

        braindump add "Submit report on 25 August at 5 PM" --tags work,urgent
    """
    # Resolve deadline
    if deadline:
        parsed_deadline = parse_deadline(deadline)
        if parsed_deadline is None:
            print_warning(f"Could not parse deadline '{deadline}' – stored as null.")
    else:
        parsed_deadline = parse_deadline(text)

    # Resolve category
    resolved_category: str
    if category:
        if category not in ALL_CATEGORIES:
            print_error(
                f"Invalid category '{category}'. "
                f"Valid choices: {', '.join(ALL_CATEGORIES)}"
            )
            raise typer.Exit(code=1)
        resolved_category = category
    else:
        resolved_category = detect_category(text)

    # Resolve priority
    if priority not in ALL_PRIORITIES:
        print_error(
            f"Invalid priority '{priority}'. "
            f"Valid choices: {', '.join(ALL_PRIORITIES)}"
        )
        raise typer.Exit(code=1)

    # Resolve tags
    tag_list: list[str] = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        entry = BrainEntry(
            text=text,
            deadline=parsed_deadline,
            category=resolved_category,
            priority=priority,
            tags=tag_list,
        )
        _get_storage().add_entry(entry)
    except (StorageError, ValueError) as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    # Success feedback
    deadline_msg = (
        f"⏰  [bold yellow]{parsed_deadline.strftime('%d %b %Y %I:%M %p')}[/bold yellow]"
        if parsed_deadline
        else "⏰  [dim]No deadline detected[/dim]"
    )
    console.print(
        f"\n[bold green]✓ Added![/bold green]  [cyan]{entry.short_id}[/cyan]  {text}"
    )
    console.print(f"   Category : [bold]{resolved_category}[/bold]")
    console.print(f"   Priority : [bold]{priority}[/bold]")
    console.print(f"   {deadline_msg}\n")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@app.command("list")
def list_entries(
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by category."
    ),
    pending_only: bool = typer.Option(
        False, "--pending", help="Show only pending entries."
    ),
    completed_only: bool = typer.Option(
        False, "--completed", help="Show only completed entries."
    ),
    overdue_only: bool = typer.Option(
        False, "--overdue", help="Show only overdue entries."
    ),
    priority: Optional[str] = typer.Option(
        None, "--priority", "-p", help="Filter by priority."
    ),
    tag: Optional[str] = typer.Option(
        None, "--tag", help="Filter entries containing this tag."
    ),
    limit: int = typer.Option(0, "--limit", "-n", help="Limit number of results (0 = all)."),
) -> None:
    """List all thoughts.

    Use --pending / --completed / --overdue to filter by status.
    Use --category / --priority / --tag for further filtering.
    """
    try:
        db = _get_storage().load()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    entries = db.sorted_entries()

    # Apply filters
    if category:
        if category not in ALL_CATEGORIES:
            print_error(f"Unknown category '{category}'.")
            raise typer.Exit(code=1)
        entries = [e for e in entries if e.category.lower() == category.lower()]

    if pending_only:
        entries = [e for e in entries if not e.completed]
    elif completed_only:
        entries = [e for e in entries if e.completed]

    if overdue_only:
        entries = [e for e in entries if e.is_overdue]

    if priority:
        if priority not in ALL_PRIORITIES:
            print_error(f"Unknown priority '{priority}'.")
            raise typer.Exit(code=1)
        entries = [e for e in entries if e.priority.lower() == priority.lower()]

    if tag:
        entries = [e for e in entries if tag.lower() in [t.lower() for t in e.tags]]

    if limit > 0:
        entries = entries[:limit]

    if not entries:
        print_info("No entries found matching the given filters.")
        return

    console.print(render_entries_table(entries))
    console.print(f"  [dim]Showing {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.[/dim]\n")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@app.command("search")
def search_entries(
    query: str = typer.Argument(..., help="Search term."),
    fuzzy: bool = typer.Option(False, "--fuzzy", "-f", help="Enable fuzzy matching."),
) -> None:
    """Search thoughts by text, category, or tags.

    Examples:

        braindump search bug

        braindump search "milk" --fuzzy
    """
    try:
        results = _get_storage().search(query, fuzzy=fuzzy)
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    if not results:
        print_info(f"No results found for [bold]'{query}'[/bold].")
        return

    mode_label = "fuzzy" if fuzzy else "exact"
    console.print(render_entries_table(results, title=f"Search results for '{query}' ({mode_label})"))
    console.print(f"  [dim]{len(results)} result(s).[/dim]\n")


# ---------------------------------------------------------------------------
# complete
# ---------------------------------------------------------------------------

@app.command("complete")
def complete_entry(
    entry_id: str = typer.Argument(..., help="Entry ID (full UUID or short prefix).")
) -> None:
    """Mark an entry as completed.

    Example:

        braindump complete a1b2c3d4
    """
    try:
        entry = _get_storage().complete_entry(entry_id)
    except EntryNotFoundError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    print_success(f"Marked [cyan]{entry.short_id}[/cyan] as complete: [dim]{entry.text}[/dim]")


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

@app.command("delete")
def delete_entry(
    entry_id: str = typer.Argument(..., help="Entry ID (full UUID or short prefix)."),
    force: bool = typer.Option(
        False, "--force", "-f", help="Skip confirmation prompt."
    ),
) -> None:
    """Delete an entry (stored for undo).

    Example:

        braindump delete a1b2c3d4
    """
    # Load first to show the text in the confirmation prompt
    try:
        db = _get_storage().load()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    entry = db.get_by_id(entry_id)
    if entry is None:
        print_error(f"No entry found with id '{entry_id}'.")
        raise typer.Exit(code=1)

    if not force:
        confirmed = Confirm.ask(
            f"Delete [bold red]{entry.short_id}[/bold red]: '{entry.text}'?"
        )
        if not confirmed:
            print_info("Delete cancelled.")
            return

    try:
        _get_storage().delete_entry(entry_id)
    except (EntryNotFoundError, StorageError) as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    print_success(
        f"Deleted [cyan]{entry.short_id}[/cyan]. "
        f"Run [bold]braindump undo[/bold] to restore it."
    )


# ---------------------------------------------------------------------------
# undo
# ---------------------------------------------------------------------------

@app.command("undo")
def undo_delete() -> None:
    """Restore the most recently deleted entry.

    Example:

        braindump undo
    """
    try:
        entry = _get_storage().undo_delete()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    if entry is None:
        print_warning("Nothing to undo – the undo stack is empty.")
        return

    print_success(f"Restored [cyan]{entry.short_id}[/cyan]: [dim]{entry.text}[/dim]")


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

@app.command("stats")
def show_stats() -> None:
    """Show statistics: totals, completion rate, breakdown by category.

    Example:

        braindump stats
    """
    try:
        db = _get_storage().load()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    if not db.entries:
        print_info("No entries yet. Add your first thought with [bold]braindump add[/bold].")
        return

    render_stats(db)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@app.command("export")
def export_data(
    fmt: str = typer.Argument(
        ...,
        help=f"Export format. One of: {EXPORT_FORMATS}",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output file path. Defaults to braindump_export.<fmt>.",
    ),
) -> None:
    """Export all entries to a file.

    Examples:

        braindump export json

        braindump export csv --output my_notes.csv

        braindump export markdown --output notes.md
    """
    fmt = fmt.lower()
    if fmt not in EXPORT_FORMATS:
        print_error(f"Unknown format '{fmt}'. Valid options: {', '.join(EXPORT_FORMATS)}")
        raise typer.Exit(code=1)

    storage = _get_storage()

    # Determine output path
    if output is None:
        ext = "md" if fmt == "markdown" else fmt
        output = Path(f"braindump_export.{ext}")

    try:
        if fmt == "json":
            path = storage.export_json(output)
        elif fmt == "csv":
            path = storage.export_csv(output)
        else:  # markdown
            path = storage.export_markdown(output)
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    print_success(f"Exported to [bold cyan]{path}[/bold cyan]")


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------

@app.command("backup")
def backup_data() -> None:
    """Create a timestamped backup of the database.

    Example:

        braindump backup
    """
    try:
        path = _get_storage().backup()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    print_success(f"Backup saved to [bold cyan]{path}[/bold cyan]")


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

@app.command("info")
def show_info(
    entry_id: str = typer.Argument(..., help="Entry ID (full UUID or short prefix).")
) -> None:
    """Show full details for a single entry.

    Example:

        braindump info a1b2c3d4
    """
    try:
        db = _get_storage().load()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    entry = db.get_by_id(entry_id)
    if entry is None:
        print_error(f"No entry found with id '{entry_id}'.")
        raise typer.Exit(code=1)

    console.print(render_entry_detail(entry))


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------

@app.command("tags")
def manage_tags(
    entry_id: str = typer.Argument(..., help="Entry ID."),
    add_tags: Optional[str] = typer.Option(
        None, "--add", help="Comma-separated tags to add."
    ),
    remove_tags: Optional[str] = typer.Option(
        None, "--remove", help="Comma-separated tags to remove."
    ),
) -> None:
    """Add or remove tags on an entry.

    Examples:

        braindump tags a1b2c3d4 --add urgent,work

        braindump tags a1b2c3d4 --remove urgent
    """
    try:
        db = _get_storage().load()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    entry = db.get_by_id(entry_id)
    if entry is None:
        print_error(f"No entry found with id '{entry_id}'.")
        raise typer.Exit(code=1)

    if add_tags:
        new = [t.strip() for t in add_tags.split(",") if t.strip()]
        for t in new:
            if t not in entry.tags:
                entry.tags.append(t)

    if remove_tags:
        rm = [t.strip() for t in remove_tags.split(",") if t.strip()]
        entry.tags = [t for t in entry.tags if t not in rm]

    try:
        _get_storage().save(db)
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    print_success(
        f"Tags updated for [cyan]{entry.short_id}[/cyan]: "
        f"{', '.join(entry.tags) or '(none)'}"
    )


# ---------------------------------------------------------------------------
# priority
# ---------------------------------------------------------------------------

@app.command("priority")
def set_priority(
    entry_id: str = typer.Argument(..., help="Entry ID."),
    level: str = typer.Argument(..., help="Priority: High / Medium / Low."),
) -> None:
    """Change the priority of an entry.

    Example:

        braindump priority a1b2c3d4 High
    """
    if level not in ALL_PRIORITIES:
        print_error(
            f"Invalid priority '{level}'. Choices: {', '.join(ALL_PRIORITIES)}"
        )
        raise typer.Exit(code=1)

    try:
        db = _get_storage().load()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    entry = db.get_by_id(entry_id)
    if entry is None:
        print_error(f"No entry found with id '{entry_id}'.")
        raise typer.Exit(code=1)

    entry.priority = level
    try:
        _get_storage().save(db)
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    print_success(
        f"Priority of [cyan]{entry.short_id}[/cyan] set to [bold]{level}[/bold]."
    )


# ---------------------------------------------------------------------------
# reminders (daily)
# ---------------------------------------------------------------------------

@app.command("remind")
def daily_reminders() -> None:
    """Show today's reminders: overdue + entries due today.

    Example:

        braindump remind
    """
    try:
        db = _get_storage().load()
    except StorageError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)

    today = datetime.now().date()
    reminders = [
        e for e in db.entries
        if not e.completed and e.deadline and e.deadline.date() == today
    ]
    overdue = db.get_overdue()

    if not reminders and not overdue:
        print_success("You're all caught up – no reminders for today! 🎉")
        return

    if overdue:
        console.print(render_entries_table(overdue, title="[bold red]⚡ Overdue[/bold red]"))

    if reminders:
        console.print(render_entries_table(reminders, title="[bold yellow]⏰ Due Today[/bold yellow]"))
