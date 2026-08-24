"""Offline verification of the DATABASE lane against in-memory SQLite.

No Docker/Postgres required -- proves models + crud logic are correct so the
code is green before the team's Postgres is even installed. The same crud runs
unchanged on Postgres in production. Schema matches ARCHITECTURE.md.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db import crud
from db.models import Base, Finding


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
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


def test_cascade_delete(session):
    repo = crud.get_or_create_repository(session, name="c", url="u")
    scan = crud.start_scan(session, repo.id)
    crud.save_finding(session, scan.id, {"file": "x.py", "line": 1, "algorithm": "MD5"})
    session.commit()

    session.delete(scan)  # ON DELETE CASCADE removes findings
    session.commit()
    assert session.query(Finding).count() == 0
