"""Pydantic response models for the route Ronak owns: GET /scans/{id}.

Defines the exact JSON shape the frontend (Karan & Satyam) consumes.
`from_attributes=True` lets FastAPI serialize the SQLAlchemy rows directly:

    @app.get("/scans/{scan_id}", response_model=ScanWithFindings)
    def read_scan(scan_id: int, db: Session = Depends(get_session)):
        data = crud.get_scan_with_findings(db, scan_id)
        if data is None:
            raise HTTPException(404)
        return data

Requires pydantic v2 (installed with FastAPI). Not imported by the offline
SQLite test-suite, which exercises models/crud only.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int | None = None
    file: str
    line: int
    algorithm: str
    key_size: int | None = None
    confidence: str
    risk_tier: str | None = None
    risk_reason: str | None = None
    criticality: str


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: int | None = None
    started_at: dt.datetime | None = None
    status: str


class RiskSummary(BaseModel):
    total: int = 0
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0
    UNSCORED: int = 0


class ScanWithFindings(BaseModel):
    """The GET /scans/{id} payload: scan status + findings + risk summary."""

    scan: ScanOut
    findings: list[FindingOut] = []
    summary: RiskSummary | None = None


class RemediationOut(BaseModel):
    finding_id: int | str | None = None
    suggestion: str
    source: str  # 'llm' or 'table'
    provider: str | None = None
    model: str | None = None
    fallback_used: bool = False
    severity: str | None = None


class RemediationRequest(BaseModel):
    algorithm: str
    file: str = "unknown"
    line: int = 1
    api_key: str | None = None
    provider: str | None = None
    model: str | None = None

