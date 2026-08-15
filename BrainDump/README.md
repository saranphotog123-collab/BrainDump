# 🧠 BrainDump

> **Capture your thoughts, reminders & tasks — from the terminal or a full desktop GUI.**

BrainDump is a production-ready CLI **and** PySide6 desktop application that lets you save thoughts instantly, auto-detects deadlines from natural language, and classifies notes into categories — all stored locally in a simple JSON file.

```
# CLI
braindump add "Fix the login bug by Friday"
braindump list

# Desktop GUI
python -m gui.app
```

---

## Table of Contents

1. [Features](#features)
2. [Desktop GUI](#desktop-gui)
3. [Project Architecture](#project-architecture)
4. [Installation](#installation)ct-architecture)
3. [Installation](#installation)
4. [Virtual Environment Setup](#virtual-environment-setup)
5. [CLI Usage](#cli-usage)
6. [Examples](#examples)
7. [Testing](#testing)
8. [Project Structure](#project-structure)
9. [Configuration](#configuration)
10. [Future Improvements](#future-improvements)
11. [License](#license)

---

## Features

| Feature | Description |
|---|---|
| **Add thoughts** | Save any thought, reminder, or task instantly |
| **Natural language dates** | Parses "tomorrow", "next Monday", "25 August at 5 PM", "in 3 days" |
| **Auto-categorisation** | Keyword-based classification into 8 categories |
| **Priority levels** | High / Medium / Low with colour-coded display |
| **Rich tables** | Beautiful terminal output powered by Rich |
| **Search** | Exact and fuzzy search across text, category, and tags |
| **Complete / Delete** | Mark done or remove entries |
| **Undo delete** | Restore the last deleted entry |
| **Statistics** | Totals, completion rate, breakdown by category |
| **Export** | JSON, CSV, and Markdown export |
| **Backup** | Timestamped backup of the database |
| **Tags** | Add/remove custom tags per entry |
| **Daily reminders** | Surface overdue + due-today items |
| **Desktop GUI** | Full PySide6 dark-theme desktop application |

---

## Desktop GUI

BrainDump ships a full PySide6 desktop application that exposes every CLI feature through a polished dark-theme interface.

### Launching

```bash
# Activate your virtual environment first
.venv\Scripts\Activate.ps1        # Windows PowerShell
source .venv/bin/activate          # macOS / Linux

# Launch the GUI
python -m gui.app
```

### GUI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Menu Bar  │  File  │  Edit  │  View                                │
├─────────────────────────────────────────────────────────────────────┤
│  Toolbar   │ ＋ New │ ✓ Complete │ ✎ Edit │ ✕ Delete │ ↩ Undo …   │
├──────────────┬──────────────────────────────────────────────────────┤
│              │  🔍 Search bar                      N entries        │
│  Sidebar     ├──────────────────────────────────────────────────────┤
│              │                                                      │
│  STATUS      │  ID       Thought       Category  Priority  Deadline │
│  ○ All       │  ──────────────────────────────────────────────────  │
│  ○ Pending   │  11111111 Buy milk…     Shopping   Medium    16 Aug  │
│  ✓ Completed │  22222222 Fix login…    Coding     High      21 Aug  │
│  ⚡ Overdue  │  33333333 Submit assi…  Study      High      25 Aug  │
│              │  …                                                   │
│  CATEGORY    │                                                      │
│  ● Work      │                                                      │
│  ● Study     │                                                      │
│  ● Coding    │                                                      │
│  …           │                                                      │
│              │                                                      │
│  PRIORITY    │                                                      │
│  ● High      │                                                      │
│  ● Medium    │                                                      │
│  ● Low       │                                                      │
├──────────────┴──────────────────────────────────────────────────────┤
│  Status bar — Ready                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### GUI Features

| Feature | How to use |
|---|---|
| **Add entry** | Toolbar `＋ New` or `Ctrl+N` — dialog with live deadline/category preview |
| **Edit entry** | Select row → `✎ Edit` or `F2` |
| **Complete entry** | Select row → `✓ Complete` or `Space` — also toggle checkbox in status column |
| **Delete entry** | Select row → `✕ Delete` or `Del` — confirmation prompt |
| **Undo delete** | `↩ Undo` or `Ctrl+Z` — restores last deleted entry |
| **Double-click** | Opens full detail panel for the entry |
| **Filter sidebar** | Click any Status / Category / Priority item to instantly filter the table |
| **Live search** | Type in search bar — searches text, category, tags simultaneously |
| **Fuzzy search** | Toggle the `Fuzzy` button in search bar |
| **Statistics** | `📊 Stats` or `Ctrl+I` — totals, completion rate, category bar charts |
| **Reminders** | `⏰ Remind` or `Ctrl+R` — overdue + due-today popup |
| **Export** | `⬆ Export` or `Ctrl+E` — JSON, CSV, or Markdown with file picker |
| **Backup** | `💾 Backup` or `Ctrl+B` — timestamped copy in `data/backups/` |

### GUI Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New entry |
| `Ctrl+F` | Focus search bar |
| `F2` | Edit selected entry |
| `Space` | Toggle complete on selected entry |
| `Delete` | Delete selected entry |
| `Ctrl+Z` | Undo last delete |
| `Ctrl+I` | Open statistics |
| `Ctrl+R` | Open reminders |
| `Ctrl+E` | Export dialog |
| `Ctrl+B` | Create backup |
| `F5` | Refresh from disk |
| `Ctrl+Q` | Quit |

### GUI File Structure

```
gui/
├── __init__.py       — package marker
├── app.py            — QApplication entry point, palette, stylesheet
├── styles.py         — dark-theme QSS + colour constants (Colors, CATEGORY_COLORS…)
├── models.py         — EntryTableModel (QAbstractTableModel) + EntryFilterProxyModel
├── widgets.py        — SearchBar, FilterSidebar, BadgeDelegate, StatusDelegate
├── dialogs.py        — AddEntryDialog, EntryDetailDialog, StatsDialog, ExportDialog, ConfirmDialog
└── main_window.py    — MainWindow (wires everything together)
```

---

## Project Architecture

BrainDump follows a **clean, layered architecture**:

```
┌─────────────────────────────────────────┐
│              CLI Layer                  │  ← app/cli.py   (Typer commands)
├─────────────────────────────────────────┤
│           Business Logic                │  ← app/parser.py (NLP date + category)
├─────────────────────────────────────────┤
│            Data Models                  │  ← app/models.py (Pydantic)
├─────────────────────────────────────────┤
│          Persistence Layer              │  ← app/storage.py (JSON I/O)
├─────────────────────────────────────────┤
│        Display / Utilities              │  ← app/utils.py  (Rich rendering)
└─────────────────────────────────────────┘
```

Each layer has a **single responsibility** and depends only on layers below it. The storage layer is injected into the CLI, making it fully testable with a temporary database.

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Option A – Install as a package (recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/braindump.git
cd braindump

# Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# Install the package in editable mode
pip install -e ".[dev]"
```

After installation the `braindump` command is available globally in the venv.

### Option B – Run directly with Python

```bash
pip install -r requirements.txt
python -m app.main --help
```

---

## Virtual Environment Setup

```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate
#    Windows PowerShell:
.venv\Scripts\Activate.ps1
#    Windows cmd.exe:
.venv\Scripts\activate.bat
#    macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Install in editable mode with dev extras
pip install -e ".[dev]"

# 5. Verify installation
braindump --version
```

---

## CLI Usage

### Global flags

```
braindump --help            Show help and exit
braindump --version         Show version and exit
braindump --verbose <cmd>   Enable debug logging
```

---

### `add` – Add a new thought

```bash
braindump add "<text>"  [OPTIONS]

Options:
  -c, --category TEXT   Override auto-detected category
  -p, --priority TEXT   Priority: High / Medium / Low  [default: Medium]
  -t, --tags TEXT       Comma-separated tags
  -d, --deadline TEXT   Override deadline (natural language or date string)
```

---

### `list` – List all thoughts

```bash
braindump list  [OPTIONS]

Options:
  -c, --category TEXT   Filter by category
  -p, --priority TEXT   Filter by priority
      --pending         Show only pending entries
      --completed       Show only completed entries
      --overdue         Show only overdue entries
      --tag TEXT        Filter by tag
  -n, --limit INT       Limit number of results (0 = all)
```

---

### `search` – Search thoughts

```bash
braindump search "<query>"  [OPTIONS]

Options:
  -f, --fuzzy   Enable fuzzy matching
```

---

### `complete` – Mark as done

```bash
braindump complete <id>
```

---

### `delete` – Remove an entry

```bash
braindump delete <id>  [OPTIONS]

Options:
  -f, --force   Skip confirmation prompt
```

---

### `undo` – Restore last deleted entry

```bash
braindump undo
```

---

### `stats` – Show statistics

```bash
braindump stats
```

---

### `export` – Export data

```bash
braindump export <format>  [OPTIONS]

Formats: json | csv | markdown

Options:
  -o, --output PATH   Output file path
```

---

### `backup` – Create a backup

```bash
braindump backup
```

Saves a timestamped copy to `data/backups/braindump_backup_YYYYMMDD_HHMMSS.json`.

---

### `info` – Show full entry details

```bash
braindump info <id>
```

---

### `tags` – Manage tags

```bash
braindump tags <id>  [OPTIONS]

Options:
  --add TEXT      Comma-separated tags to add
  --remove TEXT   Comma-separated tags to remove
```

---

### `priority` – Change priority

```bash
braindump priority <id> <High|Medium|Low>
```

---

### `remind` – Daily reminders

```bash
braindump remind
```

Shows overdue entries and entries due today.

---

## Examples

```bash
# Add a shopping reminder – auto-detected as Shopping + tomorrow deadline
braindump add "Need to buy milk tomorrow"

# Add a coding task with high priority and tags
braindump add "Fix the login bug by Friday" --priority High --tags "work,urgent"

# Add a study deadline
braindump add "Submit assignment on 25 August at 5 PM"

# List everything, sorted by deadline
braindump list

# List only High priority pending items
braindump list --pending --priority High

# Search for anything related to bugs
braindump search bug

# Mark an entry as complete (use the short ID from the list)
braindump complete a1b2c3d4

# Delete with confirmation prompt
braindump delete a1b2c3d4

# Delete without prompt
braindump delete a1b2c3d4 --force

# Restore the last deleted entry
braindump undo

# View statistics
braindump stats

# Export to CSV
braindump export csv --output my_notes.csv

# Export to Markdown
braindump export markdown --output notes.md

# Create a backup
braindump backup

# See what's due today or overdue
braindump remind

# Add a tag
braindump tags a1b2c3d4 --add urgent

# Change priority
braindump priority a1b2c3d4 High

# Show full details
braindump info a1b2c3d4
```

---

## Categories

BrainDump automatically classifies entries using keyword matching:

| Category | Example triggers |
|---|---|
| **Coding** | bug, fix, deploy, API, refactor, git, script |
| **Study** | assignment, exam, lecture, course, homework |
| **Work** | meeting, client, sprint, standup, report |
| **Shopping** | buy, groceries, order, store, cart |
| **Health** | doctor, gym, medication, workout, dental |
| **Finance** | bill, rent, credit, budget, tax, payment |
| **Personal** | birthday, trip, family, hobby, vacation |
| **General** | *(fallback – no keywords matched)* |

Override at any time with `--category`:
```bash
braindump add "Random idea" --category Personal
```

---

## Natural Language Date Examples

| Input phrase | Parsed result |
|---|---|
| `tomorrow` | Next day at midnight |
| `today` | Today at midnight |
| `tonight` | Today evening |
| `next Monday` | Coming Monday |
| `this weekend` | Nearest Saturday |
| `Friday` | Coming Friday |
| `in 3 days` | 3 days from now |
| `in two weeks` | 14 days from now |
| `25 August` | Aug 25 of the current/next year |
| `August 25` | Aug 25 of the current/next year |
| `5 PM tomorrow` | Tomorrow at 17:00 |
| `Submit on 25 August at 5 PM` | Aug 25 at 17:00 |

---

## Testing

```bash
# Activate the virtual environment first
.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate    # macOS / Linux

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_parser.py
pytest tests/test_storage.py
pytest tests/test_cli.py

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run with HTML coverage report
pytest --cov=app --cov-report=html
# Then open htmlcov/index.html in your browser

# Run only fast tests (exclude slow/integration)
pytest -m "not slow"
```

---

## Project Structure

```
BrainDump/
│
├── app/                        # Main application package (CLI + business logic)
│   ├── __init__.py             # Package metadata (version, author)
│   ├── main.py                 # CLI entry point – launches Typer app
│   ├── cli.py                  # All Typer CLI command definitions
│   ├── parser.py               # NLP date extraction + category detection
│   ├── storage.py              # JSON persistence layer (StorageManager)
│   ├── models.py               # Pydantic data models (BrainEntry, BrainDumpDB)
│   ├── utils.py                # Rich display helpers (tables, panels, stats)
│   └── constants.py            # App-wide constants (categories, keywords, paths)
│
├── gui/                        # PySide6 desktop application
│   ├── __init__.py
│   ├── app.py                  # QApplication entry point, palette, QSS
│   ├── styles.py               # Dark-theme QSS stylesheet + colour constants
│   ├── models.py               # EntryTableModel + EntryFilterProxyModel
│   ├── widgets.py              # SearchBar, FilterSidebar, custom delegates
│   ├── dialogs.py              # AddEntry, Detail, Stats, Export, Confirm dialogs
│   └── main_window.py          # MainWindow — wires all components together
│
├── data/
│   ├── braindump.json          # Live database (auto-created on first run)
│   └── backups/                # Timestamped backups (created by `braindump backup`)
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py          # 40+ unit tests for date parsing & categorisation
│   ├── test_storage.py         # 50+ unit tests for storage CRUD, export, backup
│   └── test_cli.py             # 60+ integration tests via Typer CliRunner
│
├── requirements.txt            # Pinned runtime + dev dependencies
├── pyproject.toml              # Build config, pytest, coverage, ruff, mypy settings
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

### Key design decisions

- **Atomic writes** – all database saves write to a `.tmp` file first then rename, preventing corruption on crash.
- **Dependency injection** – `StorageManager` is injected into the CLI via `set_storage()`, enabling full test isolation without mocking.
- **Pydantic v2** – uses `field_validator` (v2 API) for clean validation with descriptive error messages.
- **dateparser + regex** – regexes extract precise date phrases before passing to dateparser, improving accuracy and avoiding false positives.
- **Undo stack** – deleted entries are kept in a capped LIFO stack inside the DB, persisted across sessions.

---

## Configuration

BrainDump stores its data in `data/braindump.json` relative to the project root. You can change this by editing `app/constants.py`:

```python
DB_FILE: Path = DATA_DIR / "braindump.json"
```

Or pass a custom path to `StorageManager` programmatically:

```python
from app.storage import StorageManager
sm = StorageManager(db_path=Path("/custom/path/db.json"))
```

---

## Future Improvements

- [ ] **Config file** – `~/.braindump/config.toml` for user preferences (default priority, date format, etc.)
- [ ] **Recurring tasks** – RRULE-based recurrence ("every Monday")
- [ ] **Notifications** – OS-level desktop notifications via `plyer`
- [ ] **Sync** – Optional cloud sync (S3, Dropbox, GitHub Gist)
- [ ] **Interactive TUI** – Full terminal UI with `textual`
- [ ] **Natural language priority** – Detect "urgent", "critical" from text
- [ ] **Sub-tasks** – Nested task support with parent/child relationships
- [ ] **Time tracking** – Log time spent on tasks
- [ ] **Web dashboard** – Read-only browser view of the JSON database
- [ ] **Import** – Import from Todoist, Notion, Apple Reminders CSV export
- [ ] **Shell auto-completion** – Already supported by Typer; document setup per shell

---

## License

MIT License – see [LICENSE](LICENSE) for details.

---

*Built with [Typer](https://typer.tiangolo.com/), [Rich](https://rich.readthedocs.io/), [Pydantic](https://docs.pydantic.dev/), and [dateparser](https://dateparser.readthedocs.io/).*
