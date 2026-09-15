# Third-party Dependency Scanning

## 1. Proposed Approach

Add a new scanner module that parses dependency manifest files such as `requirements.txt`, `package.json`, and `package-lock.json` from scanned repositories, then cross-references extracted package/version pairs against a known-vulnerable or cryptographically relevant library dataset. This should run as an additional pass alongside the existing source-code scan within the same scan lifecycle and reuse the existing findings and risk pipeline where practical. Dependency findings could use the existing `library`, `file`, and `matched_call` fields, but the semantic fit of the current findings schema needs confirmation. Given the 3-day window, an initial scope of Python and JavaScript manifests is proposed, subject to team confirmation.

## 2. Tech Stack / Libraries You’d Use

- Python standard-library parsing such as `json` and line-based parsing for `requirements.txt`.
- A vulnerability/cryptographic-relevance reference dataset, with the source and offline/online approach to be decided.
- Existing SQLAlchemy 2.0 models and FastAPI patterns where integration is required.

## 3. Files You Expect to Create or Modify

**New:**
- `scanner/dependency_scanner.py` — proposed manifest-parsing and dependency-scanning module.
- A small local reference-data file may be needed, if an offline dataset is selected.

**Existing:**
- `db/schema.sql` / `db/models.py` — only if the existing findings schema is insufficient.
- `api/routers/` — the relevant scan lifecycle integration point, if required.
- `scanner/cli.py` — if CLI execution requires explicit integration.

Exact module paths need verification against the repository tree.

## 4. Data or Interfaces You Expect to Need From Other Features

- Existing scan and findings flow for storing and retrieving dependency findings.
- Coordination with Unified Confidence Scoring (#5) for confidence mapping.
- Coordination with CBOM export validation/polish (#6) to confirm dependency findings serialize correctly into CycloneDX 1.6.

## 5. Open Questions / Assumptions You’re Making

- Which ecosystems and manifest formats are in scope beyond Python and JavaScript?
- Should vulnerability/cryptographic-relevance data be bundled locally or obtained from an external source?
- Is external data access permitted given the project's no-third-party-data-egress positioning?
- Can dependency findings be represented cleanly by the existing findings schema, or are additional fields/table changes required?
- Assumes manifests are read from the same target directory used by the existing scanner.
