# Agent Status Page — Complete Implementation Specification

---

## 1. Header

**Feature Name:** Agent Status Page  
**Feature Code:** `ASP`  
**Owner:** Frontend team (Karan, Satyam) + Backend integration (Shreyanshi)  
**Spec Version:** 1.0 (aligned with SYSTEM_INTERFACE_CONTRACT v2, draft)  
**Status:** Ready for implementation (Wave 2, unblocked by ENR in Wave 1)  
**Changelog from Step 1 proposal:**
- Removed proposal to create `/agents` endpoint (now owned by ENR, ASP consumes read-only)
- Scoped "stale window" to open sign-off item C-06 (exact threshold TBD by team, not spec'd here)
- Aligned database tables to existing `reports`, `agents`, `enrollment_tokens` (no new tables)
- Changed `organization_id` scoping to conditional per C-10 (NULL handling deferred to RBAC feature)

**Reviewer Sign-Off:** [*pending team signatures*]

---

### Step 5 integration-audit corrections (v1.1)

| # | Was | Now | Why |
|---|---|---|---|
| 1 | `require_role("analyst")` | `require_role(Role.AUDITOR, Role.SECURITY_ADMIN)` | No `analyst` role exists. Contract §2.2 defines exactly `SECURITY_ADMIN`, `AUDITOR`, `DEVELOPER` |
| 2 | `require_role` imported from `api/core/security.py` | imported from `api/core/rbac.py` | `Role` and `require_role` are both defined in `rbac.py` (RBAC spec §7) |
| 3 | Section 8 Step 3: "Create new file `api/routers/agents.py`" | ENR implements; ASP reviews the response contract only | Contradicted this spec's own Section 5 and C-05; `api/routers/agents.py` is SOLE to ENR |
| 4 | `bg-green-100 text-green-800`, `bg-yellow-100`, `bg-gray-100`, `bg-red-100` | `bg-green-10 text-green`, `bg-surface-r text-medium` / `text-t4` / `text-critical` | C-07 / §3.7 forbid raw palette values. Worse, `tailwind.config.js` redefines `green` as a single token value, so `bg-green-100` resolves to nothing and renders unstyled |
| 5 | `GET /agents/{agentId}` | `GET /agents/{agent_id}` | Path params are snake_case (§3.4); the JS variable name stays `agentId` |

---

## 2. Goal & Context

**Problem:** Enterprises deploying ECDAT agents across distributed repositories need visibility into agent health and delivery status. Currently, there is no dashboard view showing which agents are active, when they last reported, how many scans they delivered, and whether reports are authentic (signed and verifiable). This visibility is essential for maintaining confidence in the supply-chain integrity of cryptographic discovery results.

**PS 26164 Requirement:** Requirement #4 (Recommendation & Reporting) — *agents must remain integral to the enterprise's audit trail, proving report provenance via Ed25519 signatures and demonstrating delivery/liveness through evidence-based status*. A read-only agent status page operationalizes this guarantee.

**Success Criterion:** An authenticated analyst can open `/agents` in the dashboard, see a table of enrolled agents with last-report timestamp, scan count, latest scan link, and signature verification state, and drill into individual agent history without mutation capabilities. The page surfaces loading states, empty states, permission-denied (RBAC), and stale-agent warnings (time window per C-06).

---

## 3. Scope

### In-Scope
- **Agent Status Page route & views:** New page at `/agents` displaying enrolled agents, sortable/filterable by organization (per RBAC scoping).
- **Agent Status Table component:** List of agents with columns: agent ID, registration time, last-report time, report count, latest scan reference, signature state (verified/unverified/error), and one action (drill-in to agent history).
- **Agent Status Card component:** Summary card for an individual agent showing enrollment date, total reports accepted, scan summary (count by risk tier), and a drill-in link to that agent's full history page.
- **Status-indicator semantics:** `active` (reported within the stale window), `stale` (no report in stale window), `no-report` (enrolled but never reported), `error` (signature verification failed).
- **Signature verification display:** Show pass/fail per report's Ed25519 signature validation (do not re-verify; trust the database's `signature_verified` boolean set by the intake pipeline).
- **Real-time polling:** TanStack Query hook polling the `GET /agents` endpoint every 30 seconds (configurable).
- **Organization scoping:** Agents filtered to the authenticated user's organization (RBAC dependency, C-10).
- **UI patterns:** Loading skeleton, empty state ("No agents enrolled"), permission-denied state ("You do not have access to agent data"), and stale-agent warning badge on the table rows.

### Out-of-Scope
- **Agent control/mutation:** No "pause agent," "revoke agent," "rerun scan" buttons. This page is read-only.
- **Real-time heartbeat status:** No live process health checks. Status is evidence-based (last report timestamp only).
- **Scan queue or task scheduling:** No integration with agent command-and-control.
- **Agent enrollment UI:** Agent registration/enrollment is owned by ENR feature; ASP only displays enrolled agents.
- **Bulk agent export:** No CSV/JSON bulk export of agent roster (out of scope; may be future UX).
- **Custom thresholds or alerts:** No per-agent alert configuration; stale window is global and set by C-06 team decision.

---

## 4. Required Context Files

Implementer must read these files in this order before beginning work:

1. **`SYSTEM_INTERFACE_CONTRACT.md`** — Canonical file ownership, merge order (Wave 2), conflict resolutions C-05, C-06, C-10.
2. **`ARCHITECTURE.md`** — FastAPI application structure, database schema, auth context, and integration patterns.
3. **`db/schema.sql`** — Exact `agents`, `enrollment_tokens`, `reports` table definitions and columns.
4. **`db/models.py`** — SQLAlchemy ORM models (Agent, EnrollmentToken, Report); confirm primary key types and relationships.
5. **`api/routers/agents.py`** — Read-only endpoint specification owned by ENR; ASP calls this, does not modify it.
6. **`api/core/security.py`** — RBAC/auth dependency injection pattern (Principal/require_role).
7. **`api/models.py`** — Pydantic response schemas for agents, reports, and status enums.
8. **`dashboard/src/App.jsx`** — Route registration pattern; ASP registers `/agents` route here.
9. **`dashboard/src/lib/api.js`** — Frontend API client; ASP adds `getAgents()` method.
10. **`dashboard/src/lib/constants.js`** — Shared UI constants (status labels, colors, time windows).
11. **`dashboard/package.json`** — Verify React Router, TanStack Query, and Recharts versions already pinned.

---

## 5. File Ownership

### Files ASP Creates (SOLE Ownership)

These files are **new** and ASP owns them exclusively. No other feature may modify them:

- **`dashboard/src/pages/AgentStatusPage/index.jsx`** — Main page component; mounts AgentStatusTable and any filters/controls.
- **`dashboard/src/components/AgentStatusTable.jsx`** — Tabular display of agents with inline status indicators.
- **`dashboard/src/components/AgentStatusCard.jsx`** — Summary card view for a single agent (used in drill-in detail view or on hover).
- **`dashboard/src/hooks/useAgents.js`** — TanStack Query custom hook; `useAgents(organizationId?)`, `useAgent(agentId)`, polling logic.

### Files ASP Modifies (COORDINATED Ownership)

These files are shared; ASP edits are coordinated through the named integration owner:

- **`dashboard/src/App.jsx`** (Integration Owner: Frontend lane, Karan/Satyam)
  - **Edit:** Register the `/agents` route pointing to `<AgentStatusPage />`.
  - **Constraint:** Do not break existing routes (DashboardPage, LoginPage, TrendsPage, etc.). Use React Router `<Route>` pattern consistent with existing code.

- **`dashboard/src/lib/api.js`** (Integration Owner: Frontend lane, Karan/Satyam)
  - **Edit:** Add two methods:
    - `getAgents(organizationId?: string): Promise<Agent[]>` — Call `GET /agents` with optional org filter.
    - `getAgent(agentId: string): Promise<AgentDetail>` — Call `GET /agents/{agent_id}` (if ENR exposes this; else use list + filter client-side).
  - **Constraint:** Match the existing fetch wrapper pattern (auth header, error handling).

- **`dashboard/src/lib/constants.js`** (Integration Owner: Frontend lane)
  - **Edit:** Add constants:
    - `AGENT_STATUS_LABELS = { active: "Active", stale: "Stale", no_report: "Not Reporting", error: "Signature Error" }`
    - `AGENT_STATUS_COLORS` — must map to ECDAT design tokens (`text-green`, `text-medium`, `text-t4`, `text-critical`), never raw Tailwind palette names (C-07, §3.7)
    - `AGENT_POLLING_INTERVAL_MS = 30000` (configurable via ENV if needed)
    - `STALE_AGENT_WINDOW_DAYS` — TBD by C-06; placeholder value 7 until resolved.
  - **Constraint:** Do not rename existing constants.

### Files ASP Does NOT Touch (FROZEN / SOLE to Other Features)

**Do not open PRs against these files.** They are owned by other features or frozen by the contract:

- `api/routers/agents.py` — **SOLE to ENR**. ASP consumes the `/agents` endpoint; does not modify the router.
- `api/core/security.py` — **COORDINATED by backend lane (Shreyanshi), modified first by RBAC**. ASP uses its `Principal` and `require_role` exports; does not modify auth logic.
- `api/models.py` — **COORDINATED by backend lane**. ASP may read `AgentResponse`, `ReportResponse` schemas; additions go through Shreyanshi.
- `db/schema.sql`, `db/models.py`, `db/crud.py` — **COORDINATED by DB lane (Ronak)**. ENR adds `agents` and `enrollment_tokens` tables; ASP reads from them via the ORM, does not issue migrations.
- `dashboard/src/index.css`, `tailwind.config.js` — **SOLE to FE (Karan)**. ASP uses existing Tailwind utilities; does not add new design tokens.
- `dashboard/src/components/ConfidenceStamp.jsx`, `FindingsTable.jsx` — **Owned by CONF and DFS respectively**. ASP does not modify them.
- `api/routers/remediation.py`, `cbom.py`, `scans.py` — **Owned by other features**. ASP does not modify scan-related routers.

---

## 6. Tech Stack & Pinned Versions

**Frontend:**
- **React** — v18.x (pinned in `dashboard/package.json`, no change)
- **React Router** — v6.x (pinned, used for page routing)
- **TanStack Query (react-query)** — v5.x (pinned, used for polling `GET /agents`)
- **Tailwind CSS** — v3.x (pinned in `tailwind.config.js`)
- **Lucide React** — v0.x (pinned, used for status icons: CheckCircle, AlertCircle, Clock, etc.)
- **Vite** — v5.x (build tool, no change)

**Backend:**
- **FastAPI** — v0.x (pinned in `requirements.txt`, no change)
- **SQLAlchemy** — v2.0 (pinned, ORM for Agent/Report queries)
- **Pydantic** — v2.x (pinned, response validation)
- **PostgreSQL** — v16 (via docker-compose, no change)
- **Python** — 3.11 (existing constraint)

**Verification:**
- **Do NOT add** new npm or Python packages. If a dependency is missing, that is a pre-wave-1 blocker (signaled to Shreyanshi or Karan).
- **Do NOT change versions** of existing pinned deps. If you need a newer feature, raise it to the team lead before coding.

---

## 7. Concrete Interface Definitions

### Frontend Components

```javascript
// dashboard/src/pages/AgentStatusPage/index.jsx
export default function AgentStatusPage() {
  const { data: agents, isLoading, isError, error } = useAgents();
  // Returns: { agents: Agent[], isLoading: bool, isError: bool, error?: Error }
  // Renders: <AgentStatusTable agents={agents} loading={isLoading} /> or error/loading skeleton
}

// dashboard/src/components/AgentStatusTable.jsx
interface AgentStatusTableProps {
  agents: Agent[];
  loading?: boolean;
  onRowClick?: (agentId: string) => void;
}
export default function AgentStatusTable(props: AgentStatusTableProps) {
  // Renders: <table> with columns [ID, Registered, Last Report, Reports, Latest Scan, Signature, Status]
  // Status cell shows badge: active (green), stale (yellow), no_report (gray), error (red)
  // Row click drills into AgentDetailPage or modal
}

// dashboard/src/components/AgentStatusCard.jsx
interface AgentStatusCardProps {
  agent: Agent;
  showDrillIn?: boolean;
}
export default function AgentStatusCard(props: AgentStatusCardProps) {
  // Renders: <Card> with agent summary: enrollment date, total reports, scan breakdown, status badge
}

// dashboard/src/hooks/useAgents.js
export function useAgents(organizationId?: string) {
  // Returns: useQuery({
  //   queryKey: ["agents", organizationId],
  //   queryFn: () => api.getAgents(organizationId),
  //   refetchInterval: 30000,  // AGENT_POLLING_INTERVAL_MS
  //   staleTime: 15000,
  // })
}

export function useAgent(agentId: string) {
  // Returns: useQuery({
  //   queryKey: ["agent", agentId],
  //   queryFn: () => api.getAgent(agentId),
  //   refetchInterval: 30000,
  // })
}
```

### Frontend API Client

```javascript
// dashboard/src/lib/api.js — additions

export const getAgents = async (organizationId?: string): Promise<Agent[]> => {
  const url = new URL(`${API_BASE_URL}/agents`);
  if (organizationId) {
    url.searchParams.append("organization_id", organizationId);
  }
  const response = await fetch(url.toString(), {
    headers: authHeaders(), // Reuse existing pattern
  });
  if (!response.ok) {
    throw new Error(`GET /agents failed: ${response.statusText}`);
  }
  return response.json();
};

export const getAgent = async (agentId: string): Promise<Agent> => {
  const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(`GET /agents/{agent_id} failed: ${response.statusText}`);
  }
  return response.json();
};
```

### Frontend Data Model

```javascript
// dashboard/src/lib/constants.js — additions

export const AGENT_STATUS = {
  ACTIVE: "active",       // Last report ≤ stale window
  STALE: "stale",         // Last report > stale window
  NO_REPORT: "no_report", // Enrolled but no report ever
  ERROR: "error",         // Signature verification failed
};

export const AGENT_STATUS_LABELS = {
  [AGENT_STATUS.ACTIVE]: "Active",
  [AGENT_STATUS.STALE]: "Stale",
  [AGENT_STATUS.NO_REPORT]: "Not Reporting",
  [AGENT_STATUS.ERROR]: "Signature Error",
};

export const AGENT_STATUS_COLORS = {
  // ECDAT design tokens ONLY (dashboard/tailwind.config.js), per C-07 / contract §3.7.
  // Do not use numeric Tailwind palette steps here. `tailwind.config.js` redefines
  // `green` as a single value (`var(--green)`), so `bg-green-100` / `text-green-800`
  // do not exist in the merged palette and render with no styling at all.
  [AGENT_STATUS.ACTIVE]:    "bg-green-10 text-green",
  [AGENT_STATUS.STALE]:     "bg-surface-r text-medium",
  [AGENT_STATUS.NO_REPORT]: "bg-surface-r text-t4",
  [AGENT_STATUS.ERROR]:     "bg-surface-r text-critical",
};

export const AGENT_POLLING_INTERVAL_MS = 30000;
export const STALE_AGENT_WINDOW_DAYS = 7; // PLACEHOLDER; C-06 decision pending
```

### Backend Data Models (Pydantic Schemas)

```python
# api/models.py — additions

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReportSummary(BaseModel):
    """Summary of a report for agent status display."""
    id: int
    created_at: datetime
    scan_id: Optional[int]
    signature_verified: bool  # Trust database's verification result
    agent_id: str

class AgentResponse(BaseModel):
    """Agent status response for dashboard."""
    agent_id: str
    enrolled_at: datetime
    organization_id: Optional[str]
    last_report_time: Optional[datetime]  # NULL if no report ever
    accepted_report_count: int            # Total reports persisted
    latest_report: Optional[ReportSummary]  # Most recent report
    latest_scan_id: Optional[int]         # Latest scan from latest report
    delivery_status: str  # "active" | "stale" | "no_report" | "error"

    class Config:
        from_attributes = True

class AgentsListResponse(BaseModel):
    """List of agents for the /agents endpoint."""
    agents: list[AgentResponse]
    total_count: int
    organization_id: Optional[str]
```

### Backend Read-Only Endpoint (Owned by ENR, Called by ASP)

```python
# api/routers/agents.py — specification for ENR to implement
# from api.core.rbac import Principal, Role, require_role

from fastapi import APIRouter, Depends, Query
from api.core.security import require_role  # RBAC dependency
from api.models import AgentResponse, AgentsListResponse

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("", response_model=AgentsListResponse)
async def list_agents(
    organization_id: Optional[str] = Query(None),
    principal: Principal = Depends(require_role(Role.AUDITOR, Role.SECURITY_ADMIN)),  # RBAC: read-only analyst access
):
    """
    List enrolled agents for the authenticated user's organization.
    
    If organization_id is provided, filter to that org.
    If not provided, use principal.organization_id.
    If principal has cross-org permissions, organization_id filters the result.
    
    Returns: { agents: [...], total_count: int, organization_id: str }
    """
    pass  # ENR implements; ASP calls via api.getAgents()

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    principal: Principal = Depends(require_role(Role.AUDITOR, Role.SECURITY_ADMIN)),
):
    """
    Get a single agent's status by ID.
    
    Returns: AgentResponse with delivery_status computed at query time.
    """
    pass  # ENR implements; ASP calls via api.getAgent()
```

### Database Schema (Already Defined by ENR)

```sql
-- db/schema.sql — relevant excerpts (ENR owns these; ASP reads)

-- Agents table (created by ENR)
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "agent_worker_01"
    organization_id VARCHAR(255),            -- NULL if not scoped (C-10 handling)
    enrolled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Reports table (already exists for report-sync)
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    organization_id VARCHAR(255),
    scan_id INTEGER REFERENCES scans(id) ON DELETE SET NULL,
    bundle_digest VARCHAR(64),
    signature_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Enrollment tokens table (created by ENR)
CREATE TABLE enrollment_tokens (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) UNIQUE NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
```

### Database Query Layer (CRUD)

```python
# db/crud.py — additions

from db.models import Agent, Report
from sqlalchemy import func
from datetime import datetime, timedelta

async def get_agents_for_org(
    db: Session,
    organization_id: Optional[str],
    stale_window_days: int = 7
) -> list[dict]:
    """
    Fetch agents and their status for the given org.
    
    Returns list of dicts:
    {
        "agent_id": str,
        "enrolled_at": datetime,
        "organization_id": str,
        "last_report_time": datetime | None,
        "accepted_report_count": int,
        "latest_report": Report | None,
        "delivery_status": "active" | "stale" | "no_report" | "error"
    }
    """
    query = db.query(Agent).filter(Agent.organization_id == organization_id)
    agents = query.all()
    
    result = []
    now = datetime.utcnow()
    stale_threshold = now - timedelta(days=stale_window_days)
    
    for agent in agents:
        reports = db.query(Report).filter(Report.agent_id == agent.agent_id).order_by(Report.created_at.desc()).all()
        latest_report = reports[0] if reports else None
        
        if latest_report is None:
            status = "no_report"
        elif not latest_report.signature_verified:
            status = "error"
        elif latest_report.created_at >= stale_threshold:
            status = "active"
        else:
            status = "stale"
        
        result.append({
            "agent_id": agent.agent_id,
            "enrolled_at": agent.enrolled_at,
            "organization_id": agent.organization_id,
            "last_report_time": latest_report.created_at if latest_report else None,
            "accepted_report_count": len(reports),
            "latest_report": latest_report,
            "delivery_status": status,
        })
    
    return result

async def get_agent_by_id(db: Session, agent_id: str) -> dict:
    """Fetch a single agent's status; same structure as get_agents_for_org item."""
    # Similar logic; return single dict or None
    pass
```

---

## 8. Step-by-Step Implementation Plan

Execute in this order; each step is tied to one file and one PR (after Wave 1 RBAC merges).

### Step 1: Backend Data Models (1 PR)
**File:** `api/models.py`  
**PR Title:** "ASP: Add agent status Pydantic schemas"  
**Changes:**
- Add `ReportSummary`, `AgentResponse`, `AgentsListResponse` classes (copy from Section 7).
- Import datetime, Optional from stdlib.
- Do not modify existing schemas (DFS, TRI, CMP may be adding columns; coordinate via Shreyanshi).

**Test:** `pytest tests/test_api.py -k "AgentResponse" -v` (schema validation only, no endpoint yet)

### Step 2: Backend CRUD Queries (1 PR)
**File:** `db/crud.py`  
**PR Title:** "ASP: Add agent status aggregation queries"  
**Changes:**
- Add `get_agents_for_org()` function (copy from Section 7).
- Add `get_agent_by_id()` function.
- Import datetime, timedelta, func from sqlalchemy.
- Compute `delivery_status` at query time based on `last_report_time` and `signature_verified`.

**Test:** 
```bash
pytest tests/test_crud.py -k "test_get_agents_for_org" -v
# Expects: empty list if no agents; status="no_report" if enrolled but no reports; status="active" if report within window
```

### Step 3: Backend Read-Only Endpoint (1 PR, coordinated with ENR)
**File:** `api/routers/agents.py`  
**PR Title:** "ENR+ASP: Implement GET /agents read-only analyst endpoint"  
**Ownership:** ENR owns and implements this file (C-05, contract §1.2 lists `api/routers/agents.py` as **SOLE / ENR**). ASP does **not** open a PR against it — ASP's deliverable in this step is review sign-off on the response contract only.  
**ENR implements (ASP reviews):**
- `GET /agents` (list) and `GET /agents/{agent_id}` (detail) in the existing ENR-owned `api/routers/agents.py`.
- Uses `get_agents_for_org()` and `get_agent_by_id()` from CRUD (ASP contributes these to `db/crud.py`, which is COORDINATED, not SOLE).
- Applies `require_role(Role.AUDITOR, Role.SECURITY_ADMIN)` from `api/core/rbac.py` (`Role` and `require_role` are both defined there, not in `api/core/security.py`).
- Mounted in `api/main.py` by the backend lane in the RBAC → ENR → AUD order (C-09).

**ASP blocks here if ENR has not merged.** Do not stub the router locally to unblock frontend work; use the fixture payload in Section 7 against a mocked client instead.

**Test:**
```bash
pytest tests/test_api.py -k "test_get_agents_unauthenticated" -v
# Expects: 403 Forbidden
pytest tests/test_api.py -k "test_get_agents_auditor" -v
# Expects: 200, { agents: [...], total_count: int, organization_id: str }
```

### Step 4: Database CRUD Integration Test (1 PR)
**File:** `tests/test_agents.py` (new)  
**PR Title:** "ASP: Add agent status integration tests"  
**Changes:**
- Create `tests/test_agents.py`.
- Write fixtures: `create_test_agent()`, `create_test_report()`.
- Test scenarios: active agent, stale agent, no-report agent, signature-error agent.
- Test org scoping: filter agents by organization_id.

**Test:**
```bash
pytest tests/test_agents.py -v
# Expects: 4 tests passing, one for each delivery_status value
```

### Step 5: Frontend Constants & API Client (1 PR)
**File:** `dashboard/src/lib/constants.js`, `dashboard/src/lib/api.js`  
**PR Title:** "ASP: Add agent constants and API client methods"  
**Changes:**
- Add `AGENT_STATUS`, `AGENT_STATUS_LABELS`, `AGENT_STATUS_COLORS`, `AGENT_POLLING_INTERVAL_MS`, `STALE_AGENT_WINDOW_DAYS` to constants.js (copy from Section 7).
- Add `getAgents()` and `getAgent()` methods to api.js (copy from Section 7).
- Use existing `authHeaders()` pattern; do not introduce new auth handling.

**Test:**
```bash
npm run build  # Vite build should pass
npm run lint   # ESLint should pass
```

### Step 6: Frontend Custom Hook (1 PR)
**File:** `dashboard/src/hooks/useAgents.js`  
**PR Title:** "ASP: Add TanStack Query hook for agent status polling"  
**Changes:**
- Create new file `dashboard/src/hooks/useAgents.js`.
- Export `useAgents(organizationId?)` and `useAgent(agentId)` hooks (copy from Section 7).
- Use TanStack Query v5 syntax: `useQuery()`.
- Set refetchInterval to `AGENT_POLLING_INTERVAL_MS`.

**Test:**
```bash
# Manual: import useAgents in a test component, render, verify polling fires
# Or: write React Testing Library test for hook behavior
```

### Step 7: Frontend Components (2 PRs)
**PR 1: `dashboard/src/components/AgentStatusTable.jsx`**  
**Title:** "ASP: Implement agent status table component"  
**Changes:**
- Create AgentStatusTable component (see Section 7 for signature).
- Render `<table>` with rows per agent.
- Columns: agent_id, enrolled_at, last_report_time, accepted_report_count, latest_scan_id, signature_verified, delivery_status.
- Status cell: use `AGENT_STATUS_COLORS` badge from constants.
- Loading state: render skeleton placeholder rows.
- Empty state: "No agents enrolled" message.
- Use Lucide React icons (CheckCircle for verified, AlertCircle for error, Clock for stale).

**PR 2: `dashboard/src/components/AgentStatusCard.jsx`**  
**Title:** "ASP: Implement agent summary card component"  
**Changes:**
- Create AgentStatusCard component (see Section 7 for signature).
- Show: enrollment date, total reports, scan summary (breakdown by risk tier if available), status badge.
- Optional drill-in link (onRowClick callback).
- Match dashboard's existing Card styling (re-use `<Card>` from `dashboard/src/components/ui/Card.jsx`).

**Test:**
```bash
npm run test  # React Testing Library tests for component rendering
npm run build
```

### Step 8: Frontend Page & Routing (2 PRs)
**PR 1: `dashboard/src/pages/AgentStatusPage/index.jsx`**  
**Title:** "ASP: Implement agent status page"  
**Changes:**
- Create new directory `dashboard/src/pages/AgentStatusPage/`.
- Create `index.jsx` with default export `<AgentStatusPage />`.
- Use `useAgents()` hook.
- Render `<AgentStatusTable>` with data.
- Handle loading state (skeleton), error state (error message), empty state.
- Add optional filters/search (out of scope for Step 1; use basic layout now).

**PR 2: `dashboard/src/App.jsx`**  
**Title:** "ASP: Register /agents route"  
**Changes:**
- Import `AgentStatusPage` from `dashboard/src/pages/AgentStatusPage/index.jsx`.
- Add `<Route path="/agents" element={<AgentStatusPage />} />` in the router.
- Place after DashboardPage and before or after TrendsPage (TBD by team; just not conflicting).

**Test:**
```bash
npm run dev
# Open http://localhost:5173/agents
# Verify table loads, agents render, polling fires every 30s
```

### Step 9: E2E Test & Documentation (1 PR)
**File:** `tests/test_agents_e2e.py` or `docs/AGENT_STATUS_PAGE.md`  
**Title:** "ASP: E2E tests and documentation"  
**Changes:**
- Write Playwright E2E test for happy path: load `/agents`, verify table renders, verify polling works.
- Or: write markdown documentation explaining agent status page usage, stale window, signature verification.
- Update `docs/DASHBOARD_IMPROVEMENT_REVIEW.md` if it exists; note the new `/agents` page.

**Test:**
```bash
npm run test:e2e  # If Playwright is set up
# Or: manual walkthrough of the 5-minute demo
```

---

## 9. Naming & Symbol Registry

All new symbols introduced by this feature, checked against contract's naming conventions and shared-resource index for collisions.

### Frontend Symbols

| Symbol | Type | File | Notes |
|---|---|---|---|
| `AgentStatusPage` | React Component | `dashboard/src/pages/AgentStatusPage/index.jsx` | Matches existing page naming (e.g., DashboardPage) |
| `AgentStatusTable` | React Component | `dashboard/src/components/AgentStatusTable.jsx` | Matches existing table naming (e.g., FindingsTable) |
| `AgentStatusCard` | React Component | `dashboard/src/components/AgentStatusCard.jsx` | New card type; no collision |
| `useAgents` | React Hook | `dashboard/src/hooks/useAgents.js` | Matches pattern (useScans, useFindings exist) |
| `useAgent` | React Hook | `dashboard/src/hooks/useAgents.js` | Single-agent variant |
| `getAgents` | API Method | `dashboard/src/lib/api.js` | Matches pattern (getScans, getFindings) |
| `getAgent` | API Method | `dashboard/src/lib/api.js` | Single-agent variant |
| `AGENT_STATUS` | Constant | `dashboard/src/lib/constants.js` | Enum-like object: ACTIVE, STALE, NO_REPORT, ERROR |
| `AGENT_STATUS_LABELS` | Constant | `dashboard/src/lib/constants.js` | i18n-friendly labels |
| `AGENT_STATUS_COLORS` | Constant | `dashboard/src/lib/constants.js` | Tailwind color classes |
| `AGENT_POLLING_INTERVAL_MS` | Constant | `dashboard/src/lib/constants.js` | 30000 ms (30 sec) |
| `STALE_AGENT_WINDOW_DAYS` | Constant | `dashboard/src/lib/constants.js` | TBD by C-06; placeholder 7 |

### Backend Symbols

| Symbol | Type | File | Notes |
|---|---|---|---|
| `ReportSummary` | Pydantic Model | `api/models.py` | For nested report in AgentResponse |
| `AgentResponse` | Pydantic Model | `api/models.py` | Individual agent status |
| `AgentsListResponse` | Pydantic Model | `api/models.py` | Response for `GET /agents` list endpoint |
| `get_agents_for_org` | Function | `db/crud.py` | Query helper; org-scoped agent list |
| `get_agent_by_id` | Function | `db/crud.py` | Query helper; single agent |
| `/agents` | Endpoint | `api/routers/agents.py` | GET list; owned by ENR |
| `/agents/{agent_id}` | Endpoint | `api/routers/agents.py` | GET detail; owned by ENR |
| `delivery_status` | Enum-like | All layers | Values: "active", "stale", "no_report", "error" |

### No New Environment Variables

This feature does not introduce new env vars. The stale window is a constant; if runtime config is needed, that is a C-06 team decision.

### No New CLI Flags

This feature is UI-only; no scanner CLI changes.

### No New Database Columns or Tables

This feature reuses existing tables: `agents`, `enrollment_tokens`, `reports`, `scans`. No migrations required beyond what ENR already does.

---

## 10. Known Cross-Feature Risks

Pulled from the contract's Flagged Conflicts & Shared Resource Index:

### C-05: GET /agents Endpoint Conflict (ENR ↔ ASP)
**Status:** RESOLVED  
**Resolution:** ENR owns `api/routers/agents.py` and implements `GET /agents` endpoint. ASP consumes this endpoint read-only via the frontend API client. ASP does not create or modify the router.  
**Implementation Consequence:** ASP must wait for ENR to merge in Wave 2 before implementing the frontend page. The backend-side Step 3 (Section 8) is coordinated with ENR; Shreyanshi is the integration owner for `api/main.py` mount.

### C-06: Stale Agent Time Window (Open Sign-Off)
**Status:** AWAITING TEAM DECISION  
**What is blocked:** The exact number of days separating "active" from "stale" delivery status.  
**Current placeholder:** `STALE_AGENT_WINDOW_DAYS = 7` in `dashboard/src/lib/constants.js`.  
**Decision needed by:** Before Step 1 frontend PR merges.  
**If not resolved:** Use 7 days as a default; document as TBD in the code comment.  
**Who decides:** Team lead (Shashank or Shreyanshi).

### C-10: Organization Scoping for NULL organization_id (RBAC ↔ ASP ↔ others)
**Status:** AWAITING TEAM DECISION  
**What is blocked:** How to handle agents or scans with NULL `organization_id` when user is filtered to a specific org.  
**Current assumption:** RBAC feature (Shreyanshi's responsibility) implements the Principal/require_role logic. ASP assumes that by the time the backend endpoint is called, RBAC has already filtered the request to only show agents in principal.organization_id. NULL org_id rows are handled by RBAC, not ASP.  
**If not resolved:** Implement a fallback in `get_agents_for_org()` that treats NULL org_id as "visible to all orgs"; this is a security risk and should not happen without explicit team sign-off.  
**Implementation consequence:** ASP's backend CRUD assumes organization_id is never NULL for agents; if that assumption breaks, test coverage will reveal it immediately.

### C-13: FindingsTable Column Registry (DFS ↔ others)
**Status:** Compatible  
**Resolution:** ASP does not modify FindingsTable. ASP has its own AgentStatusTable. No conflict.

---

## 11. Pre-Answered Ambiguities

**Situation 1:** *"What if an agent is enrolled but the latest report has `signature_verified = FALSE`?"*  
**Answer:** Set `delivery_status = "error"`. The signature verification happened in the intake pipeline (`api/routers/report_sync.py`); ASP does not re-verify. The boolean column is the single source of truth. Display an AlertCircle icon and "Signature Error" status badge in red.

**Situation 2:** *"Should I poll the /agents endpoint even when the user is not on the /agents page?"*  
**Answer:** No. TanStack Query handles this automatically — the hook only refetches if the component is mounted. Once the user navigates away from AgentStatusPage, the hook unmounts and polling stops. This minimizes backend load.

**Situation 3:** *"What if the user's organization has 0 agents enrolled?"*  
**Answer:** Render the empty state: a centered message "No agents enrolled" with optional text "Create your first agent via the enrollment process." No error is raised; the page is valid even with 0 agents.

**Situation 4:** *"What if the GET /agents endpoint returns a 403 Forbidden?"*  
**Answer:** Render the permission-denied state: "You do not have access to agent data. Contact your administrator to grant analyst role." Do not retry the request. Log the error for debugging.

**Situation 5:** *"What if GET /agents returns HTTP 500 from the backend?"*  
**Answer:** Render the error state: "Failed to load agents. Please try again later." Include the error message in the browser console (not in the UI, for security). Log to Sentry or your error tracking service if configured.

**Situation 6:** *"Should the agent status page filter by organization_id in the frontend?"*  
**Answer:** No. The backend endpoint (GET /agents) is already filtered by RBAC. The frontend receives only agents the authenticated user can see. If you want client-side filtering by org, that is a UI enhancement for multi-org users; it is out of scope for the initial delivery.

**C-06 Sign-Off (Stale Window Threshold):**  
**Current placeholder:** 7 days.  
**Team decision needed:** Confirm 7 days, or specify an alternative (e.g., 1 day for aggressive monitoring, 30 days for infrequent scans). This must be resolved and committed to code before the frontend PR merges. If unresolved by Step 5 (Section 8), the code goes out with a TODO comment and 7-day default; tests can be written to verify the threshold logic regardless of the exact number.

**C-10 Sign-Off (NULL organization_id Visibility):**  
**Current assumption:** RBAC handles organization filtering at the route level. By the time the request reaches `get_agents_for_org()`, the caller has already provided a valid organization_id (either explicit or from principal.organization_id). ASP does not expect NULL org_id rows to pass through.  
**If RBAC is not yet ready:** The implementation will fail at test time when trying to filter agents by org. Coordinate with Shreyanshi to ensure RBAC is merged first (Wave 1).

---

## 12. Test Plan / Definition of Done

### Backend Tests

**CRUD layer (`tests/test_agents.py`):**
```bash
pytest tests/test_agents.py -v

# Expected output:
# test_create_agent_and_report ... PASSED
# test_get_agents_for_org_active ... PASSED
# test_get_agents_for_org_stale ... PASSED
# test_get_agents_for_org_no_report ... PASSED
# test_get_agents_for_org_signature_error ... PASSED
# test_get_agent_by_id_not_found ... PASSED
# 6 passed in 1.23s
```

**API Tests (`tests/test_api.py`):**
```bash
pytest tests/test_api.py::test_get_agents_unauthenticated -v
# Expected: 403 Forbidden

pytest tests/test_api.py::test_get_agents_analyst -v
# Expected: 200 OK, { agents: [...], total_count: N, organization_id: "..." }

pytest tests/test_api.py::test_get_agents_filter_org -v
# Expected: 200 OK, agents filtered to requested organization_id
```

**Integration Test (Optional):**
```bash
pytest tests/test_agents_integration.py -v
# Full flow: create agent → create report → query via endpoint → verify status
```

### Frontend Tests

**Component Tests (`dashboard/src/components/AgentStatusTable.test.jsx`):**
```bash
npm run test -- AgentStatusTable.test.jsx

# Expected:
# ✓ renders agents table with correct columns
# ✓ shows loading skeleton while data is pending
# ✓ shows empty state when no agents
# ✓ displays status badges with correct colors
# ✓ calls onRowClick callback when row is clicked
# 5 passed
```

**Hook Tests (`dashboard/src/hooks/useAgents.test.js`):**
```bash
npm run test -- useAgents.test.js

# Expected:
# ✓ fetches agents on mount
# ✓ refetches every 30 seconds
# ✓ returns error state on 403
# 3 passed
```

**Page Integration (`dashboard/src/pages/AgentStatusPage/index.test.jsx`):**
```bash
npm run test -- AgentStatusPage.test.jsx

# Expected:
# ✓ renders agent status table
# ✓ shows loading state initially
# ✓ shows error state on API failure
# ✓ shows empty state with no agents
# 4 passed
```

### E2E / Manual Walkthrough

**Happy Path (5 minutes):**
1. Open dashboard and log in as analyst.
2. Navigate to `/agents` (or click "Agents" menu item).
3. Table loads with enrolled agents (if any exist in test data).
4. Verify status badges render correctly (active=green, stale=yellow, error=red).
5. Wait 30 seconds and verify a second polling request is sent (check Network tab in DevTools).
6. Click a row and verify drill-in or detail view loads.

**Error Path:**
1. Simulate a 500 error on the backend: modify mock to return 500.
2. Reload the page and verify "Failed to load agents" message appears.
3. Verify no infinite retry loop (refetch should not fire continuously).

**Permission Path (if RBAC is ready):**
1. Log in as a user with no analyst role.
2. Navigate to `/agents`.
3. Verify 403 Forbidden message appears, not a blank page.

### Build & Linting

```bash
npm run build  # Vite build should succeed, no warnings
npm run lint   # ESLint should pass
pytest         # All Python tests pass
```

### Definition of Done Checklist

- [ ] All 13 files created/modified as per Section 5 (File Ownership).
- [ ] Backend models (Step 1) merged and tested.
- [ ] CRUD queries (Step 2) merged and tested.
- [ ] Endpoint (Step 3) merged and tested (coordinated with ENR).
- [ ] Frontend constants & API client (Step 5) merged and tested.
- [ ] Frontend hook (Step 6) merged and tested.
- [ ] Frontend components (Step 7) merged and tested.
- [ ] Frontend page & routing (Step 8) merged and tested.
- [ ] E2E tests (Step 9) pass.
- [ ] No console warnings or errors in the browser.
- [ ] `npm run build` produces no errors.
- [ ] `pytest` with `tests/test_agents.py` passes.
- [ ] Dashboard loads `/agents` page without 404.
- [ ] Agent table renders with mock data in dev mode.
- [ ] Polling fires every 30 seconds (verified in DevTools Network tab).
- [ ] Status badges display correct colors.
- [ ] Code follows existing patterns in the repository (no new linting exceptions).
- [ ] Commit message includes feature code: "ASP: <description>".
- [ ] PR description links to SYSTEM_INTERFACE_CONTRACT.md Section 1 for resolver C-05.
- [ ] If C-06 is unresolved, PR includes a TODO comment with the placeholder value.

---

## 13. Rollback Plan

If this feature breaks the build, deploy, or dashboard, roll back as follows:

### Scenario: Dashboard does not render after ASP merge

**Immediate action:**
1. Revert the last ASP PR (Step 8, `dashboard/src/App.jsx`).
2. Verify dashboard loads at `/` again.
3. Check browser console for import/syntax errors.

**Root cause investigation:**
- Syntax error in JSX: Check Step 7 or 8 files for missing semicolons, unclosed tags.
- Missing dependency: Run `npm install` and `npm run build` to verify all imports resolve.
- Routing conflict: Check App.jsx for duplicate route paths (verify no other feature added `/agents` before ASP).

**Remediation:**
- Fix syntax or dependency issue locally.
- Re-open PR with corrected code.
- Merge once tests pass.

### Scenario: Backend endpoint returns 500 or invalid data after ASP merge

**Immediate action:**
1. Revert the last backend PR (Step 3, `api/routers/agents.py`).
2. Revert CRUD queries (Step 2, `db/crud.py`) if the 500 originates there.
3. Check `pytest tests/test_agents.py` for failures.

**Root cause investigation:**
- Database schema mismatch: Verify `agents`, `enrollment_tokens`, and `reports` tables exist and have the expected columns.
- ORM query error: Check for AttributeError on Agent or Report models (e.g., accessing a non-existent field).
- RBAC integration: If endpoint returns 403, ensure RBAC Wave 1 merged first.

**Remediation:**
- Run migrations: `python -m alembic upgrade head` (if needed).
- Fix CRUD query or model import.
- Re-test with `pytest tests/test_agents.py`.
- Merge once passing.

### Scenario: Polling causes excessive backend load or 429 (rate limit)

**Immediate action:**
1. Reduce `AGENT_POLLING_INTERVAL_MS` from 30000 to 60000 (1 minute) in `dashboard/src/lib/constants.js`.
2. Verify no new 429 errors in browser console.

**Root cause investigation:**
- Too many concurrent clients polling: Check if frontend is in demo mode with many test instances.
- Backend rate limiting is too aggressive: Check `api/core/security.py` or rate limiter configuration.

**Remediation:**
- Increase polling interval (acceptable up to 5 minutes for demo).
- If production, implement request deduplication in the API (e.g., caching in TanStack Query with longer staleTime).

### Scenario: RBAC integration fails; /agents returns 403 for all users

**Immediate action:**
1. Verify RBAC Wave 1 has merged (confirm `api/core/security.py` and `require_role()` exist).
2. Check Principal model: Does it have `organization_id`?
3. Verify test user has `analyst` role assigned in the test database.

**Root cause investigation:**
- RBAC not yet merged: Wait for Wave 1 to complete; ASP is unblocked by RBAC in the merge order.
- Role assignment missing: Check `tests/conftest.py` or test fixtures; ensure test user has analyst role.
- Principal.organization_id is NULL: Check RBAC implementation (C-10 sign-off question).

**Remediation:**
- Coordinate with Shreyanshi (backend lead) to ensure RBAC and Principal are ready.
- Add test fixtures for analyst-scoped users.
- Re-test with `pytest tests/test_api.py::test_get_agents_analyst`.

### Scenario: Agent status values are always "error" or "stale"

**Immediate action:**
1. Check the test database: Do `agents`, `reports` tables have rows?
2. Verify `signature_verified` column is TRUE for test reports (set in the intake pipeline).
3. Check `STALE_AGENT_WINDOW_DAYS` constant: Is it too small?

**Root cause investigation:**
- Test data not seeded: Run `python db/seed.py` to populate test agents and reports.
- Signature verification not running: Check `api/routers/report_sync.py` is persisting reports correctly.
- Stale window threshold is wrong: Verify C-06 decision or adjust placeholder value.

**Remediation:**
- Seed test data: `python db/seed.py`.
- Re-run tests with `pytest tests/test_agents.py::test_get_agents_for_org_active`.
- If stale window is too strict, increase `STALE_AGENT_WINDOW_DAYS` temporarily for testing.

### Full Rollback (Last Resort)

```bash
# Revert all ASP PRs in reverse order (Steps 9 → 1)
git revert <commit-hash-step-9>
git revert <commit-hash-step-8>
git revert <commit-hash-step-7-pr2>
git revert <commit-hash-step-7-pr1>
git revert <commit-hash-step-6>
git revert <commit-hash-step-5>
git revert <commit-hash-step-4>
git revert <commit-hash-step-3>
git revert <commit-hash-step-2>
git revert <commit-hash-step-1>

# Rebuild and redeploy
docker-compose down
docker-compose build
docker-compose up -d

# Verify
curl http://localhost:8000/health
npm run build && npm run preview
```

After rollback, create a postmortem in Slack or GitHub Discussions documenting:
- What broke
- Root cause
- How to prevent it next time
- Owner for remediation

---

## Appendix: Deviations from Step 1 Proposal

The initial proposal (`agent-status-page.md`) contained these elements that are now scoped out or modified per the SYSTEM_INTERFACE_CONTRACT:

| Original Proposal | Contract Resolution | This Spec |
|---|---|---|
| "ASP creates `api/routers/agents.py`" | ENR owns the router (C-05); ASP consumes it | Section 5: ASP does not touch the router |
| "The page should start scans" | Out of scope (agent mutation) | Section 3: No control buttons, read-only only |
| "Real-time process heartbeat status" | No live heartbeat channel exists | Section 2: Evidence-based delivery status only |
| "Custom per-agent alert thresholds" | Out of scope (global config only) | Section 3: Stale window is global (C-06) |
| "Agent enrollment UI" | Owned by ENR feature | Section 3: Out of scope |
| "Bulk CSV export of agent roster" | Out of scope for initial delivery | Section 3: Out of scope |

---

**Specification prepared by:** [Author/Owner]  
**Date:** 2025-09-20  
**Status:** Ready for Wave 2 implementation (after RBAC Wave 1 merges)  
**Next step:** Team sign-off on C-06 (stale window days) before Step 5 frontend PR opens.
