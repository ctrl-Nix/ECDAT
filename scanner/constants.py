"""
ECDAT Scanner -- shared constants and utilities.
"""

from pathlib import Path

from scanner.confidence import BAND_THRESHOLDS, CONFIDENCE_BANDS

# Maximum bytes a single artefact (manifest, binary, config file) may be
# before the engine skips it with a warning.  Shared across all engines (C-12).
SCAN_MAX_ARTIFACT_BYTES: int = 10 * 1024 * 1024  # 10 MB

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

# File patterns recognised by the config/IaC engine (IAC, C-12).
# These are glob-style suffix or exact-name patterns used by _is_config_file()
# in scanner/config_engine.py.  Do NOT modify SKIP_DIRS to accommodate them.
CONFIG_FILE_PATTERNS: tuple[str, ...] = (
    "*.yaml",
    "*.yml",
    "*.tf",
    "nginx.conf",
    "*.conf",
    "*.json",
    ".gitlab-ci.yml",
    ".gitlab-ci.yaml",
)


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

