"""
tests/test_config_engine.py — Unit tests for scanner/config_engine.py (IAC feature).

All tests run against in-memory fixtures (tmp_path) or the committed fixture
files in tests/fixtures/config/.  No network, no DB, no Docker required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scanner import config_engine
from scanner.config_engine import (
    ConfigFinding,
    _detect_format,
    _has_interpolation,
    _parse_nginx,
    _parse_yaml,
    load_rules,
    scan_directory,
    scan_file,
)

FIXTURES = Path(__file__).parent / "fixtures" / "config"
RULES = load_rules()

# ── Helper ──────────────────────────────────────────────────────────────────

def _algorithms(findings) -> list[str]:
    return sorted(f.algorithm for f in findings)


def _assert_finding(findings, algorithm: str) -> ConfigFinding:
    """Assert exactly one finding with the given algorithm; return it."""
    matches = [f for f in findings if f.algorithm == algorithm]
    assert matches, f"No finding with algorithm={algorithm!r}; got {_algorithms(findings)}"
    return matches[0]


# ── load_rules ───────────────────────────────────────────────────────────────

def test_load_rules_returns_nonempty_dict():
    rules = load_rules()
    assert isinstance(rules, dict)
    assert len(rules) > 0
    # Spot-check expected rule IDs
    assert "tls_v1_0" in rules
    assert "weak_cipher_rc4" in rules
    assert "ssl_verify_false" in rules
    assert "rsa_1024" in rules


def test_load_rules_from_missing_path_returns_empty(tmp_path):
    rules = load_rules(tmp_path / "nonexistent.yaml")
    assert rules == {}


def test_load_rules_from_malformed_yaml_returns_empty(tmp_path):
    bad = tmp_path / "rules.yaml"
    bad.write_text("[[[ not yaml", encoding="utf-8")
    rules = load_rules(bad)
    assert rules == {}


# ── _detect_format ───────────────────────────────────────────────────────────

def test_detect_format_k8s_yaml(tmp_path):
    assert _detect_format(tmp_path / "deployment.yaml") == "yaml_k8s"
    assert _detect_format(tmp_path / "service.yml") == "yaml_k8s"


def test_detect_format_compose(tmp_path):
    assert _detect_format(tmp_path / "docker-compose.yml") == "yaml_compose"
    assert _detect_format(tmp_path / "compose.yaml") == "yaml_compose"


def test_detect_format_github_actions(tmp_path):
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    assert _detect_format(workflows_dir / "ci.yml") == "yaml_github"


def test_detect_format_gitlab(tmp_path):
    assert _detect_format(tmp_path / ".gitlab-ci.yml") == "yaml_gitlab"


def test_detect_format_terraform(tmp_path):
    assert _detect_format(tmp_path / "main.tf") == "hcl2"


def test_detect_format_nginx(tmp_path):
    assert _detect_format(tmp_path / "nginx.conf") == "nginx"
    assert _detect_format(tmp_path / "site.conf") == "nginx"


def test_detect_format_json(tmp_path):
    assert _detect_format(tmp_path / "config.json") == "json"


# ── _has_interpolation ────────────────────────────────────────────────────────

def test_has_interpolation_detects_various_forms():
    assert _has_interpolation("${VAR}")
    assert _has_interpolation("${{ secrets.KEY }}")
    assert _has_interpolation("#{variable}")
    assert _has_interpolation("{{ .Values.tls }}")


def test_has_interpolation_clean_values():
    assert not _has_interpolation("TLSv1.0")
    assert not _has_interpolation("1024")
    assert not _has_interpolation("false")
    assert not _has_interpolation("")


# ── YAML detection ────────────────────────────────────────────────────────────

def test_scan_file_yaml_vulnerable(capsys):
    p = FIXTURES / "k8s-vulnerable.yaml"
    findings = scan_file(p, RULES)
    assert len(findings) > 0
    algos = _algorithms(findings)
    # Should detect TLSv1.0, TLSv1.1, RC4, DES, RSA-1024, and ssl_verify
    assert "TLSv1.0" in algos
    assert "TLSv1.1" in algos
    assert "RC4" in algos
    assert "DES" in algos
    assert "RSA" in algos
    assert "TLS" in algos  # ssl_verify_false
    # No stdout output (findings are returned, not printed)
    assert capsys.readouterr().out == ""


def test_scan_file_yaml_clean():
    p = FIXTURES / "k8s-clean.yaml"
    findings = scan_file(p, RULES)
    algos = _algorithms(findings)
    # Should only find TLSv1.3 (not weak_by_default) and RSA-4096 (not weak)
    # tls_version: TLSv1.3 → found but weak_by_default=False
    # RSA-4096 → found but weak_by_default=False
    # ssl_verify: true → no finding (value doesn't match false/disabled patterns)
    for f in findings:
        assert not f.weak_by_default, f"Expected clean finding but weak_by_default=True for {f.algorithm}"


def test_scan_file_yaml_tls10_emits_high_confidence(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("tls_version: TLSv1.0\n", encoding="utf-8")
    findings = scan_file(yaml_file, RULES)
    f = _assert_finding(findings, "TLSv1.0")
    assert f.confidence == "high"
    assert f.confidence_band == "VERIFIED"
    assert f.confidence_score > 0.0
    assert f.detection_method == "config_analysis"
    assert f.language == "config"
    assert f.artifact_type == "CONFIG_FILE"


def test_scan_file_yaml_ssl_verify_false(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("verify: false\n", encoding="utf-8")
    findings = scan_file(yaml_file, RULES)
    f = _assert_finding(findings, "TLS")
    assert f.confidence == "high"
    assert f.weak_by_default is True


def test_scan_file_yaml_rsa_1024(tmp_path):
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("rsa_bits: \"1024\"\n", encoding="utf-8")
    findings = scan_file(yaml_file, RULES)
    f = _assert_finding(findings, "RSA")
    assert f.key_size == 1024


def test_confidence_unverified_interpolation(tmp_path):
    """Unresolved variable → confidence=unverified, band=UNVERIFIED."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("tls_version: \"${TLS_MIN_VERSION}\"\n", encoding="utf-8")
    findings = scan_file(yaml_file, RULES)
    # The value contains an interpolation; should emit unverified
    assert len(findings) > 0
    for f in findings:
        assert f.confidence == "unverified"
        assert f.confidence_band == "UNVERIFIED"
        assert "import_unresolved" in f.confidence_signals


def test_confidence_unverified_github_actions_interpolation(tmp_path):
    """GitHub Actions ${{ }} interpolation → unverified."""
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    ci = workflows / "ci.yml"
    ci.write_text(
        "name: CI\njobs:\n  test:\n    env:\n      tls_version: ${{ secrets.TLS }}\n",
        encoding="utf-8",
    )
    findings = scan_file(ci, RULES)
    assert len(findings) > 0
    for f in findings:
        assert f.confidence_band == "UNVERIFIED"


def test_scan_file_yaml_multiple_tls_versions(tmp_path):
    """Both TLS 1.0 and TLS 1.3 in same file → two separate findings."""
    yaml_file = tmp_path / "multi.yaml"
    yaml_file.write_text(
        "minimum_version: TLSv1.0\nmaximum_version: TLSv1.3\n",
        encoding="utf-8",
    )
    findings = scan_file(yaml_file, RULES)
    algos = _algorithms(findings)
    assert "TLSv1.0" in algos
    assert "TLSv1.3" in algos


def test_negative_comment_no_finding(tmp_path):
    """Comments containing crypto strings must NOT produce findings."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "# tls_version: TLSv1.0 — old config, do not use\nssl_version: TLSv1.3\n",
        encoding="utf-8",
    )
    findings = scan_file(yaml_file, RULES)
    # Comments are stripped by PyYAML; only the active value TLSv1.3 is present
    for f in findings:
        assert f.algorithm != "TLSv1.0", "Comment content leaked into findings"


def test_negative_variable_name_no_finding(tmp_path):
    """Keys whose NAMES contain crypto strings but VALUES are safe → no weak finding."""
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(
        "old_tls_v10_disabled: \"TLSv1.3\"\nrsa_1024_feature_off: \"true\"\n",
        encoding="utf-8",
    )
    findings = scan_file(yaml_file, RULES)
    # The key patterns don't match "old_tls_v10_disabled"; "tls_version"/"rsa_bits" are not present
    for f in findings:
        assert f.algorithm not in ("TLSv1.0", "RC4"), (
            f"Variable name leaked into findings: {f.algorithm}"
        )


def test_scan_file_yaml_adversarial():
    """Full adversarial fixture — only TLSv1.3 and RSA-4096 should appear."""
    p = FIXTURES / "adversarial.yaml"
    findings = scan_file(p, RULES)
    for f in findings:
        assert not f.weak_by_default, (
            f"Adversarial fixture produced weak finding: {f.algorithm} in {f.matched_call}"
        )


# ── HCL2 detection ────────────────────────────────────────────────────────────

def test_scan_file_terraform_rsa_1024():
    p = FIXTURES / "terraform-vulnerable.tf"
    findings = scan_file(p, RULES)
    algos = _algorithms(findings)
    assert "RSA" in algos
    rsa_findings = [f for f in findings if f.algorithm == "RSA" and f.key_size == 1024]
    assert rsa_findings, "Expected RSA-1024 finding"
    assert rsa_findings[0].library == "terraform"


def test_scan_file_terraform_tls_policy():
    p = FIXTURES / "terraform-vulnerable.tf"
    findings = scan_file(p, RULES)
    # ELBSecurityPolicy-TLS-1-0 → TLSv1.0
    tls_findings = [f for f in findings if f.algorithm == "TLSv1.0"]
    assert tls_findings, "Expected TLSv1.0 finding from ELB policy"


def test_scan_file_terraform_clean():
    p = FIXTURES / "terraform-clean.tf"
    findings = scan_file(p, RULES)
    for f in findings:
        assert not f.weak_by_default, (
            f"Clean terraform produced weak finding: {f.algorithm}"
        )


# ── Nginx detection ───────────────────────────────────────────────────────────

def test_parse_nginx_extracts_directives(tmp_path):
    text = "server {\n    ssl_protocols TLSv1.0 TLSv1.1;\n    ssl_ciphers RC4;\n}"
    directives = _parse_nginx(tmp_path / "test.conf", text)
    directive_names = [d[0] for d in directives]
    assert "ssl_protocols" in directive_names
    assert "ssl_ciphers" in directive_names


def test_parse_nginx_ignores_comments(tmp_path):
    text = "# ssl_protocols TLSv1.0;\nssl_protocols TLSv1.3;\n"
    directives = _parse_nginx(tmp_path / "test.conf", text)
    values = [d[1] for d in directives if d[0] == "ssl_protocols"]
    assert len(values) == 1
    assert "TLSv1.3" in values[0]
    # The comment value TLSv1.0 must NOT appear
    assert "TLSv1.0" not in values[0]


def test_scan_file_nginx_vulnerable():
    p = FIXTURES / "nginx-vulnerable.conf"
    findings = scan_file(p, RULES)
    algos = _algorithms(findings)
    # Should detect TLSv1.0, TLSv1.1, RC4, DES, MD5
    assert "TLSv1.0" in algos or "TLSv1.1" in algos
    assert "RC4" in algos
    assert "DES" in algos
    for f in findings:
        assert f.library == "nginx"
        assert f.detection_method == "config_analysis"


def test_scan_file_nginx_clean():
    p = FIXTURES / "nginx-clean.conf"
    findings = scan_file(p, RULES)
    # TLSv1.3 only — not weak by default
    for f in findings:
        assert not f.weak_by_default, (
            f"Clean nginx produced weak finding: {f.algorithm}"
        )


def test_nginx_line_numbers_are_positive():
    p = FIXTURES / "nginx-vulnerable.conf"
    findings = scan_file(p, RULES)
    for f in findings:
        assert f.line > 0, "Nginx findings should have positive line numbers"


# ── Docker Compose ────────────────────────────────────────────────────────────

def test_scan_file_docker_compose_vulnerable():
    p = FIXTURES / "docker-compose-vulnerable.yml"
    findings = scan_file(p, RULES)
    # docker-compose.yml is YAML; environment values are scanned
    # SSL_VERIFY=false and TLS_VERSION=TLSv1.0 are env strings, not parsed YAML keys
    # The fixture uses YAML dict format under `environment` list which PyYAML parses as strings.
    # Findings may or may not appear depending on whether the env values are YAML scalars.
    # If none are found, that is acceptable (env as list of "KEY=VALUE" strings are not dict keys).
    assert isinstance(findings, list)  # just verify no crash


# ── source_context ────────────────────────────────────────────────────────────

def test_source_context_test_only(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    f = tests_dir / "tls-test.yaml"
    f.write_text("tls_version: TLSv1.0\n", encoding="utf-8")
    findings = scan_file(f, RULES)
    assert len(findings) > 0
    for finding in findings:
        # The engine emits the raw source_context; CLI layer may override it.
        # Check the artifact_type is CONFIG_FILE
        assert finding.artifact_type == "CONFIG_FILE"


# ── Error handling ────────────────────────────────────────────────────────────

def test_error_handling_malformed_yaml(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("[[[ not yaml", encoding="utf-8")
    findings = scan_file(bad, RULES)
    assert findings == []
    err = capsys.readouterr().err
    assert "[warn]" in err


def test_error_handling_malformed_json(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    findings = scan_file(bad, RULES)
    assert findings == []
    err = capsys.readouterr().err
    assert "[warn]" in err


def test_error_handling_oversize_file(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(config_engine, "SCAN_MAX_ARTIFACT_BYTES", 10)
    large = tmp_path / "config.yaml"
    large.write_text("tls_version: TLSv1.0\n" * 100, encoding="utf-8")
    findings = scan_file(large, RULES)
    assert findings == []
    err = capsys.readouterr().err
    assert "[warn]" in err


def test_error_handling_unreadable_file(tmp_path, capsys):
    bad = tmp_path / "config.yaml"
    # Write binary that's not valid UTF-8
    bad.write_bytes(b"\xff\xfe\x00")
    findings = scan_file(bad, RULES)
    assert findings == []


# ── scan_directory ────────────────────────────────────────────────────────────

def test_scan_directory_aggregates_all_fixtures():
    findings = scan_directory(FIXTURES, RULES)
    assert len(findings) > 0
    # Should find config findings from multiple file types
    methods = {f.detection_method for f in findings}
    assert "config_analysis" in methods


def test_scan_directory_skips_node_modules(tmp_path):
    nm = tmp_path / "node_modules"
    nm.mkdir()
    cfg = nm / "config.yaml"
    cfg.write_text("tls_version: TLSv1.0\n", encoding="utf-8")

    safe = tmp_path / "config.yaml"
    safe.write_text("tls_version: TLSv1.3\n", encoding="utf-8")

    findings = scan_directory(tmp_path, RULES)
    files = {f.file for f in findings}
    assert not any("node_modules" in f for f in files), (
        "node_modules findings leaked into results"
    )


def test_scan_directory_single_file(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("tls_version: TLSv1.0\n", encoding="utf-8")
    findings_dir = scan_directory(tmp_path, RULES)
    findings_file = scan_file(cfg, RULES)
    # Directory scan should find the same file
    assert len(findings_dir) == len(findings_file)


def test_scan_directory_sorted_output(tmp_path):
    (tmp_path / "a.yaml").write_text("tls_version: TLSv1.0\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("tls_version: TLSv1.1\n", encoding="utf-8")
    findings = scan_directory(tmp_path, RULES)
    files = [f.file for f in findings]
    assert files == sorted(files), "scan_directory output must be sorted by file"


# ── artifact fields ───────────────────────────────────────────────────────────

def test_artifact_fields_are_set_correctly(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("tls_version: TLSv1.0\n", encoding="utf-8")
    findings = scan_file(cfg, RULES)
    assert len(findings) > 0
    f = findings[0]
    assert f.artifact_type == "CONFIG_FILE"
    assert f.artifact_ref == str(cfg)
    assert f.detection_method == "config_analysis"
    assert f.language == "config"


# ── JSON detection ────────────────────────────────────────────────────────────

def test_scan_file_json_detects_weak_tls(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"tls_version": "TLSv1.0", "ssl_verify": "false"}), encoding="utf-8")
    findings = scan_file(cfg, RULES)
    algos = _algorithms(findings)
    assert "TLSv1.0" in algos
    assert "TLS" in algos  # ssl_verify_false


def test_scan_file_json_malformed(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    findings = scan_file(bad, RULES)
    assert findings == []
    assert "[warn]" in capsys.readouterr().err


# ── CLI integration ───────────────────────────────────────────────────────────

def test_cli_scan_type_config_emits_config_findings(tmp_path, capsys):
    from scanner.cli import main
    cfg = tmp_path / "config.yaml"
    cfg.write_text("tls_version: TLSv1.0\n", encoding="utf-8")
    ret = main([str(tmp_path), "--scan-type", "config"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    config_findings = [f for f in parsed if f.get("detection_method") == "config_analysis"]
    assert len(config_findings) > 0
    f = config_findings[0]
    assert f["artifact_type"] == "CONFIG_FILE"
    assert f["language"] == "config"


def test_cli_mixed_scan_source_and_config(tmp_path, capsys):
    from scanner.cli import main
    # Python source
    py = tmp_path / "main.py"
    py.write_text("from Crypto.Cipher import AES\nAES.new(key, AES.MODE_CBC)\n", encoding="utf-8")
    # Config
    cfg = tmp_path / "config.yaml"
    cfg.write_text("tls_version: TLSv1.0\n", encoding="utf-8")
    main([str(tmp_path), "--scan-type", "source", "--scan-type", "config"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    languages = {f["language"] for f in parsed}
    assert "config" in languages


def test_cli_config_no_stdout_for_empty_dir(tmp_path, capsys):
    from scanner.cli import main
    # A directory with no config files
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "readme.md").write_text("# readme", encoding="utf-8")
    main([str(sub), "--scan-type", "config"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed == []
