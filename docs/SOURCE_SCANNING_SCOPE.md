# ECDAT Scanning Scope and Evidence Contract

> **Scope note (current sprint).** This document was written when source-code
> scanning was ECDAT's only detection technique. Four further engines —
> dependency manifests, config/IaC, binaries and container layers — are now in
> scope per `AGENT_RULES.md` #6 and `SYSTEM_INTERFACE_CONTRACT.md` §2.2
> (`findings.artifact_type`). Each engine ships its own scope document with its
> own non-claims: `DEPENDENCY_SCANNING_SCOPE.md`, `CONFIG_IAC_SCANNING_SCOPE.md`,
> `BINARY_SCANNING_SCOPE.md`, `CONTAINER_SCANNING_SCOPE.md`. This file remains
> authoritative for **source-code** scanning only. Nothing below is weakened by
> the new engines; the non-claims in this file continue to bind the AST and
> tree-sitter detectors.

## Supported inputs

This document covers the **source-code** engines. They analyze local source in
the following languages:
Python (`.py`), Java (`.java`), JavaScript (`.js`, `.mjs`, `.cjs`, `.jsx`), and
TypeScript (`.ts`, `.mts`, `.cts`, `.tsx`). Python uses AST analysis; Java and
the JavaScript/TypeScript family use tree-sitter queries. The supported workflow
is a read-only local directory mount or file path.

The detector reports import-backed, statically recognizable crypto calls and
literals covered by its rule set. Every report record includes the file, line,
matched call, library, algorithm, primitive, language, detection method,
confidence, and source context. The default report is an **inventory and
triage input**, not evidence of exploitability or runtime reachability.

## Deliberate non-claims

The source-code engines do not analyze Go/Rust/C/C++, generated code, dynamic
dispatch, reflection, arbitrary application wrappers, computed algorithm values,
environment-derived keys, or full interprocedural data flow. They cannot prove
that a finding is executed, externally reachable, processes sensitive data, or
is deployed.

Native binaries, container image layers and third-party dependency inventories
are **no longer non-claims for the product** — they are handled by the binary,
container and dependency engines respectively, each with its own scope document.
They remain non-claims *for these source-code engines*: the AST and tree-sitter
detectors must never be described as covering them.

Still out of scope for ECDAT as a whole, and not to be implied anywhere in the
UI, CLI, docs or pitch:

- **Registry pulls.** Container scanning accepts a `docker save` tarball or an
  OCI layout directory. `ecdat scan nginx:latest` does not work and is not
  planned; a registry pull would contradict the no-egress guarantee.
- **Runtime or dynamic analysis.** Every finding is static evidence.
- **General IaC security auditing.** The config engine detects crypto-relevant
  settings only, not misconfiguration in general.
- **Statically linked, stripped or packed binaries.** Typical Go and Rust builds
  defeat symbol-table analysis; the binary engine documents this as a non-claim
  rather than degrading silently.

> **Confidence means parser/rule confidence, not business impact.** A
> `VERIFIED` record means a supported syntactic pattern was observed. It makes
> no claim about production reachability, exploitability, or data sensitivity.

> **Confidence is also not comparable across techniques by accident — it is
> comparable by design.** All five engines emit signals into the shared scorer
> in `scanner/confidence.py`, which produces `confidence_score` and a
> `confidence_band` of `VERIFIED` / `PROBABLE` / `UNVERIFIED`. This matters most
> for the weakest evidence: a package named `openssl` in a container image
> proves the library is **installed**, not that a weak algorithm is **used**, and
> it is banded `UNVERIFIED` accordingly. Presenting inventory evidence at the
> same certainty as a traced call site is prohibited in every surface —
> dashboard, CBOM, CLI output and pitch.

## Source context labels

Path heuristics mark `test`, `tests`, `fixtures`, `__tests__`, and related paths
as `TEST_ONLY`, and demo/example paths as `DEMO_ONLY`. An engineer can override
this for an entire target with `--source-context`. A deployment review must
confirm whether `SOURCE` findings are in a production path. The supplied demo
is intentionally `DEMO_ONLY`.

## PQC reporting interpretation

ECDAT records classical weakness and quantum vulnerability separately. The
HNDL field is `UNKNOWN` unless a data owner submits an explicit
`--data-shelf-life-years` value. It is a prioritization aid based on the
recorded model version and assumptions—not a NIST conformance certificate nor a
prediction of cryptographically relevant quantum computer timelines.

## Safe rollout

Begin with `--summary-only` inventory mode. Review algorithm calls, source
context, system ownership, deployment reachability, and data shelf-life
assumptions. Only then set a CI `--fail-on` threshold. Report suspected scanner
gaps with the minimal sanitized source example and expected/actual result; add
a regression test before expanding a rule.
