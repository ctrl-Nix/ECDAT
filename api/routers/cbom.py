"""
CBOM Router — CycloneDX 1.6 CBOM export for ECDAT.

Endpoints per ARCHITECTURE.md §2.3:
  GET /scans/{scan_id}/cbom
      Returns a CycloneDX 1.6 JSON document containing all cryptographic
      asset components found in the scan, with risk tiers and evidence.

      ?download=true  — add Content-Disposition: attachment header so the
                        browser/curl saves it as a .json file.

Security: this analyst route requires a bearer token with an allowed RBAC role.
This router calls cbom_generator.generate_cbom() — no business logic here.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.rbac import Principal, Role, require_role
from api.database import get_session
from api.services.cbom_generator import CBOM_BOM_FORMAT, generate_cbom

log = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["cbom"])

# CycloneDX JSON media type per spec
_CBOM_CONTENT_TYPE = "application/vnd.cyclonedx+json"


@router.get(
    "/{scan_id}/cbom",
    summary="Export CycloneDX 1.6 CBOM",
    description=(
        "Generates and returns a CycloneDX 1.6 Cryptographic Bill of Materials "
        "for the given scan. Each finding becomes a `cryptographic-asset` component "
        "with algorithm, evidence, risk tier, and PQC migration direction. "
        "Returns 404 if the scan does not exist. "
        "Returns 400 if the scan has not completed yet."
    ),
    response_class=Response,
    responses={
        200: {
            "content": {_CBOM_CONTENT_TYPE: {}},
            "description": "CycloneDX 1.6 CBOM JSON document.",
        },
        400: {"description": "Scan not yet completed."},
        404: {"description": "Scan not found."},
    },
)
def get_cbom(
    scan_id: int,
    db: Annotated[Session, Depends(get_session)],
    user: Annotated[Principal, Depends(require_role(Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN))],
    download: bool = Query(
        False,
        description="Set to true to receive file as a download attachment.",
    ),
) -> Response:
    """GET /scans/{scan_id}/cbom — CycloneDX 1.6 CBOM export."""
    scan = crud.get_scan(db, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found.",
        )

    # Guard: don't export a partial CBOM for an in-progress scan
    if scan.status in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Scan {scan_id} is still {scan.status!r}. "
                "CBOM is only available after the scan completes."
            ),
        )

    cbom = generate_cbom(db, scan_id)
    if cbom is None:
        # generate_cbom returns None only when scan not found — belt & suspenders
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found.",
        )

    cbom_json = json.dumps(cbom, indent=2, default=str)

    headers: dict[str, str] = {}
    if download:
        headers["Content-Disposition"] = (
            f'attachment; filename="ecdat-scan-{scan_id}-cbom.json"'
        )

    log.info(
        "GET /scans/%d/cbom served %d components (download=%s)",
        scan_id,
        len(cbom.get("components", [])),
        download,
    )

    return Response(
        content=cbom_json,
        media_type=_CBOM_CONTENT_TYPE,
        headers=headers,
    )

