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


def _should_skip(path: Path, scan_root: Path | None = None) -> bool:
    """Check whether a path lies below a generated or dependency directory.

    The caller-selected root is not itself an artifact. This distinction keeps
    normal Docker mounts such as ``/target`` scanable while still excluding a
    nested ``target/`` build directory in a Java repository.
    """
    try:
        parts = path.resolve().relative_to(scan_root.resolve()).parts if scan_root else path.parts
    except (ValueError, OSError):
        parts = path.parts
    for part in parts:
        if part in SKIP_DIRS:
            return True
    return False
