"""
ECDAT Scanner -- Python engine.

Detects cryptographic usage in Python source via the stdlib ast module
(never regex). Rules are still hardcoded in this file as CALL_RULES --
that is a deliberate, documented scope decision, not an oversight. See
ARCHITECTURE.md, "Known scope gaps" for the reasoning and the plan to
externalize them into rules/python.yaml alongside Java and JavaScript.
"""

import ast
import sys
from pathlib import Path
from typing import Optional

from scanner.finding import Finding


CALL_RULES = {
    "hashlib.md5":    {"algorithm": "MD5",    "primitive": "hash", "library": "hashlib"},
    "hashlib.sha1":   {"algorithm": "SHA-1",  "primitive": "hash", "library": "hashlib"},
    "hashlib.sha256": {"algorithm": "SHA-256", "primitive": "hash", "library": "hashlib"},
    "hashlib.sha384": {"algorithm": "SHA-384", "primitive": "hash", "library": "hashlib"},
    "hashlib.sha512": {"algorithm": "SHA-512", "primitive": "hash", "library": "hashlib"},

    "DES.new":  {"algorithm": "DES", "primitive": "encrypt", "library": "PyCryptodome"},
    "ARC4.new": {"algorithm": "RC4", "primitive": "encrypt", "library": "PyCryptodome"},
    "AES.new":  {"algorithm": "AES", "primitive": "encrypt", "library": "PyCryptodome"},
    "HMAC.new": {"algorithm": "HMAC", "primitive": "mac", "library": "PyCryptodome"},

    "RSA.generate":             {"algorithm": "RSA", "primitive": "asymmetric-keygen", "library": "PyCryptodome"},
    "rsa.generate_private_key": {"algorithm": "RSA", "primitive": "asymmetric-keygen", "library": "cryptography"},

    "ssl.SSLContext":              {"algorithm": "TLS", "primitive": "protocol", "library": "ssl"},
    "ssl.create_default_context": {"algorithm": "TLS", "primitive": "protocol", "library": "ssl"},
    "ssl.wrap_socket":             {"algorithm": "TLS", "primitive": "protocol", "library": "ssl"},
}

METHOD_ONLY_RULES = {
    "load_cert_chain": {"algorithm": "TLS", "primitive": "certificate-load", "library": "ssl"},
}

WEAK_ALGORITHMS = {"MD5", "SHA-1", "DES", "RC4"}


class CryptoVisitor(ast.NodeVisitor):
    """Walks a module's AST and records cryptographic call sites.

    Only ast.Import / ast.ImportFrom / ast.Call nodes are inspected.
    Comments and string/variable names are never consulted -- the AST
    doesn't expose them at this level, which is exactly the point.
    """

    def __init__(self, filename: str, source_lines: list):
        self.filename = filename
        self.source_lines = source_lines
        self.findings = []
        self.aliases = {}  # local name -> real dotted module/name

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self.aliases[local_name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            local_name = alias.asname or alias.name
            self.aliases[local_name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def _resolve_call_name(self, func: ast.expr):
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name):
                base = self.aliases.get(func.value.id, func.value.id)
                base_short = base.split(".")[-1]
                return f"{base_short}.{func.attr}"
            return func.attr
        if isinstance(func, ast.Name):
            return self.aliases.get(func.id, func.id)
        return None

    def _extract_key_size(self, node: ast.Call) -> Optional[int]:
        for kw in node.keywords:
            if kw.arg in ("key_size", "bits") and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, int):
                    return kw.value.value
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                return arg.value
        return None

    def _source_snippet(self, node: ast.Call) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            return self.source_lines[node.lineno - 1].strip()

    def visit_Call(self, node: ast.Call):
        resolved = self._resolve_call_name(node.func)
        rule = None
        matched_key = None

        if resolved in CALL_RULES:
            rule = CALL_RULES[resolved]
            matched_key = resolved
        elif isinstance(node.func, ast.Attribute) and node.func.attr in METHOD_ONLY_RULES:
            rule = METHOD_ONLY_RULES[node.func.attr]
            matched_key = node.func.attr

        if rule:
            key_size = self._extract_key_size(node) if rule["algorithm"] == "RSA" else None
            self.findings.append(Finding(
                file=self.filename,
                line=node.lineno,
                matched_call=self._source_snippet(node),
                library=rule["library"],
                algorithm=rule["algorithm"],
                primitive=rule["primitive"],
                language="python",
                weak_by_default=rule["algorithm"] in WEAK_ALGORITHMS,
                confidence="high",  # Python's alias resolution is import-backed by construction
                key_size=key_size,
                detection_method="ast_static_analysis",
            ))

        self.generic_visit(node)


def scan_file(path: Path) -> list:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"[warn] could not read {path}: {e}", file=sys.stderr)
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        print(f"[warn] could not parse {path}: {e}", file=sys.stderr)
        return []

    visitor = CryptoVisitor(str(path), source.splitlines())
    visitor.visit(tree)
    return visitor.findings


from scanner.constants import SKIP_DIRS, _should_skip


def scan_directory(target: Path) -> list:
    all_findings = []
    for py_file in sorted(target.rglob("*.py")):
        if _should_skip(py_file):
            continue
        all_findings.extend(scan_file(py_file))
    return all_findings