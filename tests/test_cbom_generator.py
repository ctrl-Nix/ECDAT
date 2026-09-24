from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.services import cbom_generator


def _finding(**overrides):
    finding = {
        "file": "src/crypto.py",
        "line": 12,
        "library": "cryptography",
        "algorithm": "RSA",
        "confidence": "high",
        "risk_tier": "HIGH",
        "risk_reason": "Quantum-vulnerable public key algorithm.",
        "primitive": "pke",
        "criticality": "HIGH",
        "key_size": 2048,
        "source_context": "SOURCE",
        "confidence_band": "VERIFIED",
        "confidence_score": 0.98,
        "detection_method": "ast_visitor",
        "artifact_type": "SOURCE_FILE",
        "risk_model_version": "2026.1",
        "classical_broken": False,
        "quantum_vulnerable": True,
        "hndl_exposure": "HIGH",
        "recommended_replacement": "ML-KEM",
        "recommendation_type": "quantum",
        "migration_effort_days": 5,
        "data_shelf_life_years": 10,
        "quantum_threat_horizon_years": 12,
        "assumption_source": "test fixture",
    }
    finding.update(overrides)
    return finding


def test_build_cbom_from_findings_is_database_free_and_maps_scored_values():
    summary = {
        "total": 1,
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 0,
        "LOW": 0,
        "UNSCORED": 0,
    }

    result = cbom_generator.build_cbom_from_findings(
        [_finding(id=42)], summary, organization_id="org-1", scan_id=7
    )

    component = result["components"][0]
    assert result["bomFormat"] == "CycloneDX"
    assert result["specVersion"] == "1.6"
    assert result["x-ecdat-risk-summary"] == summary
    assert result["metadata"]["component"]["name"] == "scan-7"
    assert result["metadata"]["properties"] == [
        {"name": "ecdat:organization_id", "value": "org-1"}
    ]
    assert component["bom-ref"] == "finding-42"
    assert component["cryptoProperties"]["algorithmProperties"]["keySize"] == 2048
    assert {item["name"]: item["value"] for item in component["properties"]}["ecdat:risk_tier"] == "HIGH"
    assert {item["name"]: item["value"] for item in component["properties"]}["ecdat:recommended_replacement"] == "ML-KEM"
    assert {item["name"]: item["value"] for item in component["properties"]}["ecdat:confidence_band"] == "VERIFIED"
    assert "additionalContext" not in component["evidence"]["occurrences"][0]


def test_build_cbom_from_findings_uses_stable_refs_without_database_ids():
    result = cbom_generator.build_cbom_from_findings(
        [_finding(), _finding(algorithm="AES")],
        {"total": 2, "CRITICAL": 0, "HIGH": 2, "MEDIUM": 0, "LOW": 0, "UNSCORED": 0},
    )

    assert [item["bom-ref"] for item in result["components"]] == [
        "finding-1",
        "finding-2",
    ]


def test_build_cbom_from_findings_rejects_inconsistent_summary():
    with pytest.raises(ValueError, match="Summary total"):
        cbom_generator.build_cbom_from_findings(
            [_finding()],
            {"total": 0, "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNSCORED": 0},
        )


def test_generate_cbom_keeps_orm_metadata_and_report_provenance(monkeypatch):
    import db.crud as crud

    started_at = SimpleNamespace(isoformat=lambda: "2026-09-20T09:15:02")
    report = SimpleNamespace(
        report_id="report-1",
        agent_id="agent-1",
        organization_id="org-1",
        bundle_digest="digest-1",
        signature_algorithm="Ed25519",
        classification="CONFIDENTIAL",
    )
    scan = SimpleNamespace(
        id=5,
        started_at=started_at,
        repository=SimpleNamespace(organization_id="org-1"),
        report=report,
    )
    finding = SimpleNamespace(
        id=23,
        file="src/crypto.py",
        line=12,
        algorithm="RSA",
        key_size=2048,
        confidence="high",
        risk_tier="HIGH",
        risk_reason="Quantum-vulnerable public key algorithm.",
        criticality="HIGH",
        source_context="SOURCE",
        confidence_band="VERIFIED",
        confidence_score=0.98,
        detection_method="ast_visitor",
        artifact_type="SOURCE_FILE",
        library="cryptography",
        primitive="pke",
    )
    monkeypatch.setattr(crud, "get_scan", lambda *_: scan)
    monkeypatch.setattr(crud, "get_findings_for_scan", lambda *_: [finding])
    monkeypatch.setattr(
        crud,
        "get_risk_summary",
        lambda *_: {"total": 1, "CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0, "UNSCORED": 0},
    )
    monkeypatch.setattr(crud, "get_risk_assessments_for_scan", lambda *_: {})

    result = cbom_generator.generate_cbom(object(), 5)

    assert result["metadata"]["timestamp"] == "2026-09-20T09:15:02"
    assert result["x-ecdat-report-provenance"] == {
        "origin": "offline-agent-signed-bundle",
        "report_id": "report-1",
        "agent_id": "agent-1",
        "organization_id": "org-1",
        "bundle_digest": "digest-1",
        "signature_algorithm": "Ed25519",
        "classification": "CONFIDENTIAL",
    }
    assert result["components"][0]["bom-ref"] == "finding-23"
