"""Regression tests for the offline-first CLI and signed report bundles."""

from __future__ import annotations

import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from api.services.report_bundle import public_key_to_base64, verify_bundle
from scanner.cli import main


def _weak_python_fixture(path):
    path.write_text("import hashlib\nhashlib.md5(b'example')\n", encoding="utf-8")


def test_fail_on_returns_ci_policy_exit_code(tmp_path):
    source = tmp_path / "legacy.py"
    _weak_python_fixture(source)

    assert main([str(source), "--fail-on", "CRITICAL"]) == 2
    assert main([str(source), "--fail-on", "LOW"]) == 2
    assert main([str(source), "--fail-on", "CRITICAL", "--summary-only"]) == 2


def test_signed_bundle_is_verifiable_and_contains_scored_findings(tmp_path):
    source = tmp_path / "legacy.py"
    _weak_python_fixture(source)
    signing_key = Ed25519PrivateKey.generate()
    key_path = tmp_path / "agent-ed25519.pem"
    key_path.write_bytes(
        signing_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    bundle_path = tmp_path / "report.ecdat.json"

    assert main([
        str(source), "--report-bundle", str(bundle_path),
        "--organization-id", "org-demo", "--repository-id", "repo-demo",
        "--agent-id", "agent-demo", "--signing-key", str(key_path),
        "--data-shelf-life-years", "20",
    ]) == 0

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    verified = verify_bundle(bundle, public_key_to_base64(signing_key))
    assert verified["organization_id"] == "org-demo"
    assert verified["findings"][0]["risk_tier"] == "CRITICAL"
    assert verified["findings"][0]["data_shelf_life_years"] == 20
    assert verified["findings"][0]["source_context"] == "SOURCE"


def test_sync_rejects_insecure_http_endpoint(tmp_path):
    source = tmp_path / "legacy.py"
    _weak_python_fixture(source)
    signing_key = Ed25519PrivateKey.generate()
    key_path = tmp_path / "agent-ed25519.pem"
    key_path.write_bytes(
        signing_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )

    assert main([
        str(source), "--report-bundle", str(tmp_path / "report.json"),
        "--organization-id", "org-demo", "--repository-id", "repo-demo",
        "--agent-id", "agent-demo", "--signing-key", str(key_path),
        "--sync-url", "http://dashboard.invalid/agent/v1/report-bundles",
        "--client-cert", "client.pem", "--client-key", "client-key.pem",
    ]) == 1


def test_explicit_source_context_overrides_path_guessing(tmp_path):
    source = tmp_path / "legacy.py"
    _weak_python_fixture(source)

    assert main([str(source), "--source-context", "DEMO_ONLY"]) == 0
