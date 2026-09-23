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

try:
    from scanner.dependency_engine import scan_directory as _scan_dep_dir, scan_file as _scan_dep_file
    def scan_dependency(target, rules=None):
        if getattr(target, "is_dir", lambda: False)():
            return _scan_dep_dir(target, rules)
        return _scan_dep_file(target, rules)
except Exception:
    def scan_dependency(*args, **kwargs):
        raise RuntimeError("dependency scanner unavailable; engine failed to import")

try:
    from scanner.config_engine import scan_directory as _scan_cfg_dir, scan_file as _scan_cfg_file
    def scan_config(target, rules=None):
        if getattr(target, "is_dir", lambda: False)():
            return _scan_cfg_dir(target, rules)
        return _scan_cfg_file(target, rules)
except Exception:
    def scan_config(*args, **kwargs):
        raise RuntimeError("config scanner unavailable; engine failed to import")

try:
    from scanner.binary_engine import scan_file as scan_binary
except Exception:  # pragma: no cover - dependency may be absent
    def scan_binary(*args, **kwargs):
        raise RuntimeError("binary scanner unavailable; install lief")

__all__ = ["scan_cli", "Finding", "scan_python", "scan_multilang", "scan_dependency", "scan_config", "scan_binary"]
