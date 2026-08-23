"""
Remediation Table & Criticality Mapping Module for ECDAT.

Provides rule-based lookup table for crypto remediation fixes/reasons
and file path criticality classification per PS 26164 requirements.
"""

REMEDIATION_TABLE = {

    "MD5": {
        "fix": "SHA-256 or BLAKE2",
        "reason": "hashing — assess security margin",
    },
    "SHA1": {
        "fix": "SHA-256",
        "reason": "hashing — assess security margin",
    },
    "DES": {
        "fix": "AES-256-GCM",
        "reason": "symmetric — check key size & data lifetime",
    },
    "RSA_LT_2048_SIGNATURE": {
        "fix": "RSA-3072+/Ed25519 now; ML-DSA (Dilithium-class) for PQC track",
        "reason": "signature purpose",
    },
    "RSA_LT_2048_KEYEXCHANGE": {
        "fix": "ML-KEM (Kyber-class)",
        "reason": "key-establishment purpose",
    },
}

DEFAULT_REMEDIATION = {
    "fix": "Manual review needed",
    "reason": "No rule exists yet.",
}


def get_remediation(algorithm: str) -> dict:
    """
    Look up recommended remediation fix and reason for a given algorithm.

    Args:
        algorithm: Canonical algorithm string (e.g. 'MD5', 'RSA_LT_2048_SIGNATURE').

    Returns:
        Dict with 'fix' and 'reason' keys. Returns default fallback if not found.
    """
    if algorithm in REMEDIATION_TABLE:
        return REMEDIATION_TABLE[algorithm].copy()
    return DEFAULT_REMEDIATION.copy()


def get_criticality(file_path: str) -> str:
    """
    Determine business criticality based on file path keyword matching
    per skills/cbom-quantum-risk/SKILL.md.

    Args:
        file_path: File path string to evaluate.

    Returns:
        'CRITICAL' if path contains auth/login/payment/billing/session,
        'HIGH' if path contains api/service/core/db/database,
        'MEDIUM' otherwise.
    """
    path = file_path.lower()
    if any(k in path for k in ["auth", "login", "payment", "billing", "session"]):
        return "CRITICAL"
    elif any(k in path for k in ["api", "service", "core", "db", "database"]):
        return "HIGH"
    else:
        return "MEDIUM"
