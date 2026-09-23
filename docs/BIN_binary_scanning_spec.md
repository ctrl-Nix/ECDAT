# Binary Scanning (Heuristic) — Implementation Specification

## 1. Header

| Field | Value |
|---|---|
| **Feature name** | Binary scanning (heuristic) |
| **Feature code** | `BIN` (per `SYSTEM_INTERFACE_CONTRACT.md` §0) |
| **Owner** | Scanner lane — binary-scanning sub-owner (reports to Shashank, scanner lane owner of `scanner/cli.py`, `scanner/constants.py`, `scanner/__init__.py`) |
| **Spec version** | v2.0 |
| **Status** | **BLOCKED — implementation-ready, do not merge.** Blocked on open sign-off items **C-20** (is binary scanning in scope at all — `AGENT_RULES.md` #6 says yes, `PRODUCT_DESCRIPTION.md`/`README.md`/`docs/SOURCE_SCANNING_SCOPE.md` say no) and **C-18** (native `lief` parser vs. pure-Python fallback). Per contract §6 Merge Order, Wave 0: *"Human sign-off on C-20 — CNT, BIN, IAC may not start until this resolves."* Coding against this spec (branch work, fixtures, tests) may proceed; merging to `main` may not. |
| **Reviewer sign-off** | ☐ Scanner lane (Shashank) — `scanner/cli.py`, `scanner/constants.py`, `scanner/__init__.py` diffs ☐ DB lane (Ronak) — shared `003_artifact_scanning.sql` PR ☐ CBOM/risk lane (Maitreyi) — evidence/property mapping ☐ Backend lane (Shreyanshi) — `requirements.txt` grouped diff ☐ Product/human sign-off — C-20, C-18 |

**Changelog (v1.0 → v2.0, Step 1 proposal → this spec):**

| Step 1 proposal said | This spec says instead | Why |
|---|---|---|
| Modify `scanner/finding.py` docstring | **Do not touch.** `scanner/finding.py` is **FROZEN**; only CONF may add fields, once (C-03). | Contract ownership tier |
| Add a boolean `--binaries` CLI flag | Add a `binary` value to the shared repeatable `--scan-type {source,dependency,config,binary,container}` flag (§3.5, C-11) | Flag namespace is shared across 4 features |
| Confidence: `high` (tier 1) / `medium` (tier 2) | Confidence: `high` (tier 1) / `unverified` (tier 2) — the two legacy values `scanner/finding.py` already documents | `medium` is not a legal value in the current FROZEN `Finding.confidence` vocabulary; CONF (C-03), not BIN, may introduce a third value |
| Modify `api/services/scan_runner.py` gate as needed | **Do not touch, ever.** `scan_runner.py` is **FROZEN**, owned by CONF (C-02). | Contract ownership tier |
| Modify `api/services/cbom_generator.py` directly | Coordinate with CBOM lane's `build_cbom_from_findings` refactor (C-14); BIN does not edit this file directly | COORDINATED, single refactor owner |
| Assumed a schema change was optional | Schema change is now **mandated and pre-allocated**: `db/migrations/003_artifact_scanning.sql`, shared with DEP/CNT/IAC (§2.1) | Contract reserves this exact migration number |
| Flagged the scope contradiction as an open question | Same conclusion, now formally **C-20**, status **Low confidence, blocking, no resolution proposed** | Confirmed by contract, not resolved by it |
| Assumed no DB schema change ("recommend against dedicated columns in v1") | Explicitly **superseded**: contract's rejected-proposals table (§2.3) notes *"`findings.offset` / `artifact_format` columns — Superseded by `artifact_ref` + `artifact_type`; BIN itself recommended against dedicated columns in v1"* — the contract records and overrides that recommendation. | `artifact_ref`/`artifact_type` are now mandatory, shared columns |

---

## 2. Goal & Context

PS 26164 requires **Discovery** and **Identification** of cryptographic usage; ECDAT currently satisfies both only for source code (Python AST, Java/JS tree-sitter). Compiled artifacts — statically or dynamically linked native binaries — are cryptographic usage ECDAT cannot currently see at all, and PS 26164's discovery requirement does not say "source code only." This feature adds a second-tier, heuristic detection engine that inspects ELF/PE/Mach-O binaries for linked cryptographic symbols (high-confidence, tier 1) and known cryptographic byte constants (lower-confidence, tier 2), emitting the same `Finding` shape every other engine emits so the risk engine, CBOM generator, and dashboard require no engine-specific logic. Whether this work may currently be pitched or merged is a separate, unresolved product question (C-20) that this spec does not decide.

---

## 3. Scope

**In-Scope**
- Detecting cryptographic **linkage** in native ELF, PE, and Mach-O binaries via imported/dynamic symbol tables, needed-library names, and exported symbols (**tier 1**, `detection_method="binary_symbol_table"`, `confidence="high"`).
- Detecting cryptographic **byte-constant presence** (e.g., AES S-box, MD5/SHA initial hash values) in read-only data sections via fixed-signature search (**tier 2**, `detection_method="binary_constant_scan"`, `confidence="unverified"`).
- A new externally loaded rule pack, `scanner/rules/binary.yaml`, following the existing `language:`/`rules:` YAML shape already loaded by `scanner.multilang_engine.load_rules()` (C-26: compatible, reused as-is).
- Emitting `artifact_type="BINARY"` and `artifact_ref="<section>+0x<offset>"` / `"<section>:<symbol>"` per finding, per migration `003_artifact_scanning.sql`.
- One new, additive branch in the shared `--scan-type` flag (`binary`), gated by `SCAN_ENABLE_BINARY`.
- A dedicated scope document, `docs/BINARY_SCANNING_SCOPE.md`, stating detection limits (no obfuscation/packing defeat, no proof of runtime use).

**Out-of-Scope (this feature)**
- Container image / layer scanning (`CNT`'s `scanner/container_engine.py`).
- JAR/`.class` constant-pool parsing (stretch goal, not this spec).
- Any change to `scanner/finding.py`, `api/services/scan_runner.py`, `api/services/risk_engine.py`, or `api/services/cbom_generator.py` internals — all FROZEN or COORDINATED-elsewhere.
- Any rewrite of `PRODUCT_DESCRIPTION.md`, `README.md`, or `ARCHITECTURE.md` §1/§6 — reserved for the single scope-editor pass in Wave 4 (C-19).
- Symbol demangling, disassembly, control-flow analysis, or any claim of runtime reachability.
- Persisting sub-`high`-confidence (tier 2) findings to the database — blocked until CONF's confidence-gate replacement lands (C-02); see §11.

---

## 4. Required Context Files

Exact existing repository paths an implementer must read before writing code, in reading order:

1. `SYSTEM_INTERFACE_CONTRACT.md` — full document; specifically §1.1 (Scanner lane ownership table), §2.1–§2.2 (migration 003), §3.1–3.6 (naming), C-02, C-03, C-11, C-12, C-13, C-14, C-18, C-19, C-20, C-23, C-26, §6 (Merge Order), §7 (Open Items)
2. `AGENT_RULES.md` — all 9 rules, especially #2 (file ownership), #3 (literal interfaces), #4 (stop on ambiguity), #5 (no regex), #6 (current scope list)
3. `ARCHITECTURE.md` — §1 (directory/status table), §2.1 (Scanner → API contract, `Finding` field list), §2.2 (API → DB contract), §6 (Planned Additions, binary/container item)
4. `PRODUCT_DESCRIPTION.md` — §5 (honest build-status table) and §7 (scope-discipline judge talking point) — read-only, to understand why C-20 exists; **do not edit**
5. `db/schema.sql` — current `findings` table definition
6. `db/migrations/001_secure_reporting.sql` — the dual-application pattern (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` in the migration; the same columns inline in `schema.sql`) that migration `003` must follow
7. `scanner/finding.py` — read-only; the FROZEN dataclass this feature must emit unchanged
8. `scanner/constants.py` — `SKIP_DIRS`, `_should_skip()` signature
9. `scanner/cli.py` — `scan()`, `_prepare_findings()`, `_source_context()`, `build_parser()`
10. `scanner/python_engine.py` — `scan_file()`/`scan_directory()` pattern (older, no `rules` param)
11. `scanner/multilang_engine.py` — `scan_file(path, rules_by_lang)`/`scan_directory(target, rules_by_lang)`, `load_rules()` (to be reused, not re-implemented), `EXT_TO_LANG`
12. `scanner/rules/java.yaml` — example of the `language:`/`rules:` YAML shape `load_rules()` expects
13. `scanner/__init__.py` — the guarded try/except export pattern already used for `scan_multilang`
14. `api/services/scan_runner.py` — read-only; understand the `confidence == "high"` gate at the line the contract cites (`api/services/scan_runner.py:103`) — **do not edit**
15. `api/services/cbom_generator.py` — read-only; `_finding_to_component()`, the `additionalContext` free-text pattern being replaced by CBV/CBOM lane (C-14)
16. `docker-compose.yml` — `db` service `volumes:` initdb mount pattern
17. `requirements.txt` — current pins; confirm `cryptography` is absent (C-18) and `lief` is not yet listed
18. `.env.example` — current variable list and grouping
19. `docs/SOURCE_SCANNING_SCOPE.md` — structure/tone template for `docs/BINARY_SCANNING_SCOPE.md`
20. `tests/test_scanner_battle.py` — existing engine test fixture pattern (in-memory source, `tempfile`, decoy/negative tests)
21. `tests/test_scan_runner.py` — the confidence-gate behavior BIN's tier-2 output will run into (C-02)

---

## 5. File Ownership

### SOLE (BIN owns; no other feature may open a PR against these)
| Path | Notes |
|---|---|
| `scanner/binary_engine.py` | new |
| `scanner/rules/binary.yaml` | new |
| `docs/BINARY_SCANNING_SCOPE.md` | new; SOLE per file per §1.5 |
| `tests/test_binary_engine.py` | new |
| `tests/fixtures/binaries/` | new; tiny prebuilt ELF/PE fixtures + a provenance note |

### COORDINATED (BIN proposes a diff; named owner merges/sequences it)
| Path | Owner | BIN's contribution |
|---|---|---|
| `scanner/cli.py` | scanner lane (Shashank) | one additive `elif "binary" in scan_types:` branch, queued behind CLI's Wave-2 introduction of `--scan-type` (C-11) |
| `scanner/constants.py` | scanner lane | add `BINARY_SKIP_DIRS`; contribute to the shared `SCAN_MAX_ARTIFACT_BYTES` constant (C-12) |
| `scanner/__init__.py` | scanner lane | add a guarded `scan_binary` export mirroring the existing `scan_multilang` try/except pattern |
| `db/migrations/003_artifact_scanning.sql` | DB lane (Ronak) | **one shared file/PR** with DEP, CNT, IAC (§2.1) — BIN does not write this file alone |
| `db/schema.sql`, `db/models.py`, `db/crud.py` | DB lane (Ronak) | BIN participates only via the shared 003 PR; no unilateral edits |
| `docker-compose.yml` | deploy lane | the `04_artifact_scanning.sql` initdb mount (matching migration 003's reserved prefix) lands as part of the same shared PR |
| `requirements.txt` | backend lane | BIN's `lief` (or fallback trio) line item enters the single grouped diff (C-18) |
| `.env.example` | deploy lane | `SCAN_ENABLE_BINARY`, contribution to shared `SCAN_MAX_ARTIFACT_BYTES` |
| `dashboard/src/lib/constants.js` | frontend lane | one column-registry entry, added **after** DFS's registry restructure lands (C-13) — not `FindingsTable.jsx` directly |
| `docs/ECDAT_CLI_GUIDE.md` | scanner lane | document `--scan-type binary` usage once `cli.py` change merges |

### FROZEN — must never be touched by this feature
| Path | Owner | Reason |
|---|---|---|
| `scanner/finding.py` | scanner lane | Only CONF may add fields, once (C-03) |
| `api/services/scan_runner.py` | CONF | The confidence gate is CONF's to replace (C-02) |
| `api/services/risk_engine.py` | CBOM/risk lane (Maitreyi) | Sole scoring authority (C-04) |

### Do-not-touch — every other feature's SOLE or FROZEN files
`scanner/dependency_engine.py`, `scanner/dependency_rules/` (DEP) · `scanner/container_engine.py`, `scanner/image_layers.py` (CNT) · `scanner/config_engine.py` (IAC) · `scanner/confidence.py` (CONF) · `scanner/enroll_cli.py` (ENR) · `scanner/ecdat_cli.py`, `pyproject.toml` (CLI) · `scanner/rules/container.yaml` (CNT) · `scanner/rules/config.yaml` (IAC) · `api/routers/auth.py`, `api/core/rbac.py` (RBAC) · `api/routers/agents.py` (ENR) · `api/services/enrollment.py` (ENR) · `api/routers/audit.py`, `api/services/audit.py` (AUD) · `api/routers/triage.py` (TRI) · `api/routers/trends.py` (TRD) · `api/routers/compliance.py` (CMP) · `api/services/cbom_validator.py` (CBV) · `dashboard/src/index.css`, `tailwind.config.js`, `dashboard/public/fonts/` (FE) · `dashboard/src/components/ConfidenceStamp.jsx` (CONF) · `dashboard/src/components/AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `pages/AgentStatusPage/`, `hooks/useAgents.js` (ASP) · `dashboard/src/components/ComplianceReport.jsx` (CMP) · `dashboard/src/components/RiskTrendChart.jsx`, `RiskTierBreakdown.jsx`, `pages/TrendsPage/` (TRD) · `dashboard/src/context/AuthContext.jsx`, `pages/LoginPage/LoginForm.jsx` (RBAC) · `dashboard/src/pages/LandingPage/index.jsx` (frontend lane, sole GSAP consumer) · `dashboard/src/components/FindingsTable.jsx` JSX body (C-13 — additive registry only) · `dashboard/src/lib/api.js`, `dashboard/src/api.js` (frontend lane; the latter is slated for deletion, C-08) · `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml` (INS) · `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md` §1/§6 (single scope editor only, C-19).

---

## 6. Tech Stack & Pinned Versions

| Dependency | Status against `requirements.txt` | Note |
|---|---|---|
| Python 3.11 | Already pinned (`requirements.txt` header comment, `Dockerfile` `FROM python:3.11-slim`) | No change |
| `lief` | **Not present today. Blocked on C-18 sign-off.** Candidate pin: `lief==0.17.3` (current PyPI release; ships `cp311` wheels for `manylinux_2_28`/`musllinux` — verify against `python:3.11-slim`'s glibc before merge, per C-18's requirement that `lief` be wheel-verified) | Native parser on untrusted binary input inside a `cap_drop: [ALL]`, `read_only: true` container (`docker-compose.yml` `backend` service) — this is exactly the security review trigger C-18 names |
| **Fallback if C-18 resolves against `lief`:** `pyelftools>=0.31`, `pefile>=2024.8.26`, `macholib>=1.16.3` | Not present today | Pure-Python, three APIs instead of one, per BIN's own Step 1 fallback proposal, retained here per C-18 |
| `PyYAML` | Already pinned (`PyYAML>=6.0`) | Reused for `binary.yaml`; no version change needed |
| `pytest` | Already pinned (`pytest>=8.0`) | Test framework, unchanged |

No other library is required. Per C-18, the actual choice between `lief` and the pure-Python fallback trio is **not decided by this spec** — see §11, item 5. Whichever is chosen, it enters `requirements.txt` only through the backend lane's single grouped diff (§1.5), never as a standalone BIN edit.

---

## 7. Concrete Interface Definitions

```python
# scanner/binary_engine.py — new file, SOLE ownership: BIN
# Public surface: exactly these two functions, per SYSTEM_INTERFACE_CONTRACT.md §3.1.
# Nothing else from this module may be imported across lanes.

from pathlib import Path
from scanner.finding import Finding


def scan_file(path: Path, rules: dict | None = None) -> list[Finding]: ...


def scan_directory(root: Path, rules: dict | None = None) -> list[Finding]: ...


# Rule loading reuses the existing multilang loader unchanged (C-26: compatible).
from scanner.multilang_engine import load_rules  # noqa: E402


# scanner/constants.py — COORDINATED addition (scanner lane merges), per C-12.
# BINARY_SKIP_DIRS is a NAMED SEPARATE set; SKIP_DIRS (source walk) is unchanged.

BINARY_SKIP_DIRS: set[str] = {
    ".git", "__pycache__", ".pytest_cache", "node_modules",
}

SCAN_MAX_ARTIFACT_BYTES: int = 100 * 1024 * 1024  # shared constant, C-12


# scanner/__init__.py — COORDINATED addition (scanner lane merges).

try:
    from scanner.binary_engine import scan_file as scan_binary
except Exception:  # pragma: no cover - dependency may be absent
    def scan_binary(*args, **kwargs):
        raise RuntimeError("binary scanner unavailable; install lief")
```

```python
# scanner/cli.py — COORDINATED, one additive branch queued behind CLI's
# Wave-2 introduction of the --scan-type flag (C-11). Literal signature of
# the flag as fixed by contract §3.5:
#
#   --scan-type {source,dependency,config,binary,container}   # repeatable; default: source
#
# BIN's branch inside the existing scan() dispatch:

if "binary" in scan_types:
    findings.extend(binary_engine.scan_directory(target, binary_rules))
```

```yaml
# scanner/rules/binary.yaml — new file, SOLE ownership: BIN
# Loaded by the EXISTING scanner.multilang_engine.load_rules() (language: + rules: keys).
language: "binary"
rules:
  - tier: 1
    match_type: "symbol"
    match_pattern: "MD5_Init"
    algorithm: "MD5"
    primitive: "hash"
    library: "OpenSSL/libcrypto"
    weak_by_default: true
    expected_format: ["ELF", "PE", "MachO"]
  - tier: 2
    match_type: "constant"
    match_pattern_hex: "637c777bf26b6fc53001672bfed7ab76"
    algorithm: "AES"
    primitive: "encrypt"
    library: "unknown"
    weak_by_default: false
```

```python
# Literal Finding() construction inside binary_engine.py, per rule tier.
# All field names/types are the FROZEN scanner.finding.Finding shape, unchanged.

Finding(
    file=str(path),
    line=0,
    matched_call=f".dynsym:{symbol_name}",       # tier 1 example
    library=rule["library"],
    algorithm=rule["algorithm"],
    primitive=rule["primitive"],
    language=binary_format.lower(),               # "elf" | "pe" | "macho"
    weak_by_default=rule["weak_by_default"],
    confidence="high",
    key_size=None,
    detection_method="binary_symbol_table",
)

Finding(
    file=str(path),
    line=0,
    matched_call=f".rodata+0x{offset:x}",         # tier 2 example
    library=rule["library"],
    algorithm=rule["algorithm"],
    primitive=rule["primitive"],
    language=binary_format.lower(),
    weak_by_default=rule["weak_by_default"],
    confidence="unverified",
    key_size=None,
    detection_method="binary_constant_scan",
)
```

```python
# scanner/cli.py _prepare_findings() — COORDINATED, additive tagging step
# for binary-origin findings only (does not touch other engines' output):

for finding in raw:
    if finding["detection_method"] in ("binary_symbol_table", "binary_constant_scan"):
        finding["artifact_type"] = "BINARY"
        finding["artifact_ref"] = finding["matched_call"]
```

```sql
-- db/migrations/003_artifact_scanning.sql — COORDINATED, shared PR (DEP+CNT+BIN+IAC)
-- Quoted verbatim from SYSTEM_INTERFACE_CONTRACT.md §2.2. BIN does not author
-- this file alone; reproduced here for interface literalness only.
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
```

```yaml
# docker-compose.yml — COORDINATED, added in the same shared PR as migration 003.
# Reserved compose mount prefix for 003_artifact_scanning.sql is "04_" (contract §2.1).
      - ./db/migrations/003_artifact_scanning.sql:/docker-entrypoint-initdb.d/04_artifact_scanning.sql:ro
```

```bash
# .env.example — COORDINATED addition
SCAN_ENABLE_BINARY=false
SCAN_MAX_ARTIFACT_BYTES=104857600
```

```json
// Example scanner/cli.py stdout element for a binary target (tier 1 + tier 2),
// after risk_engine.score_findings() — JSON array contract unchanged (§3.5).
[
  {
    "file": "libpayments.so",
    "line": 0,
    "matched_call": ".dynsym:MD5_Init",
    "library": "OpenSSL/libcrypto",
    "algorithm": "MD5",
    "primitive": "hash",
    "language": "elf",
    "weak_by_default": true,
    "confidence": "high",
    "key_size": null,
    "detection_method": "binary_symbol_table",
    "artifact_type": "BINARY",
    "artifact_ref": ".dynsym:MD5_Init",
    "source_context": "SOURCE",
    "risk_tier": "CRITICAL",
    "criticality": "MEDIUM"
  }
]
```

---

## 8. Step-by-Step Implementation Plan

1. **`docs/BINARY_SCANNING_SCOPE.md`** — write the scope/limits document (SOLE, no dependency on any other file).
2. **`scanner/rules/binary.yaml`** — author the tier-1/tier-2 rule set (symbols, needed libraries, constants) using the schema in §7.
3. **`scanner/binary_engine.py`** — implement `scan_file`/`scan_directory` per the frozen §3.1 signature, importing `load_rules` from `scanner.multilang_engine` and `Finding` from `scanner.finding` (read-only import, no edits to either file).
4. **`scanner/constants.py`** — submit the `BINARY_SKIP_DIRS` and `SCAN_MAX_ARTIFACT_BYTES` addition to the scanner lane for merge (COORDINATED; do not merge unilaterally).
5. **`scanner/__init__.py`** — submit the guarded `scan_binary` export addition to the scanner lane.
6. **`tests/fixtures/binaries/`** — commit small prebuilt ELF/PE fixtures (a positive fixture per tier, one adversarial "constant-in-a-comment-equivalent" negative fixture) with a provenance note (how each was built, from what source, with what toolchain).
7. **`tests/test_binary_engine.py`** — unit tests against the fixtures: tier-1 symbol hit, tier-2 constant hit, decoy/negative case, unsupported-format case, oversized-file case (`SCAN_MAX_ARTIFACT_BYTES`).
8. **`scanner/cli.py`** — submit the additive `elif "binary" in scan_types:` branch and the `_prepare_findings()` artifact tagging step to the scanner lane, queued **after** the CLI feature's Wave-2 `--scan-type` flag has merged (C-11); do not introduce the flag itself.
9. **`docs/ECDAT_CLI_GUIDE.md`** — submit a documentation addition for `--scan-type binary` and `SCAN_ENABLE_BINARY` to the scanner lane.
10. **`requirements.txt`** — submit the `lief` (or fallback trio) line item to the backend lane's single grouped diff, contingent on C-18 sign-off.
11. **`db/migrations/003_artifact_scanning.sql`, `db/schema.sql`, `db/models.py`, `db/crud.py`, `docker-compose.yml`** — submit BIN's needs (the `BINARY` artifact type, the `<section>+0x<offset>` / `<section>:<symbol>` `artifact_ref` convention) to the DB lane's shared PR with DEP/CNT/IAC; do not author these files independently.
12. **`.env.example`** — submit `SCAN_ENABLE_BINARY` and the shared `SCAN_MAX_ARTIFACT_BYTES` entry to the deploy lane.
13. **`dashboard/src/lib/constants.js`** — submit one column-registry entry for `artifact_ref`/`line=0→—` display, only after DFS's registry restructure of `FindingsTable.jsx` has landed (C-13); do not edit `FindingsTable.jsx` directly.
14. **Human sign-off gate** — do not merge steps 8, 10, 11, 12, 13 to `main` until C-20 (scope) and C-18 (lief) are resolved.

---

## 9. Naming & Symbol Registry

| Symbol | Kind | Value / Signature | Collision check |
|---|---|---|---|
| `scanner.binary_engine.scan_file` | function | `scan_file(path: Path, rules: dict \| None = None) -> list[Finding]` | Matches §3.1 frozen engine pair exactly; no collision |
| `scanner.binary_engine.scan_directory` | function | `scan_directory(root: Path, rules: dict \| None = None) -> list[Finding]` | Same |
| `scanner.binary_engine.load_rules` | — | **Not defined here.** Imported from `scanner.multilang_engine.load_rules` | Avoids a second, divergent loader (C-26) |
| `scanner.constants.BINARY_SKIP_DIRS` | constant | `set[str]` | New name, does not collide with existing `SKIP_DIRS`; matches C-12's exact naming |
| `scanner.constants.SCAN_MAX_ARTIFACT_BYTES` | constant | `int` | **Shared** with CNT/IAC per C-12 — first feature to land it wins; others must import, not redefine |
| `scanner.__init__.scan_binary` | function alias | guarded import of `binary_engine.scan_file` | Mirrors `scan_multilang`; no collision |
| `binary_symbol_table` | `detection_method` value | tier 1 | From the FROZEN registry §3.2 exactly — must not be renamed |
| `binary_constant_scan` | `detection_method` value | tier 2 | From the FROZEN registry §3.2 exactly — must not be renamed |
| `SCAN_ENABLE_BINARY` | env var | boolean, default `false` | Explicitly listed under the `SCAN_` prefix in §3.3 as owned by "scanner lanes" — reserved for this purpose |
| `--scan-type binary` | CLI flag value | one value of the shared repeatable enum | Defined by §3.5; BIN does not introduce the flag, only this value |
| `findings.artifact_type = 'BINARY'` | DB value | one value of the shared `artifact_type` tuple | Defined by migration 003 exactly |
| `db/models.py` `ARTIFACT_TYPES` tuple | module constant (DB lane's, not BIN's) | `("SOURCE_FILE","DEPENDENCY_MANIFEST","CONFIG_FILE","BINARY","CONTAINER_LAYER")` | Per §3.8 (value sets as TEXT + tuple); DB lane authors this in the shared PR — listed here for BIN's verification only |

No new PascalCase functions, no `/api/v1` routes, no new single-letter CLI flags, no new confidence-string values, no new Postgres `ENUM` — all consistent with §3.1–§3.8.

---

## 10. Known Cross-Feature Risks

Pulled directly from the contract; resolutions are as decided there, not re-derived here.

- **C-02** (`api/services/scan_runner.py` drops every non-`"high"` finding): *"DEP, CNT, BIN and IAC must not edit this file; they depend on CONF landing first. Until it does, they are CLI-only features and must say so in their scope docs."* → `docs/BINARY_SCANNING_SCOPE.md` must state that tier-2 (`confidence="unverified"`) findings print in CLI/JSON output but do not persist to the database until CONF's confidence-gate replacement (`SCAN_MIN_CONFIDENCE_BAND`) merges. Per §6 Merge Order, CONF phase 1 is Wave 1 and BIN is Wave 3, so this should already be resolved by the time BIN merges — but BIN must not assume this and must not touch the gate itself.
- **C-03** (four incompatible confidence vocabularies): resolution is CONF's two-field model; BIN keeps emitting the existing `high`/`unverified` legacy values unchanged and takes no action on backfill, test breakage, or the demo baseline — those are explicitly CONF's open items, not BIN's.
- **C-11** (`scanner/cli.py` flag namespace collision): resolved to one repeatable `--scan-type` flag, default `source`; BIN adds a value, not a flag.
- **C-12** (`scanner/constants.py` skip-list conflict): resolved — `SKIP_DIRS` (source) stays untouched; BIN adds its own `BINARY_SKIP_DIRS` and shares `SCAN_MAX_ARTIFACT_BYTES` with CNT/IAC without mutating their sets.
- **C-13** (`FindingsTable.jsx` edited by seven features): resolved — BIN adds a `dashboard/src/lib/constants.js` registry entry only, after DFS's restructure; `line=0` renders as `—`, never `0`.
- **C-14** (`cbom_generator.py` pulled six ways): resolved — one refactor by the CBOM lane (`build_cbom_from_findings`); BIN's only requirement is that its findings carry `detection_method` and a non-zero-implying `artifact_ref`, consumed via the shared `ecdat:detection_method` / `ecdat:artifact_type` property-key registry, not free-text `additionalContext`.
- **C-18** (`lief` vs. pure-Python fallback): **unresolved**, Medium confidence, explicitly blocks BIN. See §11.
- **C-19** (scope-honesty docs rewritten five times): resolved to a single scope-editor pass in Wave 4; BIN authors only its own `docs/BINARY_SCANNING_SCOPE.md` and must not touch `PRODUCT_DESCRIPTION.md`/`README.md`/`ARCHITECTURE.md`.
- **C-20** (is binary scanning in scope at all): **unresolved**, Low confidence, explicitly blocking. See §11.
- **C-23** (DEP/CNT/BIN will report the same library three times): resolved — the three findings are retained as distinct evidence, not merged, keyed on `(artifact_type, artifact_ref, package_ecosystem, package_name, package_version, algorithm)`; dashboard-side grouping is an open question (see §11) but not BIN's to answer alone.
- **C-26** (compatible items): the `Finding` dataclass shape and the `scanner/rules/*.yaml` loader are both explicitly confirmed compatible/reusable — BIN's design leans on both without modification.

---

## 11. Pre-Answered Ambiguities

1. **If a binary is larger than `SCAN_MAX_ARTIFACT_BYTES`,** skip it, emit a `[warn]` line to stderr (matching the existing `scanner/python_engine.py` warn-and-continue pattern), and do not raise — a single oversized artifact must not abort a whole-directory scan.
2. **If `lief` (or the fallback library) fails to parse a file** (corrupt, truncated, unsupported sub-format), catch the exception, emit a `[warn]` to stderr with the filename, and return an empty finding list for that file — never let one bad binary crash `scanner/cli.py`'s subprocess (which `api/services/scan_runner.py` invokes with a 300 s hard timeout it also cannot be changed to accommodate).
3. **If a tier-2 byte-constant match falls inside a section also carrying a tier-1 symbol hit for the same algorithm** (e.g., `.dynsym:MD5_Init` and an MD5 constant both present), emit **both** findings rather than deduplicating — they are different evidence types (`binary_symbol_table` vs. `binary_constant_scan`) and C-23's resolution explicitly preserves distinct evidence rather than merging at write time.
4. **If the target directory mixes source files and binaries in one scan** (a realistic case, since `scans.scan_context` already supports a single scan mixing artefact types per migration 003's comment), run whichever engines correspond to the requested `--scan-type` values against the same tree; do not require separate invocations.
5. **If `--scan-type binary` is passed but `SCAN_ENABLE_BINARY=false`,** treat this as a configuration error: print an explicit stderr message and exit 1 (not exit 2, since this is not a policy violation) — never silently ignore the requested engine.
6. **If a linked shared library's ecosystem cannot be classified** into the existing `package_ecosystem` value set (`pypi | npm | maven | deb | apk | rpm` — none of which fit a native `.so`/`.dll` linkage): **the contract does not cover this.** Leave `package_ecosystem` and `package_version` as `NULL`, populate only `package_name` (canonical library name, e.g. `"openssl"`) when confidently parseable from the SONAME, and flag to the DB/CBOM lanes whether a new ecosystem value (e.g. `"native"`) should be added to that tuple. Do not invent and ship a new value unilaterally.
7. **C-18 open item (blocks this feature):** whether `binary_engine.py` uses `lief` or the pure-Python `pyelftools`/`pefile`/`macholib` trio is a security-review call on native parsing inside a `cap_drop: [ALL]`, `read_only: true` container. **Not resolved here.** Implementer should build against the frozen `scan_file`/`scan_directory` interface so either backend can be swapped in without touching any caller.
8. **C-20 open item (blocks this feature):** whether binary scanning is in scope at all is contradicted between `AGENT_RULES.md` #6 (yes) and the pitch documents (no, deliberate differentiator). **Not resolved here**, per the contract's own note that this "is not resolvable by an integration architect." This spec exists so implementation can proceed the moment sign-off lands, per AGENT_RULES.md #4 ("stop and ask a human," not guess).
9. **Dashboard grouping of duplicate package evidence (C-23's own open sub-question):** whether DEP/CNT/BIN findings for the same library are grouped or listed in the UI, and whether a grouped row takes the maximum risk tier, is unresolved and is a frontend/DFS decision, not BIN's.

---

## 12. Test Plan / Definition of Done

```bash
# Unit tests for the new engine (once fixtures + binary_engine.py exist)
pytest tests/test_binary_engine.py -v
# Expected: all tests pass. At minimum:
#   test_tier1_symbol_hit_high_confidence        -> 1 Finding, confidence="high", detection_method="binary_symbol_table"
#   test_tier2_constant_hit_unverified_confidence -> 1 Finding, confidence="unverified", detection_method="binary_constant_scan"
#   test_no_finding_on_unrelated_binary           -> 0 findings (decoy/negative case)
#   test_unsupported_format_returns_empty_list    -> 0 findings, no exception
#   test_oversized_file_is_skipped                -> 0 findings, one stderr [warn] line

# Full existing suite must still pass unmodified (BIN touches no FROZEN file)
pytest tests/ -v
# Expected: no regressions in test_scan_runner.py, test_scanner_battle.py,
# test_cli_secure.py, test_crud.py, test_realworld_source_scanner.py.

# CLI smoke test against a fixture binary, engine gated behind SCAN_ENABLE_BINARY
SCAN_ENABLE_BINARY=true python -m scanner.cli tests/fixtures/binaries --scan-type binary
# Expected: JSON array on stdout containing the fixture's known finding(s),
# each with artifact_type="BINARY" and a non-null artifact_ref; exit code 0
# (or 2 only if a --fail-on threshold is also passed and met).

# Confirm the confidence-gate interaction (documents current, pre-CONF behavior)
python -m scanner.cli tests/fixtures/binaries --scan-type binary --json-out /tmp/out.json
# Expected: tier-1 ("high") findings appear in /tmp/out.json; if scan_runner.py
# is invoked downstream (not this CLI path) before CONF lands, tier-2
# ("unverified") findings will not appear in the database — this is the
# documented, accepted C-02 behavior, not a bug to fix here.
```

**Definition of Done:**
- [ ] `scanner/binary_engine.py` exposes exactly `scan_file`/`scan_directory` with the frozen signature; no other public symbol.
- [ ] `scanner/rules/binary.yaml` loads via the unmodified `scanner.multilang_engine.load_rules()`.
- [ ] All tests in §12 pass; no existing test file is modified.
- [ ] `docs/BINARY_SCANNING_SCOPE.md` states the tier-2/persistence limitation from C-02 explicitly.
- [ ] `scanner/finding.py`, `api/services/scan_runner.py`, `api/services/risk_engine.py` show zero diff.
- [ ] All COORDINATED-file diffs are submitted as separate PRs to their named lane owners, not merged directly by this feature.
- [ ] C-20 and C-18 sign-off recorded before any COORDINATED PR is merged to `main`.

---

## 13. Rollback Plan

- **Scanner-side (`scanner/binary_engine.py`, `scanner/rules/binary.yaml`, tests, docs):** all new, additive files with no callers outside the guarded `scanner/__init__.py` try/except. Revert by deleting these files and the `scan_binary` export line; nothing else in the scanner package depends on them, since `scan_binary` is never imported by `python_engine.py` or `multilang_engine.py`.
- **`scanner/cli.py` branch:** additive `elif` inside `scan()`; revert by removing that one branch. Because `--scan-type` defaults to `source` only (C-11), removing the branch cannot affect any existing CI gate, the `--fail-on HIGH` policy, or the 18-finding demo baseline — no other scan type is touched.
- **`scanner/constants.py` addition:** `BINARY_SKIP_DIRS` and `SCAN_MAX_ARTIFACT_BYTES` are new names; revert by deleting them, provided no other merged feature (CNT/IAC) has taken a dependency on `SCAN_MAX_ARTIFACT_BYTES` in the interim — check for that import before removing.
- **Database (`db/migrations/003_artifact_scanning.sql` + `db/schema.sql`):** all additions are `ADD COLUMN IF NOT EXISTS` with safe defaults (`artifact_type` defaults to `'SOURCE_FILE'`) and nullable otherwise — rollback is `ALTER TABLE findings DROP COLUMN IF EXISTS artifact_type, DROP COLUMN IF EXISTS artifact_ref, ...` for a genuinely broken deploy, but since this migration is **shared** with DEP/CNT/IAC, rolling it back rolls back all four features simultaneously — coordinate with the DB lane before doing so rather than dropping columns unilaterally.
- **`docker-compose.yml` mount:** remove the single `04_artifact_scanning.sql` line; fresh volumes are unaffected since `db/schema.sql` is the source of truth for them, and existing volumes simply stop receiving that migration on next `up`.
- **`requirements.txt`:** remove the `lief` (or fallback trio) line from the backend lane's grouped diff; no other code imports it outside `scanner/binary_engine.py`, so removal cannot break another feature's import.
- **Dashboard registry entry:** delete the single `dashboard/src/lib/constants.js` entry; `FindingsTable.jsx` was never edited directly, so no JSX rollback is needed.
- **If the break is discovered post-merge and the cause is unclear,** the safe first action is `SCAN_ENABLE_BINARY=false` (already the default) — this fully disables the new code path without requiring a code revert, since the CLI branch is unreachable when the flag is off.
