import pytest
from fastapi.testclient import TestClient

from api.core.config import settings
from api.core.rbac import Principal, Role, decode_token, encode_token
from api.database import get_engine, init_db, get_sessionmaker
from api.main import app
from db.crud import create_user


@pytest.fixture(autouse=True)
def rbac_setup(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "01234567890123456789012345678901")
    monkeypatch.setattr(settings, "ENABLE_LOCAL_SCAN_API", False)
    init_db(get_engine())


def _create_user(username: str, role: Role, password: str = "correct-password"):
    with get_sessionmaker()() as session:
        return create_user(session, username, password, role.value)


def _token(username: str, role: Role) -> str:
    return encode_token(Principal(1, username, role.value))


def test_token_round_trip():
    principal = Principal(7, "auditor01", Role.AUDITOR.value, "org-1")
    assert decode_token(encode_token(principal)) == principal


def test_auth_login_valid_credentials():
    _create_user("valid-admin", Role.SECURITY_ADMIN)
    response = TestClient(app).post(
        "/auth/login", json={"username": "valid-admin", "password": "correct-password"}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user_role"] == Role.SECURITY_ADMIN.value


def test_auth_login_invalid_username():
    response = TestClient(app).post(
        "/auth/login", json={"username": "missing-user", "password": "correct-password"}
    )
    assert response.status_code == 401


def test_auth_login_invalid_password():
    _create_user("wrong-password", Role.AUDITOR)
    response = TestClient(app).post(
        "/auth/login", json={"username": "wrong-password", "password": "incorrect"}
    )
    assert response.status_code == 401


def test_require_role_valid_token():
    response = TestClient(app).get(
        "/scans", headers={"Authorization": f"Bearer {_token('auditor', Role.AUDITOR)}"}
    )
    assert response.status_code == 200


def test_require_role_invalid_token():
    response = TestClient(app).get(
        "/scans", headers={"Authorization": "Bearer invalid.jwt.token"}
    )
    assert response.status_code == 401


def test_require_role_insufficient_role():
    response = TestClient(app).post(
        "/scans",
        json={"target_path": "/repo"},
        headers={"Authorization": f"Bearer {_token('auditor', Role.AUDITOR)}"},
    )
    assert response.status_code == 403


def test_scans_create_developer_allowed():
    response = TestClient(app).post(
        "/scans",
        json={"target_path": "/repo"},
        headers={"Authorization": f"Bearer {_token('developer', Role.DEVELOPER)}"},
    )
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"]


def test_scans_create_auditor_denied():
    response = TestClient(app).post(
        "/scans",
        json={"target_path": "/repo"},
        headers={"Authorization": f"Bearer {_token('auditor', Role.AUDITOR)}"},
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]


def test_findings_read_auditor_allowed():
    response = TestClient(app).get(
        "/scans/999/findings",
        headers={"Authorization": f"Bearer {_token('auditor', Role.AUDITOR)}"},
    )
    assert response.status_code == 404


def test_remediation_generate_developer_allowed():
    response = TestClient(app).post(
        "/scans/remediation/generate",
        json={"algorithm": "MD5", "file": "demo.py", "line": 1},
        headers={"Authorization": f"Bearer {_token('developer', Role.DEVELOPER)}"},
    )
    assert response.status_code == 200