# Dependency Scanning Scope

Dependency scanning (`--scan-type dependency`) provides an inventory of recognised cryptographic libraries declared in standard third-party manifests.

## Supported Ecosystems and Manifests
- **Python (PyPI):** `requirements.txt` (and variants like `requirements-dev.txt`), `pyproject.toml`, `Pipfile.lock`, `poetry.lock`
- **JavaScript (npm):** `package.json`, `package-lock.json`
- **Java (Maven):** `pom.xml`

## What a Finding Means
A finding from this engine means **"a recognised cryptographic library is *declared* in this manifest."** 

It does **not** mean:
- The library is actually used in the codebase (no call-site tracing is performed).
- The library is vulnerable to a specific CVE (no vulnerability or registry lookups are performed).
- The library is a direct dependency (transitive/direct distinctions are not made).

## Algorithm and Risk
When a library is present but the specific algorithm cannot be determined from the manifest alone, the finding is emitted with `algorithm = "UNKNOWN"`. 

The risk engine assigns `risk_tier = UNSCORED` to `UNKNOWN` algorithms. This allows the dashboard to display the dependency for inventory purposes without triggering policy violations incorrectly.

## Line Numbers
For unstructured text files like `requirements*.txt`, the `line` field contains the actual 1-based line number. 
For structured formats (JSON, TOML, XML), the `line` field is always `0` (which renders as `—` in the dashboard), meaning "no line information for structured formats".

## Confidence and API Integration
Findings emitted by the dependency scanner carry the legacy `confidence = "unverified"`. 

Because the backend's scan runner currently drops all findings that are not `high` confidence, this feature is **CLI-only until CONF replaces the `scan_runner` gate**. Dependency findings will not be persisted by `POST /scans` API calls; they can only be stored if a signed report bundle carrying them is ingested.

## Not an SBOM
This feature is not a complete Software Bill of Materials (SBOM). It lists **only** recognised cryptographic libraries that match the internal static rule packs. For a full dependency inventory, users should use dedicated SBOM tooling.

## Default Scans
Default scans (`--scan-type source`) remain completely unchanged and do not run the dependency engine.
