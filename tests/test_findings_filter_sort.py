import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db import crud
from db.models import Base


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


@pytest.fixture()
def populated_scan(session):
    repo = crud.get_or_create_repository(session, name="filter-sort", url="https://example.test/filter-sort")
    scan = crud.start_scan(session, repo.id)
    crud.save_findings(session, scan.id, [
        {"file": "a.py", "line": 1, "algorithm": "MD5", "risk_tier": "CRITICAL", "language": "python", "primitive": "hash"},
        {"file": "b.java", "line": 2, "algorithm": "RSA", "risk_tier": "HIGH", "language": "java", "primitive": "asymmetric-cipher"},
        {"file": "c.js", "line": 3, "algorithm": "AES", "risk_tier": "LOW", "language": "javascript", "primitive": "symmetric-cipher"},
    ])
    session.commit()
    return scan.id


def test_risk_tier_list_uses_or_within_category(session, populated_scan):
    findings = crud.get_findings_for_scan(session, populated_scan, risk_tier=["CRITICAL", "HIGH"])
    assert {finding.risk_tier for finding in findings} == {"CRITICAL", "HIGH"}


def test_filters_use_and_across_categories(session, populated_scan):
    findings = crud.get_findings_for_scan(
        session, populated_scan, risk_tier=["CRITICAL", "HIGH"], language=["java"]
    )
    assert [finding.algorithm for finding in findings] == ["RSA"]


def test_sort_by_algorithm_descending(session, populated_scan):
    findings = crud.get_findings_for_scan(session, populated_scan, sort_by="algorithm", sort_dir="desc")
    assert [finding.algorithm for finding in findings] == ["RSA", "MD5", "AES"]


def test_empty_filter_list_is_ignored_and_default_order_is_stable(session, populated_scan):
    expected = crud.get_findings_for_scan(session, populated_scan)
    actual = crud.get_findings_for_scan(session, populated_scan, primitive=[], algorithm=[], language=[])
    assert [finding.id for finding in actual] == [finding.id for finding in expected]
