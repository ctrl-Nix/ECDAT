"""Offline verification of the DATABASE lane against in-memory SQLite.

No Docker/Postgres required -- proves models + crud logic are correct so the
code is green before the team's Postgres is even installed. The same crud runs
unchanged on Postgres in production. Schema matches ARCHITECTURE.md.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from db import crud
from db.models import Base, Finding


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})

    # Enforce FK constraints on this engine so ON DELETE CASCADE works standalone
    # (SQLite ships with FK enforcement off). Self-contained -- does not rely on
    # api.database's global listener being imported first.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# --- normalizer ------------------------------------------------------------

def test_normalize_scanner_contract():
    cols = crud.normalize_finding(
        {"file": "a/b.py", "line": "42", "algorithm": "MD5", "confidence": "high"}
    )
    assert cols["file"] == "a/b.py"
    assert cols["line"] == 42
    assert cols["algorithm"] == "MD5"
    assert cols["criticality"] == "MEDIUM"   # default


def test_normalize_aliases_and_risk():
    cols = crud.normalize_finding(
        {
            "filePath": "keys.py",
            "keyLength": 1024,
            "algorithm": "RSA",
            "line": 7,
            "severity": "critical",          # alias -> risk_tier, upper-cased
            "criticality": "high",
        }
    )
    assert cols["file"] == "keys.py"
    assert cols["key_size"] == 1024
    assert cols["risk_tier"] == "CRITICAL"
    assert cols["criticality"] == "HIGH"


def test_normalize_defaults_never_crash():
    cols = crud.normalize_finding({"note": "no useful fields"})
    assert cols["file"] == "UNKNOWN"
    assert cols["algorithm"] == "UNKNOWN"
    assert cols["line"] == 0                 # NOT NULL column gets a default
    assert cols["risk_tier"] is None
    assert cols["criticality"] == "MEDIUM"
    # invalid tier is dropped to None
    assert crud.normalize_finding({"risk_tier": "bogus"})["risk_tier"] is None


# --- end-to-end crud -------------------------------------------------------

def test_full_scan_lifecycle(session):
    repo = crud.get_or_create_repository(
        session, name="demo", url="https://github.com/acme/demo"
    )
    again = crud.get_or_create_repository(session, name="whatever", url=repo.url)
    assert again.id == repo.id  # dedupe by url

    scan = crud.start_scan(session, repo.id)
    assert scan.status == "running"

    crud.save_findings(
        session,
        scan.id,
        [
            {"file": "hash.py", "line": 3, "algorithm": "MD5", "risk_tier": "HIGH"},
            {"filePath": "keys.py", "line": 10, "algorithm": "RSA",
             "keyLength": 1024, "risk_tier": "CRITICAL", "criticality": "CRITICAL"},
            {"file": "ok.py", "line": 9, "algorithm": "AES", "risk_tier": "LOW"},
        ],
    )
    crud.complete_scan(session, scan.id)
    session.commit()

    refreshed = crud.get_scan(session, scan.id)
    assert refreshed.status == "completed"

    assert len(crud.get_findings_for_scan(session, scan.id)) == 3

    crits = crud.get_findings_for_scan(session, scan.id, risk_tier="critical")
    assert len(crits) == 1 and crits[0].algorithm == "RSA"
    assert crits[0].key_size == 1024

    summary = crud.get_risk_summary(session, scan.id)
    assert summary == {
        "total": 3, "CRITICAL": 1, "HIGH": 1, "MEDIUM": 0, "LOW": 1, "UNSCORED": 0
    }

    payload = crud.get_scan_with_findings(session, scan.id)
    assert payload["scan"].id == scan.id
    assert len(payload["findings"]) == 3


def test_stores_all_scanner_and_risk_fields(session):
    """A full pipeline finding (scanner evidence + risk-engine output) must
    persist every field -- nothing dropped between scan and dashboard."""
    repo = crud.get_or_create_repository(session, name="r", url="r")
    scan = crud.start_scan(session, repo.id)
    # Shape mirrors scanner/finding.py enriched by risk_engine.score_finding.
    crud.save_finding(session, scan.id, {
        "file": "src/auth.py",
        "line": 14,
        "matched_call": "hashlib.md5",
        "library": "hashlib",
        "algorithm": "MD5",
        "primitive": "hash",
        "language": "python",
        "weak_by_default": True,
        "confidence": "high",
        "key_size": None,
        "detection_method": "static_analysis",
        "risk_tier": "CRITICAL",
        "risk_reason": "MD5 is classically broken.",
        "criticality": "HIGH",
        "quantum_vulnerable": False,
        "classical_broken": True,
        "recommended_replacement": "SHA-256",
        "recommendation_type": "classical",
    })
    session.commit()

    f = crud.get_findings_for_scan(session, scan.id)[0]
    assert f.matched_call == "hashlib.md5"
    assert f.library == "hashlib"
    assert f.primitive == "hash"
    assert f.language == "python"
    assert f.weak_by_default is True
    assert f.detection_method == "static_analysis"
    assert f.classical_broken is True
    assert f.quantum_vulnerable is False
    assert f.recommended_replacement == "SHA-256"
    assert f.recommendation_type == "classical"
    assert f.risk_tier == "CRITICAL"
    assert f.criticality == "HIGH"


def test_invalid_recommendation_type_dropped(session):
    cols = crud.normalize_finding({"algorithm": "MD5", "recommendation_type": "bogus"})
    assert cols["recommendation_type"] is None
    cols2 = crud.normalize_finding({"algorithm": "RSA", "recommendation_type": "hybrid"})
    assert cols2["recommendation_type"] == "hybrid"


def test_cascade_delete(session):
    repo = crud.get_or_create_repository(session, name="c", url="u")
    scan = crud.start_scan(session, repo.id)
    crud.save_finding(session, scan.id, {"file": "x.py", "line": 1, "algorithm": "MD5"})
    session.commit()

    session.delete(scan)  # ON DELETE CASCADE removes findings
    session.commit()
    assert session.query(Finding).count() == 0
