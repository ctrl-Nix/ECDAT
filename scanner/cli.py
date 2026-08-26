"""
ECDAT Scanner -- unified CLI.

One command, any mix of supported languages in one target directory.
Dispatches each file to its matching engine by extension and merges
all results into one Finding list, using the shared schema so nothing
downstream needs to know which engine produced which finding.

Usage:
    python -m scanner.cli <file_or_directory> [--json-out findings.json]
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path

from scanner import python_engine
from scanner import multilang_engine
from scanner.constants import SKIP_DIRS, _should_skip

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = Path(__file__).resolve().parent / "rules"


def scan(target: Path) -> list:
    rules = multilang_engine.load_rules(RULES_DIR)
    findings = []

    if target.is_dir():
        findings.extend(python_engine.scan_directory(target))
        findings.extend(multilang_engine.scan_directory(target, rules))
    elif target.suffix == ".py":
        findings.extend(python_engine.scan_file(target))
    elif target.suffix in multilang_engine.EXT_TO_LANG:
        findings.extend(multilang_engine.scan_file(target, rules))
    else:
        print(f"[warn] no engine registered for {target.suffix or '(no extension)'}", file=sys.stderr)

    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scanner.cli <file_or_directory> [--json-out findings.json]")
        sys.exit(1)

    target = Path(sys.argv[1])
    findings = scan(target)
    output = [asdict(f) for f in findings]

    if "--json-out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--json-out") + 1]
        Path(out_path).write_text(json.dumps(output, indent=2))
        print(f"Wrote {len(output)} findings to {out_path}")
    else:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()