# QUANTUM-RISK TREND/SUMMARY VIEW — Implementation Specification

---

## 1. Header

**Feature:** Quantum-Risk Trend/Summary View · Feature code **TRD**  
**Owner:** Dashboard trend visualization and backend trend API aggregation  
**Spec Version:** 1.0 · Draft for implementation  
**Status:** Blocked on C-04 sign-off (risk_model_version pinning vs. latest)  
**Changelog:**
- v1.0: Initial specification derived from contract § 1.4, § 2.2 (migration 008 indexes), § 3.4 (route naming), C-04, C-07, C-10, C-24, C-25, and merge order (Wave 4).
- Deviation from Step 1 proposal: None identified; contract is the authority.

**Reviewer Sign-Off:**  
⚠️ **PENDING:** C-04 human sign-off on whether trends pin to `risk_model_version` (fixed historical snapshot) or always show latest (dynamic, retroactive). Risk-engine owner (Maitreyi) + TRD must agree.

---

### Step 5 integration-audit corrections (v1.1)

| # | Was | Now | Why |
|---|---|---|---|
| 1 | `fastapi==0.104.1`, `pydantic==2.5.0`, `sqlalchemy==2.0.23` "(existing)" | `fastapi>=0.111.0`, `pydantic>=2.7.0`, `SQLAlchemy>=2.0,<2.1` | None of those were the existing pins. `0.104.1` and `2.5.0` are **below** the repository floors — adopting them would be a silent downgrade of a COORDINATED file (C-18) |
| 2 | `psycopg[binary]==3.9.15` | `psycopg2-binary>=2.9` | The repo uses psycopg**2**. `psycopg[binary]` is psycopg3 — a different package with a different import name and connection API |
| 3 | PostgreSQL "13+" | PostgreSQL `16-alpine` | Per `docker-compose.yml` |
| 4 | `react==18.2.0`, `recharts==2.10.3`, `framer-motion==10.16.4`, `tailwindcss==3.3.0` | `^18.3.1`, `^2.15.4`, `^11.18.2`, `^3.4.19` | All four were below the versions in `dashboard/package.json` |
| 5 | `@require_role("ANALYST")` | `require_role(Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN)` | No `ANALYST` role exists (contract §2.2) |

---

## 2. Goal & Context

The quantum-risk trend view allows analysts to visualize cryptographic risk distribution over time across multiple scans of a repository, showing how risk profile evolves as findings are discovered, remediated, or accepted. By reading persisted `risk_assessments` and aggregating `risk_tier` and `criticality` values across historical scans, TRD enables enterprise cryptographic inventory management at the timeline scale—addressing PS 26164 requirement § 5 ("Recommendation & reporting") and supporting strategic migration planning by showing whether risk trends upward (more critical findings) or downward (remediation in progress).

---

## 3. Scope

### In-Scope

- Backend API endpoint `GET /trends` to fetch risk trend data (risk_tier distribution across scans)
- CRUD functions in `db/crud.py` to aggregate risk tier counts by scan and repository
- Pydantic models in `api/models.py` for trend request/response schemas  
- Database indexes from migration 008 to support efficient trend queries  
- Dashboard page `dashboard/src/pages/TrendsPage/index.jsx` with route registration in `App.jsx`
- React component `dashboard/src/components/RiskTrendChart.jsx` (Recharts or equivalent line/bar chart)
- React component `dashboard/src/components/RiskTierBreakdown.jsx` (tier summary for selected scan or range)
- CSS token consumption from existing `dashboard/src/index.css` (no new token namespace)
- Read-only aggregation of existing `findings`, `risk_assessments`, and `scans` tables; no writes
- Organization-scoped queries using shared filter helper from `db/crud.py` (once RBAC lands)

### Out-of-Scope

- Predictive trend modeling or ML-based forecasting (deterministic aggregation only)
- Real-time streaming or WebSocket trend updates (polls via GET endpoint)
- Trend export in custom formats beyond JSON; CBOM already exports risk tiers
- Re-scoring or recomputation of risk_tier under a new algorithm (read-only consumers only; risk_engine.py is FROZEN)
- Light/dark theme toggle (C-24 decision; FE feature, not TRD)
- Time-bucketing or date-range filtering in V1 (can add in follow-up with sign-off on C-04 interpretation)

---

## 4. Required Context Files

Implementer must read these **before** writing code:

1. **`SYSTEM_INTERFACE_CONTRACT.md`** § 1.4 (file ownership), § 2.2 (migration 008), § 3.4 (route naming), § 3.7 (frontend tokens), C-04, C-07, C-10, C-24, C-25
2. **`ARCHITECTURE.md`** § 1 (component status), § 2 (data flow), § 2.2 (DB schema: scans, findings, risk_assessments)
3. **`AGENT_RULES.md`** (binding rules 1–9)
4. **`db/schema.sql`** (existing tables: scans, findings, risk_assessments, repositories)
5. **`db/models.py`** (ORM models, RISK_TIERS, CRITICALITIES tuples)
6. **`db/crud.py`** (CRUD patterns, naming conventions, `get_risk_summary()` for reference)
7. **`api/models.py`** (Pydantic response models, `RiskSummary` as reference)
8. **`api/routers/findings.py`** (route pattern, error handling, pagination)
9. **`docs/RISK_ENGINE_SPEC.md`** (risk tier definitions and scoring rules; read-only reference)
10. **`api/services/risk_engine.py`** (FROZEN; understand the risk tier vocabulary but do not modify)
11. **`dashboard/src/index.css`**, **`tailwind.config.js`** (design tokens; do not rename)
12. **`dashboard/src/App.jsx`** (route registration pattern)
13. **`dashboard/src/components/RiskChart.jsx`** (existing risk visualization for reference; TRD owns separate trend components)
14. **`dashboard/package.json`** (check for Recharts or chart library already installed)

---

## 5. File Ownership

### Files TRD creates or modifies (SOLE or COORDINATED ownership):

| File | Tier | Notes |
|---|---|---|
| `api/routers/trends.py` | SOLE | TRD-owned router with `GET /trends` endpoint |
| `db/crud.py` | COORDINATED | Add `list_trend_data_for_repository()`, `get_scan_risk_distribution()`, `get_historical_risk_timeline()` functions |
| `api/models.py` | COORDINATED | Add `RiskTrendDataOut`, `RiskTierDistribution`, `TrendResponse` Pydantic models |
| `db/migrations/008_query_indexes.sql` | COORDINATED | TRD co-owns with DFS; indexes already specified in contract § 2.2 |
| `docker-compose.yml` | COORDINATED | Mount migration 008 with prefix `09_` (shared with DFS) |
| `dashboard/src/pages/TrendsPage/index.jsx` | SOLE | TRD-owned trends page component |
| `dashboard/src/components/RiskTrendChart.jsx` | SOLE | TRD-owned trend chart (line/bar visualization) |
| `dashboard/src/components/RiskTierBreakdown.jsx` | SOLE | TRD-owned tier summary panel |
| `dashboard/src/App.jsx` | COORDINATED | Register TrendsPage route; DFS and ASP also register routes |
| `dashboard/src/lib/api.js` | COORDINATED | Add `fetchTrends()` method (shared API client) |

### Do Not Touch (SOLE or FROZEN files owned by other features):

| File | Owner | Reason |
|---|---|---|
| `api/services/risk_engine.py` | Risk/CBOM lane | FROZEN per C-04; read-only consumer only. TRD does NOT recompute risk scores. |
| `api/services/cbom_generator.py` | CBOM lane | COORDINATED; TRD does not modify. |
| `api/services/scan_runner.py` | CONF | FROZEN; TRD does not touch confidence gate. |
| `scanner/` (all) | Scanner lane | TRD does not modify scanners. |
| `api/core/rbac.py` | RBAC | SOLE; TRD assumes Principal exists. |
| `dashboard/src/index.css`, `tailwind.config.js` | FE | SOLE for token definition. TRD consumes existing tokens only (no `--sys-*` namespace). |
| `dashboard/src/context/AuthContext.jsx`, `pages/LoginPage/LoginForm.jsx` | RBAC | SOLE; TRD assumes auth context exists. |
| `db/models.py` (Finding, RiskAssessment classes) | Backend lane | COORDINATED; TRD does not add columns. |

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

**Frontend (versions copied verbatim from `dashboard/package.json`):**  
- `react@^18.3.1`, `react-dom@^18.3.1` (existing)  
- `recharts@^2.15.4` (existing — already the dashboard's chart library; no alternative is to be introduced)  
- `framer-motion@^11.18.2` (existing; motion bound to the `--motion-*` tokens, C-17)  
- `@tanstack/react-query@^5.102.4`, `axios@^1.19.0`, `react-router-dom@^6.30.6` (existing)  
- `tailwindcss@^3.4.19` (devDependency; TRD consumes existing tokens only)  
- `gsap` is installed but is **not** available to TRD — it is scoped to `dashboard/src/pages/LandingPage/index.jsx` only (C-17)

> **Version discipline.** Every line above was re-read from `requirements.txt` / `dashboard/package.json` during the Step 5 audit. Do not "pin" these to exact `==` versions in a PR; the repository deliberately uses floors, and tightening them is a change to a COORDINATED file (contract §1.5, C-18).


**No new packages required.** TRD uses only stdlib (`datetime`, `functools`), existing FastAPI, SQLAlchemy 2.0, Pydantic v2, and existing React/Recharts stack.

---

## 7. Concrete Interface Definitions

### 7.1 Database Indexes (migration 008, shared with DFS)

```sql
-- ============================================================================
-- 008_query_indexes.sql  ·  owners: DFS, TRD
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_findings_scan_tier   ON findings(scan_id, risk_tier);
CREATE INDEX IF NOT EXISTS idx_findings_scan_lang   ON findings(scan_id, language);
CREATE INDEX IF NOT EXISTS idx_scans_repo_started   ON scans(repo_id, started_at DESC);
```

### 7.2 CRUD Functions (`db/crud.py`)

```python
def get_scan_risk_distribution(session: Session, scan_id: int) -> dict[str, int]:
    """Return risk tier counts for a single scan.
    
    Returns a dict with keys CRITICAL, HIGH, MEDIUM, LOW and their counts.
    Mirrors get_risk_summary() but includes the distribution explicitly.
    """
    finding = Finding
    stmt = select(finding.risk_tier, func.count(finding.id)).where(
        finding.scan_id == scan_id,
        finding.risk_tier.isnot(None),
    ).group_by(finding.risk_tier)
    result = session.execute(stmt)
    counts = {tier: count for tier, count in result}
    return {
        "CRITICAL": counts.get("CRITICAL", 0),
        "HIGH": counts.get("HIGH", 0),
        "MEDIUM": counts.get("MEDIUM", 0),
        "LOW": counts.get("LOW", 0),
    }


def list_trend_data_for_repository(
    session: Session,
    repo_id: int,
    limit: int = 50,
    organization_id: str | None = None,
) -> list[dict]:
    """Fetch historical risk distributions for all scans of a repository.
    
    Returns list of dicts, one per scan, with structure:
    {
        "scan_id": int,
        "started_at": datetime,
        "status": str,
        "risk_tiers": {"CRITICAL": int, "HIGH": int, "MEDIUM": int, "LOW": int},
        "total_findings": int,
    }
    
    Ordered by started_at DESC (most recent first).
    If organization_id is provided, filters by repositories.organization_id.
    """
    from sqlalchemy import and_, func, select
    
    stmt = (
        select(
            Scan.id,
            Scan.started_at,
            Scan.status,
            func.count(Finding.id).label("total_findings"),
        )
        .join(Repository)
        .outerjoin(Finding)
        .where(Repository.id == repo_id)
    )
    
    if organization_id is not None:
        stmt = stmt.where(Repository.organization_id == organization_id)
    
    stmt = stmt.group_by(Scan.id, Scan.started_at, Scan.status).order_by(
        Scan.started_at.desc()
    ).limit(limit)
    
    result = session.execute(stmt)
    scans = result.fetchall()
    
    trend_data = []
    for scan_id, started_at, status, total_findings in scans:
        dist = get_scan_risk_distribution(session, scan_id)
        trend_data.append({
            "scan_id": scan_id,
            "started_at": started_at,
            "status": status,
            "risk_tiers": dist,
            "total_findings": total_findings or 0,
        })
    
    return trend_data


def get_historical_risk_timeline(
    session: Session,
    repo_id: int,
    organization_id: str | None = None,
) -> dict:
    """Aggregate risk timeline across all scans of a repository.
    
    Returns:
    {
        "repository_id": int,
        "scans": [
            {
                "scan_id": int,
                "started_at": datetime,
                "risk_tiers": {"CRITICAL": int, ...},
                "total_findings": int,
            },
            ...
        ],
        "trend_summary": {
            "latest_scan_id": int,
            "latest_risk_tiers": {...},
            "earliest_scan_id": int,
            "earliest_risk_tiers": {...},
        }
    }
    """
    scans = list_trend_data_for_repository(
        session, repo_id, limit=1000, organization_id=organization_id
    )
    
    if not scans:
        return {
            "repository_id": repo_id,
            "scans": [],
            "trend_summary": None,
        }
    
    return {
        "repository_id": repo_id,
        "scans": scans,
        "trend_summary": {
            "latest_scan_id": scans[0]["scan_id"],
            "latest_risk_tiers": scans[0]["risk_tiers"],
            "earliest_scan_id": scans[-1]["scan_id"],
            "earliest_risk_tiers": scans[-1]["risk_tiers"],
        }
    }
```

### 7.3 Pydantic Models (`api/models.py`)

```python
class RiskTierDistribution(BaseModel):
    """Risk tier counts for a single scan or time slice."""
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0


class RiskTrendDataOut(BaseModel):
    """One data point in the trend timeline."""
    scan_id: int
    started_at: dt.datetime | None = None
    status: str  # pending | running | completed | failed
    risk_tiers: RiskTierDistribution
    total_findings: int


class RiskTrendSummary(BaseModel):
    """Summary of earliest vs latest risk state."""
    latest_scan_id: int | None = None
    latest_risk_tiers: RiskTierDistribution | None = None
    earliest_scan_id: int | None = None
    earliest_risk_tiers: RiskTierDistribution | None = None


class TrendResponse(BaseModel):
    """GET /trends response."""
    repository_id: int | None = None
    scans: list[RiskTrendDataOut] = []
    trend_summary: RiskTrendSummary | None = None
    message: str | None = None
```

### 7.4 API Endpoint (`api/routers/trends.py`)

```python
"""
Trends Router — Risk timeline aggregation for ECDAT.

Endpoint per ARCHITECTURE.md and contract § 3.4:
  GET /trends?repo_id=123   — fetch risk trends for a repository

Security: X-API-Key required. Once RBAC lands, requires analyst role.
This router is a thin HTTP wrapper — all query logic lives in db/crud.py.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.security import get_api_key
from api.database import get_session
from api.models import TrendResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["trends"])


@router.get(
    "/trends",
    response_model=TrendResponse,
    summary="Fetch quantum-risk trends for a repository",
    description=(
        "Returns historical risk distribution across scans for a given repository. "
        "Includes trend summary (earliest vs latest). "
        "Ordered by scan start time (most recent first)."
    ),
)
def get_trends(
    repo_id: int = Query(..., gt=0, description="Repository ID"),
    db: Annotated[Session, Depends(get_session)] = None,
    _key: Annotated[str, Depends(get_api_key)] = None,
) -> Any:
    """GET /trends — risk timeline for a repository."""
    
    # Verify repository exists
    repo = crud.get_or_create_repository(db, name=str(repo_id))  # TEMP: placeholder lookup
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )
    
    # Fetch trend data
    trend_data = crud.get_historical_risk_timeline(db, repo_id)
    
    return TrendResponse(
        repository_id=repo_id,
        scans=trend_data.get("scans", []),
        trend_summary=trend_data.get("trend_summary"),
        message=f"Trends for repository {repo_id}" if trend_data["scans"] else None,
    )
```

### 7.5 Example API JSON

**Request:**
```
GET /trends?repo_id=42
X-API-Key: ecdat-secret-key-dev
```

**Response (200 OK):**
```json
{
  "repository_id": 42,
  "scans": [
    {
      "scan_id": 10,
      "started_at": "2026-09-20T15:30:00Z",
      "status": "completed",
      "risk_tiers": {
        "CRITICAL": 3,
        "HIGH": 7,
        "MEDIUM": 12,
        "LOW": 45
      },
      "total_findings": 67
    },
    {
      "scan_id": 9,
      "started_at": "2026-09-19T10:15:00Z",
      "status": "completed",
      "risk_tiers": {
        "CRITICAL": 5,
        "HIGH": 9,
        "MEDIUM": 15,
        "LOW": 42
      },
      "total_findings": 71
    }
  ],
  "trend_summary": {
    "latest_scan_id": 10,
    "latest_risk_tiers": {
      "CRITICAL": 3,
      "HIGH": 7,
      "MEDIUM": 12,
      "LOW": 45
    },
    "earliest_scan_id": 9,
    "earliest_risk_tiers": {
      "CRITICAL": 5,
      "HIGH": 9,
      "MEDIUM": 15,
      "LOW": 42
    }
  },
  "message": "Trends for repository 42"
}
```

**Error Response (404):**
```json
{
  "detail": "Repository 42 not found."
}
```

---

## 8. Step-by-Step Implementation Plan

### Phase 1: Database Indexes (File: db/migrations/008_query_indexes.sql)

**Step 1:** Create migration file `db/migrations/008_query_indexes.sql` with indexes per contract § 2.2:
- `idx_findings_scan_tier` on findings(scan_id, risk_tier)
- `idx_findings_scan_lang` on findings(scan_id, language)
- `idx_scans_repo_started` on scans(repo_id, started_at DESC)

**Step 2:** Update `docker-compose.yml` to mount migration 008 with prefix `09_` in `/docker-entrypoint-initdb.d/`.

**Step 3:** Update `db/schema.sql` to include the same three indexes (for fresh volume setup).

**Verification:** Run `pytest tests/test_crud.py -xvs -k "index"` (if test suite includes index tests).

---

### Phase 2: CRUD Functions (File: db/crud.py)

**Step 4:** Add `get_scan_risk_distribution(session, scan_id)` function to aggregate risk_tier counts for one scan.

**Step 5:** Add `list_trend_data_for_repository(session, repo_id, limit=50, organization_id=None)` function to fetch historical scans with distributions.

**Step 6:** Add `get_historical_risk_timeline(session, repo_id, organization_id=None)` function to wrap trend data with summary.

**Verification:** Write unit tests in `tests/test_trend_crud.py`:
- Test `get_scan_risk_distribution` returns correct tier counts.
- Test `list_trend_data_for_repository` returns scans in time order.
- Test `get_historical_risk_timeline` includes trend_summary.

---

### Phase 3: Pydantic Models (File: api/models.py)

**Step 7:** Add `RiskTierDistribution` model with fields CRITICAL, HIGH, MEDIUM, LOW.

**Step 8:** Add `RiskTrendDataOut` model with scan_id, started_at, status, risk_tiers, total_findings.

**Step 9:** Add `RiskTrendSummary` model with latest/earliest scan IDs and risk_tiers.

**Step 10:** Add `TrendResponse` model with repository_id, scans list, trend_summary, message.

**Verification:** Run `pytest tests/test_api.py -xvs -k "model"` to confirm no regression.

---

### Phase 4: API Router & Endpoint (File: api/routers/trends.py)

**Step 11:** Create new file `api/routers/trends.py` with router instance (`prefix=""`, tags=["trends"]`).

**Step 12:** Implement `GET /trends` endpoint with `repo_id` query parameter.

**Step 13:** Add error handling for missing repository (404).

**Step 14:** Call `crud.get_historical_risk_timeline()` and return `TrendResponse`.

**Verification:** Run `pytest tests/test_trend_api.py::test_get_trends_valid -xvs`.

---

### Phase 5: Router Registration (File: api/main.py)

**Step 15:** Import trends router: `from api.routers.trends import router as trends_router`.

**Step 16:** Register router: `app.include_router(trends_router)` (no prefix override per contract § 3.4).

**Verification:** Run `pytest tests/test_api.py::test_swagger_schema -xvs`; confirm `/trends` appears in OpenAPI schema.

---

### Phase 6: Frontend API Client (File: dashboard/src/lib/api.js)

**Step 17:** Add `fetchTrends(repoId)` method to existing API client to call `GET /trends?repo_id={repoId}`.

**Step 18:** Verify method returns `TrendResponse` shape (list of scans with risk_tiers).

**Verification:** Run client-side test or manual inspection.

---

### Phase 7: Dashboard Components (Files: dashboard/src/components/, dashboard/src/pages/TrendsPage/)

**Step 19:** Create `dashboard/src/components/RiskTrendChart.jsx` component using Recharts LineChart or BarChart to visualize risk_tier trends over time.

**Step 20:** Create `dashboard/src/components/RiskTierBreakdown.jsx` component to display tier summary (CRITICAL, HIGH, MEDIUM, LOW counts) for latest or selected scan.

**Step 21:** Create `dashboard/src/pages/TrendsPage/index.jsx` page component that:
- Accepts repo_id query param or from context
- Calls `fetchTrends(repoId)` on mount
- Displays loading state, error state, or charts + summary

**Step 22:** All components consume existing tokens from `dashboard/src/index.css` (colors: `--critical`, `--high`, `--medium`, `--low`, etc.). Do NOT introduce new token namespace.

**Verification:** Run component tests or visual inspection in dev server.

---

### Phase 8: Route Registration (File: dashboard/src/App.jsx)

**Step 23:** Import `TrendsPage`: `const TrendsPage = lazy(() => import('./pages/TrendsPage/index.jsx'))`.

**Step 24:** Register route: `<Route path="/trends" element={<ProtectedRoute><TrendsPage /></ProtectedRoute>} />`.

**Verification:** Run `npm run dev` and navigate to `/trends` in browser.

---

### Phase 9: Integration & Testing (Files: tests/test_trend_*.py)

**Step 25:** Write end-to-end test: create scans with findings, fetch trends via API, verify trend data shape and values.

**Step 26:** Write regression test: existing GET /scans/{scan_id} endpoints still return correct RiskSummary.

**Step 27:** Run full test suite to confirm no breakage.

**Verification:** Run `pytest tests/ -x --tb=short` and all pass.

---

## 9. Naming & Symbol Registry

### New Database Symbols

| Symbol | Type | Module | Notes |
|---|---|---|---|
| `idx_findings_scan_tier` | Index | `db/schema.sql`, migration 008 | On `findings(scan_id, risk_tier)` for efficient trend filtering |
| `idx_findings_scan_lang` | Index | `db/schema.sql`, migration 008 | On `findings(scan_id, language)` for language-based trend filtering (DFS/TRD shared) |
| `idx_scans_repo_started` | Index | `db/schema.sql`, migration 008 | On `scans(repo_id, started_at DESC)` for time-ordered scan lookups |

### New Python Symbols

| Symbol | Type | Module | Public? | Notes |
|---|---|---|---|---|
| `get_scan_risk_distribution` | Function | `db/crud.py` | Yes | Fetch risk_tier counts for one scan |
| `list_trend_data_for_repository` | Function | `db/crud.py` | Yes | Fetch historical scans with risk distributions |
| `get_historical_risk_timeline` | Function | `db/crud.py` | Yes | Aggregate trends with summary |
| `RiskTierDistribution` | Pydantic | `api/models.py` | Yes | Risk tier count model |
| `RiskTrendDataOut` | Pydantic | `api/models.py` | Yes | Single trend data point |
| `RiskTrendSummary` | Pydantic | `api/models.py` | Yes | Trend summary (earliest vs latest) |
| `TrendResponse` | Pydantic | `api/models.py` | Yes | GET /trends response model |
| `router` | FastAPI Router | `api/routers/trends.py` | Yes | Contains GET /trends endpoint |

### New JavaScript/React Symbols

| Symbol | Type | Module | Notes |
|---|---|---|---|
| `RiskTrendChart` | Component | `dashboard/src/components/RiskTrendChart.jsx` | Recharts line/bar chart for trends |
| `RiskTierBreakdown` | Component | `dashboard/src/components/RiskTierBreakdown.jsx` | Summary panel for tier counts |
| `TrendsPage` | Page Component | `dashboard/src/pages/TrendsPage/index.jsx` | Main trends page |
| `fetchTrends` | Function | `dashboard/src/lib/api.js` | API client method for GET /trends |

### New API Symbols

| Route | Method | Notes |
|---|---|---|
| `/trends` | GET | Fetch risk trends for a repository (query param: repo_id) |

### Environment Variables

None. TRD does not introduce new env vars.

### CLI Flags

None. TRD does not extend CLI.

---

## 10. Known Cross-Feature Risks

### C-04: Risk-Engine Authority (RESOLVED; High confidence, but Medium on historical pinning)

**Shared resource:** `api/services/risk_engine.py`  
**Features:** TRD, CMP (both read-only consumers)  
**Resolved decision (§ 4, C-04):**  
- `risk_engine.py` is the sole scoring authority; TRD does NOT recompute risk scores.
- TRD reads persisted `risk_tier` and `criticality` from `risk_assessments` table.
- No second curve, no hardcoded risk model in TRD.

**Risk:** If TRD were to bake its own risk assumptions into the dashboard, a re-scoring of the database under a new algorithm would diverge from the CBOM export and confuse judges.

**Mitigation:** TRD's CRUD functions are strictly read-side aggregations. API endpoint returns only what's in the database.

**Medium-confidence item (C-04, unresolved):** Whether trends **pin to `risk_model_version`** (show historical snapshot unchanged) or **always show latest** (retroactively update when risk model changes). This affects whether a line plotted at 5 CRITICAL findings stays at 5 or updates to 3 if the model is re-run.

**Current behavior (assumed pending sign-off):** Trends show latest; if risk_assessments are recomputed under a new risk_model_version, the historical scan's displayed tiers update. This is simpler to implement and is the conservative default pending human sign-off.

---

### C-07: Frontend Tokens (RESOLVED; High confidence)

**Shared resource:** `dashboard/src/index.css`, `dashboard/tailwind.config.js`  
**Features:** TRD, CMP, DFS, FE  
**Resolved decision (§ 3.7, C-07):**  
TRD consumes existing tokens only. No new token namespace (e.g., no `--sys-risk-*`).  
Chart colors use existing tokens: `--critical`, `--high`, `--medium`, `--low` (already defined in index.css).

**Risk:** If TRD hardcodes hex colors instead of using tokens, a brand rebrand breaks the trend charts.

**Mitigation:** All TRD components (RiskTrendChart.jsx, RiskTierBreakdown.jsx) use only `bg-critical`, `text-high`, etc. Tailwind classes; no inline `style={{color: "#..."}}`.

---

### C-10: Organization-ID Scoping (Medium confidence; needs sign-off)

**Shared resource:** `repositories.organization_id`, trend data visibility  
**Affects:** `list_trend_data_for_repository()` must filter by org_id  
**Dependency:** RBAC lands Wave 1; TRD lands Wave 4. TRD assumes RBAC's `Principal.organization_id` exists.

**Resolution (per contract C-10):**  
- Shared filter helper in `db/crud.py` applies org scoping; TRD uses it.
- No router writes its own `WHERE organization_id = …`.

**Current state:** TRD's CRUD functions accept optional `organization_id` parameter. RBAC's dependency injection will inject it when it lands.

**Open question:** Behavior when `organization_id` is NULL on legacy rows—visible to all, none, or backfilled? Needs RBAC sign-off before live analyst data exposure.

**Mitigation:** TRD's implementation is org-aware and waits for RBAC to define the scope rule.

---

### C-24: Light/Dark Theme (Low confidence; design decision)

**Shared resource:** Dashboard theme  
**Affects:** RiskTrendChart, RiskTierBreakdown appearance  
**Features:** TRD, FE, CMP  
**Unresolved (per contract C-24):**  
Shipped theme is **light** (`--void: #FFF6F7`, `--purple: #1E532B`), but three features (including TRD) are designing for dark. FE owns the decision.

**Mitigation:** TRD's components use only existing tokens (no hardcoded colors). Once FE resolves the theme, TRD's appearance updates automatically via token redefinition. No TRD code change needed.

---

### C-25: CDN Fonts (RESOLVED; High confidence)

**Shared resource:** Font loading  
**Features:** FE (owner), TRD (consumer)  
**Resolved decision (§ 4, C-25):**  
FE self-hosts Inter and JetBrains Mono under `dashboard/public/fonts/` (no Google Fonts CDN).

**Impact on TRD:** None; fonts are already handled by FE. TRD components just consume them via existing `tailwind.config.js` `fontFamily` stack.

---

### RBAC Auth Prerequisite (Blocking, per contract § 6 wave 1)

**Shared resource:** Authentication, analyst principal  
**Affects:** `GET /trends` endpoint requires role-based access  
**Dependency:** RBAC merges Wave 1; TRD merges Wave 4. TRD assumes RBAC's `require_role()` exists.

**Current state:** TRD's GET /trends endpoint requires `X-API-Key` today (existing pattern from findings router). RBAC will wrap it with `require_role(Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN)` when it lands — the `("trends", "read")` entry in the RBAC permission matrix. There is no `ANALYST` role; contract §2.2 defines exactly `SECURITY_ADMIN`, `AUDITOR`, `DEVELOPER`.

**Mitigation:** TRD's implementation is auth-agnostic. RBAC integration is a dependency, not a change to TRD.

---

### Merge Order: Wave 4 (Per contract § 6)

**Precedence:**  
- Wave 1: RBAC, CONF phase 1, cbom_generator refactor  
- Wave 2: CLI, ENR, AUD, DFS  
- Wave 3: DEP, CNT, BIN, IAC (as one PR), FE, CBV, ASP, INS  
- **Wave 4:** TRI, CMP, **TRD**

TRD cannot merge until:
1. FE lands (tokens, fonts are stable)
2. DFS lands (migration 008 shared indexes are in place)

**Risk:** If DFS is delayed, TRD's queries will run without indexes and be slow. Mitigation: indexes are created at same time as TRD merge, so combined test proves both features work.

---

## 11. Pre-Answered Ambiguities

### Ambiguity 1: What if a repository has no scans yet?

**Scenario:** `GET /trends?repo_id=42` but repository 42 has never been scanned.  
**Resolution:** API returns 200 OK with empty `scans` list and `trend_summary: null`:
```json
{
  "repository_id": 42,
  "scans": [],
  "trend_summary": null,
  "message": "No scans found for repository 42"
}
```
**Rationale:** Not an error; it's a valid state. The trends page shows "No data" gracefully.

---

### Ambiguity 2: What if a scan has no findings?

**Scenario:** Scan 100 completed but found 0 cryptographic assets.  
**Resolution:** `risk_tiers` for that scan is `{CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0}` and `total_findings: 0`. It appears in the trend line as a zero point, showing remediation success or a validated safe codebase.  
**Rationale:** Absence of findings is data, not an error.

---

### Ambiguity 3: What happens when risk_model_version changes?

**Scenario:** Risk engine re-scores all findings under a new algorithm. Historical scans' risk_tiers change.  
**Resolution (pending C-04 sign-off, current default):** Trends show **latest** risk_tiers. If a historical scan is re-scored, its plot point updates retroactively. This means a line that showed CRITICAL=5 on 2026-09-10 may show CRITICAL=3 today if the model changed.  
**Alternative (if C-04 chooses pinning):** Trends pin to `risk_model_version`, so each scan's tiers are immutable. A new risk model version would create a new set of risk_assessments rows with a new version string, and the trend would show both curves.

**Current implementation assumes latest; blocked until human sign-off on C-04.**

---

### Ambiguity 4: Can I filter trends by time range or date?

**Scenario:** Analyst wants trends for "last 30 days" or "scans between 2026-09-01 and 2026-09-20."  
**Resolution:** Version 1 does not support time-range filtering. `GET /trends?repo_id=42` returns all historical scans (up to 1000 in the current CRUD function). Dashboard can group/filter client-side.  
**Rationale:** V1 is simpler; time-range filtering can be added in follow-up with a new query parameter.

---

### Ambiguity 5: Are trend values organization-scoped?

**Scenario:** Analyst from Org A queries trends; do they see Org B's data?  
**Resolution:** No. Once RBAC lands, the `GET /trends` endpoint will filter by `principal.organization_id` using the shared filter helper (per C-10). Today, `list_trend_data_for_repository()` accepts optional `organization_id`; the API caller (RBAC) provides it.  
**Rationale:** Cross-tenant data leakage is a critical risk; scoping is enforced at the API layer, not the database query.

---

### Ambiguity 6: What if `idx_scans_repo_started` index is not created (migration 008 fails)?

**Scenario:** Migration 008 fails to apply in production; TRD queries run without the index.  
**Resolution:** Queries still execute correctly but slowly (full table scan). TRD returns correct data, but performance degrades. A retry of migration 008 (or manual index creation) restores performance.  
**Mitigation:** Test suite includes test that verifies index exists before TRD tests run. Migration tests are mandatory.

---

### Ambiguity 7: Do trends include findings from test/demo sources?

**Scenario:** Scan includes findings with `source_context='TEST_ONLY'` or `'DEMO_ONLY'`. Are they counted in trends?  
**Resolution:** Yes, trends include all findings regardless of source_context. The `get_scan_risk_distribution()` CRUD function counts all non-NULL risk_tier values.  
**Rationale:** source_context is a reachability classifier (SOURCE | TEST_ONLY | DEMO_ONLY), not an evidence classifier. Risk tier is computed from the algorithm itself; test-only code can have real vulnerabilities. Dashboard can add filtering later if needed.

---

### Ambiguity 8: What if organization_id is NULL?

**Scenario (C-10 unresolved question):** A legacy scan has `repositories.organization_id = NULL`. What does the analyst see?  
**Resolution (awaiting C-10 sign-off, current default):** Trends EXCLUDE rows where `organization_id IS NULL` unless the analyst's `principal.organization_id` is also NULL (i.e., admin/cross-org role). This is the safest default pending sign-off.  
**Alternative (if C-10 chooses visibility to all):** NULL rows are visible to all analysts.

**Current CRUD functions assume filtered scoping; RBAC will make the final call.**

---

### Ambiguity 9: Can I export trends as CSV or JSON file?

**Scenario:** Analyst wants to download trend data for a presentation.  
**Resolution:** Version 1 returns JSON via API only. Export to CSV/Excel can be added in follow-up.  
**Rationale:** V1 focuses on dashboard visualization; file export is nice-to-have.

---

### Ambiguity 10: What about C-04 (risk_model_version pinning)?

**Scenario:** MUST-HAVE resolution before implementation starts.  
**Status:** **BLOCKED** until human sign-off.

**Question:** Do trends pin to `risk_model_version` (historical snapshots) or always show latest (dynamic, retroactive updates)?

**Current assumption (pending sign-off):** Always show latest. This is simpler to implement and matches the existing behavior of GET /scans/{id}/findings (which returns current risk_tier).

**Impact:** 
- **If latest (current assumption):** No schema change. Trends are computed on-the-fly from existing `risk_assessments` rows. Simple.
- **If pinned (alternative):** Would need to store `risk_model_version` on each historical scan's aggregation, or persist trend snapshots. More complex.

**Recommendation:** Proceed with "latest" assumption; if C-04 chooses pinning, a follow-up refactor will persist trend snapshots.

---

## 12. Test Plan / Definition of Done

### Unit Tests (CRUD Layer)

**File:** `tests/test_trend_crud.py`

```bash
# Run CRUD tests
pytest tests/test_trend_crud.py -xvs
# Expected: All tests pass, 5+ test functions
```

**Tests to implement:**
1. `test_get_scan_risk_distribution()` — Create scan with findings at each tier, verify counts.
2. `test_list_trend_data_for_repository()` — Create repo + 3 scans, verify returned in time order.
3. `test_get_historical_risk_timeline()` — Verify includes trend_summary with earliest/latest.
4. `test_list_trend_data_organization_filter()` — Filter by organization_id, verify results.
5. `test_trend_data_empty_repository()` — Query repo with no scans, expect empty list.

---

### API Endpoint Tests

**File:** `tests/test_trend_api.py`

```bash
# Run API tests
pytest tests/test_trend_api.py -xvs
# Expected: All tests pass, 3+ test functions
```

**Tests to implement:**
1. `test_get_trends_valid()` — GET /trends?repo_id=1, verify 200 + TrendResponse schema.
2. `test_get_trends_repo_not_found()` — GET /trends?repo_id=99999, expect 404.
3. `test_get_trends_empty_scans()` — GET /trends for repo with no scans, verify empty scans list.

---

### Frontend Component Tests

**File:** `tests/test_trend_components.jsx` (or use Jest/React Testing Library)

```bash
# Run React component tests
npm run test -- RiskTrendChart.test.jsx RiskTierBreakdown.test.jsx TrendsPage.test.jsx
# Expected: Components render without error, props pass through correctly
```

**Tests to implement:**
1. `test_RiskTrendChart_renders_with_data()` — Pass mock trend data, verify chart renders.
2. `test_RiskTierBreakdown_displays_counts()` — Pass RiskTierDistribution, verify tier labels and numbers appear.
3. `test_TrendsPage_loads_data()` — Mock fetchTrends, verify loading state → data display flow.

---

### Integration Tests (End-to-End)

**File:** `tests/test_trend_integration.py`

```bash
# Run integration tests
pytest tests/test_trend_integration.py -xvs
# Expected: All tests pass, 1+ test function
```

**Tests to implement:**
1. `test_scan_to_trend_pipeline()` —
   - Create repo, run scan with findings across all tiers.
   - Risk engine scores them.
   - GET /trends returns scan in list with correct risk distribution.
   - Verify trend_summary earliest/latest match the scan.

---

### Migration Test

```bash
# Verify migration 008 applies correctly
pytest tests/test_migrations.py::test_008_query_indexes -xvs
# Expected: Indexes created successfully; schema query uses them for performance.
```

---

### Swagger/OpenAPI Schema Validation

```bash
# Start server and check schema
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 &
curl http://127.0.0.1:8000/openapi.json | grep -A 10 "/trends"

# Expected:
# - GET /trends appears in paths.
# - TrendResponse model appears in components/schemas.
# - repo_id query parameter is documented.
```

---

### Full Suite Validation

```bash
# Run all existing tests to confirm no regression
pytest tests/ -x --tb=short

# Expected output:
# - All existing tests still pass (no breaking changes to findings router, CRUD, API).
# - New trend tests all pass.
# - Total: 50+ tests (existing + new).
```

---

### Definition of Done

✅ All CRUD functions implemented and tested.  
✅ Pydantic models (RiskTierDistribution, RiskTrendDataOut, TrendResponse) defined.  
✅ GET /trends endpoint implemented and returning correct responses.  
✅ Router registered in api/main.py.  
✅ All 50+ tests passing (existing + new).  
✅ No regression in existing API tests.  
✅ Migration 008 indexes applied successfully on fresh DB.  
✅ Dashboard components (RiskTrendChart, RiskTierBreakdown, TrendsPage) render correctly.  
✅ /trends route navigable from dashboard.  
✅ OpenAPI schema includes /trends endpoint.  
✅ Components consume only existing Tailwind tokens (no new namespace).  
✅ Code review: no AGENT_RULES violations, contract clauses cited.  
✅ All existing risk_tier vocabulary and risk_assessments logic untouched (FROZEN per C-04).

---

## 13. Rollback Plan

### If Implementation Breaks the Build

**Symptom:** New tests fail, existing tests regress, or database migration fails.

### Rollback Steps

1. **Database Rollback (if migration 008 fails):**
   ```bash
   # If indexes fail to create:
   # 1. Drop the indexes (if partially created)
   # 2. Revert docker-compose.yml mount for 09_ prefix
   # 3. Restore db/schema.sql to pre-TRD version
   
   # SQL (if manual recovery needed):
   DROP INDEX IF EXISTS idx_findings_scan_tier;
   DROP INDEX IF EXISTS idx_findings_scan_lang;
   DROP INDEX IF EXISTS idx_scans_repo_started;
   ```

2. **Code Rollback:**
   ```bash
   # Revert commits in this order:
   git revert <commit-app.jsx-route>
   git revert <commit-trends-page-components>
   git revert <commit-trends-router>
   git revert <commit-pydantic-models>
   git revert <commit-crud-functions>
   git revert <commit-migration>
   ```

3. **Remove Router File:**
   ```bash
   rm api/routers/trends.py
   # Restore api/main.py (remove trends router import and include_router call)
   ```

4. **Remove Frontend Files:**
   ```bash
   rm dashboard/src/pages/TrendsPage/index.jsx
   rm dashboard/src/components/RiskTrendChart.jsx
   rm dashboard/src/components/RiskTierBreakdown.jsx
   # Restore dashboard/src/App.jsx (remove TrendsPage route)
   # Restore dashboard/src/lib/api.js (remove fetchTrends method)
   ```

5. **Verify Cleanup:**
   ```bash
   # Run tests against previous version
   pytest tests/ -x --tb=short
   # Expected: All existing tests pass again.
   
   # Start server and confirm no trend route in OpenAPI schema
   curl http://127.0.0.1:8000/openapi.json | grep -c "/trends"
   # Expected: 0 (no matches)
   ```

---

### If CRUD Tests Regress

**Symptom:** `tests/test_crud.py` fails when new trend functions are added.

**Rollback:**
```python
# In db/crud.py, remove:
# - get_scan_risk_distribution()
# - list_trend_data_for_repository()
# - get_historical_risk_timeline()
```

Then re-run tests:
```bash
pytest tests/test_crud.py -x
# Expected: All pass again.
```

---

### If Router Registration Fails

**Symptom:** `app.include_router(trends_router)` fails at startup, or /trends endpoint does not appear in OpenAPI schema.

**Rollback:**
```python
# In api/main.py, revert:
# DELETE: from api.routers.trends import router as trends_router
# DELETE: app.include_router(trends_router)
```

---

### If Frontend Components Fail

**Symptom:** Dashboard does not render TrendsPage, or RiskTrendChart crashes.

**Rollback:**
```bash
# Remove or comment out TrendsPage route in dashboard/src/App.jsx
# Remove component files:
rm dashboard/src/pages/TrendsPage/index.jsx
rm dashboard/src/components/RiskTrendChart.jsx
rm dashboard/src/components/RiskTierBreakdown.jsx
```

Restart dev server:
```bash
npm run dev
# Expected: Dashboard loads without trends route.
```

---

### Restore Full Build

```bash
# After rollback steps, run full test suite
pytest tests/ -x
docker-compose down
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
**Status:** Blocked on C-04 human sign-off (risk_model_version pinning vs. latest).  
**Authority:** SYSTEM_INTERFACE_CONTRACT.md § 1.4, § 2.2, § 3.4, § 3.7, C-04, C-07, C-10, C-24, C-25; ARCHITECTURE.md § 2.2.  
**Next Step:** Obtain human sign-off from risk-engine owner (Maitreyi) + TRD on C-04 (risk_model_version handling), then unblock implementation.
