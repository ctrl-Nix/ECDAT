# ECDAT — Enterprise Cryptographic Discovery & Quantum-Risk Analysis Platform

**Smart India Hackathon 2026** · **Problem Statement PS 26164** · Team **ctrl-Nix** (KIIT Bhubaneswar)

[![CI Gate](https://github.com/ctrl-Nix/ECDAT/actions/workflows/ecdat-scan.yml/badge.svg)](.github/workflows/ecdat-scan.yml)
[![Standard](https://img.shields.io/badge/CBOM-CycloneDX%201.6-blue)](https://cyclonedx.org)
[![Python](https://img.shields.io/badge/Python-3.11-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 1. Problem Context (PS 26164)

**Enterprises do not know where their vulnerable cryptography lives.**

- **The Approaching Quantum Threat:** NIST's Post-Quantum Cryptography (PQC) migration standards are here, and classical algorithms like RSA and ECC face obsolescence under Shor's algorithm. Furthermore, Harvest Now, Decrypt Later (HNDL) attacks threaten high-shelf-life sensitive data today.
- **The Discovery Gap:** Most organizations lack an automated, accurate inventory of cryptographic usage across polyglot repositories.
- **Nascent Tooling Ecosystem:** The Cryptography Bill of Materials (CBOM) was only standardized in CycloneDX v1.6 (April 2024). Standardized tooling is practically nonexistent.
- **The Flaws of Existing Approaches:** Current practices rely on manual audits, naive regex scanners prone to overwhelming false positives, or proprietary third-party SaaS products that require exporting sensitive proprietary source code off-premises.

> **Our Mission:** Deliver an open-source, self-hosted, CI/CD-integrated platform that scans source code **structurally (AST and Tree-sitter, never naive regex)**, generates a standardized **CycloneDX 1.6 CBOM**, evaluates quantum risk using an adaptation of **Mosca's theorem**, provides actionable remediation, and blocks non-compliant PRs through automated compliance gates.

---

## 2. The Solution: ECDAT

ECDAT is a CLI-first, Docker-orchestrated cryptographic analysis platform built to satisfy all 5 core requirements of **PS 26164**:

| PS 26164 Requirement | ECDAT Delivery |
|---|---|
| **1. Discovery** | Static AST analysis for Python (`ast`) and Tree-sitter for Java, JavaScript, and TypeScript/TSX without executing code or relying on regex |
| **2. Identification** | Detects algorithms, primitives, key sizes, libraries, and assigns confidence ratings based on verified import origins |
| **3. Cataloguing (CBOM)** | Generates standardized CycloneDX 1.6 CBOM documents populated with `cryptographic-asset` components |
| **4. Quantum-Risk Scoring** | Deterministic two-axis risk engine (classical vulnerability vs. quantum vulnerability) incorporating Mosca's theorem and data shelf-life |
| **5. Recommendation & Reporting** | Generates concrete migration advice (PQC & classical alternatives), supports multi-provider AI rephrasing with deterministic fallback, and provides an interactive dashboard |

### Two Operational Modes, Zero Code Egress

```text
Mode 1: CI/CD Compliance Gate                 Mode 2: Local / Air-Gapped Scanner
─────────────────────────────                 ──────────────────────────────────
Enterprise CI/CD Pipeline                     Engineer Workstation / Isolated Runner
       │                                                     │
       ▼                                                     ▼
┌──────────────┐                              ┌──────────────────────────────┐
│  ecdat scan  │                              │  ecdat scan --report-bundle  │
│  --fail-on   │                              │  --sync-url (mTLS)           │
└──────┬───────┘                              └──────────────┬───────────────┘
       │                                                     │
       ▼                                                     ▼
  Pass/Fail Gate                                  Ed25519-Signed Bundle
  (Exit code 0 or 2)                              Forwarded to Central Gateway
```

- **Data Privacy Guarantee:** Source code never leaves the enterprise boundary. Scans are local-first, paths can be redacted (`--redact-paths`), and remote report delivery uses cryptographically signed Ed25519 bundles over mutual TLS (mTLS).

---

## 3. Implementation Status

### 3.1 Implemented (Active & Verified)
- **Python AST Engine (`scanner/python_engine.py`):** Syntactic inspection via Python standard library `ast`. Resolves import aliases, matches call sites (e.g. `hashlib`, `cryptography`), extracts RSA key sizes, and is completely immune to comments and decoy variable names.
- **Multi-Language Tree-Sitter Engine (`scanner/multilang_engine.py`):** Static parsing for Java, JavaScript, and TypeScript/TSX using Tree-sitter 0.21.3. Resolves static/named imports, CommonJS `require()`, ES6 module specifiers, browser Web Crypto globals, extracts key sizes, and assigns sequential finding IDs.
- **External Detection Rules (`scanner/rules/`):** Declarative YAML detection rules for Java (`java.yaml`) and JavaScript/TypeScript (`javascript.yaml`).
- **Unified Finding Schema (`scanner/finding.py`):** Normalized data model capturing file, line, algorithm, key size, library, primitive, language, detection method, source context, and confidence level (`high` vs `unverified`).
- **Scanner CLI (`scanner/cli.py`):** Offline scanning command with `--json-out`, `--summary-only`, `--redact-paths`, `--source-context` tagging (`SOURCE`, `TEST_ONLY`, `DEMO_ONLY`), policy thresholds (`--fail-on {CRITICAL,HIGH,MEDIUM,LOW}`), Ed25519 bundle signing (`--report-bundle`), and HTTPS mTLS syncing (`--sync-url`).
- **Deterministic Quantum Risk Engine (`api/services/risk_engine.py`):** Evaluates risk across two distinct axes:
  - *Classical Broken:* e.g., MD5, SHA-1, DES (CRITICAL regardless of quantum horizon).
  - *Quantum Vulnerable:* e.g., RSA, ECC, DSA broken via Shor's algorithm (HIGH/CRITICAL).
  - *Secure:* e.g., AES-256, SHA-256, ML-KEM, ML-DSA (LOW).
  - Integrates Mosca's theorem parameters ($X + Y > Z$) with configurable `--data-shelf-life-years`.
- **CycloneDX 1.6 CBOM Generator (`api/services/cbom_generator.py`):** Dynamic export of machine-readable CycloneDX 1.6 JSON containing cryptographic asset components with properties, risk tiers, and PQC transition notes.
- **Remediation Service & Fallback (`api/routers/remediation.py`, `remediation_table.py`):** Multi-provider LLM support (Google Gemini, OpenAI, Grok/xAI, Groq/Llama, NVIDIA Build, Ollama) strictly prompted to phrase guidance as PR comments, backed unconditionally by a local deterministic lookup table.
- **FastAPI Backend (`api/`):** Fully implemented REST API with security middleware (canonical JSON enforcement, 5 MB payload limit, strict CSP, HSTS, X-Content-Type-Options headers) and mounted routers:
  - `POST /scans`, `GET /scans`, `GET /scans/{scan_id}`
  - `GET /scans/{scan_id}/findings`, `GET /scans/{scan_id}/findings/{finding_id}`
  - `GET /scans/{scan_id}/cbom` (with attachment download option)
  - `GET /scans/health`, `GET /scans/{scan_id}/remediation/{finding_id}`, `POST /scans/remediation/generate`
  - `POST /agent/v1/report-bundles` (authenticated mTLS signed intake)
- **Database Layer (`db/`):** PostgreSQL 16 schema (`db/schema.sql`, `db/migrations/001_secure_reporting.sql`) with cascade constraints and indexes, SQLAlchemy 2.0 ORM models (`db/models.py`), and centralized CRUD queries (`db/crud.py`).
- **Security & Deployment (`deploy/`, `docker-compose.yml`):** Nginx reverse proxy gateway configured for mTLS client verification; hardened containers with dropped privileges (`cap_drop: [ALL]`, `read_only: true`, non-root execution).
- **Automated CI/CD Quality Gate (`.github/workflows/ecdat-scan.yml`):** GitHub Actions workflow executing scanner policy checks on pull requests.

### 3.2 In Progress
- **Frontend Dashboard Live Gateway Integration (`dashboard/`):** The React SPA structure, Vite build, Tailwind CSS styles, and UI components (`App.jsx`, `FindingsTable.jsx`, `RiskChart.jsx`, `CBOMViewer.jsx`) are built and containerized via `dashboard/Dockerfile`. However, the UI currently operates in demo mode using local fixture data (`mockData.js`) and is being actively wired to the authenticated live backend endpoints through the Nginx gateway.
- **Gateway Certificate Lifecycle Automation:** The Nginx edge gateway (`deploy/nginx/nginx.conf`) enforces mTLS and TLS termination, but certificates (`deploy/tls/`) are currently manually provisioned rather than managed via automated PKI/ACME enrollment.

### 3.3 Planned (Future Additions)
- **Registry-backed container scanning:** Image scanning currently accepts a `docker save` tarball or OCI layout only. Pulling directly from a registry is deliberately excluded — it would break the no-egress guarantee — and would need an explicit opt-in design.
- **Compiled-artifact depth:** Binary scanning covers ELF/PE/Mach-O symbol tables and linked libraries. Statically linked, stripped or packed binaries (typical Go and Rust builds) defeat symbol-table analysis and are documented as a non-claim.
- **Automated Demo Codebase Generator (`scripts/generate_demo_repo.py`):** The script exists as a 4-line stub with TODO notes. Full automated generation of a multi-language vulnerable demo repository is planned.
- **Automated VCS Pull Request Bot:** GitHub/GitLab bot commenting directly on PR lines with remediation suggestions rather than only failing builds.
- **Enterprise SSO / RBAC:** Enterprise OIDC/SAML authentication for multi-tenant team access.

---

## 4. Repository Layout

```text
ECDAT/
├── api/                    # FastAPI backend (routers, services, core, DB wiring)
│   ├── core/               # Configuration and security dependencies
│   ├── routers/            # Scans, findings, CBOM, remediation, report-sync
│   └── services/           # CBOM generator, risk engine, scan runner, report bundles
├── dashboard/              # React + Vite + Tailwind CSS reporting dashboard
│   ├── src/                # UI components (FindingsTable, RiskChart, CBOMViewer)
│   └── Dockerfile          # Multi-stage Nginx container for frontend SPA
├── db/                     # Canonical database layer (Ronak)
│   ├── migrations/         # SQL schema migrations
│   ├── crud.py             # Centralized SQLAlchemy query operations
│   ├── models.py           # Declarative ORM models
│   └── schema.sql          # PostgreSQL DDL with indexes and constraints
├── deploy/                 # Production deployment orchestration
│   ├── nginx/              # Nginx gateway reverse proxy with mTLS
│   └── tls/                # TLS certificate setup instructions
├── docs/                   # Guides (CLI guide, risk engine spec, demonstration guide)
├── scanner/                # AST and Tree-sitter detection engine (Shashank)
│   ├── cli.py              # Scanner CLI & CI entrypoint
│   ├── multilang_engine.py # Tree-sitter scanner for Java, JS, TS
│   ├── python_engine.py    # Python AST scanner with alias tracking
│   └── rules/              # Declarative YAML detection rules
├── scripts/                # Utility scripts (generate_demo_repo.py)
├── skills/                 # Team skill definitions & agent operational protocols
├── tests/                  # Pytest test suite (API, CRUD, LLM fallback, rules)
├── ARCHITECTURE.md         # Full system architecture source of truth
├── docker-compose.yml      # Multi-container orchestration (db, backend, dashboard, gateway)
├── Dockerfile              # Hardened backend Docker container definition
├── PRODUCT_DESCRIPTION.md  # SIH pitch context, elevator pitches & compliance mapping
└── requirements.txt        # Python package dependencies
```

---

## 5. Quick Start

### 5.1 Run the Scanner Locally (No Docker Required)

Requires **Python 3.11** (due to native tree-sitter bindings):

```bash
# 1. Clone and set up environment
git clone https://github.com/ctrl-Nix/ECDAT.git
cd ECDAT
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Run an offline scan against a target directory
python -m scanner.cli ./scanner --fail-on HIGH

# 3. Scan and generate an Ed25519-signed report bundle
python -m scanner.cli /path/to/code \
  --report-bundle report.json \
  --organization-id org_corp \
  --repository-id repo_payment \
  --agent-id agent_worker_01 \
  --signing-key /path/to/private_key.pem
```

### 5.2 Run the Automated Test Suite

```bash
# Runs API, CRUD, risk engine, and fallback tests (uses in-memory SQLite, no Postgres required)
pytest
```

### 5.3 Run the Full Platform with Docker Compose

```bash
# 1. Prepare environment variables
cp .env.example .env

# 2. Start PostgreSQL, FastAPI backend, React dashboard, and Nginx gateway
docker compose up -d

# 3. Check container health
docker compose ps

# 4. Access the services
# - API Health: https://localhost:8443/health (or http://localhost:8000/health internally)
# - Dashboard:  https://localhost:8443/
```

For full database lane documentation, see **[db/README.md](db/README.md)**.  
For the complete technical architecture and data contracts, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.
