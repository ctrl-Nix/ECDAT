# CBOM Export Validation/Polish

## 1. Proposed Approach

Treat the existing `api/services/cbom_generator.py` as the primary CBOM generation path and add validation rather than redesigning the export system. Generated CBOM JSON should be checked against the CycloneDX 1.6 schema, with validation failures surfaced clearly and specific violations identified. “Polish” should focus on targeted fixes such as missing required fields, malformed evidence references, or inconsistent risk-tier and criticality values discovered during validation. The frontend placeholder `CbomExport.jsx` can then be connected to the confirmed-valid existing export path. Given the 3-day window, scope should remain limited to validation and targeted field fixes.

## 2. Tech Stack / Libraries You’d Use

- `cyclonedx-python-lib` — proposed option for CycloneDX generation/validation if acceptable as a project dependency.
- `jsonschema` with a vendored CycloneDX 1.6 schema — alternative if direct schema validation is preferred.
- Existing Python/FastAPI implementation for integrating validation with the current CBOM flow.

## 3. Files You Expect to Create or Modify

**Existing:**
- `api/services/cbom_generator.py` — fix or adjust CBOM fields identified by validation.
- `api/routers/cbom.py` — integrate validation if required by the existing export flow.
- `dashboard/src/components/CbomExport.jsx` — complete the currently identified placeholder export action.
- `dashboard/src/components/CBOMViewer.jsx` — modify only if corrected CBOM fields affect display.

**New:**
- A CBOM validation helper or test module, with the exact path to be confirmed against the repository tree.

## 4. Data or Interfaces You Expect to Need From Other Features

- Existing `findings` and `risk_assessments` data already used by the CBOM generator.
- Coordination with Third-party Dependency Scanning (#1) if dependency findings are added to CBOM output.
- Possible alignment with Unified Confidence Scoring (#5) if confidence information is represented in CBOM evidence.

## 5. Open Questions / Assumptions You’re Making

- Whether `cyclonedx-python-lib` or `jsonschema` is acceptable as a new dependency.
- Whether validation should occur during export or as a separate validation step.
- Whether Standalone CBOM/compliance report view (#7) depends on this feature being completed first.
- What validation failures currently exist; an initial validation run is needed to determine the actual fixes required.
- Assuming no CLI CBOM command is added, since no current CLI CBOM export command is documented.
