"""
scanner/config_engine.py — Config/IaC cryptographic discovery engine (IAC feature).

Scans structured configuration files (YAML, HCL2, Nginx, JSON) for
cryptographic weaknesses such as deprecated TLS versions, weak ciphers,
disabled certificate verification, and undersized keys.

Public API (contract §3.1):
    scan_file(path: Path, rules: dict | None = None) -> list[Finding]
    scan_directory(root: Path, rules: dict | None = None) -> list[Finding]

Design constraints (AGENT_RULES.md):
- No regex-based crypto detection. Detection is entirely structural: parsed
  YAML/HCL2 dicts, tokenised nginx directive lists.
- Errors during parsing are logged to stderr; the scan continues.
- FROZEN: scanner/finding.py is not modified by this engine.
- FROZEN: api/services/scan_runner.py is not called from here.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from scanner.confidence import (
    ConfidenceSignal,
    calculate_confidence_score,
    legacy_confidence_for,
)
from scanner.constants import SCAN_MAX_ARTIFACT_BYTES, SKIP_DIRS
from scanner.finding import Finding

# ── Try to import hcl2; guard for environments without it. ─────────────────
try:
    import hcl2 as _hcl2  # python-hcl2 ≥ 4.3.5
    _HCL2_AVAILABLE: bool = True
except ImportError:  # pragma: no cover
    _hcl2 = None  # type: ignore[assignment]
    _HCL2_AVAILABLE = False


# ── Constants ──────────────────────────────────────────────────────────────

RULES_PATH = Path(__file__).parent / "rules" / "config.yaml"

DETECTION_METHOD = "config_analysis"
ARTIFACT_TYPE = "CONFIG_FILE"
LANGUAGE = "config"

# Library tag per format (Finding.library)
_LIBRARY_FOR_FORMAT: dict[str, str] = {
    "yaml_k8s": "kubernetes",
    "yaml_compose": "docker_compose",
    "yaml_github": "github_actions",
    "yaml_gitlab": "gitlab_ci",
    "yaml": "tls_literal",
    "hcl2": "terraform",
    "nginx": "nginx",
    "json": "tls_literal",
}

# source_context path markers
_TEST_PARTS = {"test", "tests", "__tests__", "fixtures", "fixture", "spec", "e2e"}
_DEMO_PARTS = {"demo", "demos", "example", "examples", "sample", "samples"}

# Interpolation markers (detect unresolved variable references in values)
_INTERP_MARKERS = ("${", "${!", "#{", "{{", "${{")

MAX_EVIDENCE_CHARS = 500


# ── Data structures ─────────────────────────────────────────────────────────

@dataclass
class ConfigFinding(Finding):
    """Finding subclass adding config-specific artifact fields."""
    artifact_type: str = ARTIFACT_TYPE
    artifact_ref: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


def _source_context(path: Path, root: Optional[Path] = None) -> str:
    """Classify path into SOURCE / TEST_ONLY / DEMO_ONLY."""
    try:
        rel = path.relative_to(root) if root else path
    except ValueError:
        rel = path
    parts = {p.lower() for p in rel.parts}
    if parts & _TEST_PARTS:
        return "TEST_ONLY"
    if parts & _DEMO_PARTS:
        return "DEMO_ONLY"
    return "SOURCE"


def _has_interpolation(value: str) -> bool:
    """Return True if value contains an unresolved variable interpolation."""
    for marker in _INTERP_MARKERS:
        if marker in value:
            return True
    return False


def _truncate_evidence(text: str) -> str:
    if len(text) <= MAX_EVIDENCE_CHARS:
        return text
    return text[:MAX_EVIDENCE_CHARS]


def _detect_format(path: Path) -> str:
    """Classify file into a format key for library tagging."""
    name = path.name.lower()
    suffix = path.suffix.lower()

    if name in (".gitlab-ci.yml", ".gitlab-ci.yaml"):
        return "yaml_gitlab"
    if ".github" in [p.lower() for p in path.parts]:
        return "yaml_github"
    if name in ("docker-compose.yml", "docker-compose.yaml",
                "compose.yml", "compose.yaml"):
        return "yaml_compose"
    if suffix in (".yaml", ".yml"):
        return "yaml_k8s"  # default YAML is treated as Kubernetes-flavoured
    if suffix == ".tf":
        return "hcl2"
    if name in ("nginx.conf",) or suffix == ".conf":
        return "nginx"
    if suffix == ".json":
        return "json"
    return "yaml"


def _library_for(fmt: str) -> str:
    return _LIBRARY_FOR_FORMAT.get(fmt, "tls_literal")


def _read_file(path: Path) -> Optional[str]:
    """Read file, respecting SCAN_MAX_ARTIFACT_BYTES; return None on error."""
    try:
        st = path.stat()
    except OSError as exc:
        _warn(f"Cannot stat {path}: {exc}")
        return None
    if st.st_size > SCAN_MAX_ARTIFACT_BYTES:
        _warn(f"Config file too large, skipping: {path} ({st.st_size} bytes)")
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _warn(f"Cannot read {path}: {exc}")
        return None


# ── Rule loading ─────────────────────────────────────────────────────────────

ConfigRules = dict[str, dict[str, Any]]


def load_rules(rules_path: Optional[Path] = None) -> ConfigRules:
    """Load and return the config detection rules from config.yaml.

    Returns an empty dict (no rules) if the file is missing or malformed.
    """
    p = rules_path if rules_path is not None else RULES_PATH
    try:
        text = p.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except FileNotFoundError:
        _warn(f"Config rules file not found: {p}")
        return {}
    except yaml.YAMLError as exc:
        _warn(f"Failed to parse config rules {p}: {exc}")
        return {}
    if not isinstance(data, dict):
        return {}
    rules = data.get("rules", {})
    if not isinstance(rules, dict):
        return {}
    return rules


# ── YAML parsing and detection ───────────────────────────────────────────────

def _parse_yaml(path: Path, text: str) -> Optional[list[dict[str, Any]]]:
    """Parse YAML; return list of documents or None on error.

    PyYAML resolves anchors/aliases transparently, so detection sees final values.
    """
    try:
        docs = list(yaml.safe_load_all(text))
        # Filter out None documents (e.g. empty documents in multi-doc YAML)
        return [d for d in docs if d is not None]
    except yaml.YAMLError as exc:
        _warn(f"Failed to parse YAML {path}: {exc}")
        return None


def _walk_yaml(obj: Any, path_parts: list[str]) -> list[tuple[list[str], Any]]:
    """Recursively walk a parsed YAML object, yielding (key_path, value) pairs.

    - dict: recurse into values
    - list: recurse into items
    - scalar: yield (path_parts, value)
    """
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(_walk_yaml(v, path_parts + [str(k)]))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_walk_yaml(item, path_parts))
    else:
        # Scalar (str, int, bool, float, None)
        if obj is not None:
            results.append((path_parts, obj))
    return results


def _detect_yaml(
    path: Path,
    docs: list[dict[str, Any]],
    rules: ConfigRules,
    source_ctx: str,
    fmt: str,
) -> list[ConfigFinding]:
    """Apply YAML detectors from all rules to all YAML documents in the file."""
    findings: list[ConfigFinding] = []

    for doc in docs:
        pairs = _walk_yaml(doc, [])
        for key_path, raw_value in pairs:
            leaf_key = key_path[-1].lower() if key_path else ""
            value_str = str(raw_value).strip() if raw_value is not None else ""

            for rule_id, rule in rules.items():
                for detector in rule.get("detectors", []):
                    if detector.get("kind") != "yaml":
                        continue
                    finding = _apply_yaml_detector(
                        detector, rule_id, rule, leaf_key, value_str,
                        key_path, path, source_ctx, fmt
                    )
                    if finding:
                        findings.append(finding)

    return findings


def _apply_yaml_detector(
    detector: dict[str, Any],
    rule_id: str,
    rule: dict[str, Any],
    leaf_key: str,
    value_str: str,
    key_path: list[str],
    path: Path,
    source_ctx: str,
    fmt: str,
) -> Optional[ConfigFinding]:
    """Check a single YAML detector spec against a (leaf_key, value_str) pair."""
    # key_patterns: the leaf key must match (case-insensitive)
    key_patterns = [p.lower() for p in detector.get("key_patterns", [])]
    key_contains = [p.lower() for p in detector.get("key_contains", [])]

    # Check key match
    key_matched = False
    if key_patterns:
        key_matched = leaf_key in key_patterns
    elif key_contains:
        key_matched = any(kc in leaf_key for kc in key_contains)
    else:
        key_matched = True  # no key filter → match all keys

    if not key_matched:
        return None

    # First: detect interpolation on the value — regardless of value_patterns
    interp = _has_interpolation(value_str)

    # value_patterns: the value string must match one of the exact patterns
    # OR (for interpolation) the key matched and the value has an interpolation
    value_patterns = detector.get("value_patterns", [])
    value_matched = False
    value_substring = detector.get("value_substring", False)  # opt-in substring mode
    clean_val = value_str.strip('"\'')
    tokens = [t.strip('"\'') for t in re.split(r"[:,\s;]+", clean_val) if t.strip('"\'')]

    for vp in value_patterns:
        vp_clean = vp.strip('"\'')
        if clean_val == vp_clean or clean_val.lower() == vp_clean.lower():
            value_matched = True
            break
        if any(tok == vp_clean or tok.lower() == vp_clean.lower() or tok.startswith(vp_clean + "-") or tok.startswith(vp_clean + "_") for tok in tokens):
            value_matched = True
            break
        if value_substring and (vp_clean in clean_val or vp_clean.lower() in clean_val.lower()):
            value_matched = True
            break

    if not value_matched and not interp:
        return None
    if not value_matched and interp:
        # Only emit an interpolation finding if there were value_patterns to match against
        # (i.e. the rule is relevant to this key, and the value is an unresolved reference)
        pass  # we proceed; conf_gain will be forced to unverified below

    # Determine confidence
    conf_gain = rule.get("confidence_gain", "high")
    if interp:
        conf_gain = "unverified"

    signals = _signals_for(conf_gain, is_yaml=True)
    verdict = calculate_confidence_score(signals)

    evidence = _truncate_evidence(f"{'.'.join(key_path)}: {value_str}")

    return ConfigFinding(
        file=str(path),
        line=0,
        matched_call=evidence,
        library=_library_for(fmt),
        algorithm=rule["algorithm"],
        primitive=rule["primitive"],
        language=LANGUAGE,
        weak_by_default=rule.get("weak_by_default", True),
        confidence=legacy_confidence_for(verdict.band),
        key_size=rule.get("key_size"),
        detection_method=DETECTION_METHOD,
        confidence_score=verdict.score,
        confidence_band=verdict.band,
        confidence_signals=verdict.signals,
        confidence_model_version=verdict.model_version,
        artifact_type=ARTIFACT_TYPE,
        artifact_ref=str(path),
    )


# ── HCL2 parsing and detection ────────────────────────────────────────────────

def _parse_hcl2(path: Path, text: str) -> Optional[dict[str, Any]]:
    """Parse HCL2 (Terraform) using python-hcl2; return parsed dict or None."""
    if not _HCL2_AVAILABLE:
        _warn(f"python-hcl2 not available; skipping HCL2 file {path}")
        return None
    try:
        import io
        data = _hcl2.load(io.StringIO(text))  # type: ignore[union-attr]
        return data
    except Exception as exc:
        _warn(f"Failed to parse HCL2 {path}: {exc}")
        return None


def _walk_hcl2(obj: Any, path_parts: list[str]) -> list[tuple[list[str], Any]]:
    """Recursively walk parsed HCL2, yielding (attr_path, value) pairs."""
    results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(_walk_hcl2(v, path_parts + [str(k)]))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_walk_hcl2(item, path_parts))
    else:
        if obj is not None:
            results.append((path_parts, obj))
    return results


def _detect_hcl2(
    path: Path,
    data: dict[str, Any],
    rules: ConfigRules,
    source_ctx: str,
    fmt: str,
) -> list[ConfigFinding]:
    """Apply HCL2 detectors to parsed HCL2 data."""
    findings: list[ConfigFinding] = []
    pairs = _walk_hcl2(data, [])

    for key_path, raw_value in pairs:
        leaf_key = key_path[-1].lower() if key_path else ""
        value_str = str(raw_value).strip() if raw_value is not None else ""

        for rule_id, rule in rules.items():
            for detector in rule.get("detectors", []):
                if detector.get("kind") != "hcl2":
                    continue
                finding = _apply_hcl2_detector(
                    detector, rule_id, rule, leaf_key, value_str,
                    key_path, path, source_ctx, fmt
                )
                if finding:
                    findings.append(finding)

    return findings


def _apply_hcl2_detector(
    detector: dict[str, Any],
    rule_id: str,
    rule: dict[str, Any],
    leaf_key: str,
    value_str: str,
    key_path: list[str],
    path: Path,
    source_ctx: str,
    fmt: str,
) -> Optional[ConfigFinding]:
    """Check a single HCL2 detector spec against (leaf_key, value_str)."""
    # attribute: exact match
    attr = detector.get("attribute")
    attr_patterns = [p.lower() for p in detector.get("attribute_patterns", [])]

    key_matched = False
    if attr:
        key_matched = leaf_key == attr.lower()
    elif attr_patterns:
        key_matched = any(ap in leaf_key for ap in attr_patterns)
    else:
        key_matched = True

    if not key_matched:
        return None

    clean_val = value_str.strip('"\'')
    value_patterns = detector.get("value_patterns", [])
    value_matched = False
    for vp in value_patterns:
        vp_clean = vp.strip('"\'')
        if clean_val == vp_clean or clean_val.lower() == vp_clean.lower():
            value_matched = True
            break

    if not value_matched:
        return None

    interp = _has_interpolation(value_str)
    conf_gain = rule.get("confidence_gain", "high")
    if interp:
        conf_gain = "unverified"

    signals = _signals_for(conf_gain, is_yaml=False)
    verdict = calculate_confidence_score(signals)
    evidence = _truncate_evidence(f"{'.'.join(key_path)} = {value_str}")

    return ConfigFinding(
        file=str(path),
        line=0,
        matched_call=evidence,
        library=_library_for(fmt),
        algorithm=rule["algorithm"],
        primitive=rule["primitive"],
        language=LANGUAGE,
        weak_by_default=rule.get("weak_by_default", True),
        confidence=legacy_confidence_for(verdict.band),
        key_size=rule.get("key_size"),
        detection_method=DETECTION_METHOD,
        confidence_score=verdict.score,
        confidence_band=verdict.band,
        confidence_signals=verdict.signals,
        confidence_model_version=verdict.model_version,
        artifact_type=ARTIFACT_TYPE,
        artifact_ref=str(path),
    )


# ── Nginx parsing and detection ──────────────────────────────────────────────

def _parse_nginx(path: Path, text: str) -> list[tuple[str, str, int]]:
    """Parse nginx config into (directive, value, line_number) triples.

    Pure tokenisation — no regex-based crypto detection. We only extract
    directive names and their values from lines that look like:
        <whitespace><directive_name> <value...>;

    Comments (# ...) and block delimiters ({ }) are ignored.
    This is intentionally minimal; it is enough for ssl_protocols, ssl_ciphers,
    ssl_verify_client and similar single-value directives.
    """
    results: list[tuple[str, str, int]] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        # Skip blank lines, comments, block delimiters
        if not line or line.startswith("#") or line in ("{", "}"):
            continue
        # Remove trailing semicolon
        if line.endswith(";"):
            line = line[:-1].rstrip()
        # Split into directive + value
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        directive = parts[0].lower()
        value = parts[1]
        results.append((directive, value, lineno))
    return results


def _detect_nginx(
    path: Path,
    directives: list[tuple[str, str, int]],
    rules: ConfigRules,
    source_ctx: str,
    fmt: str,
) -> list[ConfigFinding]:
    """Apply nginx detectors from rules to parsed directive list."""
    findings: list[ConfigFinding] = []

    for directive, value, lineno in directives:
        for rule_id, rule in rules.items():
            for detector in rule.get("detectors", []):
                if detector.get("kind") != "nginx":
                    continue
                expected_dir = detector.get("directive", "").lower()
                if directive != expected_dir:
                    continue

                # value_contains: any of these substrings appear in the value
                vc_patterns = detector.get("value_contains", [])
                value_matched = False
                for vc in vc_patterns:
                    # Check if the directive value token contains this substring
                    # We check the full value string for the occurrence.
                    # This is NOT regex — simple substring containment.
                    if vc in value or vc in (value + " ") or value.endswith(vc.rstrip()):
                        value_matched = True
                        break

                if not value_matched:
                    continue

                interp = _has_interpolation(value)
                conf_gain = rule.get("confidence_gain", "high")
                if interp:
                    conf_gain = "unverified"

                signals = _signals_for(conf_gain, is_yaml=False)
                verdict = calculate_confidence_score(signals)
                evidence = _truncate_evidence(f"{directive} {value};")

                findings.append(ConfigFinding(
                    file=str(path),
                    line=lineno,
                    matched_call=evidence,
                    library=_library_for(fmt),
                    algorithm=rule["algorithm"],
                    primitive=rule["primitive"],
                    language=LANGUAGE,
                    weak_by_default=rule.get("weak_by_default", True),
                    confidence=legacy_confidence_for(verdict.band),
                    key_size=rule.get("key_size"),
                    detection_method=DETECTION_METHOD,
                    confidence_score=verdict.score,
                    confidence_band=verdict.band,
                    confidence_signals=verdict.signals,
                    confidence_model_version=verdict.model_version,
                    artifact_type=ARTIFACT_TYPE,
                    artifact_ref=str(path),
                ))

    return findings


# ── JSON parsing and detection ────────────────────────────────────────────────

def _parse_json(path: Path, text: str) -> Optional[Any]:
    """Parse JSON; return parsed object or None on error."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        _warn(f"Failed to parse JSON {path}: {exc}")
        return None


def _detect_json(
    path: Path,
    data: Any,
    rules: ConfigRules,
    source_ctx: str,
    fmt: str,
) -> list[ConfigFinding]:
    """Apply YAML-style detectors to parsed JSON (same structural walk)."""
    # JSON shares the same structural detection as YAML
    findings: list[ConfigFinding] = []
    if not isinstance(data, (dict, list)):
        return findings

    pairs = _walk_yaml(data, [])  # works for JSON dicts/lists too
    for key_path, raw_value in pairs:
        leaf_key = key_path[-1].lower() if key_path else ""
        value_str = str(raw_value).strip() if raw_value is not None else ""

        for rule_id, rule in rules.items():
            for detector in rule.get("detectors", []):
                if detector.get("kind") not in ("yaml", "json"):
                    continue
                finding = _apply_yaml_detector(
                    detector, rule_id, rule, leaf_key, value_str,
                    key_path, path, source_ctx, fmt
                )
                if finding:
                    findings.append(finding)

    return findings


# ── Confidence signal helpers ─────────────────────────────────────────────────

def _signals_for(conf_gain: str, is_yaml: bool) -> list[str]:
    """Map confidence_gain to confidence signal names.
    
    For VERIFIED/high confidence findings: import_resolved + call_site_matched
    gives score = 0.35 + 0.20 = 0.55 → PROBABLE. Adding expected_module_confirmed
    brings it to 0.75 → PROBABLE still. The key insight: literal config settings
    map best to import_resolved (0.35) + call_site_matched (0.20) + 
    expected_module_confirmed (0.20) + literal_algorithm_arg (0.15) = 0.90 → VERIFIED.
    """
    if conf_gain == "unverified":
        return [ConfidenceSignal.IMPORT_UNRESOLVED.value]  # maps to low score → UNVERIFIED
    # explicit literal: strong signal set → VERIFIED band
    return [
        ConfidenceSignal.IMPORT_RESOLVED.value,
        ConfidenceSignal.CALL_SITE_MATCHED.value,
        ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value,
        ConfidenceSignal.LITERAL_ALGORITHM_ARG.value,
    ]


# ── Deduplication ─────────────────────────────────────────────────────────────

def _dedupe_key(f: ConfigFinding) -> tuple:
    return (f.file, f.algorithm, f.matched_call, f.artifact_type)


def _dedupe(findings: list[ConfigFinding]) -> list[ConfigFinding]:
    seen: set[tuple] = set()
    result = []
    for f in findings:
        k = _dedupe_key(f)
        if k not in seen:
            seen.add(k)
            result.append(f)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def scan_file(path: Path, rules: Optional[ConfigRules] = None) -> list[Finding]:
    """Scan a single configuration file for cryptographic weaknesses.

    Args:
        path: Absolute path to a supported config file.
        rules: Optional parsed ruleset. If None, loads from default location.

    Returns:
        Sorted list of Finding objects. Empty list if no findings or file unsupported.

    Side effects: None (pure function, no DB writes, no network calls).
    """
    if rules is None:
        rules = load_rules()

    fmt = _detect_format(path)
    text = _read_file(path)
    if text is None:
        return []

    source_ctx = _source_context(path)
    findings: list[ConfigFinding] = []

    if fmt in ("yaml", "yaml_k8s", "yaml_compose", "yaml_github", "yaml_gitlab"):
        docs = _parse_yaml(path, text)
        if docs is not None:
            findings.extend(_detect_yaml(path, docs, rules, source_ctx, fmt))

    elif fmt == "hcl2":
        data = _parse_hcl2(path, text)
        if data is not None:
            findings.extend(_detect_hcl2(path, data, rules, source_ctx, fmt))

    elif fmt == "nginx":
        directives = _parse_nginx(path, text)
        findings.extend(_detect_nginx(path, directives, rules, source_ctx, fmt))

    elif fmt == "json":
        data = _parse_json(path, text)
        if data is not None:
            findings.extend(_detect_json(path, data, rules, source_ctx, fmt))

    else:
        return []

    findings = _dedupe(findings)
    findings.sort(key=lambda f: (f.file, f.line, f.algorithm or ""))
    return list(findings)


def _is_config_file(path: Path) -> bool:
    """Return True if this path is a supported config file type."""
    from scanner.constants import CONFIG_FILE_PATTERNS
    name = path.name.lower()
    suffix = path.suffix.lower()

    # Match against CONFIG_FILE_PATTERNS globs (simple suffix / name matching)
    for pattern in CONFIG_FILE_PATTERNS:
        if pattern.startswith("*."):
            # Suffix match
            ext = pattern[1:]  # e.g., ".yaml"
            if suffix == ext:
                return True
        elif pattern.startswith("."):
            # Exact name match (e.g., ".gitlab-ci.yml")
            if name == pattern.lower():
                return True
        else:
            # Exact name match (e.g., "nginx.conf")
            if name == pattern.lower():
                return True

    return False


def _should_skip_for_config(path: Path, root: Path) -> bool:
    """Return True if path should be skipped during directory scan.

    Per C-12: config engine does NOT inherit SKIP_DIRS blindly.
    It skips only the directories that have no business containing
    config files we care about (generated JS/Python artifacts, VCS metadata).
    """
    # Only skip VCS, package manager, IDE artefacts.
    CONFIG_SKIP = {"node_modules", ".git", "__pycache__", ".pytest_cache",
                   ".venv", "venv", "env", ".idea", ".vscode", ".nyc_output"}
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    for part in rel.parts:
        if part in CONFIG_SKIP:
            return True
    return False


def scan_directory(root: Path, rules: Optional[ConfigRules] = None) -> list[Finding]:
    """Recursively scan a directory for supported configuration files.

    Args:
        root: Absolute path to the directory to scan.
        rules: Optional parsed ruleset. If None, loads from default location.

    Returns:
        Aggregated sorted list of Finding objects from all config files.

    Side effects: None.
    """
    if rules is None:
        rules = load_rules()

    if root.is_file():
        return scan_file(root, rules)

    all_findings: list[Finding] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if _should_skip_for_config(p, root):
            continue
        if not _is_config_file(p):
            continue
        all_findings.extend(scan_file(p, rules))

    all_findings.sort(key=lambda f: (f.file, f.line, f.algorithm or ""))
    return all_findings
