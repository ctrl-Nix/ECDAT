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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from db.models import Finding, RiskAssessment, Scan

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
    import db.crud as crud
    from db.models import Scan

    scan: Scan | None = crud.get_scan(session, scan_id)
    if scan is None:
        return None

    findings: list[Finding] = crud.get_findings_for_scan(session, scan_id)
    summary: dict[str, int] = crud.get_risk_summary(session, scan_id)

    assessments = crud.get_risk_assessments_for_scan(session, scan_id)
    finding_dicts = [
        _finding_to_dict(finding, assessments.get(finding.id))
        for finding in findings
    ]
    cbom = build_cbom_from_findings(
        finding_dicts,
        summary,
        organization_id=(scan.repository.organization_id if scan.repository else None),
        scan_id=scan.id,
    )

    # Keep the API's established scan timestamp and custody metadata. The pure
    # builder supplies the shared component and risk-summary implementation.
    cbom["metadata"] = _build_metadata(scan)
    cbom["x-ecdat-report-provenance"] = _report_provenance(scan)
    return cbom


def build_cbom_from_findings(
    findings: list[dict[str, Any]],
    summary: dict[str, Any],
    organization_id: str | None = None,
    scan_id: int | None = None,
) -> dict[str, Any]:
    """Build a CBOM from already-scored finding dictionaries without a DB.

    Risk values are copied as supplied; this function deliberately does not
    import or invoke the risk engine. The ORM API entry point calls this same
    builder after loading rows from the database.
    """
    if not isinstance(findings, list):
        raise ValueError("findings must be a list of objects")
    required_finding_fields = {
        "file", "line", "library", "algorithm", "confidence",
        "risk_tier", "risk_reason", "primitive",
    }
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ValueError(f"Finding at index {index} must be an object")
        missing = sorted(required_finding_fields - finding.keys())
        if missing:
            raise ValueError(
                f"Finding at index {index} missing required field: {missing[0]}"
            )
        if not isinstance(finding["file"], str) or not isinstance(finding["algorithm"], str):
            raise ValueError(f"Finding at index {index} has invalid file or algorithm")
        if type(finding["line"]) is not int or finding["line"] < 0:
            raise ValueError(f"Finding at index {index} has invalid line")
        if finding["risk_tier"] is not None and not isinstance(finding["risk_tier"], str):
            raise ValueError(f"Finding at index {index} has invalid risk_tier")
        if finding["risk_tier"] not in (None, "UNSCORED", "LOW", "MEDIUM", "HIGH", "CRITICAL"):
            raise ValueError(f"Finding at index {index} has invalid risk_tier")
    if not isinstance(summary, dict):
        raise ValueError("summary must be an object")
    required_summary_fields = {"total", "CRITICAL", "HIGH", "MEDIUM", "LOW", "UNSCORED"}
    missing_summary = sorted(required_summary_fields - summary.keys())
    if missing_summary:
        raise ValueError(f"Summary missing required field: {missing_summary[0]}")
    if any(type(summary[key]) is not int or summary[key] < 0 for key in required_summary_fields):
        raise ValueError("Summary counts must be non-negative integers")
    counts = {tier: 0 for tier in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNSCORED")}
    for finding in findings:
        tier = finding["risk_tier"] or "UNSCORED"
        counts[tier] += 1
    if summary["total"] != len(findings):
        raise ValueError("Summary total does not match the findings count")
    for tier, count in counts.items():
        if summary[tier] != count:
            raise ValueError(f"Summary count for {tier} does not match the findings")

    components = [
        _finding_dict_to_component(finding, index)
        for index, finding in enumerate(findings, start=1)
    ]
    metadata: dict[str, Any] = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tools": [
            {
                "vendor": "ECDAT",
                "name": "ECDAT — Enterprise Cryptographic Discovery & Assessment Tool",
                "version": "1.0.0",
            }
        ],
    }
    if scan_id is not None:
        metadata["component"] = {
            "type": "application",
            "name": f"scan-{scan_id}",
            "version": "1",
        }
    if organization_id is not None:
        metadata["properties"] = [
            {"name": "ecdat:organization_id", "value": organization_id}
        ]

    return {
        "bomFormat": CYCLONEDX_FORMAT,
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": metadata,
        "components": components,
        "externalReferences": [],
        "x-ecdat-risk-summary": dict(summary),
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


def _finding_to_component(
    finding: Finding, assessment: RiskAssessment | None = None
) -> dict[str, Any]:
    """
    Transform one Finding ORM row → one CycloneDX 1.6 cryptography-asset component.

    Fields follow the actual CycloneDX 1.6 cryptography extension specification.
    """
    return _finding_dict_to_component(_finding_to_dict(finding, assessment), finding.id)


def _finding_to_dict(
    finding: Finding, assessment: RiskAssessment | None = None
) -> dict[str, Any]:
    """Convert ORM evidence to the scored dictionary shape used by the builder."""
    result = {
        name: getattr(finding, name)
        for name in (
            "id", "file", "line", "algorithm", "key_size", "confidence", "risk_tier",
            "risk_reason", "criticality", "source_context", "library", "primitive",
            "confidence_band", "confidence_score", "detection_method", "artifact_type",
        )
    }
    if assessment is not None:
        result.update(
            {
                "risk_model_version": assessment.risk_model_version,
                "classical_broken": assessment.classical_broken,
                "quantum_vulnerable": assessment.quantum_vulnerable,
                "hndl_exposure": assessment.hndl_exposure,
                "recommended_replacement": assessment.recommended_replacement,
                "recommendation_type": assessment.recommendation_type,
                "migration_effort_days": assessment.migration_effort_days,
                "data_shelf_life_years": assessment.data_shelf_life_years,
                "quantum_threat_horizon_years": assessment.quantum_threat_horizon_years,
                "assumption_source": assessment.assumption_source,
            }
        )
    return result


def _finding_dict_to_component(
    finding: dict[str, Any], index: int
) -> dict[str, Any]:
    """Map one scored finding dictionary to the generator's component shape."""
    algo = finding.get("algorithm") or "UNKNOWN"
    key_size = finding.get("key_size")
    crypto_props: dict[str, Any] = {
        "assetType": "algorithm",
        "algorithmProperties": {
            "primitive": _PRIMITIVE_MAP.get(algo, "other"),
            "implementationLevel": "softwarePlainRam",
            "cryptoFunctions": list(_CRYPTO_FUNCTIONS_MAP.get(algo, [])),
        },
    }
    if key_size:
        crypto_props["algorithmProperties"]["parameterSetIdentifier"] = str(key_size)
        crypto_props["algorithmProperties"]["keySize"] = key_size

    properties = [
        {"name": "ecdat:risk_tier", "value": finding.get("risk_tier") or "UNSCORED"},
        {"name": "ecdat:criticality", "value": finding.get("criticality") or "MEDIUM"},
    ]
    if finding.get("risk_reason"):
        properties.append({"name": "ecdat:risk_reason", "value": finding["risk_reason"]})
    properties.append({"name": "ecdat:source_context", "value": finding.get("source_context", "SOURCE")})
    extension_properties = (
        ("ecdat:confidence_band", "confidence_band"),
        ("ecdat:confidence_score", "confidence_score"),
        ("ecdat:detection_method", "detection_method"),
        ("ecdat:artifact_type", "artifact_type"),
    )
    for property_name, field_name in extension_properties:
        value = finding.get(field_name)
        if value is not None:
            properties.append({"name": property_name, "value": str(value)})

    assessment_properties = (
        ("ecdat:risk_model_version", "risk_model_version", False),
        ("ecdat:classical_broken", "classical_broken", True),
        ("ecdat:quantum_vulnerable", "quantum_vulnerable", True),
        ("ecdat:hndl_exposure", "hndl_exposure", False),
        ("ecdat:recommended_replacement", "recommended_replacement", False),
        ("ecdat:recommendation_type", "recommendation_type", False),
        ("ecdat:migration_effort_days", "migration_effort_days", False),
        ("ecdat:data_shelf_life_years", "data_shelf_life_years", False),
        ("ecdat:quantum_threat_horizon_years", "quantum_threat_horizon_years", False),
        ("ecdat:assumption_source", "assumption_source", False),
    )
    for property_name, field_name, boolean in assessment_properties:
        value = finding.get(field_name)
        if value is not None:
            properties.append(
                {"name": property_name, "value": str(value).lower() if boolean else str(value)}
            )

    file_name = finding.get("file", "unknown")
    line = finding.get("line", 0)
    confidence = finding.get("confidence", "unverified")
    return {
        "type": "cryptographic-asset",
        "bom-ref": str(finding.get("bom_ref") or f"finding-{finding.get('id', index)}"),
        "name": algo,
        "version": _infer_version(algo, key_size),
        "description": f"{algo} detected at {file_name}:{line} (confidence={confidence})",
        "cryptoProperties": crypto_props,
        "evidence": {
            "occurrences": [
                {
                    "location": file_name,
                    "line": line,
                }
            ]
        },
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


def _report_provenance(scan: Scan) -> dict[str, Any]:
    """Return custody metadata when this scan came from a signed local bundle."""
    report = scan.report
    if report is None:
        return {"origin": "local-api", "integrity": "not-signed-bundle"}
    return {
        "origin": "offline-agent-signed-bundle",
        "report_id": report.report_id,
        "agent_id": report.agent_id,
        "organization_id": report.organization_id,
        "bundle_digest": report.bundle_digest,
        "signature_algorithm": report.signature_algorithm,
        "classification": report.classification,
    }

