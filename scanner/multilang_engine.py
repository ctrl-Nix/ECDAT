"""
ECDAT Multi-Language Cryptographic Scanner
==========================================

Tree-sitter based static analysis for Java, JavaScript, and TypeScript.
Loads per-language detection rules from external YAML files at runtime.

Adding a new language means:
  1. Install the tree-sitter grammar (or ensure tree-sitter-languages ships it)
  2. Drop a ``{language}.yaml`` rule file into the rules directory
  3. Add the file extension → language mapping in ``EXT_TO_LANG``
  4. (Optional) Add an import-resolution query in ``IMPORT_QUERIES``

No scanner logic changes required.

Requires::

    pip install "tree-sitter==0.21.3" tree-sitter-languages pyyaml

.. note::
   Pinned to tree-sitter 0.21.3 + tree-sitter-languages for compatibility.
   Requires Python 3.11 (see Dockerfile) -- tree-sitter-languages has no Python 3.12+ wheels.

.. note:: PIPELINE FIX (finding_id)
   The shared ``Finding`` dataclass (scanner/finding.py) has no
   ``finding_id`` field, but downstream consumers do expect one:
     - risk_engine.py's ``score_findings_batch()`` requires
       ``f["finding_id"]`` on every item and will raise ``KeyError``
       without it.
     - cbom_generator.py already tolerates its absence (falls back to
       list index via ``finding.get("id", finding_id)``), but having a
       real, stable id is still preferable for cross-referencing the
       CBOM back to a specific risk_assessments row.
   Rather than changing the shared ``Finding`` schema (which every
   engine depends on), this module assigns a sequential ``finding_id``
   at serialization time -- see ``findings_to_dicts()`` below. This is
   the single choke point all output passes through (stand-alone CLI
   below, and any future ``scanner/cli.py`` merge step), so JSON written
   from here can be fed straight into risk_engine.score_findings_batch()
   or cbom_generator.build_cbom_from_findings() with no glue script.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from tree_sitter_languages import get_language, get_parser

# Use the canonical Finding model shared by all engines.
# This guarantees that Python-engine and multilang-engine output are
# structurally identical and can be merged safely by ``scanner/cli.py``.
from scanner.constants import SKIP_DIRS, _should_skip
from scanner.finding import Finding

__all__ = [
    "load_rules",
    "scan_file",
    "scan_directory",
    "findings_to_dicts",
    "RULES_DIR_DEFAULT",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Map file extensions to the language identifier used by tree-sitter-languages.
EXT_TO_LANG: Dict[str, str] = {
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",   # TypeScript uses the same call-expression grammar as JS
    ".jsx": "javascript",  # JSX call syntax is identical for our purposes
    ".tsx": "typescript",
}

# Default rules directory — resolved relative to this module so that
# ``scanner/cli.py`` does not need to hard-code a path.
RULES_DIR_DEFAULT: Path = Path(__file__).resolve().parent / "rules"

# ---------------------------------------------------------------------------
# Tree-sitter queries
# ---------------------------------------------------------------------------

# One query per language that captures the *shape* of a method/function call.
# The actual cryptographic knowledge lives entirely in ``rules/*.yaml``.
_CALL_QUERIES: Dict[str, str] = {
    "java": """
        [
          (method_invocation
            object: (identifier) @object
            name: (identifier) @method
            arguments: (argument_list) @args)
          (method_invocation
            name: (identifier) @method
            arguments: (argument_list) @args)
        ] @call
    """,
    "javascript": """
        [
          (call_expression
            function: (member_expression
              object: (identifier) @object
              property: (property_identifier) @method)
            arguments: (arguments) @args)
          (call_expression
            function: (identifier) @method
            arguments: (arguments) @args)
        ] @call
    """,
    "typescript": """
        [
          (call_expression
            function: (member_expression
              object: (identifier) @object
              property: (property_identifier) @method)
            arguments: (arguments) @args)
          (call_expression
            function: (identifier) @method
            arguments: (arguments) @args)
        ] @call
    """,
}

# Queries that resolve where an identifier came from.
# This is the direct equivalent of the alias-tracking the Python scanner
# already does via ``ast.Import`` / ``ast.ImportFrom``.
_IMPORT_QUERIES: Dict[str, str] = {
    "java": """
        [
          (import_declaration) @decl
          (import_declaration
            (modifiers (static)) @static_decl)
        ] @decl
    """,
    "javascript": """
        [
          (variable_declarator
            name: (identifier) @varname
            value: (call_expression
              function: (identifier) @fn
              arguments: (arguments (string) @modname)))
          (import_statement
            (import_clause (identifier) @varname)
            (string) @modname)
          (import_statement
            (import_clause
              (named_imports
                (import_specifier (identifier) @varname)))
            (string) @modname)
        ] @decl
    """,
    "typescript": """
        [
          (variable_declarator
            name: (identifier) @varname
            value: (call_expression
              function: (identifier) @fn
              arguments: (arguments (string) @modname)))
          (import_statement
            (import_clause (identifier) @varname)
            (string) @modname)
          (import_statement
            (import_clause
              (named_imports
                (import_specifier (identifier) @varname)))
            (string) @modname)
        ] @decl
    """,
}

# ---------------------------------------------------------------------------
# Caches — parsers and languages are expensive to build; keep them around.
# ---------------------------------------------------------------------------

_PARSER_CACHE: Dict[str, object] = {}
_LANGUAGE_CACHE: Dict[str, object] = {}


def _get_parser(language: str) -> object:
    """Return a cached tree-sitter parser for *language*."""
    if language not in _PARSER_CACHE:
        _PARSER_CACHE[language] = get_parser(language)
    return _PARSER_CACHE[language]


def _get_language(language: str) -> object:
    """Return a cached tree-sitter language object for *language*."""
    if language not in _LANGUAGE_CACHE:
        _LANGUAGE_CACHE[language] = get_language(language)
    return _LANGUAGE_CACHE[language]


# ---------------------------------------------------------------------------
# Rule loading
# ---------------------------------------------------------------------------

def load_rules(rules_dir: Path) -> Dict[str, List[dict]]:
    """Load every ``*.yaml`` in *rules_dir* and group by language.

    Returns a dict ``{language: [rule, ...]}`` where each *rule* is the
    raw dict from the YAML file (containing keys like ``match_object``,
    ``match_method``, ``algorithm``, ``primitive``, etc.).
    """
    rules_by_lang: Dict[str, List[dict]] = {}
    if not rules_dir.is_dir():
        logger.warning("Rules directory does not exist: %s", rules_dir)
        return rules_by_lang

    for filepath in sorted(rules_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed to parse %s: %s", filepath, exc)
            continue

        if not isinstance(data, dict) or "language" not in data or "rules" not in data:
            logger.warning("Skipping malformed rule file: %s", filepath)
            continue

        lang = data["language"]
        rules_by_lang.setdefault(lang, []).extend(data["rules"])
        logger.debug("Loaded %d rules for %s from %s", len(data["rules"]), lang, filepath.name)

    return rules_by_lang


# ---------------------------------------------------------------------------
# Import / binding resolution
# ---------------------------------------------------------------------------

def _resolve_java_imports(tree, source: bytes) -> tuple[Dict[str, str], Dict[str, str]]:
    """Map simple class name → fully-qualified import path.

    Also returns static imports mapping method name → class name.

    Example::

        import java.security.MessageDigest;
        import static java.security.MessageDigest.getInstance;
        #  => imports: {"MessageDigest": "java.security.MessageDigest"}
        #  => static_imports: {"getInstance": "MessageDigest"}

    Wildcard imports (``.*``) are intentionally ignored because they cannot
    be resolved to a specific class without classpath analysis.
    """
    lang = _get_language("java")
    query = lang.query(_IMPORT_QUERIES["java"])
    imports: Dict[str, str] = {}
    static_imports: Dict[str, str] = {}

    for _, captures in query.matches(tree.root_node):
        decl_nodes = captures.get("decl")
        if not decl_nodes:
            continue

        decl_node = decl_nodes[0]
        raw = source[decl_node.start_byte:decl_node.end_byte].decode("utf-8", "ignore")
        stripped = raw.strip()
        if stripped.startswith("import"):
            stripped = stripped[len("import"):].strip()
        is_static = stripped.startswith("static")
        if is_static:
            stripped = stripped[len("static"):].strip()
        stripped = stripped.rstrip(";").strip()

        if stripped.endswith(".*"):
            continue  # wildcard — cannot resolve to a specific class

        parts = stripped.split(".")
        simple_name = parts[-1]
        full_path = stripped
        class_name = parts[-2] if len(parts) >= 2 else simple_name

        if is_static:
            # For static imports, map method name to class name
            # e.g., "java.security.MessageDigest.getInstance" -> {"getInstance": "MessageDigest"}
            static_imports[simple_name] = class_name
            # Also add to imports so confidence check works
            class_path = ".".join(parts[:-1])
            imports[class_name] = class_path
        else:
            imports[simple_name] = full_path

    return imports, static_imports


def _resolve_js_bindings(tree, source: bytes) -> tuple[Dict[str, str], Dict[str, str]]:
    """Map local variable name → module specifier.

    Handles CommonJS, ES6 default imports, and ES6 named imports.

    Returns:
        bindings: Maps variable/function name → module name
        static_imports: Maps imported function name → module name (for ES6 named imports)
    """
    lang = _get_language("javascript")
    query = lang.query(_IMPORT_QUERIES["javascript"])
    bindings: Dict[str, str] = {}
    static_imports: Dict[str, str] = {}

    for _, captures in query.matches(tree.root_node):
        var_nodes = captures.get("varname")
        mod_nodes = captures.get("modname")
        fn_nodes = captures.get("fn")

        if not var_nodes or not mod_nodes:
            continue

        var_node = var_nodes[0]
        mod_node = mod_nodes[0]
        fn_node = fn_nodes[0] if fn_nodes else None

        varname = source[var_node.start_byte:var_node.end_byte].decode("utf-8", "ignore")
        modname = _extract_string_text(mod_node, source)
        if not modname:
            continue
        modname = modname.replace("node:", "")

        # For CommonJS, ensure the call is actually ``require()``.
        if fn_node is not None:
            fn_text = source[fn_node.start_byte:fn_node.end_byte].decode("utf-8", "ignore")
            if fn_text != "require":
                continue
            # CommonJS: const crypto = require("crypto")
            bindings[varname] = modname
        else:
            # ES6 imports: import crypto from "crypto" or import { createHash } from "crypto"
            # For default imports, varname is the alias (e.g., "crypto")
            # For named imports, varname is the imported function (e.g., "createHash")
            # Both map to the module name
            bindings[varname] = modname
            static_imports[varname] = modname

    return bindings, static_imports


# ---------------------------------------------------------------------------
# Argument extraction helpers
# ---------------------------------------------------------------------------

def _extract_string_text(node, source: bytes) -> Optional[str]:
    """Return the unquoted text of a string literal node.

    Tries ``string_fragment`` first (most tree-sitter grammars), then
    falls back to stripping quotes from the raw node text.
    """
    for child in [node, *node.children]:
        if child.type == "string_fragment":
            return source[child.start_byte:child.end_byte].decode("utf-8", "ignore")
    raw = source[node.start_byte:node.end_byte].decode("utf-8", "ignore")
    return raw.strip('"')


def _first_string_arg(args_node, source: bytes) -> Optional[str]:
    """Return the text of the first string literal inside an argument list."""
    if args_node is None:
        return None
    for child in args_node.children:
        if "string" in child.type:
            return _extract_string_text(child, source)
    return None


def _extract_key_size(args_node, source: bytes) -> Optional[int]:
    """Attempt to extract a key-size or modulus-length from arguments.

    Strategies (best-effort)::

      1. Look for a numeric literal (e.g. ``initialize(1024)``).
      2. For JavaScript/TypeScript, look inside an object literal for
         properties named ``modulusLength`` or ``keyLength``.
    """
    if args_node is None:
        return None

    # Strategy 1: direct numeric literal
    for child in args_node.children:
        if child.type == "decimal_integer_literal":
            try:
                return int(source[child.start_byte:child.end_byte].decode("utf-8", "ignore"))
            except ValueError:
                continue
        if child.type == "number":  # JS/TS
            try:
                return int(float(source[child.start_byte:child.end_byte].decode("utf-8", "ignore")))
            except ValueError:
                continue

    # Strategy 2: object literal (JS/TS)
    for child in args_node.children:
        if child.type == "object":
            for pair in child.children:
                if pair.type != "pair":
                    continue
                key_node = pair.child_by_field_name("key")
                val_node = pair.child_by_field_name("value")
                if key_node is None or val_node is None:
                    continue
                key_text = source[key_node.start_byte:key_node.end_byte].decode("utf-8", "ignore")
                if key_text in ("modulusLength", "keyLength", "length"):
                    try:
                        return int(float(source[val_node.start_byte:val_node.end_byte].decode("utf-8", "ignore")))
                    except ValueError:
                        continue

    return None


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------

def scan_file(path: Path, rules_by_lang: Dict[str, List[dict]]) -> List[Finding]:
    """Scan a single source file and return all cryptographic findings.

    Parameters
    ----------
    path:
        Absolute or relative path to the source file.
    rules_by_lang:
        Output of :func:`load_rules` — rules grouped by language key.

    Returns
    -------
    List[Finding]
        Findings sorted by line number.
    """
    lang_key = EXT_TO_LANG.get(path.suffix)
    if lang_key is None or lang_key not in rules_by_lang:
        return []

    # Resolve the actual tree-sitter language identifier.
    # TypeScript uses the TypeScript parser but may reuse JS rules.
    ts_language = "typescript" if lang_key == "typescript" else lang_key

    try:
        source = path.read_bytes()
        parser = _get_parser(ts_language)
        tree = parser.parse(source)
    except Exception as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        return []

    # Resolve imports / require bindings so we can verify confidence.
    if lang_key == "java":
        bindings, static_imports = _resolve_java_imports(tree, source)
    elif lang_key in ("javascript", "typescript"):
        bindings, static_imports = _resolve_js_bindings(tree, source)
    else:
        bindings = _resolve_js_bindings(tree, source)
        static_imports = {}

    # Run the call-expression query.
    ts_lang = _get_language(ts_language)
    query_text = _CALL_QUERIES.get(lang_key) or _CALL_QUERIES.get(ts_language)
    if query_text is None:
        logger.warning("No query defined for language %r", lang_key)
        return []

    query = ts_lang.query(query_text)
    matches = query.matches(tree.root_node)

    findings: List[Finding] = []

    for _, captures in matches:
        call_nodes = captures.get("call")
        object_nodes = captures.get("object")
        method_nodes = captures.get("method")
        args_nodes = captures.get("args")

        if not (call_nodes and method_nodes):
            continue

        call_node = call_nodes[0]
        method_node = method_nodes[0]
        args_node = args_nodes[0] if args_nodes else None
        object_node = object_nodes[0] if object_nodes else None

        method_name = source[method_node.start_byte:method_node.end_byte].decode("utf-8", "ignore")
        arg_text = _first_string_arg(args_node, source)

        # For static calls, object_name is empty; try to resolve via static imports
        object_name = ""
        if object_node:
            object_name = source[object_node.start_byte:object_node.end_byte].decode("utf-8", "ignore")
        elif method_name in static_imports:
            # Static import: use the class name from the import
            object_name = static_imports[method_name]

        for rule in rules_by_lang[lang_key]:
            if rule.get("match_object") != object_name:
                continue
            if rule.get("match_method") != method_name:
                continue

            expected_arg = rule.get("match_arg_contains")
            if expected_arg and (not arg_text or expected_arg.lower() not in arg_text.lower()):
                continue

            # Confidence: does the object name trace back to a real import?
            confidence = "unverified"
            expected = rule.get("expected_import") or rule.get("expected_module")
            resolved = bindings.get(object_name)
            if expected and resolved == expected:
                confidence = "high"

            # Best-effort key-size extraction.
            key_size = _extract_key_size(args_node, source)

            findings.append(
                Finding(
                    file=str(path),
                    line=call_node.start_point[0] + 1,  # tree-sitter is 0-indexed
                    matched_call=source[call_node.start_byte:call_node.end_byte].decode("utf-8", "ignore"),
                    library=object_name,
                    algorithm=rule["algorithm"],
                    primitive=rule["primitive"],
                    language=lang_key,
                    weak_by_default=rule["weak_by_default"],
                    confidence=confidence,
                    key_size=key_size,
                    detection_method="tree_sitter_query",
                )
            )
            break  # first matching rule wins per call site

    findings.sort(key=lambda f: f.line)
    return findings


def scan_directory(target: Path, rules_by_lang: Dict[str, List[dict]]) -> List[Finding]:
    """Recursively scan *target* (file or directory) for cryptographic usage.

    Parameters
    ----------
    target:
        Path to a single file or a directory to walk recursively.
    rules_by_lang:
        Output of :func:`load_rules`.

    Returns
    -------
    List[Finding]
        All findings across every matched file, sorted by (file, line).
    """
    all_findings: List[Finding] = []

    if target.is_file():
        if not _should_skip(target):
            all_findings.extend(scan_file(target, rules_by_lang))
    elif target.is_dir():
        for ext in EXT_TO_LANG:
            for filepath in sorted(target.rglob(f"*{ext}")):
                if not _should_skip(filepath):
                    all_findings.extend(scan_file(filepath, rules_by_lang))
    else:
        logger.error("Target path does not exist: %s", target)

    all_findings.sort(key=lambda f: (f.file, f.line))
    return all_findings


# ---------------------------------------------------------------------------
# Serialization — MISMATCH FIX: attach a stable finding_id here
# ---------------------------------------------------------------------------

def findings_to_dicts(findings: List[Finding]) -> List[dict]:
    """Convert ``Finding`` objects to plain dicts, each tagged with a
    sequential ``finding_id``.

    This is the single place scanner output gets serialized, so every
    downstream consumer sees a consistent, present ``finding_id``:

      - risk_engine.score_findings_batch() requires ``f["finding_id"]``
        on every item -- without this, it raises ``KeyError`` on raw
        multilang output.
      - cbom_generator.finding_to_crypto_asset() already tolerates a
        missing id (falls back to list index), but will now pick up
        this real id via ``finding.get("id", finding_id)`` lookups that
        also check ``"finding_id"``... concretely, both engines can take
        this same list of dicts with no extra glue script.

    The id is assigned in (file, line)-sorted order (i.e. the same order
    ``scan_directory`` already returns), so ids are stable across runs
    as long as the input files don't change.
    """
    result = []
    for idx, finding in enumerate(findings):
        d = asdict(finding)
        d["finding_id"] = idx  # <-- the fix: guarantees the key every downstream engine expects
        d.setdefault("id", idx)  # kept too, in case older tooling reads "id" instead
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Stand-alone CLI (for testing / debugging — ``scanner/cli.py`` is the
# canonical entrypoint for production use).
# ---------------------------------------------------------------------------

def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python multilang_engine.py <target_dir> <rules_dir> [-o findings.json]", file=sys.stderr)
        sys.exit(1)

    target_path = Path(sys.argv[1])
    rules_path = Path(sys.argv[2])
    rules = load_rules(rules_path)

    results = scan_directory(target_path, rules)
    output = findings_to_dicts(results)

    if "-o" in sys.argv:
        out_path = sys.argv[sys.argv.index("-o") + 1]
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Wrote {len(output)} findings to {out_path}", file=sys.stderr)
    else:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    _main()
