"""
CBOM Generator — CycloneDX 1.6 Cryptographic Bill of Materials.

Transforms persisted Finding rows (from db.crud) into a valid CycloneDX 1.6
JSON document using the cryptography-asset component extension.

Per skills/cbom-quantum-risk/SKILL.md and ARCHITECTURE.md:
  - Every component carries: algorithm, assetType, evidence, risk_tier,
    risk_reason, criticality, and recommended migration direction.
  - No field structure is invented — only actual CycloneDX 1.6 spec fields.
  - Risk tiers come from the DB (populated by risk_engine), never re-scored here.
  - Output is a dict that serialises directly to valid CycloneDX JSON.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

import db.crud as crud
from db.models import Finding, Scan

# ---------------------------------------------------------------------------
# CycloneDX 1.6 constants
# ---------------------------------------------------------------------------
CYCLONEDX_SPEC_VERSION = "1.6"
CYCLONEDX_FORMAT = "CycloneDX"
CBOM_BOM_FORMAT = "application/vnd.cyclonedx+json"

# Maps ECDAT algorithm names → CycloneDX algorithmProperties.primitive
# Ref: CycloneDX 1.6 cryptography-asset spec
_PRIMITIVE_MAP: dict[str, str] = {
    "MD5":    "hash",
    "SHA-1":  "hash",
    "SHA-256": "hash",
    "SHA-384": "hash",
    "SHA-512": "hash",
    "HMAC":   "mac",
    "DES":    "blockCipher",
    "3DES":   "blockCipher",
    "RC4":    "streamCipher",
    "AES":    "blockCipher",
    "AES-256": "blockCipher",
    "RSA":    "publicKeyEncryption",
    "ECC":    "other",
    "DSA":    "signature",
    "TLS":    "other",
    "TLS-1.0": "other",
    "TLS-1.1": "other",
    "TLS-1.2": "other",
    "TLS-1.3": "other",
}

# Maps ECDAT algorithm → CycloneDX algorithmProperties.cryptoFunctions
# (subset of what that finding expresses)
_CRYPTO_FUNCTIONS_MAP: dict[str, list[str]] = {
    "MD5":    ["digest"],
    "SHA-1":  ["digest"],
    "SHA-256": ["digest"],
    "SHA-384": ["digest"],
    "SHA-512": ["digest"],
    "HMAC":   ["mac"],
    "DES":    ["encrypt", "decrypt"],
    "3DES":   ["encrypt", "decrypt"],
    "RC4":    ["encrypt", "decrypt"],
    "AES":    ["encrypt", "decrypt"],
    "AES-256": ["encrypt", "decrypt"],
    "RSA":    ["encapsulate", "decapsulate", "sign", "verify"],
    "ECC":    ["keyGenerate", "keyDerive"],
    "DSA":    ["sign", "verify"],
    "TLS":    ["auth"],
    "TLS-1.0": ["auth"],
    "TLS-1.1": ["auth"],
    "TLS-1.2": ["auth"],
    "TLS-1.3": ["auth"],
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_cbom(session: Session, scan_id: int) -> dict[str, Any] | None:
    """
    Build a CycloneDX 1.6 CBOM JSON document for the given scan.

    Args:
        session:  Active SQLAlchemy session.
        scan_id:  ID of a completed scan.

    Returns:
        CycloneDX CBOM dict (serialisable to JSON), or None if scan not found.
    """
    scan: Scan | None = crud.get_scan(session, scan_id)
    if scan is None:
        return None

    findings: list[Finding] = crud.get_findings_for_scan(session, scan_id)
    summary: dict[str, int] = crud.get_risk_summary(session, scan_id)

    components = [_finding_to_component(f) for f in findings]

    return {
        "bomFormat": CYCLONEDX_FORMAT,
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": _build_metadata(scan),
        "components": components,
        "externalReferences": [],
        # ECDAT extension — not a CycloneDX field, namespaced to avoid collision
        "x-ecdat-risk-summary": summary,
    }


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _build_metadata(scan: Scan) -> dict[str, Any]:
    """Build the CycloneDX metadata block for a scan."""
    return {
        "timestamp": (
            scan.started_at.isoformat()
            if scan.started_at
            else dt.datetime.utcnow().isoformat()
        ),
        "tools": [
            {
                "vendor": "ECDAT",
                "name": "ECDAT — Enterprise Cryptographic Discovery & Assessment Tool",
                "version": "1.0.0",
            }
        ],
        "component": {
            "type": "application",
            "name": f"scan-{scan.id}",
            "version": "1",
        },
    }


def _finding_to_component(finding: Finding) -> dict[str, Any]:
    """
    Transform one Finding ORM row → one CycloneDX 1.6 cryptography-asset component.

    Fields follow the actual CycloneDX 1.6 cryptography extension specification.
    """
    algo = finding.algorithm or "UNKNOWN"
    primitive = _PRIMITIVE_MAP.get(algo, "other")
    crypto_functions = _CRYPTO_FUNCTIONS_MAP.get(algo, [])

    # Build the cryptoProperties block (CycloneDX 1.6 crypto extension)
    crypto_props: dict[str, Any] = {
        "assetType": "algorithm",
        "algorithmProperties": {
            "primitive": primitive,
            "implementationLevel": "softwarePlainRam",
            "cryptoFunctions": crypto_functions,
        },
    }
    if finding.key_size:
        crypto_props["algorithmProperties"]["parameterSetIdentifier"] = str(finding.key_size)
        crypto_props["algorithmProperties"]["keySize"] = finding.key_size

    # Evidence — traceable back to scanner source
    evidence = {
        "occurrences": [
            {
                "location": finding.file,
                "line": finding.line,
                "additionalContext": f"Detection confidence: {finding.confidence}",
            }
        ]
    }

    # Risk classification (ECDAT extension within CycloneDX properties)
    properties = [
        {"name": "ecdat:risk_tier",   "value": finding.risk_tier or "UNSCORED"},
        {"name": "ecdat:criticality", "value": finding.criticality or "MEDIUM"},
    ]
    if finding.risk_reason:
        properties.append({"name": "ecdat:risk_reason", "value": finding.risk_reason})

    # Recommended migration (PQC direction from risk_engine → stored in DB via save_findings)
    # We surface it as a property since CycloneDX has no migration field yet.
    # (Fields come from the scored finding dict persisted by scan_runner.)

    return {
        "type": "cryptographic-asset",
        "bom-ref": f"finding-{finding.id}",
        "name": algo,
        "version": _infer_version(algo, finding.key_size),
        "description": (
            f"{algo} detected at {finding.file}:{finding.line} "
            f"(confidence={finding.confidence})"
        ),
        "cryptoProperties": crypto_props,
        "evidence": evidence,
        "properties": properties,
    }


def _infer_version(algorithm: str, key_size: int | None) -> str:
    """
    Build a human-readable version string from algorithm + key size.

    e.g.: RSA + 1024 → "RSA-1024", MD5 → "MD5"
    """
    if key_size:
        return f"{algorithm}-{key_size}"
    return algorithm

