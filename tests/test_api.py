"""
Unit tests for FastAPI main application routes.
"""

from fastapi.testclient import TestClient

from api.core.config import settings
from api.core.rbac import Principal, Role, encode_token
from api.main import app

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
