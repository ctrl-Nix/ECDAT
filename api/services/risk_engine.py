"""
Risk Engine — Quantum-Aware Cryptographic Risk Scoring for ECDAT.

Implements a fully deterministic, rule-based, explainable risk scoring model.
Operates on two independent axes:
  - Classical Security: Is this broken by today's computers?
  - Quantum Vulnerability: Will quantum computers break this (Shor's / Grover's)?

Per ARCHITECTURE.md and docs/RISK_ENGINE_SPEC.md.
NO LLM-generated risk scores — every tier is traceable to named factors.
"""

from __future__ import annotations

from typing import Any

from remediation_table import get_criticality

# ---------------------------------------------------------------------------
# Risk Rules Table — Complete Algorithm → Risk Profile Mapping
# Documented Mosca weights/thresholds per docs/RISK_ENGINE_SPEC.md:
#   migration_effort_days  — effort to replace (1=easy, 30=hard)
#   data_shelf_life_years  — how long data must stay confidential
#   quantum_threat_horizon — NIST estimate: 10-15 years
#   Rule: tier=HIGH if migration_effort + data_shelf_life > threat_horizon
# ---------------------------------------------------------------------------
RISK_RULES: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------ Hashes
    "MD5": {
        "tier": "CRITICAL",
        "classical_broken": True,
        "classical_break_detail": "practically broken — collision attacks known, <2^18 cost",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "SHA-256 or BLAKE2",
        "recommendation_type": "classical",
        "migration_effort_days": 1,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "MD5 is classically broken — collision attacks are well-documented and "
            "computationally trivial. Immediate replacement with SHA-256 required."
        ),
    },
    "SHA-1": {
        "tier": "CRITICAL",
        "classical_broken": True,
        "classical_break_detail": "practically broken — SHAttered collision, ~$45k cloud cost",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "SHA-256",
        "recommendation_type": "classical",
        "migration_effort_days": 1,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "SHA-1 is classically broken — the SHAttered chosen-prefix collision was "
            "demonstrated at ~$45k cloud cost. Replace with SHA-256 immediately."
        ),
    },
    "SHA-224": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm halves effective bits to 112 — still secure for ordinary use",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 112,
        "risk_reason": None,
    },
    "SHA-256": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm halves effective bits to 128 — still secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "risk_reason": None,
    },
    "SHA-384": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm reduces to 192-bit effective — still secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 192,
        "risk_reason": None,
    },
    "SHA-512": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm reduces to 256-bit effective — still secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 256,
        "risk_reason": None,
    },
    # --------------------------------------------------------- Symmetric Ciphers
    "DES": {
        "tier": "CRITICAL",
        "classical_broken": True,
        "classical_break_detail": "practically broken — brute-force feasible since 1999 (EFF DES Cracker)",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "AES-256-GCM",
        "recommendation_type": "classical",
        "migration_effort_days": 3,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "DES uses a 56-bit key that has been feasibly brute-forced since 1999. "
            "Replace with AES-256-GCM for authenticated encryption."
        ),
    },
    "3DES": {
        "tier": "HIGH",
        "classical_broken": False,
        "classical_break_detail": "deprecated — Sweet32 birthday attack; NIST disallowed after 2023",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "AES-256-GCM",
        "recommendation_type": "classical",
        "migration_effort_days": 5,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "3DES is deprecated by NIST — Sweet32 birthday attack demonstrates 64-bit block "
            "cipher weakness. Migrate to AES-256-GCM."
        ),
    },
    "RC4": {
        "tier": "CRITICAL",
        "classical_broken": True,
        "classical_break_detail": "practically broken — statistical biases, RFC 7465 prohibits use in TLS",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "AES-256-GCM",
        "recommendation_type": "classical",
        "migration_effort_days": 3,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "RC4 has known statistical biases and is prohibited in TLS by RFC 7465. "
            "Replace immediately with AES-256-GCM."
        ),
    },
    "AES": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm halves key bits — AES-256 remains 128-bit quantum-secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "risk_reason": None,
    },
    "AES-256": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Grover's algorithm reduces to 128-bit equivalent — still secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "risk_reason": None,
    },
    # ------------------------------------------------------- Asymmetric / PQC Risk
    "RSA": {
        "tier": "HIGH",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": True,
        "quantum_break_detail": "Shor's algorithm breaks all RSA key sizes in polynomial time",
        "recommended_replacement": "ML-KEM-768 + ML-DSA-65 (hybrid with RSA-3072+)",
        "recommendation_type": "hybrid",
        "migration_effort_days": 30,
        "data_shelf_life_years": 10,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "RSA is quantum-vulnerable — Shor's algorithm breaks it regardless of key size. "
            "Confirm the data shelf life and migration effort before setting a Mosca urgency. "
            "Plan a compatible hybrid migration to ML-KEM-768 for key establishment."
        ),
    },
    "ECC": {
        "tier": "HIGH",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": True,
        "quantum_break_detail": "Shor's algorithm breaks all ECC curves in polynomial time",
        "recommended_replacement": "ML-KEM-768 + ML-DSA-65",
        "recommendation_type": "post-quantum",
        "migration_effort_days": 30,
        "data_shelf_life_years": 10,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "ECC is quantum-vulnerable — Shor's algorithm breaks all elliptic curve groups. "
            "Migrate to NIST-standardized ML-KEM (key exchange) or ML-DSA (signatures)."
        ),
    },
    "DSA": {
        "tier": "HIGH",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": True,
        "quantum_break_detail": "Shor's algorithm breaks DSA in polynomial time",
        "recommended_replacement": "ML-DSA-65",
        "recommendation_type": "post-quantum",
        "migration_effort_days": 21,
        "data_shelf_life_years": 10,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "DSA is quantum-vulnerable via Shor's algorithm. Migrate digital signatures "
            "to ML-DSA-65 (NIST FIPS 204)."
        ),
    },
    "HMAC": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Security depends on underlying hash; with SHA-256+ remains secure",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "risk_reason": None,
    },
    # ----------------------------------------------------------------- Protocols
    "TLS": {
        "tier": "MEDIUM",
        "classical_broken": False,
        "classical_break_detail": "Acceptable if TLS 1.2+ with strong cipher suites",
        "quantum_vulnerable": False,
        "quantum_break_detail": "Lacks PQC key exchange; harvest-now-decrypt-later risk for TLS < 1.3",
        "recommended_replacement": "TLS-1.3 with hybrid PQC key exchange (draft)",
        "recommendation_type": "hybrid",
        "migration_effort_days": 7,
        "data_shelf_life_years": 5,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "TLS usage detected; assess version. TLS 1.0/1.1 are critically broken; "
            "TLS 1.2 is acceptable but lacks PQC key exchange; TLS 1.3 is recommended."
        ),
    },
    "TLS-1.0": {
        "tier": "CRITICAL",
        "classical_broken": True,
        "classical_break_detail": "practically broken — POODLE, BEAST attacks; deprecated by RFC 8996",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "TLS-1.3",
        "recommendation_type": "classical",
        "migration_effort_days": 7,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "TLS 1.0 is classically broken (POODLE, BEAST) and deprecated by RFC 8996. "
            "Upgrade to TLS 1.3 immediately."
        ),
    },
    "TLS-1.1": {
        "tier": "HIGH",
        "classical_broken": True,
        "classical_break_detail": "deprecated — no modern cipher suites, RFC 8996",
        "quantum_vulnerable": False,
        "quantum_break_detail": None,
        "recommended_replacement": "TLS-1.3",
        "recommendation_type": "classical",
        "migration_effort_days": 7,
        "data_shelf_life_years": 0,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "TLS 1.1 is deprecated by RFC 8996 and lacks modern cipher suites. "
            "Upgrade to TLS 1.3."
        ),
    },
    "TLS-1.2": {
        "tier": "MEDIUM",
        "classical_broken": False,
        "classical_break_detail": "acceptable if configured securely with strong cipher suites",
        "quantum_vulnerable": False,
        "quantum_break_detail": "Lacks PQC key exchange; harvest-now-decrypt-later risk",
        "recommended_replacement": "TLS-1.3 with hybrid PQC (draft)",
        "recommendation_type": "hybrid",
        "migration_effort_days": 14,
        "data_shelf_life_years": 5,
        "nist_quantum_security_level": 0,
        "risk_reason": (
            "TLS 1.2 is currently acceptable but lacks post-quantum key exchange. "
            "Plan migration to TLS 1.3 with hybrid PQC extensions."
        ),
    },
    "TLS-1.3": {
        "tier": "LOW",
        "classical_broken": False,
        "classical_break_detail": None,
        "quantum_vulnerable": False,
        "quantum_break_detail": "Not yet quantum-broken; PQC key exchange extensions in IETF draft",
        "recommended_replacement": None,
        "recommendation_type": None,
        "migration_effort_days": 0,
        "data_shelf_life_years": None,
        "nist_quantum_security_level": 128,
        "risk_reason": None,
    },
}

# Canonical tier ordering for sorting and comparison
TIER_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNSCORED": 4}

# Mosca's theorem — NIST consensus quantum threat horizon
QUANTUM_THREAT_HORIZON_YEARS = 12
RISK_MODEL_VERSION = "2026.1"


def _normalize_algorithm(algorithm: str) -> str:
    """Normalize algorithm string to canonical form matching RISK_RULES keys."""
    mapping = {
        "sha1": "SHA-1", "sha-1": "SHA-1",
        "sha224": "SHA-224", "sha-224": "SHA-224",
        "md5": "MD5",
        "sha256": "SHA-256", "sha-256": "SHA-256",
        "sha384": "SHA-384", "sha-384": "SHA-384",
        "sha512": "SHA-512", "sha-512": "SHA-512",
        "des": "DES",
        "3des": "3DES", "triple-des": "3DES", "triple_des": "3DES",
        "rc4": "RC4", "arc4": "RC4",
        "aes": "AES",
        "aes-128-cbc": "AES", "aes-256-gcm": "AES-256", "aes-256-cbc": "AES-256",
        "aes256": "AES-256", "aes-256": "AES-256",
        "rsa": "RSA",
        "ecc": "ECC", "ec": "ECC",
        "dsa": "DSA",
        "hmac": "HMAC",
        "tls": "TLS",
        "tls1.0": "TLS-1.0", "tls-1.0": "TLS-1.0",
        "tls1.1": "TLS-1.1", "tls-1.1": "TLS-1.1",
        "tls1.2": "TLS-1.2", "tls-1.2": "TLS-1.2",
        "tls1.3": "TLS-1.3", "tls-1.3": "TLS-1.3",
    }
    return mapping.get(algorithm.lower().strip(), algorithm.upper().strip())


def _apply_key_size_override(
    algorithm: str, key_size: int | None, base: dict[str, Any]
) -> dict[str, Any]:
    """
    Override risk tier for RSA/ECC based on key size.
    RSA < 2048 → CRITICAL (classically factorable).
    RSA == 2048 → MEDIUM (classically okay; quantum-vulnerable).
    RSA > 2048 → HIGH (quantum-vulnerable only).
    """
    if key_size is None:
        return {}
    if algorithm == "RSA":
        if key_size < 2048:
            return {
                "tier": "CRITICAL",
                "classical_broken": True,
                "classical_break_detail": (
                    f"RSA-{key_size} is factorable by classical means (GNFS algorithm)"
                ),
                "risk_reason": (
                    f"RSA-{key_size} is both classically factorable and quantum-vulnerable "
                    f"via Shor's algorithm. Immediate migration to RSA-3072+ or ML-KEM-768."
                ),
            }
        elif key_size == 2048:
            return {
                "tier": "MEDIUM",
                "risk_reason": (
                    f"RSA-2048 is classically acceptable but quantum-vulnerable via Shor's "
                    f"algorithm. Plan migration to ML-KEM-768 within the threat horizon."
                ),
            }
    return {}


def _mosca_urgency(rule: dict[str, Any]) -> bool:
    """
    Simplified Mosca's theorem check:
    Urgent if (data_shelf_life_years + migration_effort_days/365) > quantum_threat_horizon.
    """
    if not rule.get("quantum_vulnerable"):
        return False
    shelf = rule.get("data_shelf_life_years")
    if shelf is None:
        return False
    effort_years = (rule.get("migration_effort_days") or 0) / 365
    return (shelf + effort_years) > QUANTUM_THREAT_HORIZON_YEARS


def score_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """
    Score a single finding dict with risk_tier, risk_reason, and criticality.

    Args:
        finding: Dict with at least 'algorithm', 'file', and optionally 'key_size'.

    Returns:
        Same dict enriched with 'risk_tier', 'risk_reason', 'criticality',
        'quantum_vulnerable', 'classical_broken', 'recommended_replacement'.
    """
    algorithm_raw = finding.get("algorithm", "")
    file_path = finding.get("file", "") or finding.get("file_path", "")
    key_size = finding.get("key_size")

    canonical = _normalize_algorithm(algorithm_raw)
    rule = RISK_RULES.get(canonical, {})

    # Apply key-size override for RSA/ECC
    override = _apply_key_size_override(canonical, key_size, rule)
    effective = {**rule, **override}
    supplied_shelf_life = finding.get("data_shelf_life_years")
    if supplied_shelf_life is not None:
        try:
            supplied_shelf_life = float(supplied_shelf_life)
        except (TypeError, ValueError):
            supplied_shelf_life = None
    if supplied_shelf_life is not None and supplied_shelf_life >= 0:
        effective["data_shelf_life_years"] = supplied_shelf_life

    tier = effective.get("tier", "UNSCORED").upper()
    risk_reason = effective.get("risk_reason")

    # Mosca urgency is calculated only from a concrete business shelf-life
    # assumption. Rule defaults describe a planning baseline; they are not
    # evidence that a particular application's data remains sensitive.
    mosca_urgent: bool | None = None
    has_explicit_shelf_life = supplied_shelf_life is not None
    if not override and effective.get("quantum_vulnerable") and tier == "HIGH":
        if has_explicit_shelf_life:
            mosca_urgent = _mosca_urgency(effective)
        if mosca_urgent:
            risk_reason = (risk_reason or "") + (
                " Mosca urgency: data shelf-life + migration effort exceeds quantum threat horizon."
            )

    if not effective.get("quantum_vulnerable"):
        hndl_exposure = "NOT_APPLICABLE"
    elif not has_explicit_shelf_life:
        hndl_exposure = "UNKNOWN"
    elif mosca_urgent:
        hndl_exposure = "HIGH"
    else:
        hndl_exposure = "ASSESSMENT_REQUIRED"

    source_context = str(finding.get("source_context") or "SOURCE").upper()
    if source_context in {"TEST_ONLY", "DEMO_ONLY"}:
        context_note = (
            f" Observed in {source_context.lower().replace('_', ' ')}; "
            "verify deployed-path reachability before treating this as production exposure."
        )
        risk_reason = (risk_reason or "Static crypto inventory finding.") + context_note

    criticality = get_criticality(file_path)

    enriched = dict(finding)
    enriched.update({
        "risk_tier": tier,
        "risk_reason": risk_reason,
        "criticality": criticality,
        "quantum_vulnerable": effective.get("quantum_vulnerable", False),
        "classical_broken": effective.get("classical_broken", False),
        "recommended_replacement": effective.get("recommended_replacement"),
        "recommendation_type": effective.get("recommendation_type"),
        "migration_effort_days": effective.get("migration_effort_days"),
        "data_shelf_life_years": effective.get("data_shelf_life_years"),
        "quantum_threat_horizon_years": QUANTUM_THREAT_HORIZON_YEARS,
        "hndl_exposure": hndl_exposure,
        "assumption_source": finding.get("assumption_source"),
        "risk_model_version": RISK_MODEL_VERSION,
        "source_context": source_context,
    })
    return enriched


def score_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Score a batch of findings.

    Args:
        findings: List of finding dicts.

    Returns:
        List of enriched finding dicts sorted by risk tier (CRITICAL first).
    """
    scored = [score_finding(f) for f in findings]
    scored.sort(key=lambda f: TIER_ORDER.get(f.get("risk_tier", "UNSCORED"), 99))
    return scored
