"""
Findings Router — paginated findings query for ECDAT.

Endpoints per ARCHITECTURE.md §2.3:
  GET /scans/{scan_id}/findings
      ?risk_tier=HIGH   — filter by tier (CRITICAL/HIGH/MEDIUM/LOW)
      &limit=50         — page size (default 50, max 200)
      &offset=0         — pagination offset

  GET /scans/{scan_id}/findings/{finding_id}
      — single finding detail (used by remediation panel click-through)

Security: analyst routes require a bearer token with the appropriate RBAC role.
This router is a thin HTTP wrapper — all query logic lives in db/crud.py.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.params import FindingListParams, common_list_params
from api.core.rbac import Principal, Role, require_role
from api.database import get_session
from api.models import FindingOut, RiskSummary
from db.models import RISK_TIERS

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
    filters: dict[str, list[str] | None]
    sort_by: str | None = None
    sort_dir: str = "asc"
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
    params: Annotated[FindingListParams, Depends(common_list_params)],
    min_band: str | None = Query(
        None,
        description="Return findings whose confidence_band meets or exceeds this level.",
        pattern="^(VERIFIED|PROBABLE|UNVERIFIED)$",
    ),
) -> Any:
    """GET /scans/{scan_id}/findings — paginated, filtered findings list."""
    scan = crud.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found.",
        )

    risk_tiers = [tier.strip().upper() for tier in params.risk_tier or []]
    if invalid_tiers := [tier for tier in risk_tiers if tier not in RISK_TIERS]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid risk_tier value(s): {', '.join(invalid_tiers)}",
        )

    findings = crud.get_findings_for_scan(
        db,
        scan_id=scan_id,
        risk_tier=risk_tiers or None,
        primitive=params.primitive,
        algorithm=params.algorithm,
        language=params.language,
        sort_by=params.sort_by,
        sort_dir=params.sort_dir,
        min_band=min_band,
        limit=params.limit,
        offset=params.offset,
    )
    summary = crud.get_risk_summary(db, scan_id)

    return {
        "scan_id": scan_id,
        "findings": findings,
        "total_on_page": len(findings),
        "offset": params.offset,
        "limit": params.limit,
        "risk_tier_filter": risk_tiers[0] if risk_tiers else None,
        "filters": {
            "risk_tier": risk_tiers or None,
            "primitive": params.primitive or None,
            "algorithm": params.algorithm or None,
            "language": params.language or None,
        },
        "sort_by": params.sort_by,
        "sort_dir": params.sort_dir,
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


