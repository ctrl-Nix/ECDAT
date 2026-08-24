"""
Unit tests for FastAPI main application routes.
"""

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_read_root():
    """Test GET / returns expected message and status code 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_get_remediation_for_finding_endpoint():
    """Test GET /scans/{scan_id}/remediation/{finding_id} route returns remediation dict."""
    response = client.get("/scans/1/remediation/42")
    assert response.status_code == 200
    data = response.json()
    assert "suggestion" in data
    assert "source" in data
    assert data["source"] in ["llm", "table"]
    assert "MD5" in data["suggestion"] or "SHA-256" in data["suggestion"]
