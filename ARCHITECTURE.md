# ECDAT Architecture & System Design

Enterprise Cryptographic Discovery & Assessment Tool (ECDAT) — Architectural Source of Truth.

---

## 1. Repository Directory Structure & Component Status

Legend:
- ✅ **Built** (Existing active codebase)
- 🚧 **Placeholder** (File initialized with specification header and TODOs)
- ❌ **Not started** (Planned component, not yet scaffolded)

```text
ECDAT/
├── .github/
│   └── workflows/
│       └── ecdat-scan.yml                     ✅ [Built] CI/CD compliance gate workflow
├── api/
│   ├── __init__.py                            ✅ [Built] Package init
│   ├── database.py                            ✅ [Built] Database session & connection helpers
│   ├── main.py                                ✅ [Built] FastAPI app entrypoint & middleware
│   ├── models.py                              ✅ [Built] Pydantic schemas
│   ├── core/
│   │   ├── __init__.py                        ✅ [Built] Package init
│   │   ├── config.py                          ✅ [Built] Pydantic-settings environment configuration
│   │   └── security.py                        ✅ [Built] X-API-Key header auth & validation
│   ├── routers/
│   │   ├── __init__.py                        ✅ [Built] Package init
│   │   ├── cbom.py                            ✅ [Built] GET /scans/{id}/cbom
│   │   ├── findings.py                        ✅ [Built] GET /scans/{id}/findings (paginated)
│   │   ├── remediation.py                     ✅ [Built] GET /scans/{id}/remediation/{finding_id}
│   │   └── scans.py                           ✅ [Built] POST /scans, GET /scans/{id}, GET /health
│   └── services/
│       ├── __init__.py                        ✅ [Built] Package init
│       ├── cbom_generator.py                  ✅ [Built] CycloneDX 1.6 CBOM transform
│       ├── risk_engine.py                     ✅ [Built] Quantum-aware risk scoring & Mosca model
│       └── scan_runner.py                     ✅ [Built] Async scanner execution & ingestion
├── dashboard/
│   ├── README-frontend.md                     ✅ [Built] Frontend guide
│   ├── index.html                             ✅ [Built] HTML entry point
│   ├── package.json                           ✅ [Built] Dependencies & scripts
│   ├── package-lock.json                      ✅ [Built] Dependency lockfile
│   ├── vite.config.js                         ✅ [Built] Vite dev server & build configuration
│   └── src/
│       ├── App.jsx                            ✅ [Built] Main dashboard layout
│       ├── api.js                             🚧 [Placeholder] Axios client with API key auth
│       ├── main.jsx                           ✅ [Built] React DOM entry point
│       ├── mockData.js                        ✅ [Built] Development mock findings & summaries
│       └── components/
│           ├── CBOMViewer.jsx                 ✅ [Built] CycloneDX CBOM JSON/tree viewer
│           ├── CbomExport.jsx                 🚧 [Placeholder] CBOM download action button
│           ├── ChartsPanel.jsx                🚧 [Placeholder] Recharts breakdown panel
│           ├── ConfidenceStamp.jsx            🚧 [Placeholder] AST validation status stamp
│           ├── FindingsTable.jsx              ✅ [Built] Interactive findings data grid
│           ├── RiskBadge.jsx                  🚧 [Placeholder] Severity/risk-tier pill
│           ├── RiskChart.jsx                  ✅ [Built] Distribution chart
│           └── StatCards.jsx                  🚧 [Placeholder] 4-card metric summary header
├── db/
│   ├── README.md                              ✅ [Built] Database layer documentation
│   ├── __init__.py                            ✅ [Built] Package init
│   ├── crud.py                                ✅ [Built] Centralized SQLAlchemy 2.0 query layer
│   ├── models.py                              ✅ [Built] Canonical ORM models (Repository, Scan, Finding)
│   ├── schema.sql                             ✅ [Built] Canonical PostgreSQL schema
│   └── seed.py                                ✅ [Built] Database seeding script
├── docs/
│   ├── clinerules.txt                         ✅ [Built] Agent operational rules
│   ├── PROMPT_RESTRUCTURE_AGENT.md            ✅ [Built] Restructuring specification
│   ├── RISK_ENGINE_SPEC.md                    ✅ [Built] Quantum risk calculation engine spec
│   ├── SKILL_GENERATE_AUDIT.md                ✅ [Built] Audit skill reference
│   └── SKILL_SCANNER_FIXES.md                 ✅ [Built] Scanner bugfix guide
├── scanner/
│   ├── __init__.py                            ✅ [Built] Package init
│   ├── cli.py                                 ✅ [Built] Command-line interface for scanner
│   ├── finding.py                             ✅ [Built] Finding dataclass definition
│   ├── multilang_engine.py                    ✅ [Built] Tree-sitter engine for Java, JS/TS, Go, C/C++
│   ├── python_engine.py                       ✅ [Built] AST visitor for Python cryptography
│   └── rules/                                 ✅ [Built] Detection rules & patterns
├── scripts/
│   └── generate_demo_repo.py                  🚧 [Placeholder] Multi-language vulnerable demo repo
├── skills/
│   ├── ast-crypto-scanning/SKILL.md           ✅ [Built] AST detection patterns skill
│   ├── backend/SKILL.md                       ✅ [Built] Backend API development skill
│   ├── cbom-quantum-risk/SKILL.md             ✅ [Built] CBOM & quantum risk engine skill
│   ├── ci-cd-gate/SKILL.md                    ✅ [Built] CI/CD gate action & exit-codes skill
│   ├── db/SKILL.md                            ✅ [Built] Database & ORM standards skill
│   ├── frontend/SKILL.md                      ✅ [Built] React dashboard development skill
│   ├── remediation-copy/SKILL.md              ✅ [Built] Remediation & LLM prompt skill
│   ├── scanner/SKILL.md                       ✅ [Built] Core scanner CLI skill
│   └── secure-api-development/SKILL.md        ✅ [Built] Secure API implementation skill
├── tests/
│   ├── __init__.py                            ✅ [Built] Test package init
│   ├── conftest.py                            ✅ [Built] Pytest fixtures & in-memory SQLite DB
│   ├── test_api.py                            ✅ [Built] API route tests
│   ├── test_crud.py                           ✅ [Built] Database CRUD integration tests
│   ├── test_llm.py                            ✅ [Built] Gemini remediation tests
│   ├── test_remediation.py                    ✅ [Built] Remediation router tests
│   └── test_remediation_table.py              ✅ [Built] Static fix table lookup tests
├── .clinerules                                ✅ [Built] Global workspace instructions
├── .dockerignore                              ✅ [Built] Docker build ignore list
├── .env.example                               ✅ [Built] Environment variable template
├── .gitignore                                 ✅ [Built] Git ignore configuration
├── AGENTS_AND_SKILLS.md                       ✅ [Built] Team skill assignments & ownership registry
├── ARCHITECTURE.md                            ✅ [Built] Architecture source of truth (this document)
├── CODEBASE_AUDIT.md                          ✅ [Built] Codebase health audit & remediation log
├── Dockerfile                                 ✅ [Built] Multi-stage container definition
├── docker-compose.yml                         ✅ [Built] Multi-service orchestration (Postgres, API, Dashboard)
├── main.py                                    ✅ [Built] Root run helper
├── PRODUCT_DESCRIPTION.md                     ✅ [Built] Product specification & value proposition
├── PROMPT_FIX_ARCHITECTURE.md                 ✅ [Built] Architecture cleanup instructions
├── README.md                                  ✅ [Built] Project overview & quickstart
├── remediation_table.py                       ✅ [Built] Deterministic cryptographic migration map
└── requirements.txt                           ✅ [Built] Python package dependencies
```

---

## 2. Component Contracts & Data Flow

```mermaid
flowchart TD
    subgraph Client / CI
        CLI["Scanner CLI / CI Action<br/>(scanner/cli.py)"]
        Dashboard["React Dashboard<br/>(dashboard/src/)"]
    end

    subgraph API Layer ["FastAPI Backend (api/)"]
        Auth["X-API-Key Auth<br/>(api/core/security.py)"]
        RouterScans["Scans Router<br/>(api/routers/scans.py)"]
        RouterFindings["Findings Router<br/>(api/routers/findings.py)"]
        RouterCBOM["CBOM Router<br/>(api/routers/cbom.py)"]
        RouterRemediation["Remediation Router<br/>(api/routers/remediation.py)"]
        
        ScanRunner["Scan Runner Service<br/>(api/services/scan_runner.py)"]
        RiskEngine["Risk Engine Service<br/>(api/services/risk_engine.py)"]
        CBOMGen["CBOM Generator Service<br/>(api/services/cbom_generator.py)"]
    end

    subgraph Database Layer ["Database (db/)"]
        CRUD["Data Access Layer<br/>(db/crud.py)"]
        DB[(PostgreSQL / SQLite<br/>db/schema.sql)]
    end

    subgraph External
        Gemini["Google Gemini 1.5 Flash<br/>(Remediation Guidance)"]
    end

    CLI -->|POST /scans<br/>Target Repo Path| RouterScans
    RouterScans --> Auth
    RouterScans -->|Background Task| ScanRunner
    ScanRunner -->|Run Subprocess| CLI
    ScanRunner -->|Ingest Raw Findings| RiskEngine
    RiskEngine -->|Enriched Findings| CRUD
    CRUD --> DB

    Dashboard -->|GET /scans/{id}| RouterScans
    Dashboard -->|GET /scans/{id}/findings| RouterFindings
    Dashboard -->|GET /scans/{id}/cbom| RouterCBOM
    Dashboard -->|GET /scans/{id}/remediation/{fid}| RouterRemediation

    RouterFindings --> CRUD
    RouterCBOM --> CRUD
    RouterCBOM --> CBOMGen
    RouterRemediation --> Gemini
```

### 2.1 Scanner → API Contract
1. Scanner produces findings structured according to `scanner.finding.Finding`:
   - `file`: Path to source file containing cryptography
   - `line`: Line number of detection (1-indexed)
   - `algorithm`: Canonical algorithm name (e.g., `MD5`, `RSA`, `AES-128-CBC`)
   - `key_size`: Key/modulus size in bits (if extractable)
   - `confidence`: Detection certainty (`high`, `medium`, `low`)
2. `api/services/scan_runner.py` runs the scan, processes output into `db.crud.save_findings()`, and invokes `api.services.risk_engine.py` to annotate each finding with:
   - `risk_tier`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
   - `risk_reason`: Contextual quantum/classical vulnerability explanation
   - `criticality`: Business asset impact level

### 2.2 API → Database Contract
- All database operations route strictly through `db/crud.py`.
- Foreign key cascading is maintained (`repositories` → `scans` → `findings`).
- Schema definitions in `db/models.py` strictly align with `db/schema.sql`.

### 2.3 API → Dashboard Contract
- **Scan Creation**: `POST /scans` returns `202 Accepted` with `{ "scan_id": int, "status": "running" }`.
- **Scan Details**: `GET /scans/{id}` returns scan metadata, findings collection, and aggregate risk counts.
- **Findings Query**: `GET /scans/{id}/findings?risk_tier=HIGH&limit=50&offset=0` supports pagination and filtering.
- **CBOM Export**: `GET /scans/{id}/cbom` dynamically produces CycloneDX 1.6 JSON containing cryptographic asset components.
- **Remediation**: `GET /scans/{id}/remediation/{finding_id}` returns remediation advice with LLM or static fallback indicator.

---

## 3. Technology Stack

| Component | Technology | Version / Standard | Notes |
|---|---|---|---|
| **Backend Framework** | FastAPI | >= 0.110.0 | High-performance async REST API |
| **Data Validation** | Pydantic | v2 (`from_attributes=True`) | Strict schema models and environment settings |
| **ORM & DB Access** | SQLAlchemy | 2.0+ (Mappe[T], mapped_column) | Dual support for SQLite (dev/test) & PostgreSQL (prod) |
| **Database** | PostgreSQL | 15+ | Relational persistence with cascade delete constraints |
| **Scanner Engines** | Python AST & Tree-Sitter | Python 3.10+ / Tree-sitter 0.21+ | Multi-language static cryptographic discovery |
| **Frontend Framework** | React + Vite | React 18+ / Vite 5+ | SPA with fast hot module replacement |
| **Data Visualization** | Recharts & Lucide React | Latest | Interactive charts & UI iconography |
| **BOM Standard** | CycloneDX | Spec 1.6 (cbom draft) | Cryptographic Bill of Materials standard |
| **AI Remediation** | Google Gemini API | `gemini-1.5-flash` | Generative PR comments with static deterministic fallback |
| **Containerization** | Docker & Docker Compose | Compose v2 | Multi-container deployment (Postgres, API, Dashboard) |

---

## 4. Security Posture Summary

1. **Authentication & Authorization**:
   - API endpoints require an `X-API-Key` header validated against configured server secrets.
   - Timing-safe comparison is employed to prevent side-channel timing attacks.
2. **Subprocess & Path Sanitization**:
   - `scan_runner.py` enforces absolute filesystem path validation within allowed directories to prevent path traversal attacks.
   - Scanner commands are invoked with parameter arrays (`shell=False`) to eliminate shell injection vulnerabilities.
3. **Information Disclosure Prevention**:
   - Global exception handlers intercept unexpected errors and return sanitized error responses without leaking internal stack traces or database schema details.
4. **Deterministic Fallbacks**:
   - AI remediation queries always default safely to local rule-based tables (`remediation_table.py`) when external network access or LLM API keys are unavailable.

---

## 5. Work Assignment & Ownership Matrix

| Area | Primary Owner | Secondary Owner | Associated Skill File | Status |
|---|---|---|---|---|
| **Database & Models** | Ronak | Team | [skills/db/SKILL.md](skills/db/SKILL.md) | ✅ Active |
| **Backend API & Core** | Shreyanshi | Ronak | [skills/backend/SKILL.md](skills/backend/SKILL.md) | ✅ Active |
| **Frontend Dashboard** | Karan | Satyam | [skills/frontend/SKILL.md](skills/frontend/SKILL.md) | ✅ Active |
| **Scanner Engine** | Shashank | Team | [skills/scanner/SKILL.md](skills/scanner/SKILL.md) | ✅ Active |
| **CBOM & Quantum Risk Engine** | Maitreyi | Shashank | [skills/cbom-quantum-risk/SKILL.md](skills/cbom-quantum-risk/SKILL.md) | ✅ Active |
| **CI/CD Quality Gate** | Shashank | Team | [skills/ci-cd-gate/SKILL.md](skills/ci-cd-gate/SKILL.md) | ✅ Active |
| **Remediation & LLM Copy** | Shreyanshi | Team | [skills/remediation-copy/SKILL.md](skills/remediation-copy/SKILL.md) | ✅ Active |
