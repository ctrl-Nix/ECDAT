"""End-to-end tests for signed offline report intake and persisted PQC evidence."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from api.core.config import settings
from api.database import get_session
from api.main import app
from api.services.report_bundle import build_bundle, public_key_to_base64, sign_bundle
from api.services.risk_engine import score_findings
from db.models import Base


def _bundle(private_key: Ed25519PrivateKey) -> dict:
    findings = score_findings([{
        "file": "src/auth.py", "line": 12, "matched_call": "hashlib.md5(data)",
        "library": "hashlib", "algorithm": "MD5", "primitive": "hash",
        "language": "python", "weak_by_default": True, "confidence": "high",
        "detection_method": "python_ast", "data_shelf_life_years": 20,
        "assumption_source": "test-profile",
    }, {
        "file": "src/keys.ts", "line": 7, "matched_call": "generateKeyPair('rsa')",
        "library": "node:crypto", "algorithm": "RSA", "primitive": "asymmetric",
        "language": "typescript", "weak_by_default": False, "confidence": "high",
        "detection_method": "tree_sitter", "data_shelf_life_years": 20,
        "assumption_source": "test-profile",
    }])
    payload = build_bundle(
        organization_id="org-example", repository_id="payments-api", agent_id="agent-001",
        findings=findings,
        summary={"total": 2, "CRITICAL": 1, "HIGH": 1, "MEDIUM": 0, "LOW": 0, "UNSCORED": 0},
        scan_context={"scanner_mode": "offline_local", "source_root": "payments-api", "path_redaction": True},
    )
    return sign_bundle(payload, private_key)


def test_signed_report_sync_persists_pqc_evidence_and_cbom(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(settings, "REPORT_SYNC_AGENT_KEYS", {"agent-001": public_key_to_base64(private_key)})
    monkeypatch.setattr(settings, "REPORT_SYNC_REQUIRE_MTLS", True)
    monkeypatch.setattr(settings, "API_KEY", "test-api-key")

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    bundle = _bundle(private_key)
    headers = {"X-ECDAT-Agent-ID": "agent-001", "X-ECDAT-mTLS-Verified": "SUCCESS"}
    try:
        response = client.post("/agent/v1/report-bundles", json=bundle, headers=headers)
        assert response.status_code == 201
        accepted = response.json()
        assert accepted["accepted"] is True
        assert accepted["bundle_digest"] == bundle["bundle_digest"]

        replay = client.post("/agent/v1/report-bundles", json=bundle, headers=headers)
        assert replay.status_code == 201
        assert replay.json()["accepted"] is False

        scan = client.get(f"/scans/{accepted['scan_id']}", headers={"X-API-Key": "test-api-key"})
        assert scan.status_code == 200
        rsa = next(item for item in scan.json()["findings"] if item["algorithm"] == "RSA")
        assert rsa["risk_assessment"]["quantum_vulnerable"] is True
        assert rsa["risk_assessment"]["hndl_exposure"] == "HIGH"

        cbom = client.get(f"/scans/{accepted['scan_id']}/cbom", headers={"X-API-Key": "test-api-key"})
        assert cbom.status_code == 200
        body = cbom.json()
        assert body["x-ecdat-report-provenance"]["bundle_digest"] == bundle["bundle_digest"]
        rsa_component = next(item for item in body["components"] if item["name"] == "RSA")
        props = {item["name"]: item["value"] for item in rsa_component["properties"]}
        assert props["ecdat:quantum_vulnerable"] == "true"
        assert props["ecdat:hndl_exposure"] == "HIGH"
    finally:
        app.dependency_overrides.clear()


def test_sync_rejects_unsigned_or_tampered_bundle(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    private_key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(settings, "REPORT_SYNC_AGENT_KEYS", {"agent-001": public_key_to_base64(private_key)})
    monkeypatch.setattr(settings, "REPORT_SYNC_REQUIRE_MTLS", True)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    bundle = _bundle(private_key)
    bundle["organization_id"] = "tampered-org"
    try:
        response = client.post(
            "/agent/v1/report-bundles", json=bundle,
            headers={"X-ECDAT-Agent-ID": "agent-001", "X-ECDAT-mTLS-Verified": "SUCCESS"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
