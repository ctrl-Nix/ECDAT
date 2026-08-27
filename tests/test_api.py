"""
Unit tests for FastAPI main application routes.
"""

from fastapi.testclient import TestClient
from api.core.config import settings
from api.main import app

client = TestClient(app)


def test_read_root():
    """Test GET / returns expected message and status code 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_get_remediation_for_missing_finding_returns_404():
    """A nonexistent finding must not receive a fabricated MD5 remediation."""
    response = client.get("/scans/1/remediation/42", headers={"X-API-Key": settings.API_KEY})
    assert response.status_code == 404
    assert response.json()["detail"] == "Finding not found in the requested scan"
