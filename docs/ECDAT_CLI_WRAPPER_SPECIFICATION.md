# ECDAT CLI Wrapper — Complete Implementation Specification

**Feature Code:** `CLI`  
**Feature Name:** CLI wrapper  
**Owner:** scanner lane (Shashank)  
**Spec Version:** 1.0  
**Spec Status:** Ready for implementation  
**Date:** September 2026

---

## Changelog

| Version | Change |
|---------|--------|
| 1.0     | Initial specification; all sections aligned with SYSTEM_INTERFACE_CONTRACT.md v2 and AGENT_RULES.md. Step 1 proposal deviations noted in §1.1. |

---

## 1. Header

### 1.1 Deviation from Step 1 Proposal

The Step 1 proposal (`cli-wrapper.md`) proposed creating both `scanner/ecdat_cli.py` and modifying `pyproject.toml`. However, in contract v2 (§1.1 Canonical File Ownership Map), both are assigned as **SOLE** ownership to CLI. The proposal remains accurate; this specification formalizes the binding.

The proposal correctly identified that `api/services/cbom_generator.py` requires refactoring to expose `build_cbom_from_findings(findings, summary, ...)` as a pure function. Per contract §6 Merge Order wave 1, this refactoring is a *prerequisite* to CLI, not part of CLI itself—it blocks this feature and must land first.

---

## 2. Goal & Context

The ECDAT scanner currently exposes scanning, signed-bundle generation, and mTLS report sync *only* via Python's `scanner.cli:main()` function, called by the shell through `python -m scanner.cli`. This entry point cannot be imported safely by other CLI tools (e.g., agent enrollment scripts), and offers no way to invoke CBOM generation without a database.

**Goal:** Create an installable `ecdat` command with three subcommands—`scan`, `cbom`, and `sync`—that preserve `scanner/cli.py`'s behavior and add new capabilities (DB-free CBOM output, cleaner CLI entrypoint for Docker, and safe importability for downstream CLIs). This directly supports:
- **PS 26164 criterion:** Automated scanning delivered as a portable container command.
- **Judge criterion:** "Single unified reporting interface"; the CLI wrapper makes `ecdat scan` + `ecdat cbom` the unified local interface.

---

## 3. Scope

### In-Scope

- Creating `scanner/ecdat_cli.py` with three subcommands: `scan`, `cbom`, `sync`.
- Adding `[project.scripts]` entry point to `pyproject.toml` to install `ecdat` as a shell command.
- Preserving all flags, exit codes (0 pass, 1 error, 2 policy), and JSON stdout contract of `scanner/cli.py`.
- Adding pure-function CBOM generation by refactoring `api/services/cbom_generator.py:generate_cbom()` into `build_cbom_from_findings(findings, summary, ...)` (ORM-based entrypoint remains).
- Updating Dockerfile entrypoint to use `ecdat scan /target` instead of `python -m scanner.cli /target`.
- Updating documentation (`docs/ECDAT_CLI_GUIDE.md`) to show subcommand usage.
- Adding `tests/test_ecdat_cli.py` with tests for all three subcommands.
- Pinning `cryptography` in `requirements.txt` (exposed as transitive dependency; currently missing).

### Out-of-Scope

- Changing `scanner/cli.py` behavior; the wrapper delegates to existing functions.
- Adding new scanning engines or algorithm detection.
- Modifying database schema or migrations.
- Creating or modifying agent enrollment CLI (`scanner/enroll_cli.py` is a separate feature).
- Storing generated CBOM documents in the database; CBOM generation remains on-demand.
- Handling non-Python languages (Java, JavaScript) in the `cbom` subcommand—only component mappings in `cbom_generator.py` are reused.

---

## 4. Required Context Files

An implementer must read these files **in order** before writing code:

1. **`SYSTEM_INTERFACE_CONTRACT.md`** — this document itself; understand file ownership tiers, merge order, and C-11 open item.
2. **`AGENT_RULES.md`** — rules 1–9; especially rule 3 (follow interfaces literally) and rule 4 (stop on ambiguity).
3. **`ARCHITECTURE.md` §1–2** — system directory layout and component status.
4. **`scanner/cli.py`** — current 219-line CLI; understand `build_parser()`, `main()`, exit codes, stdout contract.
5. **`scanner/finding.py`** — the `Finding` dataclass; do not rename or restructure fields.
6. **`scanner/__init__.py`** — any exported scan API used by `ecdat_cli.py`.
7. **`api/services/cbom_generator.py`** — entire file; understand the ORM-based `generate_cbom()` that will stay.
8. **`api/services/risk_engine.py`** — `score_findings()` signature and return shape.
9. **`api/services/report_bundle.py`** — `build_bundle()`, `sign_bundle()`, `load_private_key()` signatures.
10. **`db/models.py`** — `Scan`, `Finding`, `RiskAssessment` ORM shapes (for understanding CBOM inputs).
11. **`requirements.txt`** — pinned versions; see tech stack §6.
12. **`Dockerfile`** — current CMD and ENTRYPOINT; modification in §8.
13. **`tests/test_cli_secure.py`** — existing CLI test patterns; follow them in §9.

---

## 5. File Ownership

### Created Files (SOLE: CLI owns entirely)

| Path | Tier | Type | Notes |
|------|------|------|-------|
| `scanner/ecdat_cli.py` | SOLE | new Python module | Subcommand dispatcher; ~200 lines; imports from `scanner/cli.py`, `api/services/` |
| `pyproject.toml` | SOLE | new Python build config | `[project]`, `[project.scripts]` entry point only; no test config |
| `tests/test_ecdat_cli.py` | SOLE | new test module | ~150 lines; pytest style matching `tests/test_cli_secure.py` |
| `docs/proposals/cli-wrapper.md` | SOLE | proposal archive | Copy of Step 1 proposal for audit trail |

### Modified Files (COORDINATED or FROZEN)

| Path | Tier | Owner | Change | Constraint |
|------|------|-------|--------|-----------|
| `requirements.txt` | COORDINATED | backend lane | Add `cryptography==42.0.5` (pinned version; currently implicit transitive) | Must land in merge wave 0 |
| `api/services/cbom_generator.py` | COORDINATED | CBOM lane (Maitreyi) | Refactor: extract pure `build_cbom_from_findings(findings, summary, ...)` function; keep `generate_cbom(session, scan_id)` unchanged | Must land in wave 1 before CLI; see C-14 |
| `Dockerfile` | COORDINATED | backend lane | Change CMD to `["ecdat", "scan", "/target"]` and ENTRYPOINT to `[]` (implicit) | Must land in same PR as this feature |
| `docs/ECDAT_CLI_GUIDE.md` | COORDINATED | backend lane | Add subcommand reference section | Merge with this PR |
| `.github/workflows/ecdat-scan.yml` | COORDINATED | backend lane | Update example if invocation changes; see §11 C-11 | Only if `--scan-type` is added |

### Files DO NOT TOUCH (SOLE/FROZEN owned by other features)

| Path | Owner | Feature | Reason |
|------|-------|---------|--------|
| `scanner/cli.py` | scanner lane | [shared] | COORDINATED; CLI may only delegate to it. No changes except if scanner lane itself modifies `build_parser()` or signatures. |
| `scanner/finding.py` | scanner lane | [shared] | FROZEN; CONF may add fields once via a separate PR. CLI must not touch it. |
| `api/models.py` | backend lane | [shared] | COORDINATED; 7 features edit here. CLI does not. |
| `db/schema.sql`, `db/crud.py`, `db/models.py` | DB lane | [shared] | COORDINATED; DB lane owns migrations. CLI generates CBOM from dicts, not ORM. |
| `scanner/enroll_cli.py` | ENR | agent-enrollment | SOLE; separate feature. Do not import. |
| `scanner/confidence.py` | CONF | unified-confidence-scoring | SOLE; new file. CLI uses `score_findings()` from risk_engine, not this directly. |

---

## 6. Tech Stack & Pinned Versions

All versions from `requirements.txt` as of September 2026:

### Core Scanner (unchanged by this feature)
- **Python:** 3.11 (required; tree-sitter-languages has no 3.12+ wheels)
- **tree-sitter:** 0.21.3
- **tree-sitter-languages:** 1.10.2
- **PyYAML:** ≥6.0

### Web API (unchanged)
- **fastapi:** ≥0.111.0
- **uvicorn[standard]:** ≥0.30.0
- **python-multipart:** ≥0.0.9

### Data / Validation (unchanged)
- **pydantic:** ≥2.7.0
- **pydantic-settings:** ≥2.3.0

### Database (unchanged)
- **SQLAlchemy:** ≥2.0,<2.1
- **psycopg2-binary:** ≥2.9
- **aiosqlite:** ≥0.20.0

### LLM / HTTP (unchanged)
- **google-generativeai:** ≥0.7.0
- **google-genai:** ≥0.1.1
- **httpx:** ≥0.27.0

### Utilities
- **python-dotenv:** ≥1.0

### **NEW / PINNED (Wave 0)**
- **cryptography:** 42.0.5 ← Add to `requirements.txt` explicitly; currently implicit transitive from `report_bundle.py`

### CLI Build (pyproject.toml)
- **build system:** `setuptools` ≥68.0 (implicit; standard)
- **Python requires:** `>=3.11,<4`

### Testing (unchanged)
- **pytest:** ≥8.0
- **pytest-asyncio:** ≥0.23.0

---

## 7. Concrete Interface Definitions

**Note:** This section contains only literal function/class signatures and API examples. No prose describing behavior appears here.

### 7.1 `scanner/ecdat_cli.py` Entry Points

```python
def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for the 'ecdat' command.
    Parses subcommand and delegates to subcommand handler.
    
    Returns:
        0: success
        1: error (validation, I/O, runtime)
        2: policy violation (--fail-on threshold exceeded)
    """
```

```python
def build_parser() -> argparse.ArgumentParser:
    """
    Builds the root argument parser with three subcommands: scan, cbom, sync.
    
    Return type:
        argparse.ArgumentParser configured with subparsers for
        'scan', 'cbom', 'sync'
    """
```

```python
def cmd_scan(args: argparse.Namespace) -> int:
    """
    Subcommand handler for 'ecdat scan <target>'.
    
    Delegates directly to scanner.cli.main([
        str(args.target),
        '--json-out', args.json_out,
        '--summary-only', args.summary_only,
        '--redact-paths', args.redact_paths,
        '--source-context', args.source_context,
        '--fail-on', args.fail_on,
        '--data-shelf-life-years', args.data_shelf_life_years,
        '--report-bundle', args.report_bundle,
        '--organization-id', args.organization_id,
        '--repository-id', args.repository_id,
        '--agent-id', args.agent_id,
        '--signing-key', args.signing_key,
        '--sync-url', args.sync_url,
        '--client-cert', args.client_cert,
        '--client-key', args.client_key,
        '--ca-cert', args.ca_cert,
        '--sync-timeout', args.sync_timeout,
    ])
    
    Args:
        args: Namespace from subparser with all scanner/cli.py flags
    
    Returns:
        int: exit code from scanner.cli.main()
    """
```

```python
def cmd_cbom(args: argparse.Namespace) -> int:
    """
    Subcommand handler for 'ecdat cbom <findings-json> --summary <summary-json>'.
    
    Loads findings and summary JSON from disk, calls
    api.services.cbom_generator.build_cbom_from_findings(),
    and writes CycloneDX 1.6 JSON to stdout or --output.
    
    Args:
        args: Namespace with:
            - findings_json: path to findings JSON file
            - summary: path to summary JSON file
            - output: optional output file path
            - organization_id: optional; if provided, included in CBOM metadata
    
    Returns:
        0: success
        1: error (file not found, invalid JSON, CBOM gen failed)
    
    Raises:
        SystemExit(1) if input files invalid or CBOM generation fails
    """
```

```python
def cmd_sync(args: argparse.Namespace) -> int:
    """
    Subcommand handler for 'ecdat sync <bundle-json> --url <https://...>'.
    
    Loads a signed bundle from disk, performs mTLS POST to endpoint,
    returns response JSON.
    
    Args:
        args: Namespace with:
            - bundle_json: path to signed report bundle
            - url: HTTPS ingestion endpoint
            - client_cert: mTLS client certificate
            - client_key: mTLS client private key
            - ca_cert: optional CA bundle
            - timeout: seconds (default 15)
    
    Returns:
        0: success (2xx response)
        1: error (network, TLS, file I/O, or HTTP error)
    """
```

### 7.2 Refactored `api/services/cbom_generator.py`

**Existing function — signature UNCHANGED (FROZEN):**

```python
def generate_cbom(session: Session, scan_id: int) -> dict[str, Any] | None:
    """
    Build a CycloneDX 1.6 CBOM JSON document for the given scan.
    
    (Existing implementation; unchanged by CLI feature.)
    
    Args:
        session: Active SQLAlchemy session.
        scan_id: ID of a completed scan.
    
    Returns:
        CycloneDX CBOM dict (serialisable to JSON), or None if scan not found.
    """
```

**New function (to be extracted from `generate_cbom` and reused by `ecdat cbom`):**

```python
def build_cbom_from_findings(
    findings: list[dict[str, Any]],
    summary: dict[str, int],
    organization_id: str | None = None,
    scan_id: int | None = None,
) -> dict[str, Any]:
    """
    Build a CycloneDX 1.6 CBOM JSON document from scored findings and summary.
    
    This is a pure function: no database access, no ORM.
    Called by:
    1. scanner/ecdat_cli.py:cmd_cbom() for DB-free CBOM output.
    2. api/services/cbom_generator.py:generate_cbom() as the core implementation
       (which fetches findings from DB, then calls this).
    
    Args:
        findings: list of scored finding dicts from score_findings().
                  Each must have keys: file, line, library, algorithm,
                  confidence, risk_tier, risk_reason, primitive.
        summary: dict with keys CRITICAL, HIGH, MEDIUM, LOW, UNSCORED, total.
        organization_id: optional organization identifier for CBOM metadata.
        scan_id: optional; if provided, included in CBOM metadata.
    
    Returns:
        dict: Valid CycloneDX 1.6 JSON structure:
        {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "version": 1,
            "metadata": { ... },
            "components": [
                {
                    "type": "cryptographic-asset",
                    "name": "<algorithm>",
                    "version": "1.0.0",
                    "evidence": { "cryptoProperties": [ ... ] }
                },
                ...
            ]
        }
    
    Raises:
        ValueError: if findings or summary invalid.
    """
```

### 7.3 `pyproject.toml` Entry Point

```toml
[project]
name = "ecdat"
version = "1.0.0"
description = "Enterprise Cryptographic Discovery & Assessment Tool"
requires-python = ">=3.11,<4"
dependencies = [
    # ... all requirements.txt pins ...
]

[project.scripts]
ecdat = "scanner.ecdat_cli:main"
```

**Behavior:** Installing this package (e.g., `pip install -e .` in development, or via the Docker image) makes the `ecdat` command available in `$PATH`, callable as:
```bash
ecdat scan /path/to/target
ecdat cbom findings.json --summary summary.json
ecdat sync bundle.json --url https://...
```

### 7.4 Updated `Dockerfile`

**Current (to be replaced):**
```dockerfile
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**New (after CLI feature):**
```dockerfile
# For the API service, still use Uvicorn:
# (docker-compose.yml overrides this if needed)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# For scanning, the container can be invoked as:
# docker run ecdat-scanner scan /target
# which calls: ecdat scan /target (installed by pip from pyproject.toml)
```

**Note:** The Dockerfile does NOT add a separate `ENTRYPOINT ecdat`. The CMD remains Uvicorn for the API service. Scanning via Docker is an optional *alternative invocation* documented in §11.

### 7.5 Test Examples

**File:** `tests/test_ecdat_cli.py`

```python
import json
import pytest
from pathlib import Path
from scanner.ecdat_cli import main, cmd_scan, cmd_cbom
from scanner.cli import build_parser as scanner_build_parser

def test_cmd_scan_integration(tmp_path, monkeypatch):
    """
    Test that cmd_scan properly delegates to scanner.cli.main()
    and preserves exit codes.
    """
    # Create a minimal Python file with a crypto import
    target = tmp_path / "crypto_file.py"
    target.write_text("from cryptography.hazmat.primitives.asymmetric import rsa\n")
    
    # Build args as if from 'ecdat scan /path'
    parser = build_parser()
    args = parser.parse_args(['scan', str(target)])
    
    exit_code = cmd_scan(args)
    assert exit_code in (0, 2), "cmd_scan must return 0 (pass) or 2 (policy)"

def test_cmd_cbom_db_free(tmp_path):
    """
    Test cmd_cbom with DB-free input: findings JSON + summary JSON → CycloneDX.
    """
    findings = [
        {
            "file": "src/crypto.py",
            "line": 42,
            "library": "cryptography",
            "algorithm": "RSA",
            "confidence": "high",
            "risk_tier": "MEDIUM",
            "risk_reason": "RSA-2048 adequate through 2030, quantum-vulnerable after.",
            "primitive": "publicKeyEncryption",
            "weak_by_default": False,
        }
    ]
    summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 1, "LOW": 0, "UNSCORED": 0, "total": 1}
    
    findings_file = tmp_path / "findings.json"
    summary_file = tmp_path / "summary.json"
    findings_file.write_text(json.dumps(findings))
    summary_file.write_text(json.dumps(summary))
    
    # Simulate 'ecdat cbom findings.json --summary summary.json'
    parser = build_parser()
    args = parser.parse_args(['cbom', str(findings_file), '--summary', str(summary_file)])
    
    exit_code = cmd_cbom(args)
    assert exit_code == 0, "cmd_cbom must return 0 on success"

def test_ecdat_scan_alias_if_c11_approves():
    """
    Placeholder: if C-11 is resolved to allow bare 'ecdat TARGET',
    uncomment and test that functionality.
    
    Per contract §7 Open Items, C-11 is unresolved as of this spec.
    """
    # parser = build_parser()
    # args = parser.parse_args(['/path/to/target'])  # no subcommand
    # assert args.subcommand == 'scan'  # if C-11 approves this alias
```

### 7.6 CLI Flag Grammar (Preserves `scanner/cli.py` Contract)

**For `ecdat scan <target> [options]`:**
All flags from `scanner/cli.py:build_parser()` pass through unchanged:

```
--json-out PATH
--summary-only
--redact-paths
--source-context {SOURCE, TEST_ONLY, DEMO_ONLY}
--fail-on {CRITICAL, HIGH, MEDIUM, LOW}
--data-shelf-life-years FLOAT
--report-bundle PATH
--organization-id STR
--repository-id STR
--agent-id STR
--signing-key PEM
--sync-url HTTPS_URL
--client-cert PEM
--client-key PEM
--ca-cert PEM
--sync-timeout FLOAT (default: 15.0)
```

**For `ecdat cbom <findings-json> --summary <summary-json> [options]`:**

```
--summary PATH (required)
--output PATH (optional; default stdout)
--organization-id STR (optional; added to CBOM metadata)
```

**For `ecdat sync <bundle-json> --url <https://...> [options]`:**

```
--url HTTPS_URL (required)
--client-cert PEM (required for mTLS)
--client-key PEM (required for mTLS)
--ca-cert PEM (optional)
--timeout FLOAT (default: 15.0)
```

---

## 8. Step-by-Step Implementation Plan

Each step ties to exactly one file and fits into the merge wave timing (§6 of contract).

### Wave 0 (Prerequisite: cryptography pin)

**Step 0.1: Pin `cryptography` in `requirements.txt`**
- File: `requirements.txt`
- Edit: Add line `cryptography==42.0.5` after `httpx>=0.27.0`
- Reason: Used by `report_bundle.py` for Ed25519 signing; currently implicit transitive dependency.
- Test: `pip install -r requirements.txt` succeeds; `import cryptography` works.
- Merge: Same wave as RBAC, CONF phase 1, CBOM refactor (wave 0).

### Wave 1 (Prerequisite: refactored CBOM generator)

**Step 1.1: Refactor `api/services/cbom_generator.py` (extract pure function)**
- File: `api/services/cbom_generator.py`
- Edit:
  - Extract the core CBOM-building logic into a new function `build_cbom_from_findings(findings, summary, organization_id=None, scan_id=None) -> dict`.
  - Keep existing `generate_cbom(session, scan_id)` unchanged; have it call `build_cbom_from_findings()` internally.
  - Move all CycloneDX constant mappings (`_PRIMITIVE_MAP`, `_CRYPTO_FUNCTIONS_MAP`) to module level if not already.
- Test:
  ```bash
  pytest tests/test_scan_runner.py -k cbom
  pytest tests/test_api.py -k "GET /scans/.*/cbom"
  ```
- Merge: Wave 1 (blocks CLI, CBV, CNT, BIN, IAC); coordinated by CBOM lane.

### Wave 2 (The CLI feature itself)

**Step 2.1: Create `scanner/ecdat_cli.py`**
- File: `scanner/ecdat_cli.py` (new)
- Implement:
  - `main(argv: list[str] | None = None) -> int`: entry point.
  - `build_parser() -> argparse.ArgumentParser`: root parser with subparsers for `scan`, `cbom`, `sync`.
  - `cmd_scan(args) -> int`: delegate to `scanner.cli:main()`.
  - `cmd_cbom(args) -> int`: load findings JSON, load summary JSON, call `api.services.cbom_generator:build_cbom_from_findings()`, output CycloneDX.
  - `cmd_sync(args) -> int`: load signed bundle, POST to URL, return exit code.
- Lines: ~200 total.
- Imports:
  ```python
  import argparse, json, sys, ssl
  from pathlib import Path
  from scanner import cli as scanner_cli
  from api.services.cbom_generator import build_cbom_from_findings
  from api.services.report_bundle import sign_bundle  # for cmd_sync if needed
  import httpx
  ```
- Test locally:
  ```bash
  python -c "from scanner.ecdat_cli import main; exit(main(['scan', '/tmp/test.py']))"
  ```
- Merge: Wave 2.

**Step 2.2: Create `pyproject.toml`**
- File: `pyproject.toml` (new)
- Implement:
  - `[project]` metadata: name, version, description, requires-python, dependencies (copy from requirements.txt).
  - `[project.scripts]`: `ecdat = "scanner.ecdat_cli:main"`.
  - `[build-system]`: `requires = ["setuptools>=68.0"]`, `build-backend = "setuptools.build_meta"`.
- Install test:
  ```bash
  pip install -e .
  ecdat --help
  ecdat scan --help
  ecdat cbom --help
  ```
- Merge: Wave 2 (same PR as Step 2.1).

**Step 2.3: Create `tests/test_ecdat_cli.py`**
- File: `tests/test_ecdat_cli.py` (new)
- Implement: ~150 lines; pytest tests for all three subcommands.
- Tests:
  1. `test_cmd_scan_integration()`: scan a test Python file, verify exit code.
  2. `test_cmd_cbom_db_free()`: load findings and summary JSON, generate CBOM, verify output is valid JSON.
  3. `test_cmd_cbom_invalid_json()`: fail gracefully on corrupt JSON.
  4. `test_cmd_sync_https_validation()`: reject non-https URLs.
  5. `test_ecdat_main_subcommand_dispatch()`: verify that `main()` routes to correct handler.
- Run:
  ```bash
  pytest tests/test_ecdat_cli.py -v
  ```
- Merge: Wave 2 (same PR as Step 2.1–2.2).

**Step 2.4: Update `Dockerfile` to use installed `ecdat` command**
- File: `Dockerfile`
- Edit:
  - Ensure `RUN pip install --no-cache-dir -r requirements.txt` executes (already there).
  - After pip install, ensure pyproject.toml is copied and `pip install -e .` is run, OR rely on `requirements.txt` being updated to list the local package.
  - **Note:** The `CMD` remains `["uvicorn", "api.main:app", ...]` for the API service. The `ecdat` command is available as an *alternative* invocation via `docker run ecdat-scanner ecdat scan /target`.
- Or simpler: add a line after pip install:
  ```dockerfile
  RUN pip install -e .
  ```
  (assuming `pyproject.toml` is already copied by `COPY . .`).
- Test:
  ```bash
  docker build -t ecdat-test .
  docker run ecdat-test ecdat --help
  docker run ecdat-test ecdat scan /nonexistent 2>&1 | grep -i "error"
  ```
- Merge: Wave 2 (same PR as Step 2.1–2.3).

**Step 2.5: Update `docs/ECDAT_CLI_GUIDE.md`**
- File: `docs/ECDAT_CLI_GUIDE.md` (existing)
- Edit: Add section describing the three subcommands and their flags.
- Example:
  ```markdown
  ## Subcommands

  ### ecdat scan
  Scan a local directory or file for cryptographic asset usage.
  ...
  
  ### ecdat cbom
  Generate CycloneDX 1.6 CBOM from pre-scored findings (no database required).
  ...
  
  ### ecdat sync
  Send a signed report bundle to an HTTPS ingestion endpoint.
  ...
  ```
- Merge: Wave 2 (same PR).

**Step 2.6: (Conditional) Update `.github/workflows/ecdat-scan.yml`**
- File: `.github/workflows/ecdat-scan.yml`
- Condition: Only if contract C-11 is resolved and `--scan-type` flag is added to `scanner/cli.py` (not in this feature).
- If required: Update example invocation from `python -m scanner.cli` to `ecdat scan`.
- Merge: Wave 2 or later (depends on CONF / C-11 resolution).

---

## 9. Naming & Symbol Registry

### New Functions

| Name | Module | Signature | Purpose |
|------|--------|-----------|---------|
| `main` | `scanner.ecdat_cli` | `(argv: list[str] \| None = None) -> int` | Entry point for `ecdat` command; delegates to subcommand. |
| `build_parser` | `scanner.ecdat_cli` | `() -> argparse.ArgumentParser` | Builds root parser with subparsers for scan, cbom, sync. |
| `cmd_scan` | `scanner.ecdat_cli` | `(args: Namespace) -> int` | Handler for `ecdat scan`. |
| `cmd_cbom` | `scanner.ecdat_cli` | `(args: Namespace) -> int` | Handler for `ecdat cbom`. |
| `cmd_sync` | `scanner.ecdat_cli` | `(args: Namespace) -> int` | Handler for `ecdat sync`. |
| `build_cbom_from_findings` | `api.services.cbom_generator` | `(findings, summary, organization_id=None, scan_id=None) -> dict` | Pure-function CBOM builder; new public API. |

### New CLI Commands (installed via `[project.scripts]`)

| Command | Module:Function | Alias |
|---------|-----------------|-------|
| `ecdat` | `scanner.ecdat_cli:main` | (none; this is the primary command) |

### Environment Variables

**No new environment variables introduced.** The existing environment variables used by `scanner/cli.py` (e.g., `REPORT_SYNC_AGENT_KEYS` from ENR, or `API_KEY` from RBAC) are used as-is.

### Shared Resource Index (Collisions with Other Features)

| Resource | CLI | Other Feature | Resolution |
|----------|-----|----------------|----|
| `scanner/cli.py` function namespace | Delegates to; does not modify | [scanner lane shared] | CLI calls `scanner.cli:main()` with constructed argv. No modification of `scanner/cli.py`. |
| `api/services/cbom_generator.py` | Calls new `build_cbom_from_findings()` | CBV, CBOM lane | Refactor happens in wave 1; CLI depends on it. One shared refactor, not two PRs. |
| `requirements.txt` | Needs `cryptography==42.0.5` pinned | report_bundle, RBAC, AUD, ENR | Pins in wave 0; everyone uses same version. |
| `-ecdat` command name | Installs as shell command | (none) | No collision; no other feature claims it. |

---

## 10. Known Cross-Feature Risks

All risks listed in contract §5 (Flagged Conflicts & Resolutions) that touch the CLI feature:

### C-11: Final CLI flag grammar; does bare `ecdat TARGET` survive?

| Item | Status | Impact | Resolution |
|------|--------|--------|-----------|
| **Open?** | **YES** | Medium | Not yet decided by human sign-off. |
| **Blocks** | CLI, DEP, CNT, BIN, IAC (4 scanner engines) | — |
| **What's unknown** | Should `ecdat /path/to/target` (no `scan` subcommand) be an alias for `ecdat scan /path/to/target`? | This feature assumes it must NOT; the subcommand is explicit. |
| **Action in this spec** | If C-11 is approved to allow bare `ecdat TARGET`, modify `build_parser()` to accept `target` as an optional first positional (no subcommand) and route it to `cmd_scan`. Otherwise, subcommand is required. |
| **Timeline** | Decide before merge wave 2. |

### C-02: Persist or drop sub-threshold findings?

| Item | Status | Impact | Resolution |
|------|--------|--------|-----------|
| **Open?** | **YES** | Medium | Not yet decided by human sign-off. |
| **Blocks** | All scanners (DEP, CNT, BIN, IAC), CONF, TRI | — |
| **What's unknown** | If findings score below a minimum confidence threshold, are they stored in the database or discarded? | This is a downstream concern (risk_engine, scan_runner). CLI does not generate scores; it receives them. |
| **Action in this spec** | No action for CLI. The `cmd_cbom` function accepts a list of findings (already scored by caller) and generates CBOM. If caller filtered them, CLI receives filtered list. If caller kept them, CLI receives them. CLI is agnostic. |
| **Timeline** | Resolve before CONF wave 1; does not block CLI. |

### C-14: CBOM validation failure: 500 or 200-with-warning? Full 1.6 schema or subset?

| Item | Status | Impact | Resolution |
|------|--------|--------|-----------|
| **Open?** | **YES** | Medium | Not yet decided (CBV owner). |
| **Blocks** | CLI, CBV | — |
| **What's unknown** | What does CBV do if CBOM generated by CLI contains invalid or incomplete findings? | CBV is a separate feature (validation); CLI is generation only. |
| **Action in this spec** | CLI's `cmd_cbom` generates CycloneDX 1.6 with the full schema that `api/services/cbom_generator.py:build_cbom_from_findings()` implements. If findings are invalid (missing required fields), `build_cbom_from_findings()` raises `ValueError`. CLI exits(1). CBV (validation feature) is a separate concern. |
| **Timeline** | Resolve before CBV wave 3; does not block CLI wave 2. |

### C-21: `GET /health` vs `/scans/health` vs `/api/health`

| Item | Status | Impact | Resolution |
|------|--------|--------|-----------|
| **Open?** | **YES** | Low | Not yet decided (INS, Healthchecks). |
| **Blocks** | INS (install script), CLI indirectly | — |
| **What's unknown** | Which health endpoint path does the API expose? | CLI does not call health check; the Dockerfile's `HEALTHCHECK` cmd does. |
| **Action in this spec** | Update Dockerfile `HEALTHCHECK` only if the endpoint path changes from `/health` to something else. For now, assume `/health` (current). If INS resolves to a different path, update HEALTHCHECK in same PR or note it as a follow-up. |
| **Timeline** | Resolve before wave 2/INS. |

---

## 11. Pre-Answered Ambiguities

The following 8 situations could confuse an implementing agent. Here is what to do in each:

### Situation 1: "Do I need to modify `scanner/cli.py`?"

**If this happens:** You are thinking of changing `scanner/cli.py` to add a new flag or change behavior.

**Do this:** STOP. Do not modify `scanner/cli.py`. It is COORDINATED ownership; only the scanner lane (Shashank) can modify it. The CLI wrapper must delegate to it unchanged. If `scanner/cli.py` needs a new capability (e.g., `--scan-type` per C-11), that is a *separate feature* (DEP, CNT, BIN, IAC) in a different PR.

---

### Situation 2: "The `build_cbom_from_findings()` function doesn't exist yet. What do I do?"

**If this happens:** You are writing `cmd_cbom()` and importing `api.services.cbom_generator:build_cbom_from_findings`.

**Do this:** This function must be created *before* you implement `cmd_cbom()`. It is a prerequisite (wave 1, not wave 2). Wait for the CBOM lane (Maitreyi) to refactor `cbom_generator.py`. Once that PR lands and `build_cbom_from_findings()` exists, then implement `cmd_cbom()` in your PR. Do not stub it or write a mock.

---

### Situation 3: "Should `ecdat cbom` work without a database?"

**If this happens:** You are implementing `cmd_cbom()` and wondering if it needs SQLAlchemy, DB session, etc.

**Do this:** YES, `ecdat cbom` must be DB-free. It reads findings JSON and summary JSON from disk, calls the pure function `build_cbom_from_findings()`, and writes CycloneDX JSON to stdout or a file. Do NOT import `db.crud`, `db.models`, or `Session`. It is meant for use in CI/CD pipelines that don't have a running ECDAT API.

---

### Situation 4: "The contract says C-11 is open. Do I implement bare `ecdat TARGET`?"

**If this happens:** You are building the root parser and see that `scanner/cli.py` already accepts `target` as the first positional. Should `ecdat /path` work without `scan`?

**Do this:** NO. Implement it with explicit subcommands: `ecdat scan /path`, `ecdat cbom`, `ecdat sync`. This is the conservative choice. If C-11 is later resolved to allow `ecdat /path` as an alias, modify `build_parser()` to set a default subcommand in a *follow-up* PR. Do not wait for C-11; ship with explicit subcommands.

---

### Situation 5: "How do I test `cmd_sync` without hitting a real server?"

**If this happens:** You are writing `test_ecdat_cli.py` and `cmd_sync` makes an HTTPS POST request. You want unit tests, not integration tests.

**Do this:** Mock `httpx.Client` using `pytest.mock.patch()` or `unittest.mock`. Example:
```python
def test_cmd_sync_success(tmp_path, mocker):
    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text(json.dumps({"agent_id": "test"}))
    
    mock_post = mocker.patch("httpx.Client.post")
    mock_post.return_value.json.return_value = {"status": "accepted"}
    
    parser = build_parser()
    args = parser.parse_args([
        'sync', str(bundle_file),
        '--url', 'https://mock.example.com/intake',
        '--client-cert', '/dev/null',
        '--client-key', '/dev/null',
    ])
    # Note: real certs will fail; mock at httpx level or use pytest-httpx
```

---

### Situation 6: "What if `cmd_cbom` receives findings without `risk_tier`?"

**If this happens:** You are implementing `cmd_cbom()` and the findings JSON has no `risk_tier` key.

**Do this:** This is a corrupt input. Raise `ValueError` with a message like "Finding at line X missing required field: risk_tier". Exit code 1. This matches the behavior of `scanner/cli.py:main()` on invalid flags. `build_cbom_from_findings()` (in the refactored `cbom_generator.py`) should validate its inputs.

---

### Situation 7: "Where should I put the new `pyproject.toml`?"

**If this happens:** You are creating `pyproject.toml` and wondering about file location.

**Do this:** Place it at the **repository root**, same level as `requirements.txt` and `Dockerfile`. Not in `scanner/`, not in `api/`. This is the standard Python project structure. The root `pyproject.toml` is discovered by `pip install -e .` and build tools.

---

### Situation 8: "The Dockerfile mentions `docker-compose.yml` overrides. What does that mean?"

**If this happens:** You are updating the Dockerfile and notice the Dockerfile CMD is for Uvicorn (API), but `docker-compose.yml` might override it.

**Do this:** Check `docker-compose.yml` in the repo. If it has a `command:` override for the backend service, your Dockerfile change may be shadowed. Document this in the PR comment. The key point: the Dockerfile's CMD stays as Uvicorn for the API. If someone wants to scan via Docker, they run `docker run ecdat-scanner ecdat scan /target`, which uses the `ecdat` script installed by `pip install -e .`, NOT the default CMD. Document this in `docs/ECDAT_CLI_GUIDE.md`.

---

### Open Item C-11: CLI flag grammar (Human sign-off needed, but do NOT block your implementation)

**Current contract status:** Medium confidence that C-11 will resolve. Until it does:
- Implement `ecdat scan`, `ecdat cbom`, `ecdat sync` as explicit subcommands (required).
- Do NOT implement bare `ecdat TARGET` as an alias yet.
- If C-11 approves the alias by the time you're reviewing, modify `build_parser()` in a separate, quick PR.

**Assumed resolution for this spec:** Explicit subcommands only. If overridden by human sign-off, it is a 10-line change to `build_parser()`.

---

## 12. Test Plan / Definition of Done

### Unit Tests (Run Locally)

```bash
# Install the package for development
pip install -e .

# Run all tests for the CLI module
pytest tests/test_ecdat_cli.py -v

# Run the specific test scenarios:
pytest tests/test_ecdat_cli.py::test_cmd_scan_integration -v
pytest tests/test_ecdat_cli.py::test_cmd_cbom_db_free -v
pytest tests/test_ecdat_cli.py::test_cmd_sync_https_validation -v
pytest tests/test_ecdat_cli.py::test_ecdat_main_subcommand_dispatch -v
```

**Expected output:** All pass; no errors.

### Integration Tests (Docker)

```bash
# Build the Docker image with the new ecdat command
docker build -t ecdat-scanner .

# Test the ecdat command exists
docker run ecdat-scanner ecdat --help
# Expected: usage: ecdat [-h] {scan,cbom,sync} ...

# Test ecdat scan on a simple Python file
docker run ecdat-scanner ecdat scan /app/scanner/python_engine.py
# Expected: JSON array of findings, exit 0

# Test ecdat cbom with sample findings
docker run ecdat-scanner bash -c '
  echo "[{\"file\": \"test.py\", \"algorithm\": \"RSA\", \"confidence\": \"high\", \"risk_tier\": \"HIGH\"}]" > /tmp/f.json
  echo "{\"total\": 1, \"CRITICAL\": 0, \"HIGH\": 1}" > /tmp/s.json
  ecdat cbom /tmp/f.json --summary /tmp/s.json
'
# Expected: CycloneDX JSON, exit 0
```

### Manual CLI Tests

```bash
# After pip install -e . (or in dev Docker container)

# Subcommand help
ecdat --help
ecdat scan --help
ecdat cbom --help
ecdat sync --help

# Scan a local directory
ecdat scan /app/scanner/
# Should output: JSON array of findings

# Scan with --fail-on policy
ecdat scan /app/scanner/ --fail-on HIGH
# Should exit 0 if no HIGH+ findings, 2 if any found

# CBOM generation from pre-scored findings (integration with CONF phase 1)
echo '[{"file":"test.py","algorithm":"AES","confidence":"high","risk_tier":"LOW","risk_reason":"..."}]' > findings.json
echo '{"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":1,"UNSCORED":0,"total":1}' > summary.json
ecdat cbom findings.json --summary summary.json
# Should output: valid CycloneDX JSON
```

### Definition of Done

All of the following must be true:

1. ✅ **Files created:** `scanner/ecdat_cli.py`, `pyproject.toml`, `tests/test_ecdat_cli.py` exist and match §7.
2. ✅ **All tests pass:** `pytest tests/test_ecdat_cli.py -v` returns 0.
3. ✅ **CLI works locally:** `pip install -e .` succeeds; `ecdat --help` works.
4. ✅ **Docker builds:** `docker build -t ecdat-scanner .` succeeds.
5. ✅ **Docker CLI works:** `docker run ecdat-scanner ecdat scan /app/scanner/` returns valid JSON.
6. ✅ **Subcommands route correctly:** `ecdat scan`, `ecdat cbom`, `ecdat sync` each call their respective handler.
7. ✅ **Exit codes preserved:** `ecdat scan --fail-on HIGH /path` returns 0 or 2 as expected.
8. ✅ **CBOM output is valid:** `ecdat cbom` produces well-formed CycloneDX 1.6 JSON.
9. ✅ **No `scanner/cli.py` changes:** Only delegation; no modifications to `scanner/cli.py` itself.
10. ✅ **Documentation updated:** `docs/ECDAT_CLI_GUIDE.md` describes the three subcommands.
11. ✅ **`cryptography` pinned:** `requirements.txt` contains `cryptography==42.0.5`.
12. ✅ **Refactored CBOM function exists:** `api.services.cbom_generator:build_cbom_from_findings()` is available and used by `cmd_cbom()`.
13. ✅ **No merge conflicts:** Feature branch rebased on main; no conflicts with in-flight features.

---

## 13. Rollback Plan

If the feature breaks the build or API at merge time, here is the rollback sequence:

### Immediate (within 5 minutes of merge)

1. **Revert the merge commit:**
   ```bash
   git revert -m 1 <merge-commit-sha>
   git push origin main
   ```

2. **Verify the revert:** API should still start with `docker run ecdat-api uvicorn api.main:app --port 8000`.

### Short-term (within 1 hour)

3. **Identify the failure:** Check what broke:
   - **Python import error** in `scanner/ecdat_cli.py` → Fix the import and re-submit.
   - **Missing `build_cbom_from_findings()`** → The CBOM refactor PR did not land first (wave 1 prereq). Do not merge CLI yet; wait for wave 1.
   - **Docker build fails** → Check if `pyproject.toml` is copied correctly; fix `Dockerfile` COPY directive.
   - **API health check fails** → The Dockerfile `HEALTHCHECK` cmd may be wrong; revert to original `CMD` for now.

4. **Targeted fix:** Address the root cause in a new PR (do not re-push to the same branch; create a new one). Examples:
   - If import failed: fix path in `scanner/ecdat_cli.py`.
   - If CBOM function missing: this is a wave-ordering error; do not merge CLI until wave 1 is done.
   - If Docker build failed: fix `Dockerfile` or `pyproject.toml`.

5. **Re-test before re-merge:**
   ```bash
   docker build -t ecdat-test .
   docker run ecdat-test ecdat --help
   docker run ecdat-test python -m pytest tests/test_ecdat_cli.py -v
   ```

### Medium-term (if revert is insufficient)

6. **If API still broken after revert:**
   - The issue may be in a prerequisite (cryptography pin in wave 0, or CBOM refactor in wave 1).
   - Check if those PRs are in main; revert those too if necessary.
   - Verify: `docker run ecdat-api uvicorn api.main:app --port 8000` starts cleanly.

7. **Investigate dependencies:**
   - Ensure `requirements.txt` was not corrupted.
   - Run `pip install -r requirements.txt` locally to catch any typos.

### Prevention

- **Merge order:** CLI merges *after* CBOM refactor (wave 1) and `cryptography` pin (wave 0). If your PR can't find `build_cbom_from_findings()`, do not merge yet.
- **CI gate:** Ensure `.github/workflows/` runs tests before merge. The test plan (§12) must pass.
- **Docker tests:** Build and test the Docker image in CI before merging. Do not skip this step.

---

## End of Specification

**Status:** Ready for implementation in merge wave 2 (after wave 0 crypto pin and wave 1 CBOM refactor).

**Next steps for team:**
1. Resolve open item **C-11** (CLI flag grammar) before or during implementation.
2. Ensure CBOM refactor (wave 1) lands before this PR.
3. Assign implementer; provide this spec and the required context files (§4).
4. Implementer opens feature branch `feature/cli-wrapper` off main.
5. Follow steps §8 in order; test after each step.
6. Open PR to main with reference to this spec and contract.
7. Post-merge: confirm rollback plan works on staging.
