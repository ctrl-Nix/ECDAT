# Compliance Report View — Implementation Specification

## 1. Header — feature name, owner, spec version + changelog, status, reviewer sign-off

- **Feature:** Compliance Report View (`CMP`)
- **Owner:** `CMP`
- **Spec version:** `1.0`
- **Status:** Implementation-ready only after the contract's applicable human sign-offs are resolved.
- **Reviewer sign-off:** Pending; the contract explicitly lists unresolved CMP-affecting sign-offs and states: “Nothing below is decided. Each blocks the listed features.”
- **Changelog:** v1.0 supersedes Step 1 by following the contract's conditional API ownership: `api/routers/compliance.py` is created **only if** `GET /scans/{scan_id}` proves insufficient; no CMP database migration or compliance table is introduced; `api/services/risk_engine.py` remains read-only; `PRODUCT_DESCRIPTION.md` is not edited by the feature PR. The Step 1 proposal's “no new compliance table initially” and read-only aggregation approach is retained. The Step 1 proposal's assumption of a dedicated compliance endpoint is conditionalized by the contract.

## 2. Goal & Context — one paragraph, tied to a specific PS 26164 requirement or judge criterion

Implement a live, scan-specific compliance/readiness report in the React dashboard using persisted `findings` and `risk_assessments` evidence, directly supporting PS 26164 Requirement **5. Recommendation & Reporting**, which ECDAT maps to “dashboard + CI summary”; the product description also states that ECDAT “Generates concrete migration advice (PQC & classical alternatives)” and provides an interactive dashboard. The report is an evidence/readiness view, not a formal legal certification, and must not create a second risk-scoring implementation. fileciteturn1file2L29-L35

## 3. Scope — explicit In-Scope / Out-of-Scope bullets

**In-Scope**
- Replace the dashboard's mock/hard-coded Reports view with live data from `GET /scans/{scan_id}`.
- Render scan identity/status, total findings, risk-tier counts, classical-broken count, quantum-vulnerable count, confidence distribution, affected-file evidence, remediation/replacement evidence, and risk-model version evidence.
- Use persisted `risk_tier`, `criticality`, and `risk_assessments` rows only; no risk recomputation.
- Create `dashboard/src/components/ComplianceReport.jsx` as the CMP-owned component.
- Integrate the component through the existing coordinated frontend files.
- Keep API access exclusively through `dashboard/src/lib/api.js`.
- Use existing Tailwind tokens/classes; no new CMP colour namespace.

**Out-of-Scope**
- New compliance database tables or columns.
- New risk formulas, risk curves, or modifications to `api/services/risk_engine.py`.
- Formal NIST/DPDP certification claims or a universal compliance percentage without a contract-defined control matrix.
- PDF/CSV report generation as a new backend source of truth.
- Changes to scanner detection logic.
- Changes to `dashboard/src/components/FindingsTable.jsx`; CMP uses the post-DFS column architecture rather than editing the table JSX.
- Editing `PRODUCT_DESCRIPTION.md` inside the CMP feature PR.
- A new API route unless `GET /scans/{scan_id}` is proven insufficient.

## 4. Required Context Files — exact existing repo paths the implementer must read first

The implementer must read these files before writing code:

- `AGENT_RULES.md`
- `ARCHITECTURE.md`
- `PRODUCT_DESCRIPTION.md`
- `db/schema.sql`
- `db/models.py`
- `db/crud.py`
- `api/models.py`
- `api/routers/scans.py`
- `api/services/risk_engine.py`
- `dashboard/src/pages/DashboardPage/index.jsx`
- `dashboard/src/lib/api.js`
- `dashboard/src/index.css`
- `dashboard/tailwind.config.js`
- `dashboard/package.json`
- `requirements.txt`
- `SYSTEM_INTERFACE_CONTRACT.md`

The contract's ownership map explicitly defines `dashboard/src/components/ComplianceReport.jsx` as “SOLE | CMP”, `dashboard/src/lib/api.js` as “COORDINATED”, and `dashboard/src/pages/DashboardPage/index.jsx`, `lib/constants.js`, `mockData.js` as “COORDINATED”.

## 5. File Ownership — files this feature creates or modifies, matching the ownership tier (SOLE / COORDINATED / FROZEN) the contract assigned it; an explicit "do not touch" list for every other feature's SOLE or FROZEN files

**Create — CMP SOLE**
- `dashboard/src/components/ComplianceReport.jsx`

**Modify — COORDINATED, through the frontend integration owner**
- `dashboard/src/pages/DashboardPage/index.jsx`
- `dashboard/src/lib/api.js`
- `dashboard/src/lib/constants.js`
- `dashboard/src/pages/DashboardPage/index.jsx`

**Do not modify CMP-owned conditional backend file unless the stated condition is met**
- `api/routers/compliance.py` — contract: “new, **only if** `GET /scans/{scan_id}` proves insufficient”. Current Step 1 analysis and repository contract indicate the existing response is sufficient, so do not create it for v1.

**Do not touch these other-feature SOLE/FROZEN files**
- `scanner/dependency_engine.py`, `scanner/dependency_rules/`
- `scanner/container_engine.py`, `scanner/image_layers.py`
- `scanner/binary_engine.py`
- `scanner/config_engine.py`
- `scanner/confidence.py`
- `scanner/enroll_cli.py`
- `scanner/ecdat_cli.py`, `pyproject.toml`
- `scanner/rules/container.yaml`
- `scanner/rules/binary.yaml`
- `scanner/rules/config.yaml`
- `scanner/finding.py`
- `api/routers/auth.py`, `api/core/rbac.py`
- `api/routers/agents.py`
- `api/services/enrollment.py`
- `api/routers/audit.py`, `api/services/audit.py`
- `api/routers/triage.py`
- `api/routers/trends.py`
- `api/services/cbom_validator.py`
- `api/services/scan_runner.py`
- `api/services/risk_engine.py`
- `dashboard/src/index.css`, `tailwind.config.js`, `dashboard/public/fonts/`
- `dashboard/src/components/ConfidenceStamp.jsx`
- `dashboard/src/components/AgentStatusTable.jsx`, `dashboard/src/components/AgentStatusCard.jsx`, `dashboard/src/pages/AgentStatusPage/`, `dashboard/src/hooks/useAgents.js`
- `dashboard/src/components/RiskTrendChart.jsx`, `dashboard/src/components/RiskTierBreakdown.jsx`, `dashboard/src/pages/TrendsPage/`
- `dashboard/src/context/AuthContext.jsx`, `dashboard/src/pages/LoginPage/LoginForm.jsx`
- `dashboard/src/pages/LandingPage/index.jsx`
- `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml`

**Frozen/controlled shared resources not owned by CMP**
- `scanner/finding.py` is FROZEN.
- `api/services/scan_runner.py` is FROZEN.
- `api/services/risk_engine.py` is FROZEN.

The contract's merge position is exact: **“| **4** | TRI · CMP · TRD | — |”**. CMP presentation also waits for Wave 3 FE: **“| **3** | FE (tokens, self-hosted fonts, motion) | CMP, TRD presentation (C-07, C-25) |”**.

## 6. Tech Stack & Pinned Versions — exact libraries and version numbers, checked against requirements.txt / package.json so nothing already pinned is silently changed

- Python runtime: **3.11**.
- React: `^18.3.1`.
- React DOM: `^18.3.1`.
- Vite: `^5.4.1`.
- Tailwind CSS: `^3.4.19`.
- Recharts: `^2.15.4`.
- Axios: `^1.19.0`.
- `@tanstack/react-query`: `^5.102.4`.
- `lucide-react`: `^0.428.0`.
- `clsx`: `^2.1.1`.
- `tailwind-merge`: `^2.6.1`.
- No new dependency is required for CMP v1.
- Do not change `requirements.txt` or `dashboard/package.json` dependency versions in the CMP PR.

## 7. Concrete Interface Definitions — literal function/class signatures, literal SQL matching the contract's migration numbering, literal example API JSON. No prose description of behavior — only the interface itself

```jsx
function ComplianceReport({ scan, summary, findings })

function buildComplianceEvidence(findings, summary)
```

```python
# Existing contract/API interface consumed by CMP:
GET /scans/{scan_id}

# Existing response model:
class ScanWithFindings(BaseModel):
    scan: ScanOut
    findings: list[FindingOut] = []
    summary: RiskSummary | None = None
```

```json
{
  "scan": {
    "id": 42,
    "repo_id": 7,
    "started_at": "2026-09-20T15:30:00",
    "status": "completed"
  },
  "findings": [
    {
      "id": 101,
      "scan_id": 42,
      "file": "src/auth.py",
      "line": 18,
      "algorithm": "RSA",
      "key_size": 1024,
      "confidence": "high",
      "risk_tier": "CRITICAL",
      "risk_reason": "RSA-1024",
      "criticality": "CRITICAL",
      "matched_call": "rsa.generate_private_key",
      "library": "cryptography",
      "primitive": "asymmetric-encryption",
      "language": "python",
      "weak_by_default": true,
      "detection_method": "ast_visitor",
      "source_context": "SOURCE",
      "risk_assessment": {
        "risk_model_version": "1.0",
        "classical_broken": false,
        "quantum_vulnerable": true,
        "hndl_exposure": "HIGH",
        "recommended_replacement": "ML-KEM-768",
        "recommendation_type": "PQC",
        "migration_effort_days": 5,
        "data_shelf_life_years": 10.0,
        "quantum_threat_horizon_years": 15.0,
        "assumption_source": "deterministic-risk-engine",
        "assessed_at": "2026-09-20T15:30:01"
      }
    }
  ],
  "summary": {
    "total": 1,
    "CRITICAL": 1,
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0,
    "UNSCORED": 0
  }
}
```

```sql
-- CMP migration: none.
-- Contract migration numbers remain reserved as defined in SYSTEM_INTERFACE_CONTRACT.md §2.1.
-- No CMP schema addition is introduced by this feature.
```

## 8. Step-by-Step Implementation Plan — numbered steps, each tied to exactly one file

1. **`dashboard/src/components/ComplianceReport.jsx`** — create the CMP-owned component using the exact `ComplianceReport({ scan, summary, findings })` interface; derive all displayed evidence from props; use only Tailwind token classes; include scan metadata, risk summary, classical/quantum exposure, confidence evidence, remediation evidence, and explicit evidence/readiness wording.
2. **`dashboard/src/pages/DashboardPage/index.jsx`** — import `ComplianceReport`, pass the existing live scan state into it, and replace the existing `ReportsTab` mock report rendering with the component; do not add a second API client or second risk calculation.
3. **`dashboard/src/lib/api.js`** — retain this file as the sole API client; add no endpoint method unless the existing `GET /scans/{scan_id}` contract is proven insufficient during implementation.
4. **`dashboard/src/lib/constants.js`** — add only CMP-owned display metadata if needed, using the coordinated constants registry after DFS has landed; do not introduce duplicated canonical risk/confidence values.
5. **`dashboard/src/pages/DashboardPage/index.jsx`** — remove the CMP-specific hard-coded report/download data that would otherwise remain reachable from the Reports view.
6. **`dashboard/src/components/ComplianceReport.jsx`** — verify every metric against `summary`, `FindingOut`, and nested `RiskAssessmentOut`; never call or duplicate `api/services/risk_engine.py`.
7. **`dashboard/src/components/ComplianceReport.jsx`** — add empty/loading/error states using existing dashboard classes and no inline colour or animation values.
8. **`dashboard/src/pages/DashboardPage/index.jsx`** — verify CMP consumes the live scan selected/fetched by the existing dashboard data flow and does not introduce a second scan-fetch lifecycle.

## 9. Naming & Symbol Registry — every new function, class, DB column, env var, and CLI flag this feature introduces, checked against the contract's naming conventions and shared-resource index for collisions

| Kind | New symbol | Owner | Collision status |
|---|---|---|---|
| Component | `ComplianceReport` | CMP | Reserved by contract as `dashboard/src/components/ComplianceReport.jsx` |
| Function | `buildComplianceEvidence` | CMP | `camelCase` frontend symbol; no contract collision found |
| DB column | None | — | No schema change |
| DB table | None | — | No schema change |
| Environment variable | None | — | No new variable |
| CLI flag | None | — | No new flag |
| API route | None in v1 | — | `GET /scans/{scan_id}` is reused |

The applicable naming rules are quoted exactly from the contract: “Modules, functions, variables: `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE_CASE`.”; “Components `PascalCase.jsx` in `components/`; pages `pages/<Name>Page/index.jsx`; hooks `use<Thing>.js` in `hooks/`; API calls only through `lib/api.js`.”; and “No `/api/v1` prefix.”

## 10. Known Cross-Feature Risks — pulled directly from the contract's Flagged Conflicts & Resolutions and Shared Resource Index for any item naming this feature; state the resolution already decided, not a new one

- **C-04 — `api/services/risk_engine.py`:** Resolution is fixed: “`risk_engine.py` is the sole scoring authority. TRD and CMP are strictly read-side: they aggregate persisted `risk_tier`, `criticality` and `risk_assessments` rows and render them. No recomputation, no second curve.”
- **C-07 — `dashboard/src/index.css`, `tailwind.config.js`:** Resolution is fixed: “FE extends the existing tokens in place. All views consume them as Tailwind classes. Local hex values, inline colour styles and per-component animation durations are prohibited.” CMP therefore waits for FE Wave 3 presentation work.
- **C-08 — `dashboard/src/lib/api.js`:** Resolution is fixed: “`dashboard/src/lib/api.js` is canonical. Delete `dashboard/src/api.js`. RBAC owns adding the `Authorization: Bearer` flow there; every other feature adds only its own method.”
- **C-10 — `organization_id` scoping:** CMP is listed in the shared-resource index as conflicting and the contract marks the tenant-visibility question as unresolved. No new tenant rule may be invented by CMP.
- **C-13 — `dashboard/src/components/FindingsTable.jsx`, `dashboard/src/lib/constants.js`:** Resolution is fixed: DFS lands the column/filter architecture first; FE lands presentation second; remaining features add column definitions through the shared registry rather than editing table JSX. CMP must not bypass that structure.
- **C-16 — `GET /scans/{scan_id}/findings` query parameters:** Resolution is fixed to a shared FastAPI dependency `api/core/params.py::common_list_params` with OR-within-category and AND-across-category semantics; however, CMP-specific filter reuse remains an unresolved sign-off item and is therefore not implemented in v1.
- **C-19/C-20 — scope-truth documents:** Resolution for C-19 is a single scope-truth documentation pass after scanner scope docs exist; feature PRs must not touch `PRODUCT_DESCRIPTION.md`. C-20 has **no proposed resolution** in the contract and requires human sign-off; CMP does not make a scope decision.
- **C-24 — dashboard theme:** The contract says no resolution is applied; FE owns the decision and CMP must not hardcode either polarity.
- **Shared Resource Index:** `risk_assessments` is read-only for CMP; `GET /scans/{scan_id}` is compatible; `GET /compliance` is a CMP-only conditional route; `dashboard/src/components/ComplianceReport.jsx` is CMP SOLE.

## 11. Pre-Answered Ambiguities — at least 5 concrete situations an implementing agent could get confused by, each as "if X happens, do Y"; include every open sign-off item from the contract touching this feature, with the team's resolved answer

- **If `GET /scans/{scan_id}` contains all fields required by the report, do not create `api/routers/compliance.py`.** The contract makes that router conditional: “new, **only if** `GET /scans/{scan_id}` proves insufficient”.
- **If a report metric appears to require new risk mathematics, do not add it.** Read persisted `risk_tier`, `criticality`, and `risk_assessments`; `risk_engine.py` remains the sole scoring authority.
- **If a designer proposes a dark-only or light-only hard-coded colour, do not add it.** C-07 requires existing Tailwind tokens, while C-24 says the theme decision is unresolved and FE owns it.
- **If a developer finds `dashboard/src/api.js`, do not use it.** The contract makes `dashboard/src/lib/api.js` canonical and requires deletion of the orphaned duplicate in the appropriate coordinated frontend work.
- **If the FindingsTable needs a CMP column, do not edit its JSX directly.** Wait for DFS's column architecture and add the CMP definition through `dashboard/src/lib/constants.js`.
- **If a CMP-specific filter is requested, do not invent filter semantics.** C-16's shared semantics are resolved, but the contract explicitly leaves the CMP-specific compatibility question unresolved.
- **If `organization_id` is NULL or tenant visibility becomes relevant, do not guess.** C-10 is explicitly unresolved for CMP.
- **If the product documentation needs updating because scanner scope changed, do not edit `PRODUCT_DESCRIPTION.md` in the CMP PR.** C-19 assigns a single later scope-truth documentation pass.
- **If the implementer reaches C-24 (light/dark toggle) or C-10/C-16 decisions, stop at that boundary.** The contract's §7 says “Nothing below is decided. Each blocks the listed features.” It provides no team's resolved answer for these CMP-affecting items; therefore this specification does not invent one.
- **If a formal compliance percentage is requested, do not implement it.** The supplied Step 1 proposal says to avoid a single “87% Compliance Score” unless measurable controls and weighting exist; no such control matrix is defined in the contract or supplied product description.
- **If report export is requested, keep the report data model/read view separate from export generation.** The Step 1 proposal explicitly treats PDF/CSV as a later layer rather than the source of truth.

## 12. Test Plan / Definition of Done — exact commands to run, exact expected output

```text
cd dashboard
npm run build
```

Expected: process exits with code `0`; Vite completes the production build without an error.

```text
cd ..
pytest
```

Expected: process exits with code `0`; the repository test suite reports no failed tests.

```text
cd dashboard
npm run dev
```

Expected: the dashboard starts successfully; opening the Reports view shows the CMP component without console/API-client errors when a completed scan is available.

Definition of Done:
- `ComplianceReport.jsx` exists and is CMP-owned.
- Reports view no longer uses CMP mock report data as its source of truth.
- Data displayed in the report is traceable to `GET /scans/{scan_id}` fields.
- No CMP changes to `risk_engine.py`, `scan_runner.py`, scanner engines, DB schema, CLI flags, or `PRODUCT_DESCRIPTION.md`.
- No raw hex, inline colour styles, or per-component animation durations are introduced.
- No new dependency is introduced.
- `npm run build` and `pytest` pass.

The repository documents the general test command as `pytest`, and the dashboard package exposes `npm run build` as its production build command.

## 13. Rollback Plan — what to do if this breaks the build

1. Revert the CMP branch's changes to `dashboard/src/components/ComplianceReport.jsx`, `dashboard/src/pages/DashboardPage/index.jsx`, and `dashboard/src/lib/constants.js`.
2. Restore the previous coordinated `dashboard/src/lib/api.js` state if CMP changed it.
3. Do not revert shared Wave 0–3 contract changes belonging to other features.
4. Do not revert `dashboard/src/api.js` deletion if that deletion was merged by the owning frontend work under C-08.
5. Run `cd dashboard && npm run build` and `cd .. && pytest` after rollback.
6. If the failure is caused by an unresolved contract item, stop implementation and obtain human sign-off rather than changing a FROZEN interface or inventing a resolution.
