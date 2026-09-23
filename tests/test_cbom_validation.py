from __future__ import annotations

import copy
import datetime as dt
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import api.routers.cbom as cbom_router
import db.crud as crud
from api.core.config import settings
from api.core.rbac import Principal, Role, encode_token
from api.database import get_session
from api.main import app
from api.services.cbom_generator import generate_cbom
from api.services.cbom_validator import (
    CBOM_ISSUE_CODES,
    CBOM_VALIDATION_SCOPE,
    CbomIssue,
    CbomValidationResult,
    validate_cbom,
)
from api.services.risk_engine import score_findings
from db.models import Base


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def real_cbom(engine):
    with Session(engine) as session:
        repo = crud.get_or_create_repository(
            session, "test-repo", "https://github.com/test/test"
        )
        scan = crud.start_scan(session, repo.id)
        raw_findings = [
            {
                "file": "a.py",
                "line": 3,
                "algorithm": "MD5",
                "confidence": "high",
                "language": "python",
                "primitive": "hash",
                "detection_method": "ast_visitor",
            },
            {
                "file": "k.py",
                "line": 9,
                "algorithm": "RSA",
                "key_size": 1024,
                "confidence": "high",
                "language": "python",
                "primitive": "pke",
                "detection_method": "ast_visitor",
            },
            {
                "file": "c.java",
                "line": 5,
                "algorithm": "3DES",
                "confidence": "high",
                "language": "java",
                "detection_method": "tree_sitter_query",
            },
            {
                "file": "e.js",
                "line": 2,
                "algorithm": "ECC",
                "confidence": "unverified",
                "language": "javascript",
                "detection_method": "tree_sitter_query",
                "source_context": "TEST_ONLY",
            },
        ]
        scored = score_findings(raw_findings)
        crud.save_findings(session, scan.id, scored)
        crud.complete_scan(session, scan.id)
        cbom = generate_cbom(session, scan.id)
        assert cbom is not None
        return json.loads(json.dumps(cbom, default=str))


def test_generated_export_is_valid(real_cbom):
    res = validate_cbom(real_cbom)
    assert res.valid is True
    assert res.issues == []
    assert res.scope == CBOM_VALIDATION_SCOPE


def test_empty_scan_export_is_valid(engine):
    with Session(engine) as session:
        repo = crud.get_or_create_repository(
            session, "empty-repo", "https://github.com/test/empty"
        )
        scan = crud.start_scan(session, repo.id)
        crud.complete_scan(session, scan.id)
        cbom = generate_cbom(session, scan.id)
        assert cbom is not None
        doc = json.loads(json.dumps(cbom, default=str))
        assert doc["components"] == []
        res = validate_cbom(doc)
        assert res.valid is True
        assert res.issues == []


@pytest.mark.parametrize("bad_input", [None, [], "cbom", 7])
def test_non_object_document_rejected(bad_input):
    res = validate_cbom(bad_input)
    assert res.valid is False
    assert {(i.code, i.path) for i in res.issues} == {("DOCUMENT_NOT_OBJECT", "")}


def test_wrong_bom_format_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["bomFormat"] = "SPDX"
    res = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/bomFormat") in {(i.code, i.path) for i in res.issues}


def test_wrong_spec_version_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["specVersion"] = "1.5"
    res = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/specVersion") in {(i.code, i.path) for i in res.issues}


def test_missing_components_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    del doc["components"]
    res = validate_cbom(doc)
    assert ("FIELD_MISSING", "/components") in {(i.code, i.path) for i in res.issues}


def test_components_wrong_type_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"] = "not-a-list"
    res = validate_cbom(doc)
    assert ("FIELD_WRONG_TYPE", "/components") in {(i.code, i.path) for i in res.issues}


def test_component_type_must_be_cryptographic_asset(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"][0]["type"] = "library"
    res = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/components/0/type") in {
        (i.code, i.path) for i in res.issues
    }


def test_unknown_asset_type_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"][0]["cryptoProperties"]["assetType"] = "hardware"
    res = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/components/0/cryptoProperties/assetType") in {
        (i.code, i.path) for i in res.issues
    }


def test_algorithm_asset_requires_algorithm_properties(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"][0]["cryptoProperties"]["algorithmProperties"] = None
    res = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/components/0/cryptoProperties") in {
        (i.code, i.path) for i in res.issues
    }


def test_empty_evidence_occurrences_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"][1]["evidence"]["occurrences"] = []
    res = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/components/1/evidence/occurrences") in {
        (i.code, i.path) for i in res.issues
    }


def test_line_zero_accepted_and_negative_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"][0]["evidence"]["occurrences"][0]["line"] = 0
    res = validate_cbom(doc)
    assert res.valid is True

    doc["components"][0]["evidence"]["occurrences"][0]["line"] = -1
    res_neg = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/components/0/evidence/occurrences/0/line") in {
        (i.code, i.path) for i in res_neg.issues
    }


def test_duplicate_bom_ref_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"][1]["bom-ref"] = doc["components"][0]["bom-ref"]
    res = validate_cbom(doc)
    assert ("BOM_REF_DUPLICATE", "/components/1/bom-ref") in {
        (i.code, i.path) for i in res.issues
    }


def test_serial_number_must_be_canonical_urn_uuid(real_cbom):
    doc1 = copy.deepcopy(real_cbom)
    doc1["serialNumber"] = "not-a-urn"
    res1 = validate_cbom(doc1)
    assert ("FIELD_INVALID_VALUE", "/serialNumber") in {
        (i.code, i.path) for i in res1.issues
    }

    doc2 = copy.deepcopy(real_cbom)
    doc2["serialNumber"] = doc2["serialNumber"].upper()
    res2 = validate_cbom(doc2)
    assert ("FIELD_INVALID_VALUE", "/serialNumber") in {
        (i.code, i.path) for i in res2.issues
    }


def test_metadata_timestamp_must_be_iso8601(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["metadata"]["timestamp"] = "not-an-iso8601-date"
    res = validate_cbom(doc)
    assert ("FIELD_INVALID_VALUE", "/metadata/timestamp") in {
        (i.code, i.path) for i in res.issues
    }


def test_missing_risk_tier_property_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["components"][0]["properties"] = [
        p for p in doc["components"][0]["properties"] if p["name"] != "ecdat:risk_tier"
    ]
    res = validate_cbom(doc)
    assert ("RISK_TIER_PROPERTY_MISSING", "/components/0/properties") in {
        (i.code, i.path) for i in res.issues
    }


def test_invalid_risk_tier_property_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    for p in doc["components"][0]["properties"]:
        if p["name"] == "ecdat:risk_tier":
            p["value"] = "SEVERE"
    res = validate_cbom(doc)
    assert ("RISK_TIER_PROPERTY_INVALID", "/components/0/properties") in {
        (i.code, i.path) for i in res.issues
    }


def test_invalid_criticality_property_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    for p in doc["components"][0]["properties"]:
        if p["name"] == "ecdat:criticality":
            p["value"] = "EXTREME"
    res = validate_cbom(doc)
    assert ("CRITICALITY_PROPERTY_INVALID", "/components/0/properties") in {
        (i.code, i.path) for i in res.issues
    }


def test_summary_total_mismatch_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["x-ecdat-risk-summary"]["total"] = 999
    res = validate_cbom(doc)
    assert ("SUMMARY_TOTAL_MISMATCH", "/x-ecdat-risk-summary/total") in {
        (i.code, i.path) for i in res.issues
    }


def test_summary_tier_mismatch_rejected(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["x-ecdat-risk-summary"]["CRITICAL"] += 1
    doc["x-ecdat-risk-summary"]["LOW"] -= 1
    res = validate_cbom(doc)
    issues = {(i.code, i.path) for i in res.issues}
    assert ("SUMMARY_TIER_MISMATCH", "/x-ecdat-risk-summary/CRITICAL") in issues
    assert ("SUMMARY_TIER_MISMATCH", "/x-ecdat-risk-summary/LOW") in issues


def test_ecdat_extension_fields_are_accepted(real_cbom):
    doc = copy.deepcopy(real_cbom)
    assert validate_cbom(doc).valid is True
    del doc["x-ecdat-risk-summary"]
    assert validate_cbom(doc).valid is True
    doc["x-custom-extension"] = {"foo": "bar"}
    assert validate_cbom(doc).valid is True


def test_non_json_serialisable_document_rejected(real_cbom):
    doc1 = copy.deepcopy(real_cbom)
    doc1["externalReferences"].append(dt.datetime.now())
    res1 = validate_cbom(doc1)
    assert ("NOT_JSON_SERIALIZABLE", "") in {(i.code, i.path) for i in res1.issues}

    doc2 = copy.deepcopy(real_cbom)
    doc2["externalReferences"].append(float("nan"))
    res2 = validate_cbom(doc2)
    assert ("NOT_JSON_SERIALIZABLE", "") in {(i.code, i.path) for i in res2.issues}


def test_validation_does_not_mutate_input(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc_copy = copy.deepcopy(doc)
    validate_cbom(doc)
    assert doc == doc_copy


def test_issue_output_is_deterministic_and_uses_known_codes(real_cbom):
    doc = copy.deepcopy(real_cbom)
    doc["specVersion"] = "1.5"
    doc["bomFormat"] = "SPDX"
    res1 = validate_cbom(doc)
    res2 = validate_cbom(doc)
    assert res1.model_dump() == res2.model_dump()
    assert res1.issues == sorted(
        res1.issues, key=lambda x: (x.path, x.code, x.message)
    )
    assert len(res1.issues) > 0
    for issue in res1.issues:
        assert issue.code in CBOM_ISSUE_CODES


def test_issue_messages_never_echo_document_values(real_cbom):
    doc = copy.deepcopy(real_cbom)
    sentinel = "SECRET_SENTINEL_STRING_XYZ"
    doc["bomFormat"] = sentinel
    doc["components"][0]["type"] = sentinel
    doc["components"][0]["evidence"]["occurrences"][0]["location"] = sentinel
    doc["components"][0]["evidence"]["occurrences"][0]["line"] = -1
    doc["components"][0]["description"] = sentinel
    res = validate_cbom(doc)
    assert sentinel not in res.model_dump_json()


# ---------------------------------------------------------------------------
# Phase B: Endpoint integration tests (GET /scans/{scan_id}/cbom)
# ---------------------------------------------------------------------------


def _seed_scan_with_findings(engine) -> int:
    with Session(engine) as session:
        repo = crud.get_or_create_repository(
            session, "endpoint-repo", "https://github.com/test/endpoint"
        )
        scan = crud.start_scan(session, repo.id)
        raw_findings = [
            {
                "file": "a.py",
                "line": 3,
                "algorithm": "MD5",
                "confidence": "high",
                "language": "python",
                "primitive": "hash",
                "detection_method": "ast_visitor",
            },
            {
                "file": "k.py",
                "line": 9,
                "algorithm": "RSA",
                "key_size": 1024,
                "confidence": "high",
                "language": "python",
                "primitive": "pke",
                "detection_method": "ast_visitor",
            },
            {
                "file": "c.java",
                "line": 5,
                "algorithm": "3DES",
                "confidence": "high",
                "language": "java",
                "detection_method": "tree_sitter_query",
            },
            {
                "file": "e.js",
                "line": 2,
                "algorithm": "ECC",
                "confidence": "unverified",
                "language": "javascript",
                "detection_method": "tree_sitter_query",
                "source_context": "TEST_ONLY",
            },
        ]
        scored = score_findings(raw_findings)
        crud.save_findings(session, scan.id, scored)
        crud.complete_scan(session, scan.id)
        session.commit()
        return scan.id


def auth_headers(role: Role = Role.AUDITOR) -> dict[str, str]:
    token = encode_token(Principal(1, "auditor", role.value))
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": settings.API_KEY or "ci-test-key",
    }


@pytest.fixture()
def client(engine, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "01234567890123456789012345678901")

    def override_get_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_endpoint_serves_validated_export_unchanged(client, engine, monkeypatch):
    scan_id = _seed_scan_with_findings(engine)

    spy_called = []
    orig_validate = cbom_router.validate_cbom

    def spy_validate(cbom_dict):
        spy_called.append(cbom_dict)
        return orig_validate(cbom_dict)

    monkeypatch.setattr(cbom_router, "validate_cbom", spy_validate)

    response = client.get(
        f"/scans/{scan_id}/cbom?download=true",
        headers=auth_headers(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.cyclonedx+json"
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="ecdat-scan-{scan_id}-cbom.json"'
    )
    data = response.json()
    assert len(data.get("components", [])) == 4
    assert len(spy_called) == 1
    assert spy_called[0]["bomFormat"] == "CycloneDX"


def test_endpoint_unknown_scan_is_404_and_skips_validation(client, monkeypatch):
    spy_called = []
    monkeypatch.setattr(
        cbom_router,
        "validate_cbom",
        lambda cbom_dict: spy_called.append(cbom_dict),
    )

    response = client.get("/scans/9999/cbom", headers=auth_headers())
    assert response.status_code == 404
    assert len(spy_called) == 0


def test_endpoint_in_progress_scan_is_400_and_skips_validation(
    client, engine, monkeypatch
):
    with Session(engine) as session:
        repo = crud.get_or_create_repository(
            session, "running-repo", "https://github.com/test/running"
        )
        scan = crud.start_scan(session, repo.id)
        scan_id = scan.id
        session.commit()

    spy_called = []
    monkeypatch.setattr(
        cbom_router,
        "validate_cbom",
        lambda cbom_dict: spy_called.append(cbom_dict),
    )

    response = client.get(f"/scans/{scan_id}/cbom", headers=auth_headers())
    assert response.status_code == 400
    assert len(spy_called) == 0


def test_endpoint_invalid_cbom_returns_500_with_sanitized_error(
    client, engine, monkeypatch
):
    scan_id = _seed_scan_with_findings(engine)

    monkeypatch.setattr(
        cbom_router,
        "validate_cbom",
        lambda cbom_dict: CbomValidationResult(
            valid=False,
            issues=[
                CbomIssue(
                    code="FIELD_INVALID_VALUE",
                    path="/secret/internal/path",
                    message="Sensitive internal exception trace detail",
                )
            ],
        ),
    )

    response = client.get(f"/scans/{scan_id}/cbom", headers=auth_headers())
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"error": "CBOM validation failed"}
    assert "Sensitive" not in response.text
    assert "internal" not in response.text


def test_validation_failure_does_not_leak_document_values(
    client, engine, monkeypatch
):
    scan_id = _seed_scan_with_findings(engine)

    orig_generate = cbom_router.generate_cbom

    def corrupt_cbom(db, sid):
        doc = orig_generate(db, sid)
        doc["bomFormat"] = "INVALID_BOM_FORMAT"
        doc["components"][0]["description"] = "CONFIDENTIAL_PASSWORD_SECRET_HASH"
        return doc

    monkeypatch.setattr(cbom_router, "generate_cbom", corrupt_cbom)

    response = client.get(f"/scans/{scan_id}/cbom", headers=auth_headers())
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"error": "CBOM validation failed"}
    assert "CONFIDENTIAL_PASSWORD_SECRET_HASH" not in response.text
    assert "INVALID_BOM_FORMAT" not in response.text
    assert "Traceback" not in response.text


def test_validator_is_called_exactly_once(client, engine, monkeypatch):
    scan_id = _seed_scan_with_findings(engine)

    call_count = 0
    orig_validate = cbom_router.validate_cbom

    def counting_validate(cbom_dict):
        nonlocal call_count
        call_count += 1
        return orig_validate(cbom_dict)

    monkeypatch.setattr(cbom_router, "validate_cbom", counting_validate)

    response = client.get(f"/scans/{scan_id}/cbom", headers=auth_headers())
    assert response.status_code == 200
    assert call_count == 1

