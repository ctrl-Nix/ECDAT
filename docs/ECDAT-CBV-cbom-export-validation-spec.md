# ECDAT · CBV · cbom-export-validation — Feature Specification

2026-09-20

## 1. Header

This spec is **BLOCKED (partial)**: the validator and its unit tests can be built now, but wiring it into the export endpoint must wait for a human answer on contract item C-14, which the contract lists as undecided.

| Field | Value |
| --- | --- |
| Feature name | `cbom-export-validation` (feature code `CBV`) |
| Owner | Not assigned in the contract. `ARCHITECTURE.md` §5 assigns the CBOM & Quantum Risk Engine area to Maitreyi (secondary: Shashank). A human must confirm whether CBV sits in that lane. |
| Spec version | v0.1, 2026-09-20 |
| Status | Phase A (validator + unit tests): ready. Phase B (router wiring + failure contract): blocked on C-14 sign-off. |
| Step 1 source | `cbom-export-validation.md` |

Contract merge-order position, quoted verbatim from `SYSTEM_INTERFACE_CONTRACT.md` §6:

```text
| **0** | Pin `cryptography` in `requirements.txt`; delete `dashboard/src/api.js`; reserve migration numbers | Everything (C-18, C-08, C-01) |
| **1** | RBAC (`Principal` contract, `users`, `require_role`) | ENR, AUD, ASP, INS, all analyst routes (C-09) |
| **1** | `cbom_generator` refactor to `build_cbom_from_findings` | CLI, CBV, CNT, BIN, IAC (C-14) |
| **2** | AUD | — |
| **3** | CBV · ASP · INS | — |
```

### Changelog

| Version | Date | Change |
| --- | --- | --- |
| v0.1 | 2026-09-20 | First full spec. Deviations from the Step 1 proposal are listed below; each follows the contract. |

Deviations from Step 1 (the contract wins):

1. Step 1 lists `api/services/cbom_generator.py` "only if normalization is needed". CBV does **not** modify it: the contract makes it COORDINATED under the CBOM lane, with one refactor landing before any consumer (C-14).
2. Step 1 lists `requirements.txt` "only if a dedicated schema-validation library is selected". CBV never touches it: C-18 fixes Pydantic v2 and rules out a JSON-schema library.
3. Step 1 extends `tests/test_api.py`. CBV does not: the contract's ownership map does not list that file. Endpoint tests live in the new `tests/test_cbom_validation.py`.
4. Step 1 assumes a validation failure returns HTTP 500. That is the open C-14 question, so it is not adopted. The contract's §7 says "Nothing below is decided."
5. Step 1 says to reject "unsupported values" and to validate against CycloneDX. Enum-level checks on `primitive`, `cryptoFunctions` and `algorithmProperties` keys are excluded from v0.1 because the full-schema-or-subset half of C-14 is also open (§11 A-02).

### Reviewer sign-off

| Role | Name | Status |
| --- | --- | --- |
| Feature owner | not assigned | pending |
| CBOM lane: owns `cbom_generator.py` and `risk_engine.py` | Maitreyi | pending |
| Backend lane: integration owner for `api/routers/cbom.py` | Shreyanshi | pending |
| Human decision on C-14 (both halves, §11 A-01 and A-02) | not named in the contract | pending; blocks Phase B |

## 2. Goal & Context

PS 26164 requirement 3 ("Cataloguing (CBOM)" in the README's requirement table) asks for a standardized CycloneDX 1.6 CBOM, and minute 4 of the demo script in `PRODUCT_DESCRIPTION.md` §6 puts that export in front of judges, so every document leaving `GET /scans/{scan_id}/cbom` must be checked before it is served: CBV adds one deterministic, side-effect-free validator (`api/services/cbom_validator.py`) that rejects structurally broken or internally inconsistent exports (missing `evidence`, duplicate `bom-ref`, an `x-ecdat-risk-summary` whose counts disagree with the components), and, per contract C-14, it is the single code path that validates both API and CLI output so the pitch claim that the two "provably match" is testable. Its scope is deliberately narrower than "CycloneDX schema-valid": the current generator's output fails the official `bom-1.6.schema.json` in nine places (§11 A-02), so CBV must never be described as proving schema conformance, in line with `AGENT_RULES.md` #6 and the honesty rules in `PRODUCT_DESCRIPTION.md` §5.

## 3. Scope

CBV validates the dict that the CBOM generator returns and nothing else; it neither changes what is generated nor decides what the endpoint does when validation fails.

### In scope

- New module `api/services/cbom_validator.py` exposing `validate_cbom(cbom) -> CbomValidationResult`. Invalid documents produce issues, never exceptions.
- Structural checks via Pydantic v2 models that tolerate extension fields: required document fields, `cryptographic-asset` components, `cryptoProperties`, `evidence.occurrences`, well-formed `properties`.
- ECDAT invariants: unique `bom-ref`; exactly one `ecdat:risk_tier` per component, valued from `db.models.RISK_TIERS` plus `UNSCORED`; `ecdat:criticality` valued from `db.models.CRITICALITIES` when present; `x-ecdat-risk-summary` counts equal to the component counts (counting only, no re-scoring); strict JSON-serialisability.
- Issue messages built from fixed text, property names and JSON-pointer paths only; never from document values (file paths, descriptions).
- Phase B (blocked): call `validate_cbom` inside `get_cbom` between generation and serialization.
- New tests in `tests/test_cbom_validation.py`.

### Out of scope

- Enforcing the full official CycloneDX 1.6 JSON Schema, or enum-checking `primitive`, `cryptoFunctions` and `algorithmProperties` keys (C-14, open).
- The endpoint's failure contract: HTTP status, body shape and warning transport (C-14, open).
- Any edit to `api/services/cbom_generator.py`, including fixing its non-spec output values.
- Risk scoring or recomputation (C-04: `risk_engine.py` is the sole authority).
- Persisting exports or validation results: the contract (§2.3) rejects a `cbom_exports` table. No SQL, no migration, no `db/schema.sql` change.
- New routes, environment variables, CLI flags or response headers.
- CLI wiring: `scanner/ecdat_cli.py` is SOLE to the CLI feature and will call `validate_cbom`.
- Audit events (AUD), authentication (RBAC), dashboard changes, and pitch or scope documents (C-19).
- Validating the `ecdat:*` key registry or the confidence vocabulary (C-03 is open).
- Deep validation of certificate or related-crypto-material properties (CNT, BIN, IAC own those shapes).

## 4. Required Context Files

Read these in order before writing code (`AGENT_RULES.md` #1). Every repo path below was confirmed in the supplied `ECDAT-main.zip`.

| # | Path | Read it for |
| --- | --- | --- |
| 1 | `AGENT_RULES.md` | The nine binding rules; #2 (ownership), #3 (literal interfaces), #4 (stop, don't guess), #9 (no faked prerequisites) |
| 2 | `api/routers/cbom.py` | The endpoint being wrapped: 404 and 400 branches, `json.dumps(cbom, indent=2, default=str)`, `Content-Disposition` handling |
| 3 | `api/services/cbom_generator.py` | What the validator receives: `generate_cbom`, `_finding_to_component`, `_PRIMITIVE_MAP`, `_CRYPTO_FUNCTIONS_MAP`, the `x-ecdat-*` fields |
| 4 | `api/models.py` | `RiskSummary`, which the validator reuses for `x-ecdat-risk-summary` |
| 5 | `db/models.py` | `RISK_TIERS`, `CRITICALITIES`, `SCAN_STATUSES` and the ORM tables |
| 6 | `db/__init__.py` | It imports `crud`, so importing `db.models` also loads `crud` and `risk_engine` (see §11 A-13) |
| 7 | `db/crud.py` | `get_scan`, `get_findings_for_scan`, `get_risk_summary`, `get_risk_assessments_for_scan`, `save_findings` (fixtures) |
| 8 | `db/schema.sql` | Confirms CBV needs no schema change |
| 9 | `api/services/risk_engine.py` | FROZEN. Read only `score_findings` (used to build test fixtures). Do not import scoring rules |
| 10 | `api/database.py` | `get_session` dependency and the in-memory SQLite behaviour tests rely on |
| 11 | `api/core/security.py`, `api/core/config.py` | `get_api_key` and `settings.API_KEY` for endpoint tests |
| 12 | `api/main.py` | Router mounting and the response-header middleware. No change expected |
| 13 | `conftest.py` | Forces `DATABASE_URL=sqlite:///:memory:` and `API_KEY=ci-test-key` before app import |
| 14 | `tests/test_crud.py`, `tests/test_api.py`, `tests/test_security_controls.py` | Existing fixture and `monkeypatch` patterns to imitate |
| 15 | `requirements.txt`, `Dockerfile`, `.github/workflows/ecdat-scan.yml` | Version floors and the exact CI test command |
| 16 | `ARCHITECTURE.md` (§2.3, §4, §5), `PRODUCT_DESCRIPTION.md` (§5, §6), `docs/RISK_ENGINE_SPEC.md` | Endpoint table, security posture, honesty rules; read only, do not edit |

Attached to the task but not located in the repo by the contract: `SYSTEM_INTERFACE_CONTRACT.md` and `cbom-export-validation.md` (the Step 1 proposal). Do not assume a repo path for either.

Two things a reader will look for and not find:

- `skills/cbom-quantum-risk/SKILL.md` is named in `api/services/cbom_generator.py`, `db/schema.sql` and `ARCHITECTURE.md`, but the `skills/` directory is absent from the supplied archive. It is not a required file. If it is also absent in your checkout, say so (`AGENT_RULES.md` #9).
- `build_cbom_from_findings` (the Wave 1 refactor, contract C-14) does not exist in the analysed snapshot; only `generate_cbom(session, scan_id)` does. CBV must not create or stub it.

## 5. File Ownership

CBV creates two files and edits one; every other file in the repo is off limits under `AGENT_RULES.md` #2.

### Files this feature creates or modifies

| File | Action | Tier and owner |
| --- | --- | --- |
| `api/services/cbom_validator.py` | create | SOLE, CBV |
| `api/routers/cbom.py` | modify, additive only, Phase B | COORDINATED, backend lane (Shreyanshi) |
| `tests/test_cbom_validation.py` | create | The contract assigns no tier: §1.5 lists only four test files plus `test_scan_runner.py`. No other feature claims this path, so CBV treats it as SOLE and says so in the PR (§11 A-15) |

Contract rows, quoted verbatim from §1:

```text
| `api/services/cbom_validator.py` | SOLE | CBV | new |
| `api/routers/scans.py`, `cbom.py`, `remediation.py`, `report_sync.py` | COORDINATED | backend lane | RBAC swaps the auth dependency; AUD adds event calls; CNT changes `ScanCreateRequest` |
| **`api/services/cbom_generator.py`** | **COORDINATED** | **CBOM lane (Maitreyi)** | 6 features need it; one refactor — see C-14 |
```

Edits to `api/routers/cbom.py` go through the backend lane in the §6 merge order: after RBAC (Wave 1) and AUD (Wave 2). Leave their lines exactly as merged.

### Read-only dependencies (import, never edit)

| File | Tier | What CBV imports |
| --- | --- | --- |
| `api/models.py` | COORDINATED, backend lane | `RiskSummary` |
| `db/models.py` | COORDINATED, DB lane (Ronak) | `RISK_TIERS`, `CRITICALITIES` |
| `api/services/cbom_generator.py` | COORDINATED, CBOM lane (Maitreyi) | `generate_cbom` in tests only |
| `api/services/risk_engine.py` | FROZEN, CBOM/risk lane | `score_findings` in tests only |

### Do not touch

- **FROZEN:** `scanner/finding.py`, `api/services/scan_runner.py`, `api/services/risk_engine.py`.
- **SOLE, other features (scanner lane):** `scanner/dependency_engine.py`, `scanner/dependency_rules/`, `scanner/container_engine.py`, `scanner/image_layers.py`, `scanner/binary_engine.py`, `scanner/config_engine.py`, `scanner/confidence.py`, `scanner/enroll_cli.py`, `scanner/ecdat_cli.py`, `pyproject.toml`, `scanner/rules/container.yaml`, `scanner/rules/binary.yaml`, `scanner/rules/config.yaml`.
- **SOLE, other features (API lane):** `api/routers/auth.py`, `api/core/rbac.py`, `api/routers/agents.py`, `api/services/enrollment.py`, `api/routers/audit.py`, `api/services/audit.py`, `api/routers/triage.py`, `api/routers/trends.py`, `api/routers/compliance.py`.
- **SOLE, database:** every `db/migrations/002_*.sql` to `008_*.sql`. CBV owns none of them.
- **SOLE, dashboard:** `dashboard/src/index.css`, `dashboard/tailwind.config.js`, `dashboard/public/fonts/`, `dashboard/src/components/ConfidenceStamp.jsx`, `AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `pages/AgentStatusPage/`, `hooks/useAgents.js`, `ComplianceReport.jsx`, `RiskTrendChart.jsx`, `RiskTierBreakdown.jsx`, `pages/TrendsPage/`, `context/AuthContext.jsx`, `pages/LoginPage/LoginForm.jsx`, `pages/LandingPage/index.jsx`.
- **SOLE, ops and docs:** `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml`, `docs/*_SCANNING_SCOPE.md`, `docs/CONFIDENCE_MODEL_SPEC.md`, `docs/COMPLIANCE_REPORT_SCOPE.md`.
- **COORDINATED, not CBV's to edit:** `api/services/cbom_generator.py`, `api/models.py`, `api/routers/findings.py`, `api/routers/scans.py`, `api/routers/remediation.py`, `api/routers/report_sync.py`, `api/core/security.py`, `api/core/config.py`, `api/main.py`, `db/schema.sql`, `db/models.py`, `db/crud.py`, `db/seed.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `deploy/nginx/nginx.conf`, `.github/workflows/ecdat-scan.yml`, `.env.example`, `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md`, `docs/ECDAT_CLI_GUIDE.md`, all remaining `scanner/*` and `dashboard/*` files, and the existing tests in `tests/`, including `tests/test_api.py`.

## 6. Tech Stack & Pinned Versions

CBV adds no dependency and changes no line of `requirements.txt`. Nothing there is exact-pinned except `tree-sitter==0.21.3` and `tree-sitter-languages==1.10.2`, which CBV does not touch; everything else is a floor, quoted verbatim below.

| Component | Existing line (verbatim) | What CBV uses | CBV change |
| --- | --- | --- | --- |
| Python | `FROM python:3.11-slim` (`Dockerfile`) | stdlib `json`, `uuid`, `datetime`, `typing` | none |
| Pydantic | `pydantic>=2.7.0` | `BaseModel`, `ConfigDict`, `Field`, `ValidationError`, `field_validator`, `model_validator` | none |
| FastAPI | `fastapi>=0.111.0` | existing router, `TestClient` | none |
| SQLAlchemy | `SQLAlchemy>=2.0,<2.1` | tests only | none |
| pydantic-settings | `pydantic-settings>=2.3.0` | `settings.API_KEY` in tests | none |
| httpx | `httpx>=0.27.0` | required by `TestClient` | none |
| pytest | `pytest>=8.0` | tests | none |
| `cryptography` | not in `requirements.txt` | not used | none. Wave 0 pins it (C-18) |
| JSON-schema library | not present | forbidden: C-18 says CBV uses Pydantic v2 "rather than adding a JSON-schema library" | none |

Verification performed while writing this spec (Python 3.12.3, because CI's 3.11 image was not available):

- The full 31-test file (28 Phase A + 3 Phase B) passes on the floor versions pydantic 2.7.0 (pydantic-core 2.18.1), fastapi 0.111.0 (starlette 0.37.2), SQLAlchemy 2.0.30, pydantic-settings 2.3.0, httpx 0.27.0, pytest 8.0.0, and on pydantic 2.13.5, fastapi 0.141.1, SQLAlchemy 2.0.54, pytest 9.1.1.
- The literal floor `SQLAlchemy 2.0.0` would not build on Python 3.12, so it was not tested. CI runs 3.11.
- In a clean venv without `cryptography`, `import api.main` fails with `ModuleNotFoundError`. This is the live defect C-18 assigns to Wave 0; CBV's tests import `api.main`, so Wave 0 must land first.

## 7. Concrete Interface Definitions

### 7.1 SQL

```sql
-- db/migrations/: none. CBV owns no migration number (002-008 are allocated in contract §2.1).
-- db/schema.sql: no change. Contract §2.3 rejects a `cbom_exports` table.
-- docker-compose.yml initdb mounts: no change.
```

### 7.2 `api/services/cbom_validator.py` (new, SOLE)

```python
from __future__ import annotations

import datetime as dt
import json
import uuid
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from api.models import RiskSummary
from db.models import CRITICALITIES, RISK_TIERS

CBOM_VALIDATION_SCOPE: str = "ecdat-structural-invariants"
EXPECTED_BOM_FORMAT: str = "CycloneDX"
EXPECTED_SPEC_VERSION: str = "1.6"
CRYPTO_ASSET_TYPES: tuple[str, ...] = (
    "algorithm",
    "certificate",
    "protocol",
    "related-crypto-material",
)
UNSCORED_TIER: str = "UNSCORED"
RISK_TIER_PROPERTY: str = "ecdat:risk_tier"
CRITICALITY_PROPERTY: str = "ecdat:criticality"

CBOM_ISSUE_CODES: frozenset[str] = frozenset(
    {
        "DOCUMENT_NOT_OBJECT",
        "NOT_JSON_SERIALIZABLE",
        "FIELD_MISSING",
        "FIELD_WRONG_TYPE",
        "FIELD_INVALID_VALUE",
        "BOM_REF_DUPLICATE",
        "SUMMARY_TOTAL_MISMATCH",
        "SUMMARY_TIER_MISMATCH",
        "RISK_TIER_PROPERTY_MISSING",
        "RISK_TIER_PROPERTY_INVALID",
        "CRITICALITY_PROPERTY_INVALID",
    }
)


class CbomIssue(BaseModel):
    code: str
    path: str
    message: str


class CbomValidationResult(BaseModel):
    valid: bool
    scope: str = CBOM_VALIDATION_SCOPE
    issues: list[CbomIssue] = Field(default_factory=list)


_EXT = ConfigDict(extra="allow")


class _Property(BaseModel):
    model_config = _EXT
    name: str = Field(min_length=1)
    value: str


class _Occurrence(BaseModel):
    model_config = _EXT
    location: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=0, strict=True)


class _Evidence(BaseModel):
    model_config = _EXT
    occurrences: list[_Occurrence] = Field(min_length=1)


class _CryptoProperties(BaseModel):
    model_config = _EXT
    assetType: Literal["algorithm", "certificate", "protocol", "related-crypto-material"]
    algorithmProperties: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _algorithm_requires_properties(self) -> "_CryptoProperties": ...


class _Component(BaseModel):
    model_config = _EXT
    type: Literal["cryptographic-asset"]
    bom_ref: str = Field(alias="bom-ref", min_length=1)
    name: str = Field(min_length=1)
    cryptoProperties: _CryptoProperties
    evidence: _Evidence
    properties: list[_Property]


class _MetadataComponent(BaseModel):
    model_config = _EXT
    type: str = Field(min_length=1)
    name: str = Field(min_length=1)


class _Metadata(BaseModel):
    model_config = _EXT
    timestamp: str
    tools: list[Any] | dict[str, Any]
    component: _MetadataComponent | None = None

    @field_validator("timestamp")
    @classmethod
    def _iso8601(cls, v: str) -> str: ...


class _Document(BaseModel):
    model_config = _EXT
    bomFormat: Literal["CycloneDX"]
    specVersion: Literal["1.6"]
    serialNumber: str
    version: int = Field(ge=1, strict=True)
    metadata: _Metadata
    components: list[_Component]
    externalReferences: list[Any] | None = None
    x_ecdat_risk_summary: RiskSummary | None = Field(default=None, alias="x-ecdat-risk-summary")
    x_ecdat_report_provenance: dict[str, Any] | None = Field(
        default=None, alias="x-ecdat-report-provenance"
    )

    @field_validator("serialNumber")
    @classmethod
    def _urn_uuid(cls, v: str) -> str: ...


def _path(loc: tuple[Any, ...]) -> str: ...
def _classify(err_type: str) -> str: ...
def _prop(component: _Component, name: str) -> list[str]: ...
def _finish(issues: list[CbomIssue]) -> CbomValidationResult: ...


def validate_cbom(cbom: dict[str, Any]) -> CbomValidationResult: ...
```

### 7.3 `api/routers/cbom.py` (modify, additive, Phase B)

```python
# NEW import, placed directly after the existing cbom_generator import:
from api.services.cbom_validator import validate_cbom

# Inside get_cbom(), signature and existing 404/400 branches unchanged.
# Existing lines, untouched:
#     cbom = generate_cbom(db, scan_id)
#     if cbom is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scan {scan_id} not found.")
# NEW, inserted here:
    validation = validate_cbom(cbom)
    if not validation.valid:
        ...  # GATED on C-14 sign-off. No body specified. See §11 A-01.
# Existing line, untouched:
#     cbom_json = json.dumps(cbom, indent=2, default=str)
```

### 7.4 Literal example JSON

#### 7.4a `GET /scans/1/cbom` → 200, `Content-Type: application/vnd.cyclonedx+json` (shape unchanged; generated by the current `generate_cbom`)

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.6",
  "serialNumber": "urn:uuid:3e671687-395b-41f5-a30f-a58921a69b79",
  "version": 1,
  "metadata": {
    "timestamp": "2026-09-20T09:15:02",
    "tools": [
      {
        "vendor": "ECDAT",
        "name": "ECDAT — Enterprise Cryptographic Discovery & Assessment Tool",
        "version": "1.0.0"
      }
    ],
    "component": { "type": "application", "name": "scan-1", "version": "1" }
  },
  "components": [
    {
      "type": "cryptographic-asset",
      "bom-ref": "finding-1",
      "name": "MD5",
      "version": "MD5",
      "description": "MD5 detected at services/legacy_hash.py:14 (confidence=high)",
      "cryptoProperties": {
        "assetType": "algorithm",
        "algorithmProperties": {
          "primitive": "hash",
          "implementationLevel": "softwarePlainRam",
          "cryptoFunctions": ["digest"]
        }
      },
      "evidence": {
        "occurrences": [
          {
            "location": "services/legacy_hash.py",
            "line": 14,
            "additionalContext": "Detection confidence: high"
          }
        ]
      },
      "properties": [
        { "name": "ecdat:risk_tier", "value": "CRITICAL" },
        { "name": "ecdat:criticality", "value": "HIGH" },
        { "name": "ecdat:risk_reason", "value": "MD5 is classically broken — collision attacks are well-documented and computationally trivial. Immediate replacement with SHA-256 required." },
        { "name": "ecdat:source_context", "value": "SOURCE" },
        { "name": "ecdat:risk_model_version", "value": "2026.1" },
        { "name": "ecdat:classical_broken", "value": "true" },
        { "name": "ecdat:quantum_vulnerable", "value": "false" },
        { "name": "ecdat:hndl_exposure", "value": "NOT_APPLICABLE" },
        { "name": "ecdat:recommended_replacement", "value": "SHA-256 or BLAKE2" },
        { "name": "ecdat:recommendation_type", "value": "classical" },
        { "name": "ecdat:migration_effort_days", "value": "1" },
        { "name": "ecdat:data_shelf_life_years", "value": "0.0" },
        { "name": "ecdat:quantum_threat_horizon_years", "value": "12.0" }
      ]
    }
  ],
  "externalReferences": [],
  "x-ecdat-risk-summary": { "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 1, "UNSCORED": 0, "total": 1 },
  "x-ecdat-report-provenance": { "origin": "local-api", "integrity": "not-signed-bundle" }
}
```

#### 7.4b Existing error bodies (unchanged)

```json
{ "detail": "Scan 9999 not found." }
```

```json
{ "detail": "Scan 5 is still 'running'. CBOM is only available after the scan completes." }
```

#### 7.4c `validate_cbom(...).model_dump()` for 7.4a

```json
{ "valid": true, "scope": "ecdat-structural-invariants", "issues": [] }
```

#### 7.4d `validate_cbom(...).model_dump()`, structural failure (`bomFormat` changed to `"SPDX"`, first component's `evidence` deleted)

```json
{
  "valid": false,
  "scope": "ecdat-structural-invariants",
  "issues": [
    { "code": "FIELD_INVALID_VALUE", "path": "/bomFormat", "message": "Input should be 'CycloneDX'" },
    { "code": "FIELD_MISSING", "path": "/components/0/evidence", "message": "Field required" }
  ]
}
```

#### 7.4e `validate_cbom(...).model_dump()`, invariant failure (7.4a with its component appended a second time)

```json
{
  "valid": false,
  "scope": "ecdat-structural-invariants",
  "issues": [
    { "code": "BOM_REF_DUPLICATE", "path": "/components/1/bom-ref", "message": "bom-ref must be unique within the document." },
    { "code": "SUMMARY_TIER_MISMATCH", "path": "/x-ecdat-risk-summary/CRITICAL", "message": "Summary count for CRITICAL does not match component properties." },
    { "code": "SUMMARY_TOTAL_MISMATCH", "path": "/x-ecdat-risk-summary/total", "message": "Summary total does not equal the component count." }
  ]
}
```

#### 7.4f Endpoint response when `validation.valid is False`

Not defined. Contract C-14 is open. See §11 A-01.

## 8. Step-by-Step Implementation Plan

Branch and merge rules: work only on the branch a human assigns you (`AGENT_RULES.md` #8; the contract names no branch). CBV merges in Wave 3. Before Phase B, rebase onto whatever RBAC, AUD and the `cbom_generator` refactor have landed.

### Phase A (unblocked; may be built now)

1. **`api/services/cbom_validator.py`.** Create the module with the imports, constants, `CBOM_ISSUE_CODES`, `CbomIssue` and `CbomValidationResult` exactly as in §7.2. Do not import `re`, `jsonschema`, `fastapi`, `api.services.cbom_generator` or `api.services.risk_engine`.
2. **`api/services/cbom_validator.py`.** Add the private models exactly as in §7.2 and implement their three validators:
   - `_CryptoProperties._algorithm_requires_properties`: when `assetType == "algorithm"` and `algorithmProperties is None`, raise `ValueError` with fixed text; return `self` otherwise.
   - `_Metadata._iso8601`: call `dt.datetime.fromisoformat(v)`; let its `ValueError` propagate; return `v`.
   - `_Document._urn_uuid`: require the prefix `urn:uuid:`; parse the tail with `uuid.UUID(tail)`; require `str(parsed) == tail` (canonical lower-case); raise `ValueError` with fixed text otherwise. No regex.
3. **`api/services/cbom_validator.py`.** Implement the helpers and `validate_cbom`, in this order:
   1. Non-`dict` input: return one issue, code `DOCUMENT_NOT_OBJECT`, path `""`.
   2. `json.dumps(cbom, allow_nan=False)`; on `TypeError`, `ValueError` or `RecursionError` add `NOT_JSON_SERIALIZABLE` at path `""` and continue.
   3. `_Document.model_validate(cbom)`. On `ValidationError`, add one issue per error and return without step 4. Code: `FIELD_MISSING` if the Pydantic error type is `missing`; `FIELD_WRONG_TYPE` if it ends in `_type` or `_parsing` or equals `model_type`; otherwise `FIELD_INVALID_VALUE`. Path: `"/" + "/".join(str(p) for p in loc)`, or `""` for an empty `loc`. Message: the Pydantic `msg` only; never the error's `input` and never `str(ValidationError)`.
   4. Cross-checks on the validated model:
      - `BOM_REF_DUPLICATE` at `/components/{i}/bom-ref`, once per duplicated ref, at the index of its second occurrence.
      - Per component, exactly one `ecdat:risk_tier` property, otherwise `RISK_TIER_PROPERTY_MISSING` at `/components/{i}/properties`; its value must be in `RISK_TIERS` plus `UNSCORED`, otherwise `RISK_TIER_PROPERTY_INVALID` at the same path.
      - Each `ecdat:criticality` property value must be in `CRITICALITIES`, otherwise `CRITICALITY_PROPERTY_INVALID` at the same path.
      - If `x-ecdat-risk-summary` is present: `total` must equal the component count (`SUMMARY_TOTAL_MISMATCH`, path `/x-ecdat-risk-summary/total`), and for each of `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `UNSCORED` the summary count must equal the number of components carrying that tier (`SUMMARY_TIER_MISMATCH`, path `/x-ecdat-risk-summary/{TIER}`). Count only; never score.
   5. `_finish`: sort issues by `(path, code, message)`; `valid` is `True` iff there are no issues.
   Messages in step 4 are fixed text plus property or tier names; never document values.
4. **`tests/test_cbom_validation.py`.** Create the file with the fixtures and the 28 Phase A tests listed in §12.

### Phase B (blocked until a human records the C-14 answer)

5. **`api/routers/cbom.py`.** Add the import and the `validate_cbom` call exactly as in §7.3. Write the failure branch only after the C-14 answer is recorded in the contract and this spec is revised to v0.2 with that branch in §7. Touch no other line, including the auth dependency and any AUD call.
6. **`tests/test_cbom_validation.py`.** Add the 3 endpoint tests listed in §12, plus the failure-contract tests that v0.2 defines.

## 9. Naming & Symbol Registry

Checked against contract §3 (naming conventions) and §5 (Shared Resource Index). A repo-wide search found no existing use of any name below.

| Kind | Symbol | Location | Convention check |
| --- | --- | --- | --- |
| Module | `api.services.cbom_validator` | `api/services/cbom_validator.py` | Path assigned by contract §1.2 |
| Function | `validate_cbom` | same | §3.1: `snake_case`, disambiguated by module path, no `ecdat_` prefix |
| Classes | `CbomIssue`, `CbomValidationResult` | same | §3.1: `PascalCase` |
| Constants | `CBOM_VALIDATION_SCOPE`, `EXPECTED_BOM_FORMAT`, `EXPECTED_SPEC_VERSION`, `CRYPTO_ASSET_TYPES`, `UNSCORED_TIER`, `RISK_TIER_PROPERTY`, `CRITICALITY_PROPERTY`, `CBOM_ISSUE_CODES` | same | §3.1: `UPPER_SNAKE_CASE`. Deliberately not `CYCLONEDX_FORMAT`, `CYCLONEDX_SPEC_VERSION` or `CBOM_BOM_FORMAT`, which already exist in `cbom_generator.py` (the last one holds a media type despite its name) |
| Issue codes (11) | the strings in `CBOM_ISSUE_CODES` | same | Not audit actions (§3.6) and not `detection_method` values (§3.2) |
| Private | `_EXT`, `_Property`, `_Occurrence`, `_Evidence`, `_CryptoProperties`, `_Component`, `_MetadataComponent`, `_Metadata`, `_Document`, `_path`, `_classify`, `_prop`, `_finish` | same | Module-private; not importable across lanes (§3.1) |
| Test module and fixtures | `tests/test_cbom_validation.py`; fixtures `engine`, `real_cbom`, `client` | tests | Matches existing `tests/test_*.py` |
| DB tables and columns | none | none | §2.3 rejects `cbom_exports` |
| Environment variables | none | none | None of the §3.3 reserved prefixes (`AUTH_`, `AGENT_ENROLLMENT_`, `SCAN_`, `AUDIT_`, `VITE_`) fits CBV, and none is needed |
| CLI flags | none | none | The CLI feature owns `ecdat cbom` and calls `validate_cbom` |
| HTTP routes and headers | none new | none | `GET /scans/{scan_id}/cbom` is unchanged; the contract defines no response-header convention |
| `ecdat:*` property keys | none new | none | Reads `ecdat:risk_tier` and `ecdat:criticality`; the registry is the CBOM lane's (C-14) |

Shared Resource Index (§5) rows touched: `api/services/cbom_generator.py` (read-only), `api/routers/cbom.py` (edit; "Compatible", C-14), `api/models.py` (read-only import), `requirements.txt` (untouched), `GET /scans/{scan_id}/cbom` ("Compatible", C-14).

## 10. Known Cross-Feature Risks

Each item below names CBV in the contract. The resolution shown is the one already decided there.

| Contract item | Decided resolution | Consequence for CBV |
| --- | --- | --- |
| C-14 (`cbom_generator.py` pulled six ways) | "One refactor, owned by the CBOM lane, before any consumer merges: extract a pure `build_cbom_from_findings(findings: list[dict], summary: dict) -> dict`, and make the existing ORM-based `generate_cbom` a thin wrapper over it. CBV validates the returned dict, so CLI and API output are validated by the same code path." | `validate_cbom` takes the dict and imports no generator code. Tests use `generate_cbom(session, scan_id)`. |
| C-14, extension keys | "All ECDAT extensions use a single registry of `ecdat:*` property keys — `ecdat:confidence_band`, `ecdat:confidence_score`, `ecdat:detection_method`, `ecdat:artifact_type` — never free-text `additionalContext`." | CBV must not require or forbid `additionalContext`, and must tolerate any `ecdat:*` key. |
| C-18 (`requirements.txt`) | "CBV uses Pydantic v2, already present, rather than adding a JSON-schema library." | No new dependency; `requirements.txt` untouched. |
| §5.1 and §5.3, `api/routers/cbom.py` and `GET /scans/{scan_id}/cbom` (CBV, RBAC, AUD) | "Compatible" (C-14). RBAC swaps the auth dependency; AUD adds event calls (`ecdat.cbom.export`, §3.6). Merge order RBAC, then AUD, then CBV. | CBV's router edit is additive and leaves both features' lines alone. |
| §2.3 (rejected schema proposals) | A `cbom_exports` table is rejected because "Persisting exports creates a second source of truth CBV exists to prevent." | CBV persists nothing and adds no SQL. |
| C-04 (`risk_engine.py`) | `risk_engine.py` is the sole scoring authority. | CBV only counts persisted tiers; it never scores. |
| C-19 (scope documents) | Scope-truth documents are edited once, by a single scope editor. | CBV does not touch `PRODUCT_DESCRIPTION.md`, `README.md` or `ARCHITECTURE.md`, even to correct the CBOM claims noted in §11 A-02. |

## 11. Pre-Answered Ambiguities

**Contract gap, stated up front.** The task asked that open sign-off items be answered with "the team's resolved answer". The contract supplied says of its §7 list: "Nothing below is decided." C-14, the only open item that blocks CBV, has no resolved answer, so none is invented here. A-01 and A-02 are the two halves of it. Step 1's four open questions map as: full schema or subset → A-02; `x-ecdat-*` strictness → A-04; empty scan → A-03; HTTP 500 → A-01.

### A-01 (C-14, first half): failure contract

**If** `validate_cbom` returns `valid=False` and you must decide what `get_cbom` does (500, or 200 with a warning): **do** nothing in Phase B beyond §7.3. Do not write the failure branch, do not log-and-serve as an interim, and ask a human (`AGENT_RULES.md` #4). The contract requires that Medium items "must not be implemented until a human signs off". The sign-off must state:

1. the HTTP status;
2. if 200, how the warning travels (the contract defines no response-header convention, and a CycloneDX body cannot take extra top-level fields if the full schema is chosen);
3. the response body shape;
4. the audit `outcome` value for a failed validation (AUD's are `allowed | denied | error`).

Phase A ships dormant and changes no runtime behaviour.

### A-02 (C-14, second half): full CycloneDX 1.6 schema or the cryptographic-asset subset

**If** you are tempted to add `primitive` or `cryptoFunctions` enum checks, `additionalProperties` strictness, or a vendored schema file: **do not**. The answer is undecided. Implement only the checks in §8 step 3, which hold under either answer. Never call the result "schema-valid"; `CbomValidationResult.scope` says `ecdat-structural-invariants` for that reason.

Evidence for whoever decides, verified on 2026-09-20 by validating real `generate_cbom` output for four findings (MD5, RSA-1024, 3DES, ECC) against the official `bom-1.6.schema.json` (fetched from the CycloneDX specification repository, master branch): **9 errors**.

| Where | Generator emits | Official 1.6 schema |
| --- | --- | --- |
| Top level | `x-ecdat-risk-summary`, `x-ecdat-report-provenance` | top level has `additionalProperties: false` |
| `algorithmProperties` | `implementationLevel`, and `keySize` when a key size exists | `additionalProperties: false`; neither key exists |
| `primitive` | `blockCipher`, `publicKeyEncryption` (also `streamCipher` in `_PRIMITIVE_MAP`) | enum uses `block-cipher`, `pke`, `stream-cipher` |
| `cryptoFunctions` | `keyGenerate`, `keyDerive` (also `mac` and `auth` in `_CRYPTO_FUNCTIONS_MAP`) | enum has `keygen`, `keyderive`, `tag`; no `mac` or `auth` |

The `streamCipher`, `mac` and `auth` rows come from reading the generator maps against the schema enums; the sample did not exercise them. Consequences the decision must weigh, stated without recommending:

- A full-schema answer means the generator's output must change first. `cbom_generator.py` is COORDINATED under the CBOM lane, so CBV cannot do it.
- With a 500-on-failure answer, a full-schema check would fail every export containing those algorithms.
- C-18 excludes a JSON-schema library, so a full-schema answer must also say how it is implemented with Pydantic alone, or reopen C-18.
- `docs/RISK_ENGINE_SPEC.md` (§6, "Pitch-Ready Talking Points") says "Our CBOM uses the real CycloneDX 1.6 cryptographic-asset specification". The output above does not currently validate against the official schema. That is a scope-truth edit for the single scope editor (C-19), not for CBV.

### Other pre-answered situations

- **A-03. Empty scan.** *If* a completed scan has zero findings, *do* treat `components: []` as valid. The contract is silent; this preserves today's behaviour (`generate_cbom` returns an empty list and the endpoint serves 200) and matches the official schema, which sets no minimum on `components`. `test_empty_scan_export_is_valid` encodes it. A human may overrule.
- **A-04. `x-ecdat-*` fields.** *If* a document has `x-ecdat-risk-summary` or `x-ecdat-report-provenance`, *do* accept them, check only the count consistency of the summary, do not require them, and do not reject unknown top-level keys. The contract is silent on strictness. Under a full-schema answer to A-02 these fields become illegal, so A-02 and A-04 must be answered together.
- **A-05. Post-refactor `ecdat:*` properties.** *If* the generator (after Wave 1) drops `additionalContext` and adds `ecdat:confidence_band`, `ecdat:confidence_score`, `ecdat:detection_method` or `ecdat:artifact_type`, *do* nothing: they are extension properties and pass. Do not validate their values; C-03's vocabulary questions (backfill, `--fail-on`) are open.
- **A-06. `build_cbom_from_findings` not present.** *If* it is still absent when you start, *do* say so and do not stub it (`AGENT_RULES.md` #9). Tests use `generate_cbom(session, scan_id)`, which the contract keeps as a thin wrapper. If that signature has changed, stop and flag a human.
- **A-07. Auth after RBAC.** *If* RBAC has merged and `X-API-Key` no longer authenticates `GET /scans/{scan_id}/cbom` (C-09: "does `X-API-Key` survive?" is open), *do* stop and ask. The contract publishes no RBAC test helper. Do not edit the auth dependency. Today's tests send `X-API-Key: ci-test-key`.
- **A-08. AUD call placement.** *If* AUD's `ecdat.cbom.export` call already sits in `get_cbom`, *do* leave it where it is and insert validation between generation and serialization. Do not move it. What outcome it records on a failed validation is part of A-01.
- **A-09. Missing or zero `line`.** *If* an occurrence has no `line`, or `line: 0` (binary findings, C-13 and C-14), *do* accept both. `location` stays required and non-empty. Negative or non-integer `line` is invalid.
- **A-10. Other asset types.** *If* CNT or BIN adds `certificate` or `related-crypto-material` components, *do* accept any of the four `assetType` values, require `algorithmProperties` only for `algorithm`, and do not deep-validate certificate properties.
- **A-11. Messages and test assertions.** *If* you want to put a document value in an issue message, *do not*: messages hold fixed text, property names, tier names and JSON-pointer paths only (findings need authentication to read, `ARCHITECTURE.md` §4). The wording of `FIELD_*` messages comes from Pydantic and can change between versions, so tests assert `(code, path)` and never message text.
- **A-12. Regex or a schema library.** *If* you reach for `re` (for `serialNumber`, say) or `jsonschema`, *do not*: parse with `uuid.UUID` (C-18; the spirit of `AGENT_RULES.md` #5).
- **A-13. Import footprint.** *If* someone objects that the validator pulls in SQLAlchemy, `db.crud`, `api.services.risk_engine` and `remediation_table`, *do* explain that `db/__init__.py` imports `crud`. FastAPI and `cbom_generator` are not imported, and no connection is opened. Do not copy the two tuples locally; C-16 wants "canonical value tuples in `db/models.py`". If the CLI lane needs a lighter import, flag it to the CBOM lane.
- **A-14. `RiskSummary` drift.** *If* `api/models.py` `RiskSummary` no longer has exactly `total`, `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `UNSCORED` at merge time, *do* stop and flag the backend lane.
- **A-15. New test file ownership.** *If* asked who owns `tests/test_cbom_validation.py`, *do* answer that the contract assigns no tier, CBV treats it as SOLE, and the PR says so.
- **A-16. Cross-checks skipped.** *If* a structurally invalid document reports no `BOM_REF_DUPLICATE` or `SUMMARY_*` issue, *do* leave it: cross-checks run only after the structure validates (§8 step 3). Re-validate after fixing the structure.

## 12. Test Plan / Definition of Done

Counts below were measured on the analysed snapshot (Python 3.12.3 sandbox with `tree-sitter==0.21.3` installed): baseline **64 passed**; with CBV Phase A **92**; with Phase A and B **95**. If other features have merged tests first, record your own baseline `B` and expect `B + 28` and `B + 31`.

### Phase A

```bash
# 0. Baseline before you start
pytest -q --disable-warnings -p no:cacheprovider 2>&1 | tail -1
# expected: 64 passed, ...           (record B if different)

# 1. CBV unit tests
pytest tests/test_cbom_validation.py -q --disable-warnings -p no:cacheprovider
# expected last line begins: 28 passed

# 2. Whole suite
pytest -q --disable-warnings -p no:cacheprovider 2>&1 | tail -1
# expected last line begins: 92 passed          (B + 28)

# 3. CI parity (from .github/workflows/ecdat-scan.yml)
docker build --tag ecdat-scanner:local .
docker run --rm -e API_KEY=ci-test-key -e REPORT_SYNC_REQUIRE_MTLS=false \
  --entrypoint python ecdat-scanner:local -m pytest -q --disable-warnings --maxfail=1
# expected last line begins: 92 passed

# 4. Issue-code registry
python -c "from api.services.cbom_validator import CBOM_ISSUE_CODES as c; print(sorted(c))"
# expected:
# ['BOM_REF_DUPLICATE', 'CRITICALITY_PROPERTY_INVALID', 'DOCUMENT_NOT_OBJECT', 'FIELD_INVALID_VALUE', 'FIELD_MISSING', 'FIELD_WRONG_TYPE', 'NOT_JSON_SERIALIZABLE', 'RISK_TIER_PROPERTY_INVALID', 'RISK_TIER_PROPERTY_MISSING', 'SUMMARY_TIER_MISMATCH', 'SUMMARY_TOTAL_MISMATCH']

# 5. No regex, no schema library, no forbidden imports
grep -nE "^\s*(import re|from re import)|\bre\.(compile|match|search|fullmatch|sub|findall)\(" api/services/cbom_validator.py; echo "exit=$?"
# expected: exit=1 and no other output
grep -nE "jsonschema|fastjsonschema|cbom_generator|import fastapi|from fastapi" api/services/cbom_validator.py requirements.txt; echo "exit=$?"
# expected: exit=1 and no other output

# 6. Ownership guard
git diff --name-only "$(git merge-base origin/main HEAD)"..HEAD | sort
# expected exactly:
# api/services/cbom_validator.py
# tests/test_cbom_validation.py
```

### Phase A tests (28, all in `tests/test_cbom_validation.py`)

Fixtures: `engine` (in-memory SQLite with `StaticPool`, `Base.metadata.create_all`); `real_cbom` (runs `score_findings` on the four raw findings below, saves them with `crud.save_findings`, returns `json.loads(json.dumps(generate_cbom(...), default=str))`).

| Raw finding | file, line | algorithm | extra |
| --- | --- | --- | --- |
| 1 | `a.py`, 3 | `MD5` | `confidence: high`, `language: python`, `primitive: hash`, `detection_method: ast_visitor` |
| 2 | `k.py`, 9 | `RSA` | `key_size: 1024`, `confidence: high`, `language: python`, `primitive: pke`, `detection_method: ast_visitor` |
| 3 | `c.java`, 5 | `3DES` | `confidence: high`, `language: java`, `detection_method: tree_sitter_query` |
| 4 | `e.js`, 2 | `ECC` | `confidence: unverified`, `language: javascript`, `detection_method: tree_sitter_query`, `source_context: TEST_ONLY` |

Every rejection test asserts the `(code, path)` pair shown.

| Test | Asserts |
| --- | --- |
| `test_generated_export_is_valid` | `valid is True`, `issues == []`, `scope == CBOM_VALIDATION_SCOPE` |
| `test_empty_scan_export_is_valid` | zero-finding scan gives `components == []` and `valid is True` |
| `test_non_object_document_rejected` (4 params: `None`, `[]`, `"cbom"`, `7`) | `{("DOCUMENT_NOT_OBJECT", "")}` |
| `test_wrong_bom_format_rejected` | `("FIELD_INVALID_VALUE", "/bomFormat")` |
| `test_wrong_spec_version_rejected` (`"1.5"`) | `("FIELD_INVALID_VALUE", "/specVersion")` |
| `test_missing_components_rejected` | `("FIELD_MISSING", "/components")` |
| `test_components_wrong_type_rejected` | `("FIELD_WRONG_TYPE", "/components")` |
| `test_component_type_must_be_cryptographic_asset` | `("FIELD_INVALID_VALUE", "/components/0/type")` |
| `test_unknown_asset_type_rejected` | `("FIELD_INVALID_VALUE", "/components/0/cryptoProperties/assetType")` |
| `test_algorithm_asset_requires_algorithm_properties` | `("FIELD_INVALID_VALUE", "/components/0/cryptoProperties")` |
| `test_empty_evidence_occurrences_rejected` | `("FIELD_INVALID_VALUE", "/components/1/evidence/occurrences")` |
| `test_line_zero_accepted_and_negative_rejected` | `line=0` valid; `line=-1` gives `("FIELD_INVALID_VALUE", "/components/0/evidence/occurrences/0/line")` |
| `test_duplicate_bom_ref_rejected` | `("BOM_REF_DUPLICATE", "/components/1/bom-ref")` |
| `test_serial_number_must_be_canonical_urn_uuid` | `"not-a-urn"` and an upper-case-hex URN both give `("FIELD_INVALID_VALUE", "/serialNumber")` |
| `test_metadata_timestamp_must_be_iso8601` | `("FIELD_INVALID_VALUE", "/metadata/timestamp")` |
| `test_missing_risk_tier_property_rejected` | `("RISK_TIER_PROPERTY_MISSING", "/components/0/properties")` |
| `test_invalid_risk_tier_property_rejected` (`"SEVERE"`) | `("RISK_TIER_PROPERTY_INVALID", "/components/0/properties")` |
| `test_invalid_criticality_property_rejected` (`"EXTREME"`) | `("CRITICALITY_PROPERTY_INVALID", "/components/0/properties")` |
| `test_summary_total_mismatch_rejected` | `("SUMMARY_TOTAL_MISMATCH", "/x-ecdat-risk-summary/total")` |
| `test_summary_tier_mismatch_rejected` | `SUMMARY_TIER_MISMATCH` at `/x-ecdat-risk-summary/CRITICAL` and `/LOW` |
| `test_ecdat_extension_fields_are_accepted` | valid with both `x-ecdat-*` fields; still valid with `x-ecdat-risk-summary` removed |
| `test_non_json_serialisable_document_rejected` | a `datetime` value and a `NaN` each give `("NOT_JSON_SERIALIZABLE", "")` |
| `test_validation_does_not_mutate_input` | input deep-equals its pre-call copy |
| `test_issue_output_is_deterministic_and_uses_known_codes` | two runs equal; issues sorted by `(path, code)`; all codes in `CBOM_ISSUE_CODES` |
| `test_issue_messages_never_echo_document_values` | a sentinel string planted in `location`, `description`, `type`, `line` and `bomFormat` never appears in `model_dump_json()` |

### Phase B (only after the C-14 answer is recorded)

```bash
pytest tests/test_cbom_validation.py -q --disable-warnings -p no:cacheprovider
# expected last line begins: 31 passed, plus any failure-contract tests added by spec v0.2
pytest -q --disable-warnings -p no:cacheprovider 2>&1 | tail -1
# expected last line begins: 95 passed          (B + 31, plus v0.2 tests)
git diff --name-only "$(git merge-base origin/main HEAD)"..HEAD | sort
# expected exactly: api/routers/cbom.py, api/services/cbom_validator.py, tests/test_cbom_validation.py
```

The three endpoint tests use a `client` fixture (`app.dependency_overrides[get_session]` bound to the shared in-memory engine, popped afterwards) and send `X-API-Key: settings.API_KEY or "ci-test-key"`:

| Test | Asserts |
| --- | --- |
| `test_endpoint_serves_validated_export_unchanged` | `?download=true` gives 200, `application/vnd.cyclonedx+json`, `Content-Disposition: attachment; filename="ecdat-scan-{id}-cbom.json"`, four components; a spy on `api.routers.cbom.validate_cbom` is called exactly once with the generated dict |
| `test_endpoint_unknown_scan_is_404_and_skips_validation` | `/scans/9999/cbom` gives 404; validator not called |
| `test_endpoint_in_progress_scan_is_400_and_skips_validation` | a `running` scan gives 400; validator not called |

### Definition of done

- Every command above prints its expected output.
- The diff touches only the files in §5's "create or modify" table.
- `requirements.txt` is unchanged.
- No test asserts Pydantic message text.
- Phase B is not started until §11 A-01 and A-02 have recorded answers.

## 13. Rollback Plan

CBV has no database, environment, dependency or infrastructure footprint, so rollback is a code revert only; nothing needs migrating back.

1. **Phase A alone** (two new files, no runtime effect): `git revert --no-edit <commit-sha>` on your feature branch, or delete `api/services/cbom_validator.py` and `tests/test_cbom_validation.py`. Nothing imports them.
2. **Phase B** (router wiring): `git revert --no-edit <router-commit-sha>`. `GET /scans/{scan_id}/cbom` returns to its pre-CBV behaviour. The validator module can stay.
3. **Merged to `main` and the build is red:** `git revert -m 1 <merge-commit-sha>`, open a PR from a feature branch (never commit to `main`, `AGENT_RULES.md` #8), and re-run the §12 baseline command.
4. **Confirm the rollback:** `pytest -q --disable-warnings -p no:cacheprovider 2>&1 | tail -1` must show the pre-CBV baseline (`64 passed` on the analysed snapshot, or your recorded `B`), and `git diff --name-only <pre-merge-sha>..HEAD -- api/routers/cbom.py api/services/cbom_validator.py tests/test_cbom_validation.py` must print nothing.
5. **If the export endpoint is failing in a demo:** revert step 2 first; it is the only change that can alter an HTTP response.
6. **Tell the owners:** notify the backend lane (Shreyanshi) if `api/routers/cbom.py` was reverted, since RBAC and AUD edits sit in the same file and the revert must not remove them.
