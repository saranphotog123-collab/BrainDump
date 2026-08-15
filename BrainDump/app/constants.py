"""
constants.py
============
Application-wide constants: categories, keyword mappings, config defaults,
date/time formatting strings, and export settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = ROOT_DIR / "data"
DB_FILE: Path = DATA_DIR / "braindump.json"
BACKUP_DIR: Path = DATA_DIR / "backups"
LOG_FILE: Path = ROOT_DIR / "braindump.log"

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
class Category:
    WORK = "Work"
    STUDY = "Study"
    PERSONAL = "Personal"
    SHOPPING = "Shopping"
    HEALTH = "Health"
    FINANCE = "Finance"
    CODING = "Coding"
    GENERAL = "General"

ALL_CATEGORIES: List[str] = [
    Category.WORK,
    Category.STUDY,
    Category.PERSONAL,
    Category.SHOPPING,
    Category.HEALTH,
    Category.FINANCE,
    Category.CODING,
    Category.GENERAL,
]

# ---------------------------------------------------------------------------
# Keyword → Category mapping  (order matters: more specific → less specific)
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    Category.CODING: [
        "bug", "fix", "debug", "code", "coding", "program", "programming",
        "deploy", "deployment", "api", "endpoint", "function", "class",
        "module", "library", "framework", "git", "commit", "push", "pull",
        "branch", "merge", "refactor", "test", "testing", "ci", "cd",
        "pipeline", "docker", "kubernetes", "database", "schema", "migration",
        "script", "algorithm", "data structure", "lint", "review", "pr",
        "pull request", "issue", "ticket", "jira", "github", "gitlab",
        "repository", "repo", "server", "backend", "frontend", "fullstack",
        "react", "vue", "angular", "django", "flask", "fastapi", "python",
        "javascript", "typescript", "node", "rust", "java", "kotlin", "swift",
    ],
    Category.STUDY: [
        "study", "learn", "learning", "read", "reading", "assignment",
        "homework", "exam", "test", "quiz", "lecture", "class", "course",
        "tutorial", "practice", "revision", "revise", "notes", "note",
        "chapter", "textbook", "textbook", "research", "thesis", "dissertation",
        "project", "presentation", "submit", "submission", "university",
        "college", "school", "professor", "teacher", "grade", "gpa",
        "certificate", "certification", "skill", "workshop", "seminar",
        "webinar", "mooc", "coursera", "udemy", "edx",
    ],
    Category.WORK: [
        "meeting", "meet", "call", "standup", "sprint", "deadline",
        "report", "presentation", "client", "colleague", "manager", "boss",
        "hr", "salary", "promotion", "interview", "onboarding", "offboarding",
        "task", "project", "milestone", "kpi", "okr", "email", "slack",
        "teams", "zoom", "office", "wfh", "remote", "work", "job",
        "career", "resume", "cv", "hire", "hiring", "performance", "review",
        "feedback", "proposal", "contract", "invoice", "billing",
    ],
    Category.SHOPPING: [
        "buy", "purchase", "order", "shop", "shopping", "grocery",
        "groceries", "store", "mall", "amazon", "online", "cart",
        "checkout", "delivery", "milk", "bread", "eggs", "vegetables",
        "fruits", "meat", "fish", "snacks", "clothes", "shoes", "gadget",
        "electronics", "furniture", "appliance", "gift", "present",
    ],
    Category.HEALTH: [
        "doctor", "hospital", "clinic", "medicine", "medication", "pill",
        "prescription", "appointment", "checkup", "dental", "dentist",
        "gym", "workout", "exercise", "run", "running", "jog", "yoga",
        "meditation", "sleep", "diet", "nutrition", "calories", "weight",
        "blood", "pressure", "sugar", "insulin", "therapy", "mental health",
        "anxiety", "stress", "health", "wellness", "vitamins", "supplement",
        "vaccine", "vaccination",
    ],
    Category.FINANCE: [
        "pay", "payment", "bill", "bills", "rent", "mortgage", "loan",
        "emi", "credit", "debit", "bank", "account", "transaction",
        "budget", "expense", "income", "salary", "invest", "investment",
        "stock", "mutual fund", "tax", "insurance", "premium", "policy",
        "finance", "financial", "saving", "savings", "withdraw", "deposit",
        "transfer", "upi", "wallet", "cash",
    ],
    Category.PERSONAL: [
        "birthday", "anniversary", "wedding", "party", "celebration",
        "family", "friend", "mom", "dad", "sister", "brother", "home",
        "house", "trip", "travel", "vacation", "holiday", "plan",
        "personal", "self", "hobby", "cook", "cooking", "watch",
        "movie", "series", "music", "game", "gaming", "read",
    ],
}

# ---------------------------------------------------------------------------
# Priorities
# ---------------------------------------------------------------------------
class Priority:
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

ALL_PRIORITIES: List[str] = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]

# ---------------------------------------------------------------------------
# Date / time
# ---------------------------------------------------------------------------
DATETIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S"
DISPLAY_DATE_FORMAT: str = "%d %b %Y %I:%M %p"
BACKUP_TIMESTAMP_FORMAT: str = "%Y%m%d_%H%M%S"

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
EXPORT_FORMATS: List[str] = ["json", "csv", "markdown"]

# ---------------------------------------------------------------------------
# UI / Rich table
# ---------------------------------------------------------------------------
TABLE_TITLE: str = "[bold cyan]BrainDump Entries[/bold cyan]"
STATS_TITLE: str = "[bold cyan]BrainDump Statistics[/bold cyan]"

# Category → colour mapping for Rich output
CATEGORY_COLORS: Dict[str, str] = {
    Category.WORK: "blue",
    Category.STUDY: "green",
    Category.PERSONAL: "magenta",
    Category.SHOPPING: "yellow",
    Category.HEALTH: "red",
    Category.FINANCE: "cyan",
    Category.CODING: "bright_blue",
    Category.GENERAL: "white",
}

# Priority → colour mapping
PRIORITY_COLORS: Dict[str, str] = {
    Priority.HIGH: "red",
    Priority.MEDIUM: "yellow",
    Priority.LOW: "green",
}

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
APP_NAME: str = "BrainDump"
APP_VERSION: str = "1.0.0"
MAX_UNDO_HISTORY: int = 10          # max entries kept in undo stack
FUZZY_SEARCH_THRESHOLD: int = 70    # minimum ratio for fuzzy match (0-100)
