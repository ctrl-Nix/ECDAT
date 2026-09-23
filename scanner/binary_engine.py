"""
scanner/binary_engine.py — Heuristic cryptographic scanner for compiled binaries (BIN feature).

Scans ELF, PE, and Mach-O binaries for:
- Tier 1: Linked cryptographic symbols, imported/exported symbols, and needed libraries
          (high confidence, detection_method="binary_symbol_table").
- Tier 2: Cryptographic constant signatures in read-only data sections
          (unverified confidence, detection_method="binary_constant_scan").

Public API (SYSTEM_INTERFACE_CONTRACT.md §3.1):
    scan_file(path: Path, rules: dict | list | None = None) -> list[Finding]
    scan_directory(root: Path, rules: dict | list | None = None) -> list[Finding]
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path
from typing import Any, Optional

from scanner.confidence import (
    ConfidenceSignal,
    calculate_confidence_score,
    legacy_confidence_for,
)
from scanner.constants import BINARY_SKIP_DIRS, SCAN_MAX_ARTIFACT_BYTES
from scanner.finding import Finding
from scanner.multilang_engine import load_rules

# Optional parser libraries
try:
    import lief  # type: ignore
except ImportError:
    lief = None

try:
    from elftools.elf.elffile import ELFFile  # type: ignore
    from elftools.elf.dynamic import DynamicSection  # type: ignore
    from elftools.elf.sections import SymbolTableSection  # type: ignore
except ImportError:
    ELFFile = None

try:
    import pefile  # type: ignore
except ImportError:
    pefile = None

try:
    import macholib.MachO  # type: ignore
except ImportError:
    macholib = None

RULES_DIR = Path(__file__).resolve().parent / "rules"

# Magic byte signatures for binary formats
ELF_MAGIC = b"\x7fELF"
PE_DOS_MAGIC = b"MZ"
MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit big-endian
    b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit big-endian
    b"\xce\xfa\xed\xfe",  # Mach-O 32-bit little-endian
    b"\xcf\xfa\xed\xfe",  # Mach-O 64-bit little-endian
    b"\xca\xfe\xba\xbe",  # Mach-O Fat binary
    b"\xbe\xba\xfe\xca",  # Mach-O Fat binary (reversed)
}


def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


def _get_rules(rules: dict | list | None) -> list[dict[str, Any]]:
    """Normalize rules to a list of rule dicts for binary scanning."""
    if isinstance(rules, list):
        return rules
    if isinstance(rules, dict):
        if "binary" in rules and isinstance(rules["binary"], list):
            return rules["binary"]
        if "rules" in rules and isinstance(rules["rules"], list):
            return rules["rules"]
    loaded = load_rules(RULES_DIR)
    return loaded.get("binary", [])


def _detect_format(data: bytes) -> Optional[str]:
    """Detect binary format (elf, pe, macho) from initial file bytes."""
    if len(data) < 4:
        return None
    if data.startswith(ELF_MAGIC):
        return "elf"
    if data.startswith(PE_DOS_MAGIC) and len(data) >= 0x40:
        try:
            pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
            if len(data) >= pe_offset + 4 and data[pe_offset : pe_offset + 4] == b"PE\x00\x00":
                return "pe"
        except struct.error:
            pass
    if data[:4] in MACHO_MAGICS:
        return "macho"
    return None


def _scan_with_lief(
    path: Path,
    data: bytes,
    fmt: str,
    rules: list[dict[str, Any]],
) -> Optional[list[Finding]]:
    """Parse with LIEF and extract Tier 1 and Tier 2 findings."""
    if lief is None:
        return None
    try:
        binary = lief.parse(str(path))
        if binary is None:
            return None
    except Exception as exc:
        _warn(f"LIEF failed to parse {path}: {exc}")
        return None

    findings: list[Finding] = []

    # Extract symbols and needed libraries
    symbols: list[tuple[str, str]] = []  # (symbol_name, table_name)
    try:
        for sym in getattr(binary, "symbols", []):
            if sym.name:
                symbols.append((sym.name, ".symtab"))
        for sym in getattr(binary, "dynamic_symbols", []):
            if sym.name:
                symbols.append((sym.name, ".dynsym"))
        for sym in getattr(binary, "imported_symbols", []):
            if sym.name:
                symbols.append((sym.name, ".dynsym"))
        for sym in getattr(binary, "exported_symbols", []):
            if sym.name:
                symbols.append((sym.name, ".dynsym"))
        for lib in getattr(binary, "libraries", []):
            if lib:
                symbols.append((lib, ".dynamic:NEEDED"))
    except Exception as exc:
        _warn(f"Error reading symbols with LIEF from {path}: {exc}")

    # Tier 1: Symbol matching
    tier1_rules = [r for r in rules if r.get("tier") == 1 or r.get("match_type") == "symbol"]
    seen_tier1: set[tuple[str, str]] = set()

    for sym_name, table in symbols:
        for rule in tier1_rules:
            pattern = rule.get("match_pattern", "")
            if not pattern:
                continue
            expected_formats = [f.lower() for f in rule.get("expected_format", [])]
            if expected_formats and fmt.lower() not in expected_formats:
                continue

            if sym_name == pattern or pattern in sym_name:
                key = (rule["algorithm"], sym_name)
                if key in seen_tier1:
                    continue
                seen_tier1.add(key)

                signals = [
                    ConfidenceSignal.IMPORT_RESOLVED.value,
                    ConfidenceSignal.CALL_SITE_MATCHED.value,
                    ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value,
                    ConfidenceSignal.RULE_YAML_MATCHED.value,
                ]
                verdict = calculate_confidence_score(signals)

                matched_call = f"{table}:{sym_name}" if not table.endswith(f":{sym_name}") else table
                if table.startswith(".dynamic:NEEDED"):
                    matched_call = f".dynamic:{sym_name}"

                findings.append(
                    Finding(
                        file=str(path),
                        line=0,
                        matched_call=matched_call,
                        library=rule.get("library", "unknown"),
                        algorithm=rule["algorithm"],
                        primitive=rule.get("primitive", "unknown"),
                        language=fmt.lower(),
                        weak_by_default=rule.get("weak_by_default", False),
                        confidence="high",
                        key_size=rule.get("key_size"),
                        detection_method="binary_symbol_table",
                        confidence_score=verdict.score,
                        confidence_band=verdict.band,
                        confidence_signals=verdict.signals,
                        confidence_model_version=verdict.model_version,
                    )
                )

    # Tier 2: Constant matching
    tier2_rules = [r for r in rules if r.get("tier") == 2 or r.get("match_type") == "constant"]
    try:
        sections = getattr(binary, "sections", [])
        for section in sections:
            sec_name = getattr(section, "name", ".data")
            content = bytes(getattr(section, "content", b""))
            if not content:
                continue

            for rule in tier2_rules:
                hex_pat = rule.get("match_pattern_hex", "").strip()
                if not hex_pat:
                    continue
                try:
                    pat_bytes = bytes.fromhex(hex_pat)
                except ValueError:
                    continue

                idx = 0
                while True:
                    idx = content.find(pat_bytes, idx)
                    if idx == -1:
                        break

                    signals = [
                        ConfidenceSignal.RULE_YAML_MATCHED.value,
                        ConfidenceSignal.IMPORT_UNRESOLVED.value,
                    ]
                    verdict = calculate_confidence_score(signals)

                    findings.append(
                        Finding(
                            file=str(path),
                            line=0,
                            matched_call=f"{sec_name}+0x{idx:x}",
                            library=rule.get("library", "unknown"),
                            algorithm=rule["algorithm"],
                            primitive=rule.get("primitive", "unknown"),
                            language=fmt.lower(),
                            weak_by_default=rule.get("weak_by_default", False),
                            confidence="unverified",
                            key_size=rule.get("key_size"),
                            detection_method="binary_constant_scan",
                            confidence_score=verdict.score,
                            confidence_band=verdict.band,
                            confidence_signals=verdict.signals,
                            confidence_model_version=verdict.model_version,
                        )
                    )
                    idx += len(pat_bytes)
    except Exception as exc:
        _warn(f"Error reading sections with LIEF from {path}: {exc}")

    return findings


def _scan_fallback(
    path: Path,
    data: bytes,
    fmt: str,
    rules: list[dict[str, Any]],
) -> list[Finding]:
    """Pure-python fallback parser for ELF/PE/Mach-O when LIEF is unavailable."""
    findings: list[Finding] = []
    symbols: list[tuple[str, str]] = []
    sections: list[tuple[str, bytes]] = []

    if fmt == "elf" and ELFFile is not None:
        try:
            import io
            elf = ELFFile(io.BytesIO(data))
            for sec in elf.iter_sections():
                if isinstance(sec, SymbolTableSection):
                    sec_name = sec.name or ".symtab"
                    for sym in sec.iter_symbols():
                        if sym.name:
                            symbols.append((sym.name, sec_name))
                elif isinstance(sec, DynamicSection):
                    for tag in sec.iter_tags():
                        if tag.entry.d_tag == "DT_NEEDED":
                            symbols.append((tag.needed, ".dynamic:NEEDED"))
                sec_name = sec.name or ".data"
                try:
                    sections.append((sec_name, sec.data()))
                except Exception:
                    pass
        except Exception as exc:
            _warn(f"pyelftools failed to parse {path}: {exc}")

    elif fmt == "pe" and pefile is not None:
        try:
            pe = pefile.PE(data=data, fast_load=True)
            pe.parse_data_directories()
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    dll_name = entry.dll.decode(errors="ignore") if entry.dll else ""
                    if dll_name:
                        symbols.append((dll_name, ".idata:DLL"))
                    for imp in entry.imports:
                        if imp.name:
                            symbols.append((imp.name.decode(errors="ignore"), ".idata"))
            if hasattr(pe, "DIRECTORY_ENTRY_EXPORT") and pe.DIRECTORY_ENTRY_EXPORT:
                for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if exp.name:
                        symbols.append((exp.name.decode(errors="ignore"), ".edata"))
            for sec in pe.sections:
                sec_name = sec.Name.decode(errors="ignore").strip("\x00")
                sections.append((sec_name, sec.get_data()))
        except Exception as exc:
            _warn(f"pefile failed to parse {path}: {exc}")

    if not sections:
        # Generic fallback section extraction
        sections.append((".rodata", data))

    # Generic string extraction fallback if no symbols found
    if not symbols:
        import re
        # Find printable ASCII strings
        ascii_strings = [m.group().decode("ascii") for m in re.finditer(rb"[A-Za-z0-9_]{3,64}", data)]
        for s in set(ascii_strings):
            symbols.append((s, ".dynsym"))

    # Tier 1
    tier1_rules = [r for r in rules if r.get("tier") == 1 or r.get("match_type") == "symbol"]
    seen_tier1: set[tuple[str, str]] = set()

    for sym_name, table in symbols:
        for rule in tier1_rules:
            pattern = rule.get("match_pattern", "")
            if not pattern:
                continue
            expected_formats = [f.lower() for f in rule.get("expected_format", [])]
            if expected_formats and fmt.lower() not in expected_formats:
                continue

            if sym_name == pattern or (len(pattern) >= 4 and pattern in sym_name):
                key = (rule["algorithm"], sym_name)
                if key in seen_tier1:
                    continue
                seen_tier1.add(key)

                signals = [
                    ConfidenceSignal.IMPORT_RESOLVED.value,
                    ConfidenceSignal.CALL_SITE_MATCHED.value,
                    ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value,
                    ConfidenceSignal.RULE_YAML_MATCHED.value,
                ]
                verdict = calculate_confidence_score(signals)

                matched_call = f"{table}:{sym_name}" if not table.endswith(f":{sym_name}") else table
                if table.startswith(".dynamic:NEEDED"):
                    matched_call = f".dynamic:{sym_name}"

                findings.append(
                    Finding(
                        file=str(path),
                        line=0,
                        matched_call=matched_call,
                        library=rule.get("library", "unknown"),
                        algorithm=rule["algorithm"],
                        primitive=rule.get("primitive", "unknown"),
                        language=fmt.lower(),
                        weak_by_default=rule.get("weak_by_default", False),
                        confidence="high",
                        key_size=rule.get("key_size"),
                        detection_method="binary_symbol_table",
                        confidence_score=verdict.score,
                        confidence_band=verdict.band,
                        confidence_signals=verdict.signals,
                        confidence_model_version=verdict.model_version,
                    )
                )

    # Tier 2
    tier2_rules = [r for r in rules if r.get("tier") == 2 or r.get("match_type") == "constant"]
    for sec_name, content in sections:
        if not content:
            continue
        for rule in tier2_rules:
            hex_pat = rule.get("match_pattern_hex", "").strip()
            if not hex_pat:
                continue
            try:
                pat_bytes = bytes.fromhex(hex_pat)
            except ValueError:
                continue

            idx = 0
            while True:
                idx = content.find(pat_bytes, idx)
                if idx == -1:
                    break

                signals = [
                    ConfidenceSignal.RULE_YAML_MATCHED.value,
                    ConfidenceSignal.IMPORT_UNRESOLVED.value,
                ]
                verdict = calculate_confidence_score(signals)

                findings.append(
                    Finding(
                        file=str(path),
                        line=0,
                        matched_call=f"{sec_name}+0x{idx:x}",
                        library=rule.get("library", "unknown"),
                        algorithm=rule["algorithm"],
                        primitive=rule.get("primitive", "unknown"),
                        language=fmt.lower(),
                        weak_by_default=rule.get("weak_by_default", False),
                        confidence="unverified",
                        key_size=rule.get("key_size"),
                        detection_method="binary_constant_scan",
                        confidence_score=verdict.score,
                        confidence_band=verdict.band,
                        confidence_signals=verdict.signals,
                        confidence_model_version=verdict.model_version,
                    )
                )
                idx += len(pat_bytes)

    return findings


def scan_file(path: Path, rules: dict | list | None = None) -> list[Finding]:
    """Scan a single binary file for cryptographic symbols and constant signatures.

    Returns an empty list if the file is not a supported binary format or exceeds size limits.
    """
    p = Path(path)
    try:
        st = p.stat()
    except OSError as exc:
        _warn(f"Cannot stat {p}: {exc}")
        return []

    if st.st_size > SCAN_MAX_ARTIFACT_BYTES:
        _warn(f"binary file exceeds size limit ({SCAN_MAX_ARTIFACT_BYTES} bytes), skipping: {p}")
        return []

    try:
        data = p.read_bytes()
    except OSError as exc:
        _warn(f"Cannot read {p}: {exc}")
        return []

    fmt = _detect_format(data)
    if fmt is None:
        return []

    rule_list = _get_rules(rules)
    if not rule_list:
        return []

    # Try LIEF first; fall back if unavailable or fails
    findings = _scan_with_lief(p, data, fmt, rule_list)
    if findings is None:
        findings = _scan_fallback(p, data, fmt, rule_list)

    return findings


def scan_directory(root: Path, rules: dict | list | None = None) -> list[Finding]:
    """Recursively scan a directory tree for binary artifacts.

    Skips directories listed in BINARY_SKIP_DIRS.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        if root_path.is_file():
            return scan_file(root_path, rules)
        return []

    all_findings: list[Finding] = []
    rule_list = _get_rules(rules)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune skipped directories in-place
        dirnames[:] = [d for d in dirnames if d not in BINARY_SKIP_DIRS]

        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            try:
                if fpath.is_file() and not fpath.is_symlink():
                    all_findings.extend(scan_file(fpath, rule_list))
            except (OSError, PermissionError) as exc:
                _warn(f"Error accessing {fpath}: {exc}")
                continue

    return all_findings
