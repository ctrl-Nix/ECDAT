"""Regression tests for API controls supporting the offline-agent architecture."""

from fastapi.testclient import TestClient

from api.core.config import settings
from api.main import app


def test_missing_api_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", None)
    response = TestClient(app).get("/scans")
    assert response.status_code == 503
    assert response.json()["detail"] == "API authentication is not configured"


def test_server_local_scan_creation_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    monkeypatch.setattr(settings, "ENABLE_LOCAL_SCAN_API", False)
    response = TestClient(app).post(
        "/scans",
        json={"target_path": "/an-unreachable-local-path"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 403
    assert "offline CLI" in response.json()["detail"]


def test_state_changing_requests_require_json_content_type(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-key")
    response = TestClient(app).post(
        "/scans",
        content=b'{"target_path":"/tmp"}',
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "Content-Type must be application/json"


def test_all_api_responses_are_non_cacheable_and_traceable():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-request-id"]
