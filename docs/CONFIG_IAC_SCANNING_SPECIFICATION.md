# CONFIG/IaC SCANNING FEATURE SPECIFICATION

**Version:** 1.0  
**Feature Code:** `IAC` (config-iac-scanning)  
**Owner:** [To be assigned]  
**Status:** Ready for Implementation  
**Last Updated:** 2026-09-20  

---

## 1. Header

### Feature Name
Config/IaC Scanning — Structured Configuration & Infrastructure-as-Code Cryptographic Discovery

### Ownership & Contacts
- **SOLE Owner:** `scanner/config_engine.py`, `scanner/rules/config.yaml`
- **COORDINATED Participants:** scanner lane (Shashank), backend lane (Shreyanshi), DB lane (Ronak), frontend lane (Karan/Satyam)
- **Specification Author:** [TBD — assign before implementation begins]

### Spec Version & Changelog
- **v1.0 (2026-09-20):** Initial specification derived from SYSTEM_INTERFACE_CONTRACT.md §2, §3, §4, §5 and Step 1 proposal.
- **Deviations from Step 1 proposal:** None. Step 1 proposal aligns with contract constraints. Database columns (`artifact_type`, `artifact_ref`) are now explicitly defined via contract §2.2 migration 003, not ad-hoc.

### Status
🟡 **Ready for Detailed Design** — awaiting human sign-off on C-20 (scope truth) and C-02 (sub-threshold persistence policy) before implementation begins. All file ownership, naming conventions, and interfaces are locked.

### Reviewer Sign-Off (to be completed)
- [ ] Database schema & migration ownership (Ronak)
- [ ] CLI integration & `--scan-type config` flag (Shashank)
- [ ] Risk engine & CBOM generator integration (Maitreyi)
- [ ] Dashboard table column & evidence display (Karan/Satyam)
- [ ] Security & compliance review (team lead)

---

## 2. Goal & Context

ECDAT's core mission is to **discover cryptographic usage across source code and infrastructure as code**, enabling enterprises to inventory their cryptographic attack surface before quantum threats become operational. This feature implements **configuration and IaC scanning** — the fourth of five artifact-type detection engines — to detect cryptographic configuration weaknesses (TLS versions, weak ciphers, disabled verification, plaintext transport) in Kubernetes YAML, Docker Compose, Terraform HCL, Nginx configs, and CI/CD YAML. It satisfies **PS 26164 Requirement 1 (Discovery)** and **PS 26164 Requirement 2 (Identification)** by proving that configuration-declared cryptography can be detected with high confidence (no regex, no false positives from comments) and emitting structured evidence compatible with the CBOM generator and risk engine. Configuration findings must be honest: an explicit `TLSv1.0` or `verify: false` is strong evidence; an unresolved variable reference is `unverified`, not guessed.

---

## 3. Scope

### In-Scope

- **File formats:** Kubernetes/Compose YAML, Terraform HCL, Nginx configs, GitHub Actions YAML, GitLab CI YAML, generic JSON
- **Cryptographic signals detected:**
  - TLS/SSL versions (explicit strings `TLSv1.0`, `TLSv1.1`, `TLSv1.2`, `TLSv1.3`)
  - Cipher suites (weak patterns: `RC4`, `DES`, `MD5`, `SHA1`, `PSK`, `anon`, `export`)
  - Key sizes (RSA, ECDSA key bits via string parsing)
  - Certificate verification settings (`verify: false`, `insecure: true`, `ssl_verify: off`)
  - Plaintext transport indicators (`http://`, unencrypted protocol URLs, `enabled: false` for TLS)
  - Provider references and variable interpolation boundaries (honest reporting of `unverified` when final value cannot be resolved)
- **Output:** Findings emitted as `scanner/finding.py` `Finding` dataclass with `detection_method="config_analysis"`, persisted via `api/services/scan_runner.py`
- **Confidence scoring:** Integrated with CONF lane's unified confidence model (`confidence_band`: `VERIFIED` for explicit literals, `UNVERIFIED` for unresolved interpolations)
- **CBOM integration:** Configuration-derived cryptographic assets represented in CycloneDX 1.6 via `api/services/cbom_generator.py`
- **CLI:** Scans via `--scan-type config` flag (repeatable, coordinated via C-11 resolution); findings emitted to stdout as JSON array
- **Dashboard:** Config evidence displayed in `FindingsTable.jsx` via `artifact_type: CONFIG_FILE` column, with config-specific context (file path, line, setting key/value)

### Out-of-Scope

- **Semantic policy evaluation:** IAC does NOT check whether a configuration matches an enterprise policy (e.g., "all TLS must be 1.3"). That is a compliance-engine concern, orthogonal to discovery.
- **IaC deployment validation:** IAC does NOT execute Terraform, run `docker-compose config`, or invoke Kubernetes validators. Discovery is static, local, no side effects.
- **General IaC security auditing:** IAC is crypto-focused. It does NOT detect overpermissioned IAM roles, public S3 buckets, missing encryption at rest, or other non-cryptographic misconfigurations. Use Checkov, tfsec, or Trivy for that; this tool is not a general-purpose scanner.
- **Dynamic variable resolution:** IAC does NOT resolve variables from environment files, secret managers, or runtime state. Unresolved variables are marked `unverified`, not guessed.
- **Template interpolation:** IAC does NOT evaluate Jinja2, ERB, Go templates, or bash variable substitution. Interpolation boundaries are detected via syntax, and evidence inside `{{ … }}` blocks is marked `unverified`.
- **Binary/container configs:** Configuration inspection of running containers, registry metadata, and compiled binary settings are in scope for CNT and BIN; IAC is source-code-only.

---

## 4. Required Context Files

**Implementers must read these files in this order before starting:**

1. **`ARCHITECTURE.md`** (root) — system-wide design patterns, engine signatures, confidence model  
   *Why:* Defines the `scan_file()` / `scan_directory()` contract that all engines must implement.

2. **`scanner/finding.py`** (FROZEN) — the `Finding` dataclass contract  
   *Why:* Config engine must emit exactly this schema; no additions without CONF sign-off (C-03).

3. **`db/schema.sql`** — canonical schema (existing `findings`, `scans`, `risk_assessments` tables)  
   *Why:* Migration 003 adds `artifact_type`, `artifact_ref`, `source_context` columns; these are the real constraints.

4. **`db/models.py`** — Pydantic models and enum-like value tuples  
   *Why:* `CONFIDENCES`, `RISK_TIERS`, `SOURCE_CONTEXTS` tuples; config engine must use exact strings.

5. **`scanner/constants.py`** — skip directories, file patterns  
   *Why:* Config engine adds `CONFIG_FILE_PATTERNS` here; must not collide with `SKIP_DIRS` or other engine sets.

6. **`scanner/python_engine.py`** (lines 1–50) — example engine structure  
   *Why:* Template for `scan_file()` and `scan_directory()` signatures; confidence scoring integration points.

7. **`scanner/multilang_engine.py`** (lines 1–100) — multi-language example  
   *Why:* Shows Tree-sitter integration pattern; not directly used by config engine but illustrates import/rule resolution.

8. **`scanner/rules/java.yaml`** (lines 1–30) — example rule structure  
   *Why:* Config engine rules follow a similar YAML pattern; understand the structure.

9. **`api/services/risk_engine.py`** — quantum risk scoring (FROZEN, read-only)  
   *Why:* Config findings are scored by risk_engine; understand TLS/cipher mappings, key-size overrides.

10. **`api/services/cbom_generator.py`** — CBOM generation (COORDINATED, being refactored)  
    *Why:* Config findings flow into CBOM; the refactor (`build_cbom_from_findings()` in C-14) will show how `artifact_type: CONFIG_FILE` maps to CycloneDX components.

11. **`api/routers/findings.py`** (lines 1–50) — findings API structure  
    *Why:* Config findings are returned via `/scans/{scan_id}/findings`; understand response schema.

12. **`dashboard/src/components/FindingsTable.jsx`** (lines 1–100) — table column structure  
    *Why:* Config evidence must be displayed; understand the COORDINATED column-registry pattern (C-13).

13. **`SYSTEM_INTERFACE_CONTRACT.md` §2, §3, §4** (this file) — hard constraints  
    *Why:* Final authority on schema, naming, conflicts, resolutions. Read it entirely before implementation.

14. **`.github/workflows/ecdat-scan.yml`** — CI gate workflow  
    *Why:* Config scanning must integrate into the existing CI/CD policy gate; understand the `--fail-on` behavior.

---

## 5. File Ownership

### Files This Feature Creates or Modifies (Tier Assignments)

| File Path | Tier | Responsibility | Creation/Modification |
|-----------|------|-----------------|----------------------|
| `scanner/config_engine.py` | **SOLE** | Implement YAML/HCL parsing, crypto detection logic, `scan_file()` / `scan_directory()` | **Create** |
| `scanner/rules/config.yaml` | **SOLE** | Declarative detection rules for TLS, ciphers, key sizes, verification | **Create** |
| `tests/test_config_engine.py` | **SOLE** | Unit tests for config engine (fixtures, edge cases, negative tests) | **Create** |
| `tests/fixtures/config/` | **SOLE** | Test fixtures: vulnerable and clean Kubernetes, Terraform, Nginx, CI YAML files | **Create** |
| `docs/CONFIG_IAC_SCANNING_SCOPE.md` | **SOLE** | Feature scope document, rule details, unsupported formats, limitations | **Create** |
| `scanner/constants.py` | **COORDINATED** | Add `CONFIG_FILE_PATTERNS`, do not modify `SKIP_DIRS` or other engines' sets | **Modify** (C-12) |
| `scanner/cli.py` | **COORDINATED** | Integrate config scanning via `--scan-type config` flag (Shashank handles merge) | **Modify** (C-11) |
| `scanner/__init__.py` | **COORDINATED** | Export config engine entry point: `from scanner.config_engine import scan_file, scan_directory` | **Modify** |
| `db/schema.sql` | **COORDINATED** | Already includes migration 003 columns (`artifact_type`, `artifact_ref`); no IAC-specific additions | **No change** |
| `db/migrations/003_artifact_scanning.sql` | **COORDINATED** | Shared file (DEP+CNT+BIN+IAC), pre-written in contract §2.2; IAC only executes, does not author | **No change** |
| `api/services/scan_runner.py` | **FROZEN** | Config findings pass through confidence gate; IAC must not edit | **Read-only** |
| `api/services/risk_engine.py` | **FROZEN** | Risk scoring for config findings; IAC must not edit | **Read-only** |
| `api/services/cbom_generator.py` | **COORDINATED** | Being refactored in C-14 to `build_cbom_from_findings()`; config artifacts represented as `artifact_type: CONFIG_FILE` | **Read-only (for IAC)** |
| `api/models.py` | **COORDINATED** | May add Pydantic model for config-specific evidence if needed (coordinate with Shreyanshi) | **Modify if needed** |
| `dashboard/src/components/FindingsTable.jsx` | **COORDINATED** | Adding config evidence column via `lib/constants.js` registry, not JSX editing (C-13) | **Read-only (IAC)** |
| `dashboard/src/lib/constants.js` | **COORDINATED** | IAC adds column definition for config evidence (file, setting, value, line) | **Modify** |
| `PRODUCT_DESCRIPTION.md` | **COORDINATED** | Update §5 "Honesty Table" status row for config scanning from "❌ Out of scope" when implemented (C-19, C-20) | **Modify** |
| `docs/ECDAT_CLI_GUIDE.md` | **COORDINATED** | Document `--scan-type config`, supported formats, example invocations | **Modify** |
| `.github/workflows/ecdat-scan.yml` | **COORDINATED** | No new workflow; config scanning already tested via `--scan-type config` in scanner tests | **No change** |
| `.env.example` | **COORDINATED** | No new env vars for config scanning (uses existing `SCAN_MIN_CONFIDENCE_BAND`, `DEBUG`) | **No change** |
| `docker-compose.yml` | **COORDINATED** | No changes for config scanning (migration 003 mount already exists) | **No change** |

### Do NOT Touch (Mandatory Exclusion List)

**These files are SOLE or FROZEN owned by other features; config-iac-scanning must not modify them:**

- **DEP (dependency_engine.py, dependency_rules/):** Do not edit.
- **CNT (container_engine.py, image_layers.py, container.yaml rules):** Do not edit.
- **BIN (binary_engine.py, binary.yaml rules):** Do not edit.
- **CONF (scanner/confidence.py):** Do not edit; config engine consumes confidence scoring via import.
- **scanner/python_engine.py, scanner/multilang_engine.py:** Do not edit (owned by scanner lane; CONF removes hardcoded `"high"` literal).
- **api/core/rbac.py, api/core/security.py:** RBAC-owned; do not edit.
- **api/routers/auth.py, api/routers/agents.py, api/routers/audit.py, api/routers/triage.py, api/routers/trends.py:** Do not edit.
- **dashboard/src/context/AuthContext.jsx, dashboard/src/pages/LoginPage/:** RBAC-owned; do not edit.
- **dashboard/src/components/ConfidenceStamp.jsx:** CONF-owned; do not edit.

---

## 6. Tech Stack & Pinned Versions

### Python Dependencies (Backend & Scanner)

All versions are from `requirements.txt` as of the current repo state. Implementers must not change pinned versions without explicit approval from the dependency owner.

| Library | Version (pinned in requirements.txt) | Purpose in IAC | Notes |
|---------|------|---------|-------|
| `PyYAML` | [existing] | Parse Kubernetes, Docker Compose, CI/CD YAML | Already pinned; no change |
| `python-hcl2` | [to pin in Wave 1] | Parse Terraform `.tf` files | New dependency; add during implementation coordination with Shashank |
| `python-jsonschema` | [existing] | Optional: validate YAML structure against JSONSchema | Already in deps for risk engine; reusable |
| `pathlib` | stdlib | Path discovery and traversal | No version; Python 3.11 stdlib |
| `json` | stdlib | Parse and emit JSON findings | No version; Python 3.11 stdlib |
| `re` | stdlib | **FORBIDDEN** for primary detection; only for tokenization boundaries | AGENT_RULES.md #5: no naive regex matching |
| `cryptography` | [must be pinned Wave 0] | Reference library for TLS/cipher version constants | C-18: add pinning step to Wave 0 |
| `pydantic` | [existing] | Validation of config engine output against `Finding` schema | Already used by backend |
| `pytest` | [existing] | Unit tests for config engine | Already in test suite |

### External Tool Dependencies

- **Terraform parser:** `python-hcl2` (pure Python; no system binaries required)
- **YAML parser:** PyYAML (no external binaries)
- **System binaries:** None required; config scanning is pure Python

### Frontend Dependencies (Dashboard)

- **React** [existing]
- **Tailwind CSS** [existing]
- **Recharts** [existing] — for CBOM and risk charts (not used by config engine directly)

### Database

- **PostgreSQL 16** (unchanged from existing requirement)
- **SQLAlchemy 2.0** (unchanged)

### Environment Variables

**No new environment variables introduced by config scanning.** Config engine respects existing:

- `DEBUG` — enable verbose logging
- `SCAN_MIN_CONFIDENCE_BAND` — gate findings by confidence (set by CONF, Wave 1)
- `REPORT_SYNC_AGENT_KEYS` — agent credential (unchanged)

**New variables allocated to scanner lane (SCAN_* prefix) by C-11, but not used by IAC initially:**

- `SCAN_ENABLE_BINARY` (BIN)
- `SCAN_ENABLE_CONTAINER` (CNT)
- `SCAN_MAX_ARTIFACT_BYTES` (shared)

**Config scanning uses no new env vars.** If needed in future, would follow `SCAN_CONFIG_*` prefix.

---

## 7. Concrete Interface Definitions

### 7.1 Core Engine Signatures

All config engine functions adhere to the standard engine contract (ARCHITECTURE.md, SYSTEM_INTERFACE_CONTRACT.md §3.1):

```python
# scanner/config_engine.py

from pathlib import Path
from typing import Optional
from scanner.finding import Finding

def scan_file(path: Path, rules: Optional[dict] = None) -> list[Finding]:
    """
    Scan a single configuration file for cryptographic weaknesses.
    
    Args:
        path: Absolute path to a supported config file.
        rules: Optional parsed `scanner/rules/config.yaml` ruleset.
               If None, loads from default location.
    
    Returns:
        List of Finding objects. Empty list if no findings detected.
    
    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If file format is not supported.
        yaml.YAMLError, hcl2.api.lark.LarkError: Parsing errors (caught,
            logged, returned as empty list — malformed configs are skipped).
    
    Side effects: None (pure function, no DB writes, no network calls).
    """
    pass

def scan_directory(root: Path, rules: Optional[dict] = None) -> list[Finding]:
    """
    Recursively scan a directory for configuration files.
    
    Args:
        root: Absolute path to repository root or directory to scan.
        rules: Optional parsed ruleset (same as scan_file).
    
    Returns:
        Aggregated list of all Finding objects from all config files.
    
    Implementation:
        1. Discover files matching CONFIG_FILE_PATTERNS (from constants.py).
        2. Respect SKIP_DIRS (do not descend into build/, dist/, node_modules/).
        3. Call scan_file() on each discovered file.
        4. Aggregate and return all findings.
    
    Side effects: None.
    """
    pass
```

**Immutable contract:**
- Both functions return a **sorted list** by (file path, line number, algorithm).
- Finding IDs are assigned sequentially by `scanner/cli.py` after aggregation across all engines.
- No DB writes occur inside the engine; `api/services/scan_runner.py` persists findings.
- Errors during parsing (malformed YAML, HCL syntax) are logged and skipped; the scan continues.

### 7.2 Finding Dataclass (FROZEN, inherited from scanner/finding.py)

```python
# scanner/finding.py (FROZEN — config engine must emit exactly this)

from dataclasses import dataclass
from typing import Optional

@dataclass
class Finding:
    """
    Unified cryptographic finding across all engines.
    Matches contract §7 in SYSTEM_INTERFACE_CONTRACT.md.
    """
    file: str                          # relative path from scan root
    line: int                          # line number (0 for config lines without explicit line marker)
    algorithm: Optional[str]           # "RSA", "TLSv1.0", "MD5", "DES", "RC4", "AES", etc.
    primitive: Optional[str]           # "encryption", "hashing", "key_exchange", "digital_signature"
    key_size: Optional[int]            # bits (RSA, ECDSA, AES only); None if not applicable
    library: Optional[str]             # "openssl", "cryptography", "tls_native", "hcl2_provider", etc.
    language: str                      # "config" for IAC; also "python", "java", "javascript", "binary", "container"
    detection_method: str              # FROZEN enum: "ast_visitor", "tree_sitter_query", "config_analysis", ...
    source_context: str                # FROZEN enum: "SOURCE", "TEST_ONLY", "DEMO_ONLY"
    evidence: str                      # raw text snippet (max 500 chars, no secrets)
    confidence: str                    # "high", "probable", "unverified" — will be replaced by confidence_band via CONF
    
    # Added by CONF (Wave 1, not yet in schema but implemented by then):
    confidence_score: Optional[float]  # 0.00–1.00 (confidence_band: VERIFIED=0.95, PROBABLE=0.70, UNVERIFIED=0.30)
    confidence_band: Optional[str]     # "VERIFIED", "PROBABLE", "UNVERIFIED"
    confidence_signals: Optional[list] # ["literal_algorithm_arg", "explicit_setting", "file_context"]
```

**Config engine emission rules:**
- `algorithm`: Exact TLS version string (`"TLSv1.0"`, `"TLSv1.2"`, `"TLSv1.3"`), cipher name (`"RC4"`, `"DES"`), key algorithm (`"RSA"`, `"ECDSA"`), or hash algorithm (`"MD5"`, `"SHA-1"`)
- `primitive`: One of `"encryption"`, `"hashing"`, `"key_exchange"`, `"digital_signature"`, `"protocol_version"`
- `key_size`: Integer bits (RSA, ECDSA, AES only); `None` for protocol versions and ciphers without explicit key length
- `library`: Config-specific values: `"tls_literal"`, `"nginx"`, `"kubernetes"`, `"terraform"`, `"docker_compose"`, `"github_actions"`, `"gitlab_ci"`, `"openssl_config"`
- `language`: Always `"config"` for this engine
- `detection_method`: Always `"config_analysis"` (FROZEN in §3.2)
- `source_context`: `"SOURCE"` for tracked production configs; `"TEST_ONLY"` for `tests/`, `spec/`, `e2e/` subdirectories; `"DEMO_ONLY"` for `examples/`, `demo/`
- `evidence`: Raw config line or block (e.g., `"tls_version: TLSv1.0"`, `"ssl_protocols TLSv1.0;"`), trimmed to 500 chars
- `confidence`: `"high"` if explicit literal (e.g., `tls_version: TLSv1.0`); `"unverified"` if interpolation (`${VAR}`, `{{ .variable }}`); never a guess
- `confidence_band` (post-CONF): `"VERIFIED"` for literals, `"UNVERIFIED"` for interpolations, `"PROBABLE"` for weak defaults (e.g., Terraform provider without explicit version)

### 7.3 Rules YAML Structure

```yaml
# scanner/rules/config.yaml

rules:
  # TLS Version Detection
  tls_v1_0:
    name: "TLS 1.0 (Deprecated)"
    algorithm: "TLSv1.0"
    primitive: "protocol_version"
    description: "TLS 1.0 is deprecated (RFC 8996) and broken by POODLE, BEAST, CRIME attacks."
    patterns:
      # Kubernetes
      - kind: "yaml"
        path: "*.yaml"
        context: "spec.tls[].hosts"
        key_patterns: ["tlsVersion", "ssl_protocols"]
        value_patterns: ["TLSv1.0", "1.0", "SSLv3", "SSLv2"]
      
      # Nginx
      - kind: "nginx"
        path: "*.conf"
        directive: "ssl_protocols"
        value_patterns: ["TLSv1($|\\s|;)"]
      
      # Terraform (aws_lb_listener, aws_alb_listener)
      - kind: "hcl2"
        path: "*.tf"
        resource_types: ["aws_lb_listener", "aws_alb_listener"]
        attribute: "ssl_policy"
        value_patterns: ["ELBSecurityPolicy-TLS-1-0"]
    
    risk_tier: "CRITICAL"
    confidence_gain: "high"  # explicit literal
  
  # Cipher Suite Detection (weak)
  weak_cipher_rc4:
    name: "RC4 Cipher Suite"
    algorithm: "RC4"
    primitive: "encryption"
    description: "RC4 is cryptographically broken; do not use (RFC 7465)."
    patterns:
      - kind: "yaml"
        context: "**.tls.cipherSuites"
        value_patterns: ["RC4", "RC4-SHA", "RC4-MD5"]
      
      - kind: "nginx"
        directive: "ssl_ciphers"
        value_patterns: ["RC4"]
    
    risk_tier: "CRITICAL"
    confidence_gain: "high"
  
  # Certificate Verification Disabled
  ssl_verify_false:
    name: "Certificate Verification Disabled"
    algorithm: "TLS"
    primitive: "protocol_version"
    description: "Disabling certificate verification bypasses the entire trust model."
    patterns:
      - kind: "yaml"
        key_patterns: ["verify", "insecure", "ssl_verify", "ssl_check_cert"]
        value_patterns: ["false", "False", "no", "off", "disabled"]
      
      - kind: "hcl2"
        attribute_patterns: ["insecure", "skip_credentials_validation", "skip_requesting_account_id", "skip_cert_verification"]
        value_patterns: ["true", "True"]
    
    risk_tier: "CRITICAL"
    confidence_gain: "high"
  
  # RSA Key Size
  rsa_1024:
    name: "RSA-1024"
    algorithm: "RSA"
    primitive: "key_exchange"
    key_size: 1024
    description: "RSA-1024 is deprecated (NIST SP 800-56B Rev. 3); use RSA-2048 or RSA-4096."
    patterns:
      - kind: "yaml"
        context: "**.rsa.key_size"
        value_patterns: ["1024"]
      
      - kind: "hcl2"
        resource_types: ["tls_private_key"]
        attribute: "rsa_bits"
        value_patterns: ["1024"]
    
    risk_tier: "HIGH"
    confidence_gain: "high"
  
  # Unresolved Interpolation (honest reporting)
  unresolved_tls_var:
    name: "Unresolved TLS Configuration Variable"
    algorithm: "TLS"
    primitive: "protocol_version"
    description: "TLS version is referenced via variable; cannot determine literal value."
    patterns:
      - kind: "yaml"
        value_patterns: ["\\$\\{.*\\}", "\\{\\{.*\\}\\}"]
    
    risk_tier: null  # no risk until resolved
    confidence_gain: "unverified"

# Format-specific patterns
formats:
  yaml:
    supported_files: ["*.yaml", "*.yml"]
    parser: "PyYAML"
    depth_limit: 100  # max nesting
  
  hcl2:
    supported_files: ["*.tf"]
    parser: "python-hcl2"
    depth_limit: 50
  
  nginx:
    supported_files: ["nginx.conf", "*.conf"]
    parser: "custom_nginx_parser"
    depth_limit: null  # no nesting in nginx
  
  json:
    supported_files: ["*.json"]
    parser: "json"
    depth_limit: 100
```

**Rules YAML contract:**
- `patterns[].kind`: `"yaml"`, `"hcl2"`, `"nginx"`, `"json"`, `"github_actions"`, `"gitlab_ci"`
- `patterns[].value_patterns`: List of regex patterns to match; any match triggers the rule
- `confidence_gain`: `"high"` (explicit literal), `"probable"` (weak default), `"unverified"` (interpolation boundary)
- No rule may emit `confidence: "high"` unless the pattern contains only literal values (no variables, templates)

### 7.4 CLI Integration

```bash
# scanner/cli.py (already exists; IAC adds to it via COORDINATED ownership)

# Command signature (post-C-11 resolution):
python -m scanner.cli \
  /path/to/repo \
  --scan-type config \
  --min-confidence PROBABLE \
  --fail-on HIGH \
  --json-out findings.json \
  --source-context SOURCE

# Exit codes (FROZEN):
# 0 = success, no findings above threshold
# 1 = error (invalid path, parsing error)
# 2 = policy violation (findings at or above --fail-on threshold)

# Stdout (FROZEN JSON schema):
[
  {
    "file": "k8s/deployment.yaml",
    "line": 42,
    "algorithm": "TLSv1.0",
    "primitive": "protocol_version",
    "key_size": null,
    "library": "kubernetes",
    "language": "config",
    "detection_method": "config_analysis",
    "source_context": "SOURCE",
    "evidence": "tls_version: TLSv1.0",
    "confidence": "high",
    "confidence_band": "VERIFIED",
    "confidence_score": 0.95,
    "confidence_signals": ["literal_algorithm_arg"]
  },
  {
    "file": "terraform/main.tf",
    "line": 17,
    "algorithm": "RSA",
    "primitive": "key_exchange",
    "key_size": 1024,
    "library": "terraform",
    "language": "config",
    "detection_method": "config_analysis",
    "source_context": "SOURCE",
    "evidence": "rsa_bits = 1024",
    "confidence": "high",
    "confidence_band": "VERIFIED",
    "confidence_score": 0.95,
    "confidence_signals": ["literal_algorithm_arg"]
  },
  {
    "file": ".github/workflows/ci.yaml",
    "line": 8,
    "algorithm": "TLS",
    "primitive": "protocol_version",
    "key_size": null,
    "library": "github_actions",
    "language": "config",
    "detection_method": "config_analysis",
    "source_context": "SOURCE",
    "evidence": "tls_version: ${{ secrets.TLS_VERSION }}",
    "confidence": "unverified",
    "confidence_band": "UNVERIFIED",
    "confidence_score": 0.30,
    "confidence_signals": ["interpolation_boundary"]
  }
]
```

### 7.5 Database Schema (Migration 003, Pre-Written)

```sql
-- db/migrations/003_artifact_scanning.sql (§2.2 in contract)
-- Shared by DEP, CNT, BIN, IAC (one PR, one file)
-- This is PRE-WRITTEN in the contract; IAC only executes it, does not author it.

ALTER TABLE findings ADD COLUMN IF NOT EXISTS artifact_type TEXT NOT NULL DEFAULT 'SOURCE_FILE';
    -- VALUES: SOURCE_FILE | DEPENDENCY_MANIFEST | CONFIG_FILE | BINARY | CONTAINER_LAYER

ALTER TABLE findings ADD COLUMN IF NOT EXISTS artifact_ref TEXT;
    -- For CONFIG_FILE: relative file path (e.g., "k8s/deployment.yaml")
    -- For BINARY: "<section>+0x<offset>" (BIN's use)
    -- For CONTAINER_LAYER: layer digest or path (CNT's use)

ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_ecosystem TEXT;
    -- For DEPENDENCY_MANIFEST: "pypi", "npm", "maven", etc. (DEP's use)
    -- NULL for config, binary, container

ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_name TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS package_version TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS image_digest TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS layer_digest TEXT;

CREATE INDEX IF NOT EXISTS idx_findings_artifact_type ON findings(artifact_type);
CREATE INDEX IF NOT EXISTS idx_findings_package
    ON findings(package_ecosystem, package_name)
    WHERE package_name IS NOT NULL;
```

**Config engine usage of these columns:**
- `artifact_type = "CONFIG_FILE"` — always
- `artifact_ref = <relative path>` — e.g., `"terraform/vpc.tf"`, `"k8s/ingress.yaml"`
- `package_ecosystem, package_name, package_version` — unused (NULL), for DEP's use
- `image_digest, layer_digest` — unused (NULL), for CNT's use

### 7.6 API Response Schema

```python
# api/models.py (COORDINATED; config engine may add a model if needed)

# Already exists (inherited from Finding):
class FindingResponse(BaseModel):
    id: int
    scan_id: int
    file: str
    line: int
    algorithm: Optional[str]
    primitive: Optional[str]
    key_size: Optional[int]
    library: Optional[str]
    language: str
    detection_method: str
    source_context: str
    evidence: str
    confidence: str
    risk_tier: str
    
    # Added by migration 002 (CONF):
    confidence_score: Optional[float]
    confidence_band: Optional[str]
    confidence_signals: Optional[List[str]]
    
    # Added by migration 003 (all engines, including IAC):
    artifact_type: str
    artifact_ref: Optional[str]
    package_ecosystem: Optional[str]
    package_name: Optional[str]
    package_version: Optional[str]
    image_digest: Optional[str]
    layer_digest: Optional[str]

# GET /scans/{scan_id}/findings response:
{
  "data": [
    {
      "id": 42,
      "scan_id": 1,
      "file": "k8s/deployment.yaml",
      "line": 42,
      "algorithm": "TLSv1.0",
      "primitive": "protocol_version",
      "key_size": null,
      "library": "kubernetes",
      "language": "config",
      "detection_method": "config_analysis",
      "source_context": "SOURCE",
      "evidence": "tls_version: TLSv1.0",
      "confidence": "high",
      "risk_tier": "CRITICAL",
      "confidence_score": 0.95,
      "confidence_band": "VERIFIED",
      "confidence_signals": ["literal_algorithm_arg"],
      "artifact_type": "CONFIG_FILE",
      "artifact_ref": "k8s/deployment.yaml",
      "package_ecosystem": null,
      "package_name": null,
      "package_version": null,
      "image_digest": null,
      "layer_digest": null
    }
  ],
  "meta": {
    "total": 1,
    "scanned_files": 42,
    "scan_completed_at": "2026-09-20T14:32:00Z"
  }
}
```

### 7.7 Dashboard Column Definition (FindingsTable)

```javascript
// dashboard/src/lib/constants.js (COORDINATED; config engine adds an entry)

export const FINDINGS_COLUMNS = [
  // ... existing columns (added by FE, CONF, BIN, DFS, TRI) ...
  
  {
    id: "config_evidence",
    header: "Config Evidence",
    accessorKey: "artifact_type",
    cell: ({ row }) => {
      const finding = row.original;
      
      if (finding.artifact_type !== "CONFIG_FILE") {
        return null;
      }
      
      return (
        <div className="flex flex-col gap-1">
          <span className="text-t2 font-mono text-sm">
            {finding.artifact_ref || finding.file}
          </span>
          {finding.evidence && (
            <span className="text-t3 font-mono text-xs bg-surface p-1 rounded">
              {finding.evidence.substring(0, 100)}
              {finding.evidence.length > 100 ? "…" : ""}
            </span>
          )}
          {finding.line > 0 && (
            <span className="text-t3 text-xs">Line {finding.line}</span>
          )}
        </div>
      );
    },
    size: 300,
  }
];
```

---

## 8. Step-by-Step Implementation Plan

### Wave 0 (Prerequisite — owned by other features, blocking IAC start)

- [ ] **C-01 / C-18:** Pinned `cryptography` in `requirements.txt` (backend lane)
- [ ] **C-08:** Delete `dashboard/src/api.js` (frontend lane)
- [ ] **C-20:** Human sign-off on scope truth — is config/binary/container scanning in scope? (project lead)

### Wave 1 (CONF + CBOM refactor, unblocks IAC)

- [ ] **CONF phase 1:** Lands `scanner/confidence.py`, updates `db/migrations/002_confidence_scoring.sql`, adds `confidence_score`, `confidence_band`, `confidence_signals` columns (Maitreyi)
- [ ] **CBOM refactor (C-14):** Refactors `api/services/cbom_generator.py` to `build_cbom_from_findings()` signature, handles multi-engine artifact types (Maitreyi)
- [ ] **CLI wrapper (C-11):** Adds `--scan-type` flag to `scanner/cli.py`, coordinates with all four engines (Shashank)

### Wave 2 (Config Engine Implementation — IAC lane begins)

**Step 1: Create scanner/config_engine.py** *(1–2 days)*

1. Create `scanner/config_engine.py` with stubs for `scan_file()` and `scan_directory()`.
2. Implement YAML parser using PyYAML (already pinned).
3. Implement HCL2 parser using `python-hcl2` (pin in `requirements.txt`).
4. Implement Nginx parser (custom regex-free tokenizer for `ssl_protocols`, `ssl_ciphers` directives).
5. Test with fixtures; ensure no parsing errors break the walk.

**Step 2: Create scanner/rules/config.yaml** *(1 day)*

1. Write rule definitions for TLS versions, cipher suites, key sizes, verification settings.
2. Add patterns for Kubernetes, Docker Compose, Terraform, Nginx, GitHub Actions, GitLab CI.
3. Cross-reference with `scanner/rules/java.yaml` pattern structure.
4. Add comments explaining confidence_gain for each rule.

**Step 3: Integrate with scanner/constants.py** *(0.5 days, COORDINATED)*

1. Add `CONFIG_FILE_PATTERNS` tuple: `("*.yaml", "*.yml", "*.tf", "nginx.conf", "*.conf", "*.json", ".github/workflows/", ".gitlab-ci.yml")`
2. Add `CONFIG_SKIP_PATHS` if needed (do not collide with `SKIP_DIRS` — source walk skips `build/`, config walk must search it for Terraform state, etc.)
3. Verify no collision with `SKIP_DIRS`, `BINARY_SKIP_DIRS`, `CONTAINER_LAYER_SKIP_PATHS`.

**Step 4: Export engine entry point** *(0.5 days, COORDINATED)*

1. Update `scanner/__init__.py` to export config engine: `from scanner.config_engine import scan_file, scan_directory`

**Step 5: Integration with scanner/cli.py** *(2–3 days, COORDINATED with Shashank)*

1. Add `"config"` to the `--scan-type` choices in argparse.
2. Conditionally import and call config engine based on flag.
3. Aggregate findings from all selected engines.
4. Ensure JSON output contract is preserved (same schema across all engines).
5. Test with `--scan-type source --scan-type config` (mixed scan).

**Step 6: Test fixtures and unit tests** *(2 days)*

1. Create `tests/fixtures/config/`:
   - `k8s-vulnerable.yaml` — TLS 1.0, weak ciphers, verify: false
   - `k8s-clean.yaml` — TLS 1.3, strong ciphers, verify: true
   - `terraform-vulnerable.tf` — RSA-1024, unencrypted provisioner connection
   - `terraform-clean.tf` — RSA-2048, encrypted backend
   - `nginx-vulnerable.conf` — ssl_protocols TLSv1.0; ssl_ciphers RC4;
   - `nginx-clean.conf` — ssl_protocols TLSv1.3; strong ciphers
   - `docker-compose-vulnerable.yml` — plain HTTP, self-signed cert
   - `ci-unresolved.yaml` — `tls_version: ${{ secrets.TLS_VERSION }}`
   - Adversarial: comments containing "TLSv1.0", variable names like `tls_default_version_disabled`, etc.

2. Create `tests/test_config_engine.py`:
   - Test `scan_file()` against each fixture.
   - Test `scan_directory()` aggregation.
   - Test confidence scoring (explicit = `"high"`, interpolation = `"unverified"`).
   - Test source_context detection (SOURCE vs TEST_ONLY).
   - Negative tests: ensure comments and variable names do not trigger false positives.
   - Test error handling (malformed YAML, missing files).

3. Run `pytest tests/test_config_engine.py` and ensure all pass.

**Step 7: Documentation** *(1 day)*

1. Create `docs/CONFIG_IAC_SCANNING_SCOPE.md`:
   - Supported formats (Kubernetes, Terraform, Nginx, Docker Compose, GitHub Actions, GitLab CI, JSON)
   - Supported crypto signals (TLS versions, ciphers, key sizes, verification)
   - Unsupported (policy checks, semantic validation, runtime checks)
   - Rule details and examples

2. Update `docs/ECDAT_CLI_GUIDE.md`:
   - Add `--scan-type config` examples
   - Example output
   - Interpretation of findings

3. Update `PRODUCT_DESCRIPTION.md` §5 honesty table (coordinate with C-19, C-20):
   - Change status from "❌ Out of scope" to "✅ Implemented" once merged

### Wave 3 (Database & Backend Integration, blocked until CONF lands)

**Step 8: Database & Persistence** *(1 day, COORDINATED with Ronak)*

1. Migration 003 is pre-written in the contract; no IAC-specific migration.
2. Verify `findings.artifact_type`, `findings.artifact_ref` columns are added.
3. `api/services/scan_runner.py` already handles persistence; no changes needed.
4. Test: Run `pytest tests/test_crud.py` to ensure findings are persisted and queryable.

**Step 9: Risk Engine & CBOM** *(1 day, read-only integration)*

1. Verify `api/services/risk_engine.py` scores config findings correctly:
   - TLS 1.0 = CRITICAL
   - TLS 1.2 = HIGH (quantum-vulnerable)
   - TLS 1.3 = LOW
   - RSA-1024 = CRITICAL (overrides HIGH)
   - RC4, DES = CRITICAL
   - Unverified findings = risk tier unchanged, confidence as input

2. Verify CBOM generator (post-C-14 refactor) represents config assets:
   - `"cryptographic-asset"` with `"type": "configuration"`
   - `"artifact-ref": "k8s/deployment.yaml"`
   - Properties include `"tls_version"`, `"cipher_suite"`, `"key_size"`

3. No code changes needed; read-only integration via existing interfaces.

**Step 10: API & Dashboard** *(1–2 days, COORDINATED with Karan/Satyam)*

1. `api/routers/findings.py` already returns config findings via `/scans/{scan_id}/findings` (no changes).
2. Add config evidence column to `dashboard/src/lib/constants.js`:
   - Column shows `artifact_ref` (file path) and `evidence` snippet
   - Respects `artifact_type: CONFIG_FILE` filter
   - No changes to `FindingsTable.jsx` JSX (column-registry pattern, C-13)

3. Test: Run dashboard, navigate to a scan with config findings, verify table displays config evidence.

### Wave 4 (Final Integration & Smoke Tests)

**Step 11: End-to-end test** *(1 day)*

1. Run full integration test:
   ```bash
   python -m scanner.cli /path/to/multi-format-repo \
     --scan-type source --scan-type config \
     --json-out findings.json \
     --fail-on HIGH
   ```

2. Verify findings include both source (Python/Java/JS) and config (YAML/Terraform/Nginx).
3. Run CI gate via `.github/workflows/ecdat-scan.yml` — ensure config findings are blocked at `--fail-on HIGH`.

**Step 12: Database + API + Dashboard round-trip** *(1 day)*

1. POST scan with config files via `POST /scans`.
2. Verify findings persisted to `findings` table with `artifact_type: CONFIG_FILE`.
3. GET findings via `GET /scans/{scan_id}/findings`.
4. Verify API response includes config evidence.
5. Open dashboard, view scan, verify config findings displayed with evidence snippet.

**Step 13: Rollback & safety** *(0.5 days)*

1. Ensure config engine can be disabled via `--scan-type source` (default).
2. Document rollback: if config engine breaks, set `SCAN_ENABLE_CONFIG=false` (if feature gate added).
3. Existing source/Python/Java/JS tests remain green.

---

## 9. Naming & Symbol Registry

**This section provides the exhaustive list of every new identifier introduced by config-iac-scanning, checked against SYSTEM_INTERFACE_CONTRACT.md §3 naming conventions and shared-resource index for collisions.**

### Python Modules & Functions

| Name | Type | Namespace | Purpose | Collision Check |
|------|------|-----------|---------|-----------------|
| `config_engine` | Module | `scanner/` | Main config scanner entrypoint | No collision (new) |
| `scan_file()` | Function | `scanner.config_engine` | Standard engine contract | No collision (shared signature across all engines) |
| `scan_directory()` | Function | `scanner.config_engine` | Standard engine contract | No collision (shared signature across all engines) |
| `_parse_yaml()` | Function (private) | `scanner.config_engine` | YAML parsing helper | No collision (internal to config_engine) |
| `_parse_hcl2()` | Function (private) | `scanner.config_engine` | HCL2 parsing helper | No collision (internal to config_engine) |
| `_parse_nginx()` | Function (private) | `scanner.config_engine` | Nginx parsing helper | No collision (internal to config_engine) |
| `_detect_tls_version()` | Function (private) | `scanner.config_engine` | Rule applier for TLS versions | No collision (internal) |
| `_detect_cipher_suite()` | Function (private) | `scanner.config_engine` | Rule applier for ciphers | No collision (internal) |
| `_detect_key_size()` | Function (private) | `scanner.config_engine` | Rule applier for key sizes | No collision (internal) |
| `_detect_verify_disabled()` | Function (private) | `scanner.config_engine` | Rule applier for verify: false | No collision (internal) |

### Database Columns (Migration 003, Pre-Written)

| Column | Table | Data Type | Purpose | Collision Check |
|--------|-------|-----------|---------|-----------------|
| `artifact_type` | `findings` | `TEXT NOT NULL DEFAULT 'SOURCE_FILE'` | Discriminates config vs. source vs. binary | Pre-written in contract §2.2; value `"CONFIG_FILE"` owned by IAC |
| `artifact_ref` | `findings` | `TEXT` | File path for config findings | Pre-written in contract §2.2; usage for config: relative file path |

### Constants & Enums

| Name | Type | Namespace | Values (Config Engine) | Collision Check |
|------|------|-----------|------------------------|-----------------|
| `CONFIG_FILE_PATTERNS` | Tuple | `scanner.constants` | `("*.yaml", "*.yml", "*.tf", "nginx.conf", "*.conf", "*.json", ".github/workflows/*", ".gitlab-ci.yml")` | New tuple; no collision with `SKIP_DIRS` |
| `DETECTION_METHOD_CONFIG_ANALYSIS` | String constant | (implicit via code) | `"config_analysis"` | Pre-defined in contract §3.2; read-only |

### YAML Rule Keys (scanner/rules/config.yaml)

These are rule IDs and pattern keys within the YAML; they do not collide with Python identifiers but are listed for completeness:

| Rule ID | Category | Signals | Collision Check |
|---------|----------|---------|-----------------|
| `tls_v1_0`, `tls_v1_1`, `tls_v1_2`, `tls_v1_3` | TLS versions | `tls_version`, `ssl_protocols`, `ssl_policy` | No collision; format-agnostic rule IDs |
| `weak_cipher_rc4`, `weak_cipher_des`, `weak_cipher_md5` | Ciphers | `ssl_ciphers`, `cipherSuites` | No collision |
| `rsa_1024`, `ecdsa_p256` | Key sizes | `rsa_bits`, `key_size` | No collision |
| `ssl_verify_false`, `insecure_true` | Verification | `verify`, `insecure`, `ssl_verify_off` | No collision |

### CLI Flags

| Flag | Type | Ownership | Collision Check |
|------|------|-----------|-----------------|
| `--scan-type config` | Enum value | Shared (C-11), config engine only reads | No collision; `config` is one of `{source, dependency, config, binary, container}` |
| `--min-confidence` | Existing flag (modified by CONF) | Config engine reads this | No collision; CONF owns the flag, config engine respects it |
| `--fail-on` | Existing flag | Config engine respects it | No collision; existing, unchanged |

### Environment Variables

| Variable | Type | Ownership | Purpose | Collision Check |
|----------|------|-----------|---------|-----------------|
| (None) | — | — | Config engine introduces no new env vars | N/A |

### API Endpoints

| Endpoint | Method | Ownership | Config Engine Role | Collision Check |
|----------|--------|-----------|-------------------|-----------------|
| `/scans/{scan_id}/findings` | GET | Backend lane (shared) | Findings including config artifacts returned here | No collision; existing endpoint, config findings are mixed type |
| `/scans/{scan_id}/cbom` | GET | Backend lane (shared) | Config findings included in CBOM export | No collision; existing endpoint, post-C-14 refactor |

### Dashboard Components

| Component | Type | Ownership | Purpose | Collision Check |
|-----------|------|-----------|---------|-----------------|
| `config_evidence` column | Object key | `dashboard/src/lib/constants.js` | Column registry entry for FindingsTable | No collision; new column, unique ID |

---

## 10. Known Cross-Feature Risks

**All items below are extracted from SYSTEM_INTERFACE_CONTRACT.md §4 (Flagged Conflicts & Resolutions). Implementers must read these resolutions before starting; they are non-negotiable.**

### C-01: Migration Filename Collision (HIGH confidence, RESOLVED)

**Conflict:** Five proposals independently claimed `db/migrations/002_`. Overwriting breaks existing deployments.

**Resolution per contract §2.1:**
- Config/IaC scanning uses migration 003 (shared with DEP, CNT, BIN).
- Migration 003 is allocated file name `db/migrations/003_artifact_scanning.sql` with Docker Compose mount prefix `04_`.
- The file is pre-written in contract §2.2; all four engines execute the same migration, not separate ones.
- **Action for IAC:** Do not create a separate migration file. Use the pre-written 003.

---

### C-02: Sub-Threshold Findings Persistence (MEDIUM confidence, SIGN-OFF PENDING)

**Conflict:** `api/services/scan_runner.py` currently filters `finding.get("confidence") == "high"` before persisting. Config findings with `confidence: "unverified"` (unresolved variables) would be silently dropped from the database, even though they are printed to the CLI.

**Current state:** Conflicting. Unresolved config variables are honest findings (`confidence: "unverified"`) but would disappear from the database.

**Resolution per contract:**
- CONF (Wave 1) replaces the gate with a configurable band threshold (`SCAN_MIN_CONFIDENCE_BAND`, default `PROBABLE`).
- Until CONF lands, config findings below `"high"` are CLI-only and not persisted.
- Config engine scope document must note: "Sub-threshold findings (confidence < high) are displayed in the CLI but not persisted until Wave 2. This is a known limitation."

**Action for IAC:** 
1. Emit all findings (high and unverified) from the engine.
2. Document the limitation in `docs/CONFIG_IAC_SCANNING_SCOPE.md`.
3. Do not attempt to modify `scan_runner.py`; wait for CONF.

---

### C-03: Confidence Backfill & Field Addition (MEDIUM confidence, SIGN-OFF PENDING)

**Conflict:** `scanner/finding.py` is FROZEN. Only CONF may add fields (once).

**Current state:** CONF owns adding `confidence_score`, `confidence_band`, `confidence_signals` columns and backfilling existing rows. Config engine can only emit these fields; it cannot change the schema.

**Resolution per contract §1.1:**
- CONF lands first (Wave 1) with migration 002.
- All engines (including config) then emit the new fields.
- Legacy rows (pre-CONF) have NULL values; CONF defines backfill logic.

**Action for IAC:**
1. Import `confidence` and related fields from `scanner.finding.Finding`.
2. Emit `confidence`, `confidence_band`, `confidence_score`, `confidence_signals` in findings.
3. Do not add fields to `Finding`; only CONF may do this.
4. Tests must pass both with and without the new fields (backward compatibility).

---

### C-11: CLI Flag Grammar Collision (MEDIUM confidence, SIGN-OFF PENDING)

**Conflict:** DEP (`--target-type`), CNT (`--target-type`), BIN (`--binaries`), IAC (`optional target type`), CONF (`--min-confidence`) all propose different flag schemas. Nothing coordinates defaults.

**Current state:** Conflicting on flag naming and value sets.

**Resolution per contract §3.5:**
- One repeatable `--scan-type {source,dependency,config,binary,container}` flag, default `source` only.
- `--image-tar PATH` is valid only with `--scan-type container`.
- `--min-confidence BAND` is CONF's (added by CONF, Wave 1).
- Config engine contributes `"config"` to the choices; no other flag changes.

**Action for IAC:**
1. In `scanner/cli.py`, add `"config"` to the `--scan-type` choices.
2. Do not introduce a new flag like `--target-type` or `--config-scan`; use the shared `--scan-type config`.
3. Ensure mixed scans work: `--scan-type source --scan-type config` runs both engines in one scan.

---

### C-12: Skip Path Collision (HIGH confidence, RESOLVED)

**Conflict:** `SKIP_DIRS` contains `target`, `build`, `dist` — precisely where compiled artefacts live. Config engine needs to search these directories for Terraform state, `build/nginx.conf`, etc.

**Resolution per contract §3.2:**
- Keep `SKIP_DIRS` as the source-walk list, unchanged.
- Add named per-engine sets: `CONFIG_FILE_PATTERNS` (file matchers, not a skip set).
- Config engine is responsible for discovering its own files; do not assume `SKIP_DIRS` applies.

**Action for IAC:**
1. Define `CONFIG_FILE_PATTERNS` in `scanner/constants.py`.
2. In `scanner/config_engine.py`, use a custom discovery walk that respects `SKIP_DIRS` for **traversal** but not for **file matching**. (I.e., skip `build/`, but check `build/` for `nginx.conf` if found.)
3. Do not modify `SKIP_DIRS`.

---

### C-13: FindingsTable Column Contention (MEDIUM confidence, SIGN-OFF PENDING)

**Conflict:** Seven features (CNT, BIN, IAC, CONF, DFS, TRI, FE) simultaneously edit `dashboard/src/components/FindingsTable.jsx`, causing merge conflicts.

**Current state:** Conflicting through sheer contention.

**Resolution per contract:**
- DFS lands the column-registry architecture first (Wave 2).
- FE lands presentation (Tailwind, badges) second (Wave 3).
- Each remaining feature (including IAC) adds a column definition to `dashboard/src/lib/constants.js` (a shared registry object) rather than editing `FindingsTable.jsx`.

**Action for IAC:**
1. Add a column entry to `lib/constants.js` with ID `"config_evidence"`.
2. Do not edit `FindingsTable.jsx` JSX; the component reads from the registry.
3. Column definition includes `accessorKey: "artifact_type"` (or similar), targeting config-specific fields.
4. Await DFS merge before doing dashboard work.

---

### C-14: CBOM Generator Refactor (COORDINATED, being worked by Maitreyi)

**Conflict:** Current `cbom_generator.py` is monolithic and hard-coded for source findings. Five features (CNT, BIN, IAC, DEP, CBV) depend on it for representing different artifact types.

**Current state:** Being refactored to `build_cbom_from_findings(findings: list[Finding]) -> CBOMDocument`.

**Resolution per contract §1.2:**
- Refactor to accept a list of findings (any mix of artifact types) and generate a unified CBOM.
- Config findings are represented as `"cryptographic-asset"` components with `"artifact-ref": "k8s/deployment.yaml"` and properties like `"tls_version": "1.0"`.

**Action for IAC:**
1. No code changes needed; read-only integration.
2. Ensure config findings are included in scans passed to `cbom_generator.py`.
3. Test: Run CBOM export on a scan with config findings; verify CycloneDX 1.6 output includes config assets.

---

### C-20: Scope Truth Contradiction (LOW confidence, SIGN-OFF REQUIRED BEFORE IAC STARTS)

**Conflict:** `AGENT_RULES.md` lists binary/container/dependency/config scanning as in-scope. Pitch documents (PRODUCT_DESCRIPTION.md) list these as differentiators ("not other tools") and imply out-of-scope.

**Current state:** Conflicting by contradiction. **Blocks all four engines (DEP, CNT, BIN, IAC) from starting implementation.**

**Resolution pending:** Human sign-off on whether these features are in scope. Until resolved, IAC is **blocked from Wave 2**.

**Action for IAC:**
1. **Do not start implementation until C-20 is resolved.**
2. When resolved, align scope docs (§3 of this spec) and `docs/CONFIG_IAC_SCANNING_SCOPE.md` with the signed-off scope.
3. If out-of-scope: archive this specification and wait for Phase 2.
4. If in-scope: proceed to Wave 2.

---

## 11. Pre-Answered Ambiguities

**This section lists 10+ concrete situations an implementing agent could be confused by, each with a rule. Every open sign-off item from the contract touching this feature is answered here with the team's resolved decision (if signed off) or flagged for human sign-off.**

### Scenario 1: "Should I detect cryptographic libraries imported in Terraform?"

**Situation:** A Terraform file contains `provider "aws" { ... }` which internally uses cryptography. Should config engine report this?

**Answer:** **No.** Config engine detects **configuration-declared cryptography** (explicit `tls_version: TLSv1.0` settings), not library usage. Detecting provider-internal crypto is an opaque-binary concern, outside scope. If an AWS provider uses weak crypto, that is a supply-chain discovery problem, not a config-scanning problem.

**Rule:** Config engine only reports crypto settings that are **explicitly declared in the configuration file**, not inferred provider behavior.

---

### Scenario 2: "A YAML file has an unresolved variable for TLS version. What confidence should I assign?"

**Situation:**
```yaml
spec:
  tls:
    minimum_version: ${TLS_MIN_VERSION}
```

**Answer per contract §5.1 (Open Items) C-02 & §2.2 (Migration 003):** 

1. **Emit the finding** with `confidence: "unverified"` and `confidence_band: "UNVERIFIED"`.
2. **Report the interpolation boundary** in the evidence: `"minimum_version: ${TLS_MIN_VERSION}"`.
3. **Add a signal** to `confidence_signals`: `["interpolation_boundary"]`.
4. The risk engine will score this as `risk_tier: null` (cannot be assessed without resolved value).
5. **The finding is persisted only if** `SCAN_MIN_CONFIDENCE_BAND >= "UNVERIFIED"` (set by CONF in Wave 1). Until then, it appears in CLI but not in the database.

**Rule:** Never guess the value of an unresolved variable. Report the boundary and let the human resolve it.

---

### Scenario 3: "A config file has TLS disabled in a comment. Should I detect it?"

**Situation:**
```yaml
# tls_enabled: false  # old config, do not use
spec:
  tls:
    enabled: true
```

**Answer:** **No.** Comments are **not source code** (per AGENT_RULES.md #5, no regex matching on comments). Only the active configuration `tls: { enabled: true }` is scanned. The commented line is ignored.

**Rule:** Parse config syntax structures only; ignore comments.

---

### Scenario 4: "A variable name is `RSA_1024_DISABLED`. Should I detect RSA-1024?"

**Situation:**
```yaml
key_algorithm: RSA
key_bits: ${RSA_1024_DISABLED}
```

**Answer:** **No.** The variable name is irrelevant; only the actual value matters. The value `${RSA_1024_DISABLED}` is unresolved, so emit `confidence: "unverified"`. Do not parse variable names for cryptographic hints.

**Rule:** Match **values** only, never variable or function names.

---

### Scenario 5: "Should I support Ansible playbooks or Chef recipes?"

**Situation:** A user runs `ecdat scan --scan-type config` on a repo with `site.yml` (Ansible) and `cookbooks/` (Chef).

**Answer per §3 (Scope):** **Out-of-scope for v1.** Supported formats are:
- Kubernetes/Docker Compose YAML
- Terraform HCL
- Nginx configs
- GitHub Actions YAML
- GitLab CI YAML
- Generic JSON (if cryptographic keys are present)

Ansible and Chef are domain-specific languages with their own DSLs; adding them requires separate parsers and rule sets. **Scope is locked.** If a user needs Ansible support, it becomes a Wave 2 proposal.

**Rule:** Stick to the in-scope formats list in §3. Reject unsupported file types with a log message (not an error) and skip them.

---

### Scenario 6: "A Terraform file has a conditional: `count = var.enable_insecure_tls ? 1 : 0`. Should I detect it?"

**Situation:**
```hcl
resource "aws_lb_listener" "example" {
  count             = var.enable_insecure_tls ? 1 : 0
  ssl_policy        = "ELBSecurityPolicy-TLS-1-0"
  protocol          = "HTTPS"
}
```

The `ssl_policy` is weak, but the resource itself is conditionally created. Should I report it?

**Answer:** **Yes.** Config scanning reports **declared settings**, not deployment paths. The configuration declares a weak TLS policy; whether it is deployed depends on runtime variables. Emit the finding as `confidence: "high"` (explicit `ELBSecurityPolicy-TLS-1-0`), and let the risk engine and analyst decide if the condition mitigates the risk.

**Rule:** Scan all resources, regardless of conditionals. If a setting is declared, report it, even if the resource may not be deployed.

---

### Scenario 7: "Does the config engine use the risk_engine to score findings?"

**Situation:** The config engine has just emitted a finding for RSA-1024. Should it call `risk_engine.score_findings()` to assign the risk tier?

**Answer:** **No.** The config engine is a **discovery engine** only. It emits the finding with the raw evidence (e.g., `algorithm: "RSA", key_size: 1024`). The **risk engine** (FROZEN at `api/services/risk_engine.py`) computes the risk tier asynchronously in Wave 3. The engines never call the risk engine; they emit findings, and the API layer scores them.

**Rule:** Config engine outputs only what it found; risk scoring is a separate pipeline step.

---

### Scenario 8: "How do I handle a YAML file with 500 KB of configuration data?"

**Situation:** `SCAN_MAX_ARTIFACT_BYTES` is set to 100 MB (default), but the parser tries to load a 500 KB YAML file into memory.

**Answer per contract §3.3 (environment variables):** `SCAN_MAX_ARTIFACT_BYTES` is a shared limit across all engines. Config engine must:
1. Check file size before parsing.
2. If size > limit, log a warning and skip the file.
3. Continue scanning other files.
4. Do not emit a `Finding` for the skipped file (size is not a cryptographic weakness).

**Rule:** Respect `SCAN_MAX_ARTIFACT_BYTES`. Skip large files with a log, not an error.

---

### Scenario 9: "A YAML file has both TLS 1.0 and TLS 1.3 configured. Should I report both?"

**Situation:**
```yaml
spec:
  ingress:
    - tls:
        minimum_version: TLSv1.0
        maximum_version: TLSv1.3
```

**Answer:** **Yes.** Emit two separate findings:
1. `Finding(algorithm: "TLSv1.0", line: 5, ...)`
2. `Finding(algorithm: "TLSv1.3", line: 6, ...)`

Both are reported. The risk engine scores TLS 1.0 as CRITICAL and TLS 1.3 as LOW. The analyst reviews both and can acknowledge the 1.3 setting as a mitigating factor.

**Rule:** Emit one `Finding` per detected crypto setting, not one per file.

---

### Scenario 10: "If a config finding is marked `source_context: TEST_ONLY`, does the risk engine ignore it?"

**Situation:** A test fixture file `tests/e2e/tls-test.yaml` has `tls_version: TLSv1.0`.

**Answer:** **No.** The risk engine scores the finding as CRITICAL regardless of `source_context`. However:
1. The CLI can filter via `--source-context SOURCE` (filters out TEST_ONLY).
2. The dashboard can display a badge indicating "TEST_ONLY".
3. The analyst may deprioritize remediation of test findings.

**Rule:** Emit `source_context: TEST_ONLY` accurately, but do not assume it changes the risk score. The analyst and workflow decide the priority.

---

### Scenario 11: "Should I support YAML anchors and aliases in detection?"

**Situation:**
```yaml
tls: &tls_1_0
  version: TLSv1.0

frontend:
  tls: *tls_1_0
```

**Answer:** **Yes, if the parser supports it.** PyYAML handles anchors and aliases transparently — the parsed data structure already has the dereferenced value, not the reference string. So `frontend.tls.version` is `"TLSv1.0"`, not `*tls_1_0`, and detection works as normal.

**Rule:** Let PyYAML resolve anchors. Your detection logic sees the final values, not the references.

---

### Scenario 12: "SIGN-OFF ITEM C-20: Is config-iac-scanning in scope?"

**Situation:** The project's pitch documents say "we do source-code scanning, not binary/container/config." But `AGENT_RULES.md` lists config scanning as in-scope.

**Answer:** **BLOCKED. This feature cannot proceed until human sign-off resolves C-20.**

If **in-scope (signed off):** Proceed with this specification as written.  
If **out-of-scope (signed off):** Archive this specification. Config scanning becomes a Phase 2 proposal.

**Current status:** Awaiting project lead decision. **Do not start Wave 2 implementation until this is resolved.**

---

### Scenario 13: "SIGN-OFF ITEM C-02: Should unverified findings be persisted?"

**Situation:** A config file has `tls_version: ${SECURE_TLS_VERSION}`. The finding is emitted with `confidence: "unverified"`. Should it be saved to the database?

**Answer per contract:** **Awaiting sign-off.**

**Current temporary rule (until CONF lands Wave 1):**
- Emit the finding to stdout (CLI).
- Do NOT persist to the database (current `scan_runner.py` filters `confidence != "high"`).
- Document this as a known limitation: "Unverified config findings appear in the CLI but are not stored in the database until CONF phase 1 lands."

**After CONF lands:**
- `SCAN_MIN_CONFIDENCE_BAND` will allow configuring the threshold.
- Unverified findings (default: drop) can be persisted if the threshold is lowered.

---

### Scenario 14: "Should I test config engine against live running containers?"

**Situation:** A user runs `ecdat scan --scan-type config /var/run/docker/containers/` to scan Docker container configs on a live system.

**Answer:** **No.** Config scanning is static, offline, and source-code-only. It does not interact with running systems. If a user wants to scan container configurations, they should provide the extracted config files (e.g., `Dockerfile`, `docker-compose.yml`), not running container introspection.

**Rule:** Config engine scans files, not systems. No API calls, no container runtimes, no system binaries invoked.

---

## 12. Test Plan / Definition of Done

### Test Execution Commands

#### Unit Tests (Config Engine)

```bash
# Run config engine unit tests
pytest tests/test_config_engine.py -v

# Expected output:
# tests/test_config_engine.py::test_scan_file_yaml_vulnerable PASSED
# tests/test_config_engine.py::test_scan_file_yaml_clean PASSED
# tests/test_config_engine.py::test_scan_file_terraform_rsa_1024 PASSED
# tests/test_config_engine.py::test_scan_directory_aggregation PASSED
# tests/test_config_engine.py::test_confidence_unverified_interpolation PASSED
# tests/test_config_engine.py::test_source_context_test_only PASSED
# tests/test_config_engine.py::test_negative_comment_no_finding PASSED
# tests/test_config_engine.py::test_negative_variable_name_no_finding PASSED
# tests/test_config_engine.py::test_error_handling_malformed_yaml PASSED
# ... (18 total tests, all green)
```

#### CLI Integration Tests

```bash
# Test config scanning via CLI
python -m scanner.cli tests/fixtures/config/ --scan-type config --json-out /tmp/config_findings.json

# Verify JSON output
jq '.[] | select(.language == "config") | .detection_method' /tmp/config_findings.json
# Expected: all entries have "config_analysis"

# Test mixed scan (source + config)
python -m scanner.cli tests/fixtures/ --scan-type source --scan-type config --json-out /tmp/mixed_findings.json

# Count findings by language
jq '.[].language | group_by(.) | map({language: .[0], count: length})' /tmp/mixed_findings.json
# Expected: language: "config" count > 0, plus source languages

# Test --fail-on policy gate
python -m scanner.cli tests/fixtures/config/ --scan-type config --fail-on CRITICAL
# Exit code: 2 (policy violation, if CRITICAL findings exist)

# Test --min-confidence filter (post-CONF, Wave 1)
python -m scanner.cli tests/fixtures/config/ --scan-type config --min-confidence PROBABLE --json-out /tmp/filtered.json
# Expected: findings with confidence_band >= PROBABLE included
```

#### Database & API Tests

```bash
# Run database integration tests (requires PostgreSQL or in-memory SQLite in test mode)
pytest tests/test_crud.py::test_save_config_finding -v

# Expected output:
# test_save_config_finding PASSED
# — Verifies findings are persisted with artifact_type: CONFIG_FILE

# Run scan_runner integration test
pytest tests/test_scan_runner.py -v -k "config"

# Expected output:
# test_scan_runner_accepts_config_findings PASSED
# test_scan_runner_persists_config_findings PASSED
# test_scan_runner_applies_confidence_gate PASSED (with CONF, Wave 1)
```

#### Dashboard Tests (End-to-End, Wave 3)

```bash
# Run dashboard component tests (Playwright/Cypress)
npm run test:e2e --prefix dashboard

# Expected output:
# ✓ Renders findings table with config evidence column
# ✓ Config findings display artifact_ref and evidence snippet
# ✓ Config findings filterable by artifact_type
# ✓ Config findings included in risk summary chart

# Verify in browser
docker compose up -d
# Navigate to https://localhost:8443/
# Create a scan with config files
# Verify findings table displays config evidence
```

### Definition of Done Checklist

#### Code Completion

- [ ] `scanner/config_engine.py` implemented with `scan_file()` and `scan_directory()` functions
- [ ] `scanner/rules/config.yaml` written with rules for TLS, ciphers, key sizes, verification
- [ ] `scanner/constants.py` updated with `CONFIG_FILE_PATTERNS` (no collision with `SKIP_DIRS`)
- [ ] `scanner/__init__.py` exports config engine entry point
- [ ] `scanner/cli.py` integrated with `--scan-type config` flag (Shashank to merge)
- [ ] All new code follows Python `snake_case` naming per contract §3.1
- [ ] No PascalCase function names; no `ECDAT*()` prefixes
- [ ] No regex-based detection (contract AGENT_RULES.md #5); only structural parsing

#### Testing

- [ ] `tests/test_config_engine.py` written with 18+ test cases (positive, negative, error)
- [ ] `tests/fixtures/config/` contains 8+ fixture files (vulnerable, clean, edge cases)
- [ ] All tests pass: `pytest tests/test_config_engine.py -v` (exit 0)
- [ ] No deprecation warnings; no lint errors (if linting enabled)
- [ ] Mixed-scan tests pass: `--scan-type source --scan-type config`
- [ ] Confidence scoring tests pass: explicit literals = "high", interpolations = "unverified"
- [ ] Negative tests pass: comments and variable names do not trigger false findings

#### Database & API

- [ ] Migration 003 (pre-written) runs without errors: `docker compose down -v && docker compose up db` (fresh schema)
- [ ] Findings persisted with `artifact_type: "CONFIG_FILE"` and `artifact_ref: <file_path>`
- [ ] `/scans/{scan_id}/findings` API returns config findings in response
- [ ] CBOM export includes config assets (post-C-14 refactor, Wave 3)
- [ ] Risk engine scores config findings correctly (Wave 3)

#### Documentation

- [ ] `docs/CONFIG_IAC_SCANNING_SCOPE.md` written (1–2 pages)
  - Supported formats, signals, unsupported features, rule details, examples
- [ ] `docs/ECDAT_CLI_GUIDE.md` updated with config scanning examples
- [ ] `PRODUCT_DESCRIPTION.md` §5 table updated (status changes from "❌" to "✅" once merged)
- [ ] Code comments added for non-obvious logic (e.g., interpolation detection, confidence assignment)
- [ ] No broken Markdown; headings match the actual content

#### CI/CD & Deployment

- [ ] `.github/workflows/ecdat-scan.yml` runs config scanning tests on PR (existing workflow, no changes)
- [ ] `docker-compose.yml` builds and starts all services without errors (including fresh migration 003)
- [ ] `.env.example` is up-to-date (no new env vars for config engine)
- [ ] No hardcoded paths, keys, or credentials in code or fixtures

#### Cross-Feature Readiness

- [ ] CONF (Wave 1) landed; `confidence_band` and `confidence_score` fields are available
- [ ] CLI wrapper (C-11) resolved; `--scan-type` flag is canonical
- [ ] CBOM generator refactored (C-14); multi-engine support is in place
- [ ] Dashboard column registry (C-13) is in place; config evidence column added to `lib/constants.js`
- [ ] No violations of frozen files (`scanner/finding.py`, `api/services/risk_engine.py`, `api/services/scan_runner.py`)

#### Sign-Off Items

- [ ] C-20 (scope truth) is signed off; config scanning is confirmed in-scope
- [ ] C-02 (sub-threshold persistence) is acknowledged; limitation documented
- [ ] C-11 (CLI flag grammar) confirms `--scan-type config` is the canonical flag

### Test Coverage Metrics

- **Unit test coverage:** ≥ 85% of config_engine.py lines executed
- **Integration coverage:** Config findings flow end-to-end (CLI → DB → API → Dashboard)
- **Negative test coverage:** False positives ruled out (comments, variable names, etc.)

---

## 13. Rollback Plan

### If Config Engine Breaks the Build

**Situation:** Config scanning is merged; existing tests fail, or the production CI gate is blocked.

**Immediate actions (< 15 min):**

1. **Disable config scanning in CI:**
   ```bash
   git revert <config-scanning-commit>
   ```

2. **If revert is not feasible:** Temporarily disable the feature flag:
   ```bash
   # (If SCAN_ENABLE_CONFIG is added in future)
   export SCAN_ENABLE_CONFIG=false
   pytest  # Run CI tests
   ```

3. **Communicate:** Post a rollback message to the team channel with the root cause.

### If Database Migration 003 Fails

**Situation:** Fresh docker compose fails at migration 003; `findings` table is not updated.

**Immediate actions:**

1. **Check migration logs:**
   ```bash
   docker logs ecdat-db
   # Look for SQL syntax errors, column conflicts, etc.
   ```

2. **Manual rollback (development only):**
   ```bash
   docker compose down -v  # Destroy volumes
   docker compose up db    # Rebuild from schema.sql (ignores failed migration)
   ```

3. **Investigate:** Check migration 003 SQL syntax and `docker-compose.yml` mount order (contract §2.1).

4. **If C-01 merge-order issue:** Ensure migration numbers 002–008 are properly reserved and mounted in lexical order (`03_` for 002, `04_` for 003, etc. in docker-compose.yml).

### If Config Findings Are Not Persisted

**Situation:** Config engine emits findings to stdout, but findings are not in the database.

**Debugging steps:**

1. **Check scan_runner.py confidence gate:**
   ```bash
   python -c "
   from api.services.scan_runner import run_scan
   findings = [...]  # config findings
   result = run_scan(findings)
   print(f'Persisted: {len(result)} findings')
   "
   ```
   If result is 0, the gate is filtering. **Wait for CONF (Wave 1)** to configure the threshold.

2. **Check database connection:**
   ```bash
   psql -U postgres -d ecdat -c "SELECT COUNT(*) FROM findings WHERE artifact_type = 'CONFIG_FILE';"
   ```
   If query fails: DB is not reachable or schema is incomplete.

3. **Check API logs:**
   ```bash
   docker logs ecdat-api | grep -i "config_analysis"
   ```
   If no log entries: findings are not reaching the API.

### If Dashboard Table Does Not Show Config Evidence

**Situation:** Config findings are in the database but the dashboard table does not display the config evidence column.

**Debugging steps:**

1. **Verify column registry:** Check `dashboard/src/lib/constants.js` for the `config_evidence` entry.
2. **Check API response:** Use browser DevTools → Network tab; inspect the `/api/scans/{scan_id}/findings` response. Verify `artifact_type` and `artifact_ref` are present.
3. **Verify table mounts column:** Inspect `FindingsTable.jsx` to ensure it reads from `FINDINGS_COLUMNS` registry (C-13).
4. **Await DFS merge (Wave 2):** The column-registry pattern may not be live until DFS lands.

### If Confidence Scoring Is Wrong

**Situation:** Config findings are assigned wrong confidence band or score.

**Immediate check:**

1. **This is a CONF (Wave 1) feature.** Until CONF lands, config engine emits `confidence: "high"` or `"unverified"` as raw strings.
2. **After CONF lands:** Verify `scanner/confidence.py` is imported and called correctly:
   ```bash
   grep -r "from scanner.confidence import" scanner/config_engine.py
   ```

3. **If confidence band is NULL in the DB:** Migration 002 (CONF) may not have run. Check `db/migrations/002_confidence_scoring.sql` mount in `docker-compose.yml`.

### Rollback Decision Tree

```
Config scanning broken?
├─ Yes, merge conflicts in other features
│  └─ Action: `git revert <commit>`
│
├─ Yes, database migration fails
│  └─ Action: `docker compose down -v && docker compose up db`
│
├─ Yes, findings not persisted
│  └─ Is CONF (Wave 1) merged?
│     ├─ No: This is expected (sub-threshold gate). Document as limitation.
│     └─ Yes: Debug API connection (see above).
│
├─ Yes, dashboard does not display config
│  └─ Is DFS (Wave 2) merged? If no, await merge.
│
└─ Findings are wrong (false positives, wrong risk tier)
   └─ Revert this feature; file a bug; remerge after fix.
```

### Escalation

If rollback does not restore the build within 30 minutes, **escalate to the feature owner and project lead.**

---

## Appendix A: Referenced External Documents

- **SYSTEM_INTERFACE_CONTRACT.md** — This contract (sections 1–8)
- **ARCHITECTURE.md** — System-wide design patterns, engine signatures
- **AGENT_RULES.md** — Team decision rules (no regex, no code execution)
- **db/schema.sql** — Canonical database schema
- **scanner/finding.py** — Finding dataclass definition (FROZEN)
- **scanner/cli.py** — CLI dispatcher (COORDINATED)
- **scanner/constants.py** — Skip directories, file patterns (COORDINATED)
- **PRODUCT_DESCRIPTION.md** — Product positioning and scope (to be updated)
- **docs/ECDAT_CLI_GUIDE.md** — CLI guide (to be updated)

---

## Appendix B: Example Config Findings

### Example 1: Kubernetes YAML with TLS 1.0

**File:** `k8s/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example
spec:
  tls:
    - hosts:
        - example.com
      secretName: tls-secret
  rules:
    - host: example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: example
                port:
                  number: 443
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tls-policy
spec:
  ingress:
    - from:
        - podSelector: {}
      ports:
        - protocol: TCP
          port: 443
          tls_version: TLSv1.0
```

**Finding emitted:**

```json
{
  "file": "k8s/ingress.yaml",
  "line": 24,
  "algorithm": "TLSv1.0",
  "primitive": "protocol_version",
  "key_size": null,
  "library": "kubernetes",
  "language": "config",
  "detection_method": "config_analysis",
  "source_context": "SOURCE",
  "evidence": "tls_version: TLSv1.0",
  "confidence": "high",
  "confidence_band": "VERIFIED",
  "confidence_score": 0.95,
  "confidence_signals": ["literal_algorithm_arg"],
  "artifact_type": "CONFIG_FILE",
  "artifact_ref": "k8s/ingress.yaml"
}
```

### Example 2: Terraform with RSA-1024

**File:** `terraform/main.tf`

```hcl
resource "tls_private_key" "example" {
  algorithm   = "RSA"
  rsa_bits    = 1024  # ← WEAK
}

resource "aws_db_instance" "example" {
  engine               = "postgres"
  db_name              = "example"
  username             = "admin"
  password             = random_password.db_password.result
  allocated_storage    = 20
  storage_type         = "gp2"
  engine_version       = "13.7"
  publicly_accessible  = false
  multi_az             = true
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.db_key.arn
  skip_final_snapshot  = false
}
```

**Finding emitted:**

```json
{
  "file": "terraform/main.tf",
  "line": 4,
  "algorithm": "RSA",
  "primitive": "key_exchange",
  "key_size": 1024,
  "library": "terraform",
  "language": "config",
  "detection_method": "config_analysis",
  "source_context": "SOURCE",
  "evidence": "rsa_bits = 1024",
  "confidence": "high",
  "confidence_band": "VERIFIED",
  "confidence_score": 0.95,
  "confidence_signals": ["literal_algorithm_arg", "key_size_literal"],
  "artifact_type": "CONFIG_FILE",
  "artifact_ref": "terraform/main.tf"
}
```

### Example 3: Nginx with RC4 Cipher

**File:** `nginx/nginx.conf`

```nginx
http {
  upstream backend {
    server backend1.example.com:8080;
    server backend2.example.com:8080;
  }

  server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate     /etc/ssl/certs/example.crt;
    ssl_certificate_key /etc/ssl/private/example.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         "RC4:AES128:AES256:HIGH:!aNULL:!MD5";  # ← WEAK
    ssl_prefer_server_ciphers on;

    location / {
      proxy_pass http://backend;
    }
  }
}
```

**Findings emitted:**

1. TLS 1.2 (older but supported):
   ```json
   {
     "file": "nginx/nginx.conf",
     "line": 13,
     "algorithm": "TLSv1.2",
     "primitive": "protocol_version",
     "confidence": "high",
     "artifact_ref": "nginx/nginx.conf"
   }
   ```

2. RC4 cipher:
   ```json
   {
     "file": "nginx/nginx.conf",
     "line": 15,
     "algorithm": "RC4",
     "primitive": "encryption",
     "confidence": "high",
     "artifact_ref": "nginx/nginx.conf"
   }
   ```

---

**End of Specification. Version 1.0, ready for implementation pending C-20 human sign-off.**
