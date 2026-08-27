"""Regression tests for the scanner service orchestration path."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import db.crud as crud
from api.routers.scans import _run_scan_background
from api.services.scan_runner import run_scan
from db.models import Base


def test_run_scan_updates_the_queued_scan_record(tmp_path: Path):
    """A queued scan must receive its own findings and final status."""
    target = tmp_path / "legacy.py"
    target.write_text("import hashlib\nhashlib.md5(b'fixture')\n", encoding="utf-8")

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = crud.get_or_create_repository(session, name="fixture")
        session.flush()
        queued = crud.start_scan(session, repo_id=repository.id, status="pending")
        session.flush()

        result = run_scan(session, target_path=str(target), scan_id=queued.id)
        session.commit()

        assert result["scan_id"] == queued.id
        assert result["status"] == "completed"
        assert result["finding_count"] == 1

        scans = crud.list_scans(session)
        assert len(scans) == 1
        assert scans[0].id == queued.id
        assert scans[0].status == "completed"

        findings = crud.get_findings_for_scan(session, scan_id=queued.id)
        assert len(findings) == 1
        assert findings[0].algorithm == "MD5"


def test_background_worker_completes_the_existing_queued_scan(tmp_path: Path):
    """The API worker must not create another scan after POST /scans returns."""
    target = tmp_path / "legacy.py"
    target.write_text("import hashlib\nhashlib.md5(b'fixture')\n", encoding="utf-8")
    db_path = tmp_path / "worker.db"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = crud.get_or_create_repository(session, name="fixture")
        session.flush()
        queued = crud.start_scan(session, repo_id=repository.id, status="pending")
        session.commit()
        queued_id = queued.id

    _run_scan_background(
        target_path=str(target),
        repo_name="fixture",
        repo_url=None,
        scan_id=queued_id,
        db_url=db_url,
    )

    with Session(engine) as session:
        scans = crud.list_scans(session)
        assert len(scans) == 1
        assert scans[0].id == queued_id
        assert scans[0].status == "completed"
        assert len(crud.get_findings_for_scan(session, scan_id=queued_id)) == 1


def test_run_scan_persists_verified_mixed_language_risk_results(tmp_path: Path):
    """A mixed repository must produce risk-scored findings for reports."""
    target = tmp_path / "mixed-repository"
    target.mkdir()
    (target / "legacy.py").write_text(
        "import hashlib\nhashlib.new('md5', b'fixture')\n", encoding="utf-8"
    )
    (target / "CryptoUsage.java").write_text(
        "import javax.crypto.Cipher; class C { void run() throws Exception { "
        'Cipher.getInstance("DESede"); } }',
        encoding="utf-8",
    )
    (target / "crypto.js").write_text(
        "const crypto = require('node:crypto'); crypto.createHash('sha256');\n",
        encoding="utf-8",
    )
    (target / "lookalike.js").write_text(
        "const crypto = { createHash: () => undefined }; crypto.createHash('md5');\n",
        encoding="utf-8",
    )

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = run_scan(session, target_path=str(target))
        session.commit()

        assert result["status"] == "completed"
        assert result["finding_count"] == 3
        assert result["summary"] == {
            "total": 3,
            "CRITICAL": 1,
            "HIGH": 1,
            "MEDIUM": 0,
            "LOW": 1,
            "UNSCORED": 0,
        }

        findings = crud.get_findings_for_scan(session, scan_id=result["scan_id"])
        assert {(finding.algorithm, finding.risk_tier) for finding in findings} == {
            ("MD5", "CRITICAL"),
            ("3DES", "HIGH"),
            ("SHA-256", "LOW"),
        }
