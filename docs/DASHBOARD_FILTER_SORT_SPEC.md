# Dashboard Filter/Sort by Asset Type + Risk Tier — Feature Specification

## 1. Header

| Field | Value |
|---|---|
| **Feature name** | Dashboard Filter/Sort by Asset Type + Risk Tier (`DFS`) |
| **Feature code** | `DFS` (per `SYSTEM_INTERFACE_CONTRACT.md` §0) |
| **Owner** | Frontend lane — Satyam (co-owner with Karan, per `ARCHITECTURE.md` §5); backend-lane and DB-lane coordination required for `api/routers/findings.py`, `db/crud.py`, `db/schema.sql` per contract tiers below |
| **Spec version** | v1.0 |
| **Status** | **Draft — blocked on two human sign-offs** (see §11: C-13 sprint-scope capacity call, C-16 dropdown-sourcing/CMP-reuse call). Architecture and interfaces below may be implemented; do **not** merge the sprint-scope decision implied by shipping this feature until C-13 is signed off. |
| **Reviewer sign-off** | Frontend lane (Karan): ☐ &nbsp;&nbsp; Backend lane (Shreyanshi) — `api/routers/findings.py`, `api/core/params.py`: ☐ &nbsp;&nbsp; DB lane (Ronak) — `db/schema.sql`, `db/models.py`, `db/crud.py`, `db/migrations/008_query_indexes.sql`: ☐ |

### Changelog

| Version | Change |
|---|---|
| v1.0 | Initial spec. No separate Step‑1 initial-analysis proposal document for `DFS` was supplied alongside `SYSTEM_INTERFACE_CONTRACT.md`; this spec is derived directly from the contract's `DFS` entries (Ownership Map §1.2/§1.4, Reserved migration numbers §2.1, Merged diff §2.2, Naming Conventions §3, C‑07, C‑08, C‑11 (n/a), C‑13, C‑16, Shared Resource Index §5, Merge Order §6, Open Items §7) plus the actual repository state. Three deviations from what a naive "filter/sort" proposal might otherwise assume are recorded here per the task's instruction to note deviations rather than silently follow a superseded assumption: (1) `dashboard/src/components/FindingsTable.jsx` is currently **dead code** (not imported anywhere in `dashboard/src`) — this spec treats it as the canonical target component anyway, because the contract's Ownership Map and C‑13 designate it as such regardless of its current disuse; (2) the Shared Resource Index (§5.1) lists `dashboard/src/index.css`, `tailwind.config.js` as touched by `DFS` among others, but the Ownership Map (§1.4) marks those files **SOLE / FE**, and C‑07 explicitly prohibits any feature other than FE from editing them — this spec follows the Ownership Map and C‑07 and does **not** touch those files; (3) the contract states `DFS` "registers a route" in `App.jsx` (§1.4), but the live `DashboardPage/index.jsx` is a single-route, client-side-tab SPA (no nested routes today) — this spec adds a new top-level route (`/dashboard/findings`) and additionally rewires the existing "Findings" and "Live Scan" tabs to render the same shared component, since the contract does not describe how the new route should coexist with the existing tab shell and no proposal document was available to resolve it (see §11, item 5). |

---

## 2. Goal & Context

PS 26164's fifth stated requirement is **"Recommendation & reporting"** — ECDAT is graded on whether an analyst can actually use the findings it discovers, not just generate them (`PRODUCT_DESCRIPTION.md` §2: *"Recommendation & reporting | Suggests PQC/classical replacements per finding; dashboard + CI summary"*). The team's own rehearsed demo narrative already promises this: *"Findings flow into the dashboard in real time. We see 7 weak-by-default algorithms, 1 unverified confidence finding, and the breakdown by language. The risk tier column shows Critical for MD5..."* (`PRODUCT_DESCRIPTION.md` §6). Today that breakdown does not exist as a real capability — the dashboard's findings views (`FindingsTab`, `LiveScanTab` inside `DashboardPage/index.jsx`) only filter locally over an in-memory mock array, and the one component the contract designates for this job, `dashboard/src/components/FindingsTable.jsx`, is unused dead code with a single hard-coded severity dropdown. `DFS` closes this gap: it makes `GET /scans/{scan_id}/findings` support server-side filtering by risk tier, asset/primitive/algorithm/language, and sorting, and gives the dashboard one reusable, registry-driven findings table that can show a judge a real, live, narrowed-down view of "what matters first" in a scan — the exact moment `PRODUCT_DESCRIPTION.md` §6 is written around.

`DFS` is also load-bearing for five other in-flight features (C‑13): CNT, BIN, IAC, CONF, TRI and FE all need to add a column to the findings table, and per the contract's resolution they must do so by adding an entry to a shared column registry rather than editing `FindingsTable.jsx`'s JSX directly. Landing `DFS` first (Merge Order Wave 2) is what turns those five features' table changes from five merge conflicts into five additive registry entries.

---

## 3. Scope

### In-Scope

- Extend `GET /scans/{scan_id}/findings` to accept, in addition to the existing single-value `risk_tier`: repeatable `risk_tier`, `primitive`, `algorithm`, `language` filters (OR within a category, AND across categories, per C‑16), plus `sort_by` / `sort_dir`.
- Introduce the shared FastAPI dependency `api/core/params.py::common_list_params` that C‑16 assigns as the query-parsing mechanism for this parameter surface (not middleware).
- Extend `db/crud.py::get_findings_for_scan()` to accept the new filter/sort parameters, backward-compatible with every existing caller.
- Land `db/migrations/008_query_indexes.sql` (reserved for `DFS` + `TRD` jointly, per §2.1) with its mirrored `db/schema.sql` addition and `docker-compose.yml` initdb mount, per the binding convention in §2.
- Restructure `dashboard/src/components/FindingsTable.jsx` from its current dead, single-filter stub into the reusable, prop-driven, column-registry component the contract designates it as (C‑13), backed by live data via `useFindings`.
- Add the column registry and filter-option constants to `dashboard/src/lib/constants.js`.
- Add a dedicated `/dashboard/findings` route (`dashboard/src/pages/FindingsPage/index.jsx`), registered in `App.jsx` per §1.4.
- Rewire `DashboardPage/index.jsx`'s existing "Findings" and "Live Scan" tab content to render the same shared `FindingsTable` component instead of their private inline `<table>` markup, so there is exactly one findings-table implementation in the codebase.

### Out-of-Scope

- Confidence-band filtering/sorting — owned by `CONF`, added to the same coordinated `api/routers/findings.py` / `common_list_params` surface later, not by `DFS` (`api/routers/findings.py` note: *"CONF (band filter), DFS (filter/sort), TRI (merge triage into response)"*).
- Triage status columns, filters, or the `finding_triage` table — owned by `TRI`.
- Any change to how `risk_tier`, `primitive`, or `algorithm` values are *computed* (`api/services/risk_engine.py` is FROZEN; scanner engines are SOLE/COORDINATED to the scanner lane).
- New database columns of any kind — `DFS`'s migration is indexes only, per the reserved `008_query_indexes.sql` content in §2.2.
- Any edit to `dashboard/src/index.css` or `dashboard/tailwind.config.js` (SOLE / FE, C‑07) — no new colors, no new tokens, no inline styles beyond the existing `var(--token)` pattern already used throughout `DashboardPage/index.jsx`.
- Re-adding methods to, or importing, `dashboard/src/api.js` (marked for deletion, C‑08) — all API calls go through `dashboard/src/lib/api.js`.
- CBOM export, remediation panel, agent status, trends, and compliance views/routes — owned by other features.
- Authentication, RBAC, or `X-API-Key` behavior changes.
- Any new Python or npm dependency — the feature is implementable entirely with what is already in `requirements.txt` and `dashboard/package.json`.

---

## 4. Required Context Files

The implementer must read these, in full, before writing any code:

1. `SYSTEM_INTERFACE_CONTRACT.md` — §0 (feature codes), §1.2, §1.4 (Ownership Map), §2.1, §2.2 (reserved migration + merged diff), §3.1, §3.4, §3.7, §3.8 (naming conventions), C‑07, C‑08, C‑13, C‑16 (Flagged Conflicts), §5 (Shared Resource Index), §6 (Merge Order), §7 (Open Items)
2. `AGENT_RULES.md` — all 9 rules, in particular #2, #3, #4, #5, #9
3. `ARCHITECTURE.md` — §2.2 ("API → Database Contract"), §2.3 ("API Endpoint Surface")
4. `PRODUCT_DESCRIPTION.md` — §1–§2, §6 (demo narrative)
5. `db/schema.sql`
6. `db/models.py`
7. `db/crud.py`
8. `api/routers/findings.py`
9. `api/models.py`
10. `api/core/security.py` (for `get_api_key`)
11. `api/database.py` (for `get_session`)
12. `dashboard/src/components/FindingsTable.jsx`
13. `dashboard/src/lib/constants.js`
14. `dashboard/src/lib/api.js`
15. `dashboard/src/hooks/useFindings.js`
16. `dashboard/src/App.jsx`
17. `dashboard/src/pages/DashboardPage/index.jsx`
18. `dashboard/src/mockData.js`
19. `docker-compose.yml` (existing initdb mount block, lines mounting `db/schema.sql` and `db/migrations/001_secure_reporting.sql`)
20. `docs/DASHBOARD_IMPROVEMENT_REVIEW.md`
21. `tests/test_crud.py`, `tests/test_api.py`, `conftest.py`

---

## 5. File Ownership

### 5.1 Files this feature creates

| Path | Tier (per contract) | Note |
|---|---|---|
| `db/migrations/008_query_indexes.sql` | SOLE per file, allocated to **DFS + TRD** (§2.1) | `DFS` lands it first (Merge Order Wave 2); content already fully specifies both features' indexes (§2.2), so `TRD` needs no follow-up edit |
| `api/core/params.py` | **Not listed in the Ownership Map** — see note below | New shared FastAPI dependency module introduced by C‑16's resolution; `DFS` is its first consumer |
| `dashboard/src/pages/FindingsPage/index.jsx` | New, under COORDINATED `dashboard/src/App.jsx` route table (§1.4) | Dedicated route target |

> **Ownership-map gap, flagged per AGENT_RULES #2 rather than silently assumed:** `api/core/params.py` does not appear anywhere in §1 of the contract. C‑16 names the dependency (`api/core/params.py::common_list_params`) and states it will later be consumed by `CONF`, `CMP`, `TRD`, `TRI` — which makes it a COORDINATED file in substance — but no owner or tier is assigned. This spec treats it as **COORDINATED, backend lane**, created by `DFS` as first mover, on the same logic the contract already applies to `api/models.py` and `api/routers/findings.py`. This assignment is an implementer inference, not a contract citation, and should be confirmed with the backend lane before merge.

### 5.2 Files this feature modifies

| Path | Tier | What `DFS` changes |
|---|---|---|
| `db/schema.sql` | COORDINATED, DB lane (Ronak) | Mirror the `008_query_indexes.sql` content (idempotent `CREATE INDEX IF NOT EXISTS`), per §2 binding conventions |
| `db/crud.py` | COORDINATED, DB lane (Ronak) | Extend `get_findings_for_scan()` only — see §7 |
| `docker-compose.yml` | COORDINATED, deploy lane | Add one initdb mount line for `008_query_indexes.sql` → `09_query_indexes.sql`, nothing else |
| `api/routers/findings.py` | COORDINATED, backend lane | Add `primitive`, `algorithm`, `language`, `sort_by`, `sort_dir` via `common_list_params`; widen `risk_tier` to repeatable; extend `FindingsPageResponse` additively |
| `dashboard/src/lib/constants.js` | COORDINATED, frontend lane | Add `findingColumns` registry + filter-option constants; **do not** touch `mockFindings`/`mockScans`/`appRoutes` beyond what §11 item 4 specifies |
| `dashboard/src/hooks/useFindings.js` | Not in Ownership Map (frontend lane, by extension of `dashboard/src/lib/` conventions) | Document (JSDoc) the new `params` shape; no behavioral change — it already forwards `params` to `axios` |
| `dashboard/src/components/FindingsTable.jsx` | COORDINATED, frontend lane (Karan/Satyam), lands **first** per C‑13 | Full rewrite into the registry-driven component |
| `dashboard/src/App.jsx` | COORDINATED, frontend lane | Add one `<Route>` for `FindingsPage` |
| `dashboard/src/pages/DashboardPage/index.jsx` | COORDINATED, frontend lane (also touched by CONF, CMP) | Replace `FindingsTab`'s and `LiveScanTab`'s inline `<table>` blocks with `<FindingsTable />` |

### 5.3 Do-not-touch — every other feature's SOLE or FROZEN files

- **Scanner lane (all SOLE/FROZEN):** `scanner/dependency_engine.py`, `scanner/container_engine.py`, `scanner/image_layers.py`, `scanner/binary_engine.py`, `scanner/config_engine.py`, `scanner/confidence.py`, `scanner/enroll_cli.py`, `scanner/ecdat_cli.py`, `pyproject.toml`, `scanner/rules/container.yaml`, `scanner/rules/binary.yaml`, `scanner/rules/config.yaml`, `scanner/finding.py` (FROZEN), `scanner/cli.py`, `scanner/constants.py`, `scanner/python_engine.py`, `scanner/multilang_engine.py`, `scanner/__init__.py`, `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml`
- **API lane:** `api/routers/auth.py`, `api/core/rbac.py`, `api/routers/agents.py`, `api/services/enrollment.py`, `api/routers/audit.py`, `api/services/audit.py`, `api/routers/triage.py`, `api/routers/trends.py`, `api/routers/compliance.py`, `api/services/cbom_validator.py`, `api/services/scan_runner.py` (**FROZEN**), `api/services/cbom_generator.py` (COORDINATED, CBOM lane only), `api/services/risk_engine.py` (**FROZEN**), `api/core/security.py`, `api/core/config.py`, `api/main.py` (COORDINATED, backend lane, RBAC→ENR→AUD order — `DFS` is not in that sequence)
- **DB lane:** `db/seed.py` (touched only by CONF/RBAC), `db/migrations/002_confidence_scoring.sql`, `003_artifact_scanning.sql`, `004_rbac_users.sql`, `005_agent_enrollment.sql`, `006_audit_events.sql`, `007_finding_triage.sql` (each SOLE to its own feature per §2.1)
- **Frontend lane:** `dashboard/src/index.css`, `dashboard/tailwind.config.js`, `dashboard/public/fonts/` (**SOLE, FE**), `dashboard/src/components/ConfidenceStamp.jsx` (**SOLE, CONF**), `dashboard/src/components/AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `pages/AgentStatusPage/`, `hooks/useAgents.js` (**SOLE, ASP**), `dashboard/src/components/ComplianceReport.jsx` (**SOLE, CMP**), `dashboard/src/components/RiskTrendChart.jsx`, `RiskTierBreakdown.jsx`, `pages/TrendsPage/` (**SOLE, TRD**), `dashboard/src/context/AuthContext.jsx`, `pages/LoginPage/LoginForm.jsx` (**SOLE, RBAC**), `dashboard/src/pages/LandingPage/index.jsx` (**SOLE, frontend lane / sole GSAP consumer**), `dashboard/src/api.js` (**marked DELETE, frontend lane — do not resurrect or add to it**)
- **Ops/CI/docs:** `scripts/install.sh`, `install.ps1`, `.github/workflows/install-smoke.yml` (**SOLE, INS**), `requirements.txt` (COORDINATED, single backend-lane diff — `DFS` needs no new dependency and must not add one), `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md` §1/§6 (single scope editor only, C‑19), `docs/*_SCANNING_SCOPE.md`, `CONFIDENCE_MODEL_SPEC.md`, `COMPLIANCE_REPORT_SCOPE.md` (SOLE per owning feature)
- **Tests:** `tests/test_crud.py`, `test_realworld_source_scanner.py`, `test_scanner_battle.py`, `test_security_controls.py` — these are already flagged "Breaking!" for `CONF`/`RBAC` (C‑03, C‑09); `DFS` may **add** new test functions to `tests/test_crud.py`/`tests/test_api.py` for its own new parameters but must not alter or remove existing assertions in those files.

---

## 6. Tech Stack & Pinned Versions

No new dependency is required in either `requirements.txt` or `dashboard/package.json`.

| Layer | Library | Version (as already pinned) | Source |
|---|---|---|---|
| Backend runtime | Python | 3.11-slim | `ARCHITECTURE.md` §3 |
| Backend framework | FastAPI | `>=0.111.0` | `requirements.txt` |
| Validation | Pydantic | `>=2.7.0` (v2) | `requirements.txt` |
| ORM | SQLAlchemy | `>=2.0,<2.1` | `requirements.txt` |
| Test runner | pytest | `>=8.0` | `requirements.txt` |
| Frontend framework | React | `^18.3.1` | `dashboard/package.json` |
| Routing | react-router-dom | `^6.30.6` | `dashboard/package.json` (already present — contract §0.1 confirms "need adding" proposals were wrong) |
| Data fetching | @tanstack/react-query | `^5.102.4` | `dashboard/package.json` (already present; `useFindings.js` already uses it) |
| HTTP client | axios | `^1.19.0` | `dashboard/package.json`, via `dashboard/src/lib/api.js` |
| Motion | framer-motion | `^11.18.2` | `dashboard/package.json` (canonical per C‑17; `DFS` must not introduce `gsap` usage outside `LandingPage`) |
| Styling | Tailwind CSS | `^3.4.19` | `dashboard/tailwind.config.js` (existing tokens only, consumed as utility classes — no new tokens, C‑07) |
| Icons | lucide-react | `^0.428.0` | `dashboard/package.json` |

`cryptography` remains unpinned in `requirements.txt` (C‑18) — this is a Wave‑0 backend-lane fix, orthogonal to `DFS`, and is **not** to be pinned as part of this feature's diff (a `DFS` PR touching `requirements.txt` would violate the "single grouped diff" resolution in C‑18).

---

## 7. Concrete Interface Definitions

```sql
-- ============================================================================
-- db/migrations/008_query_indexes.sql  ·  owners: DFS, TRD
-- Verbatim per SYSTEM_INTERFACE_CONTRACT.md §2.2. No new columns.
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_findings_scan_tier   ON findings(scan_id, risk_tier);
CREATE INDEX IF NOT EXISTS idx_findings_scan_lang   ON findings(scan_id, language);
CREATE INDEX IF NOT EXISTS idx_scans_repo_started   ON scans(repo_id, started_at DESC);
```

```sql
-- db/schema.sql — mirrored addition, appended after the existing
-- "Day-4 indexes (owned by Ronak)" block, per §2 binding conventions
-- ("every change appears twice ... and stay idempotent and identical in effect").
CREATE INDEX IF NOT EXISTS idx_findings_scan_tier   ON findings(scan_id, risk_tier);
CREATE INDEX IF NOT EXISTS idx_findings_scan_lang   ON findings(scan_id, language);
CREATE INDEX IF NOT EXISTS idx_scans_repo_started   ON scans(repo_id, started_at DESC);
```

```yaml
# docker-compose.yml — one additional line in the `db` service's `volumes:`,
# matching the existing mount pattern and the §2.1 compose-mount prefix (09_):
      - ./db/migrations/008_query_indexes.sql:/docker-entrypoint-initdb.d/09_query_indexes.sql:ro
```

```python
# api/core/params.py  (new)
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query


@dataclass(frozen=True)
class FindingListParams:
    risk_tier: list[str] | None
    primitive: list[str] | None
    algorithm: list[str] | None
    language: list[str] | None
    sort_by: str | None
    sort_dir: str
    limit: int
    offset: int


def common_list_params(
    risk_tier: Annotated[list[str] | None, Query(
        description="Repeat for OR-within-category, e.g. ?risk_tier=CRITICAL&risk_tier=HIGH",
    )] = None,
    primitive: Annotated[list[str] | None, Query()] = None,
    algorithm: Annotated[list[str] | None, Query()] = None,
    language: Annotated[list[str] | None, Query()] = None,
    sort_by: Annotated[str | None, Query(
        pattern="^(risk_tier|algorithm|primitive|language|file|line)$",
    )] = None,
    sort_dir: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FindingListParams: ...
```

```python
# api/routers/findings.py — updated route signature and response model.
# Existing single-value `risk_tier: str | None` Query param is REPLACED by
# the shared dependency; existing behavior (single risk_tier) remains
# expressible as a one-element list.

class FindingsPageResponse(BaseModel):
    """Paginated GET /scans/{scan_id}/findings response."""
    scan_id: int
    findings: list[FindingOut]
    total_on_page: int
    offset: int
    limit: int
    risk_tier_filter: str | None = None          # UNCHANGED — first value of risk_tier, or None; kept for backward compatibility
    filters: dict[str, list[str] | None]          # NEW — {"risk_tier": [...], "primitive": [...], "algorithm": [...], "language": [...]}
    sort_by: str | None = None                    # NEW
    sort_dir: str = "asc"                         # NEW
    summary: RiskSummary


def list_findings(
    scan_id: int,
    db: Annotated[Session, Depends(get_session)],
    _key: Annotated[str, Depends(get_api_key)],
    params: Annotated[FindingListParams, Depends(common_list_params)],
) -> Any: ...
```

```python
# db/crud.py — get_findings_for_scan(), extended signature.
# `risk_tier` keeps accepting a bare str (every existing caller:
# api/services/cbom_generator.py, api/routers/scans.py, db/seed.py,
# tests/test_crud.py, tests/test_scan_runner.py) alongside the new list form.
# sort_by=None preserves the existing `.order_by(Finding.id)` behavior exactly.

def get_findings_for_scan(
    session: Session,
    scan_id: int,
    risk_tier: str | list[str] | None = None,
    primitive: str | list[str] | None = None,
    algorithm: str | list[str] | None = None,
    language: str | list[str] | None = None,
    sort_by: str | None = None,
    sort_dir: str = "asc",
    limit: int | None = None,
    offset: int = 0,
) -> list[Finding]: ...
```

```json
// Example: GET /scans/101/findings?risk_tier=CRITICAL&risk_tier=HIGH&language=python&language=java&sort_by=risk_tier&sort_dir=desc&limit=50&offset=0
// Headers: X-API-Key: <key>
{
  "scan_id": 101,
  "findings": [
    {
      "id": 42,
      "scan_id": 101,
      "file": "src/auth/legacy_login.py",
      "line": 17,
      "algorithm": "MD5",
      "key_size": null,
      "confidence": "high",
      "risk_tier": "CRITICAL",
      "risk_reason": "MD5 used for password verification; collision attacks cost under $100.",
      "criticality": "CRITICAL",
      "matched_call": "hashlib.md5(...)",
      "library": "hashlib",
      "primitive": "hash",
      "language": "python",
      "weak_by_default": true,
      "detection_method": "ast_visitor",
      "source_context": "SOURCE",
      "risk_assessment": null
    }
  ],
  "total_on_page": 1,
  "offset": 0,
  "limit": 50,
  "risk_tier_filter": "CRITICAL",
  "filters": {
    "risk_tier": ["CRITICAL", "HIGH"],
    "primitive": null,
    "algorithm": null,
    "language": ["python", "java"]
  },
  "sort_by": "risk_tier",
  "sort_dir": "desc",
  "summary": { "total": 1, "CRITICAL": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNSCORED": 0 }
}
```

```javascript
// dashboard/src/lib/constants.js — new exports (camelCase, matching the
// file's existing style: mockFindings, mockScans, riskColors, appRoutes).
// `line === 0` renders as an em dash, never `0`, per C-13's resolution
// ("a binary has no line number") — applied here even though DFS does not
// itself add binary findings, because the registry is the shared contract.

export const findingColumns = [
  { key: 'risk_tier',  header: 'Risk Tier',  sortable: true,  accessor: (f) => f.risk_tier },
  { key: 'algorithm',  header: 'Algorithm',  sortable: true,  accessor: (f) => f.algorithm },
  { key: 'file',       header: 'File',       sortable: true,  accessor: (f) => f.file },
  { key: 'line',       header: 'Line',       sortable: false, accessor: (f) => (f.line === 0 ? '—' : f.line) },
  { key: 'primitive',  header: 'Primitive',  sortable: true,  accessor: (f) => f.primitive ?? '—' },
  { key: 'language',   header: 'Language',   sortable: true,  accessor: (f) => f.language ?? '—' },
  { key: 'confidence', header: 'Confidence', sortable: false, accessor: (f) => f.confidence },
];

// Canonical per db/models.py RISK_TIERS. Display order is UI severity order,
// not the tuple's storage order — this is a presentation choice, not a
// value-set change.
export const riskTierOptions = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

// primitiveOptions / languageOptions intentionally NOT defined here —
// no canonical value tuple exists for these columns anywhere in the
// codebase today. See §11, item 2 (open, unresolved per C-16).
```

```jsx
// dashboard/src/hooks/useFindings.js — unchanged function signature;
// JSDoc documents the newly-supported `params` shape only.

/**
 * @param {number} scanId
 * @param {{
 *   risk_tier?: string[],
 *   primitive?: string[],
 *   algorithm?: string[],
 *   language?: string[],
 *   sort_by?: 'risk_tier'|'algorithm'|'primitive'|'language'|'file'|'line',
 *   sort_dir?: 'asc'|'desc',
 *   limit?: number,
 *   offset?: number,
 * }} [params]
 */
export function useFindings(scanId, params = {}) { /* unchanged body */ }
```

```jsx
// dashboard/src/components/FindingsTable.jsx — new exported interface.
/**
 * @param {number} scanId
 * @param {boolean} [embedded=false] - compact mode (no page chrome), for
 *   reuse inside DashboardPage's existing tab shell.
 */
export default function FindingsTable({ scanId, embedded = false }) { /* see §8 */ }
```

```jsx
// dashboard/src/pages/FindingsPage/index.jsx — new page.
export default function FindingsPage() { /* see §8 */ }
```

```jsx
// dashboard/src/App.jsx — one added lazy import, one added <Route>.
const FindingsPage = lazy(() => import('./pages/FindingsPage/index.jsx'));
// ...
<Route path="/dashboard/findings" element={<ProtectedRoute><FindingsPage /></ProtectedRoute>} />
```

---

## 8. Step-by-Step Implementation Plan

1. **`db/migrations/008_query_indexes.sql`** — create the file with the exact three `CREATE INDEX IF NOT EXISTS` statements from §7. No other content.
2. **`db/schema.sql`** — append the identical three statements immediately after the existing `"Day-4 indexes (owned by Ronak)"` block, so a fresh volume and an upgraded volume converge on the same index set.
3. **`docker-compose.yml`** — add the one mount line from §7 to the `db` service's `volumes:` list, immediately after the existing `001_secure_reporting.sql` mount line.
4. **`db/crud.py`** — extend `get_findings_for_scan()` to the signature in §7: normalize each of `risk_tier`/`primitive`/`algorithm`/`language` (str-or-list-or-None) into a list internally; apply each as `Finding.<col>.in_(values)` when non-empty (AND across the four categories, OR within each list); apply `sort_by`/`sort_dir` as `getattr(Finding, sort_by)` with `.asc()`/`.desc()` when `sort_by` is not `None`, else keep the existing `.order_by(Finding.id)` untouched. Do not change any other function in the file.
5. **`api/core/params.py`** — create the file with `FindingListParams` and `common_list_params()` exactly as in §7.
6. **`api/routers/findings.py`** — replace the current `risk_tier: str | None = Query(...)` parameter on `list_findings` with `params: Annotated[FindingListParams, Depends(common_list_params)]`; pass `params.risk_tier`, `params.primitive`, `params.algorithm`, `params.language`, `params.sort_by`, `params.sort_dir`, `params.limit`, `params.offset` through to `crud.get_findings_for_scan(...)`; validate `risk_tier` values against `db.models.RISK_TIERS` inside the route (400/422 on an unrecognized tier) since no such validation currently exists at the dependency level; extend `FindingsPageResponse` and the returned dict exactly as in §7 (additive fields only — do not remove `risk_tier_filter`).
7. **`dashboard/src/lib/constants.js`** — add `findingColumns` and `riskTierOptions` exactly as in §7. While in this file, correct the existing `riskColors` object's CSS variable references (`var(--risk-critical)` etc.) to the tokens that actually exist in `dashboard/src/index.css` (`var(--critical)`, `var(--high)`, `var(--medium)`, `var(--low)`) — see §11, item 4. Do not touch `mockFindings`, `mockScans`, `mockCbom`, `appRoutes`.
8. **`dashboard/src/hooks/useFindings.js`** — add the JSDoc block from §7 above the existing `useFindings` function. No functional change.
9. **`dashboard/src/components/FindingsTable.jsx`** — rewrite as the component described in §7: accepts `scanId`/`embedded`; renders filter controls (risk-tier multi-select from `riskTierOptions`, plus free-text search over `file`/`algorithm` client-side within the current page, matching the existing `FindingsTab` search UX) and a sortable `<table className="data-table">` built by mapping `findingColumns`; fetches via `useFindings(scanId, { ...selectedFilters, sort_by, sort_dir })`; clicking a sortable column header toggles `sort_by`/`sort_dir` state; uses only existing Tailwind utility classes and `var(--token)` references already present elsewhere in the dashboard (no new CSS).
10. **`dashboard/src/pages/FindingsPage/index.jsx`** — new page rendering page chrome (heading, back-to-dashboard link) plus `<FindingsTable scanId={latestScanId} />`, where `latestScanId` comes from the same `GET /scans?limit=1` pattern already used by `LiveScanTab` in `DashboardPage/index.jsx`.
11. **`dashboard/src/App.jsx`** — add the lazy import and `<Route>` from §7, placed alongside the existing `DashboardPage` route inside the authenticated route group.
12. **`dashboard/src/pages/DashboardPage/index.jsx`** — inside `FindingsTab`, replace the local `<table className="data-table">` block with `<FindingsTable scanId={currentScanId} embedded />` (reusing whatever scan-id source `FindingsTab` already has, or the same `GET /scans?limit=1` lookup used in `LiveScanTab` if none exists); inside `LiveScanTab`, replace its `<table className="data-table">` block the same way; remove the now-dead local table markup and the now-unused `TIER_ORDER`/`mapLiveFinding` sort-only logic that duplicates what `FindingsTable` now does server-side (keep `mapLiveFinding`'s field-mapping role only if `FindingsTable` is not wired to consume raw `FindingOut` shapes directly — resolve in code review, not by guessing silently).

---

## 9. Naming & Symbol Registry

| Symbol | Kind | Location | Convention check |
|---|---|---|---|
| `api/core/params.py` | new module | backend | `snake_case` module path — matches §3.1 |
| `FindingListParams` | new dataclass | `api/core/params.py` | `PascalCase` class — matches §3.1; no collision found (`grep -rn "FindingListParams"` → none) |
| `common_list_params` | new function | `api/core/params.py` | `snake_case`, exact name from C‑16's own resolution text — no collision found |
| `risk_tier`, `primitive`, `algorithm`, `language`, `sort_by`, `sort_dir`, `limit`, `offset` | new/extended function parameters | `api/core/params.py`, `db/crud.py`, `api/routers/findings.py` | `snake_case` — matches §3.1; `sort_by`/`sort_dir` match the exact param names C‑16 lists for `DFS` |
| `idx_findings_scan_tier`, `idx_findings_scan_lang`, `idx_scans_repo_started` | index names (already reserved by the contract, not invented here) | `db/migrations/008_query_indexes.sql`, `db/schema.sql` | `idx_<table>_<cols>` — matches §3.8 |
| `filters`, `sort_by`, `sort_dir` (response fields) | new Pydantic model fields | `api/routers/findings.py::FindingsPageResponse` | additive only; `risk_tier_filter` retained unchanged |
| `findingColumns`, `riskTierOptions` | new JS constants | `dashboard/src/lib/constants.js` | camelCase — matches the file's existing style (`riskColors`, `mockScans`), not the UPPER_SNAKE_CASE convention §3.1 reserves for **Python**; no JS constant-naming rule is stated in §3.7 beyond component/page/hook naming, so existing file style governs |
| `FindingsTable` | existing component name, retained | `dashboard/src/components/FindingsTable.jsx` | `PascalCase.jsx` in `components/` — matches §3.7; no rename (AGENT_RULES #3) |
| `FindingsPage` | new page | `dashboard/src/pages/FindingsPage/index.jsx` | `pages/<Name>Page/index.jsx` — matches §3.7; no collision with `AgentStatusPage`/`TrendsPage` (reserved to ASP/TRD) or any existing page |
| `useFindings` | existing hook, unchanged | `dashboard/src/hooks/useFindings.js` | `use<Thing>.js` — matches §3.7; no new hook created |
| No new DB columns | — | — | Migration 008 is indexes-only per §2.2 |
| No new CLI flags | — | — | `DFS` does not touch `scanner/cli.py` |
| No new environment variables | — | — | §3.3's reserved-prefix table (`AUTH_`, `AGENT_ENROLLMENT_`, `SCAN_`, `AUDIT_`, `VITE_`) has no `DFS`-relevant entry, and none is needed |
| `HTTP` route surface | unchanged | `GET /scans/{scan_id}/findings` | No new route added; existing route's query-parameter surface is widened only, per §3.4 (resource stays nested under `/scans/{scan_id}`) |

---

## 10. Known Cross-Feature Risks

Pulled directly from the contract's Flagged Conflicts and Shared Resource Index wherever `DFS` is named:

| Ref | Shared resource | Risk | Contract's resolution (already decided — do not re-litigate) |
|---|---|---|---|
| C‑13 | `dashboard/src/components/FindingsTable.jsx`, `dashboard/src/lib/constants.js` | 7 features (`CNT`, `BIN`, `IAC`, `CONF`, `DFS`, `TRI`, `FE`) all need to change the findings table | `DFS` lands the column/filter architecture first; `FE` lands presentation second; every other feature then adds a column definition to the shared registry (`findingColumns` in `constants.js`) instead of editing `FindingsTable.jsx`'s JSX. `line=0` always renders as `—`. |
| C‑16 | `api/routers/findings.py` query parameters | `DFS`, `CONF`, `CMP`, `TRD`, `TRI` all extend the same parameter surface independently | A single shared FastAPI dependency, `api/core/params.py::common_list_params`, injected via `Depends()` — not middleware. Multi-value filters are OR within a category, AND across categories. |
| C‑08 | `dashboard/src/lib/api.js` + `dashboard/src/api.js` | `DFS` is listed among features that add API-client methods | `dashboard/src/lib/api.js` is canonical; `dashboard/src/api.js` is marked DELETE. `DFS` adds no new client file and no method to the orphaned one. |
| C‑07 | `dashboard/src/index.css`, `dashboard/tailwind.config.js` | `DFS` is listed as a proposal touching these files | FE owns the token layer exclusively; all views (including `DFS`'s new table/filters) consume tokens only as existing Tailwind classes — no local hex values, no inline `style={{color:…}}`, no new token namespace. |
| §5.2 | `findings` (indexes) | `DFS` and `TRD` both need new indexes | Marked **Compatible** — §2.2's migration 008 already contains both features' indexes in one file; `DFS` lands it and `TRD` needs no further edit. |
| §5.1 | `dashboard/src/pages/DashboardPage/index.jsx` | `CONF`, `CMP`, `DFS` all edit this file | Marked **Conflicting** per C‑13 — `DFS`'s edit (rewiring `FindingsTab`/`LiveScanTab` to the shared component) must land before `CONF`/`CMP` add their own tab content, per Merge Order Wave 2. |
| §5.1 | `dashboard/src/lib/constants.js` | `CNT`, `CONF`, `DFS` all edit this file | Marked **Conflicting** per C‑13 — resolved the same way: `DFS` creates the registry shape, later features append entries to `findingColumns` rather than restructuring the file. |
| §5.1 | `dashboard/src/App.jsx` | `ASP`, `TRD`, `DFS`, `FE` all edit this file | Marked **Compatible** — each feature adds one additive `<Route>`; no ordering constraint beyond normal merge hygiene. |

---

## 11. Pre-Answered Ambiguities

1. **If a caller requests `sort_by=confidence` or any value outside `risk_tier|algorithm|primitive|language|file|line`** → the `Query(pattern=...)` on `common_list_params` rejects it with FastAPI's standard `422 Unprocessable Entity` before the request reaches the router body. Do not add `confidence` to the allowed set — that dimension belongs to `CONF` (see §3, Out-of-Scope).
2. **[Open — from C‑16, verbatim, unresolved]** *"whether filter dropdowns are populated from canonical enums or from distinct values in the current scan (DFS raised both and answered neither)."* This spec does **not** invent an answer: `dashboard/src/lib/constants.js` defines `riskTierOptions` (a real canonical tuple exists: `RISK_TIERS` in `db/models.py`) but deliberately omits `primitiveOptions`/`languageOptions`/`algorithmOptions`, because **no canonical value tuple for those three columns exists anywhere in the codebase** — `db/models.py` only defines `SCAN_STATUSES`, `RISK_TIERS`, `CRITICALITIES`, `CONFIDENCES`. Until a human decides whether to (a) add canonical tuples to `db/models.py` for `primitive`/`algorithm`/`language`, or (b) populate those dropdowns from `GET /scans/{scan_id}` distinct values, the implementer should render the `algorithm`/`primitive`/`language` filters as free-text inputs (client-side substring match against the current page, exactly like the existing `FindingsTab` search box) rather than dropdowns, and must not fabricate an enum.
3. **[Open — from C‑13, verbatim, unresolved]** *"whether DFS's restructure is in scope for its sprint, since it is now a prerequisite for five other features. Frontend lane (Karan/Satyam) capacity call."* This spec assumes the answer is yes (that is the premise of writing it), but the actual capacity decision has not been made in any document available to this spec and is not re-opened or guessed here — it is the frontend lane's call, and this document's Status field reflects that it is still pending.
4. **If the implementer notices `riskColors` in `dashboard/src/lib/constants.js` references CSS variables that do not exist** (`var(--risk-critical)`, `var(--risk-high)`, etc., versus the tokens actually defined in `dashboard/src/index.css`: `--critical`, `--high`, `--medium`, `--low`) → fix the four variable names in place to point at the existing tokens. This is not a new sign-off item: C‑07 already settles that no new token names may be introduced, and the fix substitutes existing tokens for non-existent ones rather than adding anything — do not create `--risk-*` entries in `index.css` to make the old names "work," since that file is SOLE/FE.
5. **If it is unclear how the new `/dashboard/findings` route should coexist with `DashboardPage`'s existing tab-based "Findings" and "Live Scan" nav items** (this is not settled by the contract — see changelog item 3) → keep both: the sidebar's "Findings" and "Live Scan" `NAV` items continue to switch local `activeTab` state and render `<FindingsTable scanId={...} embedded />` in place, so the existing demo walkthrough and judge-facing tab flow is undisturbed; the new `/dashboard/findings` route is an additional, directly-linkable, full-page entry point to the same component (useful for `TRD`/`CMP`/deep-linking later), not a replacement for the tabs.
6. **If `db/crud.py::get_findings_for_scan()` receives a filter list containing an empty list `[]`** (as opposed to `None`) for `primitive`/`algorithm`/`language` → treat `[]` identically to `None` (no filter applied on that column), never as "match nothing." `FastAPI`'s `Query(list[str] | None)` returns `None` when the parameter is absent at all, so an explicit empty list should only arise from a bug elsewhere in the call chain — guard for it defensively rather than let it silently produce zero rows.
7. **If a `sort_by` column contains `NULL` values for some rows** (e.g. `primitive`/`language` are nullable, `risk_tier` is nullable for pre-model legacy rows) → use the database's default `NULL`-ordering behavior (Postgres: `NULLS LAST` for `ASC`, `NULLS FIRST` for `DESC`, which is already the implicit default and requires no extra SQL) rather than coercing nulls to a sentinel value; do not special-case this in `db/crud.py`.
8. **If an existing caller of `get_findings_for_scan()` (e.g. `api/services/cbom_generator.py`, which calls it with no filters at all) is affected by this change** → it is not: every new parameter defaults to `None`/`"asc"`/unchanged, and `sort_by=None` preserves the exact pre-existing `.order_by(Finding.id)` clause, so `cbom_generator.py`, `api/routers/scans.py`, `db/seed.py`, and all existing tests continue to receive identical row sets in identical order without modification.

---

## 12. Test Plan / Definition of Done

Run from the repository root (`ECDAT-main/`), matching the existing CI invocation style in `.github/workflows/*.yml` (`pytest -q --disable-warnings`):

```bash
# 1. Full backward-compatibility regression — must be unaffected by this feature.
python -m pytest tests/ -q --disable-warnings --maxfail=1
# Expected: identical pass/fail counts to the pre-DFS baseline; in particular
# tests/test_crud.py::test_full_scan_lifecycle and tests/test_scan_runner.py
# must still pass unchanged (they call get_findings_for_scan() with the old,
# single-string risk_tier form and no new kwargs).

# 2. New DFS-specific backend tests (add as new functions in tests/test_crud.py
#    and/or a new tests/test_findings_filter_sort.py — do not edit existing
#    functions in test_crud.py, per §5.3):
python -m pytest tests/test_crud.py -k "filter or sort" -v
# Expected new assertions, at minimum:
#   - get_findings_for_scan(session, scan_id, risk_tier=["CRITICAL","HIGH"])
#     returns only CRITICAL/HIGH rows (OR within category).
#   - get_findings_for_scan(session, scan_id, risk_tier=["CRITICAL"], language=["python"])
#     returns only rows matching BOTH (AND across categories).
#   - get_findings_for_scan(session, scan_id, sort_by="algorithm", sort_dir="desc")
#     returns rows in descending algorithm order.
#   - get_findings_for_scan(session, scan_id) with no new kwargs returns the
#     same list, same order, as before this change (regression guard for item 8, §11).

# 3. API-level tests (extend tests/test_api.py):
python -m pytest tests/test_api.py -k "findings" -v
# Expected:
#   - GET /scans/{id}/findings?risk_tier=CRITICAL&risk_tier=HIGH returns 200
#     with `filters.risk_tier == ["CRITICAL","HIGH"]` in the response body.
#   - GET /scans/{id}/findings?sort_by=notacolumn returns 422.
#   - GET /scans/{id}/findings?sort_dir=sideways returns 422.
#   - GET /scans/{id}/findings with no query params returns 200 with
#     `risk_tier_filter: null`, `filters: {"risk_tier": null, "primitive": null,
#     "algorithm": null, "language": null}`, `sort_by: null`, `sort_dir: "asc"`.

# 4. Frontend build — no JS test runner exists in this repo today
#    (dashboard/package.json has no test script); the build itself is the
#    available automated check:
cd dashboard && npm run build
# Expected: vite build completes with exit code 0, no new console errors.

# 5. Manual smoke check (no automated UI test framework is configured):
#    - Load /dashboard, click "Findings" and "Live Scan" tabs: table renders
#      via the shared FindingsTable component, filters/sort controls work
#      against real API data (or the existing mock fallback path unchanged).
#    - Navigate directly to /dashboard/findings: same table renders standalone.
#    - Confirm no findings row ever displays a literal "0" in the Line column.
```

**Definition of Done:** all of (1)–(3) pass with the expected outcomes above; (4) exits 0; (5) is manually verified and screenshotted for the team's demo-prep record (per `DEMONSTRATION_GUIDE.md` convention); no file outside §5.1/§5.2 has been modified; §11 item 3's sign-off has been explicitly obtained (not just assumed) before this feature is merged past a feature branch.

---

## 13. Rollback Plan

- **Backend:** `api/core/params.py` is a new, self-contained file — deleting it and reverting `api/routers/findings.py`'s `list_findings` signature to its pre-`DFS` form (single `risk_tier: str | None = Query(...)`) fully reverses the API-surface change. `db/crud.py`'s new parameters all default to values that reproduce the exact prior query, so reverting the router alone is sufficient to restore prior behavior even before the `crud.py` diff is reverted; revert both in the same rollback commit for cleanliness.
- **Database:** `008_query_indexes.sql` and its `db/schema.sql` mirror are additive, `IF NOT EXISTS` indexes only — they carry no data-loss risk. Rollback is `DROP INDEX IF EXISTS idx_findings_scan_tier, idx_findings_scan_lang, idx_scans_repo_started;` on any environment where they were applied, plus removing the three lines from `db/schema.sql` and deleting the migration file and its `docker-compose.yml` mount line. Because migration numbers are reserved (§2.1), do **not** reuse `008` for anything else even after rollback — a future re-attempt at this feature gets a newly-negotiated number.
- **Frontend:** `dashboard/src/components/FindingsTable.jsx` was dead code before this feature; if the rewrite must be reverted, restoring the pre-`DFS` file (the two-field `useState('All')` mock-only stub) is a clean revert since nothing else imports it except the newly-added `FindingsPage` and the newly-rewired `FindingsTab`/`LiveScanTab`. Revert `dashboard/src/App.jsx`'s added `<Route>` and lazy import, delete `dashboard/src/pages/FindingsPage/`, and restore `DashboardPage/index.jsx`'s `FindingsTab`/`LiveScanTab` inline `<table>` blocks from version control in the same commit — the three are only safe to revert together, since reverting `FindingsTable.jsx` alone while `DashboardPage` still imports it would break the build.
- **If the build breaks mid-integration** (e.g. `FindingsTable.jsx` is rewritten but `DashboardPage/index.jsx` has not yet been updated to consume it, or vice versa): treat steps 9 and 12 of §8 as one atomic unit for merge purposes — do not merge one without the other, since each half individually leaves either a broken import or an unused new component with no visible effect, and CI's `npm run build` step is the fast signal that this has happened.
