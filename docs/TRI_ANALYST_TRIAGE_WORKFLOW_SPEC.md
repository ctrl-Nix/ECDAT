# ANALYST TRIAGE WORKFLOW (Status + Notes) — Implementation Specification

---

## 1. Header

**Feature:** Analyst Triage Workflow (status + notes) · Feature code **TRI**  
**Owner:** Backend analyst-facing feature; DB-level triage storage; dashboard UI integration  
**Spec Version:** 1.0 · Draft for implementation  
**Status:** Blocked on C-15 sign-off (fingerprint inputs)  
**Changelog:**
- v1.0: Initial specification derived from contract §2.2 (migration 007), §3.4, §3.6, and C-15/C-16 resolutions.
- Deviation from Step 1 proposal: TRI was initially scheduled Wave 4; moved to Wave 4 per merge order (§6 contract), not changed. Fingerprint definition resolved under C-15 (stable across re-scans).

**Reviewer Sign-Off:**  
⚠️ **PENDING:** C-15 human sign-off on fingerprint input set (`repo_id, file, algorithm, primitive, library, normalised line context`). DB lane + scanner lane authority required before implementation.

---

### Step 5 integration-audit corrections (v1.1)

| # | Was | Now | Why |
|---|---|---|---|
| 1 | `fastapi==0.104.1`, `pydantic==2.5.0`, `sqlalchemy==2.0.23` "(existing)" | `fastapi>=0.111.0`, `pydantic>=2.7.0`, `SQLAlchemy>=2.0,<2.1` | Not the existing pins; `0.104.1` and `2.5.0` sit **below** the repository floors and would be a silent downgrade of a COORDINATED file (C-18) |
| 2 | `psycopg[binary]==3.9.15` | `psycopg2-binary>=2.9` | The repo uses psycopg**2**, not psycopg3 |
| 3 | PostgreSQL "13+" | PostgreSQL `16-alpine` | Per `docker-compose.yml` |
| 4 | `@require_role("SECURITY_ADMIN")` as a bare string | `require_role(Role.DEVELOPER, Role.SECURITY_ADMIN)` | Roles are `Role` enum members from `api/core/rbac.py`, and triage write is Developer+Admin per the permission matrix |

*Unchanged and confirmed correct:* this spec's use of `principal.username` (matches the corrected RBAC `Principal`), and migration `007_finding_triage.sql`.

---

## 2. Goal & Context

The analyst triage workflow allows security engineers to record and persist findings dispositions (status + free-text notes) in a way that survives re-scans. A re-scan of the same repository must carry forward earlier triage decisions by matching findings via a stable fingerprint, so that dismissals, risk acceptances, and remediation notes do not reset on every scan run—addressing PS 26164 requirement §5 ("Recommendation & reporting") and supporting the enterprise workflow of ongoing cryptographic inventory management where a decision today should not be forgotten tomorrow.

---

## 3. Scope

### In-Scope

- Database-level triage storage: `finding_triage` table with status, notes, and audit fields  
- `findings.fingerprint` column (stable across scans) as the decision-carry-forward key  
- API endpoint `PATCH /scans/{scan_id}/findings/{finding_id}/triage` to record status + notes  
- Triage status enumeration: `open | acknowledged | false_positive | remediated | accepted_risk`  
- Merging triage status into the `GET /scans/{scan_id}/findings` response  
- CRUD functions in `db/crud.py` for triage reads/writes  
- Pydantic models in `api/models.py` for triage request/response  
- Audit event recording (`ecdat.triage.update`) per §3.6 contract  

### Out-of-Scope

- Dashboard UI for triage status display or editing (belongs to frontend lane, DFS, FE)  
- Fingerprint collision resolution or rehashing logic (belongs to scanner lane if fingerprint algorithm changes)  
- Auto-propagation of triage to newly found findings via fuzzy matching (triage is per-fingerprint; matching is analyst's responsibility)  
- Triage workflow enforcement or role-based access controls (RBAC feature owns that; TRI assumes analyst role exists)  
- Time-series triage history or audit trail beyond `updated_at` (audit_events table handles this via `ecdat.triage.update` events)

---

## 4. Required Context Files

Implementer must read these **before** writing code:

1. **`SYSTEM_INTERFACE_CONTRACT.md`** § 2.2 (migration 007 schema), § 3.4 (route naming), § 3.6 (audit actions), C-15, C-16
2. **`ARCHITECTURE.md`** § 1 (component status), § 2 (data flow), § 2.2 (DB schema), § 4 (security)  
3. **`AGENT_RULES.md`** (binding rules 1–9)
4. **`db/schema.sql`** (existing tables, indexes)
5. **`db/models.py`** (ORM models, value tuples)  
6. **`db/crud.py`** (CRUD patterns, naming conventions)
7. **`api/models.py`** (Pydantic response models, ConfigDict patterns)
8. **`api/routers/findings.py`** (existing `GET /scans/{scan_id}/findings`)
9. **`api/core/security.py`** + `api/core/config.py`** (auth context; RBAC contract is prerequisite)
10. **`api/main.py`** (router registration pattern)
11. **`tests/test_crud.py`** (existing CRUD test patterns)

---

## 5. File Ownership

### Files TRI creates or modifies (SOLE or COORDINATED ownership):

| File | Tier | Notes |
|---|---|---|
| `db/schema.sql` | COORDINATED | Add `findings.fingerprint` + `finding_triage` table (migration 007 content identical to this file) |
| `db/migrations/007_finding_triage.sql` | SOLE | TRI-owned migration file, mount prefix `08_` in docker-compose.yml |
| `db/models.py` | COORDINATED | Add `FindingTriage` ORM model; add `TRIAGE_STATUSES` tuple; add relationship to `Finding` |
| `db/crud.py` | SOLE | Add `get_triage()`, `upsert_triage()`, `list_triages_for_scan()`, `carry_forward_triage_by_fingerprint()` |
| `api/models.py` | COORDINATED | Add `TriageIn` (PATCH body), `TriageOut` (response); merge into `FindingOut` |
| `api/routers/triage.py` | SOLE | New router with `PATCH /scans/{scan_id}/findings/{finding_id}/triage` endpoint |
| `api/main.py` | COORDINATED | Register triage router; no prefix override (route is `prefix=""`) |
| `tests/test_triage.py` | SOLE | New test suite for triage CRUD, fingerprint matching, re-scan carry-forward |

### Do Not Touch (SOLE or FROZEN files owned by other features):

| File | Owner | Reason |
|---|---|---|
| `api/services/scan_runner.py` | CONF | FROZEN; confidence gate is CONF's. Do not call triage logic here. |
| `api/services/risk_engine.py` | Risk/CBOM lane | FROZEN; read-only for TRI. Triage does not change risk scores. |
| `api/services/cbom_generator.py` | CBOM lane | COORDINATED; TRI does not modify. |
| `scanner/` (all) | Scanner lane | FROZEN for TRI's purposes. TRI reads fingerprint, does not compute it. |
| `api/routers/audit.py` | AUD | SOLE; AUD publishes audit helper. TRI calls it, does not modify. |
| `dashboard/src/components/FindingsTable.jsx` | Frontend lane | COORDINATED; DFS restructures first. TRI adds column definition to registry, not JSX. |
| `db/crud.py` (finder: list_findings_*) | Backend lane | COORDINATED; TRI adds `carry_forward_triage_by_fingerprint()` only. Does not modify existing finders. |

---

## 6. Tech Stack & Pinned Versions

**Python Backend (no new dependencies; versions copied verbatim from `requirements.txt`):**  
- `fastapi>=0.111.0` (existing)  
- `SQLAlchemy>=2.0,<2.1` (existing — the upper bound is real; do not assume 2.1+)  
- `pydantic>=2.7.0` (existing)  
- `pydantic-settings>=2.3.0` (existing)  
- `psycopg2-binary>=2.9` (existing PostgreSQL driver — **psycopg2, not psycopg3**; do not import `psycopg`)  
- `aiosqlite>=0.20.0` (existing, test database)

**Database:**  
- PostgreSQL `16-alpine` per `docker-compose.yml`; SQLite via `aiosqlite` in tests. No version bump.

> **Version discipline.** Every line above was re-read from `requirements.txt` / `dashboard/package.json` during the Step 5 audit. Do not "pin" these to exact `==` versions in a PR; the repository deliberately uses floors, and tightening them is a change to a COORDINATED file (contract §1.5, C-18).


**No new packages required.** TRI uses only stdlib (`datetime`, `hashlib`), FastAPI, SQLAlchemy 2.0, and Pydantic v2 already in `requirements.txt`.

---

## 7. Concrete Interface Definitions

### 7.1 Database Schema (identical in `db/schema.sql` and `db/migrations/007_finding_triage.sql`)

```sql
-- ============================================================================
-- 007_finding_triage.sql  ·  owner: TRI
-- Separate table, not columns on findings: findings are immutable discovery
-- facts, matching the existing findings / risk_assessments split.
-- fingerprint carries an analyst decision across re-scans (see C-15).
-- ============================================================================
ALTER TABLE findings ADD COLUMN IF NOT EXISTS fingerprint TEXT;
    -- stable identity: sha256(repo_id, file, algorithm, primitive, library, normalised line context)
CREATE INDEX IF NOT EXISTS idx_findings_fingerprint ON findings(fingerprint);

CREATE TABLE IF NOT EXISTS finding_triage (
    id          SERIAL PRIMARY KEY,
    finding_id  INTEGER NOT NULL UNIQUE REFERENCES findings(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
        -- open | acknowledged | false_positive | remediated | accepted_risk
    note        TEXT,
    updated_by  TEXT,      -- username once RBAC lands; free text before
    updated_at  TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_finding_triage_fingerprint ON finding_triage(fingerprint);
```

### 7.2 ORM Model (`db/models.py`)

```python
# Add to module-level value tuples (alphabetical with existing)
TRIAGE_STATUSES = ("open", "acknowledged", "false_positive", "remediated", "accepted_risk")

# Add relationship to Finding class (line ~75 in current file)
class Finding(Base):
    # ... existing columns ...
    fingerprint: Mapped[str | None] = mapped_column(Text, index=True)
    
    triage: Mapped["FindingTriage | None"] = relationship(
        back_populates="finding", cascade="all, delete-orphan", uselist=False
    )

# Add new class (insert after RiskAssessment, before Report)
class FindingTriage(Base):
    """Analyst triage disposition and notes for a cryptographic finding."""

    __tablename__ = "finding_triage"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, default="open", nullable=False)
        # open | acknowledged | false_positive | remediated | accepted_risk
    note: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[str | None] = mapped_column(Text)  # username or free text
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())

    finding: Mapped["Finding"] = relationship(back_populates="triage")
```

### 7.3 Pydantic Models (`api/models.py`)

```python
# Add to FindingOut (around line 44, before risk_assessment field)
class FindingOut(BaseModel):
    # ... existing fields ...
    risk_assessment: "RiskAssessmentOut | None" = None
    triage: "TriageOut | None" = None  # NEW

# Add new models (after RemediationRequest, before ReportIngestResponse)
class TriageIn(BaseModel):
    """PATCH /scans/{scan_id}/findings/{finding_id}/triage request body."""
    status: str  # open | acknowledged | false_positive | remediated | accepted_risk
    note: str | None = None

class TriageOut(BaseModel):
    """Triage disposition embedded in FindingOut."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: int
    fingerprint: str
    status: str
    note: str | None = None
    updated_by: str | None = None
    updated_at: dt.datetime | None = None
```

### 7.4 CRUD Functions (`db/crud.py`)

```python
def get_triage(session: Session, finding_id: int) -> FindingTriage | None:
    """Fetch one triage record by finding_id."""
    return session.get(FindingTriage, finding_id)


def upsert_triage(
    session: Session,
    finding_id: int,
    fingerprint: str,
    status: str,
    note: str | None = None,
    updated_by: str | None = None,
) -> FindingTriage:
    """Create or update a triage record for a finding.
    
    Validates status against TRIAGE_STATUSES. If triage already exists
    (finding_id is UNIQUE), updates status/note/updated_by/updated_at in place.
    """
    if status not in TRIAGE_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {TRIAGE_STATUSES}")
    
    existing = session.get(FindingTriage, finding_id)
    if existing:
        existing.status = status
        existing.note = note
        existing.updated_by = updated_by
        existing.updated_at = func.now()
        session.flush()
        return existing
    
    triage = FindingTriage(
        finding_id=finding_id,
        fingerprint=fingerprint,
        status=status,
        note=note,
        updated_by=updated_by,
    )
    session.add(triage)
    session.flush()
    return triage


def list_triages_for_scan(session: Session, scan_id: int) -> list[FindingTriage]:
    """Fetch all triage records for findings in a scan."""
    stmt = (
        select(FindingTriage)
        .join(Finding)
        .where(Finding.scan_id == scan_id)
        .order_by(FindingTriage.updated_at.desc())
    )
    return list(session.scalars(stmt))


def carry_forward_triage_by_fingerprint(
    session: Session, new_finding_id: int, fingerprint: str
) -> FindingTriage | None:
    """Link a new finding to an existing triage record via fingerprint.
    
    On re-scan, a new finding may have a new finding_id but a matching
    fingerprint. This function finds the most recent triage decision for
    that fingerprint and returns it (unchanged). The new finding is not
    inserted into finding_triage; the analyst must explicitly PATCH if
    they want to change the status.
    
    Returns the triage record or None if no prior triage exists for this
    fingerprint.
    """
    stmt = (
        select(FindingTriage)
        .where(FindingTriage.fingerprint == fingerprint)
        .order_by(FindingTriage.updated_at.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()
```

### 7.5 API Endpoint (`api/routers/triage.py`)

```python
"""Analyst triage workflow: record finding disposition (status + notes).

Route: PATCH /scans/{scan_id}/findings/{finding_id}/triage
Ownership: TRI
Audit action: ecdat.triage.update
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.core.security import get_session  # or similar; pattern from existing routers
from api.models import TriageIn, TriageOut
from db import crud
from db.models import TRIAGE_STATUSES, Finding, FindingTriage


router = APIRouter(prefix="", tags=["triage"])


@router.patch(
    "/scans/{scan_id}/findings/{finding_id}/triage",
    response_model=TriageOut,
    status_code=status.HTTP_200_OK,
)
def update_finding_triage(
    scan_id: int,
    finding_id: int,
    payload: TriageIn,
    db: Session = Depends(get_session),
) -> TriageOut:
    """Update triage status and notes for a finding.
    
    Args:
        scan_id: Scan ID (used for scoping; validated for authorization).
        finding_id: Finding ID to triage.
        payload: { status, note? }
    
    Returns:
        Updated TriageOut.
    
    Raises:
        404: Finding not found, or finding does not belong to scan_id.
        400: Invalid status value.
    
    Audit event: ecdat.triage.update (recorded by caller or middleware).
    """
    # Validate finding exists and belongs to scan_id
    finding = db.get(Finding, finding_id)
    if not finding or finding.scan_id != scan_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    # Validate status
    if payload.status not in TRIAGE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Must be one of {list(TRIAGE_STATUSES)}",
        )
    
    # Upsert triage (fingerprint is required; assume finding has it from scan time)
    if not finding.fingerprint:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Finding has no fingerprint; cannot record triage.",
        )
    
    triage = crud.upsert_triage(
        session=db,
        finding_id=finding_id,
        fingerprint=finding.fingerprint,
        status=payload.status,
        note=payload.note,
        updated_by=None,  # RBAC feature will inject current username here
    )
    db.commit()
    
    return TriageOut.model_validate(triage)
```

### 7.6 Example API JSON

**Request:**
```json
PATCH /scans/42/findings/999/triage
Content-Type: application/json

{
  "status": "acknowledged",
  "note": "Reviewed with crypto team. Replacement scheduled for Q2 2026."
}
```

**Response (200 OK):**
```json
{
  "id": 5,
  "finding_id": 999,
  "fingerprint": "abc123def456...",
  "status": "acknowledged",
  "note": "Reviewed with crypto team. Replacement scheduled for Q2 2026.",
  "updated_by": null,
  "updated_at": "2026-09-20T15:30:00Z"
}
```

**Error Response (404):**
```json
{
  "detail": "Finding not found"
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid status 'IN_PROGRESS'. Must be one of ['open', 'acknowledged', 'false_positive', 'remediated', 'accepted_risk']"
}
```

---

## 8. Step-by-Step Implementation Plan

### Phase 1: Database Schema & ORM (Files: schema.sql, migrations, models.py)

**Step 1:** Add `findings.fingerprint TEXT` column and `idx_findings_fingerprint` index to `db/schema.sql` (identical content to migration 007).  
**Step 2:** Create `db/migrations/007_finding_triage.sql` with both column and table-creation DDL (see schema above).  
**Step 3:** Add `docker-compose.yml` mount for migration 007 with prefix `08_`.  
**Step 4:** Add `FindingTriage` ORM model to `db/models.py` with relationships.  
**Step 5:** Add `TRIAGE_STATUSES` value tuple to `db/models.py`.  
**Step 6:** Add `fingerprint` field and `triage` relationship to `Finding` class in `db/models.py`.

**Verification:** Run `pytest tests/test_crud.py -xvs` to confirm no ORM breakage.

---

### Phase 2: CRUD Layer (File: db/crud.py)

**Step 7:** Implement `get_triage()` function (single-row fetch by finding_id).  
**Step 8:** Implement `upsert_triage()` function (create or update, with status validation).  
**Step 9:** Implement `list_triages_for_scan()` function (query triage by scan_id via join).  
**Step 10:** Implement `carry_forward_triage_by_fingerprint()` function (re-scan carry-forward).

**Verification:** Write unit tests in new file `tests/test_triage_crud.py`:
- Test upsert creates new triage.
- Test upsert updates existing triage.
- Test invalid status raises ValueError.
- Test list_triages returns correct set.
- Test fingerprint carry-forward finds prior triage.

---

### Phase 3: Pydantic Models & Request/Response Shaping (File: api/models.py)

**Step 11:** Add `TriageOut` Pydantic model with fields: `id, finding_id, fingerprint, status, note, updated_by, updated_at`.  
**Step 12:** Add `TriageIn` Pydantic model with fields: `status, note?`.  
**Step 13:** Add `triage: TriageOut | None = None` field to `FindingOut`.

**Verification:** Run `pytest tests/test_api.py -k "finding" -xvs` to confirm existing tests still pass with new field.

---

### Phase 4: API Router & Endpoint (File: api/routers/triage.py)

**Step 14:** Create new file `api/routers/triage.py` with router instance.  
**Step 15:** Implement `PATCH /scans/{scan_id}/findings/{finding_id}/triage` endpoint (see concrete interface above).  
**Step 16:** Add status/fingerprint validation, error responses (404, 400, 500).  
**Step 17:** Call `crud.upsert_triage()` with payload.  
**Step 18:** Return 200 with `TriageOut` response.

**Verification:** Run `pytest tests/test_triage_api.py::test_patch_triage_valid -xvs`.

---

### Phase 5: Router Registration (File: api/main.py)

**Step 19:** Import triage router: `from api.routers.triage import router as triage_router`.  
**Step 20:** Register router: `app.include_router(triage_router)` (prefix is empty per contract §3.4).

**Verification:** Run `pytest tests/test_api.py::test_swagger_schema -xvs`; confirm triage endpoints appear in OpenAPI schema.

---

### Phase 6: Integration with Findings Response (File: api/routers/findings.py)

**Step 21:** Modify `GET /scans/{scan_id}/findings` response to include triage in each `FindingOut`.  
  - Eager-load `Finding.triage` relationship to avoid N+1 queries.
  - If triage exists, include it; if not, null it out.

**Verification:** Run `pytest tests/test_api.py::test_get_findings_with_triage -xvs`.

---

### Phase 7: Test Suite (File: tests/test_triage.py)

**Step 22:** Write test for triage CRUD: create, read, update, list.  
**Step 23:** Write test for fingerprint carry-forward on re-scan.  
**Step 24:** Write test for PATCH endpoint: valid payload, invalid status, missing finding.  
**Step 25:** Write test for triage in FindingOut response.  
**Step 26:** Write integration test: scan → triage → re-scan → verify carry-forward.

**Verification:** Run `pytest tests/test_triage.py -xvs` and all pass.

---

### Phase 8: Audit Event Integration (File: api/routers/triage.py + audit service)

**Step 27:** After `db.commit()` in PATCH handler, call audit service to record `ecdat.triage.update` event (see contract §3.6).  
  - Event structure: `{ action: "ecdat.triage.update", object_type: "finding", object_id: str(finding_id), detail: { status, note, fingerprint } }`

**Verification:** Run full test suite; confirm no audit integration breaks existing tests.

---

## 9. Naming & Symbol Registry

### New Database Symbols

| Symbol | Type | Module | Notes |
|---|---|---|---|
| `finding_triage` | Table | `db/schema.sql`, migration 007 | Owns: `id, finding_id, fingerprint, status, note, updated_by, updated_at` |
| `idx_finding_triage_fingerprint` | Index | `db/schema.sql`, migration 007 | On `finding_triage.fingerprint` for fast carry-forward lookup |
| `idx_findings_fingerprint` | Index | `db/schema.sql`, migration 007 | On `findings.fingerprint` for triage join |
| `findings.fingerprint` | Column | `db/schema.sql`, migration 007 | `TEXT`, nullable initially; should be populated by scanner lane |
| `TRIAGE_STATUSES` | Tuple | `db/models.py` | `("open", "acknowledged", "false_positive", "remediated", "accepted_risk")` |

### New Python Symbols

| Symbol | Type | Module | Public? | Notes |
|---|---|---|---|---|
| `FindingTriage` | ORM Class | `db/models.py` | Yes | Declarative SQLAlchemy model |
| `get_triage` | Function | `db/crud.py` | Yes | Fetch one triage by finding_id |
| `upsert_triage` | Function | `db/crud.py` | Yes | Create or update triage |
| `list_triages_for_scan` | Function | `db/crud.py` | Yes | Fetch all triages for scan |
| `carry_forward_triage_by_fingerprint` | Function | `db/crud.py` | Yes | Lookup prior triage by fingerprint |
| `TriageIn` | Pydantic | `api/models.py` | Yes | Request body model |
| `TriageOut` | Pydantic | `api/models.py` | Yes | Response model |
| `router` | FastAPI Router | `api/routers/triage.py` | Yes | Contains PATCH endpoint |

### New API Symbols

| Route | Method | Notes |
|---|---|---|
| `/scans/{scan_id}/findings/{finding_id}/triage` | PATCH | Record triage disposition |

### New Audit Actions (contract §3.6)

| Action | Object Type | Emitted by |
|---|---|---|
| `ecdat.triage.update` | `finding` | `api/routers/triage.py` PATCH handler |

### New Environment Variables

None. TRI does not introduce new env vars.

### New CLI Flags

None. TRI does not extend CLI.

---

## 10. Known Cross-Feature Risks

### C-15: Fingerprint Input Set (Resolved in contract §2.2)

**Shared resource:** `findings.fingerprint`  
**Features:** TRI (owner), scanner lane (computation)  
**Resolution (per contract C-15):**  
Fingerprint = `sha256(repo_id, file, algorithm, primitive, library, normalised line context)`.  
Deliberately excludes `line` number so one-line edits do not resurrect dismissed findings.  
"Normalised line context" means source line + 2 neighbors (context window), normalized for whitespace.

**Risk:** Scanner lane must compute fingerprint at scan time. TRI assumes it exists and is stable. If scanner does not compute fingerprint, triage cannot be carried forward and every triage will be orphaned on re-scan.

**Mitigation:** TRI's `upsert_triage()` raises 500 if fingerprint is NULL. Scanner lane integration test must verify fingerprint is populated for all findings before TRI test passes.

---

### C-16: Shared Query Parameters (Resolved in contract §3.4, C-16)

**Shared resource:** `GET /scans/{scan_id}/findings` query parameters  
**Features:** DFS (filter/sort), CONF (band filter), TRI (triage status in response)  
**Resolution (per contract C-16):**  
One shared FastAPI dependency `api/core/params.py::common_list_params`, injected with `Depends()`.  
Multi-value filters: OR within category, AND across categories.  
Filter values validated against canonical tuples in `db/models.py`.

**Risk:** TRI does not add query-parameter filtering (triage status is only in response, not a filter). However, if DFS adds triage-status filter later, it must use the same `common_list_params` dependency and not introduce a second filtering layer.

**Mitigation:** TRI's implementation is read-only and does not constrain DFS's choices. If DFS needs to filter by triage status, it will follow the contract's dependency pattern, not invent its own.

---

### RBAC Auth Prerequisite (Blocking, per contract §6 wave 1)

**Shared resource:** `api/core/security.py`, analyst principal identity  
**Affects:** `updated_by` field in triage  
**Dependency:** RBAC merges Wave 1; TRI merges Wave 4. TRI assumes RBAC's `Principal` exists and `updated_by` can be populated with `principal.username`.

**Current state:** `updated_by` is free-text field. RBAC's `require_role()` must be applied to the PATCH endpoint before production.

**Mitigation:** TRI's PATCH handler accepts `updated_by=None` today. RBAC's integration will inject `principal.username` when it lands.

---

### AUD Audit Event Integration (Compatible, per contract C-26)

**Shared resource:** Audit event recording  
**Affects:** `ecdat.triage.update` action  
**Dependency:** AUD merges Wave 2; TRI merges Wave 4. TRI's PATCH handler calls AUD's audit recording function (once published).

**Mitigation:** Existing audit helper already exists in `api/services/audit.py`. TRI calls it; no conflict.

---

### DFS FindingsTable Column Registry (Coordinated, per contract C-13)

**Shared resource:** `dashboard/src/components/FindingsTable.jsx`, `dashboard/src/lib/constants.js`  
**Affects:** Triage status display in table  
**Dependency:** DFS restructures the table into a column registry (Wave 2); TRI adds a column definition (Wave 4).

**Current state:** No registry exists yet. When DFS lands, it will create the registry. TRI will add a column definition referencing the triage status.

**Mitigation:** TRI's specification does not change FindingsTable directly. Frontend lane owns the UI; TRI owns data.

---

## 11. Pre-Answered Ambiguities

### Ambiguity 1: What happens if I PATCH a finding with no fingerprint?

**Scenario:** A finding exists but its `fingerprint` column is NULL (e.g., scanner did not compute it).  
**Resolution:** TRI's PATCH handler raises HTTP 500 with detail "Finding has no fingerprint; cannot record triage." The analyst must contact the scanner team to re-run the scan with fingerprint computation enabled.  
**Rationale:** A triage without a fingerprint cannot be carried forward. Silently accepting it would create orphaned triages.

---

### Ambiguity 2: What happens when the same repository is scanned twice and produces two findings with the same fingerprint?

**Scenario:** Re-scan finds a finding with the same fingerprint. What is the relationship between the old `finding_triage` and the new finding?  
**Resolution:** The old triage's `finding_id` still points to the old finding (which is now stale). The new finding has a new `finding_id` but the same fingerprint. Call `carry_forward_triage_by_fingerprint(new_finding_id, fingerprint)` to read the prior triage, but do NOT create a new triage row. The analyst must explicitly PATCH the new finding to update status. This ensures the analyst reviews the new finding before inheriting a disposition.  
**Rationale:** Auto-propagating dispositions risks false positives (a line edit might have introduced a new weakness). Manual review is safer.

---

### Ambiguity 3: Can I triage a finding in one scan and then expect that triage to apply to the same finding in another scan of a different repository?

**Scenario:** Repository A is scanned, finding is triaged as "false_positive". Repository B is scanned, produces an identical finding (same file, algorithm, library). Does the triage from A apply to B?  
**Resolution:** No. Triages are scoped by fingerprint, and fingerprint is scoped by repository (`repo_id` is part of the hash). Two different repositories have different fingerprints for the same source line. The analyst must triage each repository independently.  
**Rationale:** A false positive in one repo may be a real vulnerability in another (different build configuration, library version, etc.).

---

### Ambiguity 4: What if I change the fingerprint algorithm later? Do all existing triages become orphaned?

**Scenario:** Scanner lane decides to change fingerprint inputs (e.g., include line number, or add `key_size`). All existing `finding_triage.fingerprint` values are now stale. What happens?  
**Resolution:** This is a scanner-lane design decision, not TRI's. If fingerprint changes, the existing triage rows will not match new findings (since the hash will be different). Existing triages remain in the database but are unreachable. Scanner lane must provide a migration script to recompute fingerprints if this happens. This is intentionally out of TRI's scope.  
**Rationale:** Preventing this requires a versioned fingerprint algorithm, which adds complexity. The contract assumes fingerprint is stable; if it must change, that is a data migration, not a TRI change.

---

### Ambiguity 5: Who can call PATCH /scans/{scan_id}/findings/{finding_id}/triage? Do I need a special role?

**Scenario:** An engineer asks: "Can I triage findings, or only security admins?"  
**Resolution:** TRI does not enforce role-based access control. That is RBAC's responsibility. Today, any authenticated caller can PATCH. Once RBAC lands (Wave 1), the PATCH endpoint will be wrapped with `require_role(Role.DEVELOPER, Role.SECURITY_ADMIN)` — the `("findings", "triage")` entry in the RBAC permission matrix. TRI's implementation does not change; RBAC adds the guard.  
**Rationale:** TRI is auth-agnostic. RBAC is the single point for access control.

---

### Ambiguity 6: What about C-15 human sign-off—can I start implementing without it?

**Scenario:** Team asks whether TRI implementation can begin before C-15 is resolved.  
**Resolution:** No. C-15 blocks TRI per the contract (§7, table row "C-15 Exact finding fingerprint inputs" blocks TRI). The fingerprint input set is defined in the contract (sha256 of repo_id, file, algorithm, primitive, library, normalised context), but it is marked Medium confidence and needs sign-off. Do not implement until human (DB lane + scanner lane) confirms the fingerprint algorithm.  
**Rationale:** AGENT_RULES.md #4 requires stopping rather than guessing. The fingerprint algorithm is the foundation of triage carry-forward.

---

### Ambiguity 7: What about `updated_by`? Should I require a username or allow NULL?

**Scenario:** A PATCH request arrives with no authentication context. Should `updated_by` be set to NULL, or should the request be rejected?  
**Resolution:** TRI accepts `updated_by=NULL` (do not reject). RBAC's `Principal` contract (landing Wave 1) will inject the username. Until then, `updated_by` stays NULL and audit_events records `actor_type='api_key'` (per contract C-09). This is intentional: the data model is prepared for RBAC but does not require it.  
**Rationale:** TRI ships before RBAC. Backwards compatibility.

---

### Ambiguity 8: Does triage affect risk score or risk tier?

**Scenario:** Finding is CRITICAL but analyst triages it as "accepted_risk". Does the risk_tier change in `risk_assessments`?  
**Resolution:** No. Triage is a disposition, not a recomputation. The finding's `risk_tier` and `risk_assessment` remain unchanged. The analyst's decision is recorded in `finding_triage.status` only. Risk scoring is frozen per contract C-04 (`risk_engine.py` is read-only for TRI).  
**Rationale:** Triage = what the analyst thinks about this finding. Risk tier = what the deterministic algorithm says. They are separate axes. The dashboard will eventually display both.

---

### Ambiguity 9: Can I triage a finding that has no risk assessment?

**Scenario:** A finding is discovered but risk_engine has not yet run (findings are persisted before risk scoring). Can the analyst triage it?  
**Resolution:** Yes. `finding_triage` is independent of `risk_assessments`. The analyst can triage as soon as a finding exists, even if risk scoring is pending.  
**Rationale:** Triage is a first-pass determination ("this looks like a false positive"); risk scoring is a second pass. Decoupling them is intentional.

---

### Ambiguity 10: What if the same fingerprint appears in two different findings.id rows (a database corruption scenario)?

**Scenario:** Due to a bug, two findings have the same fingerprint but different finding_ids. `finding_triage.finding_id` is UNIQUE, so only one can have a triage row. What happens?  
**Resolution:** This is data corruption and out of scope for TRI. The UNIQUE constraint on `finding_id` prevents two triage rows for one finding, but it does not prevent two findings from having the same fingerprint. This is a scanner-data-quality issue, not a TRI issue. The contract's C-15 resolution assumes fingerprints are correct; if they are not, no triage system can fix it.  
**Rationale:** Garbage in, garbage out. TRI does not validate fingerprint uniqueness.

---

## 12. Test Plan / Definition of Done

### Unit Tests (CRUD Layer)

**File:** `tests/test_triage_crud.py`

```bash
# Run CRUD tests
pytest tests/test_triage_crud.py -xvs
# Expected: All tests pass, 6+ test functions
```

**Tests to implement:**
1. `test_upsert_triage_creates_new()` — Create a new triage, verify all fields.
2. `test_upsert_triage_updates_existing()` — Update status + note, verify updated_at changes.
3. `test_upsert_triage_invalid_status()` — Pass invalid status, expect ValueError.
4. `test_list_triages_for_scan()` — Create 3 triages across 2 findings in 1 scan, verify count.
5. `test_carry_forward_triage_by_fingerprint()` — Record triage, query by fingerprint, verify match.
6. `test_carry_forward_triage_no_match()` — Query for non-existent fingerprint, expect None.

---

### API Endpoint Tests

**File:** `tests/test_triage_api.py`

```bash
# Run API tests
pytest tests/test_triage_api.py -xvs
# Expected: All tests pass, 5+ test functions
```

**Tests to implement:**
1. `test_patch_triage_valid()` — PATCH with valid status, verify 200 + TriageOut response.
2. `test_patch_triage_finding_not_found()` — PATCH non-existent finding, expect 404.
3. `test_patch_triage_wrong_scan()` — PATCH finding from different scan, expect 404.
4. `test_patch_triage_invalid_status()` — PATCH with invalid status, expect 400 + detail message.
5. `test_patch_triage_no_fingerprint()` — Finding has NULL fingerprint, expect 500.

---

### Integration Tests (End-to-End)

**File:** `tests/test_triage_integration.py`

```bash
# Run integration tests
pytest tests/test_triage_integration.py -xvs
# Expected: All tests pass, 2+ test functions
```

**Tests to implement:**
1. `test_scan_triage_rescan_carry_forward()` — 
   - Scan repo, get finding_id + fingerprint.
   - Triage it as "acknowledged".
   - Delete/complete scan, re-scan (new finding_id, same fingerprint).
   - Query via `carry_forward_triage_by_fingerprint()`, verify prior triage is found.
   - Verify new finding can be PATCHed independently.

2. `test_triage_in_findings_response()` —
   - Create finding, triage it.
   - GET /scans/{id}/findings, verify triage field is present and populated in response.

---

### Full Suite Validation

```bash
# Run all existing tests to confirm no regression
pytest tests/ -x --tb=short

# Expected output:
# - All existing tests still pass (no breaking changes to FindingOut, CRUD, API).
# - New triage tests all pass.
# - Total: 40+ tests (existing + new).
```

---

### Swagger/OpenAPI Schema Validation

```bash
# Start server and check schema
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
curl http://127.0.0.1:8000/openapi.json | grep -A 20 "findings.*triage"

# Expected:
# - PATCH /scans/{scan_id}/findings/{finding_id}/triage appears in paths.
# - TriageIn and TriageOut models appear in components/schemas.
# - FindingOut includes triage field.
```

---

### Definition of Done

✅ All CRUD functions implemented and tested.  
✅ Pydantic models (TriageIn, TriageOut) defined.  
✅ PATCH endpoint implemented and returning correct responses.  
✅ Triage field merged into FindingOut.  
✅ All 40+ tests passing (existing + new).  
✅ No regression in existing API tests.  
✅ Fingerprint field populated by scanner (integration with scanner lane).  
✅ Audit event (ecdat.triage.update) recorded.  
✅ OpenAPI schema includes triage endpoint and models.  
✅ Migration 007 applied successfully on fresh DB.  
✅ Code review: no AGENT_RULES violations, contract clauses cited.

---

## 13. Rollback Plan

### If Implementation Breaks the Build

**Symptom:** New tests fail, existing tests regress, or database migration fails.

### Rollback Steps

1. **Database Rollback (if migration fails on apply):**
   ```bash
   # If 007_finding_triage.sql fails to apply:
   # 1. Drop the finding_triage table (if it was partially created)
   # 2. Drop the fingerprint column from findings (if it was added)
   # 3. Revert docker-compose.yml mount for 08_ prefix
   # 4. Restore db/schema.sql to pre-TRI version
   
   # SQL (if manual recovery needed):
   DROP TABLE IF EXISTS finding_triage;
   ALTER TABLE findings DROP COLUMN IF EXISTS fingerprint;
   DROP INDEX IF EXISTS idx_findings_fingerprint;
   DROP INDEX IF EXISTS idx_finding_triage_fingerprint;
   ```

2. **Code Rollback:**
   ```bash
   # Revert commits in this order:
   git revert <commit-triage-router>
   git revert <commit-pydantic-models>
   git revert <commit-crud-functions>
   git revert <commit-orm-models>
   git revert <commit-schema>
   ```

3. **Remove Migration File:**
   ```bash
   rm db/migrations/007_finding_triage.sql
   # Restore docker-compose.yml (remove 08_ mount)
   ```

4. **Verify Cleanup:**
   ```bash
   # Run tests against previous version of schema
   pytest tests/ -x --tb=short
   # Expected: All existing tests pass again.
   
   # Start server and confirm no triage routes in OpenAPI schema
   curl http://127.0.0.1:8000/openapi.json | grep -c "triage"
   # Expected: 0 (no matches)
   ```

---

### If Tests Regress Due to FindingOut Breakage

**Symptom:** Tests in `test_api.py` or `test_crud.py` fail when `triage` field is added to `FindingOut`.

**Rollback:**
```python
# In api/models.py, revert FindingOut to original:
class FindingOut(BaseModel):
    # ... existing fields, no triage field ...
    risk_assessment: "RiskAssessmentOut | None" = None
    # DELETE: triage: "TriageOut | None" = None
```

Then re-run tests:
```bash
pytest tests/test_api.py -x
# Expected: All pass again.
```

---

### If Router Registration Fails

**Symptom:** `app.include_router(triage_router)` fails at startup, or triage endpoint does not appear in OpenAPI schema.

**Rollback:**
```python
# In api/main.py, revert:
# DELETE: from api.routers.triage import router as triage_router
# DELETE: app.include_router(triage_router)
```

---

### If Audit Integration Fails

**Symptom:** PATCH endpoint works but audit event is not recorded, or audit service raises an error.

**Rollback:**
```python
# In api/routers/triage.py, temporarily disable audit:
# Comment out: audit_service.record_event(...)
# Endpoint still works; audit event is skipped.
```

Once AUD feature is available, un-comment.

---

### Restore Full Build

```bash
# After rollback steps, run full test suite
pytest tests/ -x
docker-compose up -d
curl https://localhost:8443/api/health  # or appropriate health endpoint
# Expected: All tests pass, server is healthy.

# If everything fails, restore from git:
git reset --hard HEAD~<number of commits>
docker-compose down
docker volume rm ecdat_postgres_data  # if needed
docker-compose up -d
pytest tests/
```

---

## End of Specification

**Specification Version:** 1.0  
**Status:** Blocked on C-15 human sign-off (fingerprint inputs).  
**Authority:** SYSTEM_INTERFACE_CONTRACT.md § 2.2, § 3.4–3.6, C-15, C-16.  
**Next Step:** Obtain human sign-off from DB lane (Ronak) + scanner lane (Shashank) on fingerprint input set, then unblock implementation.
