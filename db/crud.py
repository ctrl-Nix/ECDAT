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

import json
from pwdlib import PasswordHash
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.services.risk_engine import score_findings
from db.models import (
    CONFIDENCE_BANDS,
    CRITICALITIES,
    RISK_TIERS,
    SCAN_STATUSES,
    Finding,
    Repository,
    Scan,
    RiskAssessment,
    Report,
    User,
)

pwd_context = PasswordHash.recommended()


def get_user_by_username(session: Session, username: str) -> User | None:
    """Return an account by its unique username."""
    return session.scalars(select(User).where(User.username == username)).first()


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password without exposing hashing errors to login callers."""
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


def create_user(
    session: Session,
    username: str,
    password: str,
    role: str,
    organization_id: str | None = None,
) -> User:
    """Create an account with an Argon2 password hash."""
    user = User(
        username=username,
        password_hash=pwd_context.hash(password),
        role=role,
        organization_id=organization_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

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
    "matched_call": "matched_call",
    "library": "library",
    "primitive": "primitive",
    "language": "language",
    "weak_by_default": "weak_by_default",
    "detection_method": "detection_method",
    "source_context": "source_context",
    "risk_tier": "risk_tier",
    "risktier": "risk_tier",
    "severity": "risk_tier",
    "tier": "risk_tier",
    "risk_reason": "risk_reason",
    "riskreason": "risk_reason",
    "reason": "risk_reason",
    "criticality": "criticality",
    "confidence_score": "confidence_score",
    "confidencescore": "confidence_score",
    "confidence_band": "confidence_band",
    "confidenceband": "confidence_band",
    "confidence_signals": "confidence_signals",
    "confidencesignals": "confidence_signals",
}


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_band(value: Any) -> str | None:
    if value is None or value == "":
        return None
    val_str = str(value).strip().upper()
    return val_str if val_str in CONFIDENCE_BANDS else None


def _coerce_score(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _coerce_signals(value: Any) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            return None
        except (ValueError, TypeError):
            return None
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
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

    band = _coerce_band(cols.get("confidence_band"))
    cols["confidence_band"] = band
    cols["confidence_score"] = _coerce_score(cols.get("confidence_score"))
    cols["confidence_signals"] = _coerce_signals(cols.get("confidence_signals"))

    if band is not None:
        from scanner.confidence import legacy_confidence_for
        cols["confidence"] = legacy_confidence_for(band)
    else:
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
    session: Session, name: str, url: str | None = None,
    organization_id: str | None = None, external_id: str | None = None,
) -> Repository:
    """Return the existing repo (matched by url, else exact name) or create it."""
    if organization_id and external_id:
        stmt = select(Repository).where(
            Repository.organization_id == organization_id,
            Repository.external_id == external_id,
        )
    elif url:
        stmt = select(Repository).where(Repository.url == url)
    else:
        stmt = select(Repository).where(
            Repository.url.is_(None), Repository.name == name
        )
    existing = session.scalars(stmt).first()
    if existing:
        return existing

    repo = Repository(
        name=name, url=url, organization_id=organization_id, external_id=external_id
    )
    session.add(repo)
    session.flush()  # assign PK without ending the transaction
    return repo


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------

def start_scan(
    session: Session, repo_id: int, status: str = "running",
    source_scan_id: str | None = None, scan_context: str | None = None,
) -> Scan:
    """Open a new scan row. Defaults to 'running'; caller finishes it later."""
    if status not in SCAN_STATUSES:
        status = "running"
    scan = Scan(
        repo_id=repo_id, status=status, source_scan_id=source_scan_id,
        scan_context=scan_context,
    )
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
    """Persist discovery evidence and its versioned deterministic assessment."""
    row = Finding(scan_id=scan_id, **normalize_finding(finding))
    session.add(row)
    session.flush()
    _save_risk_assessment(session, row.id, finding)
    return row


def save_findings(
    session: Session, scan_id: int, findings: list[dict[str, Any]]
) -> list[Finding]:
    """Bulk-persist findings together with versioned risk assessments."""
    return [save_finding(session, scan_id=scan_id, finding=f) for f in findings]


def _save_risk_assessment(session: Session, finding_id: int, finding: dict[str, Any]) -> RiskAssessment:
    """Store reportable PQC context separately from immutable scan evidence."""
    assessment = RiskAssessment(
        finding_id=finding_id,
        risk_model_version=str(finding.get("risk_model_version") or "unknown"),
        classical_broken=bool(finding.get("classical_broken", False)),
        quantum_vulnerable=bool(finding.get("quantum_vulnerable", False)),
        hndl_exposure=str(finding.get("hndl_exposure") or "UNKNOWN"),
        recommended_replacement=finding.get("recommended_replacement"),
        recommendation_type=finding.get("recommendation_type"),
        migration_effort_days=_coerce_int(finding.get("migration_effort_days")),
        data_shelf_life_years=finding.get("data_shelf_life_years"),
        quantum_threat_horizon_years=finding.get("quantum_threat_horizon_years"),
        assumption_source=finding.get("assumption_source"),
    )
    session.add(assessment)
    session.flush()
    return assessment


def get_risk_assessments_for_scan(session: Session, scan_id: int) -> dict[int, RiskAssessment]:
    """Return assessments keyed by finding ID for report/API assembly."""
    stmt = (
        select(RiskAssessment)
        .join(Finding, RiskAssessment.finding_id == Finding.id)
        .where(Finding.scan_id == scan_id)
    )
    return {item.finding_id: item for item in session.scalars(stmt).all()}


def ingest_signed_report(
    session: Session, *, bundle: dict[str, Any], bundle_digest: str,
    signature_algorithm: str,
) -> tuple[Report, bool]:
    """Idempotently persist a verified local-agent report bundle."""
    report_id = str(bundle["report_id"])
    existing = session.scalars(select(Report).where(Report.report_id == report_id)).first()
    if existing:
        return existing, False

    organization_id = str(bundle["organization_id"])
    repository_id = str(bundle["repository_id"])
    repo = get_or_create_repository(
        session, name=repository_id, organization_id=organization_id,
        external_id=repository_id,
    )
    scan = start_scan(
        session, repo.id, status="completed", source_scan_id=report_id,
        scan_context=json.dumps(bundle.get("scan_context", {}), sort_keys=True),
    )
    # An enrolled agent's signature proves origin and integrity, not that the
    # agent host is uncompromised. Recompute all deterministic risk fields
    # centrally from the signed discovery evidence instead of trusting a
    # supplied tier, recommendation, or HNDL conclusion.
    server_scored_findings = score_findings(list(bundle.get("findings", [])))
    save_findings(session, scan.id, server_scored_findings)
    report = Report(
        report_id=report_id, scan_id=scan.id, organization_id=organization_id,
        repository_id=repository_id, agent_id=str(bundle["agent_id"]),
        bundle_digest=bundle_digest, signature_algorithm=signature_algorithm,
    )
    session.add(report)
    session.flush()
    return report, True


def get_findings_for_scan(
    session: Session,
    scan_id: int,
    risk_tier: str | None = None,
    min_band: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Finding]:
    """Findings for a scan, optionally filtered by risk tier and/or min_band.

    Uses idx_findings_scan_id (and idx_findings_severity / idx_findings_confidence_band).
    """
    stmt = select(Finding).where(Finding.scan_id == scan_id)
    if risk_tier:
        stmt = stmt.where(Finding.risk_tier == risk_tier.strip().upper())
    if min_band:
        upper_band = min_band.strip().upper()
        if upper_band == "VERIFIED":
            stmt = stmt.where(Finding.confidence_band == "VERIFIED")
        elif upper_band == "PROBABLE":
            stmt = stmt.where(Finding.confidence_band.in_(["VERIFIED", "PROBABLE"]))
        elif upper_band == "UNVERIFIED":
            stmt = stmt.where(Finding.confidence_band.in_(["VERIFIED", "PROBABLE", "UNVERIFIED"]))
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


def get_finding(session: Session, finding_id: int) -> Finding | None:
    """Fetch a single finding by primary key ID."""
    stmt = select(Finding).where(Finding.id == finding_id)
    return session.scalars(stmt).first()

