from scanner.finding import Finding
from scanner.python_engine import scan_file as scan_python


def scan_cli(*args, **kwargs):
    """Run the CLI lazily so ``python -m scanner.cli`` has no re-import warning."""
    from scanner.cli import main

    return main(*args, **kwargs)

try:
    from scanner.multilang_engine import scan_file as scan_multilang
except Exception:  # pragma: no cover - dependency may be absent during basic import checks
    def scan_multilang(*args, **kwargs):
        raise RuntimeError("multilang scanner unavailable; install tree-sitter dependencies")

__all__ = ["scan_cli", "Finding", "scan_python", "scan_multilang"]
