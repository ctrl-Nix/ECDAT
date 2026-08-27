"""
Scans Router — ECDAT scan lifecycle endpoints.

Endpoints per ARCHITECTURE.md §2.3:
  POST /scans          → 202 Accepted, launches scan as a BackgroundTask
  GET  /scans          → paginated list of scans (optional repo_id filter)
  GET  /scans/{id}     → scan metadata + findings + risk summary

Security: all routes require X-API-Key via the get_api_key dependency.
The POST /scans target_path is resolved and validated server-side inside
scan_runner._validate_path() — never shell-interpolated.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.security import get_api_key
from api.core.config import settings
from api.database import get_session
from api.models import FindingOut, RiskSummary, ScanOut, ScanWithFindings
from api.services.scan_runner import run_scan

log = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["scans"])


# ---------------------------------------------------------------------------
# Request / Response schemas (route-specific, not in api/models.py)
# ---------------------------------------------------------------------------

class ScanCreateRequest(BaseModel):
    """Body for POST /scans."""
    target_path: str = Field(
        ...,
        description="Absolute path to the repository or file to scan.",
        examples=["/repo/my-project"],
    )
    repo_name: str | None = Field(
        None,
        description="Human-readable repository name. Defaults to directory basename.",
    )
    repo_url: str | None = Field(
        None,
        description="VCS URL for deduplication (optional).",
    )


class ScanCreateResponse(BaseModel):
    """202 response for POST /scans."""
    scan_id: int
    status: str = "pending"
    message: str = "Scan queued. Poll GET /scans/{scan_id} for results."


class ScanListResponse(BaseModel):
    """GET /scans list response."""
    scans: list[ScanOut]
    total: int


# ---------------------------------------------------------------------------
# Background task helper
# ---------------------------------------------------------------------------

def _run_scan_background(
    target_path: str,
    repo_name: str | None,
    repo_url: str | None,
    scan_id: int,
    db_url: str,
) -> None:
    """
    Execute the full scan pipeline in a background thread.

    Opens its own DB session so the scan runs independently of the request
    session (which is closed by the time this runs).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, future=True, connect_args={"check_same_thread": False}
                           if db_url.startswith("sqlite") else {})
    BgSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with BgSession() as session:
        try:
            result = run_scan(
                session,
                target_path=target_path,
                repo_name=repo_name,
                repo_url=repo_url,
                scan_id=scan_id,
            )
            session.commit()
            log.info("Background scan %d finished: %s", scan_id, result["status"])
        except Exception as exc:
            session.rollback()
            log.exception("Background scan %d raised: %s", scan_id, exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScanCreateResponse,
    summary="Trigger a new cryptographic scan",
    description=(
        "Accepts a target path, creates a scan record (status=pending), "
        "and launches the scan pipeline as a background task. "
        "Returns immediately with the scan_id to poll."
    ),
)
def create_scan(
    body: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_session)],
    _key: Annotated[str, Depends(get_api_key)],
) -> ScanCreateResponse:
    """POST /scans — create and queue a scan."""
    if not settings.ENABLE_LOCAL_SCAN_API:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Server-local scan execution is disabled. Run the offline CLI and sync a signed report bundle.",
        )
    # Validate path eagerly so we 422 before returning 202
    from api.services.scan_runner import _validate_path
    try:
        _validate_path(body.target_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Create the repository and scan row synchronously so we can return scan_id.
    name = body.repo_name or body.target_path.split("/")[-1] or "unknown"
    repo = crud.get_or_create_repository(db, name=name, url=body.repo_url)
    db.flush()
    scan = crud.start_scan(db, repo_id=repo.id, status="pending")
    db.commit()

    scan_id = scan.id

    # Dispatch to background — uses its own session+engine.
    from api.database import get_database_url
    background_tasks.add_task(
        _run_scan_background,
        target_path=body.target_path,
        repo_name=body.repo_name,
        repo_url=body.repo_url,
        scan_id=scan_id,
        db_url=get_database_url(),
    )

    log.info("POST /scans accepted scan_id=%d target=%s", scan_id, body.target_path)
    return ScanCreateResponse(scan_id=scan_id)


@router.get(
    "",
    response_model=ScanListResponse,
    summary="List scans",
    description="Returns a paginated list of scans, newest first.",
)
def list_scans(
    db: Annotated[Session, Depends(get_session)],
    _key: Annotated[str, Depends(get_api_key)],
    repo_id: int | None = Query(None, description="Filter by repository ID."),
    limit: int = Query(50, ge=1, le=200, description="Max results per page."),
) -> ScanListResponse:
    """GET /scans — list all scans."""
    scans = crud.list_scans(db, repo_id=repo_id, limit=limit)
    return ScanListResponse(scans=scans, total=len(scans))


@router.get(
    "/{scan_id}",
    response_model=ScanWithFindings,
    summary="Get scan details with findings",
    description=(
        "Returns the scan record, all its findings (with risk tiers), "
        "and an aggregate risk-tier summary. "
        "Returns 404 if the scan_id does not exist."
    ),
)
def get_scan(
    scan_id: int,
    db: Annotated[Session, Depends(get_session)],
    _key: Annotated[str, Depends(get_api_key)],
    risk_tier: str | None = Query(
        None,
        description="Optional filter: only return findings at this risk tier (CRITICAL/HIGH/MEDIUM/LOW).",
    ),
    limit: int = Query(200, ge=1, le=1000, description="Max findings returned."),
    offset: int = Query(0, ge=0, description="Findings pagination offset."),
) -> Any:
    """GET /scans/{scan_id} — scan + findings + summary."""
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
        limit=limit,
        offset=offset,
    )
    summary = crud.get_risk_summary(db, scan_id)

    return {
        "scan": scan,
        "findings": findings,
        "summary": summary,
    }
