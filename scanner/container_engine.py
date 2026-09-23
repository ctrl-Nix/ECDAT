"""
scanner/container_engine.py — Container image cryptographic discovery engine (CNT feature).

Scans container image archives (docker save tarballs) and OCI image layouts for:
1. X.509 certificates and private keys (detection_method="certificate_parse").
2. Installed cryptographic packages across Debian, Alpine, RPM, and language ecosystems
   (detection_method="container_package_inventory").

Public API (SYSTEM_INTERFACE_CONTRACT.md §3.1 & CONTAINER_SCANNING_SPEC.md §7.2):
    load_rules(rules_dir: Path) -> dict
    scan_file(path: Path, rules: dict | None = None) -> list[Finding]
    scan_directory(root: Path, rules: dict | None = None) -> list[Finding]
    scan_image_tar(image_tar: Path, rules: dict | None = None, *, max_bytes: int) -> list[Finding]
    scan_oci_layout(layout_dir: Path, rules: dict | None = None, *, max_bytes: int) -> list[Finding]
"""

from __future__ import annotations

import email
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed25519, rsa

from scanner.confidence import (
    ConfidenceSignal,
    calculate_confidence_score,
    legacy_confidence_for,
)
from scanner.constants import CONTAINER_LAYER_SKIP_PATHS, SCAN_MAX_ARTIFACT_BYTES
from scanner.finding import Finding
from scanner.image_layers import (
    ExtractedImage,
    ExtractedLayer,
    ImageLayoutError,
    ImageSizeLimitExceeded,
    cleanup,
    iter_files,
    open_image,
)

RULES_DIR = Path(__file__).resolve().parent / "rules"
RULES_FILE = RULES_DIR / "container.yaml"


@dataclass
class ContainerFinding(Finding):
    """Finding subclass adding container-specific artifact fields."""
    artifact_type: str = "CONTAINER_LAYER"
    artifact_ref: Optional[str] = None
    image_digest: Optional[str] = None
    layer_digest: Optional[str] = None
    package_ecosystem: Optional[str] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None


def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


# ─── Rule Loading ─────────────────────────────────────────────────────────────

def load_rules(rules_dir: Path) -> dict[str, Any]:
    """Load container rules from container.yaml in the specified directory."""
    p = rules_dir / "container.yaml" if rules_dir.is_dir() else rules_dir
    if not p.is_file():
        _warn(f"Container rules file not found: {p}")
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception as exc:
        _warn(f"Failed to load container rules from {p}: {exc}")
        return {}


def _get_package_rules(rules: dict | None) -> list[dict[str, Any]]:
    if isinstance(rules, dict):
        if "rules" in rules and isinstance(rules["rules"], list):
            return rules["rules"]
    loaded = load_rules(RULES_DIR)
    return loaded.get("rules", [])


# ─── Certificate Detector ─────────────────────────────────────────────────────

PEM_CERT_HEADER = b"-----BEGIN CERTIFICATE-----"
PEM_RSA_KEY_HEADER = b"-----BEGIN RSA PRIVATE KEY-----"
PEM_KEY_HEADER = b"-----BEGIN PRIVATE KEY-----"
PEM_EC_KEY_HEADER = b"-----BEGIN EC PRIVATE KEY-----"


def _parse_certificate_data(
    data: bytes,
    file_label: str,
    image_digest: str,
    layer_digest: str,
) -> list[Finding]:
    """Parse PEM or DER encoded X.509 certificate or private key; return findings."""
    findings: list[Finding] = []

    cert = None
    if PEM_CERT_HEADER in data:
        try:
            cert = x509.load_pem_x509_certificate(data)
        except Exception:
            pass
    elif len(data) >= 4 and data[0] == 0x30:
        try:
            cert = x509.load_der_x509_certificate(data)
        except Exception:
            pass

    if cert is not None:
        try:
            public_key = cert.public_key()
            algo = "UNKNOWN"
            key_size: Optional[int] = None
            primitive = "publicKeyEncryption"
            weak_by_default = False

            if isinstance(public_key, rsa.RSAPublicKey):
                algo = "RSA"
                key_size = public_key.key_size
                primitive = "publicKeyEncryption"
                weak_by_default = key_size < 2048
            elif isinstance(public_key, dsa.DSAPublicKey):
                algo = "DSA"
                key_size = public_key.key_size
                primitive = "digitalSignature"
                weak_by_default = True
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                algo = "ECDSA"
                key_size = public_key.curve.key_size
                primitive = "digitalSignature"
                weak_by_default = False
            elif isinstance(public_key, ed25519.Ed25519PublicKey):
                algo = "Ed25519"
                key_size = 256
                primitive = "digitalSignature"
                weak_by_default = False

            # Check weak signature algorithm (MD5 / SHA1)
            try:
                sig_hash = cert.signature_hash_algorithm
                if sig_hash is not None and sig_hash.name.lower() in ("md5", "sha1"):
                    weak_by_default = True
            except Exception:
                pass

            signals = [
                ConfidenceSignal.IMPORT_RESOLVED.value,
                ConfidenceSignal.CALL_SITE_MATCHED.value,
                ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value,
                ConfidenceSignal.LITERAL_ALGORITHM_ARG.value,
            ]
            if key_size is not None:
                signals.append(ConfidenceSignal.KEY_SIZE_EXTRACTED.value)
            verdict = calculate_confidence_score(signals)

            matched_call = (
                "x509.load_pem_x509_certificate"
                if PEM_CERT_HEADER in data
                else "x509.load_der_x509_certificate"
            )

            findings.append(
                ContainerFinding(
                    file=file_label,
                    line=0,
                    matched_call=matched_call,
                    library="openssl",
                    algorithm=algo,
                    primitive=primitive,
                    language="n/a",
                    weak_by_default=weak_by_default,
                    confidence="high",
                    key_size=key_size,
                    detection_method="certificate_parse",
                    confidence_score=verdict.score,
                    confidence_band=verdict.band,
                    confidence_signals=verdict.signals,
                    confidence_model_version=verdict.model_version,
                    artifact_type="CONTAINER_LAYER",
                    artifact_ref=file_label,
                    image_digest=image_digest,
                    layer_digest=layer_digest,
                    package_ecosystem=None,
                    package_name=None,
                    package_version=None,
                )
            )
        except Exception as exc:
            _warn(f"Error extracting certificate properties from {file_label}: {exc}")

    # Check for private keys
    if not findings and (
        PEM_RSA_KEY_HEADER in data or PEM_KEY_HEADER in data or PEM_EC_KEY_HEADER in data
    ):
        try:
            priv_key = serialization.load_pem_private_key(data, password=None)
            algo = "UNKNOWN"
            key_size = None
            primitive = "key_exchange"
            weak_by_default = False

            if isinstance(priv_key, rsa.RSAPrivateKey):
                algo = "RSA"
                key_size = priv_key.key_size
                primitive = "publicKeyEncryption"
                weak_by_default = key_size < 2048
            elif isinstance(priv_key, dsa.DSAPrivateKey):
                algo = "DSA"
                key_size = priv_key.key_size
                primitive = "digitalSignature"
                weak_by_default = True
            elif isinstance(priv_key, ec.EllipticCurvePrivateKey):
                algo = "ECDSA"
                key_size = priv_key.curve.key_size
                primitive = "digitalSignature"
                weak_by_default = False

            signals = [
                ConfidenceSignal.IMPORT_RESOLVED.value,
                ConfidenceSignal.CALL_SITE_MATCHED.value,
                ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value,
                ConfidenceSignal.LITERAL_ALGORITHM_ARG.value,
            ]
            if key_size is not None:
                signals.append(ConfidenceSignal.KEY_SIZE_EXTRACTED.value)
            verdict = calculate_confidence_score(signals)

            findings.append(
                ContainerFinding(
                    file=file_label,
                    line=0,
                    matched_call="serialization.load_pem_private_key",
                    library="openssl",
                    algorithm=algo,
                    primitive=primitive,
                    language="n/a",
                    weak_by_default=weak_by_default,
                    confidence="high",
                    key_size=key_size,
                    detection_method="certificate_parse",
                    confidence_score=verdict.score,
                    confidence_band=verdict.band,
                    confidence_signals=verdict.signals,
                    confidence_model_version=verdict.model_version,
                    artifact_type="CONTAINER_LAYER",
                    artifact_ref=file_label,
                    image_digest=image_digest,
                    layer_digest=layer_digest,
                    package_ecosystem=None,
                    package_name=None,
                    package_version=None,
                )
            )
        except Exception:
            pass

    return findings


# ─── Package Inventory Detector ───────────────────────────────────────────────

def _parse_dpkg_status(text: str) -> list[tuple[str, str]]:
    """Parse Debian /var/lib/dpkg/status into list of (package_name, version)."""
    packages: list[tuple[str, str]] = []
    blocks = text.split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        try:
            msg = email.message_from_string(block)
            pkg_name = msg.get("Package", "").strip()
            version = msg.get("Version", "").strip()
            status = msg.get("Status", "").strip()
            if pkg_name:
                # Include installed packages (e.g. "install ok installed")
                if not status or "installed" in status:
                    packages.append((pkg_name, version or "unknown"))
        except Exception:
            continue
    return packages


def _parse_apk_installed(text: str) -> list[tuple[str, str]]:
    """Parse Alpine /lib/apk/db/installed into list of (package_name, version)."""
    packages: list[tuple[str, str]] = []
    blocks = text.split("\n\n")
    for block in blocks:
        if not block.strip():
            continue
        pkg_name = ""
        version = ""
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("P:"):
                pkg_name = line[2:].strip()
            elif line.startswith("V:"):
                version = line[2:].strip()
        if pkg_name:
            packages.append((pkg_name, version or "unknown"))
    return packages


def _parse_rpm_db(file_path: Path) -> list[tuple[str, str]]:
    """Extract package names from RPM database files (NDB / BDB)."""
    packages: list[tuple[str, str]] = []
    try:
        data = file_path.read_bytes()
        # Scan for printable strings or package headers in RPM db
        import re
        matches = re.findall(rb"([a-zA-Z0-9_\-\+]{2,64})-([0-9][a-zA-Z0-9_\.\-\+]{1,32})", data)
        for name_b, ver_b in matches:
            name = name_b.decode("ascii", errors="ignore")
            ver = ver_b.decode("ascii", errors="ignore")
            if any(name.startswith(p) for p in ("openssl", "libgcrypt", "nss", "gnutls")):
                packages.append((name, ver))
    except Exception:
        pass
    return packages


def _match_package_rules(
    packages: list[tuple[str, str]],
    ecosystem: str,
    rules: list[dict[str, Any]],
    image_digest: str,
    layer_digest: str,
    in_layer_ref: str,
) -> list[Finding]:
    """Match a list of (pkg_name, version) against rules for the given ecosystem."""
    findings: list[Finding] = []
    seen: set[str] = set()

    for pkg_name, version in packages:
        for rule in rules:
            if rule.get("ecosystem") != ecosystem:
                continue
            rule_pkg = rule.get("package", "")
            if not rule_pkg:
                continue

            # Exact or substring match for package name
            if pkg_name == rule_pkg or pkg_name.startswith(f"{rule_pkg}-") or pkg_name.startswith(f"{rule_pkg}_"):
                if pkg_name in seen:
                    continue
                seen.add(pkg_name)

                signals = [
                    ConfidenceSignal.IMPORT_RESOLVED.value,
                    ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value,
                    ConfidenceSignal.RULE_YAML_MATCHED.value,
                ]
                verdict = calculate_confidence_score(signals)

                f = ContainerFinding(
                    file=f"{layer_digest}:{pkg_name}",
                    line=0,
                    matched_call=f"{ecosystem}:{pkg_name}=={version}",
                    library=rule.get("library", "unknown"),
                    algorithm=rule["algorithm"],
                    primitive=rule.get("primitive", "unknown"),
                    language="n/a",
                    weak_by_default=rule.get("weak_by_default", False),
                    confidence="high",
                    key_size=rule.get("key_size"),
                    detection_method="container_package_inventory",
                    confidence_score=verdict.score,
                    confidence_band=verdict.band,
                    confidence_signals=verdict.signals,
                    confidence_model_version=verdict.model_version,
                    artifact_type="CONTAINER_LAYER",
                    artifact_ref=f"{layer_digest}:{pkg_name}",
                    image_digest=image_digest,
                    layer_digest=layer_digest,
                    package_ecosystem=ecosystem,
                    package_name=pkg_name,
                    package_version=version,
                )
                findings.append(f)

    return findings


# ─── Image Scanning Workflow ──────────────────────────────────────────────────

def _scan_extracted_image(
    image: ExtractedImage,
    rules: dict | None = None,
) -> list[Finding]:
    """Run certificate and package detectors across an ExtractedImage."""
    findings: list[Finding] = []
    pkg_rules = _get_package_rules(rules)
    merged_root = image.merged_root
    image_digest = image.image_digest

    # 1. Package Inventory Detector: check OS package manager databases
    # Debian dpkg
    dpkg_status = merged_root / "var" / "lib" / "dpkg" / "status"
    if dpkg_status.is_file():
        try:
            layer = image._file_layer_map.get("var/lib/dpkg/status", image.layers[-1] if image.layers else None)
            l_digest = layer.layer_digest if layer else "sha256:unknown"
            text = dpkg_status.read_text(encoding="utf-8", errors="ignore")
            pkgs = _parse_dpkg_status(text)
            findings.extend(_match_package_rules(pkgs, "deb", pkg_rules, image_digest, l_digest, "var/lib/dpkg/status"))
        except Exception as exc:
            _warn(f"Failed to scan dpkg status database: {exc}")

    # Alpine apk
    apk_installed = merged_root / "lib" / "apk" / "db" / "installed"
    if apk_installed.is_file():
        try:
            layer = image._file_layer_map.get("lib/apk/db/installed", image.layers[-1] if image.layers else None)
            l_digest = layer.layer_digest if layer else "sha256:unknown"
            text = apk_installed.read_text(encoding="utf-8", errors="ignore")
            pkgs = _parse_apk_installed(text)
            findings.extend(_match_package_rules(pkgs, "apk", pkg_rules, image_digest, l_digest, "lib/apk/db/installed"))
        except Exception as exc:
            _warn(f"Failed to scan apk installed database: {exc}")

    # RPM
    rpm_dir = merged_root / "var" / "lib" / "rpm"
    if rpm_dir.is_dir():
        for rpm_file in rpm_dir.glob("Packages*"):
            try:
                layer = image._file_layer_map.get(f"var/lib/rpm/{rpm_file.name}", image.layers[-1] if image.layers else None)
                l_digest = layer.layer_digest if layer else "sha256:unknown"
                pkgs = _parse_rpm_db(rpm_file)
                findings.extend(_match_package_rules(pkgs, "rpm", pkg_rules, image_digest, l_digest, f"var/lib/rpm/{rpm_file.name}"))
            except Exception as exc:
                _warn(f"Failed to scan RPM database {rpm_file}: {exc}")

    # 2. Certificate Detector: iterate files in the merged view
    for layer, fpath in iter_files(image):
        rel_posix = fpath.relative_to(merged_root).as_posix()
        # Skip directories listed in CONTAINER_LAYER_SKIP_PATHS
        if any(rel_posix.startswith(p) or f"/{p}/" in f"/{rel_posix}/" for p in CONTAINER_LAYER_SKIP_PATHS):
            continue

        try:
            st = fpath.stat()
            if st.st_size > 2 * 1024 * 1024:  # Certs are small; skip huge files
                continue
            data = fpath.read_bytes()
            if not data:
                continue

            # Sniff for cert / key signatures
            if (
                PEM_CERT_HEADER in data
                or PEM_RSA_KEY_HEADER in data
                or PEM_KEY_HEADER in data
                or PEM_EC_KEY_HEADER in data
                or (len(data) >= 4 and data[0] == 0x30 and fpath.suffix in (".der", ".crt", ".cer"))
            ):
                file_label = f"{layer.layer_digest}:{rel_posix}"
                cert_findings = _parse_certificate_data(data, file_label, image_digest, layer.layer_digest)
                findings.extend(cert_findings)
        except Exception as exc:
            _warn(f"Error reading {fpath}: {exc}")
            continue

    return findings


# ─── Public API ───────────────────────────────────────────────────────────────

def scan_image_tar(
    image_tar: Path,
    rules: dict | None = None,
    *,
    max_bytes: int = SCAN_MAX_ARTIFACT_BYTES,
) -> list[Finding]:
    """Scan a container image tarball (.tar) for cryptographic assets."""
    image = open_image(image_tar, max_bytes=max_bytes)
    try:
        return _scan_extracted_image(image, rules)
    finally:
        cleanup(image)


def scan_oci_layout(
    layout_dir: Path,
    rules: dict | None = None,
    *,
    max_bytes: int = SCAN_MAX_ARTIFACT_BYTES,
) -> list[Finding]:
    """Scan an unpacked OCI layout directory for cryptographic assets."""
    image = open_image(layout_dir, max_bytes=max_bytes)
    try:
        return _scan_extracted_image(image, rules)
    finally:
        cleanup(image)


def scan_file(path: Path, rules: dict | None = None) -> list[Finding]:
    """Scan a single file (image tarball or standalone certificate file)."""
    p = Path(path).resolve()
    if not p.exists():
        _warn(f"Path does not exist: {p}")
        return []

    # If image tarball
    if p.suffix == ".tar" or tarfile.is_tarfile(p):
        try:
            return scan_image_tar(p, rules=rules, max_bytes=SCAN_MAX_ARTIFACT_BYTES)
        except ImageLayoutError:
            pass
        except Exception as exc:
            _warn(f"Failed scanning image tar {p}: {exc}")
            return []

    # Single certificate / key file scan
    try:
        data = p.read_bytes()
        return _parse_certificate_data(data, str(p), "sha256:local_file", "sha256:local_file")
    except Exception as exc:
        _warn(f"Cannot read file {p}: {exc}")
        return []


def scan_directory(root: Path, rules: dict | None = None) -> list[Finding]:
    """Scan a directory for container images or OCI layouts."""
    root_path = Path(root).resolve()
    if not root_path.exists():
        _warn(f"Root path does not exist: {root_path}")
        return []

    # If the directory itself is an OCI layout
    if (root_path / "index.json").is_file() and (root_path / "blobs").is_dir():
        try:
            return scan_oci_layout(root_path, rules=rules, max_bytes=SCAN_MAX_ARTIFACT_BYTES)
        except Exception as exc:
            _warn(f"Failed scanning OCI layout at {root_path}: {exc}")
            return []

    all_findings: list[Finding] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.suffix == ".tar":
                try:
                    all_findings.extend(scan_image_tar(fpath, rules=rules, max_bytes=SCAN_MAX_ARTIFACT_BYTES))
                except ImageLayoutError:
                    continue
                except Exception as exc:
                    _warn(f"Failed scanning tar {fpath}: {exc}")
                    continue

    return all_findings
