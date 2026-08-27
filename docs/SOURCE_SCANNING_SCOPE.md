# ECDAT Source-Scanning Scope and Evidence Contract

## Supported inputs

ECDAT currently analyzes local **source code only** in the following languages:
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

ECDAT does not currently analyze native binaries, container image layers,
third-party dependency inventories/SBOMs, Go/Rust/C/C++, generated code,
dynamic dispatch, reflection, arbitrary application wrappers, computed
algorithm values, environment-derived keys, full interprocedural data flow, or
runtime configuration. It cannot prove that a finding is executed, externally
reachable, processes sensitive data, or is deployed.

> **Confidence means parser/rule confidence, not business impact.** A high
> confidence record means that a supported syntactic pattern was observed. It
> does not make a claim about production reachability, exploitability, or data
> sensitivity.

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
