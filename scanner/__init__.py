from scanner.cli import main as scan_cli
from scanner.finding import Finding
from scanner.python_engine import scan_file as scan_python

try:
    from scanner.multilang_engine import scan_file as scan_multilang
except Exception:  # pragma: no cover - dependency may be absent during basic import checks
    def scan_multilang(*args, **kwargs):
        raise RuntimeError("multilang scanner unavailable; install tree-sitter dependencies")

__all__ = ["scan_cli", "Finding", "scan_python", "scan_multilang"]
