"""
parser.py
=========
Natural-language date/time extraction and keyword-based category detection.

Public API
----------
parse_deadline(text)  -> Optional[datetime]
detect_category(text) -> str
parse_entry(text)     -> tuple[Optional[datetime], str]
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import dateparser

from app.constants import (
    CATEGORY_KEYWORDS,
    Category,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# dateparser settings
# ---------------------------------------------------------------------------
_DATEPARSER_SETTINGS: dict = {
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": False,
    "PREFER_DAY_OF_MONTH": "first",
    "DATE_ORDER": "DMY",
}

# ---------------------------------------------------------------------------
# Day-of-week helper
# ---------------------------------------------------------------------------
_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _next_weekday(weekday: int) -> datetime:
    """Return the next occurrence of *weekday* (0=Mon … 6=Sun), always future."""
    today = datetime.now()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _this_weekend() -> datetime:
    """Return the coming Saturday."""
    return _next_weekday(5)


# ---------------------------------------------------------------------------
# Custom phrase handlers  (run before dateparser, most specific first)
# ---------------------------------------------------------------------------

def _try_custom_parse(text: str) -> Optional[datetime]:
    """
    Handle phrases that dateparser struggles with on some versions:
    tonight, next <day>, this weekend, this <day>, in X days/weeks, etc.
    Returns a datetime or None.
    """
    lower = text.strip().lower()

    # "tonight"
    if re.fullmatch(r"tonight", lower):
        return datetime.now().replace(hour=21, minute=0, second=0, microsecond=0)

    # "today"
    if re.fullmatch(r"today", lower):
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # "tomorrow"
    if re.fullmatch(r"tomorrow", lower):
        return (datetime.now() + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    # "next <weekday>"
    m = re.fullmatch(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", lower)
    if m:
        return _next_weekday(_WEEKDAYS[m.group(1)])

    # "this <weekday>"
    m = re.fullmatch(r"this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", lower)
    if m:
        return _next_weekday(_WEEKDAYS[m.group(1)])

    # "this weekend"
    if re.fullmatch(r"this\s+weekend", lower):
        return _this_weekend()

    # standalone weekday e.g. "friday", "on friday", "by friday"
    m = re.fullmatch(r"(?:on\s+|by\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", lower)
    if m:
        return _next_weekday(_WEEKDAYS[m.group(1)])

    # "in N days/weeks/hours"
    m = re.fullmatch(r"in\s+(\d+)\s+(day|days|week|weeks|hour|hours|minute|minutes)", lower)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if "week" in unit:
            return datetime.now() + timedelta(weeks=n)
        if "hour" in unit:
            return datetime.now() + timedelta(hours=n)
        if "minute" in unit:
            return datetime.now() + timedelta(minutes=n)
        return datetime.now() + timedelta(days=n)

    # "in two/three/… weeks/days"
    _word_nums = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "a": 1, "an": 1,
    }
    m = re.fullmatch(
        r"in\s+(one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+(day|days|week|weeks|hour|hours)",
        lower,
    )
    if m:
        n = _word_nums.get(m.group(1), 1)
        unit = m.group(2)
        if "week" in unit:
            return datetime.now() + timedelta(weeks=n)
        if "hour" in unit:
            return datetime.now() + timedelta(hours=n)
        return datetime.now() + timedelta(days=n)

    return None


# ---------------------------------------------------------------------------
# Regex patterns for phrase extraction (longest/most specific first)
# ---------------------------------------------------------------------------
_DATE_PATTERNS: list[str] = [
    # --- Compound patterns: absolute date + time ---
    # "on 25 August at 5 PM"
    r"\bon\s+\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    # "25 August at 5 PM"
    r"\b\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    # "August 25 at 5 PM"
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    # "tomorrow at 5 PM" / "today at 9:30 AM" / "tonight at 8 PM"
    r"\b(?:tomorrow|today|tonight)\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    # "at 9 AM on Monday" / "at 5 PM tomorrow"
    r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\s+(?:on\s+)?(?:tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    # --- Relative compound ---
    # "next Monday", "this weekend", "this Friday"
    r"\b(?:next|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend|week|month)\b",
    # "in 3 days", "in two weeks"
    r"\bin\s+\d+\s+(?:day|days|week|weeks|hour|hours|minute|minutes)\b",
    r"\bin\s+(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:day|days|week|weeks|hour|hours|minute|minutes)\b",
    r"\bafter\s+(?:two|three|a\s+couple\s+of|a\s+few)\s+(?:day|days|week|weeks)\b",
    # --- Absolute dates (no explicit time) ---
    # "25 August 2026" / "25 August"
    r"\b\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b(?:\s+\d{4})?",
    # "August 25 2026" / "August 25"
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}\b(?:\s+\d{4})?",
    # standalone day names
    r"\b(?:on\s+|by\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    # "tomorrow", "today", "tonight"
    r"\b(?:tomorrow|today|tonight)\b",
    # "by EOD", "by end of day/week/month"
    r"\bby\s+(?:eod|end\s+of\s+(?:day|week|month))\b",
    # DD/MM/YYYY or MM/DD/YYYY
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    # standalone time: "at 5 PM", "at 17:00"
    r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    r"\bat\s+\d{2}:\d{2}\b",
]

_COMPILED_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _DATE_PATTERNS
]


def _extract_date_phrase(text: str) -> Optional[str]:
    """Return the first recognisable date/time phrase found in *text*."""
    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            phrase = match.group(0).strip()
            logger.debug("Date phrase extracted: %r from %r", phrase, text)
            return phrase
    return None


def parse_deadline(text: str) -> Optional[datetime]:
    """
    Parse a natural-language date/time out of *text*.

    Strategy
    --------
    1. Fast-path: ISO date YYYY-MM-DD parsed directly (avoids DATE_ORDER issues).
    2. Extract the most-specific date phrase with regexes.
    3. Try custom handlers for relative terms dateparser misses.
    4. Pass extracted phrase to dateparser.
    5. Fall back: pass the whole text to dateparser.
    6. Return ``None`` if nothing is found.
    """
    if not text or not text.strip():
        return None

    # 0. ISO date fast-path (YYYY-MM-DD avoids DMY/MDY ambiguity)
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})(?:[T\s](\d{2}:\d{2}))?\b", text)
    if iso_match:
        try:
            date_str = iso_match.group(1)
            time_str = iso_match.group(2)
            if time_str:
                return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass

    phrase = _extract_date_phrase(text)

    # 1. Try custom relative/keyword handlers first (more reliable than dateparser
    #    for "tonight", "next Monday", "this weekend", etc.)
    if phrase:
        custom = _try_custom_parse(phrase)
        if custom:
            return custom

    # 2. Try dateparser on the extracted phrase
    if phrase:
        parsed = dateparser.parse(phrase, settings=_DATEPARSER_SETTINGS)
        if parsed:
            logger.debug("dateparser('%s') -> %s", phrase, parsed)
            return parsed

    # 3. Fall back: dateparser on the full text
    parsed = dateparser.parse(text, settings=_DATEPARSER_SETTINGS)
    if parsed:
        delta_years = (parsed - datetime.now()).days / 365
        if delta_years > 10:
            logger.debug("Rejected far-future date: %s", parsed)
            return None
        logger.debug("Full-text dateparser('%s') -> %s", text, parsed)
        return parsed

    return None


def detect_category(text: str) -> str:
    """
    Classify *text* into a category using keyword matching.

    The category with the most keyword hits wins.  Multi-word keyword matches
    score 2; single-word matches score 1.  Ties are broken by definition order.
    """
    lower = text.lower()
    scores: dict[str, int] = {cat: 0 for cat in CATEGORY_KEYWORDS}

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if " " in kw:
                if kw in lower:
                    scores[category] += 2
            else:
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, lower):
                    scores[category] += 1

    best_cat = max(scores, key=lambda c: scores[c])
    if scores[best_cat] == 0:
        return Category.GENERAL

    logger.debug("Category scores for %r: %s -> %s", text, scores, best_cat)
    return best_cat


def parse_entry(text: str) -> tuple[Optional[datetime], str]:
    """
    Parse both deadline and category from *text*.

    Returns
    -------
    ``(deadline, category)`` tuple.
    """
    deadline = parse_deadline(text)
    category = detect_category(text)
    return deadline, category
