# ECDAT Architecture & System Design

Enterprise Cryptographic Discovery & Assessment Tool (ECDAT) — Architectural Source of Truth.
Smart India Hackathon 2026 · Problem Statement PS 26164 · Team **ctrl-Nix**

---

## 1. Repository Directory Structure & Component Status

> **Note on Audit Currency:** Previous audit documents (such as `CODEBASE_AUDIT.md`) reflected an early development snapshot where `multilang_engine.py` was empty and `api/` was partially structured. The tree below reflects the **current, active codebase** as of September 2026.

Legend:
- ✅ **Built** (Fully implemented and functional in active codebase)
- 🚧 **In Progress / Stubbed** (Scaffolded, partial implementation, demo mode, or explicit TODO stub)
- ❌ **Planned / Out of Scope** (Architecture accounts for it, but not implemented in current phase)

```text
ECDAT/
├── .github/
│   └── workflows/
│       └── ecdat-scan.yml                     ✅ [Built] GitHub Actions CI/CD compliance gate workflow
├── api/
│   ├── __init__.py                            ✅ [Built] Package marker
│   ├── database.py                            ✅ [Built] Engine creation, connection pooling, session lifecycle
│   ├── main.py                                ✅ [Built] FastAPI entrypoint, security headers & payload limit middleware
│   ├── models.py                              ✅ [Built] Pydantic v2 schemas (FindingOut, ScanWithFindings, RemediationOut, etc.)
│   ├── core/
│   │   ├── __init__.py                        ✅ [Built] Package marker
│   │   ├── config.py                          ✅ [Built] Pydantic-settings environment configuration
│   │   └── security.py                        ✅ [Built] X-API-Key validation & mTLS agent authentication
│   ├── routers/
│   │   ├── __init__.py                        ✅ [Built] Package marker
│   │   ├── cbom.py                            ✅ [Built] GET /scans/{scan_id}/cbom (CycloneDX 1.6 export)
│   │   ├── findings.py                        ✅ [Built] GET /scans/{scan_id}/findings, GET .../{finding_id}
│   │   ├── remediation.py                     ✅ [Built] GET /scans/health, GET .../remediation/{finding_id}, POST .../remediation/generate
│   │   ├── report_sync.py                     ✅ [Built] POST /agent/v1/report-bundles (mTLS intake for signed scanner bundles)
│   │   └── scans.py                           ✅ [Built] POST /scans, GET /scans, GET /scans/{scan_id}
│   └── services/
│       ├── __init__.py                        ✅ [Built] Package marker
│       ├── cbom_generator.py                  ✅ [Built] CycloneDX 1.6 CBOM transform & cryptographic-asset builder
│       ├── report_bundle.py                   ✅ [Built] Canonical JSON digest computation, Ed25519 signing & verification
│       ├── risk_engine.py                     ✅ [Built] Quantum-aware risk engine (two-axis scoring, Mosca's theorem adaptation)
│       └── scan_runner.py                     ✅ [Built] Background subprocess scanner runner & path sanitizer
├── dashboard/
│   ├── .dockerignore                          ✅ [Built] Dashboard container build ignore list
│   ├── Dockerfile                             ✅ [Built] Multi-stage Nginx container for dashboard SPA
│   ├── README-frontend.md                     ✅ [Built] Frontend documentation
│   ├── index.html                             ✅ [Built] HTML5 entry point
│   ├── nginx.conf                             ✅ [Built] Frontend Nginx server configuration
│   ├── package.json                           ✅ [Built] React dependencies & build scripts
│   ├── postcss.config.js                      ✅ [Built] PostCSS configuration
│   ├── tailwind.config.js                     ✅ [Built] Tailwind CSS design tokens
│   ├── vite.config.js                         ✅ [Built] Vite dev server & build configuration
│   └── src/                                   🚧 [In Progress] React SPA (components built; operates in demo/mock mode with mockData.js pending live gateway hookup)
├── db/
│   ├── README.md                              ✅ [Built] Database architecture & developer notes
│   ├── __init__.py                            ✅ [Built] Package marker exposing CRUD, models, and helpers
│   ├── crud.py                                ✅ [Built] Centralized SQLAlchemy 2.0 data-access layer
│   ├── models.py                              ✅ [Built] Declarative ORM models (Repository, Scan, Finding, RiskAssessment, Report)
│   ├── schema.sql                             ✅ [Built] Canonical PostgreSQL schema with cascade rules & indexes
│   ├── seed.py                                ✅ [Built] Database seed script for development & testing
│   └── migrations/
│       └── 001_secure_reporting.sql           ✅ [Built] PostgreSQL migration for risk_assessments & signed reports tables
├── deploy/
│   ├── nginx/
│   │   └── nginx.conf                         ✅ [Built] Edge reverse proxy with mTLS client verification & routing
│   └── tls/
│       └── README.md                          ✅ [Built] Guidance for provisioning TLS server & agent CA certificates
├── docs/
│   ├── DASHBOARD_IMPROVEMENT_REVIEW.md        ✅ [Built] Frontend audit & design review
│   ├── DEMONSTRATION_GUIDE.md                 ✅ [Built] Step-by-step hackathon judge demo walkthrough
│   ├── ECDAT_CLI_GUIDE.md                     ✅ [Built] Complete CLI command, flag, and usage guide
│   ├── RISK_ENGINE_SPEC.md                    ✅ [Built] Detailed specification of quantum risk calculation rules
│   ├── SECURE_DEPLOYMENT.md                   ✅ [Built] Production hardening & deployment documentation
│   ├── SOURCE_SCANNING_SCOPE.md               ✅ [Built] Source-code scanning rationale vs. binary scanners
│   └── examples/
│       └── github-actions-ecdat-policy.yml    ✅ [Built] Reference workflow for CI gate integration
├── scanner/
│   ├── README.md                              ✅ [Built] Scanner overview
│   ├── __init__.py                            ✅ [Built] Package marker exposing scan API
│   ├── cli.py                                 ✅ [Built] CLI with local scan, --fail-on policy, Ed25519 signing & mTLS sync
│   ├── constants.py                           ✅ [Built] Ignored directories, file skip predicates, and limits
│   ├── finding.py                             ✅ [Built] Shared canonical Finding dataclass
│   ├── multilang_engine.py                    ✅ [Built] Tree-sitter engine for Java, JS, and TS/TSX with import resolution
│   ├── python_engine.py                       ✅ [Built] AST visitor for Python cryptography detection with alias tracking
│   └── rules/
│       ├── java.yaml                          ✅ [Built] Cryptographic detection rules for Java (JCA, BouncyCastle)
│       └── javascript.yaml                    ✅ [Built] Cryptographic detection rules for Node.js & Web Crypto
├── scripts/
│   └── generate_demo_repo.py                  🚧 [Stubbed] 4-line placeholder script with TODO comment for mock repo generation
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
├── tests/                                     ✅ [Built] Test suite (API, CRUD, LLM fallback, remediation tables)
├── .clinerules                                ✅ [Built] Agent operational rules & workflow constraints
├── .dockerignore                              ✅ [Built] Root Docker build ignore list
├── .env.example                               ✅ [Built] Environment variable template
├── .gitignore                                 ✅ [Built] Git ignore configuration
├── AGENTS_AND_SKILLS.md                       ✅ [Built] Team skill assignments & ownership registry
├── ARCHITECTURE.md                            ✅ [Built] Architecture source of truth (this document)
├── CODEBASE_AUDIT.md                          ✅ [Built] Historical codebase audit (retained for audit record)
├── conftest.py                                ✅ [Built] Pytest root path initialization
├── Dockerfile                                 ✅ [Built] Hardened, unprivileged backend container
├── docker-compose.yml                         ✅ [Built] Multi-service orchestration (db, backend, dashboard, gateway)
├── main.py                                    ✅ [Built] Root runner for local backend execution
├── PRODUCT_DESCRIPTION.md                     ✅ [Built] Product specification, pitch context & SIH 26164 alignment
├── README.md                                  ✅ [Built] Project overview, PS 26164 framing & status
├── remediation_table.py                       ✅ [Built] Deterministic cryptographic migration & criticality map
└── requirements.txt                           ✅ [Built] Root Python package dependencies
```

---

## 2. Component Contracts & Data Flow

```mermaid
flowchart TD
    subgraph Clients ["Scanner Clients & CI"]
        CLI["Scanner CLI / CI Gate<br/>(scanner/cli.py)"]
        SignedBundle["Signed Report Bundle<br/>(Ed25519 + SHA-256)"]
    end

    subgraph Edge ["TLS Gateway (deploy/nginx/nginx.conf)"]
        Gateway["Nginx Gateway (:8443)<br/>mTLS Client Cert Verification"]
    end

    subgraph Backend ["FastAPI Backend (api/)"]
        Security["Auth & Security Middleware<br/>(api/core/security.py)"]
        RouterSync["Report Sync Router<br/>(POST /agent/v1/report-bundles)"]
        RouterScans["Scans Router<br/>(POST/GET /scans)"]
        RouterFindings["Findings Router<br/>(GET /scans/{id}/findings)"]
        RouterCBOM["CBOM Router<br/>(GET /scans/{id}/cbom)"]
        RouterRemediation["Remediation Router<br/>(GET /scans/{id}/remediation/{fid})"]

        ScanRunner["Scan Runner Service<br/>(api/services/scan_runner.py)"]
        RiskEngine["Risk Engine Service<br/>(api/services/risk_engine.py)"]
        CBOMGen["CBOM Generator Service<br/>(api/services/cbom_generator.py)"]
        BundleVerifier["Bundle Verifier<br/>(api/services/report_bundle.py)"]
    end

    subgraph DB ["Database (PostgreSQL / SQLite)"]
        CRUD["Data Access Layer (db/crud.py)"]
        Tables[(repositories<br/>scans<br/>findings<br/>risk_assessments<br/>reports)]
    end

    subgraph UI ["Presentation Layer"]
        Dashboard["React Dashboard (dashboard/)<br/>Findings, Risk Charts, CBOM Export"]
    end

    subgraph AI ["AI Remediation (Optional Remote)"]
        MultiLLM["Gemini / OpenAI / Grok / Groq / NVIDIA / Ollama<br/>Fallback: Deterministic Table"]
    end

    %% Flow connections
    CLI -->|1. Local AST Scan & Scoring| CLI
    CLI -->|2. Optional Local Sign| SignedBundle
    SignedBundle -->|3. POST with mTLS cert| Gateway
    Gateway -->|Forward authenticated agent| RouterSync
    RouterSync --> Security
    RouterSync --> BundleVerifier
    BundleVerifier --> CRUD

    CLI -.->|Direct execution mode (when enabled)| RouterScans
    RouterScans --> ScanRunner
    ScanRunner --> RiskEngine
    RiskEngine --> CRUD

    CRUD --> Tables

    Dashboard -->|GET /scans/{id}| Gateway
    Gateway --> RouterScans
    Gateway --> RouterFindings
    Gateway --> RouterCBOM
    Gateway --> RouterRemediation

    RouterFindings --> CRUD
    RouterCBOM --> CRUD
    RouterCBOM --> CBOMGen
    RouterRemediation --> MultiLLM
```

### 2.1 Scanner → API / Report Sync Contract
1. **Canonical Finding Model** (`scanner.finding.Finding`):
   - `file`: Scanned source file path (relative or `[redacted]` when `--redact-paths` is specified).
   - `line`: 1-indexed detection line number.
   - `algorithm`: Normalized algorithm identifier (e.g. `MD5`, `SHA-1`, `RSA`, `AES-128-CBC`).
   - `key_size`: Extracted key/modulus bits (e.g. `1024`, `2048`, `256`), or `None` if dynamically configured.
   - `confidence`: Certainty rating (`high` when backed by verified import/call origin, `unverified` otherwise).
   - `matched_call`: Code snippet of detected invocation.
   - `library`: Canonical library module name (e.g. `hashlib`, `crypto`, `java.security.MessageDigest`).
   - `primitive`: Cryptographic primitive category (e.g. `hash`, `asymmetric-cipher`, `symmetric-cipher`).
   - `language`: Source language (`python`, `java`, `javascript`, `typescript`).
   - `weak_by_default`: Boolean indicating known broken/deprecated status.
   - `detection_method`: Detection technique (`ast_visitor`, `tree_sitter_query`).
   - `source_context`: Operational reachability context (`SOURCE`, `TEST_ONLY`, `DEMO_ONLY`).

2. **Offline Signed Report Bundle** (`api/services/report_bundle.py`):
   - For air-gapped workstations and isolated CI runners, the CLI generates a tamper-evident bundle:
     - Header: `bundle_version`, `report_id`, `organization_id`, `repository_id`, `agent_id`, `created_at`.
     - Payload: List of scored `findings` and aggregate `summary`.
     - Integrity: Canonical JSON SHA-256 `bundle_digest`.
     - Authenticity: Ed25519 signature over digest (`signature_algorithm: Ed25519`).
   - Bundles are delivered via `POST /agent/v1/report-bundles` over mutual TLS (`--client-cert`, `--client-key`, `--ca-cert`).

3. **Server-Side Local Execution** (`POST /scans`):
   - When `ENABLE_LOCAL_SCAN_API=true` is enabled, the backend accepts a local repository path and invokes `scan_runner.py` via an asynchronous background task, running `scanner/cli.py` safely via parameter arrays (`shell=False`).

### 2.2 API → Database Contract
All persistence is routed through `db/crud.py` adhering to SQLAlchemy 2.0 standards:
- **`repositories`**: Stores scanned codebases (`id`, `name`, `url`, `organization_id`, `external_id`).
- **`scans`**: Tracks scan execution lifecycle (`id`, `repo_id`, `started_at`, `status`, `source_scan_id`, `scan_context`). Status transitions: `pending` → `running` → `completed` | `failed`.
- **`findings`**: Stores discovery facts (`id`, `scan_id`, `file`, `line`, `algorithm`, `key_size`, `confidence`, `matched_call`, `library`, `primitive`, `language`, `weak_by_default`, `detection_method`, `source_context`, `risk_tier`, `risk_reason`, `criticality`).
- **`risk_assessments`**: Immutable interpretation record keyed to finding (`finding_id`, `risk_model_version`, `classical_broken`, `quantum_vulnerable`, `hndl_exposure`, `recommended_replacement`, `recommendation_type`, `migration_effort_days`, `data_shelf_life_years`, `quantum_threat_horizon_years`, `assumption_source`, `assessed_at`).
- **`reports`**: Custody and intake audit trail for ingested signed bundles (`report_id`, `scan_id`, `organization_id`, `repository_id`, `agent_id`, `bundle_digest`, `signature_algorithm`, `classification`, `created_at`, `expires_at`).

### 2.3 API Endpoint Surface

| Method | Route | Description | Auth Required |
|---|---|---|---|
| `GET` | `/` | API status and version check | None |
| `GET` | `/health` | Healthcheck endpoint | None |
| `POST` | `/scans` | Queue a local repository scan (202 Accepted) | `X-API-Key` (Local API enabled) |
| `GET` | `/scans` | Paginated list of scans (filter by `repo_id`) | `X-API-Key` |
| `GET` | `/scans/{scan_id}` | Scan details with findings and risk summary | `X-API-Key` |
| `GET` | `/scans/{scan_id}/findings` | Paginated findings list (filter by `risk_tier`) | `X-API-Key` |
| `GET` | `/scans/{scan_id}/findings/{finding_id}` | Single finding detail by ID | `X-API-Key` |
| `GET` | `/scans/{scan_id}/cbom` | Export CycloneDX 1.6 CBOM JSON (`?download=true`) | `X-API-Key` |
| `GET` | `/scans/health` | Remediation router health & supported LLM list | None |
| `GET` | `/scans/{scan_id}/remediation/{finding_id}` | Remediation guidance for finding (LLM or table) | `X-API-Key` |
| `POST` | `/scans/remediation/generate` | Ad-hoc remediation generation for finding input | `X-API-Key` |
| `POST` | `/agent/v1/report-bundles` | Ingest signed report bundle from offline agent | mTLS Agent Identity |

---

## 3. Technology Stack

| Component | Technology | Version / Standard | Operational Rationale |
|---|---|---|---|
| **Language Runtime** | Python | 3.11-slim | Pinned for native tree-sitter C-binding compatibility |
| **Backend Framework** | FastAPI | >= 0.110.0 | High-throughput asynchronous REST API with OpenAPI autodoc |
| **Data Validation** | Pydantic | v2 (`pydantic-settings`) | Type enforcement, serialization, environment configuration |
| **ORM Layer** | SQLAlchemy | 2.0+ | Typed queries (`Mapped[T]`), connection pooling, SQLite & Postgres parity |
| **Database** | PostgreSQL | 16-alpine | ACID persistence, JSON support, cascading foreign keys, migration indexing |
| **AST Parser (Python)** | Python Standard Library `ast` | Python 3.11 | Full syntactic analysis, alias tracking, zero false positives on comments |
| **Tree-Sitter Engine** | Tree-Sitter & Tree-Sitter-Languages | `tree-sitter==0.21.3` | Polyglot parsing for Java, JavaScript, and TypeScript/TSX |
| **Cryptographic Signing** | `cryptography` | Latest | Ed25519 key loading, signing, and verification for tamper-evident bundles |
| **Reverse Proxy / Gateway** | Nginx | 1.27-alpine | TLS termination, strict HSTS, mTLS agent certificate authentication |
| **Frontend Framework** | React + Vite | React 18 / Vite 5 | Single Page Application with fast rendering and modular structure |
| **Styling & Icons** | Tailwind CSS & Lucide Icons | Latest | Security-ledger aesthetic, responsive tables, consistent status badges |
| **BOM Standard** | CycloneDX | Spec 1.6 (CBOM standard) | Cryptographic Bill of Materials standard with algorithm properties |
| **AI Remediation** | Multi-Provider LLM | Gemini, OpenAI, Grok, Groq, NVIDIA, Ollama | Rule-constrained generative advice with deterministic static table fallback |
| **Containerization** | Docker & Docker Compose | Compose v2 | Isolated multi-container deployment (`data_net`, `app_net`, dropped root privileges) |

---

## 4. Security Posture Summary

1. **Local-First & Air-Gapped Operation**:
   - The scanner operates entirely locally by default; source code never leaves the workstation or CI runner.
   - Path redaction (`--redact-paths`) prevents internal workstation file paths from leaking outside the local perimeter.

2. **Tamper-Evident Report Synchronization**:
   - Ingestion requires cryptographically signed Ed25519 bundles.
   - Payloads are validated against a SHA-256 bundle digest and authenticated through mutual TLS (mTLS) with dedicated agent CA verification.

3. **Zero Untrusted Execution**:
   - Subprocess scanning (`scan_runner.py`) uses explicit parameter arrays with strict argument validation. Shell execution (`shell=True`) is prohibited.
   - Target directories are validated before processing to prevent path traversal attacks.

4. **HTTP & API Hardening**:
   - Strict Content-Type enforcement (`application/json`) prevents CSRF post-back attacks.
   - Enforced body payload limits (5 MB default, custom limit on report bundles) prevent denial-of-service via resource exhaustion.
   - Comprehensive response headers injected by default: `Content-Security-Policy`, `Strict-Transport-Security` (on HTTPS), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and `Permissions-Policy`.
   - Timing-safe comparison for all secret keys (`secrets.compare_digest`).

5. **Container Privilege Minimization**:
   - All production containers (`db`, `backend`, `dashboard`, `gateway`) execute with `read_only: true` root filesystems, `no-new-privileges: true`, and dropped capabilities (`cap_drop: [ALL]`).
   - The backend runs as unprivileged user `ecdat` (UID/GID non-root).

6. **Deterministic AI Safety**:
   - Remote LLM egress is disabled by default (`ALLOW_REMOTE_REMEDIATION=false`).
   - Prompts strictly constrain the LLM to phrase only the predetermined deterministic fix.
   - Automatic, graceful fallback to the local deterministic lookup table (`remediation_table.py`) on any error, timeout, or missing key.

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

---

## 6. Planned Additions

> [!NOTE]
> **System Interface Contract Status:** `SYSTEM_INTERFACE_CONTRACT.md` does not exist in the repository yet.
> The architectural additions listed below represent planned future platform capabilities to be formalized once `SYSTEM_INTERFACE_CONTRACT.md` is drafted and adopted by the team.

When `SYSTEM_INTERFACE_CONTRACT.md` is established, the following planned additions will be scheduled for implementation:

1. **Automated Multi-Language Demo Generator (`scripts/generate_demo_repo.py`)**:
   - Expand the current 4-line TODO stub into an automated generator producing vulnerable code across Python, Java, JavaScript, and TypeScript for testing and demonstrations.

2. **Live Dashboard Gateway Integration**:
   - Transition the React frontend (`dashboard/src/`) from mock-data demonstration mode to live authenticated API interaction via the Nginx gateway reverse proxy (`/scans`, `/cbom`, and real-time polling).

3. **Binary and Container Cryptographic Discovery**:
   - Extend detection beyond source code into compiled artifacts (Java JARs, Go binaries, shared object libraries) using static symbol and byte-pattern inspection.

4. **Automated VCS Pull Request Bot**:
   - Native GitHub App / GitLab webhook integration providing inline PR review comments with remediation diffs directly on offending lines of code.

5. **Enterprise SSO & Role-Based Access Control (RBAC)**:
   - Implement OpenID Connect (OIDC) / SAML 2.0 identity federation for enterprise dashboard access, distinguishing Security Admin, Auditor, and Developer roles.
