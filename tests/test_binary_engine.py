"""
tests/test_binary_engine.py — Unit tests for scanner/binary_engine.py (BIN feature).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scanner import binary_engine
from scanner.binary_engine import scan_directory, scan_file
from scanner.constants import SCAN_MAX_ARTIFACT_BYTES

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "binaries"


def test_tier1_symbol_hit_high_confidence():
    """Tier 1: Linked symbols in dynamic symbol table emit high-confidence findings."""
    elf_path = FIXTURES_DIR / "libcrypto_positive.elf"
    findings = scan_file(elf_path)
    assert len(findings) > 0

    tier1 = [f for f in findings if f.detection_method == "binary_symbol_table"]
    assert len(tier1) >= 2

    algos = [f.algorithm for f in tier1]
    assert "MD5" in algos
    assert "AES" in algos

    for f in tier1:
        assert f.confidence == "high"
        assert f.confidence_band == "VERIFIED"
        assert f.confidence_score >= 0.85
        assert f.line == 0
        assert f.language == "elf"
        assert ".dynsym:" in f.matched_call or ".symtab:" in f.matched_call


def test_tier2_constant_hit_unverified_confidence():
    """Tier 2: Byte constant matches in .rodata emit unverified-confidence findings."""
    elf_path = FIXTURES_DIR / "libcrypto_positive.elf"
    findings = scan_file(elf_path)

    tier2 = [f for f in findings if f.detection_method == "binary_constant_scan"]
    assert len(tier2) >= 1

    algos = [f.algorithm for f in tier2]
    assert "AES" in algos

    for f in tier2:
        assert f.confidence == "unverified"
        assert f.confidence_band == "UNVERIFIED"
        assert f.line == 0
        assert "+0x" in f.matched_call


def test_no_finding_on_unrelated_binary():
    """Clean ELF binaries without crypto symbols or constants emit zero findings."""
    clean_elf = FIXTURES_DIR / "clean_decoy.elf"
    findings = scan_file(clean_elf)
    assert findings == []


def test_unsupported_format_returns_empty_list():
    """Non-binary files (e.g., text files) return an empty list without raising."""
    decoy = FIXTURES_DIR / "adversarial_decoy.bin"
    findings = scan_file(decoy)
    assert findings == []


def test_oversized_file_is_skipped(tmp_path, capsys):
    """Binaries exceeding SCAN_MAX_ARTIFACT_BYTES are skipped with a stderr warning."""
    huge_file = tmp_path / "huge.elf"
    # Write ELF header + dummy bytes exceeding limit
    with open(huge_file, "wb") as f:
        f.write(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8)
        f.seek(SCAN_MAX_ARTIFACT_BYTES + 1024)
        f.write(b"\x00")

    findings = scan_file(huge_file)
    assert findings == []

    err = capsys.readouterr().err
    assert "[warn]" in err
    assert "exceeds size limit" in err


def test_pe_binary_scanning_symbols_and_constants():
    """PE executables (.exe/.dll) are scanned for imported crypto symbols and constants."""
    pe_path = FIXTURES_DIR / "crypto_sample.exe"
    findings = scan_file(pe_path)
    assert len(findings) > 0

    tier1 = [f for f in findings if f.detection_method == "binary_symbol_table"]
    tier2 = [f for f in findings if f.detection_method == "binary_constant_scan"]

    assert len(tier1) >= 2
    algos_t1 = [f.algorithm for f in tier1]
    assert "MD5" in algos_t1
    assert "DES" in algos_t1

    for f in tier1:
        assert f.confidence == "high"
        assert f.language == "pe"

    assert len(tier2) >= 1
    assert any(f.algorithm == "AES" for f in tier2)


def test_pe_clean_binary_no_findings():
    """Clean PE binaries with standard Win32 imports emit zero findings."""
    clean_pe = FIXTURES_DIR / "clean_sample.exe"
    findings = scan_file(clean_pe)
    assert findings == []


def test_scan_directory_aggregates_fixtures():
    """scan_directory recursively finds and scans all binaries in the tree."""
    findings = scan_directory(FIXTURES_DIR)
    assert len(findings) >= 5

    files_found = {Path(f.file).name for f in findings}
    assert "libcrypto_positive.elf" in files_found
    assert "crypto_sample.exe" in files_found
    assert "clean_decoy.elf" not in files_found
    assert "clean_sample.exe" not in files_found


def test_scan_directory_skips_binary_skip_dirs(tmp_path):
    """scan_directory ignores directories listed in BINARY_SKIP_DIRS."""
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    hidden_elf = node_modules / "libcrypto.elf"
    hidden_elf.write_bytes((FIXTURES_DIR / "libcrypto_positive.elf").read_bytes())

    normal_dir = tmp_path / "bin"
    normal_dir.mkdir()
    visible_elf = normal_dir / "libcrypto.elf"
    visible_elf.write_bytes((FIXTURES_DIR / "libcrypto_positive.elf").read_bytes())

    findings = scan_directory(tmp_path)
    assert len(findings) > 0
    for f in findings:
        assert "node_modules" not in f.file


def test_corrupt_binary_handling(tmp_path, capsys):
    """Truncated/corrupt binaries log a warning and return empty findings without crashing."""
    corrupt_elf = tmp_path / "corrupt.elf"
    corrupt_elf.write_bytes(b"\x7fELF\x02\x01\x01\x00\xff\xff\xff\xff")

    findings = scan_file(corrupt_elf)
    assert findings == []


def test_custom_rules_override(tmp_path):
    """Passing custom rules overrides the default rule pack."""
    custom_rules = [
        {
            "tier": 1,
            "match_type": "symbol",
            "match_pattern": "MD5_Init",
            "algorithm": "CUSTOM_MD5",
            "primitive": "hash",
            "library": "custom_lib",
            "weak_by_default": True,
        }
    ]
    elf_path = FIXTURES_DIR / "libcrypto_positive.elf"
    findings = scan_file(elf_path, rules=custom_rules)
    assert len(findings) == 1
    assert findings[0].algorithm == "CUSTOM_MD5"


def test_lief_engine_if_available():
    """If lief is installed, verify lief parser execution."""
    lief = pytest.importorskip("lief")
    elf_path = FIXTURES_DIR / "libcrypto_positive.elf"
    findings = scan_file(elf_path)
    assert len(findings) > 0


def test_cli_binary_scan_disabled_by_default(monkeypatch, capsys):
    """If SCAN_ENABLE_BINARY is false/unset, CLI exits 1 with an explicit error message."""
    from scanner.cli import main
    monkeypatch.delenv("SCAN_ENABLE_BINARY", raising=False)
    with pytest.raises(SystemExit) as exc:
        main([str(FIXTURES_DIR), "--scan-type", "binary"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "SCAN_ENABLE_BINARY is not enabled" in err


def test_cli_binary_scan_enabled(monkeypatch, capsys):
    """With SCAN_ENABLE_BINARY=true, CLI emits JSON array with artifact_type=BINARY."""
    import json
    from scanner.cli import main
    monkeypatch.setenv("SCAN_ENABLE_BINARY", "true")
    exit_code = main([str(FIXTURES_DIR), "--scan-type", "binary"])
    assert exit_code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) > 0
    for finding in data:
        assert finding["artifact_type"] == "BINARY"
        assert finding["artifact_ref"] != ""
        assert finding["detection_method"] in ("binary_symbol_table", "binary_constant_scan")


def test_cli_binary_scan_min_confidence(monkeypatch, capsys):
    """--min-confidence PROBABLE filters out UNVERIFIED tier-2 constant findings."""
    import json
    from scanner.cli import main
    monkeypatch.setenv("SCAN_ENABLE_BINARY", "true")
    exit_code = main([str(FIXTURES_DIR), "--scan-type", "binary", "--min-confidence", "PROBABLE"])
    assert exit_code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) > 0
    for finding in data:
        assert finding["confidence_band"] in ("VERIFIED", "PROBABLE")
        assert finding["detection_method"] == "binary_symbol_table"


def test_cli_binary_scan_fail_on(monkeypatch):
    """--fail-on CRITICAL returns 2 if critical findings exist."""
    from scanner.cli import main
    monkeypatch.setenv("SCAN_ENABLE_BINARY", "true")
    exit_code = main([str(FIXTURES_DIR), "--scan-type", "binary", "--fail-on", "CRITICAL"])
    assert exit_code == 2
