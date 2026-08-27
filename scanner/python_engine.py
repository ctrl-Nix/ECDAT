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

    "MD5.new": {"algorithm": "MD5", "primitive": "hash", "library": "PyCryptodome"},
    "SHA1.new": {"algorithm": "SHA-1", "primitive": "hash", "library": "PyCryptodome"},
    "SHA224.new": {"algorithm": "SHA-224", "primitive": "hash", "library": "PyCryptodome"},
    "SHA256.new": {"algorithm": "SHA-256", "primitive": "hash", "library": "PyCryptodome"},
    "SHA384.new": {"algorithm": "SHA-384", "primitive": "hash", "library": "PyCryptodome"},
    "SHA512.new": {"algorithm": "SHA-512", "primitive": "hash", "library": "PyCryptodome"},

    "DES.new":  {"algorithm": "DES", "primitive": "encrypt", "library": "PyCryptodome"},
    "DES3.new": {"algorithm": "3DES", "primitive": "encrypt", "library": "PyCryptodome"},
    "ARC4.new": {"algorithm": "RC4", "primitive": "encrypt", "library": "PyCryptodome"},
    "AES.new":  {"algorithm": "AES", "primitive": "encrypt", "library": "PyCryptodome"},
    "HMAC.new": {"algorithm": "HMAC", "primitive": "mac", "library": "PyCryptodome"},

    "RSA.generate":             {"algorithm": "RSA", "primitive": "asymmetric-keygen", "library": "PyCryptodome"},
    "rsa.generate_private_key": {"algorithm": "RSA", "primitive": "asymmetric-keygen", "library": "cryptography"},
    "ec.generate_private_key": {"algorithm": "ECC", "primitive": "asymmetric-keygen", "library": "cryptography"},
    "dsa.generate_private_key": {"algorithm": "DSA", "primitive": "asymmetric-keygen", "library": "cryptography"},

    "hashes.MD5": {"algorithm": "MD5", "primitive": "hash", "library": "cryptography"},
    "hashes.SHA1": {"algorithm": "SHA-1", "primitive": "hash", "library": "cryptography"},
    "hashes.SHA256": {"algorithm": "SHA-256", "primitive": "hash", "library": "cryptography"},
    "hashes.SHA384": {"algorithm": "SHA-384", "primitive": "hash", "library": "cryptography"},
    "hashes.SHA512": {"algorithm": "SHA-512", "primitive": "hash", "library": "cryptography"},

    "algorithms.ARC4": {"algorithm": "RC4", "primitive": "encrypt", "library": "cryptography"},
    "algorithms.TripleDES": {"algorithm": "3DES", "primitive": "encrypt", "library": "cryptography"},
    "algorithms.AES": {"algorithm": "AES", "primitive": "encrypt", "library": "cryptography"},

    "ssl.SSLContext":              {"algorithm": "TLS", "primitive": "protocol", "library": "ssl"},
    "ssl.create_default_context": {"algorithm": "TLS", "primitive": "protocol", "library": "ssl"},
    "ssl.wrap_socket":             {"algorithm": "TLS", "primitive": "protocol", "library": "ssl"},
}

WEAK_ALGORITHMS = {"MD5", "SHA-1", "DES", "3DES", "RC4"}
HASHLIB_NEW_ALGORITHMS = {
    "md5": "MD5",
    "sha1": "SHA-1",
    "sha224": "SHA-224",
    "sha256": "SHA-256",
    "sha384": "SHA-384",
    "sha512": "SHA-512",
}


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

    def _resolve_call_candidates(self, func: ast.expr) -> list[str]:
        """Return import-backed names that can identify a called crypto API.

        The scanner deliberately requires an explicit import before emitting a
        finding.  This avoids treating arbitrary application classes named
        ``AES`` or ``MessageDigest`` as cryptographic assets.  Several suffix
        candidates are retained so aliases such as ``from Crypto.Cipher import
        AES`` and ``from cryptography... import hashes`` resolve to the compact
        rule keys used below.
        """
        parts: list[str] = []
        current = func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            imported = self.aliases.get(current.id)
            if not imported:
                return []
            full_name = ".".join([imported, *reversed(parts)]) if parts else imported
        elif not parts and isinstance(func, ast.Name):
            full_name = self.aliases.get(func.id, "")
            if not full_name:
                return []
        else:
            return []

        segments = full_name.split(".")
        candidates = [full_name]
        for width in (3, 2):
            if len(segments) >= width:
                candidates.append(".".join(segments[-width:]))
        return list(dict.fromkeys(candidates))

    @staticmethod
    def _first_string_arg(node: ast.Call) -> Optional[str]:
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
        return None

    @staticmethod
    def _hmac_digest_name(node: ast.Call) -> Optional[str]:
        """Return an explicitly literal digest passed to ``hmac.new``."""
        if len(node.args) >= 3 and isinstance(node.args[2], ast.Constant):
            value = node.args[2].value
            if isinstance(value, str):
                return value
        for keyword in node.keywords:
            if keyword.arg == "digestmod" and isinstance(keyword.value, ast.Constant):
                value = keyword.value.value
                if isinstance(value, str):
                    return value
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
        candidates = self._resolve_call_candidates(node.func)
        rule = None
        if candidates:
            for candidate in candidates:
                if candidate in CALL_RULES:
                    rule = CALL_RULES[candidate]
                    break

            if rule is None and "hashlib.new" in candidates:
                algorithm = HASHLIB_NEW_ALGORITHMS.get((self._first_string_arg(node) or "").lower())
                if algorithm:
                    rule = {"algorithm": algorithm, "primitive": "hash", "library": "hashlib"}
            if rule is None and "hmac.new" in candidates:
                algorithm = HASHLIB_NEW_ALGORITHMS.get((self._hmac_digest_name(node) or "").lower())
                if algorithm:
                    rule = {"algorithm": algorithm, "primitive": "mac", "library": "hmac"}

        if rule:
            key_size = self._extract_key_size(node) if rule["algorithm"] in {"RSA", "ECC", "DSA"} else None
            self.findings.append(Finding(
                file=self.filename,
                line=node.lineno,
                matched_call=self._source_snippet(node),
                library=rule["library"],
                algorithm=rule["algorithm"],
                primitive=rule["primitive"],
                language="python",
                weak_by_default=rule["algorithm"] in WEAK_ALGORITHMS,
                confidence="high",  # Emitted candidates are explicit-import-backed.
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
        if _should_skip(py_file, target):
            continue
        all_findings.extend(scan_file(py_file))
    return all_findings
