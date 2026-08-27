"""Signed, portable ECDAT report bundles for controlled post-scan delivery.

Scanning remains local and offline.  This module serializes only scanner findings,
their deterministic assessment, and bounded scan metadata.  A separate explicit
sync operation may submit the signed bundle to a dashboard ingestion API.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


BUNDLE_VERSION = "1.0"
SIGNATURE_ALGORITHM = "Ed25519"


class ReportBundleError(ValueError):
    """Raised when a report bundle is malformed or cannot be authenticated."""


def canonical_json(value: dict[str, Any]) -> bytes:
    """Return the single deterministic representation used for signing."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def payload_digest(value: dict[str, Any]) -> str:
    """Return a prefixed SHA-256 digest of unsigned canonical bundle content."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    """Load an Ed25519 PEM private key held by the local scanning agent."""
    key_data = Path(path).read_bytes()
    key = serialization.load_pem_private_key(key_data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ReportBundleError("Signing key must be an Ed25519 private key")
    return key


def public_key_to_base64(key: Ed25519PrivateKey | Ed25519PublicKey) -> str:
    """Encode an Ed25519 public key for secure agent enrollment configuration."""
    public_key = key.public_key() if isinstance(key, Ed25519PrivateKey) else key
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def public_key_from_base64(value: str) -> Ed25519PublicKey:
    """Decode an enrolled raw Ed25519 public key."""
    try:
        raw = base64.b64decode(value, validate=True)
        return Ed25519PublicKey.from_public_bytes(raw)
    except (ValueError, TypeError) as exc:
        raise ReportBundleError("Invalid enrolled Ed25519 public key") from exc


def build_bundle(
    *,
    organization_id: str,
    repository_id: str,
    agent_id: str,
    findings: list[dict[str, Any]],
    summary: dict[str, int],
    scan_context: dict[str, Any],
) -> dict[str, Any]:
    """Create the unsigned data that a local scanning agent will sign."""
    if not all((organization_id.strip(), repository_id.strip(), agent_id.strip())):
        raise ReportBundleError("organization_id, repository_id, and agent_id are required")
    return {
        "bundle_version": BUNDLE_VERSION,
        "report_id": str(uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        "organization_id": organization_id.strip(),
        "repository_id": repository_id.strip(),
        "agent_id": agent_id.strip(),
        "scan_context": scan_context,
        "findings": findings,
        "summary": summary,
    }


def sign_bundle(payload: dict[str, Any], private_key: Ed25519PrivateKey) -> dict[str, Any]:
    """Attach a detached Ed25519 signature and deterministic digest to a bundle."""
    unsigned = dict(payload)
    unsigned.pop("signature", None)
    unsigned.pop("signature_algorithm", None)
    unsigned.pop("bundle_digest", None)
    signature = private_key.sign(canonical_json(unsigned))
    return {
        **unsigned,
        "bundle_digest": payload_digest(unsigned),
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def verify_bundle(bundle: dict[str, Any], public_key_b64: str) -> dict[str, Any]:
    """Verify signature and digest, returning authenticated unsigned content."""
    if bundle.get("signature_algorithm") != SIGNATURE_ALGORITHM:
        raise ReportBundleError("Unsupported or missing report signature algorithm")
    encoded_signature = bundle.get("signature")
    claimed_digest = bundle.get("bundle_digest")
    if not isinstance(encoded_signature, str) or not isinstance(claimed_digest, str):
        raise ReportBundleError("Report bundle is missing signature or digest")

    unsigned = dict(bundle)
    unsigned.pop("signature", None)
    unsigned.pop("signature_algorithm", None)
    unsigned.pop("bundle_digest", None)
    if payload_digest(unsigned) != claimed_digest:
        raise ReportBundleError("Report bundle digest does not match its content")

    try:
        signature = base64.b64decode(encoded_signature, validate=True)
        public_key_from_base64(public_key_b64).verify(signature, canonical_json(unsigned))
    except Exception as exc:  # cryptography intentionally uses several exception types
        raise ReportBundleError("Report bundle signature verification failed") from exc
    return unsigned
