"""
utils.py
========
Shared display helpers built on top of Rich.

Nothing in here does I/O or business logic – only rendering.

Public API
----------
console                          - shared Rich Console instance
print_success / print_error / print_warning / print_info
render_entries_table(entries)    -> Table
render_stats(db)                 -> Group
render_entry_detail(entry)       -> Panel
format_deadline(dt)              -> str
format_status(entry)             -> str
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text
from rich import box

from app.constants import (
    CATEGORY_COLORS,
    DISPLAY_DATE_FORMAT,
    PRIORITY_COLORS,
    TABLE_TITLE,
    STATS_TITLE,
    APP_NAME,
    APP_VERSION,
)
from app.models import BrainDumpDB, BrainEntry

# ---------------------------------------------------------------------------
# Shared console
# ---------------------------------------------------------------------------
console = Console()


# ---------------------------------------------------------------------------
# Colour-safe print helpers
# ---------------------------------------------------------------------------

def print_success(message: str) -> None:
    """Print a green success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_error(message: str) -> None:
    """Print a red error message."""
    console.print(f"[bold red]✗[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a yellow warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow]  {message}")


def print_info(message: str) -> None:
    """Print a cyan informational message."""
    console.print(f"[bold cyan]ℹ[/bold cyan]  {message}")


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def format_deadline(dt: Optional[datetime]) -> str:
    """Return a human-readable deadline string, or em-dash if None."""
    if dt is None:
        return "—"
    return dt.strftime(DISPLAY_DATE_FORMAT)


def format_status(entry: BrainEntry) -> Text:
    """Return a Rich Text object representing the completion/overdue status."""
    if entry.completed:
        return Text("✓ Done", style="bold green")
    if entry.is_overdue:
        return Text("⚡ Overdue", style="bold red")
    return Text("○ Pending", style="dim white")


def _category_badge(category: str) -> Text:
    colour = CATEGORY_COLORS.get(category, "white")
    return Text(category, style=f"bold {colour}")


def _priority_badge(priority: str) -> Text:
    colour = PRIORITY_COLORS.get(priority, "white")
    return Text(priority, style=f"bold {colour}")


# ---------------------------------------------------------------------------
# Rich Tables
# ---------------------------------------------------------------------------

def render_entries_table(entries: list[BrainEntry], title: str = TABLE_TITLE) -> Table:
    """
    Build a Rich Table for a list of BrainEntry objects.

    Parameters
    ----------
    entries:
        List of entries to display (already sorted if desired).
    title:
        Optional table title markup string.

    Returns
    -------
    A ``rich.table.Table`` ready to be printed.
    """
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
        header_style="bold magenta",
        width=160,
    )

    table.add_column("ID", style="dim", width=10, no_wrap=True)
    table.add_column("Thought", min_width=30, max_width=60)
    table.add_column("Category", width=12)
    table.add_column("Priority", width=10)
    table.add_column("Deadline", width=22)
    table.add_column("Tags", width=18)
    table.add_column("Status", width=12)

    for entry in entries:
        deadline_text = format_deadline(entry.deadline)
        if entry.is_overdue:
            deadline_text = f"[bold red]{deadline_text}[/bold red]"
        elif entry.deadline and entry.deadline > datetime.now():
            deadline_text = f"[green]{deadline_text}[/green]"

        tags_str = ", ".join(entry.tags) if entry.tags else "—"

        table.add_row(
            entry.short_id,
            entry.text,
            _category_badge(entry.category),
            _priority_badge(entry.priority),
            deadline_text,
            tags_str,
            format_status(entry),
        )

    return table


def render_entry_detail(entry: BrainEntry) -> Panel:
    """Render a single entry as a detailed Rich Panel."""
    lines = [
        f"[bold]ID:[/bold]          {entry.id}",
        f"[bold]Text:[/bold]        {entry.text}",
        f"[bold]Category:[/bold]    {entry.category}",
        f"[bold]Priority:[/bold]    {entry.priority}",
        f"[bold]Tags:[/bold]        {', '.join(entry.tags) or '—'}",
        f"[bold]Deadline:[/bold]    {format_deadline(entry.deadline)}",
        f"[bold]Created:[/bold]     {entry.created_at.strftime(DISPLAY_DATE_FORMAT)}",
        f"[bold]Status:[/bold]      {'✓ Completed' if entry.completed else ('⚡ Overdue' if entry.is_overdue else '○ Pending')}",
    ]
    if entry.completed and entry.completed_at:
        lines.append(
            f"[bold]Completed at:[/bold] {entry.completed_at.strftime(DISPLAY_DATE_FORMAT)}"
        )
    content = "\n".join(lines)
    return Panel(
        content,
        title=f"[bold cyan]Entry Detail[/bold cyan]",
        border_style="cyan",
        expand=False,
    )


def render_stats(db: BrainDumpDB) -> None:
    """Print a statistics panel directly to the console."""
    total = len(db.entries)
    completed = len(db.get_completed())
    pending = len(db.get_pending())
    overdue = len(db.get_overdue())

    # --- Summary table ---
    summary = Table(
        title=STATS_TITLE,
        box=box.SIMPLE_HEAD,
        header_style="bold magenta",
        show_header=True,
    )
    summary.add_column("Metric", style="bold")
    summary.add_column("Count", justify="right")

    summary.add_row("Total entries", str(total))
    summary.add_row("[green]Completed[/green]", f"[green]{completed}[/green]")
    summary.add_row("[yellow]Pending[/yellow]", f"[yellow]{pending}[/yellow]")
    summary.add_row("[red]Overdue[/red]", f"[red]{overdue}[/red]")

    console.print(summary)

    # --- Category breakdown ---
    if total > 0:
        cat_table = Table(
            title="[bold cyan]Notes by Category[/bold cyan]",
            box=box.SIMPLE_HEAD,
            header_style="bold magenta",
        )
        cat_table.add_column("Category", style="bold")
        cat_table.add_column("Count", justify="right")
        cat_table.add_column("Progress", min_width=20)

        from app.constants import ALL_CATEGORIES, CATEGORY_COLORS
        for cat in ALL_CATEGORIES:
            count = len(db.get_by_category(cat))
            if count == 0:
                continue
            bar_len = int((count / total) * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            colour = CATEGORY_COLORS.get(cat, "white")
            cat_table.add_row(
                Text(cat, style=f"bold {colour}"),
                str(count),
                f"[{colour}]{bar}[/{colour}]",
            )
        console.print(cat_table)

    # --- Completion progress bar ---
    if total > 0:
        pct = int((completed / total) * 100)
        bar_len = int((completed / total) * 40)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        colour = "green" if pct >= 75 else ("yellow" if pct >= 40 else "red")
        console.print(
            f"\n[bold]Completion rate:[/bold] [{colour}]{bar}[/{colour}] [bold]{pct}%[/bold]"
        )


def print_app_banner() -> None:
    """Print the BrainDump ASCII banner."""
    banner = f"""[bold cyan]
  ██████╗ ██████╗  █████╗ ██╗███╗   ██╗██████╗ ██╗   ██╗███╗   ███╗██████╗ 
  ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔══██╗██║   ██║████╗ ████║██╔══██╗
  ██████╔╝██████╔╝███████║██║██╔██╗ ██║██║  ██║██║   ██║██╔████╔██║██████╔╝
  ██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║██║  ██║██║   ██║██║╚██╔╝██║██╔═══╝ 
  ██████╔╝██║  ██║██║  ██║██║██║ ╚████║██████╔╝╚██████╔╝██║ ╚═╝ ██║██║     
  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝     
[/bold cyan]
  [dim]v{APP_VERSION} — Capture your thoughts, never miss a deadline.[/dim]
"""
    console.print(banner)
