# SYSTEM_INTERFACE_CONTRACT.md

**Project:** ECDAT — Enterprise Cryptographic Discovery & Assessment Tool (SIH 2026, PS 26164, team ctrl-Nix)
**Status:** Draft v2 — integration cross-check only. Not a design review.
**Scope of this document:** 17 parallel feature proposals merging into one codebase.
**Authority:** Subordinate to `ARCHITECTURE.md`, `db/schema.sql` and `AGENT_RULES.md`. Where a proposal contradicts those, those win.

---

## 0. How to read this document

This contract answers one question only: *if all 17 proposals are built in parallel, what collides?*
It does **not** judge whether any individual proposal is a good idea.

Three ownership tiers are used throughout:

| Tier | Meaning |
|---|---|
| **SOLE** | One feature owns the file. Others must not open a PR against it. |
| **COORDINATED** | Multiple features must edit it. Edits go through the named integration owner, in the merge order in §6. |
| **FROZEN** | Interface is fixed by this contract. Changing it requires human sign-off per `AGENT_RULES.md` #3. |

Feature codes used in tables:

`DEP` dependency-scanning · `CNT` container-scanning · `BIN` binary-scanning · `IAC` config-iac-scanning ·
`CONF` unified-confidence-scoring · `CLI` cli-wrapper · `INS` install-script · `ENR` agent-enrollment ·
`ASP` agent-status-page · `RBAC` minimal-rbac · `AUD` audit-logging · `TRI` analyst-triage-workflow ·
`DFS` dashboard-filter-sort · `CMP` compliance-report-view · `TRD` quantum-risk-trend-view ·
`FE` frontend-typography-color-motion-pass · `CBV` cbom-export-validation

---

## 0.1 Ground-truth corrections applied to all proposals

Several proposals reference paths, languages or conventions that do not exist in this repository. These are corrected globally and silently in every section below — implementers should not "fix" them back.

| Referenced in proposals | Actual repository reality | Affected |
|---|---|---|
| `frontend/src/...` | `dashboard/src/...` | TRD, FE |
| `frontend/src/components/RiskCharts.jsx` | `dashboard/src/components/RiskChart.jsx` + `ChartsPanel.jsx` | FE |
| `frontend/src/components/Dashboard.jsx` | `dashboard/src/pages/DashboardPage/index.jsx` | FE |
| `frontend/src/api/client.js`, `dashboard/src/api/` | `dashboard/src/lib/api.js` | TRD, TRI |
| `api/schemas/` package | `api/models.py` (single Pydantic module) | TRI, TRD |
| `db/queries/trend_queries.py` | `db/crud.py` (single data-access layer, `ARCHITECTURE.md` §2.2) | TRD |
| `/api/v1/*` endpoints | Unversioned `/scans`, `/agent/v1` for machine routes | — |
| Go-style exported names | Python `snake_case` functions, `PascalCase` classes | — |
| Postgres native `CREATE TYPE ... ENUM` | `TEXT` columns + documented value tuples (existing pattern, e.g. `CONFIDENCES` in `db/models.py`) | — |
| UUID primary keys | `SERIAL` / `BIGSERIAL` integer PKs | — |
| `scan_results` table | `findings` table | — |
| Tailwind / React Router / React Query "need adding" | Already in `dashboard/package.json` | FE, ASP, DFS |

---

## 1. Canonical File Ownership Map

### 1.1 Scanner lane (`scanner/`)

| Path | Tier | Owner | Notes |
|---|---|---|---|
| `scanner/dependency_engine.py`, `scanner/dependency_rules/` | SOLE | DEP | new |
| `scanner/container_engine.py`, `scanner/image_layers.py` | SOLE | CNT | new |
| `scanner/binary_engine.py` | SOLE | BIN | new |
| `scanner/config_engine.py` | SOLE | IAC | new |
| `scanner/confidence.py` | SOLE | CONF | new; signal vocabulary + scorer |
| `scanner/enroll_cli.py` | SOLE | ENR | separate entrypoint; must not import `cli.main` |
| `scanner/ecdat_cli.py`, `pyproject.toml` | SOLE | CLI | subcommand dispatcher |
| `scanner/rules/container.yaml` | SOLE | CNT | |
| `scanner/rules/binary.yaml` | SOLE | BIN | |
| `scanner/rules/config.yaml` | SOLE | IAC | |
| `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml` | COORDINATED | scanner lane (Shashank) | CONF adds optional per-rule modifiers only |
| **`scanner/cli.py`** | **COORDINATED** | **scanner lane (Shashank)** | 5 features queue here — see C-01, C-11 |
| **`scanner/constants.py`** | **COORDINATED** | **scanner lane** | CNT, BIN, IAC each add skip sets — see C-12 |
| **`scanner/finding.py`** | **FROZEN** | **scanner lane** | Only CONF may add fields, once — see C-03 |
| `scanner/python_engine.py`, `scanner/multilang_engine.py` | COORDINATED | scanner lane | CONF removes the hardcoded `"high"` literal (`python_engine.py:198`, `multilang_engine.py:699`) |
| `scanner/__init__.py` | COORDINATED | scanner lane | each new engine exports one entry point |

### 1.2 API lane (`api/`)

| Path | Tier | Owner | Notes |
|---|---|---|---|
| `api/routers/auth.py`, `api/core/rbac.py` | SOLE | RBAC | new |
| **`api/routers/agents.py`** | **SOLE** | **ENR** | ASP consumes it, does not create it — see C-05 |
| `api/services/enrollment.py` | SOLE | ENR | new |
| `api/routers/audit.py`, `api/services/audit.py` | SOLE | AUD | new |
| `api/routers/triage.py` | SOLE | TRI | new; see C-16 for route shape |
| `api/routers/trends.py` | SOLE | TRD | new |
| `api/routers/compliance.py` | SOLE | CMP | new, **only if** `GET /scans/{scan_id}` proves insufficient |
| `api/services/cbom_validator.py` | SOLE | CBV | new |
| **`api/services/scan_runner.py`** | **FROZEN** | **CONF** | The confidence gate is CONF's to change. DEP/CNT/BIN/IAC must not touch it — see C-02 |
| **`api/services/cbom_generator.py`** | **COORDINATED** | **CBOM lane (Maitreyi)** | 6 features need it; one refactor — see C-14 |
| **`api/services/risk_engine.py`** | **FROZEN** | **CBOM/risk lane (Maitreyi)** | TRD and CMP are read-only consumers — see C-04 |
| **`api/models.py`** | **COORDINATED** | **backend lane (Shreyanshi)** | 7 features add Pydantic models here. No `api/schemas/` package. |
| **`api/routers/findings.py`** | **COORDINATED** | **backend lane** | CONF (band filter), DFS (filter/sort), TRI (merge triage into response) |
| `api/routers/scans.py`, `cbom.py`, `remediation.py`, `report_sync.py` | COORDINATED | backend lane | RBAC swaps the auth dependency; AUD adds event calls; CNT changes `ScanCreateRequest` |
| **`api/core/security.py`**, `api/core/config.py`, `api/main.py` | **COORDINATED** | **backend lane** | RBAC first, then ENR, then AUD — see C-09 |

### 1.3 Database lane (`db/`)

| Path | Tier | Owner | Notes |
|---|---|---|---|
| **`db/schema.sql`**, **`db/models.py`**, **`db/crud.py`**, `db/seed.py` | **COORDINATED** | **DB lane (Ronak)** | Every schema change lands via §2, never ad hoc |
| `db/migrations/002–008_*.sql` | SOLE per file | allocated in §2.1 | Filenames are reserved by this contract — see C-01 |

### 1.4 Frontend lane (`dashboard/`)

| Path | Tier | Owner | Notes |
|---|---|---|---|
| `dashboard/src/index.css`, `tailwind.config.js`, `dashboard/public/fonts/` | SOLE | FE | design tokens live here and nowhere else — see C-07 |
| `dashboard/src/components/ConfidenceStamp.jsx` | SOLE | CONF | currently a 2-line TODO stub |
| `dashboard/src/components/AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `pages/AgentStatusPage/`, `hooks/useAgents.js` | SOLE | ASP | |
| `dashboard/src/components/ComplianceReport.jsx` | SOLE | CMP | |
| `dashboard/src/components/RiskTrendChart.jsx`, `RiskTierBreakdown.jsx`, `pages/TrendsPage/` | SOLE | TRD | |
| **`dashboard/src/components/FindingsTable.jsx`** | **COORDINATED** | **frontend lane (Karan/Satyam)** | 7 features add columns — see C-13 |
| **`dashboard/src/lib/api.js`** | **COORDINATED** | **frontend lane** | single API client — see C-08 |
| ~~`dashboard/src/api.js`~~ | **DELETE** | frontend lane | orphaned duplicate, hardcoded dev key — see C-08 |
| `dashboard/src/App.jsx` | COORDINATED | frontend lane | ASP, TRD, DFS each register a route |
| `dashboard/src/pages/DashboardPage/index.jsx`, `lib/constants.js`, `mockData.js` | COORDINATED | frontend lane | CONF, CMP, DFS |
| `dashboard/src/context/AuthContext.jsx`, `pages/LoginPage/LoginForm.jsx` | SOLE | RBAC | |
| `dashboard/src/pages/LandingPage/index.jsx` | SOLE | frontend lane | sole permitted GSAP consumer — see C-17 |

### 1.5 Ops, CI and docs

| Path | Tier | Owner | Notes |
|---|---|---|---|
| `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml` | SOLE | INS | |
| `deploy/nginx/nginx.conf` | COORDINATED | deploy lane | ENR adds the enroll route + `$ssl_client_fingerprint`; AUD needs `X-Forwarded-For` |
| **`requirements.txt`** | **COORDINATED** | **backend lane** | single grouped diff — see C-18 |
| `Dockerfile`, `docker-compose.yml` | COORDINATED | deploy lane | CLI (entrypoint), CNT (tar mount), migration mounts |
| `.github/workflows/ecdat-scan.yml` | COORDINATED | CI lane | CNT, IAC, CLI |
| `.env.example` | COORDINATED | deploy lane | ENR, RBAC, CONF, AUD |
| **`PRODUCT_DESCRIPTION.md`** | **COORDINATED** | **single scope editor** | 5 features rewrite the §5 honesty table — see C-19, C-20 |
| `docs/ECDAT_CLI_GUIDE.md` | COORDINATED | scanner lane | 6 features |
| `docs/*_SCANNING_SCOPE.md`, `docs/CONFIDENCE_MODEL_SPEC.md`, `docs/COMPLIANCE_REPORT_SCOPE.md` | SOLE per file | respective feature | |
| `tests/test_crud.py`, `test_realworld_source_scanner.py`, `test_scanner_battle.py`, `test_security_controls.py` | COORDINATED | owning lane | CONF and RBAC both break existing assertions — see C-03, C-09 |

---

## 2. Canonical Schema Additions

One merged diff against `db/schema.sql` as it stands today (`repositories`, `scans`, `findings`, `risk_assessments`, `reports`).

**Binding conventions, matching the existing file:**
- `SERIAL` / `BIGSERIAL` integer primary keys named `id`. **No UUIDs.**
- `TEXT` columns with a documented value tuple. **No Postgres `CREATE TYPE ... ENUM`** — adding a scanner category must not require `ALTER TYPE`.
- `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`, so `schema.sql` and the migration stay idempotent and identical in effect.
- Every change appears **twice**: in `db/schema.sql` (fresh volumes) *and* in a numbered migration (existing deployments), plus a `docker-compose.yml` initdb mount. Missing either half is the defect this project has already been bitten by.

### 2.1 Reserved migration numbers

Five proposals independently claimed `002_`. Numbers are now allocated and are not negotiable without editing this file:

| File | Lane | Compose mount prefix |
|---|---|---|
| `db/migrations/002_confidence_scoring.sql` | CONF | `03_` |
| `db/migrations/003_artifact_scanning.sql` | DEP + CNT + BIN + IAC (one file) | `04_` |
| `db/migrations/004_rbac_users.sql` | RBAC | `05_` |
| `db/migrations/005_agent_enrollment.sql` | ENR | `06_` |
| `db/migrations/006_audit_events.sql` | AUD | `07_` |
| `db/migrations/007_finding_triage.sql` | TRI | `08_` |
| `db/migrations/008_query_indexes.sql` | DFS + TRD | `09_` |

### 2.2 Merged diff

```sql
-- ============================================================================
-- 002_confidence_scoring.sql  ·  owner: CONF
-- Unified, auditable confidence. Legacy findings.confidence TEXT is RETAINED
-- and becomes a derived, read-only mirror of confidence_band so existing rows,
-- CBOM output and the CLI contract do not break on day one.
-- ============================================================================
ALTER TABLE findings ADD COLUMN IF NOT EXISTS confidence_score   NUMERIC(3,2);
    -- 0.00–1.00. NUMERIC over SMALLINT: displayed as a percentage, no unit ambiguity.
ALTER TABLE findings ADD COLUMN IF NOT EXISTS confidence_band    TEXT;
    -- VERIFIED | PROBABLE | UNVERIFIED. NULL == pre-model legacy row.
ALTER TABLE findings ADD COLUMN IF NOT EXISTS confidence_signals JSONB;
    -- named evidence signals, e.g. ["import_resolved","literal_algorithm_arg"]
CREATE INDEX IF NOT EXISTS idx_findings_confidence_band ON findings(confidence_band);

-- ============================================================================
-- 003_artifact_scanning.sql  ·  owners: DEP, CNT, BIN, IAC (ONE file, one PR)
-- findings.source_context KEEPS its existing meaning (reachability:
-- SOURCE | TEST_ONLY | DEMO_ONLY). It gains NO fourth value.
-- What kind of artefact produced the finding is a separate axis.
-- ============================================================================
ALTER TABLE findings ADD COLUMN IF NOT EXISTS artifact_type TEXT NOT NULL DEFAULT 'SOURCE_FILE';
    -- SOURCE_FILE | DEPENDENCY_MANIFEST | CONFIG_FILE | BINARY | CONTAINER_LAYER
ALTER TABLE findings ADD COLUMN IF NOT EXISTS artifact_ref      TEXT;
    -- binary: "<section>+0x<offset>" · container: layer path · manifest: file path
ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_ecosystem TEXT;
    -- pypi | npm | maven | deb | apk | rpm
ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_name      TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_version   TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS image_digest      TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS layer_digest      TEXT;

CREATE INDEX IF NOT EXISTS idx_findings_artifact_type ON findings(artifact_type);
CREATE INDEX IF NOT EXISTS idx_findings_package
    ON findings(package_ecosystem, package_name)
    WHERE package_name IS NOT NULL;

-- scans.scan_context ALREADY EXISTS and carries the image reference / target
-- descriptor. No scans.target_type column is added: one scan may legitimately
-- mix source, config, manifest and binary artefacts in a single tree.

-- ============================================================================
-- 004_rbac_users.sql  ·  owner: RBAC
-- Deliberately NO roles table. The role -> permission map lives in
-- api/core/rbac.py so it is reviewable in code review and diffable in git.
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,          -- argon2 via pwdlib; never a raw or reversible value
    role            TEXT NOT NULL,          -- SECURITY_ADMIN | AUDITOR | DEVELOPER
    organization_id TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT now(),
    last_login_at   TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);

-- ============================================================================
-- 005_agent_enrollment.sql  ·  owner: ENR
-- Replaces the static REPORT_SYNC_AGENT_KEYS env mapping with a queryable
-- registry. Only the SHA-256 of an enrolment token is ever stored.
-- ============================================================================
CREATE TABLE IF NOT EXISTS agents (
    id                      SERIAL PRIMARY KEY,
    agent_id                TEXT NOT NULL UNIQUE,   -- matches reports.agent_id (TEXT, free-form today)
    organization_id         TEXT NOT NULL,
    public_key              TEXT NOT NULL,          -- base64 raw Ed25519, same encoding as REPORT_SYNC_AGENT_KEYS
    client_cert_fingerprint TEXT,                   -- forwarded by nginx; cert issuance stays manual
    status                  TEXT NOT NULL DEFAULT 'active',   -- active | revoked
    enrolled_at             TIMESTAMP DEFAULT now(),
    revoked_at              TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agents_org_status ON agents(organization_id, status);

CREATE TABLE IF NOT EXISTS enrollment_tokens (
    id                   SERIAL PRIMARY KEY,
    token_hash           TEXT NOT NULL UNIQUE,      -- SHA-256 hex. The token itself is never persisted.
    organization_id      TEXT NOT NULL,
    created_by           INTEGER REFERENCES users(id) ON DELETE SET NULL,
    expires_at           TIMESTAMP NOT NULL,
    consumed_at          TIMESTAMP,
    consumed_by_agent_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_enrollment_tokens_open
    ON enrollment_tokens(expires_at) WHERE consumed_at IS NULL;

-- ============================================================================
-- 006_audit_events.sql  ·  owner: AUD
-- Append-only. detail MUST NOT contain source code, file paths, or secrets.
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_events (
    id              BIGSERIAL PRIMARY KEY,
    occurred_at     TIMESTAMP NOT NULL DEFAULT now(),
    actor_type      TEXT NOT NULL,      -- user | agent | api_key | anonymous
    actor_ref       TEXT,               -- username | agent_id | key-fingerprint prefix. NEVER the key.
    organization_id TEXT,
    action          TEXT NOT NULL,      -- dotted verb, see §3.6
    object_type     TEXT,               -- scan | finding | cbom | report | agent | user
    object_id       TEXT,
    outcome         TEXT NOT NULL,      -- allowed | denied | error
    client_ip       TEXT,               -- from X-Forwarded-For; trustworthy only behind the gateway
    detail          JSONB,
    prev_hash       TEXT,               -- entry_hash of the preceding row
    entry_hash      TEXT NOT NULL       -- SHA-256 over canonical JSON of this row + prev_hash
);
CREATE INDEX IF NOT EXISTS idx_audit_events_org_time ON audit_events(organization_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_action   ON audit_events(action, occurred_at DESC);

CREATE RULE audit_events_no_update AS ON UPDATE TO audit_events DO INSTEAD NOTHING;
CREATE RULE audit_events_no_delete AS ON DELETE TO audit_events DO INSTEAD NOTHING;

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

-- ============================================================================
-- 008_query_indexes.sql  ·  owners: DFS, TRD
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_findings_scan_tier   ON findings(scan_id, risk_tier);
CREATE INDEX IF NOT EXISTS idx_findings_scan_lang   ON findings(scan_id, language);
CREATE INDEX IF NOT EXISTS idx_scans_repo_started   ON scans(repo_id, started_at DESC);
```

### 2.3 Explicitly rejected schema proposals

| Proposed | Rejected because |
|---|---|
| `scan_results` table | The table is `findings`. Renaming breaks `db/crud.py`, `api/routers/findings.py`, the CBOM generator and every test. |
| Polymorphic `scans.scan_category` ENUM | A single scan legitimately mixes artefact types; the axis belongs on `findings`, not `scans`. |
| `roles` table | RBAC proposes a code-resident permission map. A DB table adds a join and an un-diffable source of truth. |
| `triage_status` column on `findings` | Destroys the evidence/interpretation separation and is clobbered by re-scan. |
| `cbom_exports` table | CBOM is generated deterministically on demand from `findings` + `risk_assessments`. Persisting exports creates a second source of truth CBV exists to prevent. |
| `agents.last_seen_at` as live heartbeat | No heartbeat channel exists. ASP derives delivery freshness from `reports.created_at`; `agents.status` is registry state. Two different facts (C-06). |
| `findings.offset` / `artifact_format` columns | Superseded by `artifact_ref` + `artifact_type`; BIN itself recommended against dedicated columns in v1. |

---

## 3. Canonical Naming Conventions

### 3.1 Python (backend, scanner, db)

- Modules, functions, variables: `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE_CASE`.
- **No PascalCase function names.** The shared scorer is `calculate_confidence_score()`, not `CalculateECDATScore()`.
- Shared logic is disambiguated by **module path, not by prefixing the project name into the identifier**: `scanner.confidence.calculate_confidence_score()` and `api.services.risk_engine.score_findings()`.
- Every detection engine exposes exactly this pair, and nothing else may be imported across lanes:
  ```python
  def scan_file(path: Path, rules: dict | None = None) -> list[Finding]: ...
  def scan_directory(root: Path, rules: dict | None = None) -> list[Finding]: ...
  ```
  Pure, path-based, no CLI or DB coupling — this is what CNT needs in order to hand extracted layers to BIN.
- New engine modules: `scanner/<domain>_engine.py`. New rule packs: `scanner/rules/<domain>.yaml`.
- CRUD helpers: `get_*`, `list_*`, `save_*`, `count_*`, `record_*` — matching `db/crud.py` today.

### 3.2 `detection_method` registry (FROZEN)

`detection_method` is the agreed discriminator across all five engines. Adding a value requires editing this list.

| Value | Emitted by | Evidence strength |
|---|---|---|
| `ast_visitor` | python_engine | traced call site |
| `tree_sitter_query` | multilang_engine | traced call site |
| `certificate_parse` | container_engine | parsed X.509 fact |
| `config_analysis` | config_engine | declared setting |
| `dependency_manifest` | dependency_engine | declared dependency |
| `binary_symbol_table` | binary_engine (tier 1) | parsed linkage |
| `binary_constant_scan` | binary_engine (tier 2) | byte-pattern presence |
| `container_package_inventory` | container_engine | package presence |

Forbidden: `static_analysis` (too vague to distinguish AST from byte scanning), `regex_match` (`AGENT_RULES.md` #5).

### 3.3 Environment variables

- `UPPER_SNAKE_CASE`, feature-prefixed. Bare `TARGET`, `TOKEN`, `SECRET`, `KEY`, `PATH` are forbidden.
- **Existing variables are frozen and must not be renamed**: `POSTGRES_*`, `API_KEY`, `DEBUG`, `CORS_ORIGINS`, `ENABLE_LOCAL_SCAN_API`, `ALLOW_REMOTE_REMEDIATION`, `REPORT_SYNC_*`, `ECDAT_HTTPS_PORT`.
- New variables use these reserved prefixes:

| Prefix | Owner | Examples |
|---|---|---|
| `AUTH_` | RBAC | `AUTH_JWT_SECRET`, `AUTH_JWT_TTL_MINUTES`, `AUTH_BOOTSTRAP_ADMIN_USERNAME` |
| `AGENT_ENROLLMENT_` | ENR | `AGENT_ENROLLMENT_TOKEN_TTL_HOURS`, `AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS` |
| `SCAN_` | scanner lanes | `SCAN_MIN_CONFIDENCE_BAND`, `SCAN_ENABLE_BINARY`, `SCAN_ENABLE_CONTAINER`, `SCAN_MAX_ARTIFACT_BYTES`, `SCAN_IMAGE_TAR_PATH` |
| `AUDIT_` | AUD | `AUDIT_FAIL_CLOSED`, `AUDIT_RETENTION_DAYS` |
| `VITE_` | frontend | `VITE_API_URL`, `VITE_API_KEY` (Vite requires this prefix for client exposure) |

Anything named `VITE_*` is **shipped to the browser**. No secret may ever carry that prefix — the current `VITE_API_KEY` default is itself a defect (C-08).

### 3.4 HTTP API routes

- **No `/api/v1` prefix.** The backend serves unversioned analyst routes; the nginx gateway exposes them externally under `/api/`. Introducing an internal `/api/v1` would break `deploy/nginx/nginx.conf`, `dashboard/src/lib/api.js`, `.github/workflows/ecdat-scan.yml` and the CLI guide simultaneously.
- Analyst / browser routes: plural resource nouns at the root — `/scans`, `/findings`, `/agents`, `/audit/events`, `/trends`, `/auth/login`.
- Machine-to-machine agent routes keep the existing versioned namespace: `/agent/v1/report-bundles`, `/agent/v1/enroll`.
- A resource owned by a scan stays nested under it: `/scans/{scan_id}/findings/{finding_id}/triage`, not a new top-level `/findings/{id}/triage`.
- Routers declare their own `prefix=` (existing pattern); `api/main.py` does not re-prefix, with the single existing exception of `remediation.router`.
- Health: the canonical external healthcheck is **`GET /api/health` through the gateway**. `https://localhost:8443/health` reaches the dashboard SPA, not the backend (C-21).

### 3.5 CLI

- Long flags only, `kebab-case`. No new single-letter flags.
- Exit codes are FROZEN: `0` pass, `1` error, `2` policy violation (`--fail-on`).
- `scanner/cli.py` stdout stays a **JSON array of finding dicts and nothing else** — `api/services/scan_runner.py` parses it. Human-readable output and logs go to stderr. Fields may be added; none may be renamed or removed.
- Engine selection uses one repeatable flag, not one boolean per engine:
  ```
  --scan-type {source,dependency,config,binary,container}   # repeatable; default: source
  --image-tar PATH        # only valid with --scan-type container
  --min-confidence BAND   # VERIFIED | PROBABLE | UNVERIFIED
  ```
- `scanner/ecdat_cli.py` subcommands: `ecdat scan`, `ecdat cbom`, `ecdat sync`. Subcommands are verbs; engines are flags. There is no `ecdat scan container` subcommand — that would split the flag surface across two grammars.

### 3.6 Audit action names

Dotted, lowercase, `ecdat.<object>.<verb>`: `ecdat.scan.create`, `ecdat.scan.read`, `ecdat.cbom.export`, `ecdat.remediation.generate`, `ecdat.report.ingest`, `ecdat.agent.enroll`, `ecdat.agent.revoke`, `ecdat.auth.login`, `ecdat.auth.denied`, `ecdat.triage.update`.

### 3.7 Frontend

- **Design tokens already exist** as CSS custom properties in `dashboard/src/index.css` (`--void`, `--surface`, `--border`, `--cyan`, `--purple`, `--green`, `--critical`, `--high`, `--medium`, `--low`, `--t1`…`--t4`) and are wired into `tailwind.config.js`. Components consume them **only** as Tailwind classes (`bg-surface`, `text-t2`, `border-border`).
- **Do not introduce a new token namespace.** A `--sys-*` rename would invalidate every existing utility class in the dashboard for zero functional gain.
- New tokens are added in `index.css` **and** `tailwind.config.js`, by FE only. Motion tokens: `--motion-fast: 150ms`, `--motion-base: 200ms`, `--motion-slow: 250ms`.
- Raw hex values, inline `style={{color:…}}`, and per-component animation timings are prohibited in `dashboard/src/components/**` and `dashboard/src/pages/**`.
- Components `PascalCase.jsx` in `components/`; pages `pages/<Name>Page/index.jsx`; hooks `use<Thing>.js` in `hooks/`; API calls only through `lib/api.js`.

### 3.8 Database

Tables plural `snake_case` · PK `id SERIAL`/`BIGSERIAL` · FK `<singular>_id` · timestamps `*_at` · booleans `is_*`/`has_*` · indexes `idx_<table>_<cols>` · value sets as `TEXT` plus a module-level tuple in `db/models.py` (the existing `CONFIDENCES` pattern), never a native Postgres ENUM.

---

## 4. Flagged Conflicts & Resolutions

Confidence refers to the **resolution**, not to the existence of the conflict.
**Medium and Low items must not be implemented until a human signs off on the listed question.**

---

### C-01 · Migration filename and initdb-ordering collision
**Shared resource:** `db/migrations/002_*.sql`, `docker-compose.yml` initdb mounts
**Proposals:** CNT, CONF, ENR, RBAC, AUD — **five** files all named `002_`
**State:** Conflicting. Two of these merging on the same day silently overwrite each other; `docker-compose.yml` mounts migrations into `/docker-entrypoint-initdb.d` with numeric prefixes, so duplicate numbers also produce non-deterministic apply order on fresh volumes.
**Resolution:** Numbers 002–008 are reserved in §2.1. Every migration also adds a `docker-compose.yml` mount with the matching `NN_` prefix, and the identical change must land in `db/schema.sql` in the same PR.
**Rationale:** initdb applies files in lexical order on fresh volumes only, so the schema file and the migration are two independent code paths that must be kept in lockstep.
**Confidence:** **High**

---

### C-02 · `scan_runner.py` drops every non-`"high"` finding
**Shared resource:** `api/services/scan_runner.py:103`
**Proposals:** DEP, CNT, BIN, IAC, CONF
**State:** Conflicting, and currently a silent data-loss bug for four unbuilt features. The runner filters `finding.get("confidence") == "high"` before scoring and persisting. Container package inventory, binary tier-2 constants, and unresolved IaC variables are all honestly sub-`high` by their own proposals — so all three would scan successfully, print findings to the CLI, and persist **zero rows**.
**Resolution:** The gate is CONF's to replace, with a configurable band threshold (`SCAN_MIN_CONFIDENCE_BAND`, default `PROBABLE`). DEP, CNT, BIN and IAC must not edit this file; they depend on CONF landing first. Until it does, they are CLI-only features and must say so in their scope docs rather than loosening the gate locally.
**Rationale:** Four features independently patching the same filter produces four different persistence semantics and no single answer to "what does the database contain".
**Confidence:** **High** on ownership and sequencing.
**→ Medium and needs sign-off:** whether sub-threshold findings are **dropped** or **persisted with their band**. CONF argues persist, because dropping destroys evidence the dashboard could legitimately show as unverified. This changes what the database means and what the demo's finding count is. Product + DB lane decision.

---

### C-03 · Four incompatible confidence vocabularies already in the repo
**Shared resource:** `scanner/finding.py`, `db/models.py:14`, `api/models.py`, `dashboard/src/mockData.js`, `LandingPage`
**Proposals:** CONF, CNT, BIN, IAC, FE, DFS
**State:** Conflicting, pre-existing. `db/models.py` declares `CONFIDENCES = ("low","medium","high")`. `scanner/finding.py` and `ARCHITECTURE.md` §2.1 document `high` / `unverified`. `mockData.js` uses `high/medium/low`. `LandingPage` shows `Verified` / `Probable`. Both engines hardcode the literal `"high"`. On top of that, CNT wants a new `inventory` value and BIN wants `medium`.
**Resolution:** Adopt CONF's two-field model as the single vocabulary: `confidence_score NUMERIC(3,2)` plus `confidence_band` ∈ `VERIFIED | PROBABLE | UNVERIFIED`. The legacy `findings.confidence` TEXT column is kept as a derived, read-only mirror (`VERIFIED→high`, else `unverified`) so CBOM output and the CLI JSON contract survive the transition. `inventory` and `medium` are expressed as bands plus a `detection_method`, not as new confidence strings.
**Rationale:** Confidence must mean the same thing for a Python AST hit and a container package listing, or cross-engine comparison is meaningless — which is the entire premise of the unified scoring work.
**Confidence:** **Medium**
**→ Needs sign-off:** (a) backfill policy for existing `confidence='high'` rows — backfill a band or leave NULL as "pre-model"? (b) `tests/test_crud.py`, `test_realworld_source_scanner.py` and `test_scanner_battle.py` assert `confidence == "high"` and will fail; who updates them, and does the 18-finding demo baseline move? (c) does `--fail-on` consider band, i.e. should an `UNVERIFIED` CRITICAL break a build?

---

### C-04 · Two risk-scoring implementations
**Shared resource:** `api/services/risk_engine.py`
**Proposals:** TRD (hardcoded statistical assumptions about risk curves), CONF, CMP, CNT, IAC
**State:** Conflicting. TRD bakes risk assumptions into a view layer while `risk_engine.py` is the documented deterministic authority (`docs/RISK_ENGINE_SPEC.md`).
**Resolution:** `risk_engine.py` is the sole scoring authority. TRD and CMP are strictly read-side: they aggregate persisted `risk_tier`, `criticality` and `risk_assessments` rows and render them. No recomputation, no second curve. Confidence stays a **separate axis** from `risk_tier` — a low-confidence MD5 finding is still a CRITICAL algorithm with weaker evidence.
**Rationale:** Two implementations of the same mathematics guarantees a CBOM export and a dashboard chart eventually disagree in front of a judge.
**Confidence:** **High** on the decoupling.
**→ Medium and needs sign-off:** whether the ECDAT confidence model must also expose historical/time-bucketed values for TRD's trend axis. Trends read across scans; the confidence model is per-finding and per-scan, and recomputation under a new `risk_model_version` would retroactively change a plotted line. Risk-engine owner (Maitreyi) + TRD must agree whether trends pin to `risk_model_version` or always show latest.

---

### C-05 · Two features create `api/routers/agents.py`
**Shared resource:** `api/routers/agents.py`
**Proposals:** ENR (admin write: mint token, list, revoke), ASP (analyst read: status aggregation)
**State:** Conflicting — a literal file collision neither proposal noticed.
**Resolution:** ENR owns `api/routers/agents.py` and the `agents` / `enrollment_tokens` tables. ASP owns only its dashboard files plus a read-only aggregation helper in `db/crud.py`, and consumes `GET /agents`. ENR merges first; ASP's endpoint is added to ENR's router, not a second file.
**Rationale:** A registry and a view of that registry are one resource; splitting them across two routers duplicates the authorization surface.
**Confidence:** **High**

---

### C-06 · "Agent status" means two different things
**Shared resource:** `agents.status`, `reports.created_at`
**Proposals:** ENR (registry lifecycle: `active`/`revoked`), ASP (delivery freshness derived from report history)
**State:** Compatible, but conflated — ASP explicitly notes no heartbeat field exists and warns against claiming live connectivity.
**Resolution:** Two separate fields in the API response, never merged into one badge: `registry_status` (`active`/`revoked`, from `agents`) and `delivery_status` (`recent`/`stale`/`never_reported`, derived from `MAX(reports.created_at)`). No `last_seen_at` heartbeat column is added.
**Rationale:** An enrolled agent that has never reported and a revoked agent that reported an hour ago are different operational facts; collapsing them produces a dashboard that lies.
**Confidence:** **High** on the split.
**→ Low and needs sign-off:** the time window separating `recent` from `stale`. There is no operational baseline, no SLA, and no heartbeat interval to derive it from. Product decision, not an engineering one.

---

### C-07 · Frontend styling: three features vs one existing token system
**Shared resource:** `dashboard/src/index.css`, `dashboard/tailwind.config.js`
**Proposals:** FE (owns the pass), DFS, TRD, CMP, plus scanner features adding table columns
**State:** Conflicting. FE proposes a new `frontend/src/theme/tokens.css`; a complete token scale already exists in `dashboard/src/index.css` and is mapped into `tailwind.config.js`. TRD and CMP describe custom chart colours.
**Resolution:** FE extends the existing tokens in place. All views consume them as Tailwind classes. Local hex values, inline colour styles and per-component animation durations are prohibited. A previously proposed `--sys-*` namespace is **rejected** — renaming the tokens invalidates every existing utility class for no functional gain.
**Rationale:** The token layer already works and is already consumed; the cheapest correct move is to extend it, not to re-namespace it mid-sprint.
**Confidence:** **High**

---

### C-08 · Two frontend API clients, one carrying a hardcoded key
**Shared resource:** `dashboard/src/api.js`, `dashboard/src/lib/api.js`
**Proposals:** RBAC, ASP, CMP, DFS, TRI all add methods to "the API client"
**State:** Conflicting, pre-existing. `lib/api.js` uses same-origin `/api` with localStorage-token and `X-API-Key` interceptors. `src/api.js` targets `http://localhost:8000` with `API_KEY = 'ecdat-secret-key-dev'` inline. **Nothing imports `src/api.js`** — all four live consumers (`useFindings`, `useScans`, `useRiskSummary`, `DashboardPage`) import `lib/api.js`.
**Resolution:** `dashboard/src/lib/api.js` is canonical. Delete `dashboard/src/api.js`. RBAC owns adding the `Authorization: Bearer` flow there; every other feature adds only its own method. Rotate the committed dev key value and remove the `VITE_API_KEY` fallback default.
**Rationale:** An orphaned client with a committed credential and a cross-origin base URL is the one that will be picked up by the next feature that greps for `axios.create`.
**Confidence:** **High** on deletion (verified: zero importers).
**→ Medium and needs sign-off:** JWT storage — keep `localStorage` (current behaviour) or move to an httpOnly cookie. This is a security posture call that interacts with the CSP and the same-origin gateway design.

---

### C-09 · Authentication rewrite blocks four other features
**Shared resource:** `api/core/security.py`, `api/main.py`, `api/core/config.py`, all analyst routers
**Proposals:** RBAC (replaces `get_api_key` with JWT + `require_role`), ENR ("interim `get_api_key`"), AUD (needs a real actor identity), ASP (needs org-scoped authorization before live data), INS (needs auth env vars and an admin bootstrap)
**State:** Conflicting on ordering. Four features are each written against a different assumed auth state.
**Resolution:** RBAC merges first and publishes the `Principal` contract (`username`, `role`, `organization_id`) **before** the others start. AUD records `actor_type='api_key'` with a key-fingerprint prefix before RBAC lands and `actor_type='user'` after. ENR's admin endpoints use `require_role(SECURITY_ADMIN)` from day one. ASP does not connect to live data until org scoping exists. Agent report-sync (mTLS + Ed25519) is untouched by all of this.
**Rationale:** Auth is the deepest shared dependency in the sprint; four features retrofitting it afterwards costs more than one blocking merge.
**Confidence:** **High** on the ordering.
**→ Medium and needs sign-off:** does `X-API-Key` survive for CLI and service callers, or is it removed entirely? `tests/test_security_controls.py`, `.github/workflows/ecdat-scan.yml` and `dashboard/src/lib/api.js` all depend on the answer, and removing it breaks the CI gate.

---

### C-10 · `organization_id` scoping is assigned to nobody
**Shared resource:** `repositories.organization_id`, `reports.organization_id`, all list endpoints
**Proposals:** RBAC ("another feature must apply it"), ASP (requires it before exposing live data), ENR (notes there is no `organizations` table and the column is free text), AUD, CMP, TRD
**State:** Conflicting by omission — every feature assumes someone else applies the tenant filter.
**Resolution:** RBAC exposes `Principal.organization_id`. A single shared filter helper in `db/crud.py` applies it; no router writes its own `WHERE organization_id = …`. No `organizations` table is added this sprint; the column stays free text.
**Rationale:** A tenant filter applied in six places is a tenant filter that is missing in one of them.
**Confidence:** **Medium**
**→ Needs sign-off:** behaviour when `organization_id` is NULL on legacy rows — visible to all, visible to none, or migration-backfilled? Cross-tenant enumeration is the specific risk ASP raised, so this needs an explicit answer before any live analyst data is exposed.

---

### C-11 · Five features modify `scanner/cli.py`; flag namespace collides
**Shared resource:** `scanner/cli.py`, CLI flag namespace
**Proposals:** DEP, CNT (`--image-tar`, `--target-type`), BIN (`--binaries`), IAC ("optional target type"), CONF (`--min-confidence`), CLI (declares it untouched)
**State:** Conflicting. CNT and IAC both propose a `--target-type`-shaped flag with different value sets; BIN proposes a separate boolean; nothing coordinates defaults.
**Resolution:** One repeatable `--scan-type {source,dependency,config,binary,container}` flag, default `source` only, per §3.5. `--image-tar` is valid only with `--scan-type container`. The scanner lane owns `cli.py` and merges these one at a time. `scanner/ecdat_cli.py` (CLI) wraps it without changing its behaviour; `scanner/enroll_cli.py` (ENR) stays a separate entrypoint so the stdout JSON contract is untouched.
**Rationale:** Defaulting to `source` preserves the existing CI gate, the `--fail-on HIGH` policy and the demo baseline, which BIN correctly identified as the constraint.
**Confidence:** **Medium**
**→ Needs sign-off:** the exact flag spelling and whether bare `ecdat TARGET` remains an alias for `scan`. Scanner lane (Shashank) ratification, since `docs/ECDAT_CLI_GUIDE.md` and `.github/workflows/ecdat-scan.yml` both encode the current grammar.

---

### C-12 · `scanner/constants.py` skip-list conflicts
**Shared resource:** `scanner/constants.py` (`SKIP_DIRS`)
**Proposals:** BIN, CNT, IAC
**State:** Conflicting. `SKIP_DIRS` contains `target`, `build` and `dist` — precisely where compiled artefacts live, so the existing source skip list actively hides what BIN needs to find. CNT needs layer-internal skips (`/proc`, `/sys`, `/usr/share/doc`); IAC needs config extensions that the source walker ignores.
**Resolution:** Keep `SKIP_DIRS` as the source-walk list, unchanged. Add named per-engine sets in the same module: `BINARY_SKIP_DIRS`, `CONTAINER_LAYER_SKIP_PATHS`, `CONFIG_FILE_PATTERNS`, plus a shared `SCAN_MAX_ARTIFACT_BYTES`. No engine mutates another's set.
**Rationale:** One walker's noise is another walker's target; a single shared list cannot serve both without silently breaking source scanning.
**Confidence:** **High**

---

### C-13 · `FindingsTable.jsx` edited by seven features
**Shared resource:** `dashboard/src/components/FindingsTable.jsx`, `dashboard/src/lib/constants.js`
**Proposals:** CNT (layer/package columns), BIN (`line=0` display), IAC (config evidence), CONF (confidence stamp), DFS (filter/sort controls), TRI (status dropdown + notes), FE (monospace cells, tier badges)
**State:** Conflicting through sheer contention — seven simultaneous PRs against one component.
**Resolution:** DFS lands the column/filter architecture first (it restructures the table). FE lands presentation second. Each remaining feature then adds a column definition to a shared registry in `dashboard/src/lib/constants.js` rather than editing the table's JSX. `line=0` renders as `—`, never `0`, since a binary has no line number.
**Rationale:** Converting the table from hand-written JSX to a column registry turns seven merge conflicts into seven additive entries.
**Confidence:** **Medium**
**→ Needs sign-off:** whether DFS's restructure is in scope for its sprint, since it is now a prerequisite for five other features. Frontend lane (Karan/Satyam) capacity call.

---

### C-14 · `cbom_generator.py` pulled six ways
**Shared resource:** `api/services/cbom_generator.py`
**Proposals:** CLI (needs a DB-free `build_cbom_from_findings(findings, summary)`), CBV (validates the output), CNT (`related-crypto-material` branch for certificates), BIN (`detection_method` in evidence; `line=0` is misleading), CONF (machine-readable confidence property instead of free-text `additionalContext` at lines 179/223), IAC (configuration-derived evidence)
**State:** Conflicting.
**Resolution:** One refactor, owned by the CBOM lane, before any consumer merges: extract a pure `build_cbom_from_findings(findings: list[dict], summary: dict) -> dict`, and make the existing ORM-based `generate_cbom` a thin wrapper over it. CBV validates the returned dict, so CLI and API output are validated by the same code path. All ECDAT extensions use a single registry of `ecdat:*` property keys — `ecdat:confidence_band`, `ecdat:confidence_score`, `ecdat:detection_method`, `ecdat:artifact_type` — never free-text `additionalContext`.
**Rationale:** One generator with two entry points is the only way the CLI's CBOM and the API's CBOM provably match, which is the claim the pitch makes.
**Confidence:** **High** on the refactor shape.
**→ Medium and needs sign-off:** CBV's open question — does a validation failure return HTTP 500 (the server generated an invalid document) or 200 with a warning? And is the full official CycloneDX 1.6 JSON schema enforced, or only the cryptographic-asset subset ECDAT emits? These change the export endpoint's failure contract.

---

### C-15 · Triage decisions do not survive a re-scan
**Shared resource:** `findings.id`, `finding_triage`
**Proposals:** TRI
**State:** Conflicting with the existing data model, and unaddressed by the proposal. `findings` rows are per-scan with `ON DELETE CASCADE` from `scans`. A re-scan creates **new** `findings.id` values, so a 1:1 triage table keyed on `finding_id` silently loses every "false positive" an analyst recorded the moment the repo is scanned again.
**Resolution:** Add `findings.fingerprint` (stable across scans: repo, file, algorithm, primitive, library, normalised context — deliberately excluding `line`, which shifts on unrelated edits). `finding_triage` stores both `finding_id` and `fingerprint`; disposition is carried forward to the newest matching finding on each scan.
**Rationale:** Triage that resets on every scan is worse than no triage, because an analyst will trust it once.
**Confidence:** **Medium**
**→ Needs sign-off:** the exact fingerprint input set. Too narrow and a one-line edit resurrects a dismissed finding; too broad and two genuinely different findings in one file collapse into one. DB lane + scanner lane, and it needs a test with a deliberately edited fixture.

---

### C-16 · Overlapping list/filter/pagination logic
**Shared resource:** `api/routers/findings.py` query parameters
**Proposals:** DFS (`risk_tier`, `primitive`, `algorithm`, `language`, `sort_by`, `sort_dir`), CONF (band filter/sort), CMP (aggregation over the same rows), TRD (time bucketing), TRI (triage status in the findings response)
**State:** Conflicting. `GET /scans/{scan_id}/findings` already accepts `risk_tier`, `limit` and `offset`; four features extend the same parameter surface independently.
**Resolution:** A shared **FastAPI dependency** — `api/core/params.py::common_list_params` — injected with `Depends()`, not middleware. Middleware cannot do typed validation, cannot appear in the OpenAPI schema, and cannot vary per route. Multi-value filters are **OR within a category, AND across categories** (`language in (py,js) AND risk_tier in (CRITICAL)`). Filter values are validated against the canonical value tuples in `db/models.py`, not against distinct values present in the data.
**Rationale:** In FastAPI, a dependency is the idiomatic unit of reuse; query parsing in middleware would bypass Pydantic validation and produce an OpenAPI schema that does not describe the real API.
**Confidence:** **Medium**
**→ Needs sign-off:** whether CMP's compliance filters can share these semantics without violating domain-specific rules, and whether filter dropdowns are populated from canonical enums or from distinct values in the current scan (DFS raised both and answered neither).

---

### C-17 · Two animation libraries, one motion spec
**Shared resource:** `dashboard/package.json`, motion behaviour
**Proposals:** FE (proposes framer-motion "or CSS only")
**State:** Conflicting, pre-existing. Both `framer-motion` and `gsap` are installed. framer-motion is used in `App.jsx`, `DashboardPage`, `LoginForm`, `ProjectDemoWalkthrough` and `LandingPage`; gsap (with ScrollTrigger) is used **only** in `LandingPage`.
**Resolution:** framer-motion is canonical for application and dashboard motion, bound to the `--motion-*` tokens. GSAP stays scoped to `dashboard/src/pages/LandingPage/index.jsx` for scroll choreography and is not imported anywhere else. No third animation dependency.
**Rationale:** Two general-purpose animation runtimes in one bundle is a size and consistency cost; a narrowly scoped scroll library with one consumer is not worth a rewrite mid-sprint.
**Confidence:** **High**

---

### C-18 · `requirements.txt` contention, and `cryptography` is unpinned
**Shared resource:** `requirements.txt`
**Proposals:** BIN (`lief`), IAC (`python-hcl2`), RBAC (`PyJWT`, `pwdlib[argon2]`), CNT and CLI (pin `cryptography`), CBV (possibly a schema validator)
**State:** Conflicting, plus a live defect: `api/services/report_bundle.py` imports `cryptography` for Ed25519 signing and verification, and `cryptography` **is not in `requirements.txt`**. The signed-bundle security story currently rests on a transitive dependency.
**Resolution:** One grouped diff owned by the backend lane. Add `cryptography>=46.0.0` to `requirements.txt` immediately — this is independent of all 17 features. Use a floor, not `==`: every other line in that file uses a floor, and a crypto-discovery tool shipping a two-year-old `cryptography` is indefensible in front of judges. `lief` and `python-hcl2` must be wheel-verified against `python:3.11-slim` before merge (`tree-sitter-languages` already constrains this project to 3.11). CBV uses Pydantic v2, already present, rather than adding a JSON-schema library.
**Rationale:** An unpinned dependency underneath tamper-evidence is a supply-chain claim the project cannot currently defend.
**Confidence:** **High** on pinning `cryptography`.
**→ Medium and needs sign-off:** `lief` specifically. It is a native parser pointed at untrusted binaries inside a `cap_drop: [ALL]`, `read_only: true` container. BIN's own fallback (`pyelftools` + `pefile` + `macholib`, pure Python) trades one API for three but removes a native parsing surface. Security review call.

---

### C-19 · Five features rewrite the same scope-honesty table
**Shared resource:** `PRODUCT_DESCRIPTION.md` §5/§7, `README.md`, `ARCHITECTURE.md` §1/§6
**Proposals:** CNT, BIN, IAC, CONF, CMP
**State:** Conflicting. CNT notes §5 currently says container scanning is out of scope and that the row "must change or the pitch becomes a lie". BIN, IAC and CMP each independently plan the same edit.
**Resolution:** Scope-truth documents are edited **once**, by a single named scope editor, after all four scanner scope docs (`docs/CONTAINER_SCANNING_SCOPE.md`, `BINARY_SCANNING_SCOPE.md`, `CONFIG_IAC_SCANNING_SCOPE.md`, `SOURCE_SCANNING_SCOPE.md`) exist. Feature PRs create their own scope doc and must not touch `PRODUCT_DESCRIPTION.md`.
**Rationale:** Five partial rewrites of a document whose entire value is being honest about limits produces a document that is honest about nothing.
**Confidence:** **High** on the process.

---

### C-20 · Scope contradiction — **RESOLVED**
**Shared resource:** project scope
**Was:** `AGENT_RULES.md` #6 declared binary, container and dependency scanning in scope, while `PRODUCT_DESCRIPTION.md` §5, `README.md` and `docs/SOURCE_SCANNING_SCOPE.md` declared them out of scope and used that restraint as a pitch differentiator.
**Resolution (team decision, ratified):** All four new detection engines — dependency, config/IaC, binary, container — are **IN SCOPE**. `AGENT_RULES.md` #6 is the current statement. The three pitch documents have been rewritten to match:
- `PRODUCT_DESCRIPTION.md` §5 now lists the four engines as in-sprint, and adds two genuine out-of-scope rows (registry pulls, runtime analysis) so the honesty table still has teeth.
- The "scope discipline" talking point is rewritten around the **one-Finding-contract** architecture and the confidence band, rather than around not building the engines.
- `docs/SOURCE_SCANNING_SCOPE.md` is now explicitly the *source-code* scope document and cross-references one scope doc per engine.
- `README.md` §3.3 no longer lists binary/container as planned.

**The pitch claim moved, it did not disappear.** The defensible line is no longer "we chose not to build these"; it is "we built them as separate engines behind one contract, and we band their evidence honestly." That claim is only true if C-02 and C-03 hold — inventory findings must reach the database banded `UNVERIFIED`, not be dropped by the `scan_runner` gate and not be relabelled `high`. **If CONF does not land, this resolution must be reverted**, because the honesty table would then describe engines whose output either vanishes or overstates itself.
**Confidence:** **High** (decision made; no longer awaiting sign-off).

### C-21 · `install.sh` assumptions contradict two other features
**Shared resource:** `scripts/install.sh`, `/health` routing, the `ecdat` entrypoint
**Proposals:** INS, CLI, RBAC
**State:** Conflicting. INS assumes no `ecdat` PATH wrapper exists "since the README's `ecdat scan` executable doesn't exist" — while CLI is building exactly that via `pyproject.toml`. INS also needs RBAC's env vars and a first-run admin bootstrap that does not yet exist, and notes the README's `https://localhost:8443/health` reaches the dashboard SPA rather than the backend.
**Resolution:** The install script stays a **single static, idempotent `scripts/install.sh`**; the enrolment token is supplied at runtime via a CLI flag or environment variable, never templated into a generated script. CLI merges before INS so the installer can build and reference the `ecdat` entrypoint. RBAC publishes `AUTH_BOOTSTRAP_ADMIN_USERNAME` and a seed path that INS invokes. `GET /api/health` through the gateway becomes the documented healthcheck and the README is corrected.
**Rationale:** A static installer is cacheable, diffable and reviewable; dynamically generated shell scripts carrying credentials are neither, and a `--wait` healthcheck pointed at an SPA will report success while the backend is down.
**Confidence:** **High**
*Note: an earlier draft of this contract described ENR as proposing dynamically generated install scripts containing enrolment tokens. It does not — ENR proposes a separate `scanner/enroll_cli.py` entrypoint. That conflict was fabricated and has been removed.*

---

### C-22 · Audit hash chain under concurrent writes
**Shared resource:** `audit_events.prev_hash` / `entry_hash`
**Proposals:** AUD
**State:** Conflicting with the deployment model. Each row hashes its predecessor, but FastAPI serves concurrent requests against a pooled connection — two simultaneous inserts can read the same `prev_hash` and fork the chain, making verification fail for a reason unrelated to tampering.
**Resolution:** Serialise appends through a Postgres advisory lock held only for the insert, or derive the chain from `id` ordering with a periodic verification job rather than at write time.
**Rationale:** A tamper-evidence mechanism that produces false positives under normal load will be switched off within a week.
**Confidence:** **Medium**
**→ Needs sign-off:** (a) fail-closed or fail-open — does a failed audit write block the request? Recommended: fail-closed for mutations and exports, fail-open for reads. (b) retention period. (c) whether a hash chain alone is sufficient or events must also ship to an external write-once sink, which `docs/SECURE_DEPLOYMENT.md` may require.

---

### C-23 · Dependency, container and binary scanners will report the same library twice
**Shared resource:** `findings.package_name` / `package_version`, de-duplication
**Proposals:** DEP, CNT, BIN — BIN explicitly asks who owns the "library version" fact
**State:** Conflicting. A single `libcrypto` can surface as a locked dependency (DEP), an installed OS package (CNT) and a linked shared library (BIN) in one scan, producing three findings for one fact.
**Resolution:** The three columns in migration 003 are shared and owned by the DB lane; all three engines write them. De-duplication key: `(artifact_type, artifact_ref, package_ecosystem, package_name, package_version, algorithm)` — so the three findings are **retained as distinct evidence** rather than merged, because they are genuinely different observations, and the dashboard groups them by `package_name` for display.
**Rationale:** Merging at write time destroys the evidence distinction between "declared", "installed" and "linked", which is exactly the distinction a CBOM is supposed to preserve.
**Confidence:** **Medium**
**→ Needs sign-off:** whether the dashboard groups or lists these, and whether a grouped row's risk tier is the maximum of its members. Untested against real multi-engine output; nobody has run all three engines on one target yet.

---

### C-24 · Dark theme assumed, light theme shipped
**Shared resource:** `dashboard/src/index.css` token values
**Proposals:** TRD ("matching the current dark audit ledger styling"), FE ("security audit ledger" visual language), CMP
**State:** Conflicting with ground truth. The shipped theme is **light** — `color-scheme: light`, `--void: #FFF6F7`, brand `--cyan: #FF788D` ("Watermelon Pink"), `--purple: #1E532B` ("Deep Forest Green"). Three features are designing against a dark palette that does not exist.
**Resolution:** None applied. FE owns the decision; until it is made, no feature hardcodes colours of either polarity, which C-07 already enforces.
**Rationale:** Light-vs-dark is a brand decision with pitch consequences, not an integration one. Flagging it now is cheaper than three features building against the wrong palette and discovering it during demo prep.
**Confidence:** **Low — product/design decision.** Also unresolved: whether a light/dark toggle is in scope at all, which FE raised and nobody answered.

---

### C-25 · Fonts loaded from an external CDN
**Shared resource:** `dashboard/src/index.css` line 2
**Proposals:** FE (assumes self-hosting is mandatory per the no-egress principle)
**State:** Conflicting, pre-existing. `index.css` opens with `@import url('https://fonts.googleapis.com/…')`, which makes every dashboard load reach a third-party host — contradicting the "data never leaves your network" claim in `PRODUCT_DESCRIPTION.md` §2 and the strict CSP described in `ARCHITECTURE.md` §4.
**Resolution:** FE self-hosts Inter and JetBrains Mono as `.woff2` under `dashboard/public/fonts/`, replaces the `@import` with `@font-face`, and the CSP drops any font-src exception. The existing `tailwind.config.js` family stacks already name both fonts, so no component changes.
**Rationale:** An air-gap claim that a browser request quietly breaks is the kind of thing a judge finds by opening devtools.
**Confidence:** **High**

---

### C-26 · Compatible, recorded for completeness
| Shared resource | Proposals | Why compatible |
|---|---|---|
| `Finding` dataclass as the sole scanner→backend contract | DEP, CNT, BIN, IAC | All four independently agreed to emit `Finding` unchanged in shape; only CONF adds fields, once |
| CLI subcommand structure | CLI + the four engines | Subcommands are verbs (`scan`/`cbom`/`sync`), engines are flags — no namespace overlap |
| Read-only aggregation over `findings` / `risk_assessments` | TRD, CMP, ASP | All three are strictly read-side, no writes, no schema changes beyond indexes |
| Agent report-sync path (mTLS + Ed25519) | RBAC, ENR, AUD | RBAC explicitly leaves it untouched; ENR changes key *resolution*, not the protocol |
| `scanner/rules/*.yaml` loader | CNT, BIN, IAC | `multilang_engine.load_rules` already loads any `*.yaml` with `language:` + `rules:` keys |

---

## 5. Shared Resource Index

Every resource touched by more than one proposal. `!` marks a resource with an open Medium or Low item.

### 5.1 Files

| Resource | Features | State | Ref |
|---|---|---|---|
| `scanner/cli.py` | DEP CNT BIN IAC CONF | Conflicting ! | C-11 |
| `scanner/constants.py` | CNT BIN IAC CONF | Conflicting | C-12 |
| `scanner/finding.py` | DEP CNT BIN CONF | Conflicting ! | C-03 |
| `scanner/python_engine.py`, `multilang_engine.py` | CNT CONF | Compatible | C-03 |
| `api/services/scan_runner.py` | DEP CNT BIN IAC CONF | Conflicting ! | C-02 |
| `api/services/cbom_generator.py` | CNT BIN IAC CONF CLI CBV | Conflicting ! | C-14 |
| `api/services/risk_engine.py` | CNT IAC CONF TRD CMP | Conflicting ! | C-04 |
| `api/routers/findings.py` | CONF DFS TRI RBAC | Conflicting ! | C-16 |
| `api/routers/scans.py` | CNT RBAC AUD | Conflicting | C-09 |
| `api/routers/cbom.py` | CBV RBAC AUD | Compatible | C-14 |
| `api/routers/agents.py` | ENR ASP | Conflicting | C-05 |
| `api/models.py` | DEP CNT CONF ENR ASP AUD CMP | Conflicting | §1.2 |
| `api/core/security.py` | RBAC ENR AUD | Conflicting ! | C-09 |
| `api/main.py`, `api/core/config.py` | RBAC ENR AUD | Conflicting | C-09 |
| `db/schema.sql`, `db/models.py` | DEP CNT CONF ENR RBAC AUD TRI DFS | Conflicting | §2 |
| `db/crud.py` | DEP CONF ENR RBAC AUD ASP CMP TRI | Conflicting ! | C-10 |
| `db/migrations/002_*.sql` | CNT CONF ENR RBAC AUD | Conflicting | C-01 |
| `db/seed.py` | CONF RBAC | Compatible | — |
| `dashboard/src/components/FindingsTable.jsx` | CNT BIN IAC CONF DFS TRI FE | Conflicting ! | C-13 |
| `dashboard/src/lib/api.js` + `src/api.js` | RBAC ASP CMP DFS TRI | Conflicting ! | C-08 |
| `dashboard/src/index.css`, `tailwind.config.js` | FE TRD CMP DFS | Conflicting ! | C-07, C-24, C-25 |
| `dashboard/src/App.jsx` | ASP TRD DFS FE | Compatible | §1.4 |
| `dashboard/src/pages/DashboardPage/index.jsx` | CONF CMP DFS | Conflicting | C-13 |
| `dashboard/src/lib/constants.js` | CNT CONF DFS | Conflicting | C-13 |
| `requirements.txt` | BIN IAC RBAC CLI CNT CBV | Conflicting ! | C-18 |
| `docker-compose.yml` | CNT RBAC AUD CLI INS | Conflicting | C-01 |
| `Dockerfile` | CNT CLI | Compatible | — |
| `deploy/nginx/nginx.conf` | ENR AUD INS | Compatible | — |
| `.env.example` | ENR RBAC CONF AUD INS | Compatible | §3.3 |
| `.github/workflows/ecdat-scan.yml` | CNT IAC CLI | Compatible | — |
| `PRODUCT_DESCRIPTION.md` | CNT BIN IAC CONF CMP | Conflicting ! | C-19, C-20 |
| `docs/ECDAT_CLI_GUIDE.md` | CNT BIN IAC CLI INS ENR | Conflicting | C-11 |
| `docs/SECURE_DEPLOYMENT.md` | INS ENR AUD | Compatible | — |
| `ARCHITECTURE.md`, `README.md` | BIN CONF INS | Conflicting | C-19 |
| `tests/test_crud.py`, `test_scanner_battle.py`, `test_realworld_source_scanner.py` | CONF | Breaking ! | C-03 |
| `tests/test_security_controls.py` | RBAC | Breaking ! | C-09 |
| `tests/test_scan_runner.py` | DEP CONF | Conflicting | C-02 |

### 5.2 Database

| Resource | Features | State | Ref |
|---|---|---|---|
| `findings` (columns) | DEP CNT CONF TRI BIN | Conflicting | §2.2 |
| `findings.confidence` | CONF CNT BIN IAC | Conflicting ! | C-03 |
| `findings.source_context` | CNT BIN IAC | Conflicting | §2.2 |
| `findings` (indexes) | DFS TRD | Compatible | §2.2 |
| `scans` | CNT TRD ASP | Compatible | §2.2 |
| `risk_assessments` | CONF TRD CMP | Read-only for all | C-04 |
| `reports` | ENR ASP AUD | Compatible | C-06 |
| `users` (new) | RBAC ENR AUD TRI | Compatible | §2.2 |
| `agents`, `enrollment_tokens` (new) | ENR ASP | Compatible | C-05 |
| `audit_events` (new) | AUD RBAC ENR | Compatible ! | C-22 |
| `finding_triage` (new) | TRI | Conflicting ! | C-15 |
| `organization_id` (scoping) | RBAC ASP ENR AUD CMP TRD | Conflicting ! | C-10 |

### 5.3 API endpoints

| Endpoint | Features | State | Ref |
|---|---|---|---|
| `GET /scans/{scan_id}/findings` | DFS CONF TRI RBAC | Conflicting ! | C-16 |
| `GET /scans/{scan_id}` | CMP RBAC AUD | Compatible | — |
| `POST /scans` | CNT RBAC AUD | Compatible | — |
| `GET /scans/{scan_id}/cbom` | CBV RBAC AUD | Compatible | C-14 |
| `GET /scans/health` vs `GET /health` vs `/api/health` | INS | Conflicting | C-21 |
| `GET /agents` (new) | ENR ASP | Conflicting | C-05 |
| `POST /agent/v1/enroll` (new) | ENR | Sole | — |
| `POST /auth/login` (new) | RBAC INS | Compatible | C-09 |
| `GET /audit/events` (new) | AUD | Sole | — |
| `PATCH /scans/{id}/findings/{fid}/triage` (new) | TRI | Sole | C-16 |
| `GET /trends` (new) | TRD | Sole | — |
| `GET /compliance` (new, conditional) | CMP | Sole | — |

### 5.4 CLI flags and environment variables

| Resource | Features | State | Ref |
|---|---|---|---|
| `--target-type` / `--image-tar` / `--binaries` / `--scan-type` | CNT BIN IAC DEP | Conflicting ! | C-11 |
| `--min-confidence` | CONF | Sole | C-03 |
| `--fail-on` (existing) | CONF TRI BIN | Conflicting ! | C-03 |
| `REPORT_SYNC_AGENT_KEYS` | ENR | Deprecated-in-place ! | C-26 note |
| `API_KEY` / `X-API-Key` | RBAC ENR AUD INS | Conflicting ! | C-09 |
| `VITE_API_KEY` | RBAC FE | Conflicting | C-08 |
| New `AUTH_*` / `AGENT_ENROLLMENT_*` / `SCAN_*` / `AUDIT_*` | RBAC ENR CONF AUD INS | Compatible | §3.3 |

---

## 6. Merge Order

Ordering is derived from the resolutions above. Items in the same wave may proceed in parallel.

| Wave | Merge | Unblocks |
|---|---|---|
| **0** | Add `cryptography>=46.0.0` to `requirements.txt`; delete `dashboard/src/api.js`; add `AGENTS.md` | Everything (C-18, C-08) |
| **0** | ~~Human sign-off on C-20~~ — **RESOLVED**, all four engines in scope | CNT, BIN, IAC, DEP cleared to start |
| **1** | RBAC (`Principal` contract, `users`, `require_role`) | ENR, AUD, ASP, INS, all analyst routes (C-09) |
| **1** | CONF phase 1 (signals, scorer, DB, CLI) | DEP, CNT, BIN, IAC (C-02, C-03) |
| **1** | `cbom_generator` refactor to `build_cbom_from_findings` | CLI, CBV, CNT, BIN, IAC (C-14) |
| **2** | CLI wrapper; `scanner/cli.py` `--scan-type` flag | INS, the four engines (C-11, C-21) |
| **2** | ENR (`agents`, `enrollment_tokens`, `api/routers/agents.py`) | ASP (C-05) |
| **2** | AUD | — |
| **2** | DFS (`FindingsTable` column registry + server-side filter/sort) | CNT, BIN, IAC, CONF, TRI, FE table work (C-13) |
| **3** | DEP · CNT · BIN · IAC (migration 003 as **one** shared PR) | — |
| **3** | FE (tokens, self-hosted fonts, motion) | CMP, TRD presentation (C-07, C-25) |
| **3** | CBV · ASP · INS | — |
| **4** | TRI · CMP · TRD | — |
| **4** | Single scope-truth documentation pass | — (C-19) |

---

## 7. Open Items Requiring Human Sign-Off

Nothing below is decided. Each blocks the listed features.

| # | Question | Blocks | Confidence |
|---|---|---|---|
| C-24 | Light or dark dashboard theme; is a toggle in scope? | FE TRD CMP | **Low** |
| C-06 | Time window separating `recent` from `stale` agent delivery | ASP | **Low** |
| C-02 | Persist or drop sub-threshold findings? | all scanners | **Medium** |
| C-03 | Confidence backfill, broken tests, demo baseline, `--fail-on` interaction | CONF + 6 | **Medium** |
| C-04 | Do trends pin to `risk_model_version` or always show latest? | TRD | **Medium** |
| C-08 | JWT in `localStorage` or httpOnly cookie? | RBAC | **Medium** |
| C-09 | Does `X-API-Key` survive for CLI/service callers? | RBAC CI ENR | **Medium** |
| C-10 | Tenant visibility for NULL `organization_id` rows | RBAC ASP CMP | **Medium** |
| C-11 | Final CLI flag grammar; does bare `ecdat TARGET` survive? | CLI + 4 engines | **Medium** |
| C-13 | Is the `FindingsTable` restructure in DFS's sprint scope? | 5 features | **Medium** |
| C-14 | CBOM validation failure: 500 or 200-with-warning? Full 1.6 schema or subset? | CBV | **Medium** |
| C-15 | Exact finding fingerprint inputs | TRI | **Medium** |
| C-16 | Can compliance filters share the standard query semantics? | CMP DFS | **Medium** |
| C-18 | `lief` (native parser on untrusted input) vs pure-Python fallback | BIN | **Medium** |
| C-22 | Audit fail-closed vs fail-open; retention; external sink? | AUD | **Medium** |
| C-23 | Group or list duplicate package findings across engines | DEP CNT BIN | **Medium** |

---

## 8. Changes from the previous draft

Recorded so reviewers do not reintroduce them.

| Previous draft | Corrected to | Why |
|---|---|---|
| `cli/main.go`, Go subcommands | `scanner/cli.py` (argparse), `scanner/ecdat_cli.py` | The project is Python 3.11; there is no Go anywhere in it |
| `CalculateECDATScore()` | `calculate_confidence_score()` | Python naming; PascalCase functions do not exist in this codebase |
| `/api/v1/scans`, `/api/v1/scan-results`, `/api/v1/agents` | `/scans`, `/agent/v1/*` | The shipped routers are unversioned; `/api/v1` would break gateway, dashboard, CI and CLI at once |
| `--sys-color-primary` token namespace | Existing `--void`/`--surface`/`--cyan`/`--t1` tokens | Renaming invalidates every Tailwind utility class already in use |
| `scans` + `scan_results` with polymorphic `scan_category` ENUM | Existing `findings` table + `findings.artifact_type` TEXT | The table is `findings`; one scan mixes artefact types, so the axis is per-finding; native ENUMs require `ALTER TYPE` to extend |
| UUID primary keys throughout | `SERIAL` / `BIGSERIAL` | Matches `db/schema.sql` and `db/models.py` |
| `roles` table with `users.role_id` | `users.role` TEXT + code-resident permission map | RBAC deliberately keeps the map in `api/core/rbac.py` for reviewability |
| `scan_results.triage_status`, `scan_results.confidence_score` | `finding_triage` table; `findings.confidence_score` | Triage must not mutate immutable evidence, and must survive re-scan |
| `cbom_exports` table | No table; generate on demand | Persisting exports creates the second source of truth CBV exists to prevent |
| `agents.status` + `last_seen_at` as one liveness field | `registry_status` + derived `delivery_status` | No heartbeat channel exists; conflating them produces a misleading dashboard |
| "Shared query-parameter parsing **middleware**" | Shared FastAPI `Depends()` dependency | Middleware bypasses Pydantic validation and never appears in the OpenAPI schema |
| ENR proposes dynamically generated install scripts containing enrolment tokens | ENR proposes `scanner/enroll_cli.py` | That conflict did not exist in any proposal; the static-installer resolution is retained under C-21 on its own merits |
| 6 conflicts, no file-path grounding | 26 conflicts, verified against the repository | Migration collision, confidence gate, vocabulary drift, duplicate `agents.py`, duplicate API clients, unpinned `cryptography`, CDN fonts, triage/re-scan loss and the scope contradiction were all unreported |
