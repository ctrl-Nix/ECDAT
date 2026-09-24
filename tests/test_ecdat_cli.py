from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scanner import ecdat_cli


def _findings_and_summary():
    findings = [
        {
            "file": "src/crypto.py",
            "line": 42,
            "library": "cryptography",
            "algorithm": "RSA",
            "confidence": "high",
            "confidence_band": "VERIFIED",
            "confidence_score": 0.98,
            "risk_tier": "HIGH",
            "risk_reason": "RSA is quantum-vulnerable.",
            "primitive": "pke",
            "criticality": "HIGH",
            "detection_method": "ast_visitor",
        }
    ]
    summary = {
        "total": 1,
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 0,
        "LOW": 0,
        "UNSCORED": 0,
    }
    return findings, summary


def test_cmd_scan_integration(tmp_path):
    target = tmp_path / "crypto_file.py"
    target.write_text(
        "from cryptography.hazmat.primitives.asymmetric import rsa\n",
        encoding="utf-8",
    )

    result = ecdat_cli.main(["scan", str(target)])

    assert result in (0, 2)


def test_cmd_scan_delegates_flags_and_preserves_policy_exit_code(monkeypatch, tmp_path):
    captured = {}

    def fake_main(argv):
        captured["argv"] = argv
        return 2

    monkeypatch.setattr(ecdat_cli.scanner_cli, "main", fake_main)
    target = tmp_path / "target.py"
    args = ecdat_cli.build_parser().parse_args(
        [
            "scan",
            str(target),
            "--scan-type",
            "source",
            "--scan-type",
            "dependency",
            "--fail-on",
            "HIGH",
            "--summary-only",
            "--min-confidence",
            "PROBABLE",
        ]
    )

    assert ecdat_cli.cmd_scan(args) == 2
    assert captured["argv"] == [
        str(target),
        "--scan-type",
        "source",
        "--scan-type",
        "dependency",
        "--min-confidence",
        "PROBABLE",
        "--summary-only",
        "--fail-on",
        "HIGH",
        "--sync-timeout",
        "15.0",
    ]


def test_cmd_cbom_db_free(tmp_path, capsys):
    findings, summary = _findings_and_summary()
    findings_file = tmp_path / "findings.json"
    summary_file = tmp_path / "summary.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")
    summary_file.write_text(json.dumps(summary), encoding="utf-8")

    result = ecdat_cli.main(
        ["cbom", str(findings_file), "--summary", str(summary_file), "--organization-id", "org-1"]
    )

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["bomFormat"] == "CycloneDX"
    assert output["specVersion"] == "1.6"
    assert output["components"][0]["name"] == "RSA"
    assert output["metadata"]["properties"][0]["value"] == "org-1"


def test_cmd_cbom_writes_output_file(tmp_path, capsys):
    findings, summary = _findings_and_summary()
    findings_file = tmp_path / "findings.json"
    summary_file = tmp_path / "summary.json"
    output_file = tmp_path / "result.cdx.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")
    summary_file.write_text(json.dumps(summary), encoding="utf-8")

    result = ecdat_cli.main(
        ["cbom", str(findings_file), "--summary", str(summary_file), "--output", str(output_file)]
    )

    assert result == 0
    assert capsys.readouterr().out == ""
    assert json.loads(output_file.read_text(encoding="utf-8"))["components"]


def test_cmd_cbom_invalid_json_fails_cleanly(tmp_path, capsys):
    findings_file = tmp_path / "findings.json"
    summary_file = tmp_path / "summary.json"
    findings_file.write_text("{not json", encoding="utf-8")
    summary_file.write_text("{}", encoding="utf-8")

    result = ecdat_cli.main(["cbom", str(findings_file), "--summary", str(summary_file)])

    captured = capsys.readouterr()
    assert result == 1
    assert "CBOM generation failed" in captured.err
    assert captured.out == ""


def test_cmd_sync_https_validation(tmp_path, capsys):
    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text('{"agent_id":"agent-1"}', encoding="utf-8")

    result = ecdat_cli.main(
        [
            "sync",
            str(bundle_file),
            "--url",
            "http://example.invalid/intake",
            "--client-cert",
            "client.pem",
            "--client-key",
            "client-key.pem",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "https://" in captured.err
    assert captured.out == ""


def test_cmd_sync_posts_signed_bundle_with_mtls(tmp_path, monkeypatch, capsys):
    bundle_file = tmp_path / "bundle.json"
    bundle = {"agent_id": "agent-1", "signature": "signed"}
    bundle_file.write_text(json.dumps(bundle), encoding="utf-8")
    tls_context = SimpleNamespace(load_cert_chain=lambda **_kwargs: None)
    monkeypatch.setattr(ecdat_cli.ssl, "create_default_context", lambda **_kwargs: tls_context)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status": "accepted"}

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["verify"] is tls_context
            assert kwargs["follow_redirects"] is False
            assert kwargs["trust_env"] is False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **kwargs):
            assert url == "https://example.invalid/intake"
            assert kwargs["json"] == bundle
            assert kwargs["headers"]["X-ECDAT-Agent-ID"] == "agent-1"
            return FakeResponse()

    monkeypatch.setattr(ecdat_cli.httpx, "Client", FakeClient)
    result = ecdat_cli.main(
        [
            "sync",
            str(bundle_file),
            "--url",
            "https://example.invalid/intake",
            "--client-cert",
            "client.pem",
            "--client-key",
            "client-key.pem",
        ]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {"status": "accepted"}


def test_ecdat_main_subcommand_dispatch(monkeypatch, tmp_path):
    called = []

    def fake_cbom(args):
        called.append(args.subcommand)
        return 7

    monkeypatch.setattr(ecdat_cli, "cmd_cbom", fake_cbom)
    findings_file = tmp_path / "findings.json"
    summary_file = tmp_path / "summary.json"

    result = ecdat_cli.main(
        ["cbom", str(findings_file), "--summary", str(summary_file)]
    )

    assert result == 7
    assert called == ["cbom"]
