# SPEC — Dependency Scanning (`DEP`)

## 1. Header

| Field | Value |
|---|---|
| **Feature name** | `dependency-scanning` — feature code **`DEP`** (contract §0). The request's `[FEATURE NAME]` placeholder was left unfilled; the feature is identified from the attached Step 1 proposal `dependency-scanning.md`. |
| **Owner** | **Not named in the contract.** No individual is assigned to `DEP`. Integration owners for the COORDINATED files this feature edits: scanner lane (Shashank), DB lane (Ronak), backend lane (Shreyanshi), deploy lane (unnamed). Risk/CBOM lane (Maitreyi) is consulted only (§11 G2). |
| **Spec version** | `1.0.0-draft` — 2026-09-20 |
| **Status** | **DRAFT — not startable until the §8 preconditions pass.** Merge position, quoted verbatim from contract §6: `\| **3** \| DEP · CNT · BIN · IAC (migration 003 as **one** shared PR) \| — \|`. Prerequisites in Waves 0–2 (contract §6): pin `cryptography`; RBAC; **CONF phase 1**; `cbom_generator` refactor; **CLI wrapper / `scanner/cli.py` `--scan-type` flag**; ENR; AUD; DFS. |
| **Governing documents** | `SYSTEM_INTERFACE_CONTRACT.md` (Draft v2, hard constraint) · `AGENT_RULES.md` (equally binding) |

### Reviewer sign-off

| Role | Person | Covers | Status |
|---|---|---|---|
| Scanner lane | Shashank | `scanner/cli.py`, `scanner/__init__.py`, G1 (Finding carrier), G8 | ☐ pending |
| DB lane | Ronak | `db/schema.sql`, `db/models.py`, `db/crud.py`, migration 003 | ☐ pending |
| Backend lane | Shreyanshi | `api/models.py` | ☐ pending |
| CBOM / risk lane | Maitreyi | G2, G5 (read-only consultation) | ☐ pending |
| CONF owner | *not named in contract* | G1, G12, A2, A3 | ☐ pending |
| Deploy lane | *not named in contract* | `docker-compose.yml` mount | ☐ pending |

### Changelog

**v1.0.0-draft** — first spec. Deviations from the Step 1 proposal (`dependency-scanning.md`), each forced by the contract:

| # | Step 1 said | This spec does | Reason |
|---|---|---|---|
| D-1 | Modify `api/services/scan_runner.py` "to consume expanded scanner output" | **Does not touch it** | Contract §1.2: `FROZEN`, owner CONF — "DEP/CNT/BIN/IAC must not touch it — see C-02" |
| D-2 | Modify `scanner/finding.py` "if dependency evidence requires new fields" | **Does not touch it** | Contract §1.1: `FROZEN` — "Only CONF may add fields, once — see C-03". Carrier for DEP's five columns is an open gap: §11 **G1** |
| D-3 | `db/models.py` / `db/schema.sql` / `db/crud.py`: "dependency fields/table if needed" | The **seven columns of migration 003 verbatim**; **no dependency table**; **no new query functions** ("query support" dropped) | Contract §2.2 / §3.8; §2.3 rejects new per-artefact tables; filters belong to C-16 / DFS, tenant filter to C-10 |
| D-4 | `scanner/cli.py`: "invoke dependency scanning and merge results" | Registers `dependency` under the **existing-by-then `--scan-type`** flag; adds **no flag**; default stays `source` only | Contract §3.5, C-11 |
| D-5 | `api/models.py`: "expose dependency metadata" | Five defaulted fields on `FindingOut`; no new models | Contract §1.2 (`api/models.py`, no `api/schemas/`) |
| D-6 | `tests/test_scan_runner.py`: "mixed source/dependency integration tests" | One **default-behaviour non-regression** test; mixed-mode coverage moves to CLI-level tests | `scan_runner` is FROZEN and forwards no scan type (§11 G9) |
| D-7 | `scanner/dependency_rules/`: "optional package-manager format rules" | Holds the **crypto-relevance rule pack** (which declared packages become findings) | Step 1 never says what qualifies as a finding; emitting every dependency would flood `findings`. Provisional — §11 G3 |
| D-8 | *(not in Step 1)* | Adds `artifact_ref` rewrite in `scanner/cli.py` | Without it `--redact-paths` leaks absolute paths through `artifact_ref` (§8 step 15) |
| D-9 | *(not in Step 1)* | Adds `docs/DEPENDENCY_SCANNING_SCOPE.md` | C-02: DEP "must say so in their scope docs"; C-19 forbids editing `PRODUCT_DESCRIPTION.md` |
| D-10 | Java "as an extension" | Kept, isolated to two conditional steps | Contract lists `maven` in `package_ecosystem`; demo need unresolved (§11 G6) |

---

## 2. Goal & Context

`DEP` adds a deterministic, offline, opt-in scan stage (`--scan-type dependency`) that reads local Python, Node.js and (conditionally) Maven manifest and lock files and emits one `Finding` per **declared cryptographic library** it recognises from a static rule pack, tagged `detection_method = "dependency_manifest"` and the migration-003 artefact columns, so third-party cryptographic libraries enter the same persistence, risk-scoring and CBOM flow as source-code findings. It serves **PS 26164 Requirement 1 (Discovery)** and the *libraries* part of **Requirement 2 (Identification)** (`README.md` §2 table) and implements the dependency-scanning item that `AGENT_RULES.md` #6 places in the current sprint scope. The evidence is a *declaration* in a manifest — it is not proof that any call site uses the library — and the spec never claims otherwise; source-code detection semantics, the risk engine and the default `source` CI gate are unchanged.

---

## 3. Scope

### In scope
- `scanner/dependency_engine.py` parsing exactly these file kinds: `requirements*.txt`, `pyproject.toml`, `Pipfile.lock`, `poetry.lock` (PyPI); `package.json`, `package-lock.json` (npm); `pom.xml` (Maven — conditional, §11 G6).
- A static, offline rule pack in `scanner/dependency_rules/` mapping `(ecosystem, normalised package name)` → `library`, `algorithm`, `primitive`, `weak_by_default`.
- Emitting `Finding`-compatible objects with `detection_method = "dependency_manifest"`, `artifact_type = "DEPENDENCY_MANIFEST"`, `artifact_ref`, `package_ecosystem`, `package_name`, `package_version` (contract §2.2).
- Engine entry points exactly as contract §3.1: `scan_file(path, rules=None)` and `scan_directory(root, rules=None)`.
- Registration of the `dependency` value of the `--scan-type` flag **that the Wave-2 CLI change already provides**; `scanner/cli.py` imports the engine lazily (inside the helper), so the default `source` path never *invokes* it; the module has no import-time side effects (no file access, rules load only inside `scan_file` / `scan_directory`).
- DEP's share of migration 003 (one shared file, one shared PR), mirrored in `db/schema.sql`, `db/models.py`, the `docker-compose.yml` initdb mount, `db/crud.py` key whitelist, and `api/models.py` `FindingOut`.
- Within-artefact de-duplication by the C-23 key.
- Tests (`tests/test_dependency_engine.py`, one addition to `tests/test_scan_runner.py`) and `docs/DEPENDENCY_SCANNING_SCOPE.md` stating the CLI-only / sub-`high` limits required by C-02.

### Out of scope
- **Any edit** to `scanner/finding.py`, `api/services/scan_runner.py`, `api/services/risk_engine.py` (FROZEN) or `scanner/constants.py`, `api/services/cbom_generator.py`, `requirements.txt` (not assigned to DEP).
- Vulnerability / CVE / advisory matching, registry or network access, subprocess calls to `pip`/`npm`/`mvn`, dependency *resolution*. (Step 1 assumption: local/offline.)
- Emitting non-cryptographic packages; SBOM export (§11 G3).
- Persisting a direct-vs-transitive distinction (§11 G4).
- CycloneDX component modelling of dependencies (§11 G5).
- `yarn.lock`, `pnpm-lock.yaml`, Gradle, Go, Cargo, NuGet, Ruby and all other ecosystems.
- Confidence banding (`scanner/confidence.py` is CONF's, SOLE) and the persist-vs-drop decision (C-02).
- API-triggered dependency scans via `POST /scans` (§11 G9).
- Dashboard work (`dashboard/**`), including package columns (CNT/DFS, C-13).
- Cross-engine de-duplication or grouping with CNT/BIN findings (C-23: retained as distinct evidence).
- Editing `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md`, `docs/SOURCE_SCANNING_SCOPE.md`, `docs/ECDAT_CLI_GUIDE.md` (C-19 / §11 G10).

---

## 4. Required Context Files

Read in this order before writing code. Every path below exists in the attached `ECDAT-main.zip` snapshot unless marked otherwise.

**Governing documents**
1. `SYSTEM_INTERFACE_CONTRACT.md` — attached to this task; **not present in the snapshot** (`ARCHITECTURE.md` §6 says it is not yet in the repo).
2. `AGENT_RULES.md`
3. `ARCHITECTURE.md` — §2.1 (Finding contract), §2.2 (API → DB contract)
4. `PRODUCT_DESCRIPTION.md`, `README.md` — read-only (C-19)
5. `dependency-scanning.md` — Step 1 proposal, attached; **not in the snapshot**

**Scanner lane**
6. `scanner/finding.py`
7. `scanner/cli.py`
8. `scanner/constants.py` — `SKIP_DIRS`, `_should_skip`
9. `scanner/__init__.py`
10. `scanner/python_engine.py` — `scan_file` / `scan_directory` shape
11. `scanner/multilang_engine.py` — `load_rules`, `scan_directory`
12. `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml` — rule style
13. `scanner/README.md`

**API / DB lane**
14. `api/services/risk_engine.py` — `RISK_RULES`, `_normalize_algorithm`, `score_finding(s)`
15. `api/services/scan_runner.py` — the `confidence == "high"` gate (read-only)
16. `api/services/cbom_generator.py` — `_finding_to_component` (read-only)
17. `api/services/report_bundle.py`, `api/routers/report_sync.py` — the persistence path that bypasses `scan_runner`
18. `api/models.py`, `api/routers/findings.py`, `api/routers/scans.py`
19. `db/schema.sql`, `db/models.py`, `db/crud.py`, `db/migrations/001_secure_reporting.sql`, `db/README.md`
20. `remediation_table.py` — `get_criticality`

**Infra, tests, docs**
21. `docker-compose.yml`, `Dockerfile`, `.dockerignore`, `requirements.txt`, `.github/workflows/ecdat-scan.yml`
22. `conftest.py`, `tests/test_scan_runner.py`, `tests/test_cli_secure.py`, `tests/test_crud.py`
23. `docs/RISK_ENGINE_SPEC.md`, `docs/SOURCE_SCANNING_SCOPE.md`, `docs/ECDAT_CLI_GUIDE.md`

**Prerequisite artefacts that do NOT exist in the snapshot** (Wave 0–2 outputs). Verified absent: `scanner/confidence.py`, `scanner/ecdat_cli.py`, any `--scan-type` in `scanner/cli.py`, `SCAN_MAX_ARTIFACT_BYTES` in `scanner/constants.py`. Per `AGENT_RULES.md` #9, if any is still absent when you start: **stop and say so**; do not stub it.
- `scanner/confidence.py` (CONF, SOLE)
- `--scan-type` in `scanner/cli.py` (CLI feature / C-11)
- `SCAN_MAX_ARTIFACT_BYTES` in `scanner/constants.py` (C-12 says "a shared `SCAN_MAX_ARTIFACT_BYTES`"; no owner named — §11 G8)

---

## 5. File Ownership

Tiers are the contract's (§0): **SOLE** = one owner, others open no PR · **COORDINATED** = edits go through the named integration owner, in §6 merge order · **FROZEN** = interface fixed by the contract.

### 5.1 Files this feature creates or modifies

| Path | Contract tier | Integration owner | DEP action |
|---|---|---|---|
| `scanner/dependency_engine.py` | **SOLE** (§1.1, "new") | DEP | create |
| `scanner/dependency_rules/pypi.yaml`, `npm.yaml`, `maven.yaml` | **SOLE** (§1.1: `scanner/dependency_rules/`) | DEP | create (file names are DEP's; contract fixes only the directory) |
| `db/migrations/003_artifact_scanning.sql` | **SOLE per file** (§1.3) — *one file shared by DEP + CNT + BIN + IAC, one PR* (§2.1) | DB lane | contribute DEP's share; do not alter CNT/BIN/IAC lines |
| `db/schema.sql` | **COORDINATED** | DB lane (Ronak) | append identical statements |
| `db/models.py` | **COORDINATED** | DB lane (Ronak) | value tuples, columns, indexes |
| `db/crud.py` | **COORDINATED** | DB lane (Ronak) | five key aliases + two validations; **no new functions** |
| `docker-compose.yml` | **COORDINATED** | deploy lane | one initdb mount line (`04_`) |
| `api/models.py` | **COORDINATED** | backend lane (Shreyanshi) | five fields on `FindingOut` |
| `scanner/cli.py` | **COORDINATED** | scanner lane (Shashank) | helper + `artifact_ref` rewrite + one hook line in the Wave-2 `--scan-type` dispatch |
| `scanner/__init__.py` | **COORDINATED** | scanner lane | export `scan_dependency` |
| `tests/test_scan_runner.py` | Shared-index entry "DEP CONF" (§5.1); tier not stated in §1 → treated as **COORDINATED** | owning lane | add one test |
| `tests/test_dependency_engine.py` | not listed in the contract; new file, no other feature claims it → **SOLE by creation** | DEP | create |
| `docs/DEPENDENCY_SCANNING_SCOPE.md` | falls under `docs/*_SCANNING_SCOPE.md` — **SOLE per file, "respective feature"** (§1.5). Not enumerated in C-19's list of four scope docs (§11 G10) | DEP | create |

### 5.2 Do-not-touch list

**FROZEN** (contract §1.1, §1.2)
- `scanner/finding.py` — only CONF may add fields, once.
- `api/services/scan_runner.py` — CONF's; "DEP/CNT/BIN/IAC must not touch it".
- `api/services/risk_engine.py` — CBOM/risk lane (Maitreyi).

**Other features' SOLE files**
- Scanner: `scanner/container_engine.py`, `scanner/image_layers.py`, `scanner/binary_engine.py`, `scanner/config_engine.py`, `scanner/confidence.py`, `scanner/enroll_cli.py`, `scanner/ecdat_cli.py`, `pyproject.toml`, `scanner/rules/container.yaml`, `scanner/rules/binary.yaml`, `scanner/rules/config.yaml`
- API: `api/routers/auth.py`, `api/core/rbac.py`, `api/routers/agents.py`, `api/services/enrollment.py`, `api/routers/audit.py`, `api/services/audit.py`, `api/routers/triage.py`, `api/routers/trends.py`, `api/routers/compliance.py`, `api/services/cbom_validator.py`
- DB: `db/migrations/002_confidence_scoring.sql`, `004_rbac_users.sql`, `005_agent_enrollment.sql`, `006_audit_events.sql`, `007_finding_triage.sql`, `008_query_indexes.sql`
- Frontend: `dashboard/src/index.css`, `dashboard/tailwind.config.js`, `dashboard/public/fonts/`, `dashboard/src/components/ConfidenceStamp.jsx`, `AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `pages/AgentStatusPage/`, `hooks/useAgents.js`, `ComplianceReport.jsx`, `RiskTrendChart.jsx`, `RiskTierBreakdown.jsx`, `pages/TrendsPage/`, `dashboard/src/context/AuthContext.jsx`, `pages/LoginPage/LoginForm.jsx`, `pages/LandingPage/index.jsx`
- Ops/docs: `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml`, every other `docs/*_SCANNING_SCOPE.md`, `docs/CONFIDENCE_MODEL_SPEC.md`, `docs/COMPLIANCE_REPORT_SCOPE.md`

**COORDINATED files the contract does *not* assign to DEP — do not edit** (flag a human if you believe you must)
- `scanner/constants.py` (DEP reuses `SKIP_DIRS` / `_should_skip` unchanged; C-12 lists only CNT/BIN/IAC/CONF)
- `scanner/python_engine.py`, `scanner/multilang_engine.py`, `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml`
- `api/services/cbom_generator.py`, `api/routers/*.py`, `api/core/*`, `api/main.py`
- `requirements.txt`, `Dockerfile`, `.env.example`, `deploy/nginx/nginx.conf`, `.github/workflows/ecdat-scan.yml`
- `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md`, `docs/ECDAT_CLI_GUIDE.md`, `docs/SOURCE_SCANNING_SCOPE.md`, `docs/SECURE_DEPLOYMENT.md`
- `tests/test_crud.py`, `tests/test_realworld_source_scanner.py`, `tests/test_scanner_battle.py`, `tests/test_security_controls.py`, `db/seed.py`
- All of `dashboard/**`

---

## 6. Tech Stack & Pinned Versions

Checked against `requirements.txt`, `Dockerfile`, and `dashboard/package.json` in the snapshot. **This feature changes no pinned or ranged version and adds no dependency.**

| Component | Version / constraint | Source of truth | DEP action |
|---|---|---|---|
| Python | **3.11** (`FROM python:3.11-slim`; `requirements.txt` header: "REQUIRES: Python 3.11 ONLY") | `Dockerfile`, `requirements.txt` | none |
| `json`, `pathlib`, `dataclasses`, `typing`, `sys`, `logging` | Python 3.11 stdlib | — | use |
| `tomllib` | Python 3.11 stdlib (first available in 3.11) | — | use for `pyproject.toml`, `poetry.lock` |
| `xml.etree.ElementTree` | Python 3.11 stdlib | — | use for `pom.xml` only, after rejecting any document containing a DOCTYPE |
| `PyYAML` | `PyYAML>=6.0` | `requirements.txt` | use `yaml.safe_load` only (same as `scanner/multilang_engine.py`) |
| `pytest` | `pytest>=8.0` | `requirements.txt` | tests |
| `SQLAlchemy` | `>=2.0,<2.1` | `requirements.txt` | ORM columns |
| `pydantic` | `>=2.7.0` | `requirements.txt` | `FindingOut` fields |
| `tree-sitter` / `tree-sitter-languages` | `==0.21.3` / `==1.10.2` | `requirements.txt` | **not used, not changed** |
| `cryptography` | **unpinned** in `requirements.txt` (live defect, C-18) | Wave 0, backend lane | DEP neither pins nor imports it |
| `dashboard/package.json` | unchanged | — | none |
| **New dependencies** | **none.** Not added: `defusedxml`, `packaging`, `lief`, `python-hcl2`, any JSON-schema library | — | any addition needs the C-18 grouped `requirements.txt` diff |

**Verified environment for the baseline in §12:** scratch venv, Python **3.12.3**, pytest 9.1.1, PyYAML 6.0.3, SQLAlchemy 2.0.54, pydantic 2.13.5, tree-sitter 0.21.3 / tree-sitter-languages 1.10.2. The project pin is 3.11 — re-run the baseline under 3.11 before starting.

---

## 7. Concrete Interface Definitions

### 7.1 `db/migrations/003_artifact_scanning.sql` — quoted verbatim from contract §2.2 (same statements appended to `db/schema.sql`)

```sql
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
```

### 7.2 `docker-compose.yml` — `db.volumes` (contract §2.1: prefix `04_`)

```yaml
      - ./db/migrations/003_artifact_scanning.sql:/docker-entrypoint-initdb.d/04_artifact_scanning.sql:ro
```

### 7.3 `db/models.py`

```python
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func, text

ARTIFACT_TYPES = ("SOURCE_FILE", "DEPENDENCY_MANIFEST", "CONFIG_FILE", "BINARY", "CONTAINER_LAYER")
PACKAGE_ECOSYSTEMS = ("pypi", "npm", "maven", "deb", "apk", "rpm")


class Finding(Base):
    artifact_type: Mapped[str] = mapped_column(
        Text, default="SOURCE_FILE", server_default="SOURCE_FILE", nullable=False
    )
    artifact_ref: Mapped[str | None] = mapped_column(Text)
    package_ecosystem: Mapped[str | None] = mapped_column(Text)
    package_name: Mapped[str | None] = mapped_column(Text)
    package_version: Mapped[str | None] = mapped_column(Text)
    image_digest: Mapped[str | None] = mapped_column(Text)
    layer_digest: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_findings_scan_id", "scan_id"),
        Index("idx_findings_severity", "risk_tier"),
        Index("idx_findings_artifact_type", "artifact_type"),
        Index(
            "idx_findings_package",
            "package_ecosystem",
            "package_name",
            postgresql_where=text("package_name IS NOT NULL"),
        ),
    )
```

### 7.4 `db/crud.py`

```python
from db.models import (
    ARTIFACT_TYPES,
    CRITICALITIES,
    PACKAGE_ECOSYSTEMS,
    RISK_TIERS,
    SCAN_STATUSES,
    Finding,
    Repository,
    Scan,
    RiskAssessment,
    Report,
)

_FINDING_KEY_ALIASES: dict[str, str] = {
    "artifact_type": "artifact_type",
    "artifact_ref": "artifact_ref",
    "package_ecosystem": "package_ecosystem",
    "package_name": "package_name",
    "package_version": "package_version",
}


def normalize_finding(finding: dict[str, Any]) -> dict[str, Any]:
    artifact_type = str(cols.get("artifact_type") or "SOURCE_FILE").strip().upper()
    cols["artifact_type"] = artifact_type if artifact_type in ARTIFACT_TYPES else "SOURCE_FILE"
    ecosystem = str(cols.get("package_ecosystem") or "").strip().lower()
    cols["package_ecosystem"] = ecosystem if ecosystem in PACKAGE_ECOSYSTEMS else None
```

### 7.5 `api/models.py`

```python
class FindingOut(BaseModel):
    source_context: str = "SOURCE"
    artifact_type: str = "SOURCE_FILE"
    artifact_ref: str | None = None
    package_ecosystem: str | None = None
    package_name: str | None = None
    package_version: str | None = None
    risk_assessment: "RiskAssessmentOut | None" = None
```

### 7.6 `scanner/dependency_engine.py`

```python
from __future__ import annotations

import json
import sys
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from scanner.constants import SCAN_MAX_ARTIFACT_BYTES, _should_skip
from scanner.finding import Finding

DEPENDENCY_RULES_DIR: Path = Path(__file__).resolve().parent / "dependency_rules"
DETECTION_METHOD: str = "dependency_manifest"
ARTIFACT_TYPE: str = "DEPENDENCY_MANIFEST"
UNKNOWN_ALGORITHM: str = "UNKNOWN"
LIBRARY_PRIMITIVE: str = "library"
LEGACY_CONFIDENCE: str = "unverified"
MAX_MATCHED_CALL_CHARS: int = 200
REQUIREMENTS_PREFIX: str = "requirements"
REQUIREMENTS_SUFFIX: str = ".txt"
MANIFEST_FILENAMES: frozenset[str] = frozenset(
    {"pyproject.toml", "Pipfile.lock", "poetry.lock", "package.json", "package-lock.json", "pom.xml"}
)
ECOSYSTEM_LANGUAGE: dict[str, str] = {"pypi": "python", "npm": "javascript", "maven": "java"}

DependencyRules = dict[str, dict[str, dict]]


@dataclass(frozen=True)
class DependencyRecord:
    path: Path
    line: int
    ecosystem: str
    name: str
    version: Optional[str]
    scope: str
    declared: str


@dataclass
class DependencyFinding(Finding):
    artifact_type: str = "DEPENDENCY_MANIFEST"
    artifact_ref: Optional[str] = None
    package_ecosystem: Optional[str] = None
    package_name: Optional[str] = None
    package_version: Optional[str] = None


def is_manifest(path: Path) -> bool: ...
def normalize_package_name(ecosystem: str, name: str) -> str: ...
def load_rules(rules_dir: Path | None = None) -> DependencyRules: ...
def parse_manifest(path: Path) -> list[DependencyRecord]: ...
def record_to_finding(record: DependencyRecord, rule: dict) -> DependencyFinding: ...
def scan_file(path: Path, rules: dict | None = None) -> list[Finding]: ...
def scan_directory(root: Path, rules: dict | None = None) -> list[Finding]: ...

def _warn(message: str) -> None: ...
def _within_root(path: Path, root: Path) -> bool: ...
def _read_manifest_text(path: Path) -> Optional[str]: ...
def _is_exact_version(spec: str) -> bool: ...
def _split_requirement(line: str) -> tuple[str, str | None, str] | None: ...
def _dedupe_key(finding: DependencyFinding) -> tuple[str, str | None, str | None, str | None, str | None, str]: ...
def _parse_requirements_txt(path: Path, text: str) -> list[DependencyRecord]: ...
def _parse_pyproject_toml(path: Path, text: str) -> list[DependencyRecord]: ...
def _parse_pipfile_lock(path: Path, text: str) -> list[DependencyRecord]: ...
def _parse_poetry_lock(path: Path, text: str) -> list[DependencyRecord]: ...
def _parse_package_json(path: Path, text: str) -> list[DependencyRecord]: ...
def _parse_package_lock_json(path: Path, text: str) -> list[DependencyRecord]: ...
def _parse_pom_xml(path: Path, text: str) -> list[DependencyRecord]: ...
```

### 7.7 `scanner/dependency_rules/*.yaml`

`pypi.yaml`
```yaml
ecosystem: "pypi"
packages:
  - name: "pycrypto"
    library: "pycrypto"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: true
  - name: "pycryptodome"
    library: "pycryptodome"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
  - name: "pycryptodomex"
    library: "pycryptodomex"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
  - name: "cryptography"
    library: "cryptography"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
  - name: "pyopenssl"
    library: "pyopenssl"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
```

`npm.yaml`
```yaml
ecosystem: "npm"
packages:
  - name: "md5"
    library: "md5"
    algorithm: "MD5"
    primitive: "hash"
    weak_by_default: true
  - name: "sha1"
    library: "sha1"
    algorithm: "SHA-1"
    primitive: "hash"
    weak_by_default: true
  - name: "crypto-js"
    library: "crypto-js"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
  - name: "node-forge"
    library: "node-forge"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
```

`maven.yaml`
```yaml
ecosystem: "maven"
packages:
  - name: "org.bouncycastle:bcprov-jdk15on"
    library: "org.bouncycastle:bcprov-jdk15on"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
  - name: "org.bouncycastle:bcprov-jdk18on"
    library: "org.bouncycastle:bcprov-jdk18on"
    algorithm: "UNKNOWN"
    primitive: "library"
    weak_by_default: false
```

### 7.8 `scanner/__init__.py`

```python
try:
    from scanner.dependency_engine import scan_file as scan_dependency
except Exception:  # pragma: no cover
    def scan_dependency(*args, **kwargs):
        raise RuntimeError("dependency scanner unavailable")

__all__ = ["scan_cli", "Finding", "scan_python", "scan_multilang", "scan_dependency"]
```

### 7.9 `scanner/cli.py`

```python
def _scan_dependency(target: Path) -> list:
    from scanner import dependency_engine

    if target.is_dir():
        return dependency_engine.scan_directory(target)
    return dependency_engine.scan_file(target)
```

Inside the Wave-2 `--scan-type` dispatch, in the branch for the value `dependency`:
```python
findings.extend(_scan_dependency(target))
```

Inside `_prepare_findings`, immediately after `finding["file"] = _relative_or_redacted(...)`:
```python
        if finding.get("artifact_type") == "DEPENDENCY_MANIFEST":
            finding["artifact_ref"] = finding["file"]
```

### 7.10 CLI stdout element — `python -m scanner.cli <dir> --scan-type dependency` (JSON array; one element shown; CONF fields not shown)

```json
{
  "file": "requirements.txt",
  "line": 1,
  "matched_call": "requirements: pycrypto==2.6.1",
  "library": "pycrypto",
  "algorithm": "UNKNOWN",
  "primitive": "library",
  "language": "python",
  "weak_by_default": true,
  "confidence": "unverified",
  "key_size": null,
  "detection_method": "dependency_manifest",
  "artifact_type": "DEPENDENCY_MANIFEST",
  "artifact_ref": "requirements.txt",
  "package_ecosystem": "pypi",
  "package_name": "pycrypto",
  "package_version": "2.6.1",
  "source_context": "SOURCE",
  "risk_tier": "UNSCORED",
  "risk_reason": null,
  "criticality": "MEDIUM",
  "quantum_vulnerable": false,
  "classical_broken": false,
  "recommended_replacement": null,
  "recommendation_type": null,
  "migration_effort_days": null,
  "data_shelf_life_years": null,
  "quantum_threat_horizon_years": 12,
  "hndl_exposure": "NOT_APPLICABLE",
  "assumption_source": null,
  "risk_model_version": "2026.1"
}
```

### 7.11 `GET /scans/7/findings` — existing route, unchanged; CONF fields not shown

```json
{
  "scan_id": 7,
  "findings": [
    {
      "id": 12,
      "scan_id": 7,
      "file": "package.json",
      "line": 0,
      "algorithm": "MD5",
      "key_size": null,
      "confidence": "unverified",
      "risk_tier": "CRITICAL",
      "risk_reason": "MD5 is classically broken — collision attacks are well-documented and computationally trivial. Immediate replacement with SHA-256 required.",
      "criticality": "MEDIUM",
      "matched_call": "dependencies: md5@^2.3.0",
      "library": "md5",
      "primitive": "hash",
      "language": "javascript",
      "weak_by_default": true,
      "detection_method": "dependency_manifest",
      "source_context": "SOURCE",
      "artifact_type": "DEPENDENCY_MANIFEST",
      "artifact_ref": "package.json",
      "package_ecosystem": "npm",
      "package_name": "md5",
      "package_version": null,
      "risk_assessment": {
        "risk_model_version": "2026.1",
        "classical_broken": true,
        "quantum_vulnerable": false,
        "hndl_exposure": "NOT_APPLICABLE",
        "recommended_replacement": "SHA-256 or BLAKE2",
        "recommendation_type": "classical",
        "migration_effort_days": 1,
        "data_shelf_life_years": 0.0,
        "quantum_threat_horizon_years": 12.0,
        "assumption_source": null,
        "assessed_at": "2026-09-20T09:30:12.418211"
      }
    },
    {
      "id": 13,
      "scan_id": 7,
      "file": "requirements.txt",
      "line": 1,
      "algorithm": "UNKNOWN",
      "key_size": null,
      "confidence": "unverified",
      "risk_tier": null,
      "risk_reason": null,
      "criticality": "MEDIUM",
      "matched_call": "requirements: pycrypto==2.6.1",
      "library": "pycrypto",
      "primitive": "library",
      "language": "python",
      "weak_by_default": true,
      "detection_method": "dependency_manifest",
      "source_context": "SOURCE",
      "artifact_type": "DEPENDENCY_MANIFEST",
      "artifact_ref": "requirements.txt",
      "package_ecosystem": "pypi",
      "package_name": "pycrypto",
      "package_version": "2.6.1",
      "risk_assessment": {
        "risk_model_version": "2026.1",
        "classical_broken": false,
        "quantum_vulnerable": false,
        "hndl_exposure": "NOT_APPLICABLE",
        "recommended_replacement": null,
        "recommendation_type": null,
        "migration_effort_days": null,
        "data_shelf_life_years": null,
        "quantum_threat_horizon_years": 12.0,
        "assumption_source": null,
        "assessed_at": "2026-09-20T09:30:12.418211"
      }
    }
  ],
  "total_on_page": 2,
  "offset": 0,
  "limit": 50,
  "risk_tier_filter": null,
  "summary": {"total": 2, "CRITICAL": 1, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNSCORED": 1}
}
```

---

## 8. Step-by-Step Implementation Plan

### Preconditions — verification only, no file changes

Run these first. If any fails, **stop and report it** (`AGENT_RULES.md` #4, #9). Do not stub, do not work around.

| # | Check | Command | Must show |
|---|---|---|---|
| P1 | CONF phase 1 landed | `test -f scanner/confidence.py && echo present` | `present` |
| P2 | Wave-2 `--scan-type` landed | `grep -n "scan-type" scanner/cli.py` | ≥ 1 match |
| P3 | Shared artefact-size constant exists | `grep -n "SCAN_MAX_ARTIFACT_BYTES" scanner/constants.py` | ≥ 1 match (§11 G8) |
| P4 | Migration number free or shared | `ls db/migrations/` | `003_artifact_scanning.sql` absent **or** already contains §7.1 (see step 1) |
| P5 | **G1 ratified in writing** by the scanner lane (Shashank) and the CONF owner | (human confirmation) | recorded in the PR description. **Steps 10 and 13 may not merge without it.** |
| P6 | Baseline recorded | `pytest --collect-only -q -p no:cacheprovider \| tail -1` | write the number down — §12 uses it |

You work only on your assigned feature branch (`AGENT_RULES.md` #8). The branch name is not specified by the contract; do not invent a convention.

### Steps

**1. File: `db/migrations/003_artifact_scanning.sql`**
If absent, create it containing §7.1 **verbatim**. If it already exists (CNT/BIN/IAC landed first), diff it against §7.1: add only missing statements, never reorder or edit another owner's lines. Applying it twice must produce no `ERROR`.

**2. File: `db/schema.sql`**
Append the same statements as §7.1 after the existing `findings` index block, keeping `IF NOT EXISTS` on every statement. `schema.sql` and the migration must be identical in effect (contract §2, C-01).

**3. File: `docker-compose.yml`**
Add the §7.2 line to `db.volumes`, after the `03_` mount if CONF's has landed, otherwise after the `02_` mount.

**4. File: `db/models.py`**
Apply §7.3. Whichever of DEP/CNT/BIN/IAC lands first adds **all seven** columns and both indexes so the ORM mirrors the DDL exactly (`db/schema.sql` header: "The SQLAlchemy models in db/models.py mirror it exactly"); later features verify rather than duplicate. DEP writes no value to `image_digest` / `layer_digest`.

**5. File: `db/crud.py`**
Apply §7.4. Add **no functions**. The alias entries are required: today `normalize_finding` silently drops any key not in `_FINDING_KEY_ALIASES`, so without them all five values are discarded at write time (verified against the snapshot).

**6. File: `api/models.py`**
Apply §7.5. Add no new Pydantic model.

**7. File: `scanner/dependency_rules/pypi.yaml`**
Create with the §7.7 seed. Entries are data only; each new entry needs a fixture assertion in `tests/test_dependency_engine.py`.

**8. File: `scanner/dependency_rules/npm.yaml`**
Create with the §7.7 seed.

**9. File: `scanner/dependency_rules/maven.yaml`** *(conditional — skip if §11 G6 is answered "Java not required")*
Create with the §7.7 seed.

**10. File: `scanner/dependency_engine.py` — foundation**
Implement the §7.6 constants and types plus `normalize_package_name`, `load_rules`, `is_manifest`, `_warn`, `_within_root`, `_read_manifest_text`.
- `normalize_package_name`: `pypi` → lower-case, and every run of `-`, `_`, `.` collapses to a single `-`; `npm` → lower-case (scoped `@scope/name` keeps its prefix); `maven` → lower-case `groupId:artifactId`. Use `str` methods only.
- `load_rules`: `sorted(rules_dir.glob("*.yaml"))`, non-recursive, `yaml.safe_load`. A file that fails to parse as YAML, or has no `ecosystem` ∈ `ECOSYSTEM_LANGUAGE`, or has no `packages` list, is skipped with a `[warn]`; a package entry missing `name`, `library`, `algorithm`, `primitive` or a boolean `weak_by_default` is skipped with a `[warn]`. Result is indexed `ecosystem → normalised name → rule dict`. `rules_dir=None` means `DEPENDENCY_RULES_DIR`.
- `is_manifest`: `path.name in MANIFEST_FILENAMES`, or the name starts with `REQUIREMENTS_PREFIX` and ends with `REQUIREMENTS_SUFFIX`.
- `_read_manifest_text`: `None` (after a `[warn]`) if `st_size > SCAN_MAX_ARTIFACT_BYTES`, on `OSError`, or on `UnicodeDecodeError`; otherwise UTF-8 (BOM tolerated).
- `_warn` writes to **stderr only**. Stdout is the JSON array (contract §3.5).
- **Do not `import re`** (`AGENT_RULES.md` #5, applied conservatively to every parser in this file).

**11. File: `scanner/dependency_engine.py` — parsers for text, JSON and TOML**
Implement `_is_exact_version`, `_split_requirement`, `_parse_requirements_txt`, `_parse_pyproject_toml`, `_parse_pipfile_lock`, `_parse_poetry_lock`, `_parse_package_json`, `_parse_package_lock_json`, and the dispatch in `parse_manifest`.
- `line` is the real 1-based line for `requirements*.txt` (first physical line of a continued entry) and **`0`** for JSON/TOML/XML formats (C-13 renders `0` as `—`; §11 G7).
- **requirements\*.txt**: join backslash-continued lines; strip inline comments (`#` at line start or after whitespace); skip blank lines, option lines (start with `-`), path lines (start with `.` or `/`) and any line containing `://` that is not the `name @ url` form; `name @ url` keeps only the name (`version=None`, `declared=name`); cut environment markers at the first `;`; drop extras and `--hash` tokens; `declared` = name + specifier text with whitespace removed; `scope` = the file name without its `.txt` suffix (`requirements`, `requirements-dev`). `version` is set only for a single `==X` / `===X` clause with no `*`.
- **`_is_exact_version`**: true only for a non-empty string starting with a digit made of letters, digits and `.`, `-`, `+`, `_`, with no dot-separated component equal to `x`, `X` or `*`. (`2.3.0`, `1.0.0-beta.1` → true; `^2.3.0`, `>=1`, `1.x`, `*`, `latest` → false.)
- **package.json**: sections `dependencies`, `devDependencies`, `optionalDependencies`, `peerDependencies`, each ignored unless it is an object; `scope` = section name; `declared` = `name@spec` only when `spec` is a string containing neither `:` nor `/`, otherwise just `name`; `version` = `spec` when `_is_exact_version(spec)`.
- **package-lock.json**: use `packages` when it is an object, else the v1 `dependencies` tree (recursive); skip the `""` root and any entry with `"link": true`; the package name is the text after the last `node_modules/` in the key; `version` = the entry's `version`; `scope` = `package-lock.json`.
- **pyproject.toml** (`tomllib`): `project.dependencies` (PEP 508 strings via `_split_requirement`), `project.optional-dependencies.<extra>`, `tool.poetry.dependencies`, `tool.poetry.dev-dependencies`, `tool.poetry.group.<g>.dependencies`; skip the `python` key; a poetry value that is a table uses its `version`; `scope` is the dotted table path.
- **Pipfile.lock**: `default` and `develop` objects; `version` `"==X"` → `X`.
- **poetry.lock** (`tomllib`): every `[[package]]` with `name` and `version`.
- **`declared` and `scope` per format** (so every implementer produces the same `matched_call`):
  - `package-lock.json`: `declared = f"{name}@{version}"`, `scope = "package-lock.json"`.
  - `Pipfile.lock`: `declared = f"{name}=={version}"`, `scope` = `"default"` or `"develop"`.
  - `poetry.lock`: `declared = f"{name}=={version}"`, `scope = "poetry.lock"`.
  - `pyproject.toml`, PEP 621 entries: `declared` built like a `requirements*.txt` entry (name + specifier text, whitespace removed); `scope` = `project.dependencies` or `project.optional-dependencies.<extra>`.
  - `pyproject.toml`, poetry entries: let `spec` be the string value, or the table's `version` string (empty if absent), whitespace removed; `declared = f"{name}=={spec}"` when `spec` starts with a digit, else `f"{name}{spec}"`; `scope` = the dotted table path (`tool.poetry.dependencies`, `tool.poetry.group.test.dependencies`).
- Any parser that hits invalid JSON/TOML or an unexpected shape returns `[]` after one `[warn]`; it never raises.

**12. File: `scanner/dependency_engine.py` — `pom.xml`** *(conditional — skip if §11 G6 is answered "Java not required"; then also remove `"pom.xml"` from `MANIFEST_FILENAMES`)*
Implement `_parse_pom_xml`: if the text upper-cased contains `<!DOCTYPE` or `<!ENTITY`, `[warn]` and return `[]` **before** any XML parse; otherwise `xml.etree.ElementTree.fromstring`, strip the XML namespace from tags, and read every `dependency` under `dependencies` and `dependencyManagement/dependencies`. Name = lower-cased `groupId:artifactId`. `version` is set only when the text is non-empty, contains no `${`, and contains none of `[`, `(`, `,`. `declared` = name plus `:<version text>` when a version text exists. Do not resolve properties or parent POMs. `line = 0`.

**13. File: `scanner/dependency_engine.py` — findings and walkers**
Implement `record_to_finding`, `_dedupe_key`, `scan_file`, `scan_directory`.
- `record_to_finding` field mapping: `file = str(record.path)`; `line = record.line`; `matched_call = f"{scope}: {declared}"` truncated to `MAX_MATCHED_CALL_CHARS`; `library = rule["library"]`; `algorithm = rule["algorithm"]`; `primitive = rule["primitive"]`; `language = ECOSYSTEM_LANGUAGE[ecosystem]`; `weak_by_default = rule["weak_by_default"]`; `confidence = LEGACY_CONFIDENCE`; `key_size = None`; **`detection_method = DETECTION_METHOD` set explicitly** (never rely on `Finding`'s default `"static_analysis"`, forbidden by contract §3.2); `artifact_type = ARTIFACT_TYPE`; `artifact_ref = str(record.path)`; `package_ecosystem = record.ecosystem`; `package_name = normalize_package_name(...)`; `package_version = record.version`.
- `matched_call` and `declared` are built from the name and version specifier **only** — never from a raw manifest line or URL.
- `scan_file(path, rules=None)`: load rules once if `None`; a non-manifest path → `[warn]` on stderr and `[]`; parse; keep only records whose `(ecosystem, normalised name)` is in the rule pack; drop duplicates by `_dedupe_key` (contract C-23 key `(artifact_type, artifact_ref, package_ecosystem, package_name, package_version, algorithm)`), first occurrence wins; sort by `(file, line, package_name)`.
- `scan_directory(root, rules=None)`: a file `root` delegates to `scan_file`; otherwise walk `root.rglob("*")`, keep regular files with `is_manifest(p)`, skip anything for which `_should_skip(p, root)` is true (reuses `SKIP_DIRS`, unchanged), skip and `[warn]` any manifest for which `_within_root(p, root)` is false (symlink escaping the root). Sort the combined result by `(file, line, package_name)`. Pure and path-based: no CLI, DB, network or subprocess use.

**14. File: `scanner/__init__.py`**
Apply §7.8. The guarded import keeps `import scanner` working even if this optional engine is broken, mirroring the existing `scan_multilang` pattern (the stub raises when called; it does not fake success).

**15. File: `scanner/cli.py`**
Apply §7.9. Add **no argparse flag**, do not touch `_violates_policy`, `_summary`, or any existing branch. `scanner/cli.py` imports the engine lazily inside `_scan_dependency`, so the default `source` path never invokes it (`scanner/__init__.py` still imports the module at package import, as it does for `scan_multilang`; the module has no import-time side effects). Wire `_scan_dependency` into the `dependency` branch of the `--scan-type` dispatch that Wave 2 created; do not restructure that dispatch. The `artifact_ref` rewrite is required: `_prepare_findings` relativises or redacts only `finding["file"]`, so without it `--redact-paths` would leave an absolute workstation path in `artifact_ref`.

**16. File: `tests/test_dependency_engine.py`**
Create exactly the 21 tests specified in §12.2, with the fixtures described there. The two `pom.xml` tests are the conditional ones.

**17. File: `tests/test_scan_runner.py`**
Add exactly one test, `test_run_scan_default_ignores_dependency_manifests` (§12.2). Do not edit the three existing tests.

**18. File: `docs/DEPENDENCY_SCANNING_SCOPE.md`**
Create. It must state: the supported manifest files and ecosystems; that a finding means "a recognised cryptographic library is *declared* in this manifest" and not "the code calls it"; that `algorithm = UNKNOWN` means "library present, algorithm not determinable from a manifest" and yields `risk_tier = UNSCORED`; that there is no CVE/registry lookup and no transitive/direct distinction; that `line = 0` means "no line information for structured formats"; that findings carry the legacy `confidence = unverified` and are therefore **CLI-only / signed-bundle-only until CONF replaces the `scan_runner` gate** (C-02, in the contract's own words: "CLI-only features"); that it is not an SBOM (`docs/SOURCE_SCANNING_SCOPE.md` disclaims "third-party dependency inventories/SBOMs"; DEP lists only recognised cryptographic libraries); that default scans (`--scan-type source`) are unchanged. Do not edit `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md`, `docs/SOURCE_SCANNING_SCOPE.md` or `docs/ECDAT_CLI_GUIDE.md` (C-19).

---

## 9. Naming & Symbol Registry

Checks applied to every row: contract §3.1 (snake_case / PascalCase / UPPER_SNAKE, no PascalCase functions, `scanner/<domain>_engine.py`), §3.2 (`detection_method` registry), §3.3 (env vars), §3.5 (CLI), §3.8 (database), §5 (shared-resource index). Collision column = result of a repository-wide search of the snapshot (`*.py`, `*.sql`, `*.md`, `*.yaml`, `*.js`, `*.jsx`) plus the contract's reserved names.

### 9.1 Files and directories

| Name | Kind | Convention / source | Collision check |
|---|---|---|---|
| `scanner/dependency_engine.py` | module | §3.1 `scanner/<domain>_engine.py`; §1.1 SOLE DEP | none |
| `scanner/dependency_rules/` | directory | §1.1 (SOLE DEP). Deliberately **not** `scanner/rules/` — see §11 G11 | none |
| `scanner/dependency_rules/pypi.yaml`, `npm.yaml`, `maven.yaml` | rule packs | file names chosen by DEP; contract fixes only the directory | none |
| `tests/test_dependency_engine.py` | test module | existing `tests/test_*.py` pattern | none |
| `docs/DEPENDENCY_SCANNING_SCOPE.md` | doc | §1.5 `docs/*_SCANNING_SCOPE.md` | none; not among C-19's four named scope docs (§11 G10) |
| `db/migrations/003_artifact_scanning.sql` | migration | **not DEP's name** — reserved by §2.1, shared with CNT/BIN/IAC | must not be duplicated or renamed |
| `04_artifact_scanning.sql` | initdb mount target | §2.1 prefix `04_` | `03_` belongs to CONF; do not reuse |

### 9.2 Python symbols — `scanner/dependency_engine.py`

| Symbol | Kind | Convention | Collision check |
|---|---|---|---|
| `scan_file`, `scan_directory` | public functions | **exact pair mandated by §3.1**; signatures identical to the contract's | same names exist in `python_engine` / `multilang_engine` by design (§3.1); disambiguated by module path. `scanner/__init__.py` re-exports only as `scan_dependency` |
| `load_rules` | public function | snake_case | **same name** as `scanner.multilang_engine.load_rules` with a different signature and return type. Disambiguated by module path (§3.1). Never import one into the other's module |
| `is_manifest`, `parse_manifest`, `normalize_package_name`, `record_to_finding` | public functions | snake_case | none. Used only inside this module and its tests; nothing else may be imported across lanes (§3.1) |
| `DependencyRecord` | frozen dataclass | PascalCase | none |
| `DependencyFinding` | dataclass, subclass of `Finding` | PascalCase | none. Existence depends on §11 **G1** |
| `DependencyRules` | type alias | PascalCase alias | none |
| `DEPENDENCY_RULES_DIR`, `DETECTION_METHOD`, `ARTIFACT_TYPE`, `UNKNOWN_ALGORITHM`, `LIBRARY_PRIMITIVE`, `LEGACY_CONFIDENCE`, `MAX_MATCHED_CALL_CHARS`, `REQUIREMENTS_PREFIX`, `REQUIREMENTS_SUFFIX`, `MANIFEST_FILENAMES`, `ECOSYSTEM_LANGUAGE` | module constants | UPPER_SNAKE_CASE | none in the snapshot |
| `_warn`, `_within_root`, `_read_manifest_text`, `_is_exact_version`, `_split_requirement`, `_dedupe_key`, `_parse_requirements_txt`, `_parse_pyproject_toml`, `_parse_pipfile_lock`, `_parse_poetry_lock`, `_parse_package_json`, `_parse_package_lock_json`, `_parse_pom_xml` | private functions | snake_case, leading underscore | none. `_should_skip` is **imported** from `scanner.constants`, not redefined |
| `scan_dependency` | re-export alias in `scanner/__init__.py` | mirrors `scan_python`, `scan_multilang` | none |
| `_scan_dependency` | private helper in `scanner/cli.py` | snake_case | none |
| `SCAN_MAX_ARTIFACT_BYTES` | constant **imported**, not introduced | contract C-12 / §3.3 | owned by the scanner lane in `scanner/constants.py` (§11 G8). DEP must not define it |

### 9.3 Database

| Name | Kind | Convention | Collision check |
|---|---|---|---|
| `findings.artifact_type`, `artifact_ref`, `package_ecosystem`, `package_name`, `package_version`, `image_digest`, `layer_digest` | columns | **quoted from §2.2**; `TEXT`, no native ENUM (§3.8) | shared with CNT/BIN/IAC — first mover adds all seven (§8 step 4); nobody renames. DEP writes five and leaves `image_digest` / `layer_digest` untouched |
| `idx_findings_artifact_type`, `idx_findings_package` | indexes | §3.8 `idx_<table>_<cols>`; **quoted from §2.2** | must not clash with `idx_findings_confidence_band` (CONF, 002) or `idx_findings_scan_id` / `idx_findings_severity` (existing) |
| `ARTIFACT_TYPES`, `PACKAGE_ECOSYSTEMS` | module tuples in `db/models.py` | §3.8 (value set as TEXT + tuple, the existing `CONFIDENCES` pattern) | shared with CNT/BIN/IAC; identical contents wherever they land |
| No new table, no `scans.target_type`, no enum type | — | §2.3 rejects each | — |

### 9.4 Values written into shared vocabularies

| Value | Vocabulary | Status |
|---|---|---|
| `dependency_manifest` | `detection_method` (§3.2, FROZEN) | already registered to `dependency_engine`; DEP adds nothing |
| `DEPENDENCY_MANIFEST` | `findings.artifact_type` (§2.2) | already listed by the contract |
| `pypi`, `npm`, `maven` | `findings.package_ecosystem` (§2.2) | already listed by the contract (lower-case) |
| `unverified` | legacy `Finding.confidence` (`scanner/finding.py`, `ARCHITECTURE.md` §2.1) | existing value; DEP invents no new confidence string (C-03) |
| `UNKNOWN` | `Finding.algorithm` | already handled by `risk_engine.score_findings` and by `cbom_generator._finding_to_component` (`finding.algorithm or "UNKNOWN"`) |
| `library` | `Finding.primitive` | **not listed in any contract registry.** Free-text field today. Recorded as a gap in §11 G2 |

### 9.5 Environment variables, CLI flags, API

| Item | Introduced by DEP? |
|---|---|
| Environment variables | **None.** Do not add `SCAN_ENABLE_DEPENDENCY` or any other toggle: §3.3 lists `SCAN_ENABLE_BINARY` and `SCAN_ENABLE_CONTAINER` only, and engine selection is by the `--scan-type` flag (§3.5) |
| CLI flags | **None.** DEP contributes only the value `dependency` to the existing repeatable `--scan-type` (C-11, §3.5). No `--dependencies`, no `--manifests`, no `--target-type` |
| HTTP routes | **None.** No `/api/v1`, no new router (§3.4) |
| Exit codes | unchanged (`0` / `1` / `2`, FROZEN, §3.5) |
| stdout | unchanged: JSON array of finding dicts only (§3.5). New keys on each element: `artifact_type`, `artifact_ref`, `package_ecosystem`, `package_name`, `package_version` ("fields may be added; none may be renamed") |
| stderr prefix `[warn]` | DEP's own convention for engine diagnostics; the contract sets none |

### 9.6 Tests

`tests/test_dependency_engine.py` — the 21 names listed in §12.2 · `tests/test_scan_runner.py` — `test_run_scan_default_ignores_dependency_manifests`. All `snake_case`, prefix `test_`.

---

## 10. Known Cross-Feature Risks

Sources: contract §4 (Flagged Conflicts & Resolutions) and §5 (Shared Resource Index). Each entry states the resolution **the contract already decided** and what it means for DEP. Nothing here is a new resolution. Where the contract leaves a question open the entry says so and points to §11.

### 10.1 Items that name DEP

**C-01 · migration filename / initdb ordering** (Confidence: High) — *Shared Index: `db/migrations/002_*.sql`, `docker-compose.yml`, `findings` columns*
Decided: `003_artifact_scanning.sql` is one file for DEP + CNT + BIN + IAC, mount prefix `04_`, and the identical change lands in `db/schema.sql` in the same PR. DEP consequence: steps 1–4 of §8; never create a second `003_*` file; never renumber.

**C-02 · `scan_runner.py` drops every non-`"high"` finding** (High on ownership; Medium on persist-vs-drop) — *Shared Index: `api/services/scan_runner.py`, `tests/test_scan_runner.py`*
Decided: the gate is CONF's to replace; DEP "must not edit this file"; until CONF lands, DEP is a "CLI-only" feature and says so in its scope doc. DEP consequence: findings are emitted with `confidence = "unverified"`; a `POST /scans` scan persists zero dependency rows (and, because the CLI default is `source`, does not run the engine at all — §11 G9). Open: persist-vs-drop — §11 A2.

**C-03 · four confidence vocabularies** (Medium) — *Shared Index: `scanner/finding.py`*
Decided: CONF's two-field model; legacy `confidence` becomes a derived mirror; `scanner/finding.py` is FROZEN, "Only CONF may add fields, once." DEP consequence: no confidence field is added or interpreted by DEP; the five artefact fields need a carrier, which the contract does not specify — §11 **G1**. Open items (a)–(c) — §11 A3.

**C-11 · five features modify `scanner/cli.py`; flag namespace collides** (Medium) — *Shared Index: `scanner/cli.py`; `--target-type` / `--image-tar` / `--binaries` / `--scan-type`*
Decided: one repeatable `--scan-type {source,dependency,config,binary,container}`, default `source` only; "The scanner lane owns `cli.py` and merges these one at a time." DEP consequence: no flag of DEP's own; hook into the existing branch after Wave 2; precondition P2. Open: exact spelling and the bare-`ecdat TARGET` alias — §11 A4.

**C-23 · dependency, container and binary scanners report the same library twice** (Medium) — *Shared Index: `findings.package_name` / `package_version`*
Decided: the three columns are shared and owned by the DB lane; de-duplication key `(artifact_type, artifact_ref, package_ecosystem, package_name, package_version, algorithm)`; the three findings are "retained as distinct evidence"; "the dashboard groups them by `package_name` for display". DEP consequence: de-duplicate only within DEP's own output by that key; never merge with CNT/BIN rows. Open: group vs list, and the grouped risk tier — §11 A5.

**C-26 · compatible items** — `Finding` as the sole scanner→backend contract ("All four independently agreed to emit `Finding` unchanged in shape; only CONF adds fields, once"). DEP consequence: this is exactly the tension behind §11 G1 — adding five fields via a subclass is an interpretation that must be ratified, not assumed.

### 10.2 Items that do not name DEP but bind it

**C-12 · `scanner/constants.py` skip-list conflicts** (High) — names CNT, BIN, IAC (and CONF). Decided: `SKIP_DIRS` stays unchanged as the source-walk list; per-engine sets are added beside it; "a shared `SCAN_MAX_ARTIFACT_BYTES`". DEP consequence: reuse `SKIP_DIRS` via `_should_skip`; add no set to `constants.py`; import (do not define) `SCAN_MAX_ARTIFACT_BYTES` — §11 G8. Note that `SKIP_DIRS` contains `node_modules`, `venv`, `env`, `build`, `dist`, `target`: manifests under those directories are never scanned, which is intentional for DEP (installed copies are not declarations).

**C-13 · `FindingsTable.jsx` edited by seven features** (Medium) — names CNT, BIN, IAC, CONF, DFS, TRI, FE. Decided: "`line=0` renders as `—`, never `0`". DEP consequence: DEP emits `line = 0` for structured formats and edits no dashboard file — §11 G7.

**C-14 · `cbom_generator.py` pulled six ways** (High on refactor shape; Medium on CBV) — names CLI, CBV, CNT, BIN, CONF, IAC. Decided: one refactor to `build_cbom_from_findings`, one registry of `ecdat:*` property keys including `ecdat:artifact_type`. DEP consequence: DEP edits nothing there. Verified in the snapshot: `_finding_to_component` emits every finding as `assetType: "algorithm"` with `primitive: "other"` when the algorithm is not in `_PRIMITIVE_MAP`, so a DEP finding with `algorithm = "UNKNOWN"` would appear as an "algorithm" component named by its evidence, not as a library. Whether and how DEP findings enter the CBOM is not decided — §11 G2, G5.

**C-18 · `requirements.txt` contention; `cryptography` unpinned** (High on pinning) — names BIN, IAC, RBAC, CNT, CLI, CBV. DEP adds no dependency (§6). Wave 0 pins `cryptography` independently.

**C-19 · five features rewrite the same scope-honesty table** (High on process) — names CNT, BIN, IAC, CONF, CMP. Decided: scope-truth documents are edited once by a single named scope editor; "Feature PRs create their own scope doc and must not touch `PRODUCT_DESCRIPTION.md`." DEP consequence: DEP creates only `docs/DEPENDENCY_SCANNING_SCOPE.md` — §11 G10.

**C-20 · the repository contradicts itself about what is in scope** (**Low — requires human sign-off**) — names CNT, BIN, IAC as blocked; the question itself covers "binary/container/dependency scanning". Decided: "None proposed." DEP consequence: DEP is not blocked by name, but the contradiction is real for dependency scanning too — `AGENT_RULES.md` #6 lists it in scope, while `docs/SOURCE_SCANNING_SCOPE.md` ("Deliberate non-claims") lists "third-party dependency inventories/SBOMs" as not analysed, and `PRODUCT_DESCRIPTION.md` §5 marks binary/container scanning out of scope. That non-claim is about *source* scanning and DEP's output is a declaration inventory for known crypto libraries, not an SBOM — but reconciling the documents is the scope editor's job (C-19), not DEP's. §11 A1.

**C-10 · `organization_id` scoping is assigned to nobody** (Medium) — Shared Index lists `db/crud.py` with DEP. DEP adds no query function, so it adds no tenant-scoping obligation. Nothing to do.

### 10.3 Shared Resource Index rows naming DEP — one-line status

| Resource (§5) | Features | Contract state | DEP action |
|---|---|---|---|
| `scanner/cli.py` | DEP CNT BIN IAC CONF | Conflicting ! (C-11) | one helper + one hook + one rewrite; queue behind Wave 2 |
| `scanner/finding.py` | DEP CNT BIN CONF | Conflicting ! (C-03) | **do not edit**; §11 G1 |
| `api/services/scan_runner.py` | DEP CNT BIN IAC CONF | Conflicting ! (C-02) | **do not edit** |
| `api/models.py` | DEP CNT CONF ENR ASP AUD CMP | Conflicting (§1.2) | five defaulted fields on `FindingOut`; no new model |
| `db/schema.sql`, `db/models.py` | DEP CNT CONF ENR RBAC AUD TRI DFS | Conflicting (§2) | statements quoted from §2.2 only |
| `db/crud.py` | DEP CONF ENR RBAC AUD ASP CMP TRI | Conflicting ! (C-10) | five aliases + two validations, no functions |
| `findings` (columns) | DEP CNT CONF TRI BIN | Conflicting (§2.2) | five written, two untouched |
| `tests/test_scan_runner.py` | DEP CONF | Conflicting (C-02) | add one test; edit none of the three existing |
| `--target-type` / `--image-tar` / `--binaries` / `--scan-type` | CNT BIN IAC DEP | Conflicting ! (C-11) | value `dependency` only |


---

## 11. Pre-Answered Ambiguities

**How to read this section.** `AGENT_RULES.md` #4: a situation not covered here means **stop and ask a human; do not guess**.

**About "the team's resolved answer".** Contract §7 opens with "Nothing below is decided." No open sign-off item has a recorded human answer. Each `A` entry therefore quotes the part the contract *did* decide (its "Resolution" line) and states what is still open. Where the contract is silent on something DEP genuinely needs (`G` entries), the entry says **NOT COVERED BY CONTRACT** and gives a *provisional default* — the spec author's, not the team's — so the implementer is not blocked; a human confirms or replaces it in the PR. Where a default is provisional the entry names who must confirm.

### 11.1 Step 1 open questions → where each is answered

| Step 1 question (`dependency-scanning.md` §5) | Answered in |
|---|---|
| Are Python, Node.js and Java all required for the SIH demo? | G6 |
| Declared dependencies only, or transitive dependencies from lockfiles too? | G4 |
| How do non-cryptographic package vulnerabilities map to crypto-specific risk tiers? | G3 (they do not: out of scope) |
| Should dependency entries become CBOM components directly? | G5, G2 |
| Assumption: local/offline, no registry queries | §3 out-of-scope; not contradicted by the contract |
| Assumption: source-scanner semantics unchanged | A4 (default `--scan-type` is `source` only) |

### 11.2 Open sign-off items from contract §7 that touch DEP (`A`)

**A1 — C-20: is binary/container/dependency scanning in scope?** *(Low; contract: "None proposed")*
- Decided: nothing. `AGENT_RULES.md` #6 says dependency scanning is in scope; `PRODUCT_DESCRIPTION.md` §5 (binary/container) and `docs/SOURCE_SCANNING_SCOPE.md` ("third-party dependency inventories/SBOMs") disagree. Contract §6 blocks CNT, BIN, IAC by name on this sign-off; it does not name DEP.
- **If** C-20 is still unsigned when you start → implement on your feature branch; do not treat `AGENT_RULES.md` #6 as ratified in any document you write. **Do not open the merge** until a human records the sign-off in the PR — whether DEP may merge before C-20 resolves is **NOT COVERED BY CONTRACT**, so this is a hold, not a resolution.
- **If** anyone asks you to "fix" the contradiction in `PRODUCT_DESCRIPTION.md`, `README.md` or `ARCHITECTURE.md` → refuse; C-19 reserves those to one scope editor. `docs/DEPENDENCY_SCANNING_SCOPE.md` states DEP's own limits only.

**A2 — C-02: persist or drop sub-threshold findings?** *(Medium; owners: product + DB lane; CONF owner consulted)*
- Decided: the gate is CONF's to replace; DEP must not edit `api/services/scan_runner.py`; until CONF lands DEP is CLI-only and says so.
- Open: whether sub-threshold findings are dropped or persisted with their band.
- **If** a CLI scan with `--scan-type dependency` prints findings but `POST /scans` stores none → expected; not a bug. Do not loosen the filter.
- **If** you are tempted to emit `confidence = "high"` so the rows survive the gate → do not. That misstates the evidence (a manifest declaration is not a traced call site) and is the local patch C-02 forbids.
- **If** CONF's gate has already landed when you start → DEP code is unchanged; only the P1 precondition and the scope-doc wording ("CLI-only") change, and the wording is updated to match what CONF shipped.

**A3 — C-03: confidence backfill, broken tests, `--fail-on` interaction** *(Medium; CONF owner)*
- Decided: two-field model (`confidence_score`, `confidence_band`); legacy `confidence` becomes a derived mirror (`VERIFIED→high`, else `unverified`).
- Open: (a) backfill of old rows, (b) who updates the tests asserting `confidence == "high"` and whether the 18-finding demo baseline moves, (c) whether `--fail-on` considers band.
- **If** a DEP finding at `CRITICAL` (e.g. npm `md5`, `weak_by_default: true`) fails `--fail-on HIGH --scan-type dependency` with exit `2` → expected today: `risk_engine` scores the algorithm, not the evidence strength. Do not lower the tier, change a rule's `weak_by_default`, or special-case dependency findings; answer (c) belongs to CONF and the scanner lane.
- **If** a DEP finding has `algorithm = "UNKNOWN"` → `risk_tier = "UNSCORED"`, which `_violates_policy` never treats as a violation (`_TIER_ORDER["UNSCORED"] = 4`). Expected.
- **If** a test that passed at P6 fails after your change and it asserts `confidence == "high"` → it is C-03(b), owned by CONF. Do not edit it; report it.
- The 18-finding demo baseline is unaffected by DEP because the default scan type is `source` only.

**A4 — C-11: final CLI flag grammar; does bare `ecdat TARGET` survive?** *(Medium; scanner lane / Shashank)*
- Decided: one repeatable `--scan-type {source,dependency,config,binary,container}`, default `source` only (§3.5).
- Open: exact spelling and the bare-alias question.
- **If** P2 finds no `--scan-type`, or it spells the value differently from `dependency` → **stop and report** (`AGENT_RULES.md` #9). Do not add the flag yourself and do not add a boolean.
- **If** the flag is given only `dependency` → the source scan does **not** run; **if** given `source` and `dependency` → both run and the lists are concatenated. That dispatch belongs to the Wave-2 change; DEP supplies only `_scan_dependency` and must not restructure it.
- **If** someone asks about `ecdat scan ...` wrapper syntax → irrelevant to DEP; `scanner/ecdat_cli.py` is the CLI feature's (SOLE). Tests call `scanner.cli.main([...])` / `python -m scanner.cli`.

**A5 — C-23: group or list duplicate package findings; grouped risk tier** *(Medium; DB lane + dashboard lane)*
- Decided: de-duplication key `(artifact_type, artifact_ref, package_ecosystem, package_name, package_version, algorithm)`; DEP/CNT/BIN rows are retained as distinct evidence; the dashboard groups by `package_name`.
- Open: whether the dashboard groups or lists; whether a grouped row's tier is the maximum.
- **If** the same package appears in two manifests (say `requirements.txt` and `pyproject.toml`) → different `artifact_ref`, so both rows stay.
- **If** the same package appears twice in one file with the same version → one row (first occurrence wins). With different versions → two rows.
- **If** you notice a CNT or BIN finding for the same library → do nothing; never merge, drop, or detect cross-engine duplicates.

### 11.3 Gaps the contract does not cover (`G`)

**G1 — what carries the five artefact columns from the scanner to persistence?** — **NOT COVERED BY CONTRACT.** *(Confirm: scanner lane (Shashank) **and** CONF owner — precondition P5.)*
- Facts: `scanner/finding.py` is FROZEN ("Only CONF may add fields, once"); §2.2 adds five columns DEP must fill; C-26 says the four engines "emit `Finding` unchanged in shape". The contract names no carrier.
- Provisional default: `DependencyFinding(Finding)` in `dependency_engine.py` (§7.6). It serializes through `dataclasses.asdict` (checked against the snapshot), needs no edit to a FROZEN file, and `scan_file` still returns `list[Finding]`-compatible objects.
- **If** the scanner lane or the CONF owner rejects the subclass → **stop**. Do not edit `scanner/finding.py`, do not stuff the values into `matched_call`, do not add a side channel.
- **If** CONF's once-only edit to `scanner/finding.py` has already added fields with **exactly** these five names → use them, delete `DependencyFinding`, and pass the values to `Finding` directly. **If** the names or types differ → stop and ask.
- Steps 10 and 13 of §8 do not merge without this confirmation.

**G2 — how do dependency findings appear in the CBOM?** — **NOT COVERED BY CONTRACT.** *(Consult: CBOM lane, Maitreyi; read-only.)*
- Facts: DEP may not edit `api/services/cbom_generator.py`. In the snapshot each finding becomes an `assetType: "algorithm"` component; an unrecognised `algorithm` gets `primitive: "other"`. `Finding.primitive = "library"` (DEP's value, listed nowhere in the contract) and `algorithm = "UNKNOWN"` therefore yield an "algorithm" component that is really a library declaration. Because of C-02, no dependency finding reaches the API's `GET /scans/{id}/cbom`; only a CLI-side CBOM path (CLI/CBV work) could show it.
- **If** you are asked to change how findings become CBOM components → do not; hand it to the CBOM lane.
- **If** the CBOM lane asks DEP to change `primitive` or `algorithm` values → that is a rule-pack data change (`scanner/dependency_rules/*.yaml`), allowed; the interface in §7 is unchanged.

**G3 — which declared packages become findings, and are vulnerabilities mapped?** — **NOT COVERED BY CONTRACT.** *(Provisional; confirm: scanner lane.)*
- Provisional default: a package yields a finding only if it is in a rule pack; the seed packs contain known cryptographic libraries only. No vulnerability/CVE data, no registry access, no mapping of non-cryptographic vulnerabilities onto risk tiers (`risk_engine.py` is FROZEN and documented as the sole authority, C-04).
- **If** asked to "report all dependencies" or emit a full SBOM → out of scope; refuse.
- **If** asked to add a package → add a rule-pack entry **and** a fixture assertion. Set a concrete `algorithm` only when the package name itself fixes it (`md5`, `sha1`); otherwise `algorithm: "UNKNOWN"`, `primitive: "library"`.
- **If** a pack entry lacks a required key → it is skipped with a `[warn]`; never crash.

**G4 — direct vs transitive dependencies** — **NOT COVERED BY CONTRACT.** *(Provisional; confirm: scanner lane + DB lane.)*
- No column for it exists in §2.2 and none may be added by DEP (§2.3).
- Provisional default: lock files (`package-lock.json`, `Pipfile.lock`, `poetry.lock`) are parsed completely, so transitive entries can yield findings; the distinction is not persisted. The manifest section or lock file name is visible only inside `matched_call` (`"<scope>: <declared>"`).
- **If** asked to add an `is_direct` or `dependency_depth` column → refuse; §2 changes go through the contract, not through this feature.

**G5 — should dependencies be CycloneDX components?** — **NOT COVERED BY CONTRACT.** *(Consult: CBOM lane.)*
- Provisional default: no. DEP produces evidence rows only; no `library`-typed component, no `dependencies` graph, no PURLs.
- **If** asked to emit CycloneDX component or dependency structures from DEP → out of scope (C-14 keeps the generator in one place).

**G6 — is Java (Maven) required for the SIH demo?** — **NOT COVERED BY CONTRACT.** *(Product decision.)*
- Contract facts: `maven` is a listed `package_ecosystem`; `AGENT_RULES.md` #6 lists Java in scope.
- Provisional default: **implement** `pom.xml` support (steps 9 and 12).
- **If** a human answers "Java not required" → skip steps 9 and 12, delete `maven.yaml` if created, remove `"pom.xml"` from `MANIFEST_FILENAMES`, drop the two `pom.xml` tests (§12.2 tests 20–21), and expect **19** tests in `tests/test_dependency_engine.py`, not 21.
- **If** a `pom.xml` uses `${property}` versions, ranges, or a parent POM → the finding is still emitted; `package_version` is `None`; nothing is resolved.

**G7 — meaning of `line = 0`** — *Contract-supported.* C-13: "`line=0` renders as `—`, never `0`." DEP uses `0` for JSON, TOML and XML manifests; `requirements*.txt` carries the real 1-based line.
- **If** the dashboard shows `0` → it is a C-13 (DFS/FE) defect, not DEP's. Edit no `dashboard/**` file.

**G8 — who owns `SCAN_MAX_ARTIFACT_BYTES`, and what is its value?** — **NOT COVERED BY CONTRACT** beyond C-12 ("a shared `SCAN_MAX_ARTIFACT_BYTES`") and §3.3 (the name).
- **If** precondition P3 fails (constant absent from `scanner/constants.py`) → stop and report. Do not define it in `dependency_engine.py`, do not edit `scanner/constants.py`, do not hard-code a number.
- DEP never chooses the value.

**G9 — dependency scans through `POST /scans`** — **NOT COVERED BY CONTRACT.**
- Facts: `api/services/scan_runner.py` is FROZEN, launches the scanner with no scan-type argument (default `source`), and filters on `confidence == "high"`.
- **If** asked to make API scans run the dependency engine → out of scope; needs CONF's gate change plus a `scan_runner` / `ScanCreateRequest` change owned by someone else (`api/routers/scans.py` is COORDINATED; the contract names CNT for `ScanCreateRequest`).

**G10 — `docs/DEPENDENCY_SCANNING_SCOPE.md` is not one of C-19's four named scope docs** — *Partly covered.* §1.5 covers `docs/*_SCANNING_SCOPE.md` as SOLE per file; C-19's "after all four scanner scope docs exist" list omits it.
- **If** the scope editor asks whether DEP's doc is required first → tell them it exists as a fifth input; do not edit other docs on their behalf.

**G11 — rule-pack location: `scanner/dependency_rules/` vs §3.1's `scanner/rules/<domain>.yaml`** — *Contract-internal tension.*
- §1.1 assigns DEP the directory `scanner/dependency_rules/` as SOLE; §3.1's generic naming line says new rule packs go in `scanner/rules/<domain>.yaml`.
- Rule: follow §1.1 (the specific ownership entry). Additional reason: `multilang_engine.load_rules` reads every `scanner/rules/*.yaml`, requires `language` + `rules` keys, and logs a "malformed rule file" warning for anything else; DEP's `ecosystem` + `packages` files would trigger that on every scan.
- **If** a reviewer asks to move the packs → do not; escalate the §1.1/§3.1 inconsistency to the contract editor.

**G12 — what confidence does DEP emit, and who bands it?** — **NOT COVERED BY CONTRACT** for `dependency_manifest`. *(Confirm: CONF owner.)*
- Provisional default: `confidence = "unverified"` (the existing legacy value, `LEGACY_CONFIDENCE`); no `confidence_score`, `confidence_band` or signals are set by DEP. Signal vocabulary and scoring are CONF's (`scanner/confidence.py`, SOLE).
- **If** CONF requires DEP to supply named signals → that arrives as CONF's change (C-03: only CONF adds fields); DEP does not invent signal names.

### 11.4 Implementation-level situations

| # | If … | Do … |
|---|---|---|
| I1 | `scan_file` receives a path that is not a recognised manifest name | write one `[warn]` line to stderr; return `[]`; do not raise |
| I2 | a manifest is malformed, empty, has the wrong JSON/TOML shape, is not UTF-8, or exceeds `SCAN_MAX_ARTIFACT_BYTES` | one `[warn]` to stderr; contribute `[]`; the scan and exit code are otherwise unaffected |
| I3 | a version is a range, wildcard, tag, URL or VCS reference (`>=3.1`, `^2.3.0`, `1.x`, `latest`, `git+https://…`) | still emit the finding; `package_version = None`; `matched_call` holds the name and the specifier text only, never the raw line or URL |
| I4 | a manifest sits under `node_modules`, `venv`, `env`, `build`, `dist`, `target` (or another `SKIP_DIRS` entry) below the scan root | skip it; do not modify `SKIP_DIRS` |
| I5 | a manifest is a symlink whose target lies outside the scan root | skip with a `[warn]`; never read outside the root |
| I6 | you are about to use `import re` or a regular expression to split a requirement line or version | do not (`AGENT_RULES.md` #5, applied to every parser here); use `str` methods |
| I7 | you are about to run `pip`, `npm`, `mvn`, or open a network connection | do not; the engine is pure, offline and path-based (§3.1) |
| I8 | `weak_by_default` is true for a package whose algorithm is `UNKNOWN` (e.g. `pycrypto`) | keep it: the flag records the library's status, the risk engine still yields `UNSCORED`; do not invent an algorithm |
| I9 | `--redact-paths` is set | `file` and `artifact_ref` must both be relative or redacted; verify with the §12.2 test 19 |
| I10 | a PR wants a new table, column, index or migration number | refuse; §2 changes go through the contract editor |


---

## 12. Test Plan / Definition of Done

`AGENT_RULES.md` #7: run the commands below and read their output before declaring the task done. Run everything from the repository root, in the project's Python 3.11 environment.

### 12.1 Commands and expected output

| # | Command | Expected |
|---|---|---|
| T0 | `pytest --collect-only -q -p no:cacheprovider \| tail -1` (run **before** any change — this is P6) | `N tests collected in …s`. **Write N down.** Snapshot value in the authoring sandbox (Python 3.12): `64 tests collected` |
| T1 | `pytest tests/test_dependency_engine.py -v -p no:cacheprovider` | 21 lines ending `PASSED`, in the order of §12.2, then `21 passed in …s`. No `FAILED`, no `ERROR`. Where symlinks cannot be created (some Windows setups) test 16 reports `SKIPPED` and the last line is `20 passed, 1 skipped`. If G6 is answered "Java not required": 19 tests, `19 passed` |
| T2 | `pytest tests/test_scan_runner.py -v -p no:cacheprovider` | 4 lines `PASSED` (the 3 existing tests plus `test_run_scan_default_ignores_dependency_manifests`), then `4 passed in …s` |
| T3 | `pytest -q -p no:cacheprovider` | last line `M passed`, where **M = N + 22** (N + 20 if Java is dropped), `0 failed`, `0 errors`. Snapshot arithmetic: 64 + 22 = **86** |
| T4 | `pytest tests/test_cli_secure.py tests/test_scanner_battle.py tests/test_realworld_source_scanner.py -q -p no:cacheprovider` | same pass count as before your change (default `source` behaviour untouched) |
| T5 | `python -m scanner.cli tests --fail-on CRITICAL >/dev/null; echo $?` versus the same command on the pre-change commit | identical exit code and identical stdout (default scan type is `source` only; C-11) |
| T6 | `python -c "import scanner; print(sorted(scanner.__all__))"` | list contains `scan_dependency`; no traceback |
| T7 | `grep -rnE "^\s*(import re\b\|from re import)" scanner/dependency_engine.py` | no output (`AGENT_RULES.md` #5) |
| T8 | `git diff --stat main...HEAD` | changed files are a subset of §5.1; **none** of `scanner/finding.py`, `api/services/scan_runner.py`, `api/services/risk_engine.py`, `scanner/constants.py`, `requirements.txt`, `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md` appear |
| T9 | Migration applied to a **fresh** database and re-applied: `docker compose exec -T db psql -U ecdat -d ecdat -v ON_ERROR_STOP=1 < db/migrations/003_artifact_scanning.sql` (run twice) | first run: `ALTER TABLE` ×7, `CREATE INDEX` ×2. Second run: no `ERROR`; PostgreSQL 16 prints `NOTICE:  column "…" of relation "findings" already exists, skipping` ×7 and `NOTICE:  relation "idx_findings_…" already exists, skipping` ×2. Then `docker compose exec -T db psql -U ecdat -d ecdat -c "\d findings"` lists the seven new columns and both indexes |
| T10 | Fresh-volume check: `docker compose down -v && docker compose up -d db`, then the `\d findings` command from T9 | same seven columns and two indexes, applied by `schema.sql` **and** by the `04_` mount without error (C-01 lockstep) |

`POSTGRES_USER` / `POSTGRES_DB` in T9/T10 are the `.env.example` defaults (`ecdat`); use your `.env` values.

### 12.2 Test list

Create the tests in exactly this order, using only `tmp_path`, `capsys`, `monkeypatch` and the standard library; no network, no dependence on the working directory. Fixture files are written into `tmp_path`. "Finding" = the object returned by `scan_file` / `scan_directory`; keys are attribute names.

| # | Test name | Fixture | Must assert |
|---|---|---|---|
| 1 | `test_is_manifest_matches_only_supported_filenames` | names only | `is_manifest` is true for `requirements.txt`, `requirements-dev.txt`, `requirements_prod.txt`, `pyproject.toml`, `Pipfile.lock`, `poetry.lock`, `package.json`, `package-lock.json`, `pom.xml`; false for `README.txt`, `requirements.md`, `package.json.bak`, `Pipfile`, `yarn.lock`, `build.gradle` |
| 2 | `test_normalize_package_name_per_ecosystem` | — | pypi `PyCrypto`→`pycrypto`; pypi `Py_Crypto.Dome`→`py-crypto-dome`; npm `@Scope/Name`→`@scope/name`; npm `Crypto-JS`→`crypto-js`; maven `Org.BouncyCastle:BCProv-JDK18on`→`org.bouncycastle:bcprov-jdk18on` |
| 3 | `test_load_rules_reads_the_shipped_packs` | none (uses `DEPENDENCY_RULES_DIR`) | `load_rules()` has `pypi` and `npm`; `pycrypto` ∈ pypi, `md5` ∈ npm; every rule dict has `name`, `library`, `algorithm`, `primitive`, `weak_by_default` |
| 4 | `test_load_rules_skips_bad_files_and_entries_with_warnings` | rules dir with: a valid `pypi` file holding one good entry, one entry missing `algorithm`, one entry with `weak_by_default: "yes"`; a file with no `ecosystem`; a file with invalid YAML | result contains only the good entry; stderr holds exactly **4** `[warn]` lines |
| 5 | `test_requirements_txt_pinned_pycrypto_emits_unknown_algorithm_finding` | `requirements.txt`: `pycrypto==2.6.1` / `requests==2.31.0` | exactly one finding; `line == 1`; `matched_call == "requirements: pycrypto==2.6.1"`; `algorithm == "UNKNOWN"`; `primitive == "library"`; `library == "pycrypto"`; `language == "python"`; `weak_by_default is True`; `confidence == "unverified"`; `key_size is None`; `detection_method == "dependency_manifest"`; `artifact_type == "DEPENDENCY_MANIFEST"`; `artifact_ref == file`; `package_ecosystem == "pypi"`; `package_name == "pycrypto"`; `package_version == "2.6.1"`; `dataclasses.asdict` contains the five artefact keys |
| 6 | `test_requirements_txt_ignores_noise_and_never_leaks_urls_or_hashes` | 11-line file: comment; `-r base.txt`; `--index-url https://…`; `-e .`; `./local/pkg`; `git+https://example.com/x.git#egg=x`; `pycrypto==2.6.1` followed by a line-continuation backslash, continued on the next line by `--hash=sha256:aaaa`; `pycryptodome==3.20.0  # inline comment`; `cryptography[ssh]==41.0.7 ; python_version >= "3.8"`; `pyopenssl @ https://example.com/pyopenssl.whl` | exactly four findings, `(line, package_name, package_version, matched_call)` = `(7, pycrypto, 2.6.1, "requirements: pycrypto==2.6.1")`, `(9, pycryptodome, 3.20.0, "requirements: pycryptodome==3.20.0")`, `(10, cryptography, 41.0.7, "requirements: cryptography==41.0.7")`, `(11, pyopenssl, None, "requirements: pyopenssl")`; no `matched_call` contains `://` or `hash` |
| 7 | `test_requirements_txt_ranges_and_wildcards_leave_version_unset` | `requirements-dev.txt`: `pycryptodome>=3.10,<4` / `PyCryptodomex==3.*` | two findings: `(1, pycryptodome, None, "requirements-dev: pycryptodome>=3.10,<4")` and `(2, pycryptodomex, None, "requirements-dev: PyCryptodomex==3.*")` |
| 8 | `test_package_json_sections_and_exact_version_predicate` | `package.json` with `dependencies` {`md5: 2.3.0`, `sha1: ^1.1.1`, `left-pad: 1.3.0`}, `devDependencies` {`crypto-js: git+https://example.com/crypto-js.git`}, `optionalDependencies` {`node-forge: 1.x`}, `peerDependencies` = the string `"not-an-object"` | four findings, all `line == 0`: `md5` (`2.3.0`, `"dependencies: md5@2.3.0"`, `MD5`), `sha1` (`None`, `"dependencies: sha1@^1.1.1"`, `SHA-1`), `crypto-js` (`None`, `"devDependencies: crypto-js"`, `UNKNOWN`), `node-forge` (`None`, `"optionalDependencies: node-forge@1.x"`, `UNKNOWN`). `_is_exact_version`: `2.3.0` and `1.0.0-beta.1` true; `^2.3.0`, `>=1`, `1.x`, `*`, `latest`, empty string false |
| 9 | `test_package_lock_json_v3_and_v1_shapes` | (a) v3 `packages` with keys `""`, `node_modules/md5` (2.3.0), `node_modules/foo/node_modules/sha1` (1.1.1), `node_modules/crypto-js` (`link: true`), `node_modules/node-forge` (1.3.1); (b) v1 `dependencies` tree: `md5` 2.3.0 containing nested `sha1` 1.1.1 | (a) exactly `md5 2.3.0`, `node-forge 1.3.1`, `sha1 1.1.1`, with `matched_call` `"package-lock.json: <name>@<version>"`; root and link skipped; (b) exactly `md5 2.3.0` and `sha1 1.1.1` |
| 10 | `test_pyproject_toml_pep621_and_poetry_tables` | `[project] dependencies = ["cryptography>=41", "requests"]`; `[project.optional-dependencies] dev = ["pycryptodome==3.20.0"]`; `[tool.poetry.dependencies]` with `python = "^3.11"`, `pycrypto = "2.6.1"`, `pyopenssl = {version = "^24.0", extras = ["x"]}`; `[tool.poetry.group.test.dependencies] pycryptodomex = "3.19.0"` | five findings, all `line == 0`, `(package_name, package_version, matched_call)`: `(cryptography, None, "project.dependencies: cryptography>=41")`, `(pycryptodome, 3.20.0, "project.optional-dependencies.dev: pycryptodome==3.20.0")`, `(pycrypto, 2.6.1, "tool.poetry.dependencies: pycrypto==2.6.1")`, `(pyopenssl, None, "tool.poetry.dependencies: pyopenssl^24.0")`, `(pycryptodomex, 3.19.0, "tool.poetry.group.test.dependencies: pycryptodomex==3.19.0")`; `python` is skipped |
| 11 | `test_pipfile_lock_and_poetry_lock` | `Pipfile.lock`: `default` {`pycrypto: ==2.6.1`}, `develop` {`cryptography: ==41.0.7`, `requests: ==2.31.0`}; `poetry.lock` with `[[package]]` entries `pycryptodome 3.20.0` and `requests 2.31.0` | Pipfile: `(cryptography, 41.0.7, "develop: cryptography==41.0.7")` and `(pycrypto, 2.6.1, "default: pycrypto==2.6.1")`; poetry: only `(pycryptodome, 3.20.0)` |
| 12 | `test_non_crypto_packages_produce_no_findings` | `requirements.txt`: `requests==2.31.0`, `flask>=3`; `package.json`: `left-pad`, `lodash` | `scan_directory(tmp_path) == []` |
| 13 | `test_malformed_manifests_return_empty_without_raising` | in separate sub-directories: `package.json` = `{ not json`; `pyproject.toml` = `[[[`; `package-lock.json` = `[]`; `Pipfile.lock` = `"str"`; a `requirements.txt` containing the bytes `ff fe 00` then `pycrypto`; an empty `requirements.txt` | `scan_file` returns `[]` for all six and raises for none; stderr holds exactly **5** `[warn]` lines (the empty file warns nothing) |
| 14 | `test_oversize_manifest_is_skipped_with_warning` | `monkeypatch.setattr(dependency_engine, "SCAN_MAX_ARTIFACT_BYTES", 10)`; `requirements.txt` = `pycrypto==2.6.1` | `[]` and a `[warn]` on stderr |
| 15 | `test_duplicate_declarations_are_deduplicated_by_c23_key` | `requirements.txt`: `pycrypto==2.6.1` / `PyCrypto==2.6.1` / `pycrypto==2.7`; plus `sub/pyproject.toml` with `dependencies = ["pycrypto==2.6.1"]` | file alone → `[(1, "2.6.1"), (3, "2.7")]` (first occurrence wins; different version is kept); `scan_directory` returns **two** rows with version `2.6.1` (different `artifact_ref` → kept, C-23) |
| 16 | `test_scan_directory_skips_skip_dirs_and_escaping_symlinks` | root with `requirements.txt` (pycrypto), `node_modules/md5/package.json`, `venv/requirements.txt`, `sub/package.json` (md5); a sibling directory outside the root holding `package.json` (sha1); `root/linked/package.json` = symlink to that outside file. Skip via `pytest.skip` when `os.symlink` raises `OSError` / `NotImplementedError` | findings' relative paths are exactly `requirements.txt` and `sub/package.json`; exactly **1** `[warn]` (the escaping symlink) |
| 17 | `test_output_is_sorted_and_engine_writes_nothing_to_stdout` | `b/package.json` (md5), `a/requirements.txt` (pycrypto), `requirements.txt` (pycrypto) | three findings, ordered by `(file, line, package_name)`; `capsys.readouterr().out == ""` |
| 18 | `test_cli_scan_type_dependency_emits_scored_artifact_findings` — *needs the Wave-2 `--scan-type` flag (P2)* | directory with `requirements.txt` (`pycrypto==2.6.1`), `package.json` (`{"dependencies":{"md5":"^2.3.0"}}`), `legacy.py` (`import hashlib` / `hashlib.md5(b'x')`) | `main([dir, "--scan-type", "dependency"]) == 0`; stdout parses as a JSON **array** of exactly 2 dicts, both `detection_method == "dependency_manifest"` and `artifact_type == "DEPENDENCY_MANIFEST"` (the source file is not scanned); the md5 element has `risk_tier == "CRITICAL"` and `package_version is None`; the pycrypto element has `risk_tier == "UNSCORED"` and `package_version == "2.6.1"`. `main([dir])` returns 0 and yields exactly 1 element, `file == "legacy.py"`, with `artifact_type` absent or `"SOURCE_FILE"`. `main([dir, "--scan-type", "source", "--scan-type", "dependency"])` yields 3 elements |
| 19 | `test_cli_redact_paths_rewrites_artifact_ref` — *needs P2* | same directory as test 18 | with `--scan-type dependency --redact-paths`: for every element `artifact_ref == file`, neither is absolute (`os.path.isabs` false), and `str(tmp_path)` does not occur anywhere in stdout. Same assertions without `--redact-paths` |
| 20 | `test_pom_xml_declared_bouncycastle_dependencies` — *conditional (G6)* | `pom.xml` in the POM namespace with three `<dependency>` entries: `org.bouncycastle:bcprov-jdk18on` `1.77`; `org.bouncycastle:bcprov-jdk15on` with version `${bc.version}`; `junit:junit` `4.13` | two findings: `(org.bouncycastle:bcprov-jdk15on, None)` and `(org.bouncycastle:bcprov-jdk18on, 1.77)`; `language == "java"`; `package_ecosystem == "maven"`; `line == 0` |
| 21 | `test_pom_xml_doctype_is_rejected_before_parsing` — *conditional (G6)* | `pom.xml` = `<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><project><dependencies></dependencies></project>`; `monkeypatch` replaces `dependency_engine.ET.fromstring` with a function that raises `AssertionError` | `scan_file` returns `[]`, the replacement is never called, and stderr contains `[warn]` |

**`tests/test_scan_runner.py` — add one test, after the three existing ones:**

| Test name | Fixture | Must assert |
|---|---|---|
| `test_run_scan_default_ignores_dependency_manifests` | a directory (`tmp_path`) holding `legacy.py` (`import hashlib` / `hashlib.md5(b'fixture')`) and `requirements.txt` (`pycrypto==2.6.1`); same in-memory SQLite setup and `run_scan(session, target_path=str(tmp_path), scan_id=queued.id)` call as the first existing test | `result["status"] == "completed"`; `result["finding_count"] == 1`; the persisted findings are exactly one row with `algorithm == "MD5"` and `artifact_type == "SOURCE_FILE"` |

### 12.3 Definition of Done

All of the following, each checked against real output:

1. §8 preconditions P1–P6 passed, and P5 (G1) is recorded in the PR description.
2. T0–T8 produce the expected results in §12.1; T9 and T10 are run by the DB lane reviewer or the author on a machine with Docker, and the output is pasted in the PR.
3. Every file changed is in §5.1; T8 shows no §5.2 file.
4. `docs/DEPENDENCY_SCANNING_SCOPE.md` exists and contains every statement required by §8 step 18, including "CLI-only until CONF replaces the `scan_runner` gate".
5. The PR description lists every §11 provisional default the reviewer must confirm (G1, G3, G4, G6, G12) and states that A1 (C-20) is unresolved.
6. Every reviewer in §1's sign-off table has replied, and their names are recorded there.

### 12.4 What was and was not verified while writing this spec

- **Run in the authoring sandbox:** the unmodified repository suite (`64 passed`, Python 3.12.3); the risk-engine outcomes shown in §7.10/§7.11 (`md5` → `CRITICAL`, `algorithm = "UNKNOWN"` → `UNSCORED`); `dataclasses.asdict` on a `Finding` subclass; `run_scan` on a directory containing `requirements.txt` plus a source file (1 finding persisted); the `artifact_ref` leak without the §7.9 rewrite, and its absence with it.
- **Throwaway check:** a scratch implementation of §8 steps 10–13, kept outside the repository, was run against tests 1–17, 20 and 21 as written above: **19 passed**. This confirms the fixtures and expected values agree with the rules in §8; it is not the real implementation and its results do not replace T1.
- **Not run:** tests 18 and 19 (the `--scan-type` flag does not exist in the snapshot); T9 and T10 (no PostgreSQL/Docker in the sandbox); anything under Python 3.11. The expected `psql` NOTICE text is stated from PostgreSQL behaviour, not observed here.

---

## 13. Rollback Plan

**Principle.** DEP is opt-in (`--scan-type dependency`) and every schema change is additive, so most failures are undone by reverting code without touching any database. Work only on the feature branch (`AGENT_RULES.md` #8); on `main`, undo by a **reviewed revert PR**, never a force-push or direct commit.

### 13.1 Symptom → action

| Symptom | First action | Then |
|---|---|---|
| Default (`source`) scan output or exit code differs from before | revert the `scanner/cli.py` hunks (§7.9); the `artifact_ref` rewrite is guarded by `artifact_type == "DEPENDENCY_MANIFEST"`, so it is the most likely cause only if that guard was dropped | re-run T3, T4, T5 |
| `import scanner` raises | revert `scanner/__init__.py` (§7.8) | re-run T6 |
| Only the dependency stage misbehaves (wrong findings, crash) | delete the one-line hook in the `dependency` branch of `scanner/cli.py` and nothing else; the engine, rules and schema can stay | dependency scanning is then unreachable; default path unchanged |
| Fresh `docker compose up` fails at database init | revert the `docker-compose.yml` mount line **and** the `db/schema.sql` hunk together (C-01 lockstep); existing databases are unaffected | re-run T10 |
| API response validation errors | revert `api/models.py` (all five fields have defaults, so no consumer depends on them) | re-run T2, T3 |
| Persistence drops or rejects artefact values | revert the `db/crud.py` hunk (aliases + validations) | findings then persist without the five values (no data loss for source findings) |
| Any test that passed at P6 now fails | bisect by reverting §8 steps in **reverse order (18 → 1)** until the count returns to N | fix forward on the branch; do not edit the failing test unless it is one of your own |

### 13.2 Database

- Migration `003_artifact_scanning.sql` is shared with CNT, BIN and IAC. **DEP must not drop its columns or remove its file unilaterally**; the seven columns are nullable or defaulted (`artifact_type` defaults to `'SOURCE_FILE'`), so leaving them in place is harmless.
- Reverting DEP's PR must leave other owners' lines in `003_artifact_scanning.sql` and their `db/models.py` entries untouched (§8 step 1, 4).
- Only if the DB lane (Ronak) approves **and** no other feature has landed on migration 003, the columns can be removed. Take a backup first (`docker compose exec -T db pg_dump -U ecdat ecdat > backup.sql`), then:

```sql
DROP INDEX IF EXISTS idx_findings_package;
DROP INDEX IF EXISTS idx_findings_artifact_type;
ALTER TABLE findings DROP COLUMN IF EXISTS layer_digest;
ALTER TABLE findings DROP COLUMN IF EXISTS image_digest;
ALTER TABLE findings DROP COLUMN IF EXISTS package_version;
ALTER TABLE findings DROP COLUMN IF EXISTS package_name;
ALTER TABLE findings DROP COLUMN IF EXISTS package_ecosystem;
ALTER TABLE findings DROP COLUMN IF EXISTS artifact_ref;
ALTER TABLE findings DROP COLUMN IF EXISTS artifact_type;
```

  The same removal must then be applied to `db/schema.sql`, `db/models.py` and the compose mount in the same PR.
- **Persisted dependency rows.** Because of C-02, `POST /scans` stores none. Dependency findings can still be stored if a signed report bundle carrying them was ingested (the ingestion path calls `save_findings` directly). To remove them, with DB-lane approval and after exporting them: `DELETE FROM findings WHERE artifact_type = 'DEPENDENCY_MANIFEST';` — `risk_assessments` rows go with them (`ON DELETE CASCADE`, `db/schema.sql`).

### 13.3 After any rollback

1. Re-run T0 and T3; the passed count must equal the P6 number **N** (or N plus whatever other features have landed since, recorded separately).
2. Re-run T5: default scan output identical to the pre-change commit.
3. Tell the owners affected: scanner lane (Shashank) for `cli.py` / `__init__.py`; DB lane (Ronak) for anything touching migration 003, `schema.sql`, `models.py`, `crud.py`; backend lane (Shreyanshi) for `api/models.py`; CNT / BIN / IAC owners if the shared migration or `db/models.py` tuples were touched.
4. Note in the PR which §11 provisional defaults, if any, caused the rollback.

### 13.4 Do not

- Do not edit `api/services/scan_runner.py`, `scanner/finding.py` or `api/services/risk_engine.py` to "make the rollback work" (FROZEN).
- Do not set `confidence = "high"` to work around a missing persisted row (§11 A2).
- Do not rename or renumber `003_artifact_scanning.sql` or its `04_` mount.
- Do not delete other features' statements from the shared migration, or their columns from the ORM.
- Do not force-push, and do not commit to `main`.
