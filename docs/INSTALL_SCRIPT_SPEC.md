# Feature Specification — Install Script (`INS`)

---

## 1. Header

| Field | Value |
|---|---|
| **Feature name** | Install Script |
| **Feature code** | `INS` (per `SYSTEM_INTERFACE_CONTRACT.md` §0, feature code table) |
| **Project** | ECDAT — Enterprise Cryptographic Discovery & Assessment Tool, SIH 2026, PS 26164, team ctrl-Nix |
| **Owner** | Deploy/ops lane. `SYSTEM_INTERFACE_CONTRACT.md` §1.5 assigns `scripts/install.sh`, `scripts/install.ps1` and `.github/workflows/install-smoke.yml` to `INS` as **SOLE**, but names no individual. **Assign a named owner before merge.** |
| **Spec version** | 2.0 |
| **Status** | Ready for implementation **after** its merge-order predecessors land (see below). Not startable today. |
| **Merge-order position** | **Wave 3**, per `SYSTEM_INTERFACE_CONTRACT.md` §6: `| **3** | CBV · ASP · INS | — |`. Blocked by Wave 1 RBAC (`Principal` contract, `users`, `require_role`) and Wave 2 `CLI wrapper; scanner/cli.py --scan-type flag`. |
| **Reviewer sign-off** | Integration architect (contract owner): ____________ · Deploy lane: ____________ · RBAC owner (bootstrap contract, C-09): ____________ · Scanner lane / Shashank (`docs/ECDAT_CLI_GUIDE.md`, C-11): ____________ · Date: __________ |

### Changelog

**v2.0 — this document.** Supersedes the Step 1 initial-analysis proposal. Deviations forced by `SYSTEM_INTERFACE_CONTRACT.md`:

| # | Step 1 proposal said | Contract requires | Reference |
|---|---|---|---|
| D-1 | "Backend `/health`: reached via the gateway as `/api/health`. The README's `https://localhost:8443/health` currently routes to the dashboard SPA." | Confirmed and made binding: `GET /api/health` through the gateway is the canonical external healthcheck, and the README is corrected. | §3.4, C-21, §5.3 |
| D-2 | Assumption 4: "Assumed no `ecdat` PATH wrapper, since the README's `ecdat scan` executable doesn't exist." | **Rejected.** "CLI merges before INS so the installer can build and reference the `ecdat` entrypoint." `scanner/ecdat_cli.py` + `pyproject.toml` are SOLE to `CLI`. INS references the entrypoint; it does not create it. | C-21, §1.1 |
| D-3 | §4: "**Minimal RBAC:** any new required env vars (e.g. a token secret) or a first-run admin bootstrap command, so the installer can generate or invoke them." | RBAC publishes `AUTH_BOOTSTRAP_ADMIN_USERNAME` and a seed path that INS **invokes**. INS does not design, name or generate RBAC's variables. | C-21, C-09, §3.3 |
| D-4 | Implied that INS may add env vars. | **INS introduces no new environment variables.** §3.3's reserved-prefix table allocates prefixes to RBAC (`AUTH_`), ENR (`AGENT_ENROLLMENT_`), scanner lanes (`SCAN_`), AUD (`AUDIT_`) and frontend (`VITE_`). **No prefix is allocated to INS.** INS only populates existing frozen variables. | §3.3 |
| D-5 | "Modify: `README.md` (§5.3 Quick Start)". | Permitted, but narrowed: C-19 reserves the scope-honesty documents for a single scope editor in Wave 4. INS edits `README.md` §5.3 Quick Start and the health URL only. INS must not touch `PRODUCT_DESCRIPTION.md` or `ARCHITECTURE.md`. | C-19, §5.1 |
| D-6 | "Modify: `docs/ECDAT_CLI_GUIDE.md` (§1 build step)". | Retained, but the file is **COORDINATED, scanner lane (Shashank)**, contended by six features under C-11. INS submits the edit through the scanner lane, not directly. | §1.5, §5.1, C-11 |
| D-7 | Proposal did not mention `docker-compose.yml`. | `docker-compose.yml` is **COORDINATED (deploy lane)** and listed as *Conflicting* for `CNT RBAC AUD CLI INS` under C-01. INS must not add or reorder migration initdb mounts; those land with their owning migration PR. | §1.5, §5.1, C-01 |
| D-8 | Assumption 5: "`scripts/` is referenced in README/ARCHITECTURE but absent from the zip; assumed it will be created." | Confirmed against the repository snapshot: `scripts/` does not exist, although `README.md` line 121 and `ARCHITECTURE.md` line 89 both claim `scripts/generate_demo_repo.py`. INS creates the directory and `install.sh` / `install.ps1` only. `scripts/generate_demo_repo.py` is not assigned to INS and must not be created by it. | §1.5, AGENT_RULES #2, #9 |
| D-9 | Assumption 1: "Windows support? … PowerShell parity is optional." | The contract reserves `scripts/install.ps1` for INS as SOLE, so the path is allocated. This spec scopes it as a deliverable. Deferring it is a human scheduling call (see §11, A-9). | §1.5 |
| D-10 | Assumption 3: air-gapped install. | **Not covered by the contract.** Recorded as an unresolved gap in §11, A-8 — not resolved here. | — |

---

## 2. Goal & Context

PS 26164 asks for a deployable cryptographic discovery and assessment platform, and `PRODUCT_DESCRIPTION.md` §2 stakes the pitch on the line *"Data never leaves the enterprise's infrastructure. No SaaS, no crawling GitHub URLs, no third-party data egress,"* with §7 ("On Self-Hosting") repeating the claim to judges. That claim is only credible if a reviewer can bring the entire stack up on their own machine from a fresh clone, which today they cannot: `docker-compose.yml` bind-mounts `./deploy/tls/server.crt`, `./deploy/tls/server.key` and `./deploy/tls/agent-ca.crt` into the gateway, `deploy/tls/README.md` states the directory "is intentionally empty of certificate material," and `.gitignore` excludes `deploy/tls/*.crt`, `*.key` and `*.pem` — so `docker compose up -d` as printed in `README.md` §5.3 fails at the gateway on any clean checkout, and `.env` must additionally be populated by hand. This feature delivers one idempotent `scripts/install.sh` that performs preflight checks, creates `.env` and dev-only TLS material, brings the stack up, builds the `ecdat-scanner:local` CLI image, and prints a verified dashboard URL — turning `PRODUCT_DESCRIPTION.md` §6 "Minute 1: The Setup" from a manual ritual into a single reproducible command, and giving the judge-facing self-hosting claim something executable behind it.

---

## 3. Scope

### In-Scope

- A single static, idempotent `scripts/install.sh`, per C-21: *"The install script stays a **single static, idempotent `scripts/install.sh`**."*
- Preflight checks: `docker`, Docker Compose v2, `openssl`, `git`, bash version, and `ECDAT_HTTPS_PORT` availability.
- Creating `.env` from `.env.example` with a generated `POSTGRES_PASSWORD` and `API_KEY`, at mode `600`.
- Generating dev-only self-signed TLS material into `deploy/tls/`: `server.crt`, `server.key`, `agent-ca.crt`, `agent-ca.key`.
- `docker compose up -d --build --wait`.
- Building the `ecdat-scanner:local` image (the tag used in `docs/ECDAT_CLI_GUIDE.md` §1 and §3).
- Post-up verification against `GET /api/health` through the gateway (C-21).
- Invoking RBAC's published first-run admin seed path (C-21), when it exists — see §11, A-3.
- Printing the dashboard URL and a sample scan command using the `ecdat` entrypoint built by `CLI` (C-21, D-2).
- `--force` guard: never overwriting an existing `.env` or existing certs without it.
- A PowerShell behavioural mirror, `scripts/install.ps1`.
- `.github/workflows/install-smoke.yml`: fresh-clone install, then health check.
- Documentation edits listed in §5.

### Out-of-Scope

- **Any new environment variable.** §3.3 allocates no prefix to INS (D-4).
- **Any database schema change, migration file, or `docker-compose.yml` initdb mount.** Migration numbers 002–008 are reserved in §2.1 and are SOLE per file to other features; C-01 requires each mount to land with its own migration PR.
- **Designing RBAC's bootstrap.** INS invokes what RBAC publishes (C-09, C-21).
- **Creating, wrapping or modifying the `ecdat` entrypoint.** `scanner/ecdat_cli.py` and `pyproject.toml` are SOLE to `CLI` (§1.1).
- **Dynamically generated installer scripts, and any script that embeds an enrolment token or other credential.** C-21: *"the enrolment token is supplied at runtime via a CLI flag or environment variable, never templated into a generated script."*
- **Production TLS.** Generated certs are dev/demo only; `docs/SECURE_DEPLOYMENT.md` keeps organization-issued material as the production path.
- **Any edit to `PRODUCT_DESCRIPTION.md` or `ARCHITECTURE.md`.** C-19: *"Feature PRs create their own scope doc and must not touch `PRODUCT_DESCRIPTION.md`."*
- **`scripts/generate_demo_repo.py`** and the `demos/ecdat-live-demo` fixture referenced by `.github/workflows/ecdat-scan.yml` — neither exists in the repository snapshot and neither is assigned to INS (AGENT_RULES #9 applies: report it, do not stub it).
- Air-gapped / offline install (§11, A-8 — unresolved).
- Regex-based detection of any kind (AGENT_RULES #5). The installer performs no source-code detection.

---

## 4. Required Context Files

Read all of these in full before writing a line, per AGENT_RULES #1. Every path below is confirmed present in the repository snapshot or named in the contract's Canonical File Ownership Map.

**Binding governance**
- `AGENT_RULES.md`
- `SYSTEM_INTERFACE_CONTRACT.md` — §1.5, §2.1, §3.3, §3.4, §3.5, C-01, C-09, C-18, C-19, C-21, §5.1, §5.3, §5.4, §6, §7
- `ARCHITECTURE.md` — §1 (directory status), §4 (security posture)
- `PRODUCT_DESCRIPTION.md` — §2, §5, §6, §7 (read-only; do not edit, C-19)

**What the installer must produce or consume**
- `.env.example`
- `docker-compose.yml`
- `Dockerfile`
- `dashboard/Dockerfile`
- `deploy/nginx/nginx.conf`
- `deploy/tls/README.md`
- `.gitignore`
- `.dockerignore`

**Backend contracts the installer verifies against**
- `api/main.py` — the `@app.get("/health")` route and the security/limits middleware
- `api/core/config.py` — `Settings`, `construct_database_url`, `POSTGRES_*`, `API_KEY`
- `api/core/security.py` — `get_api_key`, `get_report_sync_agent`

**Database, for the smoke test's assertion only (read-only for INS)**
- `db/schema.sql`
- `db/migrations/001_secure_reporting.sql`

**CLI contract the installer prints a sample command for**
- `scanner/cli.py`
- `docs/ECDAT_CLI_GUIDE.md` — §1 "Installation and Local Image Build", §2 "Command Synopsis"

**Docs INS edits or must not contradict**
- `README.md` — §4 directory tree, §5.3 "Run the Full Platform with Docker Compose"
- `docs/SECURE_DEPLOYMENT.md`

**Version pins to check against, not change**
- `requirements.txt`
- `dashboard/package.json`
- `.github/workflows/ecdat-scan.yml` — existing workflow style and action pins

---

## 5. File Ownership

### 5.1 Files this feature creates — tier **SOLE (INS)**, per contract §1.5

| Path | Action | Tier | Notes |
|---|---|---|---|
| `scripts/install.sh` | create | **SOLE — INS** | The directory `scripts/` does not exist in the snapshot and is created by this PR. |
| `scripts/install.ps1` | create | **SOLE — INS** | Behavioural mirror; identical flags and exit codes. |
| `.github/workflows/install-smoke.yml` | create | **SOLE — INS** | Fresh-clone install, then health check. |

### 5.2 Files this feature modifies — **COORDINATED**, edits go through the named integration owner in the §6 merge order

| Path | Tier / owner per contract | Permitted INS edit | Reference |
|---|---|---|---|
| `README.md` | COORDINATED — listed in §5.1 as `ARCHITECTURE.md, README.md · BIN CONF INS · Conflicting · C-19` | §5.3 Quick Start only: add the `scripts/install.sh` path, and correct `https://localhost:8443/health` to `https://localhost:8443/api/health`. Also correct §4's `scripts/` tree entry to include `install.sh` / `install.ps1`. **No scope-status edits.** | C-21, C-19 |
| `docs/SECURE_DEPLOYMENT.md` | COORDINATED — deploy lane; §5.1 lists `INS ENR AUD · Compatible` | Add a short subsection stating the installer's generated certificates are dev/demo-only and must be replaced by organization-issued material. | §5.1 |
| `docs/ECDAT_CLI_GUIDE.md` | COORDINATED — **scanner lane (Shashank)**; §5.1 lists `CNT BIN IAC CLI INS ENR · Conflicting · C-11` | §1 only: note that `scripts/install.sh` already builds `ecdat-scanner:local`. Submit via the scanner lane. **Do not touch §2's command synopsis** — C-11 flag grammar is unresolved (§11, A-2). | C-11 |
| `.env.example` | COORDINATED — deploy lane; §5.1 lists `ENR RBAC CONF AUD INS · Compatible · §3.3` | **No key additions.** Comment-only edit, if any, pointing at the installer. INS adds no variables (D-4). | §3.3 |

### 5.3 Do not touch — every other feature's SOLE or FROZEN files

An exhaustive restatement of the contract's ownership map. Opening a PR against any of these is an AGENT_RULES #2 violation.

**FROZEN (changing the interface requires human sign-off, AGENT_RULES #3):**
`scanner/finding.py` · `api/services/scan_runner.py` · `api/services/risk_engine.py` · `api/core/security.py` (COORDINATED-frozen ordering under C-09)

**SOLE to other features — scanner lane:**
`scanner/dependency_engine.py`, `scanner/dependency_rules/` (DEP) · `scanner/container_engine.py`, `scanner/image_layers.py` (CNT) · `scanner/binary_engine.py` (BIN) · `scanner/config_engine.py` (IAC) · `scanner/confidence.py` (CONF) · `scanner/enroll_cli.py` (ENR) · **`scanner/ecdat_cli.py`, `pyproject.toml` (CLI)** · `scanner/rules/container.yaml` (CNT) · `scanner/rules/binary.yaml` (BIN) · `scanner/rules/config.yaml` (IAC)

**SOLE to other features — API lane:**
`api/routers/auth.py`, `api/core/rbac.py` (RBAC) · `api/routers/agents.py`, `api/services/enrollment.py` (ENR) · `api/routers/audit.py`, `api/services/audit.py` (AUD) · `api/routers/triage.py` (TRI) · `api/routers/trends.py` (TRD) · `api/routers/compliance.py` (CMP) · `api/services/cbom_validator.py` (CBV)

**SOLE to other features — frontend lane:**
`dashboard/src/index.css`, `dashboard/tailwind.config.js`, `dashboard/public/fonts/` (FE) · `dashboard/src/components/ConfidenceStamp.jsx` (CONF) · `dashboard/src/components/AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `pages/AgentStatusPage/`, `hooks/useAgents.js` (ASP) · `dashboard/src/components/ComplianceReport.jsx` (CMP) · `dashboard/src/components/RiskTrendChart.jsx`, `RiskTierBreakdown.jsx`, `pages/TrendsPage/` (TRD) · `dashboard/src/context/AuthContext.jsx`, `pages/LoginPage/LoginForm.jsx` (RBAC) · `dashboard/src/pages/LandingPage/index.jsx` (frontend lane)

**SOLE per file — database lane:**
`db/migrations/002_confidence_scoring.sql` · `003_artifact_scanning.sql` · `004_rbac_users.sql` · `005_agent_enrollment.sql` · `006_audit_events.sql` · `007_finding_triage.sql` · `008_query_indexes.sql`

**COORDINATED and not INS's to edit:**
`scanner/cli.py`, `scanner/constants.py`, `scanner/__init__.py`, `scanner/python_engine.py`, `scanner/multilang_engine.py`, `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml` · `api/models.py`, `api/routers/findings.py`, `api/routers/scans.py`, `api/routers/cbom.py`, `api/routers/remediation.py`, `api/routers/report_sync.py`, `api/main.py`, `api/core/config.py`, `api/services/cbom_generator.py` · `db/schema.sql`, `db/models.py`, `db/crud.py`, `db/seed.py` · `dashboard/src/components/FindingsTable.jsx`, `dashboard/src/lib/api.js`, `dashboard/src/App.jsx`, `dashboard/src/pages/DashboardPage/index.jsx`, `dashboard/src/lib/constants.js`, `dashboard/src/mockData.js` · **`requirements.txt` (backend lane, C-18)** · **`docker-compose.yml`, `Dockerfile` (deploy lane, C-01)** · `deploy/nginx/nginx.conf` (deploy lane) · `.github/workflows/ecdat-scan.yml` (CI lane) · `PRODUCT_DESCRIPTION.md` (single scope editor, C-19) · `tests/test_crud.py`, `tests/test_realworld_source_scanner.py`, `tests/test_scanner_battle.py`, `tests/test_security_controls.py`

**Marked for deletion by another lane:**
`dashboard/src/api.js` — Wave 0, frontend lane, C-08. INS does not delete it.

---

## 6. Tech Stack & Pinned Versions

INS adds **no** Python or npm dependency. `requirements.txt` is COORDINATED to the backend lane under C-18 and is not opened by this PR; `dashboard/package.json` is untouched.

### 6.1 Host tooling the installer requires (checked in preflight, not installed by it)

| Tool | Minimum | Why this floor |
|---|---|---|
| `bash` | 3.2 | macOS ships bash 3.2. The script is written to 3.2 syntax: no associative arrays, no `mapfile`/`readarray`, no `${var^^}`. |
| Docker Engine | 24.0 | Floor for the Compose v2 plugin distribution used here. |
| Docker Compose | v2.17.0 | `docker compose up --wait` is a v2.17+ flag; the Step 1 proposal depends on it. |
| `openssl` | 1.1.1 | `req -addext` for SAN generation without a temporary config file. |
| `git` | 2.25 | Fresh-clone workflow parity. |
| PowerShell (for `install.ps1` only) | 7.0 | Cross-platform `pwsh`; Windows PowerShell 5.1 is not a target. |

### 6.2 Versions already pinned in the repository — consumed, never changed by INS

| Pin | Where it already lives |
|---|---|
| `python:3.11-slim` | `Dockerfile` line 1 |
| `postgres:16-alpine` | `docker-compose.yml`, service `db` |
| `nginx:1.27-alpine` | `docker-compose.yml`, service `gateway` |
| `node:20-slim` | `dashboard/Dockerfile`, build stage |
| `nginxinc/nginx-unprivileged:1.27-alpine` | `dashboard/Dockerfile`, runtime stage |
| `tree-sitter==0.21.3`, `tree-sitter-languages==1.10.2` | `requirements.txt` — the constraint that pins the project to Python 3.11 (C-18) |
| `actions/checkout@v4`, `actions/setup-node@v4` | `.github/workflows/ecdat-scan.yml` |
| `ecdat-scanner:local` (image tag) | `docs/ECDAT_CLI_GUIDE.md` §1 and §3 |

### 6.3 New pins introduced by this feature

| Pin | Value | Scope |
|---|---|---|
| ShellCheck | `koalaman/shellcheck:v0.10.0` (container image) | `.github/workflows/install-smoke.yml` lint step only. Nothing in the repository pins ShellCheck today; this is INS's choice and must not float to `latest` (see §11, A-10). |
| `actions/checkout` | `v4` | Matches the existing workflow. |
| Runner | `ubuntu-latest`, `timeout-minutes: 15` | Matches `.github/workflows/ecdat-scan.yml` style. |

---

## 7. Concrete Interface Definitions

### 7.1 `scripts/install.sh` — CLI grammar

```text
Usage: scripts/install.sh [OPTIONS]

Options:
  --force              Regenerate .env and deploy/tls/* even if they exist.
  --https-port PORT    Override ECDAT_HTTPS_PORT for this run. Default: 8443.
  --skip-cli-image     Do not build the ecdat-scanner:local image.
  --skip-bootstrap     Do not invoke the RBAC first-run admin seed path.
  --help               Print this message and exit 0.

Exit codes:
  0  install completed and GET /api/health returned 200
  1  any preflight, generation, compose, build or health-verification failure
```

### 7.2 `scripts/install.sh` — literal header and constants

```bash
#!/usr/bin/env bash
# scripts/install.sh — SOLE: INS. SYSTEM_INTERFACE_CONTRACT.md §1.5.
set -euo pipefail

readonly ECDAT_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly ECDAT_ENV_FILE="${ECDAT_REPO_ROOT}/.env"
readonly ECDAT_ENV_EXAMPLE="${ECDAT_REPO_ROOT}/.env.example"
readonly ECDAT_TLS_DIR="${ECDAT_REPO_ROOT}/deploy/tls"
readonly ECDAT_SERVER_CRT="${ECDAT_TLS_DIR}/server.crt"
readonly ECDAT_SERVER_KEY="${ECDAT_TLS_DIR}/server.key"
readonly ECDAT_AGENT_CA_CRT="${ECDAT_TLS_DIR}/agent-ca.crt"
readonly ECDAT_AGENT_CA_KEY="${ECDAT_TLS_DIR}/agent-ca.key"
readonly ECDAT_CLI_IMAGE="ecdat-scanner:local"
readonly ECDAT_DEFAULT_HTTPS_PORT="8443"
readonly ECDAT_HEALTH_PATH="/api/health"
readonly ECDAT_MIN_COMPOSE_VERSION="2.17.0"
readonly ECDAT_MIN_OPENSSL_VERSION="1.1.1"
readonly ECDAT_CERT_DAYS="365"
readonly ECDAT_CERT_SUBJECT="/CN=localhost/O=ECDAT Local Development"
readonly ECDAT_AGENT_CA_SUBJECT="/CN=ECDAT Local Agent CA/O=ECDAT Local Development"
readonly ECDAT_CERT_SAN="DNS:localhost,DNS:agent.ecdat.local,IP:127.0.0.1"
readonly ECDAT_HEALTH_RETRIES="30"
readonly ECDAT_HEALTH_INTERVAL_SECONDS="2"
```

### 7.3 `scripts/install.sh` — function signatures

```bash
log_info()              { :; }   # $1: message                       -> stderr
log_warn()              { :; }   # $1: message                       -> stderr
log_error()             { :; }   # $1: message                       -> stderr
die()                   { :; }   # $1: message                       -> stderr; exit 1

print_usage()           { :; }   #                                   -> stdout: §7.1 text
parse_args()            { :; }   # "$@"                              -> sets OPT_FORCE OPT_HTTPS_PORT OPT_SKIP_CLI_IMAGE OPT_SKIP_BOOTSTRAP

require_command()       { :; }   # $1: command_name, $2: install_hint -> 0 | die
version_at_least()      { :; }   # $1: found, $2: required            -> 0 | 1
check_docker_daemon()   { :; }   #                                    -> 0 | die
check_compose_version() { :; }   #                                    -> 0 | die
check_openssl_version() { :; }   #                                    -> 0 | die
check_bash_version()    { :; }   #                                    -> 0 | die
check_port_free()       { :; }   # $1: port                           -> 0 | die
preflight_checks()      { :; }   #                                    -> 0 | die

generate_random_secret(){ :; }   # $1: byte_count                     -> stdout: hex string
generate_env_file()     { :; }   # $1: https_port, $2: force(0|1)     -> writes "$ECDAT_ENV_FILE" mode 600
generate_tls_material() { :; }   # $1: force(0|1)                     -> writes server.crt/.key, agent-ca.crt/.key

compose_up()            { :; }   #                                    -> docker compose up -d --build --wait
build_cli_image()       { :; }   #                                    -> docker build --tag "$ECDAT_CLI_IMAGE" "$ECDAT_REPO_ROOT"
wait_for_health()       { :; }   # $1: https_port                     -> 0 | die
bootstrap_admin_user()  { :; }   #                                    -> 0 | log_warn  (see §11 A-3; no-op until RBAC publishes)
print_summary()         { :; }   # $1: https_port                     -> stdout

main()                  { :; }   # "$@"                               -> exit 0 | 1
main "$@"
```

### 7.4 Generated `.env` — literal key block written over the `.env.example` copy

```dotenv
POSTGRES_PASSWORD=<64 hex chars from generate_random_secret 32>
API_KEY=<64 hex chars from generate_random_secret 32>
ECDAT_HTTPS_PORT=<OPT_HTTPS_PORT>
```

```bash
chmod 600 "$ECDAT_ENV_FILE"
chmod 600 "$ECDAT_SERVER_KEY" "$ECDAT_AGENT_CA_KEY"
chmod 644 "$ECDAT_SERVER_CRT" "$ECDAT_AGENT_CA_CRT"
```

### 7.5 TLS generation — literal openssl invocations

```bash
openssl req -x509 -newkey rsa:4096 -sha256 -days "$ECDAT_CERT_DAYS" -nodes \
  -keyout "$ECDAT_SERVER_KEY" -out "$ECDAT_SERVER_CRT" \
  -subj "$ECDAT_CERT_SUBJECT" -addext "subjectAltName=$ECDAT_CERT_SAN"

openssl req -x509 -newkey rsa:4096 -sha256 -days "$ECDAT_CERT_DAYS" -nodes \
  -keyout "$ECDAT_AGENT_CA_KEY" -out "$ECDAT_AGENT_CA_CRT" \
  -subj "$ECDAT_AGENT_CA_SUBJECT" -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
```

### 7.6 Health verification — literal request and expected response

```bash
curl --fail --silent --show-error --insecure \
  "https://localhost:${https_port}${ECDAT_HEALTH_PATH}"
```

```json
{"status": "ok", "version": "1.0.0"}
```

### 7.7 `scripts/install.ps1` — function signatures (behavioural mirror)

```powershell
#Requires -Version 7.0
[CmdletBinding()]
param(
    [switch] $Force,
    [int]    $HttpsPort = 8443,
    [switch] $SkipCliImage,
    [switch] $SkipBootstrap
)

function Write-EcdatInfo      { param([string] $Message) }
function Write-EcdatWarn      { param([string] $Message) }
function Stop-EcdatInstall    { param([string] $Message) }
function Test-EcdatPrereq     { param([string] $CommandName, [string] $InstallHint) }
function Test-EcdatPortFree   { param([int] $Port) }
function Invoke-EcdatPreflight{ }
function New-EcdatRandomSecret{ param([int] $ByteCount) }
function New-EcdatEnvFile     { param([int] $HttpsPort, [switch] $Force) }
function New-EcdatTlsMaterial { param([switch] $Force) }
function Invoke-EcdatComposeUp{ }
function Build-EcdatCliImage  { }
function Wait-EcdatHealth     { param([int] $HttpsPort) }
function Initialize-EcdatAdmin{ }
function Write-EcdatSummary   { param([int] $HttpsPort) }
function Invoke-EcdatInstall  { }

Invoke-EcdatInstall
```

### 7.8 `.github/workflows/install-smoke.yml` — literal structure

```yaml
name: ECDAT install smoke

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  shellcheck:
    name: Lint scripts/install.sh
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Check out source
        uses: actions/checkout@v4
      - name: Run ShellCheck
        run: >-
          docker run --rm -v "$GITHUB_WORKSPACE:/mnt:ro" -w /mnt
          koalaman/shellcheck:v0.10.0 --severity=style scripts/install.sh

  fresh-clone-install:
    name: Fresh-clone install and health check
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Check out source
        uses: actions/checkout@v4
      - name: Run the installer
        run: ./scripts/install.sh --https-port 8443
      - name: Verify the gateway health route
        run: >-
          curl --fail --silent --show-error --insecure
          https://localhost:8443/api/health
      - name: Verify the installer is idempotent
        run: ./scripts/install.sh --https-port 8443
      - name: Verify .env permissions
        run: test "$(stat -c '%a' .env)" = "600"
      - name: Tear down
        if: always()
        run: docker compose down -v
```

### 7.9 Smoke-test database assertion — literal SQL

```sql
-- scripts/install.sh authors NO migration. Migration numbers 002-008 are
-- reserved per SYSTEM_INTERFACE_CONTRACT.md §2.1 and are SOLE to other features.
-- install-smoke.yml asserts only that initdb applied the two files that exist
-- today: db/schema.sql (01_schema.sql) and
-- db/migrations/001_secure_reporting.sql (02_secure_reporting.sql).
SELECT to_regclass('public.repositories')     IS NOT NULL
   AND to_regclass('public.scans')            IS NOT NULL
   AND to_regclass('public.findings')         IS NOT NULL
   AND to_regclass('public.risk_assessments') IS NOT NULL
   AND to_regclass('public.reports')          IS NOT NULL
   AS schema_ready;
```

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -tAc "SELECT to_regclass('public.findings') IS NOT NULL;"
```

### 7.10 `print_summary` — literal stdout contract

```text
ECDAT is running.

  Dashboard   https://localhost:8443/
  Health      https://localhost:8443/api/health
  CLI image   ecdat-scanner:local

Sample scan:

  docker run --rm -v "$PWD":/target:ro \
    --entrypoint python ecdat-scanner:local \
    -m scanner.cli /target --fail-on HIGH

The generated certificate is self-signed and for local development only.
See docs/SECURE_DEPLOYMENT.md before any non-local deployment.
```

---

## 8. Step-by-Step Implementation Plan

Each step touches exactly one file.

1. **`scripts/install.sh`** — create the file with the literal header, `set -euo pipefail`, and the `readonly` constant block from §7.2. Nothing else.
2. **`scripts/install.sh`** — add `log_info`, `log_warn`, `log_error`, `die`, `print_usage`, `parse_args` exactly as declared in §7.3. `parse_args` accepts only the five flags in §7.1; an unknown flag calls `die`.
3. **`scripts/install.sh`** — add `require_command`, `version_at_least`, `check_bash_version`, `check_docker_daemon`, `check_compose_version`, `check_openssl_version`, `check_port_free`, and `preflight_checks` which calls them in that order. Floors come from §6.1.
4. **`scripts/install.sh`** — add `generate_random_secret` (`openssl rand -hex "$1"`) and `generate_env_file`. `generate_env_file` returns early with `log_info` when `.env` exists and `OPT_FORCE` is 0; otherwise it copies `.env.example`, substitutes the three keys in §7.4, and applies mode 600.
5. **`scripts/install.sh`** — add `generate_tls_material` using the literal `openssl` invocations in §7.5 and the `chmod` lines in §7.4. It returns early with `log_info` when all four files exist and `OPT_FORCE` is 0; with `--force` it regenerates all four together so the server cert and agent CA never drift apart.
6. **`scripts/install.sh`** — add `compose_up` and `build_cli_image` per §7.3. `build_cli_image` is skipped when `OPT_SKIP_CLI_IMAGE` is 1.
7. **`scripts/install.sh`** — add `wait_for_health` using the literal `curl` in §7.6, retrying `ECDAT_HEALTH_RETRIES` times at `ECDAT_HEALTH_INTERVAL_SECONDS`, then `die` on exhaustion.
8. **`scripts/install.sh`** — add `bootstrap_admin_user`. Until RBAC publishes its seed path it is a no-op that emits one `log_warn` line naming what is missing, per AGENT_RULES #9 and §11 A-3. It must not invent `AUTH_*` variables.
9. **`scripts/install.sh`** — add `print_summary` emitting exactly §7.10, and `main` wiring the sequence: `parse_args` → `preflight_checks` → `generate_env_file` → `generate_tls_material` → `compose_up` → `build_cli_image` → `wait_for_health` → `bootstrap_admin_user` → `print_summary`. End the file with `main "$@"`. Make it executable (`chmod +x`).
10. **`scripts/install.ps1`** — create the behavioural mirror with the signatures in §7.7. Same flags, same order, same exit codes, same summary text.
11. **`.github/workflows/install-smoke.yml`** — create it exactly as §7.8.
12. **`README.md`** — §5.3: replace the manual `cp .env.example .env` + `docker compose up -d` block with `./scripts/install.sh`, and correct the health URL to `https://localhost:8443/api/health` per C-21. In §4's tree, add `install.sh` and `install.ps1` to the `scripts/` entry. **No other edit.**
13. **`docs/SECURE_DEPLOYMENT.md`** — add the dev-only-certificates subsection described in §5.2.
14. **`docs/ECDAT_CLI_GUIDE.md`** — §1 only: note that `scripts/install.sh` already builds `ecdat-scanner:local`. Route the change through the scanner lane (Shashank) per C-11; do not merge it directly.
15. **`.env.example`** — comment-only pointer to the installer, if the deploy lane wants it. **No key additions** (D-4). This step is optional and may be dropped without affecting the Definition of Done.

---

## 9. Naming & Symbol Registry

### 9.1 Environment variables

**INS introduces none.** Contract §3.3 reserves `AUTH_` (RBAC), `AGENT_ENROLLMENT_` (ENR), `SCAN_` (scanner lanes), `AUDIT_` (AUD) and `VITE_` (frontend). **No prefix is allocated to INS**, and §3.3 forbids bare `TARGET`, `TOKEN`, `SECRET`, `KEY`, `PATH`.

Existing frozen variables the installer **writes values into**, never renames:

| Variable | Frozen by | INS action |
|---|---|---|
| `POSTGRES_PASSWORD` | §3.3 (`POSTGRES_*` frozen) | generates a value |
| `API_KEY` | §3.3 | generates a value — collision flagged, see §10 |
| `ECDAT_HTTPS_PORT` | §3.3 | writes the `--https-port` value |
| `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `DEBUG`, `CORS_ORIGINS`, `ENABLE_LOCAL_SCAN_API`, `ALLOW_REMOTE_REMEDIATION`, `REPORT_SYNC_*` | §3.3 | copied unchanged from `.env.example` |

### 9.2 CLI flags — `scripts/install.sh` and `scripts/install.ps1`

Long flags only, `kebab-case`, no new single-letter flags (§3.5).

| Flag | New? | Collision check |
|---|---|---|
| `--force` | new | Not in `scanner/cli.py`'s parser; not in §5.4's contested set (`--target-type`, `--image-tar`, `--binaries`, `--scan-type`, `--min-confidence`, `--fail-on`). Clear. |
| `--https-port` | new | Clear. |
| `--skip-cli-image` | new | Clear. |
| `--skip-bootstrap` | new | Clear. |
| `--help` | new | Standard; installer namespace only. |

The installer's namespace is separate from `scanner/cli.py` and `scanner/ecdat_cli.py`; it adds, renames and removes nothing there.

### 9.3 Exit codes

`0` success, `1` failure. **`2` is deliberately unused**: §3.5 freezes `2` as "policy violation (`--fail-on`)" and the existing CI gate in `.github/workflows/ecdat-scan.yml` asserts `test "$result" -eq 2`. The installer must never emit it.

### 9.4 Shell functions — `scripts/install.sh`

`log_info` · `log_warn` · `log_error` · `die` · `print_usage` · `parse_args` · `require_command` · `version_at_least` · `check_bash_version` · `check_docker_daemon` · `check_compose_version` · `check_openssl_version` · `check_port_free` · `preflight_checks` · `generate_random_secret` · `generate_env_file` · `generate_tls_material` · `compose_up` · `build_cli_image` · `wait_for_health` · `bootstrap_admin_user` · `print_summary` · `main`

All `snake_case`, matching §3.1's Python convention applied consistently across the repository. No PascalCase function names.

### 9.5 Shell constants and option variables

`ECDAT_REPO_ROOT` · `ECDAT_ENV_FILE` · `ECDAT_ENV_EXAMPLE` · `ECDAT_TLS_DIR` · `ECDAT_SERVER_CRT` · `ECDAT_SERVER_KEY` · `ECDAT_AGENT_CA_CRT` · `ECDAT_AGENT_CA_KEY` · `ECDAT_CLI_IMAGE` · `ECDAT_DEFAULT_HTTPS_PORT` · `ECDAT_HEALTH_PATH` · `ECDAT_MIN_COMPOSE_VERSION` · `ECDAT_MIN_OPENSSL_VERSION` · `ECDAT_CERT_DAYS` · `ECDAT_CERT_SUBJECT` · `ECDAT_AGENT_CA_SUBJECT` · `ECDAT_CERT_SAN` · `ECDAT_HEALTH_RETRIES` · `ECDAT_HEALTH_INTERVAL_SECONDS` · `OPT_FORCE` · `OPT_HTTPS_PORT` · `OPT_SKIP_CLI_IMAGE` · `OPT_SKIP_BOOTSTRAP`

`UPPER_SNAKE_CASE` per §3.1. These are shell-local `readonly`s, not environment variables, and are not exported — so §3.3's prefix rule does not apply and no `.env` key is created.

### 9.6 PowerShell functions — `scripts/install.ps1`

`Write-EcdatInfo` · `Write-EcdatWarn` · `Stop-EcdatInstall` · `Test-EcdatPrereq` · `Test-EcdatPortFree` · `Invoke-EcdatPreflight` · `New-EcdatRandomSecret` · `New-EcdatEnvFile` · `New-EcdatTlsMaterial` · `Invoke-EcdatComposeUp` · `Build-EcdatCliImage` · `Wait-EcdatHealth` · `Initialize-EcdatAdmin` · `Write-EcdatSummary` · `Invoke-EcdatInstall`

PowerShell `Verb-Noun` is the language's mandatory convention and does not conflict with §3.1, which governs Python.

### 9.7 Generated artefacts

| Path | New? | Notes |
|---|---|---|
| `deploy/tls/server.crt`, `server.key`, `agent-ca.crt` | no | Names fixed by `docker-compose.yml`'s gateway bind mounts and `deploy/tls/README.md`. Not renameable. |
| `deploy/tls/agent-ca.key` | new | Covered by `.gitignore`'s `deploy/tls/*.key`. Verify before first run. |

### 9.8 Database columns, classes, API routes

**None.** INS adds no table, column, index, Pydantic model, router or route. It consumes one existing route, `GET /api/health` (§3.4, C-21).

---

## 10. Known Cross-Feature Risks

Pulled from the contract's Flagged Conflicts & Resolutions and Shared Resource Index. Each resolution below is the one already decided; none is re-opened here.

### R-1 · C-21 — `install.sh` assumptions contradict two other features
**Shared resource:** `scripts/install.sh`, `/health` routing, the `ecdat` entrypoint. **Proposals:** INS, CLI, RBAC. **Confidence: High.**
**Decided resolution, quoted:** *"The install script stays a **single static, idempotent `scripts/install.sh`**; the enrolment token is supplied at runtime via a CLI flag or environment variable, never templated into a generated script. CLI merges before INS so the installer can build and reference the `ecdat` entrypoint. RBAC publishes `AUTH_BOOTSTRAP_ADMIN_USERNAME` and a seed path that INS invokes. `GET /api/health` through the gateway becomes the documented healthcheck and the README is corrected."*

### R-2 · §5.3 — `GET /scans/health` vs `GET /health` vs `/api/health`
**Features:** INS. **State: Conflicting. Ref: C-21.**
Three health surfaces exist today: `api/main.py` serves `GET /health` and `GET /`; `api/routers/remediation.py` is mounted with `prefix="/scans"` and exposes `GET /scans/health`; the gateway's `location /api/ { proxy_pass http://backend:8000/; }` strips the prefix so `/api/health` reaches the backend's `/health`, while `https://localhost:8443/health` falls through `location /` to the dashboard SPA. **Resolved:** the installer verifies `GET /api/health` and nothing else.

### R-3 · C-09 / §5.4 — `API_KEY` / `X-API-Key`
**Features:** RBAC, ENR, AUD, **INS**. **State: Conflicting !** (open item, see §11 A-1). **Confidence: High on ordering.**
**Decided part:** *"RBAC merges first and publishes the `Principal` contract (`username`, `role`, `organization_id`) **before** the others start."* INS is listed as needing "auth env vars and an admin bootstrap." INS is Wave 3; RBAC is Wave 1. The installer still generates `API_KEY` because `api/core/security.py::get_api_key` fails closed with HTTP 503 when it is absent, which would break the stack regardless of the pending decision.

### R-4 · §5.4 — new `AUTH_*` / `AGENT_ENROLLMENT_*` / `SCAN_*` / `AUDIT_*` variables
**Features:** RBAC, ENR, CONF, AUD, **INS**. **State: Compatible. Ref: §3.3.**
**Decided resolution:** each prefix belongs to its owning feature. INS owns no prefix and therefore adds no variable; it copies whatever the owning features have already added to `.env.example` by the time INS merges.

### R-5 · C-01 / §5.1 — `docker-compose.yml`
**Features:** CNT, RBAC, AUD, CLI, **INS**. **State: Conflicting. Confidence: High.**
**Decided resolution, quoted:** *"Numbers 002–008 are reserved in §2.1. Every migration also adds a `docker-compose.yml` mount with the matching `NN_` prefix, and the identical change must land in `db/schema.sql` in the same PR."* INS therefore adds no mount and reorders none. The installer must tolerate a compose file whose initdb mount list has grown between Wave 1 and Wave 3 — it reads the file, it does not assert its contents.

### R-6 · §5.1 — `deploy/nginx/nginx.conf`
**Features:** ENR, AUD, **INS**. **State: Compatible.**
**Decided resolution:** *"ENR adds the enroll route + `$ssl_client_fingerprint`; AUD needs `X-Forwarded-For`."* INS reads the file to confirm the `/api/` location exists and does not edit it. Note the file already sets `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`.

### R-7 · §5.1 — `.env.example`
**Features:** ENR, RBAC, CONF, AUD, **INS**. **State: Compatible. Ref: §3.3.**
**Decided resolution:** per-prefix ownership. The installer must copy `.env.example` generically rather than assuming a fixed key list, because four other features will have added keys to it before Wave 3.

### R-8 · §5.1 — `docs/ECDAT_CLI_GUIDE.md`
**Features:** CNT, BIN, IAC, CLI, **INS**, ENR. **State: Conflicting. Ref: C-11.**
**Decided resolution:** the file is COORDINATED under the scanner lane. Six features queue there. INS's §1 build-step note goes through that lane.

### R-9 · §5.1 — `docs/SECURE_DEPLOYMENT.md`
**Features:** **INS**, ENR, AUD. **State: Compatible.** Additive subsections only; no restructure.

### R-10 · C-19 / §5.1 — `ARCHITECTURE.md`, `README.md`
**Features:** BIN, CONF, **INS**. **State: Conflicting. Confidence: High on the process.**
**Decided resolution, quoted:** *"Scope-truth documents are edited **once**, by a single named scope editor, after all four scanner scope docs … exist. Feature PRs create their own scope doc and must not touch `PRODUCT_DESCRIPTION.md`."* The §6 merge order places the "Single scope-truth documentation pass" in Wave 4, after INS. INS's README edit is confined to §5.3 and the §4 tree entry, both of which C-21 explicitly authorises for the health-URL correction.

### R-11 · C-18 / §5.1 — `requirements.txt`
**Features:** BIN, IAC, RBAC, CLI, CNT, CBV. **INS is not listed.** **State: Conflicting !**
INS adds no dependency, so this is a risk only in the negative direction: if an implementing agent is tempted to add a Python helper, it must not — the file is backend-lane COORDINATED under one grouped diff.

### R-12 · C-11 / §5.4 — CLI flag grammar in the printed sample command
**Features:** CNT, BIN, IAC, DEP, CONF, CLI. **State: Conflicting !** (open item, see §11 A-2).
The sample command in §7.10 deliberately uses only flags that exist in `scanner/cli.py` today (`--fail-on HIGH`) and the documented `--entrypoint python … -m scanner.cli` form from `docs/ECDAT_CLI_GUIDE.md` §3. It uses no contested flag.

---

## 11. Pre-Answered Ambiguities

Situations an implementing agent will hit, each as "if X, do Y." Items A-1 through A-4 are open sign-off items from contract §7 that touch INS; per the contract's own words, *"Nothing below is decided."* No resolution is invented for them here.

**A-1 · Contract §7, C-09 — "Does `X-API-Key` survive for CLI/service callers?" (Medium; blocks RBAC, CI, ENR.)**
**Status: undecided. No team answer exists in the contract.** *If* the installer's `.env` generation seems to depend on the answer, note that it does not for the generation step itself: `api/core/security.py::get_api_key` raises HTTP 503 when `settings.API_KEY` is unset, so the installer generates `API_KEY` either way and the stack comes up. *If* an agent is tempted to remove `API_KEY` from the generated `.env` because RBAC has landed, **stop and ask a human** (AGENT_RULES #4). Removing it would break `tests/test_security_controls.py`, `.github/workflows/ecdat-scan.yml` (which passes `-e API_KEY=ci-test-key`) and `dashboard/src/lib/api.js`, all of which the contract names as depending on the answer.

**A-2 · Contract §7, C-11 — "Final CLI flag grammar; does bare `ecdat TARGET` survive?" (Medium; blocks CLI + 4 engines.)**
**Status: undecided.** *If* the `ecdat` entrypoint's grammar is still in flux when INS is implemented, print the sample command in §7.10 exactly as written — the `docker run … --entrypoint python … -m scanner.cli /target --fail-on HIGH` form from `docs/ECDAT_CLI_GUIDE.md` §3, which uses no contested flag. *If* an agent wants to print `ecdat scan …` instead, **stop and ask the scanner lane**; do not guess a grammar that C-11 has not ratified.

**A-3 · Contract C-21 / C-09 — RBAC's admin bootstrap invocation.**
C-21 decides *that* INS invokes a seed path RBAC publishes and *that* `AUTH_BOOTSTRAP_ADMIN_USERNAME` is the variable name. **The contract does not specify the command, module path, or whether the initial password is generated by RBAC or supplied by INS — this is a genuine gap.** *If* RBAC has published the seed path by the time INS is implemented, `bootstrap_admin_user` invokes exactly that published command and nothing else. *If* it has not, `bootstrap_admin_user` is a no-op that emits one `log_warn` naming what is missing, per AGENT_RULES #9 ("say so — do not silently stub it out or fake success"), and `--skip-bootstrap` remains a no-op too. **Under no circumstance may INS invent an `AUTH_*` variable, a password policy, or a seed command** — §3.3 gives the `AUTH_` prefix to RBAC.

**A-4 · Contract §7, C-20 — "Is binary/container/dependency scanning in scope?" (Low; blocks CNT, BIN, IAC.)**
**Status: undecided, and the contract states it is "not resolvable by an integration architect."** Note the underlying contradiction is live in this repository: `AGENT_RULES.md` #6 says all three are in scope; `PRODUCT_DESCRIPTION.md` §5 marks "Binary/container scanning · ❌ Out of scope" and §7 uses that restraint as a pitch differentiator. *If* an agent wants the installer to pre-pull images, install parsers, or mention binary/container scanning in `print_summary`, **do none of it** — the §7.10 summary text mentions only source scanning. *If* the sign-off later lands, the summary text changes in a follow-up PR, not this one.

**A-5 · `.env` already exists on the machine.**
*If* `.env` exists and `--force` was not passed, `generate_env_file` logs and returns without touching it. *If* `--force` was passed and a `pgdata` volume already exists, `die` with an explicit message instead of regenerating: a new `POSTGRES_PASSWORD` against an initialised volume locks the backend out permanently, because the Postgres image only applies `POSTGRES_PASSWORD` on first initialisation. Tell the user to run `docker compose down -v` first and warn that this destroys all findings.

**A-6 · Certificates partially exist.**
*If* some but not all of `server.crt`, `server.key`, `agent-ca.crt`, `agent-ca.key` exist, `die` and tell the user to pass `--force` or clean `deploy/tls/` manually. Do not fill in only the missing ones — a server cert paired with a regenerated agent CA breaks `ssl_verify_client on` on the `agent.ecdat.local` virtual host in a way that surfaces much later as a confusing handshake failure.

**A-7 · The port is occupied.**
*If* `ECDAT_HTTPS_PORT` (default `8443`) is in use, `die` with the occupying port named and suggest `--https-port`. Do not auto-select a free port: the printed dashboard URL, `README.md` §5.3 and `.github/workflows/install-smoke.yml` would then disagree with reality.

**A-8 · Air-gapped or offline install (Step 1 open question 3).**
**Not covered by the contract — this is a genuine gap, and no resolution is invented here.** *If* `docker compose up -d --build` fails because `npm ci` in `dashboard/Dockerfile` or `pip install` in `Dockerfile` cannot reach a registry, `die` with a message stating the installer assumes an online build and that prebuilt image bundles are not implemented. Do not add a vendored-dependency path, an offline mirror flag, or a registry fallback. **Stop and ask a human** (AGENT_RULES #4).

**A-9 · `scripts/install.ps1` scheduling (Step 1 open question 1).**
Contract §1.5 allocates the path to INS as SOLE, so the file is in this spec's scope. *If* the team wants to ship `install.sh` first and defer the PowerShell mirror, that is a human scheduling decision — record it in the PR and leave the path unclaimed rather than creating a stub. An agent must not decide this alone.

**A-10 · ShellCheck pin unavailable.**
*If* `koalaman/shellcheck:v0.10.0` cannot be pulled in CI, fail the job. Do not substitute `latest`, do not switch to `apt-get install shellcheck`, and do not delete the lint step — an unpinned linter silently changes what passes between runs.

**A-11 · `docker compose` v1 (`docker-compose`, hyphenated) is what is installed.**
*If* `docker compose version` fails but `docker-compose --version` succeeds, `die`. The v1 binary does not support `--wait`, and contract §1.5 and the existing `docker-compose.yml` assume Compose v2. Do not add a v1 compatibility path.

**A-12 · `--wait` reports success but `/api/health` does not answer.**
This is expected in one specific case and is the reason the health check is separate: the `gateway` service declares no `HEALTHCHECK`, so `--wait` considers it ready as soon as it is running, even if nginx has exited because a TLS bind mount resolved to a directory. *If* `wait_for_health` exhausts its retries, `die` and print `docker compose logs gateway` as the next step. Do not extend the retry count to mask it, and do not add a healthcheck to `docker-compose.yml` — that file is COORDINATED to the deploy lane (R-5).

**A-13 · `scripts/` does not exist, and `scripts/generate_demo_repo.py` is referenced but absent.**
Create `scripts/` and add only `install.sh` and `install.ps1`. `README.md` line 121 and `ARCHITECTURE.md` line 89 both describe `scripts/generate_demo_repo.py` as existing; it does not. Report the discrepancy in the PR description per AGENT_RULES #9 and leave it to the scope-truth pass in Wave 4. **Do not create it, stub it, or correct the two documents' claims about it** — `ARCHITECTURE.md` is out of bounds under C-19.

**A-14 · The CI fixture `demos/ecdat-live-demo` is missing.**
`.github/workflows/ecdat-scan.yml` mounts `$GITHUB_WORKSPACE/demos/ecdat-live-demo`, which does not exist in the repository. *If* `install-smoke.yml` appears to need it, it does not — the smoke workflow in §7.8 references no fixture. Report the missing fixture to the CI lane; do not create it, and do not modify `.github/workflows/ecdat-scan.yml`, which is COORDINATED to the CI lane.

**A-15 · A migration mount was added to `docker-compose.yml` between Wave 1 and Wave 3.**
Expected, per C-01 — five features each land one. *If* the installer contains any assertion about the initdb mount list, remove it. `install-smoke.yml`'s only database assertion is §7.9's `to_regclass` check over the five tables that exist today, which stays true as tables are added.

**A-16 · `openssl` lacks `-addext`.**
*If* `openssl req -addext` is rejected (OpenSSL < 1.1.1, e.g. LibreSSL on older macOS), `die` in preflight with the detected version. Do not fall back to generating a temporary `openssl.cnf`: a SAN-less certificate makes the gateway unusable in modern browsers and would make the demo fail in front of a judge rather than at install time.

---

## 12. Test Plan / Definition of Done

Run every command below, in order, from a clean clone, per AGENT_RULES #7.

### 12.1 Static checks

```bash
bash -n scripts/install.sh
```
Expected: no output, exit 0.

```bash
docker run --rm -v "$PWD:/mnt:ro" -w /mnt koalaman/shellcheck:v0.10.0 --severity=style scripts/install.sh
```
Expected: no output, exit 0.

```bash
test -x scripts/install.sh && echo OK
```
Expected: `OK`

```bash
pwsh -NoProfile -Command "\$null = [System.Management.Automation.Language.Parser]::ParseFile('scripts/install.ps1', [ref]\$null, [ref]\$null); 'OK'"
```
Expected: `OK`

### 12.2 Help and argument handling

```bash
./scripts/install.sh --help; echo "exit=$?"
```
Expected: the §7.1 usage text, then `exit=0`.

```bash
./scripts/install.sh --nonsense; echo "exit=$?"
```
Expected: an error on stderr naming the unknown flag, then `exit=1`. **Never `exit=2`** (§9.3).

### 12.3 Fresh install

```bash
git clone <repo-url> ecdat-fresh && cd ecdat-fresh
./scripts/install.sh; echo "exit=$?"
```
Expected final stdout, verbatim per §7.10:

```text
ECDAT is running.

  Dashboard   https://localhost:8443/
  Health      https://localhost:8443/api/health
  CLI image   ecdat-scanner:local

Sample scan:

  docker run --rm -v "$PWD":/target:ro \
    --entrypoint python ecdat-scanner:local \
    -m scanner.cli /target --fail-on HIGH

The generated certificate is self-signed and for local development only.
See docs/SECURE_DEPLOYMENT.md before any non-local deployment.
```
followed by `exit=0`.

### 12.4 Generated artefacts

```bash
stat -c '%a' .env
```
Expected: `600`

```bash
stat -c '%a' deploy/tls/server.key deploy/tls/agent-ca.key
```
Expected: `600` on both lines.

```bash
grep -c '^POSTGRES_PASSWORD=replace-with' .env; grep -c '^API_KEY=replace-with' .env
```
Expected: `0` and `0`.

```bash
openssl x509 -in deploy/tls/server.crt -noout -ext subjectAltName
```
Expected output contains `DNS:localhost`, `DNS:agent.ecdat.local` and `IP Address:127.0.0.1`.

```bash
openssl x509 -in deploy/tls/agent-ca.crt -noout -ext basicConstraints
```
Expected output contains `CA:TRUE`.

```bash
git status --porcelain .env deploy/tls/
```
Expected: no output — every generated file is covered by `.gitignore`.

### 12.5 Running stack

```bash
docker compose ps --format '{{.Service}} {{.State}}'
```
Expected, in any order:
```text
backend running
dashboard running
db running
gateway running
```

```bash
curl --fail --silent --insecure https://localhost:8443/api/health
```
Expected: `{"status":"ok","version":"1.0.0"}`

```bash
curl --silent --insecure -o /dev/null -w '%{http_code}\n' https://localhost:8443/
```
Expected: `200` (the dashboard SPA — confirming why `/health` alone is the wrong probe, C-21).

```bash
docker compose exec -T db psql -U ecdat -d ecdat -tAc "SELECT to_regclass('public.findings') IS NOT NULL;"
```
Expected: `t`

```bash
docker image inspect ecdat-scanner:local --format '{{.Id}}' >/dev/null && echo OK
```
Expected: `OK`

### 12.6 Idempotency

```bash
./scripts/install.sh; echo "exit=$?"
```
Expected: `exit=0`, log lines reporting that `.env` and the TLS material already exist, and identical secrets afterwards:

```bash
sha256sum .env deploy/tls/server.crt > /tmp/before && ./scripts/install.sh >/dev/null && sha256sum -c /tmp/before
```
Expected: `.env: OK` and `deploy/tls/server.crt: OK`.

### 12.7 Guard rails

```bash
./scripts/install.sh --force; echo "exit=$?"
```
Expected with an existing `pgdata` volume: `exit=1` and a message naming `docker compose down -v` and warning of data loss (A-5).

```bash
python3 -c "import socket;s=socket.socket();s.bind(('',8443));s.listen();input()" &
./scripts/install.sh; echo "exit=$?"
```
Expected: `exit=1`, preflight failure naming port `8443` and suggesting `--https-port` (A-7).

### 12.8 Existing suites must still pass

```bash
docker build --tag ecdat-spec-check .
docker run --rm -e API_KEY=ci-test-key -e REPORT_SYNC_REQUIRE_MTLS=false \
  --entrypoint python ecdat-spec-check -m pytest -q --disable-warnings --maxfail=1
```
Expected: all tests pass, exit 0. INS changes no Python, so any failure here is a pre-existing defect or a predecessor's regression — report it, do not fix it in this PR.

### 12.9 Ownership audit

```bash
git diff --name-only main...HEAD
```
Expected, exactly and nothing more:
```text
.github/workflows/install-smoke.yml
README.md
docs/ECDAT_CLI_GUIDE.md
docs/SECURE_DEPLOYMENT.md
scripts/install.ps1
scripts/install.sh
```
(`.env.example` may appear if step 15 was taken.) Any other path is an AGENT_RULES #2 violation — revert it.

### 12.10 Definition of Done

- [ ] Every command in §12.1–§12.9 produces the stated output.
- [ ] `.github/workflows/install-smoke.yml` is green on the feature branch.
- [ ] `git diff --name-only` matches §12.9 exactly.
- [ ] No new environment variable exists anywhere in the diff (§9.1).
- [ ] No migration file, schema change, or `docker-compose.yml` edit exists in the diff (R-5).
- [ ] `PRODUCT_DESCRIPTION.md` and `ARCHITECTURE.md` are untouched (R-10).
- [ ] The `docs/ECDAT_CLI_GUIDE.md` edit has scanner-lane approval (R-8).
- [ ] The open items in §11 A-1 to A-4 and A-8 are listed unchanged in the PR description, with no resolution asserted.
- [ ] Reviewer sign-off row in §1 is filled in.

---

## 13. Rollback Plan

INS is additive: it creates three files, edits three documents, and introduces no runtime code, no dependency, no schema change and no environment variable. Nothing imports it. Rollback is therefore a clean file-level revert, and the build cannot be broken by INS in a way that survives it.

**If `.github/workflows/install-smoke.yml` fails or flakes and blocks merges:**
```bash
git rm .github/workflows/install-smoke.yml
git commit -m "INS: remove install smoke workflow pending fix"
```
This is the safest first move, because the workflow is the only INS artefact that can block anyone else's PR. `.github/workflows/ecdat-scan.yml` is a separate workflow owned by the CI lane and is unaffected.

**If the installer itself is broken:**
```bash
git revert --no-commit <install-script-merge-sha>
git commit -m "INS: revert install script"
```
The repository returns to the manual `cp .env.example .env` + `docker compose up -d` path documented in `README.md` §5.3 today. That path is already known to fail at the gateway on a clean clone (missing `deploy/tls/*`), so reverting restores the previous, worse state rather than a working one — flag this to the team rather than treating the revert as a fix.

**Recovering a developer machine the installer left in a bad state:**
```bash
docker compose down            # stop; keeps pgdata and all findings
rm -f .env
rm -f deploy/tls/server.crt deploy/tls/server.key \
      deploy/tls/agent-ca.crt deploy/tls/agent-ca.key
```
`docker compose down -v` additionally destroys the `pgdata` volume and every persisted finding. Use it only when the database must be reinitialised (for example after A-5's password-mismatch lockout), and say so out loud before running it during demo preparation.

**Partial rollback of the documentation edits:**
```bash
git checkout main -- README.md docs/SECURE_DEPLOYMENT.md docs/ECDAT_CLI_GUIDE.md
```
Note that reverting `README.md` restores `https://localhost:8443/health`, which C-21 identifies as incorrect — it reaches the dashboard SPA, not the backend. If the installer is reverted but the health-URL correction is still wanted, keep the `README.md` change and revert only `scripts/`.

**What rollback does not require:** no database migration to undo (INS authors none), no `requirements.txt` change to unwind (C-18, R-11), no `docker-compose.yml` change to unwind (C-01, R-5), and no coordination with RBAC, CLI or any Wave 3 peer — nothing depends on INS.
