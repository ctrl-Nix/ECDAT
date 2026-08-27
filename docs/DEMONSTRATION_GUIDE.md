# ECDAT Judge Demonstration Guide

## Demonstration 1: Supplied Safe Mixed-Language Repository

Use [`demos/ecdat-live-demo`](../demos/ecdat-live-demo) for the primary
presentation. It is tiny, contains no secret, network call, build step, or
deployable service, and is deliberately labeled `DEMO_ONLY`. It demonstrates
Python AST and Java/JavaScript/TypeScript tree-sitter detection while preserving
the distinction between an intentional demonstration and an enterprise finding.

```bash
docker build --tag ecdat-secure-pipeline:local .
docker run --rm \
  -v "$PWD/demos/ecdat-live-demo":/target:ro \
  --entrypoint python ecdat-secure-pipeline:local \
  -m scanner.cli /target --summary-only --source-context DEMO_ONLY --fail-on HIGH
```

The verified result is **9 findings: 4 Critical, 3 High, 2 Low**; policy exit
code is `2`. The observed runtime in the supplied Python 3.11 Docker image was
about **one second**, well below one minute. A nonzero exit is the expected
policy-gate signal, not a scanner crash.

To show the secure delivery sequence without exposing code, provision test-only
Ed25519/mTLS credentials, create a redacted signed bundle, and deliver it to the
dedicated agent-ingestion hostname. The backend accepts the bundle only when
both the trusted TLS gateway validates a client certificate and the bundle
signature matches the enrolled agent public key. See
[`ECDAT_CLI_GUIDE.md`](ECDAT_CLI_GUIDE.md) and
[`SECURE_DEPLOYMENT.md`](SECURE_DEPLOYMENT.md). The dashboard is intentionally
not used to start a scan.

## Demonstration 2: Existing Security-Relevant Repository

The recommended external repository is **OWASP VulnerableApp**:
[`SasanLabs/VulnerableApp`](https://github.com/SasanLabs/VulnerableApp). OWASP
describes it as a deliberately vulnerable modular application for validating and
benchmarking security scanners through reproducible scenarios.[1] That makes it
appropriate for a **transparent scanner demonstration**, but it must never be
presented as a vulnerability finding against an ordinary production project.

The shallow checkout below was verified on **2026-08-27** at commit
`424d4d16d81009a52221c0b002875b66d1e85b89`.

```bash
git clone --depth 1 https://github.com/SasanLabs/VulnerableApp.git owasp-vulnerableapp
docker run --rm \
  -v "$PWD/owasp-vulnerableapp":/target:ro \
  --entrypoint python ecdat-secure-pipeline:local \
  -m scanner.cli /target --summary-only --fail-on CRITICAL
```

**Verified result:** 3 findings in approximately one second: 1 Critical and 2
Low. The Critical finding is a `DES/ECB/NoPadding` Java cipher call in
`src/main/java/org/sasanlabs/internal/utility/PasswordHashingUtils.java:150`.
The Low inventory records are `AES/ECB/PKCS5Padding` and `SHA-256` calls.
Because the repository intentionally teaches reproducible vulnerabilities, say
that aloud during the demonstration and show the exact file/line evidence.

Avoid presenting the scan as a claim that all real-world use cases are covered.
For ordinary repositories, start in inventory mode and only demonstrate
supported literal/import-backed patterns; see
[`SOURCE_SCANNING_SCOPE.md`](SOURCE_SCANNING_SCOPE.md).

## Recommended presentation sequence

| Step | Show | Credible claim |
| --- | --- | --- |
| 1 | Read-only Docker mount and offline `--summary-only` scan. | Source does not leave the local target during scanning. |
| 2 | `DEMO_ONLY` result with policy exit `2`. | ECDAT recognizes supported language/API patterns and supports CI policy gates. |
| 3 | Finding evidence and risk model fields. | Classical and PQC observations are separated; HNDL needs a declared shelf-life assumption. |
| 4 | OWASP VulnerableApp exact DES evidence. | The scanner identifies a documented supported weak-cipher call in a deliberately vulnerable OWASP project. |
| 5 | Signed bundle/mTLS architecture. | Network delivery is explicit, not part of the air-gapped scan; production needs ingress, enrollment, and RBAC controls. |

## Reference

[1]: https://owasp.org/www-project-vulnerableapp/ "OWASP VulnerableApp"
