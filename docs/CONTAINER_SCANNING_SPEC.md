# ECDAT Feature Specification — Container Image Scanning

## 1. Header

| Field | Value |
|---|---|
| **Feature** | Container Image Scanning |
| **Feature code** | `CNT` (per `SYSTEM_INTERFACE_CONTRACT.md` §0) |
| **Owner lane** | Scanner lane (engine + rules); shares migration 003 with `DEP` / `BIN` / `IAC` |
| **Spec version** | v1.0 |
| **Status** | **Blocked — cannot start** until human sign-off on contract open item C-20 (scope truth: `AGENT_RULES.md` #6 says in scope; `PRODUCT_DESCRIPTION.md` §5, `README.md`, `docs/SOURCE_SCANNING_SCOPE.md` say out of scope). Per `AGENT_RULES.md` #4, do not guess. |
| **Reviewer sign-off** | ☐ Scanner lane (Shashank) · ☐ DB lane (Ronak) · ☐ Backend lane (Shreyanshi) · ☐ CBOM/risk lane (Maitreyi) · ☐ Deploy/frontend lane (Karan) · ☐ Human sign-off on C-20 · ☐ Human sign-off on C-02 (persist vs drop sub-threshold) |

### Changelog / deviations from the Step 1 proposal

The Step 1 initial-analysis proposal is overridden by the contract in the following places. The contract wins.

| Step 1 said | Contract says | Applied |
|---|---|---|
| Create `db/migrations/002_container_scanning.sql` | `002_confidence_scoring.sql` is CONF's; CNT participates in the shared `003_artifact_scanning.sql` (DEP + CNT + BIN + IAC, **one file, one PR**) — §2.1 | Use `db/migrations/003_artifact_scanning.sql`, compose mount prefix `04_` |
| Modify `api/services/scan_runner.py` (the `"high"` filter) | `scan_runner.py` is **FROZEN** for CONF; DEP/CNT/BIN/IAC must not touch it (§1.2, C-02) | Do not touch. CNT is CLI-only until CONF lands. |
| Modify `api/services/cbom_generator.py` for certificate/`related-crypto-material` branch | `cbom_generator.py` is COORDINATED by CBOM lane; one refactor to `build_cbom_from_findings(...)` lands **before** CNT (C-14, Wave 1) | Do not modify. Emit fields the refactored generator already reads. |
| Modify `api/services/risk_engine.py` for parsed-certificate key sizes | `risk_engine.py` is **FROZEN**; TRD/CMP/CNT are read-side consumers (C-04) | Do not modify. Emit `key_size` on the `Finding`; risk engine scores it. |
| Modify `api/models.py`, `api/routers/scans.py`, dashboard `FindingsTable.jsx` / `constants.js` | All COORDINATED, owned by other lanes; CNT gets no direct writes (§1.2, §1.4, C-13) | Do not modify. Column display lands via DFS's shared registry after DFS restructures the table. |
| Add new columns `image_digest`, `layer_digest` unilaterally | Those columns exist in the shared migration 003 diff and are written by whichever engine populates them (§2.2, C-23) | Write them; do not add new ones. |
| `source_context` gains a container value | `source_context` **keeps its existing meaning** (`SOURCE`/`TEST_ONLY`/`DEMO_ONLY`); artefact type moves to new `artifact_type` column (§2.2) | Use `artifact_type = 'CONTAINER_LAYER'`. |
| `detection_method` free-string | `detection_method` is a **FROZEN registry** (§3.2); CNT emits exactly `certificate_parse` and `container_package_inventory` | Registry values only. |
| New env var e.g. `ECDAT_CONTAINER_*` | Reserved prefix is `SCAN_` (§3.3) | `SCAN_ENABLE_CONTAINER`, `SCAN_MAX_ARTIFACT_BYTES`, `SCAN_IMAGE_TAR_PATH`. |
| Rule #5 (`AGENT_RULES.md`) applies to source-code scanning: no regex there. `container.yaml` package-name matching is not source-code scanning. Certificate parsing uses the `cryptography` library, not regex. | Same. | Explicit non-use of regex called out in §11. |

---

## 2. Goal & Context

Container image scanning discovers cryptographic assets — X.509 certificates, private keys, TLS-config material, and installed crypto library packages — inside a locally available OCI image tarball, and emits them as `Finding` records that flow through the same risk-scoring, CBOM-generation, and dashboard pipeline as source-code findings. This directly addresses **PS 26164 requirement 1 (Discovery)** by extending inventory beyond source files to deployed artefacts, and **PS 26164 requirement 3 (Cataloguing)** by populating the `related-crypto-material` component branch of the CycloneDX 1.6 CBOM that source-code detection cannot produce. The judge-facing consequence is that ECDAT can honestly answer "where does RSA-1024 live in what you actually ship" and not only "where does RSA-1024 appear in your `.py` files" — the exact gap `PRODUCT_DESCRIPTION.md` §1 names as unaddressed by existing tooling. The feature must never mount `/var/run/docker.sock` or reach a registry; the "data never leaves your network" claim in `PRODUCT_DESCRIPTION.md` §2 is load-bearing.

---

## 3. Scope

### In-scope

- Accepting an OCI image as either a `docker save` tarball (`.tar`) or an OCI image-layout directory, supplied via a local path.
- Parsing `manifest.json` / `index.json` / `config.json` per the OCI Image Layout spec.
- Extracting layer tarballs, resolving whiteout (`.wh.` and `.wh..wh..opq`) files to arrive at the effective filesystem view.
- Detector 1 — **certificate parsing** (`detection_method = "certificate_parse"`): PEM and DER X.509 certificates and PKCS#8/PKCS#1 private-key files anywhere on the extracted filesystem. Extracts signature algorithm, public-key algorithm, key size, and subject.
- Detector 2 — **package inventory** (`detection_method = "container_package_inventory"`): parsing `var/lib/dpkg/status`, `lib/apk/db/installed`, `var/lib/rpm/Packages*` (metadata only), and language-level `package-lock.json` / `requirements.txt` / JAR `META-INF/MANIFEST.MF` files, matched against `scanner/rules/container.yaml`.
- Emission of the standard `Finding` dataclass unchanged in shape (contract §1.1 declares `scanner/finding.py` **FROZEN**; only CONF may add fields).
- Populating `artifact_type`, `artifact_ref`, `image_digest`, `layer_digest`, `package_ecosystem`, `package_name`, `package_version` from migration 003.
- CLI: `ecdat scan --scan-type container --image-tar PATH`.
- New scope doc `docs/CONTAINER_SCANNING_SCOPE.md`.

### Out-of-scope

- Docker socket access, `docker`/`podman` CLI invocation, registry pulls, `skopeo`, and anything requiring network egress.
- Native-binary parsing inside layers (ELF/PE/Mach-O linked-library extraction) — that is `BIN`'s feature.
- Dependency-manifest scanning as a top-level scan target — that is `DEP`'s feature. CNT reads manifests only when they are already on an extracted image layer.
- Config/IaC parsing — that is `IAC`'s feature.
- Re-invoking `python_engine` / `multilang_engine` over source files found inside layers. (Considered in Step 1; removed here because the confidence gate C-02 is not yet resolved and mixing two `artifact_type` values from one detector complicates C-23 de-duplication.)
- Editing `api/services/scan_runner.py`, `api/services/cbom_generator.py`, `api/services/risk_engine.py`, `api/models.py`, `dashboard/**` (contract-FROZEN or contract-COORDINATED under other lanes).
- Editing `PRODUCT_DESCRIPTION.md`, `ARCHITECTURE.md`, `README.md` (single scope-editor pass, C-19).
- Adding native binary-parsing dependencies (`lief`) — C-18 leaves that open for `BIN`.

---

## 4. Required Context Files

The implementing agent must open and read these before writing any code (paths verified against the attached repo and the contract's Canonical File Ownership Map, §1):

- `SYSTEM_INTERFACE_CONTRACT.md` (this contract — sections 1, 2, 3, 4 C-01/C-02/C-03/C-11/C-12/C-14/C-18/C-19/C-20/C-23, 5, 6)
- `AGENT_RULES.md`
- `ARCHITECTURE.md`
- `PRODUCT_DESCRIPTION.md`
- `docs/SOURCE_SCANNING_SCOPE.md` (mirror its non-claims tone)
- `docs/RISK_ENGINE_SPEC.md`
- `docs/ECDAT_CLI_GUIDE.md`
- `scanner/finding.py`
- `scanner/cli.py`
- `scanner/constants.py`
- `scanner/multilang_engine.py` (only for the `load_rules` YAML loader shape and the `scan_file` / `scan_directory` signature contract at lines 563 and 710)
- `scanner/python_engine.py` (only for the `scan_file` / `scan_directory` signature at lines 206 and 227)
- `scanner/rules/java.yaml`, `scanner/rules/javascript.yaml` (YAML shape reference)
- `db/schema.sql`
- `db/models.py`
- `db/crud.py` (read `save_findings` and `_save_risk_assessment` to see which finding-dict keys flow to which column)
- `db/migrations/001_secure_reporting.sql` (idempotency pattern reference)
- `api/services/scan_runner.py` (**read-only** — to see the filter at line 103 that CONF replaces per C-02; do not modify)
- `api/services/cbom_generator.py` (**read-only** — to see the `_PRIMITIVE_MAP` the CBOM lane will extend)
- `api/services/risk_engine.py` (**read-only** — to see which finding-dict keys drive scoring)
- `docker-compose.yml`
- `Dockerfile`
- `.github/workflows/ecdat-scan.yml`
- `requirements.txt`

---

## 5. File Ownership

### 5.1 SOLE (this feature owns; no other feature may open a PR against them)

- `scanner/container_engine.py` — new
- `scanner/image_layers.py` — new
- `scanner/rules/container.yaml` — new
- `docs/CONTAINER_SCANNING_SCOPE.md` — new
- `tests/test_container_engine.py` — new
- `tests/fixtures/container/` — new (small synthetic image tarball fixtures)

### 5.2 COORDINATED (this feature edits; another lane merges)

- `scanner/cli.py` — scanner lane (Shashank) integrates; CNT contributes the `--image-tar` handling under the shared `--scan-type` grammar defined in C-11. Merges **after** CLI wave (Wave 2).
- `scanner/constants.py` — scanner lane; CNT adds the new **named** set `CONTAINER_LAYER_SKIP_PATHS` and contributes to shared `SCAN_MAX_ARTIFACT_BYTES` (§C-12). CNT does not touch `SKIP_DIRS`, `BINARY_SKIP_DIRS`, or `CONFIG_FILE_PATTERNS`.
- `scanner/__init__.py` — scanner lane; add one entry-point export for `container_engine`.
- `db/migrations/003_artifact_scanning.sql` — **one file, one PR, four owners** (DEP + CNT + BIN + IAC). CNT contributes the container-specific columns already listed in §2.2 of the contract; the file is written once and merged once.
- `db/schema.sql` — DB lane (Ronak); same additive diff as migration 003, in the same PR.
- `db/models.py` — DB lane; adds the columns as SQLAlchemy attributes and the value tuple `ARTIFACT_TYPES = ("SOURCE_FILE","DEPENDENCY_MANIFEST","CONFIG_FILE","BINARY","CONTAINER_LAYER")` per §3.8.
- `db/crud.py` — DB lane; extends `save_finding` to persist the new dict keys. CNT provides the exact key list.
- `docker-compose.yml` — deploy lane (Karan); adds the migration 003 mount (`./db/migrations/003_artifact_scanning.sql:/docker-entrypoint-initdb.d/04_artifact_scanning.sql:ro`) and a documented read-only bind mount comment for image tarballs.
- `Dockerfile` — deploy lane; no functional change beyond a documented `VOLUME`-style comment (image tarballs are passed via `-v` at runtime).
- `.github/workflows/ecdat-scan.yml` — CI lane; add a smoke job that scans a fixture image tarball.
- `.env.example` — deploy lane; add `SCAN_ENABLE_CONTAINER`, `SCAN_MAX_ARTIFACT_BYTES`, `SCAN_IMAGE_TAR_PATH` under §3.3.
- `docs/ECDAT_CLI_GUIDE.md` — scanner lane; add the `--scan-type container` section.
- `requirements.txt` — backend lane; adds nothing new for CNT (`cryptography` is pinned in Wave 0 per C-18 for the pre-existing report-bundle defect and is reused here).

### 5.3 FROZEN or SOLE elsewhere — do not touch

| Path | Owner / Tier | Reason |
|---|---|---|
| `scanner/finding.py` | FROZEN (only CONF, once) | C-03 |
| `api/services/scan_runner.py` | FROZEN (CONF) | C-02 |
| `api/services/risk_engine.py` | FROZEN (CBOM/risk lane) | C-04 |
| `api/services/cbom_generator.py` | COORDINATED under CBOM lane | C-14 |
| `api/models.py` | COORDINATED under backend lane | §1.2 |
| `api/routers/scans.py`, `findings.py`, `cbom.py`, `remediation.py`, `report_sync.py` | COORDINATED under backend lane | §1.2 |
| `api/core/security.py`, `api/core/config.py`, `api/main.py` | COORDINATED under backend lane | C-09 |
| `dashboard/**` (all) | Frontend lane; DFS restructures `FindingsTable` first | C-13 |
| `dashboard/src/api.js` | Marked for deletion by frontend lane (C-08) | do not resurrect |
| `scanner/python_engine.py`, `scanner/multilang_engine.py` | COORDINATED under scanner lane; CONF removes the hardcoded `"high"` | do not touch |
| `scanner/dependency_engine.py`, `scanner/binary_engine.py`, `scanner/config_engine.py`, `scanner/confidence.py`, `scanner/enroll_cli.py`, `scanner/ecdat_cli.py` | SOLE elsewhere | §1.1 |
| `scanner/rules/binary.yaml`, `scanner/rules/config.yaml`, `scanner/dependency_rules/` | SOLE elsewhere | §1.1 |
| `api/routers/auth.py`, `api/routers/agents.py`, `api/routers/audit.py`, `api/routers/triage.py`, `api/routers/trends.py`, `api/routers/compliance.py`, `api/services/enrollment.py`, `api/services/audit.py`, `api/services/cbom_validator.py`, `api/core/rbac.py`, `api/core/params.py` | SOLE elsewhere | §1.2 |
| `db/migrations/002_`, `004_`, `005_`, `006_`, `007_`, `008_` | SOLE per file | §2.1 |
| `dashboard/src/index.css`, `tailwind.config.js`, `dashboard/public/fonts/` | SOLE FE | §1.4, C-07, C-25 |
| `dashboard/src/components/ConfidenceStamp.jsx`, `AgentStatusTable.jsx`, `AgentStatusCard.jsx`, `ComplianceReport.jsx`, `RiskTrendChart.jsx`, `RiskTierBreakdown.jsx` | SOLE elsewhere | §1.4 |
| `dashboard/src/pages/AgentStatusPage/`, `TrendsPage/`, `LoginPage/LoginForm.jsx`, `LandingPage/index.jsx` | SOLE elsewhere | §1.4 |
| `dashboard/src/context/AuthContext.jsx` | SOLE RBAC | §1.4 |
| `dashboard/src/components/FindingsTable.jsx`, `lib/api.js`, `lib/constants.js`, `pages/DashboardPage/index.jsx`, `App.jsx`, `mockData.js` | COORDINATED elsewhere | §1.4, C-13 |
| `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml` | SOLE INS | §1.5 |
| `PRODUCT_DESCRIPTION.md`, `README.md`, `ARCHITECTURE.md` | Single scope-editor pass | C-19 |
| Any `tests/test_*.py` outside `test_container_engine.py` | COORDINATED under owning lane | §1.5 |

---

## 6. Tech Stack & Pinned Versions

Checked against `requirements.txt` as attached.

| Library | Version | Status | Why |
|---|---|---|---|
| Python | 3.11 (`python:3.11-slim`) | Existing | `tree-sitter-languages` constraint |
| `cryptography` | `>=42.0,<44.0` | **Pinned in Wave 0 per C-18** (independent of CNT; also covers the pre-existing `api/services/report_bundle.py` Ed25519 defect) | X.509/PEM/DER parsing for certificate detector |
| `PyYAML` | `>=6.0` | Existing | `scanner/rules/container.yaml` load |
| `tree-sitter` | `0.21.3` | Existing | untouched |
| `tree-sitter-languages` | `1.10.2` | Existing | untouched |
| stdlib `tarfile`, `hashlib`, `json`, `pathlib`, `io`, `email.parser` (for `MANIFEST.MF` and `dpkg/status` RFC-822-style parsing), `configparser` (apk), `struct` (RPM header) | — | Stdlib | Layer unpack, digests, manifest parsing — **no regex used for source-code scanning per `AGENT_RULES.md` #5**; `container.yaml` package-name matching is not source-code scanning and uses exact string / substring equality on parsed field values, not regex |

Deliberately **not added**:

- `docker` SDK (would imply socket access — contract §C-20 context)
- Registry clients (`skopeo`, `oras`, `containerd`) (offline-only)
- `syft`, `trivy` subprocess (out-of-network + duplicates `DEP`/`BIN`)
- `python-rpm` (native library; RPM header parsing done with stdlib `struct` reads on the header index for package name + version only)
- `lief` (C-18 leaves this open for `BIN`; CNT does not need it)

---

## 7. Concrete Interface Definitions

### 7.1 `scanner/image_layers.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class ExtractedLayer:
    image_digest: str
    layer_digest: str
    layer_index: int
    root: Path
    size_bytes: int


@dataclass(frozen=True)
class ExtractedImage:
    image_digest: str
    layers: tuple[ExtractedLayer, ...]
    merged_root: Path


class ImageLayoutError(ValueError):
    pass


class ImageSizeLimitExceeded(ImageLayoutError):
    pass


def open_image(image_path: Path, *, max_bytes: int) -> ExtractedImage: ...


def iter_files(image: ExtractedImage) -> Iterator[tuple[ExtractedLayer, Path]]: ...


def cleanup(image: ExtractedImage) -> None: ...
```

### 7.2 `scanner/container_engine.py`

```python
from __future__ import annotations

from pathlib import Path

from scanner.finding import Finding


def load_rules(rules_dir: Path) -> dict: ...


def scan_file(path: Path, rules: dict | None = None) -> list[Finding]: ...


def scan_directory(root: Path, rules: dict | None = None) -> list[Finding]: ...


def scan_image_tar(
    image_tar: Path,
    rules: dict | None = None,
    *,
    max_bytes: int,
) -> list[Finding]: ...


def scan_oci_layout(
    layout_dir: Path,
    rules: dict | None = None,
    *,
    max_bytes: int,
) -> list[Finding]: ...
```

Finding-dict keys populated by this engine (in addition to the frozen `Finding` fields — see `scanner/finding.py`):

```
detection_method  ∈ {"certificate_parse", "container_package_inventory"}
artifact_type     = "CONTAINER_LAYER"
artifact_ref      = "<layer_digest>:<in-layer path>"
image_digest      = "sha256:..."
layer_digest      = "sha256:..."
package_ecosystem ∈ {"deb", "apk", "rpm", "pypi", "npm", "maven"}  # container_package_inventory only, else NULL
package_name      = str                                             # container_package_inventory only, else NULL
package_version   = str                                             # container_package_inventory only, else NULL
```

### 7.3 `scanner/rules/container.yaml`

```yaml
schema: 1
description: "Container package-inventory rules — maps installed packages to crypto library assets."
rules:
  - ecosystem: deb
    package: libssl3
    library: openssl
    algorithm: RSA
    primitive: publicKeyEncryption
    weak_by_default: false
  - ecosystem: apk
    package: libcrypto3
    library: openssl
    algorithm: RSA
    primitive: publicKeyEncryption
    weak_by_default: false
  - ecosystem: deb
    package: libgcrypt20
    library: libgcrypt
    algorithm: RSA
    primitive: publicKeyEncryption
    weak_by_default: false
  # ... additional entries in the same shape ...
```

### 7.4 `db/migrations/003_artifact_scanning.sql` — CNT-owned lines only

The full file is authored jointly by DEP + CNT + BIN + IAC per C-01. The literal SQL is taken verbatim from `SYSTEM_INTERFACE_CONTRACT.md` §2.2:

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
```

The identical additive diff lands in `db/schema.sql` in the same PR (§2, C-01), and the mount is added to `docker-compose.yml`:

```yaml
      - ./db/migrations/003_artifact_scanning.sql:/docker-entrypoint-initdb.d/04_artifact_scanning.sql:ro
```

### 7.5 `scanner/cli.py` — additions

```python
parser.add_argument(
    "--scan-type",
    action="append",
    choices=("source", "dependency", "config", "binary", "container"),
    default=None,
    help="Repeatable. Selects one or more detection engines. Default: source.",
)
parser.add_argument(
    "--image-tar",
    metavar="PATH",
    type=Path,
    help="OCI image tarball (docker save) or OCI image-layout directory. "
         "Only valid with --scan-type container.",
)
```

Exit codes remain FROZEN per §3.5: `0` pass, `1` error, `2` policy violation. Stdout remains a JSON array of finding dicts. Human output goes to stderr.

### 7.6 `scanner/constants.py` — additions

```python
CONTAINER_LAYER_SKIP_PATHS: frozenset[str] = frozenset({
    "proc", "sys", "dev", "run",
    "usr/share/doc", "usr/share/man", "usr/share/locale",
    "var/cache", "var/log",
})

SCAN_MAX_ARTIFACT_BYTES: int = 2 * 1024 * 1024 * 1024   # 2 GiB
```

### 7.7 Example CLI JSON output (single finding)

```json
[
  {
    "file": "sha256:abc...:etc/ssl/certs/server.pem",
    "line": 0,
    "matched_call": "x509.load_pem_x509_certificate",
    "library": "openssl",
    "algorithm": "RSA",
    "primitive": "publicKeyEncryption",
    "language": "n/a",
    "weak_by_default": true,
    "confidence": "high",
    "key_size": 1024,
    "detection_method": "certificate_parse",
    "artifact_type": "CONTAINER_LAYER",
    "artifact_ref": "sha256:abc...:etc/ssl/certs/server.pem",
    "image_digest": "sha256:def...",
    "layer_digest": "sha256:abc...",
    "package_ecosystem": null,
    "package_name": null,
    "package_version": null,
    "source_context": "SOURCE",
    "risk_tier": "CRITICAL",
    "risk_reason": "RSA-1024 falls below current classical strength thresholds."
  }
]
```

### 7.8 `docs/CONTAINER_SCANNING_SCOPE.md` — required frontmatter headings

```
# ECDAT Container-Scanning Scope and Evidence Contract
## Supported inputs
## Deliberate non-claims
## Confidence semantics
## Package-inventory evidence strength
## Certificate-parsing evidence strength
## Safe rollout
```

---

## 8. Step-by-Step Implementation Plan

Each step is tied to exactly one file. Steps 1–8 are CNT's SOLE files. Steps 9–15 are COORDINATED contributions handed off to the lane owner in the merge order of contract §6.

1. **`docs/CONTAINER_SCANNING_SCOPE.md`** — write the scope doc first, mirroring the tone of `docs/SOURCE_SCANNING_SCOPE.md`. Deliberate non-claims: no runtime reachability, no exploitability, no registry pulls, no Docker socket, no ELF/PE/Mach-O linkage inspection.
2. **`scanner/rules/container.yaml`** — author the package rule pack. Fields per §7.3. Small starting set: `openssl` (deb/apk/rpm), `libgcrypt`, `nss`, `mbedtls`, `bouncycastle`, `wolfssl`, `cryptography` (pypi), `node-forge` (npm).
3. **`scanner/image_layers.py`** — implement the OCI layout / `docker save` unpacker with the signatures in §7.1. Enforce `max_bytes`; enforce path-traversal safety on every extracted tar entry (`Path(entry.name).is_absolute() or ".." in Path(entry.name).parts → refuse`); resolve whiteouts.
4. **`scanner/container_engine.py`** — implement the two detectors and the four public functions in §7.2. Certificate detector uses `cryptography.x509.load_pem_x509_certificate` / `load_der_x509_certificate` on files whose magic bytes match (`-----BEGIN CERTIFICATE-----` sniff for PEM; sequence-tag byte for DER). Package detector reads `var/lib/dpkg/status` (RFC-822), `lib/apk/db/installed` (blank-line-separated), RPM headers by stdlib `struct`.
5. **`scanner/__init__.py`** — export `container_engine` alongside the existing engines (COORDINATED — one line, added by scanner lane).
6. **`tests/fixtures/container/`** — generate three tiny fixture tarballs: (a) an `alpine`-shaped layout with one PEM certificate and one apk `installed` entry naming `libcrypto3`; (b) a `debian`-shaped layout with one RSA-1024 PEM cert (must score CRITICAL); (c) an OCI image-layout directory. All committed as `.tar` files under 1 MiB.
7. **`tests/test_container_engine.py`** — cover: PEM cert detected with correct `algorithm`/`key_size`; DER cert detected; apk `installed` entry produces a `container_package_inventory` finding with correct `package_ecosystem`/`package_name`/`package_version`; whiteout on a deleted cert suppresses the finding; path-traversal attempt refused; `max_bytes` enforced; a scan target with **no** image material returns `[]` from `scan_directory`.
8. **`scanner/constants.py`** — add `CONTAINER_LAYER_SKIP_PATHS` and `SCAN_MAX_ARTIFACT_BYTES` per §7.6. **Do not touch** `SKIP_DIRS`, `BINARY_SKIP_DIRS`, or `CONFIG_FILE_PATTERNS` (§C-12).
9. **`scanner/cli.py`** — hand the diff in §7.5 to the scanner lane in Wave 2. Wire `--image-tar` to `container_engine.scan_image_tar` / `scan_oci_layout`. `_relative_or_redacted` gains an image-aware branch that returns `"<layer_digest>:<in-layer path>"` unchanged rather than resolving against a source root. Stdout contract preserved.
10. **`db/migrations/003_artifact_scanning.sql`** — join the shared PR with DEP + BIN + IAC in Wave 3. Do not open it alone.
11. **`db/schema.sql`** — DB lane appends the identical `ADD COLUMN IF NOT EXISTS` block in the same PR as step 10.
12. **`db/models.py`** — DB lane adds the SQLAlchemy columns and the value tuple `ARTIFACT_TYPES` per §3.8.
13. **`db/crud.py`** — DB lane extends `save_finding` to persist the new dict keys. CNT provides the exact keys from §7.2.
14. **`docker-compose.yml`, `Dockerfile`, `.env.example`, `.github/workflows/ecdat-scan.yml`, `docs/ECDAT_CLI_GUIDE.md`** — deploy / CI / scanner-doc lanes take the diffs in §5.2 in the Wave 3 window.
15. **Final** — do **not** touch `PRODUCT_DESCRIPTION.md`, `README.md`, or `ARCHITECTURE.md`. The single scope-editor pass happens in Wave 4 (C-19).

---

## 9. Naming & Symbol Registry

Everything new this feature introduces. Checked against contract §3 conventions and §5 Shared Resource Index for collisions.

### Modules

- `scanner.container_engine` — matches `scanner/<domain>_engine.py` (§3.1). No collision.
- `scanner.image_layers` — new namespace; not in Shared Resource Index.

### Functions (all `snake_case`, §3.1)

- `scanner.container_engine.scan_file(path, rules=None) -> list[Finding]`
- `scanner.container_engine.scan_directory(root, rules=None) -> list[Finding]`
- `scanner.container_engine.scan_image_tar(image_tar, rules=None, *, max_bytes) -> list[Finding]`
- `scanner.container_engine.scan_oci_layout(layout_dir, rules=None, *, max_bytes) -> list[Finding]`
- `scanner.container_engine.load_rules(rules_dir) -> dict`
- `scanner.image_layers.open_image(image_path, *, max_bytes) -> ExtractedImage`
- `scanner.image_layers.iter_files(image) -> Iterator[tuple[ExtractedLayer, Path]]`
- `scanner.image_layers.cleanup(image) -> None`

### Classes (`PascalCase`, §3.1)

- `scanner.image_layers.ExtractedLayer` (frozen dataclass)
- `scanner.image_layers.ExtractedImage` (frozen dataclass)
- `scanner.image_layers.ImageLayoutError(ValueError)`
- `scanner.image_layers.ImageSizeLimitExceeded(ImageLayoutError)`

### Constants (`UPPER_SNAKE_CASE`, §3.1)

- `scanner.constants.CONTAINER_LAYER_SKIP_PATHS`
- `scanner.constants.SCAN_MAX_ARTIFACT_BYTES` (shared across scanner lanes per C-12; CNT is the first author)

### DB columns (all in migration 003, verbatim from contract §2.2)

- `findings.artifact_type` — value in `ARTIFACT_TYPES` tuple; CNT contributes `'CONTAINER_LAYER'`
- `findings.artifact_ref`
- `findings.image_digest`
- `findings.layer_digest`
- `findings.package_ecosystem` — CNT contributes `'deb' | 'apk' | 'rpm'`; DEP contributes `'pypi' | 'npm' | 'maven'`
- `findings.package_name`
- `findings.package_version`
- Index `idx_findings_artifact_type`
- Partial index `idx_findings_package`

### `detection_method` registry entries (FROZEN, §3.2 — no new values added by this spec)

- `"certificate_parse"` — already reserved to CNT
- `"container_package_inventory"` — already reserved to CNT

### Environment variables (`SCAN_` prefix, §3.3)

- `SCAN_ENABLE_CONTAINER` — boolean, default `false`
- `SCAN_MAX_ARTIFACT_BYTES` — int, default `2147483648` (shared with BIN/IAC per C-12)
- `SCAN_IMAGE_TAR_PATH` — optional default path for CI

Existing frozen variables (`POSTGRES_*`, `API_KEY`, `DEBUG`, `CORS_ORIGINS`, `ENABLE_LOCAL_SCAN_API`, `ALLOW_REMOTE_REMEDIATION`, `REPORT_SYNC_*`, `ECDAT_HTTPS_PORT`) are untouched.

### CLI flags (`kebab-case`, long-form only, §3.5)

- `--scan-type container` (part of the shared repeatable flag defined in C-11)
- `--image-tar PATH` (valid only with `--scan-type container`)

No new single-letter flags. Exit codes untouched.

### API routes

None. This feature adds no routes (the confidence gate on `scan_runner.py` and the `POST /scans` router are contract-frozen or COORDINATED elsewhere).

### Frontend

No symbols. The `FindingsTable` column registry (C-13) receives entries authored by the frontend lane after DFS restructures the table.

### Collision check against Shared Resource Index (§5.1, §5.4)

- `scanner/cli.py` — CNT's diff conforms to C-11 (single `--scan-type` grammar). No collision with DEP/BIN/IAC/CONF drafts.
- `scanner/constants.py` — CNT's additions are namespaced (`CONTAINER_LAYER_SKIP_PATHS`), so C-12 is satisfied.
- `scanner/finding.py` — untouched; C-03 satisfied.
- `db/migrations/003_*.sql` — CNT contributes to the shared file; C-01 satisfied.
- `docker-compose.yml` mount prefix `04_` — matches contract §2.1 allocation.

---

## 10. Known Cross-Feature Risks

Pulled directly from contract §4 and §5. Resolutions here are the ones already decided; CNT applies them, does not re-open them.

- **C-01 · migration numbering.** Resolved: CNT uses `003_artifact_scanning.sql`, compose mount `04_`. Not negotiable.
- **C-02 · `scan_runner.py` drops non-`"high"` findings.** Resolved: CNT does not touch `scan_runner.py`. Until CONF replaces the gate, CNT is a **CLI-only feature** and `docs/CONTAINER_SCANNING_SCOPE.md` says so.
- **C-03 · confidence vocabulary.** Resolved: CNT does not introduce an `inventory` value. Package-inventory findings emit `confidence = "high"` (mirror of the eventual `VERIFIED` band) or `"unverified"` (mirror of `UNVERIFIED`), plus a `detection_method` of `container_package_inventory`, so the *evidence-strength* signal lives on `detection_method`, not on `confidence`.
- **C-04 · risk-engine authority.** Resolved: CNT does not compute risk. Parsed `key_size` flows through `Finding` → `risk_engine.score_findings`.
- **C-11 · CLI flag grammar.** Resolved: single repeatable `--scan-type`, `--image-tar` valid only with `container`. Scanner lane merges.
- **C-12 · `constants.py` skip lists.** Resolved: CNT adds a new named set, does not mutate `SKIP_DIRS`.
- **C-14 · CBOM generator refactor.** Resolved: CBOM lane extracts `build_cbom_from_findings(findings, summary)` in Wave 1 before CNT ships. CNT emits `ecdat:artifact_type`, `ecdat:detection_method` property keys via the finding dict; the generator maps them.
- **C-18 · unpinned `cryptography`.** Resolved: Wave 0 pins it. CNT depends on the pin already being in `requirements.txt` when it starts.
- **C-19 · pitch-doc rewrite.** Resolved: CNT does not touch `PRODUCT_DESCRIPTION.md` / `README.md` / `ARCHITECTURE.md`. Only `docs/CONTAINER_SCANNING_SCOPE.md`.
- **C-20 · scope contradiction.** **Unresolved — blocks CNT from starting.** No workaround. Requires human sign-off.
- **C-23 · duplicate library across engines.** Resolved: CNT writes the shared columns; de-duplication key is `(artifact_type, artifact_ref, package_ecosystem, package_name, package_version, algorithm)`; findings are *retained as distinct evidence*. Dashboard grouping is DFS/frontend work, not CNT's.
- **§5.1 · `docker-compose.yml`.** Compatible; CNT adds only the `04_` initdb mount and the tarball bind-mount comment.

---

## 11. Pre-Answered Ambiguities

1. **If `SCAN_ENABLE_CONTAINER` is unset and the user passes `--scan-type container`,** do run the scan. The env var gates CI defaults, not user intent expressed on the command line.
2. **If `--image-tar` points at a directory,** treat it as an OCI image-layout (`index.json` at root). If it points at a `.tar`, treat as `docker save`. If neither shape is present, raise `ImageLayoutError` and exit 1 (not 2 — no policy violation, a real error).
3. **If a layer tar contains an absolute path or a `..` component,** refuse the entry, log to stderr, and continue with the rest of the layer. Do not abort the whole scan. This is a defence-in-depth guard, not a scan failure.
4. **If total extracted size would exceed `SCAN_MAX_ARTIFACT_BYTES`,** stop mid-extraction, raise `ImageSizeLimitExceeded`, and exit 1. Do not emit partial findings for that image — a partial scan of an image is a misleading inventory.
5. **If a file matches both detectors (e.g. a certificate shipped inside a deb),** emit two findings with different `detection_method` values and different `artifact_ref` values (the cert file path and the package name). Per C-23 they are distinct evidence and must not be merged at write time.
6. **If `container.yaml` is missing or malformed,** run the certificate detector only, log a stderr warning, and exit 0 (the package detector's absence is not a scan error). The scope doc notes this behaviour.
7. **If a whiteout file removes a certificate present in a lower layer,** the certificate does not appear in findings. `iter_files` returns the merged view.
8. **If the same `libcrypto3` package appears in two layers (base + overlay),** emit one finding attributed to the layer that last wrote the `installed` entry (the top layer's dpkg/apk DB is the effective one). This is *not* the same case as (5); it is one fact from one detector, so it de-duplicates within the detector.
9. **If the input tarball contains no `manifest.json` and no `index.json`,** it is not an OCI image. Raise `ImageLayoutError`. Do not fall back to walking the tar as if it were a filesystem.
10. **If the confidence gate C-02 is still in place at merge time** (CONF has not landed), package-inventory findings emit `confidence = "high"` because the *evidence for the package presence* is fully verified (dpkg/apk DB parsed). The evidence-strength distinction lives on `detection_method`, per the C-03 resolution. Certificate findings similarly emit `confidence = "high"`. This is honest: what is uncertain is *whether the library is used*, not whether it is installed — and `docs/CONTAINER_SCANNING_SCOPE.md` says so explicitly.
11. **If `scanner/cli.py` is passed a directory *without* `--scan-type container` but the directory happens to be an OCI layout,** do source-scanning as today. `--scan-type` explicitly selects engines; auto-detection would silently change existing CI behaviour (§3.5, C-11).
12. **If a scan mixes source and container types in one `POST /scans` call,** reject at the API layer. CNT does not modify `api/routers/scans.py`; the backend lane extends `ScanCreateRequest` in its window per §1.2. Until then, the CLI is the only container-scan entry point.
13. **If `AGENT_RULES.md` #5 (no regex for source-code scanning) is invoked against `container.yaml`,** it does not apply. `container.yaml` matches parsed package-name strings by exact/substring equality, not source-code content. Certificate parsing uses `cryptography.x509`, not regex. Called out in the scope doc.
14. **If a package rule fires on a package whose *installed but disabled* state can be inferred from the DB,** still emit the finding. "Installed but disabled" is a runtime concept; CNT is a static-inventory tool per §3 and per `docs/CONTAINER_SCANNING_SCOPE.md`.

### Open sign-off items from the contract that touch this feature

Per `AGENT_RULES.md` #4, these are recorded, not resolved by CNT:

- **C-20 · scope contradiction.** No team-resolved answer exists. **This feature cannot be started until a human signs off.**
- **C-02 · persist or drop sub-threshold findings.** Team resolution not yet recorded. CNT's default under the current gate is stated in item 10 above and does not depend on the answer; when CONF lands, sub-threshold behaviour is CONF's, not CNT's.
- **C-11 · exact CLI flag spelling; does bare `ecdat TARGET` remain an alias for `scan`?** Not yet ratified by the scanner lane. CNT implements the flag as spelled in contract §3.5 and defers any renaming to the scanner lane's ratification.
- **C-14 · CBOM validation failure = 500 or 200-with-warning; full 1.6 schema or subset?** Owned by CBOM/CBV lanes. Does not block CNT; CNT emits `ecdat:*` property keys per §C-14 and the generator maps them.
- **C-23 · dashboard grouping of duplicate package findings.** Owned by DFS/frontend. Does not block CNT; CNT retains distinct rows per item 5 above.

### Genuinely uncovered by the contract

Per the rules for this spec, if the contract does not cover something the feature needs, say so explicitly rather than inventing a resolution:

- **RPM header parsing depth.** The contract lists `rpm` as a valid `package_ecosystem` value but does not specify which fields must be extracted. CNT extracts only `name` and `version` for v1; anything richer (`epoch`, `release`, signing key) is deferred and needs scanner-lane sign-off before extension.
- **Non-OCI legacy Docker v1 image tarballs.** The contract does not mention them. CNT refuses them with a clear stderr message. If v1 support is required, that is a separate scope item.
- **Behaviour when the same finding would map to two `package_ecosystem` values** (e.g. a Python wheel installed via `apt` as a deb). CNT prefers the OS-package attribution (`deb`) because that is the layer that placed the file. This is an engineering call, not a contract item; flagged here so a reviewer can override.

---

## 12. Test Plan / Definition of Done

Definition of Done: every command below runs green in a clean `python:3.11-slim` container built from this repo's `Dockerfile`.

```bash
# 1. Unit tests
pytest tests/test_container_engine.py -q
# expected: all tests pass; no warnings about missing cryptography

# 2. Rule file loads
python -c "from pathlib import Path; from scanner import container_engine; \
  rules = container_engine.load_rules(Path('scanner/rules')); \
  assert isinstance(rules, dict) and rules"
# expected: no output, exit 0

# 3. CLI smoke — certificate detector on a fixture image
python -m scanner.cli \
  --scan-type container \
  --image-tar tests/fixtures/container/debian_rsa1024.tar
# expected: stdout is a JSON array containing at least one finding with
#   "detection_method": "certificate_parse",
#   "algorithm": "RSA",
#   "key_size": 1024,
#   "artifact_type": "CONTAINER_LAYER",
#   "risk_tier": "CRITICAL"

# 4. CLI smoke — package detector on a fixture image
python -m scanner.cli \
  --scan-type container \
  --image-tar tests/fixtures/container/alpine_libcrypto.tar
# expected: stdout is a JSON array containing at least one finding with
#   "detection_method": "container_package_inventory",
#   "package_ecosystem": "apk",
#   "package_name": "libcrypto3",
#   "artifact_type": "CONTAINER_LAYER"

# 5. Policy gate integration — CRITICAL trips --fail-on
python -m scanner.cli \
  --scan-type container \
  --image-tar tests/fixtures/container/debian_rsa1024.tar \
  --fail-on CRITICAL >/dev/null; echo $?
# expected: 2

# 6. Source-scanning unchanged (regression guard on the existing demo)
python -m scanner.cli tests/fixtures/python_demo/
# expected: stdout matches the pre-CNT baseline (18-finding demo from
# PRODUCT_DESCRIPTION.md §6 Minute 2 is unaffected)

# 7. Migration idempotency (both fresh and upgrade paths)
docker compose down -v && docker compose up -d db
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT column_name FROM information_schema.columns \
     WHERE table_name='findings' AND column_name IN \
     ('artifact_type','artifact_ref','image_digest','layer_digest',
      'package_ecosystem','package_name','package_version') \
     ORDER BY column_name;"
# expected: exactly those seven column names, one per line
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -f /docker-entrypoint-initdb.d/04_artifact_scanning.sql
# expected: NOTICE messages "column already exists, skipping"; exit 0

# 8. Path-traversal refusal
pytest tests/test_container_engine.py::test_rejects_absolute_path -q
pytest tests/test_container_engine.py::test_rejects_dotdot_path   -q
# expected: pass

# 9. Size-limit enforcement
SCAN_MAX_ARTIFACT_BYTES=1024 python -m scanner.cli \
  --scan-type container \
  --image-tar tests/fixtures/container/alpine_libcrypto.tar; echo $?
# expected: 1 (error), stderr contains "ImageSizeLimitExceeded"

# 10. Whole-suite regression
pytest -q
# expected: no new failures against the pre-CNT baseline
```

Documentation Done:

- `docs/CONTAINER_SCANNING_SCOPE.md` exists with all six headings from §7.8.
- `docs/ECDAT_CLI_GUIDE.md` mentions `--scan-type container` and `--image-tar`.
- `.env.example` lists `SCAN_ENABLE_CONTAINER`, `SCAN_MAX_ARTIFACT_BYTES`, `SCAN_IMAGE_TAR_PATH` with commented defaults.
- `.github/workflows/ecdat-scan.yml` has a job that runs command (3) or (4) against a fixture.

Not done: any edit to `PRODUCT_DESCRIPTION.md` / `README.md` / `ARCHITECTURE.md`. That is the single scope-editor pass in Wave 4 (C-19). Do not touch.

---

## 13. Rollback Plan

Rollback is per-layer, mirroring the merge order. Because migration 003 is additive (`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) and the new columns are all nullable except `artifact_type` (which has `DEFAULT 'SOURCE_FILE'`), the DB never has to be rolled back — an unwritten column is invisible to existing readers.

1. **CLI-only rollback (fastest, no DB touch).** Revert the diff in `scanner/cli.py` that adds `--scan-type container` and `--image-tar`. The `scanner.container_engine` and `scanner.image_layers` modules can stay in the tree unreferenced; nothing else imports them. CI stays green because source scanning is unchanged.
2. **Engine rollback.** Revert the SOLE files (`scanner/container_engine.py`, `scanner/image_layers.py`, `scanner/rules/container.yaml`, `tests/test_container_engine.py`, `tests/fixtures/container/`, `docs/CONTAINER_SCANNING_SCOPE.md`), plus the CNT-scoped lines of `scanner/constants.py` and `scanner/__init__.py`.
3. **Docs rollback.** Revert the CLI-guide addition; revert the `.env.example` entries.
4. **DB rollback.** Not required. The columns and indexes are additive and shared with DEP/BIN/IAC; dropping them would break their features. If a column *must* be dropped, do it via a new numbered migration (`009_`+) coordinated by the DB lane, never by editing `003_`.
5. **Compose / CI rollback.** Remove the `04_artifact_scanning.sql` mount line only if migration 003 is also being reverted — which, per point 4, it should not be.
6. **Deploy signal.** If `SCAN_ENABLE_CONTAINER=false` in prod and the CLI never receives `--scan-type container`, this feature is dark. That is the intended emergency off-switch pending root-cause analysis.
7. **Test signal.** If `pytest -q` fails only inside `tests/test_container_engine.py`, quarantine with `-m "not container"` (add the marker in the same PR) and open an issue against CNT; do not disable unrelated suites.
8. **Communication.** Post the failing command (verbatim, per Ronak's stated debugging preference: actual output, not paraphrase) in the team channel with the exit code and stderr. Do not re-run with `--continue-on-error` or similar; the offline-scan claim depends on deterministic failure modes.
