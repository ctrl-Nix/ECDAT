"""
Unit tests for FastAPI main application routes.
"""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from api.core.config import settings
from api.core.rbac import Principal, Role, encode_token
from api.database import get_session
from api.main import app
from db import crud
from db.models import Base

client = TestClient(app)


def test_read_root():
    """Test GET / returns expected message and status code 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_get_remediation_for_missing_finding_returns_404(monkeypatch):
    """A nonexistent finding must not receive a fabricated MD5 remediation."""
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "01234567890123456789012345678901")
    token = encode_token(Principal(1, "developer", Role.DEVELOPER.value))
    response = client.get(
        "/scans/1/remediation/42",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Finding not found in the requested scan"


@pytest.fixture()
def findings_api(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "01234567890123456789012345678901")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    token = encode_token(Principal(1, "developer", Role.DEVELOPER.value))
    with TestClient(app) as api_client:
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        with Session(engine) as session:
            repo = crud.get_or_create_repository(
                session, name="api-filter-sort", url="https://example.test/api-filter-sort"
            )
            scan = crud.start_scan(session, repo.id)
            crud.save_findings(session, scan.id, [
                {"file": "a.py", "line": 1, "algorithm": "MD5", "risk_tier": "CRITICAL", "language": "python", "primitive": "hash"},
                {"file": "b.java", "line": 2, "algorithm": "RSA", "risk_tier": "HIGH", "language": "java", "primitive": "asymmetric-cipher"},
            ])
            session.commit()
            scan_id = scan.id
        yield api_client, scan_id
    app.dependency_overrides.pop(get_session, None)
    engine.dispose()


def test_findings_repeated_risk_tier_filters_are_returned(findings_api):
    api_client, scan_id = findings_api
    response = api_client.get(f"/scans/{scan_id}/findings?risk_tier=CRITICAL&risk_tier=HIGH")
    assert response.status_code == 200
    assert response.json()["filters"]["risk_tier"] == ["CRITICAL", "HIGH"]
    assert len(response.json()["findings"]) == 2


def test_findings_default_filter_sort_response(findings_api):
    api_client, scan_id = findings_api
    response = api_client.get(f"/scans/{scan_id}/findings")
    assert response.status_code == 200
    assert response.json()["risk_tier_filter"] is None
    assert response.json()["filters"] == {
        "risk_tier": None, "primitive": None, "algorithm": None, "language": None,
    }
    assert response.json()["sort_by"] is None
    assert response.json()["sort_dir"] == "asc"


@pytest.mark.parametrize("query", ["sort_by=notacolumn", "sort_dir=sideways"])
def test_findings_reject_invalid_sort_parameters(findings_api, query):
    api_client, scan_id = findings_api
    response = api_client.get(f"/scans/{scan_id}/findings?{query}")
    assert response.status_code == 422
