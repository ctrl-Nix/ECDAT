"""
Findings Router — paginated findings query for ECDAT.

Endpoints per ARCHITECTURE.md §2.3:
  GET /scans/{scan_id}/findings
      ?risk_tier=HIGH   — filter by tier (CRITICAL/HIGH/MEDIUM/LOW)
      &limit=50         — page size (default 50, max 200)
      &offset=0         — pagination offset

  GET /scans/{scan_id}/findings/{finding_id}
      — single finding detail (used by remediation panel click-through)

Security: X-API-Key required on every route.
This router is a thin HTTP wrapper — all query logic lives in db/crud.py.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.rbac import Principal, Role, require_role
from api.database import get_session
from api.models import FindingOut, RiskSummary

log = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["findings"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class FindingsPageResponse(BaseModel):
    """Paginated GET /scans/{scan_id}/findings response."""
    scan_id: int
    findings: list[FindingOut]
    total_on_page: int
    offset: int
    limit: int
    risk_tier_filter: str | None = None
    summary: RiskSummary


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/{scan_id}/findings",
    response_model=FindingsPageResponse,
    summary="List findings for a scan",
    description=(
        "Returns paginated findings for the given scan. "
        "Optionally filter by risk_tier. "
        "Returns 404 if the scan does not exist."
    ),
)
def list_findings(
    scan_id: int,
    db: Annotated[Session, Depends(get_session)],
    user: Annotated[Principal, Depends(require_role(Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN))],
    risk_tier: str | None = Query(
        None,
        description="Filter by risk tier: CRITICAL, HIGH, MEDIUM, or LOW.",
        pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$",
    ),
    min_band: str | None = Query(
        None,
        description="Return findings whose confidence_band meets or exceeds this level.",
        pattern="^(VERIFIED|PROBABLE|UNVERIFIED)$",
    ),
    limit: int = Query(50, ge=1, le=200, description="Max findings per page."),
    offset: int = Query(0, ge=0, description="Pagination offset."),
) -> Any:
    """GET /scans/{scan_id}/findings — paginated, filtered findings list."""
    scan = crud.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found.",
        )

    findings = crud.get_findings_for_scan(
        db,
        scan_id=scan_id,
        risk_tier=risk_tier,
        min_band=min_band,
        limit=limit,
        offset=offset,
    )
    summary = crud.get_risk_summary(db, scan_id)

    return {
        "scan_id": scan_id,
        "findings": findings,
        "total_on_page": len(findings),
        "offset": offset,
        "limit": limit,
        "risk_tier_filter": risk_tier,
        "summary": summary,
    }


@router.get(
    "/{scan_id}/findings/{finding_id}",
    response_model=FindingOut,
    summary="Get a single finding",
    description=(
        "Returns the full detail for a single finding. "
        "Returns 404 if the scan or finding does not exist, "
        "or if the finding does not belong to the given scan."
    ),
)
def get_finding(
    scan_id: int,
    finding_id: int,
    db: Annotated[Session, Depends(get_session)],
    user: Annotated[Principal, Depends(require_role(Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN))],
) -> Any:
    """GET /scans/{scan_id}/findings/{finding_id} — single finding."""
    # Verify scan exists first for a clean 404 message
    scan = crud.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found.",
        )

    finding = crud.get_finding(db, finding_id)
    if finding is None or finding.scan_id != scan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding {finding_id} not found in scan {scan_id}.",
        )

    return finding


