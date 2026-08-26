"""
ECDAT Scanner -- shared constants and utilities.
"""

from pathlib import Path

# Directories to skip during scanning
SKIP_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
    "coverage",
    ".nyc_output",
}


def _should_skip(path: Path) -> bool:
    """Check if path should be skipped during scanning."""
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False