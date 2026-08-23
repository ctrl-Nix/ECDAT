"""
Unit tests for remediation_table.py.
"""

import pytest
from remediation_table import (
    REMEDIATION_TABLE,
    get_remediation,
    get_criticality,
)


def test_remediation_table_structure():
    """Verify REMEDIATION_TABLE contains all required keys with 'fix' and 'reason'."""
    expected_algorithms = [
        "MD5",
        "SHA1",
        "DES",
        "RSA_LT_2048_SIGNATURE",
        "RSA_LT_2048_KEYEXCHANGE",
    ]
    for algo in expected_algorithms:
        assert algo in REMEDIATION_TABLE, f"Missing algorithm {algo} in REMEDIATION_TABLE"
        assert "fix" in REMEDIATION_TABLE[algo], f"Missing 'fix' key for {algo}"
        assert "reason" in REMEDIATION_TABLE[algo], f"Missing 'reason' key for {algo}"
        assert isinstance(REMEDIATION_TABLE[algo]["fix"], str)
        assert isinstance(REMEDIATION_TABLE[algo]["reason"], str)


def test_get_remediation_known_algorithms():
    """Test get_remediation for known algorithms in the table."""
    res_md5 = get_remediation("MD5")
    assert res_md5["fix"] == "SHA-256 or BLAKE2"
    assert "hashing" in res_md5["reason"]

    res_sha1 = get_remediation("SHA1")
    assert res_sha1["fix"] == "SHA-256"

    res_des = get_remediation("DES")
    assert res_des["fix"] == "AES-256-GCM"

    res_rsa_sig = get_remediation("RSA_LT_2048_SIGNATURE")
    assert "ML-DSA" in res_rsa_sig["fix"]
    assert res_rsa_sig["reason"] == "signature purpose"

    res_rsa_kx = get_remediation("RSA_LT_2048_KEYEXCHANGE")
    assert res_rsa_kx["fix"] == "ML-KEM (Kyber-class)"
    assert res_rsa_kx["reason"] == "key-establishment purpose"


def test_get_remediation_unknown_algorithm():
    """Test get_remediation returns default dict for unknown algorithm."""
    default_expected = {"fix": "Manual review needed", "reason": "No rule exists yet."}
    res = get_remediation("UNKNOWN_ALGO_XYZ")
    assert res == default_expected


def test_get_criticality_critical_paths():
    """Test get_criticality tags paths containing auth/login/payment/billing/session as CRITICAL."""
    critical_paths = [
        "src/auth/service.py",
        "app/controllers/login_controller.py",
        "payment_gateway/processor.py",
        "billing/invoices.py",
        "user_session_manager.py",
        "C:\\Project\\AUTH\\Login.py",
    ]
    for path in critical_paths:
        assert get_criticality(path) == "CRITICAL", f"Failed for path: {path}"


def test_get_criticality_high_paths():
    """Test get_criticality tags paths containing api/service/core/db as HIGH."""
    high_paths = [
        "src/api/routes.py",
        "app/micro_service/handler.py",
        "core/engine.py",
        "database/models.py",
        "db_connection.py",
    ]
    for path in high_paths:
        assert get_criticality(path) == "HIGH", f"Failed for path: {path}"


def test_get_criticality_medium_paths():
    """Test get_criticality tags remaining paths as MEDIUM."""
    medium_paths = [
        "utils/helpers.py",
        "components/button.tsx",
        "config.json",
        "README.md",
    ]
    for path in medium_paths:
        assert get_criticality(path) == "MEDIUM", f"Failed for path: {path}"


def test_get_criticality_priority():
    """Test priority order: auth/login in path takes precedence over db/api."""
    assert get_criticality("services/auth_service.py") == "CRITICAL"
    assert get_criticality("api/billing_db.py") == "CRITICAL"
