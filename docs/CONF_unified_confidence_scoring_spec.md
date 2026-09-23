# Unified Confidence Scoring — Implementation Spec (CONF)

## 1. Header

- **Feature name:** Unified Confidence Scoring Across Scanners
- **Feature code:** `CONF` (per `SYSTEM_INTERFACE_CONTRACT.md` §0)
- **Owner:** Ronak (DB lane) — sole engineer on CONF, coordinating scanner-lane and backend-lane edits through the named integration owners in the contract.
- **Reviewers required before merge:** scanner lane (Shashank) for `scanner/*` and `Finding` field additions; backend lane (Shreyanshi) for `api/models.py`, `api/routers/findings.py`, `api/services/scan_runner.py`; CBOM/risk lane (Maitreyi) for the CBOM property-key registration; frontend lane (Karan/Satyam) for `ConfidenceStamp.jsx` and `dashboard/src/lib/constants.js`. Human sign-off required on C-02, C-03(a/b/c) and C-04's trend interaction before any part of this spec is merged past phase 1 (see §11).
- **Spec version:** `1.0.0`
- **Status:** Draft — pending sign-off on C-02, C-03(a), C-03(b), C-03(c), C-04 (CONF interaction).
- **Merge order position (contract §6):** Wave 1, alongside RBAC and the `cbom_generator` refactor. Blocks DEP, CNT, BIN, IAC in Wave 3 via C-02 and C-03.

### 1.1 Changelog / deviations from the Step 1 proposal

| # | Step 1 said | Contract says | Applied |
|---|---|---|---|
| 1 | "confidence stays a separate axis from `risk_tier`" | C-04 confirms verbatim | Kept |
| 2 | Store signals as `TEXT[]` OR `JSONB` (open) | §2.2 mandates `JSONB` | Adopted `JSONB` |
| 3 | Migration file `db/migrations/002_confidence_scoring.sql` | §2.1 confirms; adds compose mount prefix `03_` | Compose mount added |
| 4 | Keep legacy `confidence` column as derived string | C-03 confirms: `VERIFIED → "high"`, else `"unverified"` | Adopted verbatim |
| 5 | `--min-confidence` CLI flag | §5.4 / §3.5 confirm; contract adds `SCAN_MIN_CONFIDENCE_BAND` env var, default `PROBABLE` | Adopted, default `PROBABLE` |
| 6 | "Assumption: no engine currently emits `unverified`" | Confirmed by C-03 | No deviation |
| 7 | Step 1 was silent on `detection_method` | §3.2 registry is FROZEN; current code emits forbidden `ast_static_analysis` | Rename is out of scope for CONF and is flagged for scanner lane in §11 |
| 8 | Step 1 did not name the CBOM property keys | C-14 mandates `ecdat:confidence_band`, `ecdat:confidence_score`; free-text `additionalContext` is forbidden | Adopted registry keys |
| 9 | Step 1 proposed CONF edits `api/services/cbom_generator.py` directly | C-14 requires CBOM lane refactor first, then CONF consumes | Wait-behind added to §8 |

---

## 2. Goal & Context

The scanner today does not score confidence — both `scanner/python_engine.py:198` and `scanner/multilang_engine.py:699` hardcode the literal `"high"`, and `api/services/scan_runner.py:103` filters on `finding.get("confidence") == "high"` before any finding is persisted. This means (a) `PS 26164` requirement #2 ("Identification") currently ships a confidence label that is an engine-author assertion rather than evidence about the detection, and (b) four unbuilt features (`DEP`, `CNT`, `BIN`, `IAC`) that legitimately produce sub-`"high"` findings would scan successfully and persist zero rows once merged (C-02). CONF replaces the literal with a shared, deterministic scorer in `scanner/confidence.py` that emits a numeric `confidence_score` and a band `VERIFIED | PROBABLE | UNVERIFIED` unified across all engines — which is what makes the `PRODUCT_DESCRIPTION.md` §2 claim "Every finding carries a confidence score — 'high' means we verified the import" true across languages, and what makes the "documented, rule-based" auditability claim in `PRODUCT_DESCRIPTION.md` §4 defensible to a judge.

---

## 3. Scope

### In scope
- New module `scanner/confidence.py`: signal vocabulary, weights, `calculate_confidence_score()`, band thresholds.
- Adding `confidence_score`, `confidence_band`, `confidence_signals` fields to `scanner/finding.py` (the one permitted `Finding` extension per C-03).
- Emitting signals (not hardcoded `"high"`) from `scanner/python_engine.py` and `scanner/multilang_engine.py`, invoking `calculate_confidence_score()` at emit time.
- Optional per-rule confidence modifiers in `scanner/rules/java.yaml` and `scanner/rules/javascript.yaml` (COORDINATED with scanner lane, additive only).
- `--min-confidence {VERIFIED,PROBABLE,UNVERIFIED}` flag in `scanner/cli.py`.
- Environment variable `SCAN_MIN_CONFIDENCE_BAND` (default `PROBABLE`) read by `api/services/scan_runner.py`.
- Migration `db/migrations/002_confidence_scoring.sql` and the identical change in `db/schema.sql`, plus the `docker-compose.yml` initdb mount at prefix `03_`.
- `db/models.py` `Finding` fields; `db/crud.py` `_FINDING_KEY_ALIASES` + `normalize_finding()` extension; `db/seed.py` sample values updated.
- `api/models.py` `FindingOut` fields; `api/routers/findings.py` `?min_band=` filter added via the shared `common_list_params` dependency (C-16).
- Replacing the `== "high"` gate in `api/services/scan_runner.py` with a band threshold check.
- Implementing `dashboard/src/components/ConfidenceStamp.jsx` (currently a 2-line TODO stub).
- `dashboard/src/lib/constants.js` band vocabulary; `dashboard/src/mockData.js` update from `high/medium/low` to the canonical bands.
- `docs/CONFIDENCE_MODEL_SPEC.md` (SOLE per §1.5).
- `tests/test_confidence_scoring.py` (SOLE).

### Out of scope
- Any change to `api/services/risk_engine.py` or `api/services/cbom_generator.py`'s internals. CONF consumes the refactored `build_cbom_from_findings` after the CBOM lane's Wave 1 refactor lands; CONF does not perform that refactor (C-14).
- Any change to `docs/RISK_ENGINE_SPEC.md`. Confidence is a **separate axis** from `risk_tier` (C-04).
- Historical / time-bucketed confidence for TRD. Confidence is per-finding, per-scan; trend semantics are the TRD proposal's problem (C-04 open sign-off).
- Renaming `detection_method` values from `ast_static_analysis` to `ast_visitor`. `detection_method` registry is FROZEN and owned by the scanner lane (§3.2). CONF flags this to Shashank; CONF does not silently rewrite it.
- Any change to the CBOM lane's `additionalContext` free-text sites at `api/services/cbom_generator.py:179,223` — CONF requests the property-key change (C-14) and does not perform it.
- Any change to `dashboard/src/pages/LandingPage/index.jsx`'s ad-hoc `Verified`/`Probable` strings — that page is SOLE frontend-lane and is the FE pass's problem (§1.4).
- Deletion of `dashboard/src/api.js` — that is Wave 0, backend/frontend lanes (C-08).
- Any change to `dashboard/src/index.css` or `tailwind.config.js`. Tokens are FE's SOLE (§1.4, C-07).
- Any change to `dashboard/src/components/FindingsTable.jsx` before DFS lands its column-registry restructure (C-13). CONF contributes only a `confidenceBand` column definition to `dashboard/src/lib/constants.js` after DFS merges.
- Any change to `api/services/scan_runner.py` by DEP/CNT/BIN/IAC — CONF owns this file for the sprint (C-02).
- Binary/container/dependency scoping decisions (C-20 remains unresolved; CONF is independent).

---

## 4. Required Context Files

Implementers must open and read these first, per `AGENT_RULES.md` #1. All paths are verified against the attached repository and the contract's §1 Canonical File Ownership Map.

- `SYSTEM_INTERFACE_CONTRACT.md` — §0.1, §1, §2.1, §2.2, §3, §4 (C-02, C-03, C-04, C-14, C-16), §5, §6, §7.
- `AGENT_RULES.md` — every rule, especially #2, #3, #5, #6.
- `ARCHITECTURE.md` — §2.1 (Finding contract), §2.2 (data-access layer), §2.3 (findings routes).
- `PRODUCT_DESCRIPTION.md` — §2, §3, §4 (the specific pitch claims this feature defends).
- `db/schema.sql` — the current `findings` table definition (lines 47–79 as attached).
- `db/models.py` — existing `Finding` SQLAlchemy mapping; `CONFIDENCES` tuple at line 14.
- `db/crud.py` — `_FINDING_KEY_ALIASES` (lines 44–75), `normalize_finding()` (lines 86–115).
- `db/migrations/001_secure_reporting.sql` — migration file template.
- `db/seed.py` — seed contract for local fixtures.
- `scanner/finding.py` — the FROZEN dataclass being extended.
- `scanner/python_engine.py` — line 198, the `"high"` literal being removed.
- `scanner/multilang_engine.py` — line 699, the `"high"` literal being removed.
- `scanner/cli.py` — `build_parser()`, `_summary()`, `main()`.
- `scanner/constants.py` — module for band names / thresholds if shared with rules.
- `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml` — existing rule shape.
- `api/services/scan_runner.py` — lines 95–110, the confidence gate being replaced.
- `api/services/cbom_generator.py` — lines 179 and 223 (informational only; CBOM lane changes them).
- `api/routers/findings.py` — the paginated list route CONF adds `min_band=` to.
- `api/models.py` — `FindingOut` being extended.
- `dashboard/src/components/ConfidenceStamp.jsx` — the 2-line stub being implemented.
- `dashboard/src/lib/constants.js`, `dashboard/src/mockData.js` — vocabulary being unified.
- `tests/test_realworld_source_scanner.py`, `tests/test_scanner_battle.py`, `tests/test_crud.py`, `tests/test_secure_report_sync.py` — every assertion of `confidence == "high"` that will fail (C-03).
- `docker-compose.yml` — the initdb mounts (lines 12, 15) the new mount is inserted after.
- `.env.example` — where `SCAN_MIN_CONFIDENCE_BAND` is registered.

---

## 5. File Ownership

Ownership tiers are copied from `SYSTEM_INTERFACE_CONTRACT.md` §1 verbatim.

### 5.1 Files CONF creates (SOLE unless noted)

| Path | Tier | Notes |
|---|---|---|
| `scanner/confidence.py` | **SOLE** | New; signal vocabulary + scorer (§1.1) |
| `db/migrations/002_confidence_scoring.sql` | **SOLE** per §2.1 | Compose mount prefix `03_` |
| `dashboard/src/components/ConfidenceStamp.jsx` | **SOLE** | Currently a 2-line TODO stub (§1.4) |
| `docs/CONFIDENCE_MODEL_SPEC.md` | **SOLE** per §1.5 | |
| `tests/test_confidence_scoring.py` | **SOLE** | New |

### 5.2 Files CONF modifies

| Path | Tier | Integration owner | Notes |
|---|---|---|---|
| `scanner/finding.py` | **FROZEN** — CONF-only extension per §1.1 | scanner lane | Add fields once; never a second time |
| `scanner/python_engine.py` | COORDINATED | scanner lane | Remove hardcoded `"high"` at line 198; call `calculate_confidence_score()` |
| `scanner/multilang_engine.py` | COORDINATED | scanner lane | Remove hardcoded `"high"` at line 699; call `calculate_confidence_score()` |
| `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml` | COORDINATED | scanner lane | Additive per-rule modifiers only |
| `scanner/cli.py` | **COORDINATED** | scanner lane (Shashank) | Add `--min-confidence`; extend `_summary()` with band counts |
| `scanner/constants.py` | COORDINATED | scanner lane | Add `CONFIDENCE_BANDS` tuple + threshold constants |
| `api/services/scan_runner.py` | **FROZEN — CONF's to change** per §1.2 | CONF | Replace the `== "high"` gate |
| `api/models.py` | COORDINATED | backend lane (Shreyanshi) | Extend `FindingOut` |
| `api/routers/findings.py` | COORDINATED | backend lane | Add `min_band` filter via `common_list_params` |
| `db/schema.sql` | COORDINATED | DB lane (Ronak — CONF owner) | Add three columns + one index |
| `db/models.py` | COORDINATED | DB lane | Extend `Finding` mapping; retain `CONFIDENCES` tuple as legacy |
| `db/crud.py` | COORDINATED | DB lane | Extend `_FINDING_KEY_ALIASES`, `normalize_finding()`, add band coercion |
| `db/seed.py` | COORDINATED | DB lane | Update sample values |
| `docker-compose.yml` | COORDINATED | deploy lane | Add one initdb mount at prefix `03_` |
| `.env.example` | COORDINATED | deploy lane | Register `SCAN_MIN_CONFIDENCE_BAND` |
| `dashboard/src/lib/constants.js` | COORDINATED | frontend lane | Add band vocabulary; column definition **after DFS lands** (C-13) |
| `dashboard/src/mockData.js` | COORDINATED | frontend lane | Replace `high/medium/low` with canonical bands |
| `dashboard/src/pages/DashboardPage/index.jsx` | COORDINATED | frontend lane | Replace `<ConfidenceDot>` sites with `<ConfidenceStamp>` |
| `tests/test_crud.py`, `tests/test_realworld_source_scanner.py`, `tests/test_scanner_battle.py`, `tests/test_secure_report_sync.py` | COORDINATED | owning lane | Update `confidence == "high"` assertions — **who owns this is C-03(b), pending sign-off** |

### 5.3 Explicit "Do Not Touch" list (SOLE or FROZEN owned by other features)

CONF must not open a PR against any of the following:

- `api/services/risk_engine.py` (FROZEN, CBOM/risk lane) — C-04
- `api/services/cbom_generator.py` (COORDINATED, CBOM lane; CONF requests but does not perform the property-key refactor) — C-14
- `api/routers/auth.py`, `api/core/rbac.py` (SOLE, RBAC)
- `api/routers/agents.py`, `api/services/enrollment.py` (SOLE, ENR)
- `api/routers/audit.py`, `api/services/audit.py` (SOLE, AUD)
- `api/routers/triage.py` (SOLE, TRI)
- `api/routers/trends.py` (SOLE, TRD)
- `api/routers/compliance.py` (SOLE, CMP, conditional)
- `api/services/cbom_validator.py` (SOLE, CBV)
- `scanner/dependency_engine.py`, `scanner/dependency_rules/` (SOLE, DEP)
- `scanner/container_engine.py`, `scanner/image_layers.py` (SOLE, CNT)
- `scanner/binary_engine.py` (SOLE, BIN)
- `scanner/config_engine.py` (SOLE, IAC)
- `scanner/enroll_cli.py` (SOLE, ENR)
- `scanner/ecdat_cli.py`, `pyproject.toml` (SOLE, CLI)
- `scanner/rules/container.yaml`, `binary.yaml`, `config.yaml` (SOLE per feature)
- `dashboard/src/index.css`, `dashboard/tailwind.config.js`, `dashboard/public/fonts/` (SOLE, FE)
- `dashboard/src/context/AuthContext.jsx`, `dashboard/src/pages/LoginPage/LoginForm.jsx` (SOLE, RBAC)
- `dashboard/src/pages/LandingPage/index.jsx` (SOLE, frontend lane; sole GSAP consumer per C-17)
- `dashboard/src/components/AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `pages/AgentStatusPage/`, `hooks/useAgents.js` (SOLE, ASP)
- `dashboard/src/components/ComplianceReport.jsx` (SOLE, CMP)
- `dashboard/src/components/RiskTrendChart.jsx`, `RiskTierBreakdown.jsx`, `pages/TrendsPage/` (SOLE, TRD)
- `dashboard/src/components/FindingsTable.jsx` (COORDINATED, **DFS restructures first**) — C-13
- `dashboard/src/lib/api.js` (COORDINATED, frontend lane; RBAC adds the `Authorization: Bearer` flow) — C-08
- `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml` (SOLE, INS)
- `db/migrations/003_..008_*.sql` (SOLE per file, per §2.1)
- `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md` — CONF must not edit any of these; the single scope editor handles them post-sprint (C-19).

---

## 6. Tech Stack & Pinned Versions

Checked against `requirements.txt` and `dashboard/package.json` as attached. **No pin is changed, added or dropped by CONF.** Everything below is already present.

### Python (backend + scanner)
- Python **3.11 only** (`requirements.txt` header). `tree-sitter-languages` blocks 3.12+.
- `PyYAML>=6.0` — per-rule confidence modifiers.
- `SQLAlchemy>=2.0,<2.1` — the `Finding` mapping extension.
- `psycopg2-binary>=2.9`, `aiosqlite>=0.20.0` — unchanged.
- `pydantic>=2.7.0` — `FindingOut` extension in `api/models.py`.
- `fastapi>=0.111.0` — `min_band` query parameter and the `Depends(common_list_params)` C-16 dependency.
- `pytest>=8.0`, `pytest-asyncio>=0.23.0` — new test module.
- Standard library only for `scanner/confidence.py`: `dataclasses`, `enum`, `typing`, `hashlib` (fingerprinting is TRI's responsibility, not CONF's — C-15).

### Frontend
- `react ^18.3.1`, `lucide-react ^0.428.0` — `ConfidenceStamp.jsx`.
- `prop-types ^15.8.1` — `ConfidenceStamp` prop typing (existing convention in the repo).
- `tailwindcss ^3.4.19`, `tailwind-merge ^2.6.1`, `clsx ^2.1.1` — token consumption via existing utility classes only (C-07).
- No new npm dependency. Motion is not required for the stamp.

### Ops
- `docker-compose.yml` gains one `.sql` initdb mount at prefix `03_`. No image bump.

---

## 7. Concrete Interface Definitions

Signatures below are literal. Renaming, restructuring or "improving" any of them requires flagging a human per `AGENT_RULES.md` #3.

### 7.1 `scanner/confidence.py` — new module

```python
"""
scanner/confidence.py — Unified confidence scoring across every ECDAT engine.

Signals emitted by a detection engine are mapped, deterministically and
without any learned component, to a numeric score in [0.0, 1.0] and a
band in {VERIFIED, PROBABLE, UNVERIFIED}. Every engine feeds the same
scorer so a Python AST finding and a tree-sitter Java finding at the
same score mean the same thing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ConfidenceBand(str, Enum):
    VERIFIED = "VERIFIED"
    PROBABLE = "PROBABLE"
    UNVERIFIED = "UNVERIFIED"


CONFIDENCE_BANDS: tuple[str, ...] = tuple(band.value for band in ConfidenceBand)

# Band thresholds — the low bound is inclusive.
BAND_THRESHOLDS: dict[str, float] = {
    ConfidenceBand.VERIFIED.value:   0.85,
    ConfidenceBand.PROBABLE.value:   0.60,
    ConfidenceBand.UNVERIFIED.value: 0.00,
}


class ConfidenceSignal(str, Enum):
    IMPORT_RESOLVED         = "import_resolved"
    ALIAS_TRACED            = "alias_traced"
    CALL_SITE_MATCHED       = "call_site_matched"
    LITERAL_ALGORITHM_ARG   = "literal_algorithm_arg"
    KEY_SIZE_EXTRACTED      = "key_size_extracted"
    RULE_YAML_MATCHED       = "rule_yaml_matched"
    EXPECTED_MODULE_CONFIRMED = "expected_module_confirmed"
    DYNAMIC_ALGORITHM_ARG   = "dynamic_algorithm_arg"       # negative
    IMPORT_UNRESOLVED       = "import_unresolved"           # negative
    PATH_LOOKS_LIKE_TEST    = "path_looks_like_test"        # negative
    PATH_LOOKS_LIKE_VENDOR  = "path_looks_like_vendor"      # negative


SIGNAL_WEIGHTS: dict[str, float] = {
    ConfidenceSignal.IMPORT_RESOLVED.value:          0.35,
    ConfidenceSignal.ALIAS_TRACED.value:             0.15,
    ConfidenceSignal.CALL_SITE_MATCHED.value:        0.20,
    ConfidenceSignal.LITERAL_ALGORITHM_ARG.value:    0.15,
    ConfidenceSignal.KEY_SIZE_EXTRACTED.value:       0.05,
    ConfidenceSignal.RULE_YAML_MATCHED.value:        0.10,
    ConfidenceSignal.EXPECTED_MODULE_CONFIRMED.value: 0.20,
    ConfidenceSignal.DYNAMIC_ALGORITHM_ARG.value:   -0.20,
    ConfidenceSignal.IMPORT_UNRESOLVED.value:       -0.40,
    ConfidenceSignal.PATH_LOOKS_LIKE_TEST.value:    -0.10,
    ConfidenceSignal.PATH_LOOKS_LIKE_VENDOR.value:  -0.10,
}

CONFIDENCE_MODEL_VERSION: str = "conf-1.0.0"


@dataclass(frozen=True)
class ConfidenceVerdict:
    score: float           # 0.00 – 1.00, rounded to 2 dp
    band: str              # one of CONFIDENCE_BANDS
    signals: list[str]     # deduplicated, sorted, subset of ConfidenceSignal values
    model_version: str     # CONFIDENCE_MODEL_VERSION


def calculate_confidence_score(signals: Iterable[str]) -> ConfidenceVerdict: ...


def band_for_score(score: float) -> str: ...


def meets_band_threshold(band: str, minimum: str) -> bool: ...


def legacy_confidence_for(band: str) -> str:
    """Contract-mandated derived value for the legacy findings.confidence TEXT column."""
    ...
```

### 7.2 `scanner/finding.py` — extended dataclass

```python
from dataclasses import dataclass, asdict, field
from typing import Optional


@dataclass
class Finding:
    file: str
    line: int
    matched_call: str
    library: str
    algorithm: str
    primitive: str
    language: str
    weak_by_default: bool
    confidence: str = "high"                       # LEGACY, derived; see legacy_confidence_for()
    key_size: Optional[int] = None
    detection_method: str = "static_analysis"

    # ── CONF additions (one-time extension per contract §1.1, C-03) ─────────
    confidence_score: float = 0.0
    confidence_band: str = "UNVERIFIED"
    confidence_signals: list[str] = field(default_factory=list)
    confidence_model_version: str = "conf-1.0.0"

    def to_dict(self) -> dict:
        return asdict(self)
```

### 7.3 `scanner/python_engine.py` — replacement for the `line 198` literal (interface only)

```python
# Replaces: confidence="high",  # Emitted candidates are explicit-import-backed.
from scanner.confidence import (
    ConfidenceSignal,
    calculate_confidence_score,
    legacy_confidence_for,
)

def _emit_finding(self, node, rule, key_size, signals: list[str]) -> None:
    verdict = calculate_confidence_score(signals)
    self.findings.append(Finding(
        file=self.filename,
        line=node.lineno,
        matched_call=self._source_snippet(node),
        library=rule["library"],
        algorithm=rule["algorithm"],
        primitive=rule["primitive"],
        language="python",
        weak_by_default=rule["algorithm"] in WEAK_ALGORITHMS,
        confidence=legacy_confidence_for(verdict.band),
        key_size=key_size,
        detection_method="ast_static_analysis",   # scanner-lane owns §3.2 rename separately
        confidence_score=verdict.score,
        confidence_band=verdict.band,
        confidence_signals=verdict.signals,
        confidence_model_version=verdict.model_version,
    ))
```

### 7.4 `scanner/multilang_engine.py` — replacement for the `line 699` literal (interface only)

```python
# Replaces: confidence="high",  # Every emitted multilang finding is explicit-import-backed.
from scanner.confidence import (
    ConfidenceSignal,
    calculate_confidence_score,
    legacy_confidence_for,
)

# At the Finding(...) construction site inside scan_file():
verdict = calculate_confidence_score(signals)
findings.append(
    Finding(
        file=str(path),
        line=call_node.start_point[0] + 1,
        matched_call=source[call_node.start_byte:call_node.end_byte].decode("utf-8", "ignore"),
        library=rule_object,
        algorithm=rule["algorithm"],
        primitive=rule["primitive"],
        language=lang_key,
        weak_by_default=rule["weak_by_default"],
        confidence=legacy_confidence_for(verdict.band),
        key_size=key_size,
        detection_method="tree_sitter_query",
        confidence_score=verdict.score,
        confidence_band=verdict.band,
        confidence_signals=verdict.signals,
        confidence_model_version=verdict.model_version,
    )
)
```

### 7.5 `scanner/cli.py` — `--min-confidence` addition

```python
parser.add_argument(
    "--min-confidence",
    choices=("VERIFIED", "PROBABLE", "UNVERIFIED"),
    default=None,
    help="Drop findings whose confidence_band is below this level before printing. "
         "Independent of --fail-on.",
)
```

### 7.6 `db/migrations/002_confidence_scoring.sql` (literal, matching contract §2.2)

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
```

### 7.7 `db/schema.sql` — identical change

```sql
-- Appended inside the CREATE TABLE findings block (or as ADD COLUMN IF NOT EXISTS
-- following the same idempotency pattern used elsewhere in this file):
confidence_score   NUMERIC(3,2),
confidence_band    TEXT,
confidence_signals JSONB,
-- and, alongside the existing indexes for findings:
CREATE INDEX IF NOT EXISTS idx_findings_confidence_band ON findings(confidence_band);
```

### 7.8 `db/models.py` — extended `Finding`

```python
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Numeric

CONFIDENCES = ("low", "medium", "high")         # LEGACY, retained per C-03
CONFIDENCE_BANDS = ("VERIFIED", "PROBABLE", "UNVERIFIED")


class Finding(Base):
    __tablename__ = "findings"
    # ... existing columns unchanged ...
    confidence_score:   Mapped[float | None] = mapped_column(Numeric(3, 2))
    confidence_band:    Mapped[str | None]   = mapped_column(Text)
    confidence_signals: Mapped[list | None]  = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_findings_scan_id", "scan_id"),
        Index("idx_findings_severity", "risk_tier"),
        Index("idx_findings_source_context", "source_context"),
        Index("idx_findings_confidence_band", "confidence_band"),
    )
```

### 7.9 `db/crud.py` — alias registrations and coercion

```python
_FINDING_KEY_ALIASES.update({
    "confidence_score":   "confidence_score",
    "confidencescore":    "confidence_score",
    "confidence_band":    "confidence_band",
    "confidenceband":     "confidence_band",
    "confidence_signals": "confidence_signals",
    "confidencesignals":  "confidence_signals",
})


def _coerce_band(value: Any) -> str | None: ...
def _coerce_score(value: Any) -> float | None: ...
def _coerce_signals(value: Any) -> list[str] | None: ...
```

### 7.10 `api/models.py` — `FindingOut`

```python
class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # ... existing fields unchanged ...
    confidence_score:   float | None      = None
    confidence_band:    str  | None       = None
    confidence_signals: list[str] | None  = None
```

### 7.11 `api/routers/findings.py` — filter parameter (via C-16 shared dependency)

```python
# Added to the common_list_params dependency owned by DFS (api/core/params.py);
# CONF contributes only this parameter.
min_band: str | None = Query(
    default=None,
    pattern="^(VERIFIED|PROBABLE|UNVERIFIED)$",
    description="Return findings whose confidence_band meets or exceeds this level.",
)
```

### 7.12 `api/services/scan_runner.py` — gate replacement (interface only)

```python
import os
from scanner.confidence import meets_band_threshold, CONFIDENCE_BANDS

_MIN_BAND: str = os.environ.get("SCAN_MIN_CONFIDENCE_BAND", "PROBABLE")
if _MIN_BAND not in CONFIDENCE_BANDS:
    _MIN_BAND = "PROBABLE"

# Replaces the finding.get("confidence") == "high" comprehension around line 103.
def _passes_gate(finding: dict) -> bool: ...
```

### 7.13 `dashboard/src/components/ConfidenceStamp.jsx` — component interface

```jsx
import PropTypes from "prop-types";

export function ConfidenceStamp({ band, score, signals }) { /* ... */ }

ConfidenceStamp.propTypes = {
    band:    PropTypes.oneOf(["VERIFIED", "PROBABLE", "UNVERIFIED"]).isRequired,
    score:   PropTypes.number,
    signals: PropTypes.arrayOf(PropTypes.string),
};

ConfidenceStamp.defaultProps = { score: null, signals: [] };

export default ConfidenceStamp;
```

### 7.14 `dashboard/src/lib/constants.js` — band vocabulary

```js
export const CONFIDENCE_BANDS = ["VERIFIED", "PROBABLE", "UNVERIFIED"];
export const CONFIDENCE_BAND_LABELS = {
    VERIFIED:   "Verified",
    PROBABLE:   "Probable",
    UNVERIFIED: "Unverified",
};
```

### 7.15 Example `GET /scans/{scan_id}/findings?min_band=PROBABLE` response (single finding excerpt)

```json
{
    "id": 1042,
    "scan_id": 17,
    "file": "src/auth/legacy_login.py",
    "line": 42,
    "algorithm": "MD5",
    "key_size": null,
    "confidence": "high",
    "confidence_score": 0.90,
    "confidence_band": "VERIFIED",
    "confidence_signals": [
        "call_site_matched",
        "expected_module_confirmed",
        "import_resolved",
        "literal_algorithm_arg"
    ],
    "risk_tier": "CRITICAL",
    "risk_reason": "MD5 collision attacks are computationally trivial.",
    "criticality": "MEDIUM",
    "matched_call": "hashlib.md5(password)",
    "library": "hashlib",
    "primitive": "hash",
    "language": "python",
    "weak_by_default": true,
    "detection_method": "ast_static_analysis",
    "source_context": "SOURCE"
}
```

### 7.16 CBOM property-key registration (produced by CBOM lane on CONF's behalf per C-14)

```json
{
    "properties": [
        {"name": "ecdat:confidence_band",  "value": "VERIFIED"},
        {"name": "ecdat:confidence_score", "value": "0.90"},
        {"name": "ecdat:detection_method", "value": "ast_static_analysis"}
    ]
}
```

---

## 8. Step-by-Step Implementation Plan

Every step is tied to exactly one file. Steps 1–6 form phase 1 (Wave 1 mergeable). Steps 7–14 form phase 2 (Wave 2 / after DFS and CBOM refactor land).

**Phase 1 — signals, scorer, DB, CLI**

1. **`scanner/confidence.py`** — create the module with the interfaces in §7.1.
2. **`scanner/finding.py`** — extend the dataclass with the four fields in §7.2. This is the one and only permitted extension (C-03).
3. **`db/schema.sql`** — add the three columns and the index from §7.7. Idempotent form (`ADD COLUMN IF NOT EXISTS`).
4. **`db/migrations/002_confidence_scoring.sql`** — create with the literal SQL in §7.6.
5. **`docker-compose.yml`** — insert one new initdb mount, at prefix `03_`, immediately after the existing `02_secure_reporting.sql` mount (line 15).
6. **`db/models.py`** — add the three `Finding` columns and the `CONFIDENCE_BANDS` tuple per §7.8. Retain `CONFIDENCES` unchanged.
7. **`db/crud.py`** — extend `_FINDING_KEY_ALIASES` and add the three coercers per §7.9. `normalize_finding()` calls them; `save_findings()` needs no signature change.
8. **`db/seed.py`** — replace the `random.choice(["high","medium"])` at line 40 with sample band values drawn from `CONFIDENCE_BANDS`.
9. **`scanner/constants.py`** — export `CONFIDENCE_BANDS` and `BAND_THRESHOLDS` re-exports for engines and CLI to import from a single place.
10. **`scanner/python_engine.py`** — replace the `line 198` hardcoded `"high"` per §7.3. Signals are gathered at the emission site (import binding resolved? alias traced? algorithm arg a `Constant`?).
11. **`scanner/multilang_engine.py`** — replace the `line 699` hardcoded `"high"` per §7.4. Signals derived from `expected_module` match, `match_arg_contains` literal, `imports` binding.
12. **`scanner/rules/java.yaml`, `scanner/rules/javascript.yaml`** — optional per-rule `confidence_modifier: float` field, additive only. Loader ignores unknown keys today; no scanner-lane rewrite required.
13. **`scanner/cli.py`** — add `--min-confidence` per §7.5. `_summary()` gains three band counters; the JSON stdout contract is unchanged (fields may be added; none renamed or removed per §3.5).
14. **`api/services/scan_runner.py`** — replace the `== "high"` filter at line 103 with `_passes_gate()` per §7.12. Sub-threshold findings are persisted **or** dropped per the C-02 sign-off answer (§11).
15. **`.env.example`** — register `SCAN_MIN_CONFIDENCE_BAND=PROBABLE`.
16. **`tests/test_confidence_scoring.py`** — table-driven `(signals) → (score, band)` cases; band-threshold boundary cases; `legacy_confidence_for` round-trip; env-var override.
17. **`docs/CONFIDENCE_MODEL_SPEC.md`** — document the signal list, weights, thresholds, and `CONFIDENCE_MODEL_VERSION` bump policy.

**Phase 2 — API surface and dashboard**

18. **`api/models.py`** — extend `FindingOut` per §7.10.
19. **`api/routers/findings.py`** — add the `min_band` parameter through `api/core/params.py::common_list_params` after DFS publishes it (C-16). Wire it into the existing `crud.list_findings_for_scan` call.
20. **`dashboard/src/components/ConfidenceStamp.jsx`** — implement per §7.13 using `lucide-react` icons and Tailwind classes bound to existing `--critical`/`--high`/`--medium`/`--low` tokens (**no** new tokens, C-07).
21. **`dashboard/src/lib/constants.js`** — add band vocabulary per §7.14. Column-definition entry for the `FindingsTable` column registry is added **only after DFS's C-13 restructure lands**.
22. **`dashboard/src/mockData.js`** — replace `confidence: 'high' | 'medium' | 'low'` with the canonical bands.
23. **`dashboard/src/pages/DashboardPage/index.jsx`** — replace the two `<ConfidenceDot>` usage sites (lines 214, 506) with `<ConfidenceStamp>`.
24. **Tests fixup** — `tests/test_realworld_source_scanner.py`, `tests/test_scanner_battle.py`, `tests/test_crud.py`, `tests/test_secure_report_sync.py` update per C-03(b) sign-off answer.

---

## 9. Naming & Symbol Registry

Cross-checked against `SYSTEM_INTERFACE_CONTRACT.md` §3, §5.4, and every other feature's `Notes` column in §1.

### 9.1 New Python symbols (scanner/confidence.py)

| Symbol | Kind | Collision check |
|---|---|---|
| `ConfidenceBand` | class (enum) | Unique — grep of `db/`, `api/`, `scanner/` returns no match |
| `CONFIDENCE_BANDS` | module constant | Also exported from `db/models.py` (§3.8 pattern); mirrored intentionally |
| `BAND_THRESHOLDS` | module constant | Unique |
| `ConfidenceSignal` | class (enum) | Unique |
| `SIGNAL_WEIGHTS` | module constant | Unique |
| `CONFIDENCE_MODEL_VERSION` | module constant | Distinct from `risk_model_version` (C-04) |
| `ConfidenceVerdict` | dataclass | Unique |
| `calculate_confidence_score` | function | Matches §3.1 verbatim; **not** `CalculateECDATScore` (§8 changelog) |
| `band_for_score` | function | Unique |
| `meets_band_threshold` | function | Unique |
| `legacy_confidence_for` | function | Unique |

### 9.2 New DB columns

| Column | Table | Type | Collision check |
|---|---|---|---|
| `confidence_score` | `findings` | `NUMERIC(3,2)` | Reserved for CONF in §2.2, §5.2, §5.4 |
| `confidence_band` | `findings` | `TEXT` | Reserved for CONF |
| `confidence_signals` | `findings` | `JSONB` | Reserved for CONF |

### 9.3 New DB index

| Index | Table | Columns |
|---|---|---|
| `idx_findings_confidence_band` | `findings` | `(confidence_band)` |

Does not collide with DFS/TRD's `idx_findings_scan_tier`, `idx_findings_scan_lang` (008_query_indexes.sql).

### 9.4 New environment variable

| Name | Prefix owner | Default |
|---|---|---|
| `SCAN_MIN_CONFIDENCE_BAND` | `SCAN_` (scanner lanes) per §3.3 | `PROBABLE` |

Does not collide with `SCAN_ENABLE_BINARY`, `SCAN_ENABLE_CONTAINER`, `SCAN_MAX_ARTIFACT_BYTES`, `SCAN_IMAGE_TAR_PATH`.

### 9.5 New CLI flag

| Flag | Owner | Collision check |
|---|---|---|
| `--min-confidence {VERIFIED,PROBABLE,UNVERIFIED}` | CONF | §5.4 assigns this to CONF as `Sole`; distinct from `--fail-on` (§3.5) and `--scan-type` (C-11) |

### 9.6 New API query parameter

| Parameter | Route | Type |
|---|---|---|
| `min_band` | `GET /scans/{scan_id}/findings` | `str` (enum) |

Injected via C-16 `common_list_params`, not a route-local `Query()` — this is the mandated shape.

### 9.7 New CBOM property keys (registered by CBOM lane per C-14)

- `ecdat:confidence_band`
- `ecdat:confidence_score`

Never `additionalContext` free text.

### 9.8 New React symbols

| Symbol | File |
|---|---|
| `ConfidenceStamp` | `dashboard/src/components/ConfidenceStamp.jsx` |
| `CONFIDENCE_BANDS`, `CONFIDENCE_BAND_LABELS` | `dashboard/src/lib/constants.js` |

Named export plus default export, matching the existing `Card.jsx` / `Badge.jsx` convention.

---

## 10. Known Cross-Feature Risks

Pulled directly from `SYSTEM_INTERFACE_CONTRACT.md` §4 and §5. Resolutions below are the ones already decided by the contract; no new resolution is proposed here.

- **C-01 · Migration number collision.** Migration `002_` was claimed by five features. Numbers are reserved in §2.1; CONF's file is `002_confidence_scoring.sql` with compose mount prefix `03_`. Any deviation invalidates the initdb order for every downstream feature. **Confidence: High.**
- **C-02 · `scan_runner.py` gate.** DEP, CNT, BIN, IAC, CONF all touch this file; CONF owns the change. DEP/CNT/BIN/IAC must not edit it. **Confidence: High on ownership; Medium and unresolved on persist-vs-drop — see §11.**
- **C-03 · Four incompatible confidence vocabularies.** `db/models.py` has `CONFIDENCES=("low","medium","high")`; `finding.py` docstring says `high`/`unverified`; `mockData.js` uses `high/medium/low`; `LandingPage` uses `Verified`/`Probable`; both engines hardcode `"high"`. Resolution: adopt the two-field model above; legacy `confidence` TEXT is a derived read-only mirror (`VERIFIED→high`, else `unverified`). **Confidence: Medium; sign-off blocks §11(a)(b)(c).**
- **C-04 · Two risk-scoring implementations.** `risk_engine.py` is the sole authority. Confidence is a separate axis from `risk_tier` — a low-confidence MD5 finding is still CRITICAL. **Confidence: High on the decoupling.** Trend-view interaction (whether TRD pins to `risk_model_version` or shows latest) affects whether confidence values are historised — flagged in §11.
- **C-11 · CLI flag namespace.** `--min-confidence` is declared `Sole` to CONF in §5.4 — no other feature may reuse the flag or its value tuple. `--scan-type` remains scanner-lane. **Confidence: Medium.**
- **C-13 · `FindingsTable.jsx` seven-way contention.** DFS restructures the table into a column registry first. CONF adds a `confidenceBand` column definition to `dashboard/src/lib/constants.js` **only after** DFS lands. **Confidence: Medium; C-13 sign-off is DFS's, not CONF's.**
- **C-14 · `cbom_generator.py` refactor.** CBOM lane extracts `build_cbom_from_findings(findings, summary) -> dict` in Wave 1 and registers `ecdat:confidence_band`, `ecdat:confidence_score`. CONF does not edit `cbom_generator.py` directly. **Confidence: High on the refactor shape.**
- **C-16 · Overlapping list/filter/pagination.** `min_band` joins DFS's `common_list_params` FastAPI dependency in `api/core/params.py`. CONF does not add a per-route `Query()` for it. **Confidence: Medium.**
- **C-19 · Scope-honesty documents.** CONF does not edit `PRODUCT_DESCRIPTION.md`, `README.md`, or `ARCHITECTURE.md`. The single scope editor handles the rewrite once every scope doc exists. **Confidence: High on the process.**
- **§5.1 · Broken tests (breaking).** `tests/test_crud.py`, `test_realworld_source_scanner.py`, `test_scanner_battle.py`, `test_secure_report_sync.py` all assert `confidence == "high"`. C-03(b) sign-off decides who updates them and whether the 18-finding demo baseline moves.

---

## 11. Pre-Answered Ambiguities

Each entry follows "if X happens, do Y." Entries 11.1 through 11.5 are the open sign-off items in the contract that touch CONF — those five are recorded with **no resolution**, per the user instruction to flag rather than invent. Entries 11.6 onwards are agent-facing situational disambiguation.

### Open sign-off items — no resolution invented

**11.1 · C-02 · Persist or drop sub-threshold findings?**
*If a finding's `confidence_band` is below `SCAN_MIN_CONFIDENCE_BAND`, does the run persist it with its band and mark it UNVERIFIED, or drop it and never write a row?*
**Status:** open. Contract §4 C-02 flags this as Medium, needs product + DB-lane sign-off. Do not implement either behaviour in `_passes_gate` before the answer lands.

**11.2 · C-03(a) · Backfill policy for existing `confidence='high'` rows.**
*If migration 002 finds pre-existing findings rows with `confidence='high'`, does the migration backfill `confidence_band='VERIFIED'` and `confidence_score=0.85`, or does it leave both NULL and treat NULL as "pre-model legacy"?*
**Status:** open. Contract §4 C-03 lists this explicitly as Medium, needs sign-off. `db/migrations/002_confidence_scoring.sql` must be shipped with `NULL == pre-model legacy row` (as the migration comment already states); a backfill statement is only added after sign-off.

**11.3 · C-03(b) · Broken-test ownership and demo baseline.**
*If `tests/test_realworld_source_scanner.py`, `tests/test_scanner_battle.py`, `tests/test_crud.py` and `tests/test_secure_report_sync.py` fail because they assert `confidence == "high"`, who updates them, and does the pitch's "18 findings" demo baseline move?*
**Status:** open. Contract §4 C-03 lists this as Medium, needs sign-off from product + scanner lane. Do not silently rewrite these test assertions.

**11.4 · C-03(c) · `--fail-on` band interaction.**
*If a CI run finds a CRITICAL algorithm with `confidence_band=UNVERIFIED`, does `--fail-on CRITICAL` still exit 2, or does band-gating suppress the failure?*
**Status:** open. Contract §5.4 marks `--fail-on` "Conflicting !" between CONF, TRI, BIN. Leave `_violates_policy()` unchanged in phase 1; band-gating of `--fail-on` waits for sign-off. Consequence: the CI gate keeps its current semantics until then.

**11.5 · C-04 · Trend / historical confidence.**
*If TRD needs a historical / time-bucketed confidence axis, is the `confidence_score` frozen at write-time (never recomputed) or recomputable under a new `CONFIDENCE_MODEL_VERSION`?*
**Status:** open. Contract §4 C-04 flags this as Medium, requires risk-lane (Maitreyi) + TRD sign-off. Phase 1 writes `confidence_model_version` on every finding so that whichever policy is chosen later is expressible; no recomputation logic ships in phase 1.

### Agent-facing situational rules

**11.6 · If a scanner-lane engine emits a `Finding` with the `confidence` string still set to a legacy value ("high"/"medium"/"low")**, treat that finding as pre-model: leave `confidence_band` NULL, do not fabricate a band from the legacy string, and record no signals. `legacy_confidence_for()` runs only in the write direction (band → string), never the read direction.

**11.7 · If a rule YAML file contains `confidence_modifier: -0.15` or similar and the file is loaded by an older `multilang_engine.load_rules` that does not know the key**, do nothing — the loader already ignores unknown keys and the modifier is additive. Do not force-upgrade `load_rules` in this PR; that is scanner-lane's move.

**11.8 · If `SCAN_MIN_CONFIDENCE_BAND` is set to a value not in `CONFIDENCE_BANDS`** (e.g. `"HIGH"` from a copy-pasted legacy env file), fall back to `PROBABLE` and log a WARNING once at scan-runner import. Do not raise — the CI pipeline must not go down over a typo in an env var.

**11.9 · If a finding arrives at `db/crud.normalize_finding()` with `confidence_signals` as a JSON string** (from the CLI stdout contract), parse it into a `list[str]` before assigning; if the string is malformed, drop the field (persist NULL) and continue. The rule of the surrounding function ("storing 90% of findings beats 500-ing on one bad row", `db/crud.py:97`) applies verbatim.

**11.10 · If a downstream consumer (CBOM, dashboard) receives a row with `confidence_band=NULL`**, treat it as `UNVERIFIED` for display purposes only — never write that back. The NULL is the legacy marker (C-03) and must survive round-trip.

**11.11 · If the DFS `common_list_params` dependency does not yet exist when phase 2 begins**, do not add `min_band` as a per-route `Query()` on `api/routers/findings.py`. Flag the ordering to backend lane and wait — a per-route parameter here becomes technical debt DFS then has to unpick.

**11.12 · If the CBOM lane's `build_cbom_from_findings` refactor is not yet merged when the dashboard/back-end sees `confidence_band` values**, do not add `ecdat:confidence_band` to `api/services/cbom_generator.py` unilaterally. The CBOM lane owns that file (§1.2 COORDINATED, C-14).

**11.13 · If a signal name appears in an engine's output that is not in `ConfidenceSignal`**, `calculate_confidence_score()` ignores it (weight 0) and includes it in `verdict.signals` unchanged, so the evidence trail stays complete. Adding a new signal name is a `scanner/confidence.py` change plus a `docs/CONFIDENCE_MODEL_SPEC.md` entry and a `CONFIDENCE_MODEL_VERSION` bump — never done silently in an engine.

**11.14 · If `scanner/python_engine.py` or `scanner/multilang_engine.py` still emits `detection_method="ast_static_analysis"` after phase 1**, that is expected. The §3.2 registry rename to `ast_visitor` is a scanner-lane change and is explicitly out of scope for CONF (§3, §5.3).

**11.15 · If a merge conflict appears in `scanner/finding.py` from a second feature adding fields**, stop and flag `AGENT_RULES.md` #2. `finding.py` is FROZEN; only CONF may add fields, once (contract §1.1). A second additive PR is a contract violation, not a merge to resolve.

---

## 12. Test Plan / Definition of Done

All commands run from the repo root inside the `python:3.11-slim`-based dev container or a local Python 3.11 environment.

### 12.1 Unit — scorer

```bash
pytest tests/test_confidence_scoring.py -v
```

Expected (exact assertions defined in the new test module):

- `calculate_confidence_score([])` → `score == 0.0`, `band == "UNVERIFIED"`, `signals == []`.
- `calculate_confidence_score(["import_resolved","call_site_matched","literal_algorithm_arg","expected_module_confirmed"])` → `score >= 0.85`, `band == "VERIFIED"`.
- `calculate_confidence_score(["rule_yaml_matched","call_site_matched"])` → `0.60 <= score < 0.85`, `band == "PROBABLE"`.
- `calculate_confidence_score(["rule_yaml_matched","dynamic_algorithm_arg","import_unresolved"])` → `score < 0.60`, `band == "UNVERIFIED"`.
- `band_for_score(0.849) == "PROBABLE"`; `band_for_score(0.850) == "VERIFIED"` (threshold is inclusive at the low bound).
- `meets_band_threshold("PROBABLE","VERIFIED") is False`; `meets_band_threshold("VERIFIED","PROBABLE") is True`.
- `legacy_confidence_for("VERIFIED") == "high"`; `legacy_confidence_for("PROBABLE") == "unverified"`; `legacy_confidence_for("UNVERIFIED") == "unverified"`.

### 12.2 Unit — CLI

```bash
pytest tests/test_cli_secure.py -v
```

Expected: passes unchanged. The stdout JSON contract (a JSON array of finding dicts) still holds; new fields (`confidence_score`, `confidence_band`, `confidence_signals`) are present alongside legacy `confidence`.

### 12.3 Unit — CRUD

```bash
pytest tests/test_crud.py -v
```

Expected after C-03(b) sign-off: passes with band-aware assertions. Until sign-off lands, this test is expected-red and must be marked `xfail` with a reference to `C-03(b)` — not silently rewritten.

### 12.4 End-to-end scanner

```bash
pytest tests/test_realworld_source_scanner.py tests/test_scanner_battle.py -v
```

Expected after C-03(b) sign-off: assertions of `confidence == "high"` become `confidence_band == "VERIFIED"`; total finding count matches the demo baseline in `PRODUCT_DESCRIPTION.md` §5. Same `xfail` rule as 12.3 until sign-off.

### 12.5 Migration idempotency

```bash
docker compose down -v
docker compose up -d postgres
docker compose exec postgres psql -U ecdat -d ecdat -c \
  "\d findings" | grep -E "confidence_(score|band|signals)"
docker compose exec postgres psql -U ecdat -d ecdat -f \
  /docker-entrypoint-initdb.d/03_confidence_scoring.sql
```

Expected: three new columns visible after the first `up`; the second, explicit `psql -f` run is a no-op and exits 0 (idempotent `ADD COLUMN IF NOT EXISTS`).

### 12.6 API smoke

```bash
curl -s "http://localhost:8000/scans/1/findings?min_band=VERIFIED" \
  -H "X-API-Key: $API_KEY" | jq '.findings[0] | keys'
```

Expected: response includes keys `confidence_score`, `confidence_band`, `confidence_signals`; every returned row satisfies `confidence_band == "VERIFIED"`.

### 12.7 Scan-runner gate

```bash
SCAN_MIN_CONFIDENCE_BAND=VERIFIED pytest tests/test_scan_runner.py -v
SCAN_MIN_CONFIDENCE_BAND=UNVERIFIED pytest tests/test_scan_runner.py -v
```

Expected: the finding count returned by `run_scan()` monotonically decreases as `SCAN_MIN_CONFIDENCE_BAND` rises. Exact numbers pin to fixture data.

### 12.8 CLI band-filter

```bash
python -m scanner.cli tests/fixtures/python_hashes --min-confidence VERIFIED | jq '. | length'
python -m scanner.cli tests/fixtures/python_hashes --min-confidence UNVERIFIED | jq '. | length'
```

Expected: the first count is less than or equal to the second, and both are non-negative integers.

### 12.9 Dashboard build

```bash
cd dashboard && npm ci && npm run build
```

Expected: exit 0. `ConfidenceStamp.jsx` type-checks; no runtime warnings about undefined `band`.

### Definition of Done

- All commands in §12.1, §12.2, §12.5, §12.6, §12.7, §12.8, §12.9 return exit 0.
- §12.3 and §12.4 return exit 0 **after** C-03(b) sign-off; before it, they are `xfail` with a `C-03(b)` reason string.
- `docs/CONFIDENCE_MODEL_SPEC.md` exists and is linked from `docs/ECDAT_CLI_GUIDE.md`'s scanner section (link added by scanner lane, not CONF).
- `.env.example` contains `SCAN_MIN_CONFIDENCE_BAND=PROBABLE`.
- No file listed in §5.3 has been modified by this branch (`git diff --name-only main | grep -v -F -f .conf-allowlist` returns empty).

---

## 13. Rollback Plan

The feature is designed to be reversible in three tiers depending on where the break appears.

### 13.1 Dashboard build breaks
- Revert `dashboard/src/components/ConfidenceStamp.jsx` to the 2-line TODO stub.
- Revert `dashboard/src/lib/constants.js`, `dashboard/src/mockData.js`, `dashboard/src/pages/DashboardPage/index.jsx` to `main`.
- Backend and DB migrations stay in place — they are additive. Dashboard reads the new fields optionally.

### 13.2 Backend / scan-runner breaks
- Restore the `finding.get("confidence") == "high"` filter in `api/services/scan_runner.py` (one-line revert).
- Set `SCAN_MIN_CONFIDENCE_BAND` to the sentinel `""` and gate the new logic behind `if _MIN_BAND:` so an unset env falls back to legacy behaviour.
- Revert `api/models.py` `FindingOut` field additions and `api/routers/findings.py` `min_band` handling. `confidence` legacy TEXT remains populated (the derived write from `legacy_confidence_for` still runs), so CBOM output and existing consumers keep working.

### 13.3 Scanner emits wrong signals / scorer regression
- Deploy `CONFIDENCE_MODEL_VERSION="conf-1.0.0-hotfix"` alongside a corrected `SIGNAL_WEIGHTS`. Old rows carry `confidence_model_version="conf-1.0.0"`; new rows carry the hotfix version. No schema change.
- If the scorer itself is unsound, disable it engine-side: `python_engine.py` and `multilang_engine.py` fall back to passing `signals=["rule_yaml_matched","call_site_matched"]` unconditionally, which resolves to `PROBABLE`. The legacy `confidence` column keeps writing `"unverified"`, matching current tests' `xfail` state.

### 13.4 DB migration breaks
- Migration is idempotent (`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`). If the initdb order is wrong on a fresh volume, remove the `03_` mount from `docker-compose.yml` and re-run the migration via `psql -f` manually.
- If a column must be removed, ship `db/migrations/002_confidence_scoring_rollback.sql` (`ALTER TABLE findings DROP COLUMN IF EXISTS ...`) — do **not** renumber `002_`; the reserved number stays reserved (C-01).

### 13.5 Contract-violation rollback
- If any file in §5.3 was modified by mistake, revert those files first, then re-run §12.9's `git diff --name-only` allowlist check. AGENT_RULES.md #2 requires flagging a human before proceeding.
