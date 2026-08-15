"""
main.py
=======
Entry point for the BrainDump CLI application.

This module is referenced by pyproject.toml's [project.scripts] table:

    braindump = "app.main:main"

Running directly:

    python -m app.main --help
"""

import sys


def main() -> None:
    """Launch the Typer CLI application."""
    # Import here to keep startup fast and to allow the test suite to
    # patch the storage layer before the CLI is imported.
    from app.cli import app  # noqa: PLC0415

    app()


if __name__ == "__main__":
    main()
