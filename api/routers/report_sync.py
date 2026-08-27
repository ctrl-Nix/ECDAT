"""Authenticated intake for signed bundles produced by offline ECDAT agents."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.security import get_report_sync_agent
from api.database import get_session
from api.models import ReportIngestResponse
from api.services.report_bundle import ReportBundleError, verify_bundle


router = APIRouter(prefix="/agent/v1", tags=["report-sync"])


@router.post(
    "/report-bundles",
    response_model=ReportIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a signed report from an enrolled offline scanning agent",
)
def ingest_report_bundle(
    bundle: dict[str, Any],
    agent: Annotated[tuple[str, str], Depends(get_report_sync_agent)],
    db: Annotated[Session, Depends(get_session)],
) -> ReportIngestResponse:
    """Verify the enrolled agent and bundle before creating reportable records.

    This route is intended behind a mutually authenticated TLS reverse proxy.
    It has no browser authentication mechanism and must not be exposed directly
    while `REPORT_SYNC_REQUIRE_MTLS` is enabled.
    """
    agent_id, public_key = agent
    try:
        verified = verify_bundle(bundle, public_key)
    except ReportBundleError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if verified.get("agent_id") != agent_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bundle agent identity does not match mTLS agent")
    required = ("bundle_version", "report_id", "organization_id", "repository_id", "findings", "summary")
    if any(key not in verified for key in required) or not isinstance(verified["findings"], list):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Report bundle has an invalid payload")

    report, accepted = crud.ingest_signed_report(
        db,
        bundle=verified,
        bundle_digest=str(bundle["bundle_digest"]),
        signature_algorithm=str(bundle["signature_algorithm"]),
    )
    db.commit()
    return ReportIngestResponse(
        report_id=report.report_id,
        scan_id=report.scan_id,
        accepted=accepted,
        bundle_digest=report.bundle_digest,
        message="Signed report accepted" if accepted else "Previously accepted report replayed safely",
    )
