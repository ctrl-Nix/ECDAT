# ECDAT CLI Reference and CI/CD Integration Guide

> **Purpose.** ECDAT performs cryptographic asset discovery on a local source
> tree. The normal scan path is offline: it reads a mounted local file system,
> performs static analysis, assigns deterministic classical/PQC risk metadata,
> and writes findings locally. It does **not** contact a dashboard, database,
> model provider, or other external service unless an operator explicitly adds
> `--sync-url` together with a signed report bundle and mTLS credentials.

## 1. Installation and Local Image Build

ECDAT is designed to be run as a container so the analyzer version, Python
runtime, and tree-sitter bindings remain consistent.

```bash
git clone <your-approved-ecdat-repository-url>
cd ECDAT
docker build --tag ecdat-scanner:local .
```

The image uses Python 3.11 and runs as a non-root user. Mount source targets as
read-only (`:ro`) to make local scan integrity explicit.

## 2. Command Synopsis

```text
python -m scanner.cli TARGET
  [--json-out PATH]
  [--summary-only]
  [--redact-paths]
  [--source-context {SOURCE,TEST_ONLY,DEMO_ONLY}]
  [--fail-on {CRITICAL,HIGH,MEDIUM,LOW}]
  [--data-shelf-life-years YEARS]
  [--report-bundle PATH --organization-id ID --repository-id ID
   --agent-id ID --signing-key PEM]
  [--sync-url HTTPS_URL --client-cert PEM --client-key PEM
   --ca-cert PEM --sync-timeout SECONDS]
```

`TARGET` is a local source file or directory. The scanner supports Python,
Java, JavaScript, TypeScript, JSX, and TSX files. It ignores dependency and
generated-code directories such as `node_modules`, `.git`, `.venv`, `dist`,
and nested build `target` directories. The selected root itself is never
discarded merely because it is mounted as `/target`.

## 3. Core Offline Scan Commands

### Full local finding inventory

```bash
docker run --rm \
  -v "$PWD/../payments-api":/target:ro \
  --entrypoint python ecdat-scanner:local \
  -m scanner.cli /target
```

By default, stdout is a JSON **array** of scored findings for compatibility
with previous automation. Each finding includes detection evidence, language,
algorithm, confidence, classical/PQC attributes, risk tier, and source context.

### Store the compatibility JSON artifact

```bash
docker run --rm \
  -v "$PWD/../payments-api":/target:ro \
  -v "$PWD/reports":/reports \
  --entrypoint python ecdat-scanner:local \
  -m scanner.cli /target --json-out /reports/findings.json
```

`--json-out PATH` writes the legacy JSON array of scored findings. It does not
send data anywhere. Ensure the report volume has an organization-approved
encryption-at-rest policy.

### Print only aggregate risk counts

```bash
docker run --rm -v "$PWD/../payments-api":/target:ro \
  --entrypoint python ecdat-scanner:local \
  -m scanner.cli /target --summary-only
```

`--summary-only` avoids emitting file paths and code-call metadata to stdout.
Use it in CI logs when repository metadata must not be exposed.

### Redact paths outside the chosen root

```bash
python -m scanner.cli /approved/workspace/payments-api --redact-paths
```

`--redact-paths` keeps paths relative to the selected target. Any finding that
cannot be made relative is emitted with `[redacted]`, preventing an absolute
workstation path from entering a report bundle.

`--source-context` marks every finding in the submitted target as `SOURCE`,
`TEST_ONLY`, or `DEMO_ONLY`. Use it for intentionally isolated test trees and
the supplied live demo; it prevents those results from being framed as deployed
production exposure in a report.

## 4. Policy Gates for CI/CD

`--fail-on` makes ECDAT useful as a deterministic gate. It returns exit code
`2` when a finding meets or exceeds the stated tier, `0` when the scan passes,
and `1` for invalid arguments, missing targets, or failed report sync.

| Command | Build behavior |
| --- | --- |
| `--fail-on CRITICAL` | Fails only on Critical findings. |
| `--fail-on HIGH` | Fails on Critical or High findings. |
| `--fail-on MEDIUM` | Fails on Critical, High, or Medium findings. |
| `--fail-on LOW` | Fails when any scored finding exists. |

An accepted GitHub Actions pattern is shown below. It scans the checked-out
repository read-only and retains a JSON artifact only in the protected CI
system; it does not need access to a dashboard or report-sync credentials.

```yaml
name: ECDAT policy gate
on: [pull_request]
permissions:
  contents: read
jobs:
  ecdat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build --tag ecdat-scanner:${{ github.sha }} .
      - name: Block Critical cryptographic findings
        run: >-
          docker run --rm
          -v ${{ github.workspace }}:/target:ro
          --entrypoint python ecdat-scanner:${{ github.sha }}
          -m scanner.cli /target --summary-only --fail-on CRITICAL
```

Treat the initial threshold as an alerting policy. Promote it only after the
security team has reviewed the asset inventory, source-context labels, and
application reachability. The current scanner does not make reachability or
data-flow claims.

For GitLab CI, use the same policy command in a Docker-capable runner and pass
the checkout as a read-only mount. For Jenkins, place the identical command in
an `sh` stage and treat exit code `2` as a security-policy failure rather than
an infrastructure error. Neither job needs source egress or dashboard
credentials.

```yaml
# .gitlab-ci.yml excerpt — requires an approved Docker-capable runner.
ecdat_policy:
  image: docker:27
  services: [docker:27-dind]
  script:
    - docker build --tag ecdat-scanner:$CI_COMMIT_SHA .
    - >-
      docker run --rm -v "$CI_PROJECT_DIR":/target:ro
      --entrypoint python ecdat-scanner:$CI_COMMIT_SHA
      -m scanner.cli /target --summary-only --fail-on CRITICAL
```

```groovy
// Jenkins declarative-pipeline stage excerpt.
stage('ECDAT policy') {
  steps {
    sh 'docker build --tag ecdat-scanner:$BUILD_TAG .'
    sh '''docker run --rm -v "$WORKSPACE":/target:ro --entrypoint python \
      ecdat-scanner:$BUILD_TAG -m scanner.cli /target --summary-only --fail-on CRITICAL'''
  }
}
```

## 5. PQC Context and Report Interpretation

Use `--data-shelf-life-years YEARS` only when the application owner has
supplied a documented data-retention assumption. ECDAT persists that value and
its `assumption_source` so analysts can distinguish an actual business input
from unknown context.

```bash
python -m scanner.cli /target --summary-only --data-shelf-life-years 20
```

ECDAT reports classical weakness separately from quantum vulnerability. For
example, MD5 is classically broken and Critical; RSA-2048 may be classically
acceptable yet quantum-vulnerable. HNDL exposure is `UNKNOWN` until a shelf-life
assumption is supplied, then becomes `HIGH` only when the configured Mosca-style
time comparison indicates urgency. Source files under `test/`, `tests/`,
`fixtures/`, and similar paths are marked `TEST_ONLY`; they remain inventory
records but must not be represented as deployed production exposure without
reachability review.

NIST recommends organizations create cryptographic inventories and plan their
transition to PQC; it does not remove the need to validate where and how an
algorithm is used.[1]

## 6. Signed Report Bundles and Controlled Synchronization

The secure hand-off is a **separate operation after the offline scan**. A local
agent creates a JSON report bundle, canonicalizes it, computes a SHA-256 digest,
and signs it using Ed25519. The central intake service verifies that signature
against the enrolled agent public key. HTTPS plus mutual TLS protects the
network path; the detached signature preserves bundle provenance and integrity
across transit and storage.

Generate a per-agent Ed25519 signing key in an approved secret-management
workflow. For a lab-only example:

```bash
openssl genpkey -algorithm ED25519 -out agent-signing-key.pem
openssl pkey -in agent-signing-key.pem -pubout -out agent-public-key.pem
chmod 600 agent-signing-key.pem
```

The central service is enrolled with the agent's **raw base64 Ed25519 public
key** through `REPORT_SYNC_AGENT_KEYS`, for example:

```json
{"payments-build-agent-01":"<base64-ed25519-raw-public-key>"}
```

Create a signed bundle locally without transferring it:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/../payments-api":/target:ro \
  -v "$PWD/agent-secrets":/secrets:ro \
  -v "$PWD/reports":/reports \
  --entrypoint python ecdat-scanner:local \
  -m scanner.cli /target \
  --report-bundle /reports/payments-$(date +%F).ecdat.json \
  --organization-id acme-finance \
  --repository-id payments-api \
  --agent-id payments-build-agent-01 \
  --signing-key /secrets/agent-signing-key.pem \
  --redact-paths --data-shelf-life-years 20
```

To deliver that result, add the explicit HTTPS and mTLS flags. The command
rejects `http://` and refuses a sync attempt without both client certificate and
private key.

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$PWD/../payments-api":/target:ro \
  -v "$PWD/agent-secrets":/secrets:ro \
  -v "$PWD/reports":/reports \
  --entrypoint python ecdat-scanner:local \
  -m scanner.cli /target \
  --report-bundle /reports/payments.ecdat.json \
  --organization-id acme-finance \
  --repository-id payments-api \
  --agent-id payments-build-agent-01 \
  --signing-key /secrets/agent-signing-key.pem \
  --redact-paths --data-shelf-life-years 20 \
  --sync-url https://ingest.dashboard.example.gov/agent/v1/report-bundles \
  --client-cert /secrets/agent-client.pem \
  --client-key /secrets/agent-client.key \
  --ca-cert /secrets/dashboard-ca.pem
```

**Never** pass the signing key, client key, client certificate, report bundle,
or any dashboard credential through CI logs, a browser, command history shared
with other users, or source control. The direct scanner-to-ingestion route is
for provisioned agents only; it is not a browser API.

## 7. Artifact and Endpoint Contract

The central endpoint is `POST /agent/v1/report-bundles`. It accepts an enrolled
agent's signed bundle and idempotently returns the central `scan_id`, report ID,
and digest. A retry of the same signed bundle returns `accepted: false` without
duplicating the report. The server does **not** rescan source remotely; it
validates the signed report, recomputes deterministic risk/PQC fields from the
signed discovery evidence rather than trusting a supplied severity, and retains
a versioned assessment for analyst review.

The bundle includes a UUID `report_id`, UTC creation time, organization and
repository identifiers, agent ID, scan context, findings, summary, canonical
`bundle_digest`, `signature_algorithm`, and detached `signature`.

## 8. Operational Limits

ECDAT currently supports import-backed source findings for Python, Java,
JavaScript, and TypeScript families. It does not claim complete data-flow,
reflection, computed module/algorithm, arbitrary wrapper, native binary,
container-image, dependency-inventory, or runtime-reachability analysis. See
[`SOURCE_SCANNING_SCOPE.md`](SOURCE_SCANNING_SCOPE.md) for the exact supported
patterns and deliberate exclusions.

Use a staged rollout: inventory first, confirm source context and ownership,
validate production reachability, then enforce a policy threshold. This avoids
turning a static-analysis discovery tool into a false accusation engine.

## References

[1]: https://www.nccoe.nist.gov/applied-cryptography/migration-to-pqc "NIST NCCoE: Migration to Post-Quantum Cryptography"
