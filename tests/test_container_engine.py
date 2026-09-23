"""
tests/test_container_engine.py — Unit and integration tests for scanner/container_engine.py (CNT feature).
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from api.services.risk_engine import score_findings
from scanner import container_engine, image_layers
from scanner.container_engine import (
    load_rules,
    scan_directory,
    scan_file,
    scan_image_tar,
    scan_oci_layout,
)
from scanner.image_layers import ImageLayoutError, ImageSizeLimitExceeded

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "container"


def test_load_rules_returns_dict():
    """Rules file scanner/rules/container.yaml loads and returns a non-empty dictionary."""
    rules = load_rules(Path("scanner/rules"))
    assert isinstance(rules, dict)
    assert "rules" in rules
    assert len(rules["rules"]) > 0


def test_pem_cert_rsa1024_detected_weak():
    """PEM certificate with RSA-1024 key size is detected and marked weak."""
    tar_path = FIXTURES_DIR / "debian_rsa1024.tar"
    findings = scan_image_tar(tar_path)
    assert len(findings) >= 2

    cert_findings = [f for f in findings if f.detection_method == "certificate_parse"]
    assert len(cert_findings) == 1

    cf = cert_findings[0]
    assert cf.algorithm == "RSA"
    assert cf.key_size == 1024
    assert cf.weak_by_default is True
    assert cf.confidence == "high"
    assert cf.confidence_band == "VERIFIED"
    assert cf.confidence_score >= 0.85
    assert cf.artifact_type == "CONTAINER_LAYER"
    assert "server.pem" in cf.artifact_ref

    scored = score_findings([cf.to_dict()])
    assert scored[0]["risk_tier"] == "CRITICAL"


def test_pem_cert_rsa2048_detected_clean():
    """PEM certificate with RSA-2048 key size is detected and not marked weak."""
    tar_path = FIXTURES_DIR / "alpine_libcrypto.tar"
    findings = scan_image_tar(tar_path)

    cert_findings = [f for f in findings if f.detection_method == "certificate_parse"]
    assert len(cert_findings) == 1

    cf = cert_findings[0]
    assert cf.algorithm == "RSA"
    assert cf.key_size == 2048
    assert cf.weak_by_default is False
    assert cf.confidence == "high"


def test_apk_package_inventory_detected():
    """Alpine lib/apk/db/installed entries are parsed and mapped to package inventory findings."""
    tar_path = FIXTURES_DIR / "alpine_libcrypto.tar"
    findings = scan_image_tar(tar_path)

    pkg_findings = [f for f in findings if f.detection_method == "container_package_inventory"]
    assert len(pkg_findings) == 1

    pf = pkg_findings[0]
    assert pf.package_ecosystem == "apk"
    assert pf.package_name == "libcrypto3"
    assert pf.package_version == "3.0.8-r0"
    assert pf.algorithm == "RSA"
    assert pf.artifact_type == "CONTAINER_LAYER"
    assert pf.confidence == "high"


def test_dpkg_package_inventory_detected():
    """Debian var/lib/dpkg/status entries are parsed and mapped to package inventory findings."""
    tar_path = FIXTURES_DIR / "debian_rsa1024.tar"
    findings = scan_image_tar(tar_path)

    pkg_findings = [f for f in findings if f.detection_method == "container_package_inventory"]
    assert len(pkg_findings) == 1

    pf = pkg_findings[0]
    assert pf.package_ecosystem == "deb"
    assert pf.package_name == "libssl3"
    assert "3.0.2" in pf.package_version


def test_whiteout_suppresses_deleted_file():
    """A whiteout (.wh.<file>) in an upper layer deletes the lower file from the merged view."""
    tar_path = FIXTURES_DIR / "whiteout_test.tar"
    findings = scan_image_tar(tar_path)
    assert len(findings) == 0


def test_oci_layout_scanning():
    """An unpacked OCI image layout directory is scanned for package inventory and certs."""
    oci_path = FIXTURES_DIR / "oci_layout_sample"
    findings = scan_oci_layout(oci_path)
    assert len(findings) >= 1

    pf = findings[0]
    assert pf.package_name == "libgcrypt20"
    assert pf.package_ecosystem == "deb"


def test_rejects_absolute_path(tmp_path, capsys):
    """Tar entries with absolute paths are refused with a warning without aborting extraction."""
    bad_tar = tmp_path / "bad_abs.tar"
    manifest_data = json.dumps([{"Config": "cfg.json", "Layers": ["layer.tar"]}]).encode("utf-8")
    cfg_data = b"{}"

    # Inner layer with absolute path
    layer_buf = io.BytesIO()
    with tarfile.open(fileobj=layer_buf, mode="w") as t:
        ti = tarfile.TarInfo(name="/etc/ssl/certs/evil.pem")
        ti.size = 10
        t.addfile(ti, io.BytesIO(b"evil cert!"))

    # Outer tar
    with tarfile.open(bad_tar, mode="w") as outer:
        ti_m = tarfile.TarInfo(name="manifest.json")
        ti_m.size = len(manifest_data)
        outer.addfile(ti_m, io.BytesIO(manifest_data))
        ti_c = tarfile.TarInfo(name="cfg.json")
        ti_c.size = len(cfg_data)
        outer.addfile(ti_c, io.BytesIO(cfg_data))
        ti_l = tarfile.TarInfo(name="layer.tar")
        ti_l.size = len(layer_buf.getvalue())
        outer.addfile(ti_l, io.BytesIO(layer_buf.getvalue()))

    findings = scan_image_tar(bad_tar)
    assert len(findings) == 0
    err = capsys.readouterr().err
    assert "Refusing path traversal" in err


def test_rejects_dotdot_path(tmp_path, capsys):
    """Tar entries containing '..' path components are refused with a warning."""
    bad_tar = tmp_path / "bad_dotdot.tar"
    manifest_data = json.dumps([{"Config": "cfg.json", "Layers": ["layer.tar"]}]).encode("utf-8")
    cfg_data = b"{}"

    layer_buf = io.BytesIO()
    with tarfile.open(fileobj=layer_buf, mode="w") as t:
        ti = tarfile.TarInfo(name="../etc/ssl/certs/evil.pem")
        ti.size = 10
        t.addfile(ti, io.BytesIO(b"evil cert!"))

    with tarfile.open(bad_tar, mode="w") as outer:
        ti_m = tarfile.TarInfo(name="manifest.json")
        ti_m.size = len(manifest_data)
        outer.addfile(ti_m, io.BytesIO(manifest_data))
        ti_c = tarfile.TarInfo(name="cfg.json")
        ti_c.size = len(cfg_data)
        outer.addfile(ti_c, io.BytesIO(cfg_data))
        ti_l = tarfile.TarInfo(name="layer.tar")
        ti_l.size = len(layer_buf.getvalue())
        outer.addfile(ti_l, io.BytesIO(layer_buf.getvalue()))

    findings = scan_image_tar(bad_tar)
    assert len(findings) == 0
    err = capsys.readouterr().err
    assert "Refusing path traversal" in err


def test_size_limit_enforced(tmp_path):
    """Image extraction exceeding max_bytes raises ImageSizeLimitExceeded."""
    tar_path = FIXTURES_DIR / "alpine_libcrypto.tar"
    with pytest.raises(ImageSizeLimitExceeded):
        scan_image_tar(tar_path, max_bytes=100)


def test_non_image_scan_directory_returns_empty(tmp_path):
    """Scanning a directory without container images returns an empty list."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    findings = scan_directory(empty_dir)
    assert findings == []


def test_invalid_image_raises_layout_error(tmp_path):
    """Tar archive lacking manifest.json and index.json raises ImageLayoutError."""
    fake_tar = tmp_path / "fake.tar"
    with tarfile.open(fake_tar, mode="w") as t:
        ti = tarfile.TarInfo(name="dummy.txt")
        ti.size = 5
        t.addfile(ti, io.BytesIO(b"hello"))

    with pytest.raises(ImageLayoutError):
        scan_image_tar(fake_tar)


def test_cli_smoke_certificate_detector(capsys):
    """CLI smoke test: certificate detector on debian_rsa1024.tar fixture image."""
    from scanner.cli import main
    tar_path = FIXTURES_DIR / "debian_rsa1024.tar"
    exit_code = main(["--scan-type", "container", "--image-tar", str(tar_path)])
    assert exit_code == 0

    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) >= 1

    cert_findings = [f for f in data if f.get("detection_method") == "certificate_parse"]
    assert len(cert_findings) == 1
    cf = cert_findings[0]
    assert cf["algorithm"] == "RSA"
    assert cf["key_size"] == 1024
    assert cf["artifact_type"] == "CONTAINER_LAYER"
    assert cf["risk_tier"] == "CRITICAL"


def test_cli_smoke_package_detector(capsys):
    """CLI smoke test: package detector on alpine_libcrypto.tar fixture image."""
    from scanner.cli import main
    tar_path = FIXTURES_DIR / "alpine_libcrypto.tar"
    exit_code = main(["--scan-type", "container", "--image-tar", str(tar_path)])
    assert exit_code == 0

    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) >= 1

    pkg_findings = [f for f in data if f.get("detection_method") == "container_package_inventory"]
    assert len(pkg_findings) == 1
    pf = pkg_findings[0]
    assert pf["package_ecosystem"] == "apk"
    assert pf["package_name"] == "libcrypto3"
    assert pf["artifact_type"] == "CONTAINER_LAYER"


def test_cli_policy_gate_fail_on():
    """Policy gate: --fail-on CRITICAL returns 2 when RSA-1024 cert is present."""
    from scanner.cli import main
    tar_path = FIXTURES_DIR / "debian_rsa1024.tar"
    exit_code = main(["--scan-type", "container", "--image-tar", str(tar_path), "--fail-on", "CRITICAL"])
    assert exit_code == 2
