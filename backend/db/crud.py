"""Data-access functions - the only place the app writes/reads crypto data.

Day-3 deliverable: the FastAPI routes call these instead of writing raw SQL, so
all query logic stays in one reviewed place.

Primary entry points:
    get_or_create_repository()  - dedupe repos by url/name
    start_scan() / save_scan()  - open a scan row (status 'running')
    save_finding()              - persist one finding (tolerant of key naming)
    save_findings()             - bulk persist
    complete_scan()             - mark a scan finished
    get_scan()                  - one scan
    get_scan_with_findings()    - scan + its findings (the GET /scans/{id} payload)
    get_findings_for_scan()     - findings for a scan, optional risk_tier filter
    get_risk_summary()          - risk-tier counts for the dashboard header

The finding normalizer follows the ARCHITECTURE.md contract
    {file, line, algorithm, key_size, confidence, risk_tier, risk_reason, criticality}
but accepts common aliases (file_path/filePath, keyLength, severity->risk_tier)
so small scanner-output variations don't break a scan write.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import (
    CRITICALITIES,
    RISK_TIERS,
    SCAN_STATUSES,
    Finding,
    Repository,
    Scan,
)

# Maps every accepted incoming key (lower-cased, spaces stripped) to a column.
_FINDING_KEY_ALIASES: dict[str, str] = {
    "file": "file",
    "filepath": "file",
    "file_path": "file",
    "path": "file",
    "line": "line",
    "line_number": "line",
    "lineno": "line",
    "algorithm": "algorithm",
    "algo": "algorithm",
    "key_size": "key_size",
    "keysize": "key_size",
    "keylength": "key_size",
    "key_length": "key_size",
    "confidence": "confidence",
    "risk_tier": "risk_tier",
    "risktier": "risk_tier",
    "severity": "risk_tier",
    "tier": "risk_tier",
    "risk_reason": "risk_reason",
    "riskreason": "risk_reason",
    "reason": "risk_reason",
    "criticality": "criticality",
}


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Turn an arbitrary finding dict into validated Finding column kwargs."""
    cols: dict[str, Any] = {}
    for key, value in finding.items():
        target = _FINDING_KEY_ALIASES.get(str(key).lower().replace(" ", ""))
        if target and value is not None and cols.get(target) in (None, ""):
            cols[target] = value

    # NOT NULL columns get safe fallbacks so a partial finding never crashes a
    # scan write (storing 90% of findings beats 500-ing on one bad row).
    cols["file"] = str(cols.get("file") or "UNKNOWN").strip() or "UNKNOWN"
    cols["algorithm"] = str(cols.get("algorithm") or "UNKNOWN").strip() or "UNKNOWN"
    line = _coerce_int(cols.get("line"))
    cols["line"] = 0 if line is None else line          # column is NOT NULL
    cols["key_size"] = _coerce_int(cols.get("key_size"))

    cols["confidence"] = str(cols.get("confidence") or "high").strip().lower()

    tier = cols.get("risk_tier")
    if tier is None or str(tier).strip() == "":
        cols["risk_tier"] = None
    else:
        tier = str(tier).strip().upper()
        cols["risk_tier"] = tier if tier in RISK_TIERS else None

    crit = str(cols.get("criticality") or "MEDIUM").strip().upper()
    cols["criticality"] = crit if crit in CRITICALITIES else "MEDIUM"

    return cols


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

def get_or_create_repository(
    session: Session, name: str, url: str | None = None
) -> Repository:
    """Return the existing repo (matched by url, else exact name) or create it."""
    if url:
        stmt = select(Repository).where(Repository.url == url)
    else:
        stmt = select(Repository).where(
            Repository.url.is_(None), Repository.name == name
        )
    existing = session.scalars(stmt).first()
    if existing:
        return existing

    repo = Repository(name=name, url=url)
    session.add(repo)
    session.flush()  # assign PK without ending the transaction
    return repo


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------

def start_scan(session: Session, repo_id: int, status: str = "running") -> Scan:
    """Open a new scan row. Defaults to 'running'; caller finishes it later."""
    if status not in SCAN_STATUSES:
        status = "running"
    scan = Scan(repo_id=repo_id, status=status)
    session.add(scan)
    session.flush()
    return scan


# Alias matching the name used in the day-by-day plan.
def save_scan(session: Session, repo_id: int, **kwargs: Any) -> Scan:
    """Alias of start_scan() (the name from the Day-3 plan)."""
    return start_scan(session, repo_id, **kwargs)


def complete_scan(
    session: Session, scan_id: int, status: str = "completed"
) -> Scan | None:
    scan = session.get(Scan, scan_id)
    if scan is None:
        return None
    scan.status = status if status in SCAN_STATUSES else "completed"
    session.flush()
    return scan


def get_scan(session: Session, scan_id: int) -> Scan | None:
    return session.get(Scan, scan_id)


def get_scan_with_findings(session: Session, scan_id: int) -> dict[str, Any] | None:
    """Payload for GET /scans/{id}: scan status + its findings + risk summary."""
    scan = session.get(Scan, scan_id)
    if scan is None:
        return None
    return {
        "scan": scan,
        "findings": get_findings_for_scan(session, scan_id),
        "summary": get_risk_summary(session, scan_id),
    }


def list_scans(
    session: Session, repo_id: int | None = None, limit: int = 50
) -> list[Scan]:
    stmt = select(Scan).order_by(Scan.started_at.desc(), Scan.id.desc()).limit(limit)
    if repo_id is not None:
        stmt = stmt.where(Scan.repo_id == repo_id)
    return list(session.scalars(stmt).all())


def get_latest_scan_for_repo(session: Session, repo_id: int) -> Scan | None:
    stmt = (
        select(Scan)
        .where(Scan.repo_id == repo_id)
        .order_by(Scan.started_at.desc(), Scan.id.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

def save_finding(session: Session, scan_id: int, finding: dict[str, Any]) -> Finding:
    """Persist one finding (tolerant of key naming)."""
    row = Finding(scan_id=scan_id, **normalize_finding(finding))
    session.add(row)
    session.flush()
    return row


def save_findings(
    session: Session, scan_id: int, findings: list[dict[str, Any]]
) -> list[Finding]:
    """Bulk-persist findings."""
    rows = [Finding(scan_id=scan_id, **normalize_finding(f)) for f in findings]
    session.add_all(rows)
    session.flush()
    return rows


def get_findings_for_scan(
    session: Session,
    scan_id: int,
    risk_tier: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Finding]:
    """Findings for a scan, optionally filtered by risk tier.

    Uses idx_findings_scan_id (and idx_findings_severity when filtered).
    """
    stmt = select(Finding).where(Finding.scan_id == scan_id)
    if risk_tier:
        stmt = stmt.where(Finding.risk_tier == risk_tier.strip().upper())
    stmt = stmt.order_by(Finding.id).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt).all())


def count_findings(session: Session, scan_id: int) -> int:
    stmt = select(func.count()).select_from(Finding).where(Finding.scan_id == scan_id)
    return int(session.scalar(stmt) or 0)


def get_risk_summary(session: Session, scan_id: int) -> dict[str, int]:
    """Risk-tier histogram for the dashboard header, e.g.
    {"total": 12, "CRITICAL": 2, "HIGH": 5, "MEDIUM": 3, "LOW": 2, "UNSCORED": 0}.
    """
    stmt = (
        select(Finding.risk_tier, func.count())
        .where(Finding.scan_id == scan_id)
        .group_by(Finding.risk_tier)
    )
    counts = {tier: 0 for tier in RISK_TIERS}
    counts["UNSCORED"] = 0  # findings with no risk_tier yet
    total = 0
    for tier, n in session.execute(stmt):
        key = tier if tier in RISK_TIERS else "UNSCORED"
        counts[key] += int(n)
        total += int(n)
    counts["total"] = total
    return counts
