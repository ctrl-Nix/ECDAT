# Skill: Secure FastAPI Endpoint Development

## Purpose
Guide safe creation/modification of API endpoints that trigger scans, serve
findings, export CBOM data, and return remediation text.

## When to use this skill
Any time an agent adds or modifies a FastAPI route.

## Required process, before writing/modifying an endpoint
1. Identify the trust boundary — is this endpoint internal-only (local demo)
   or exposed? For this build, assume it may be exposed on a shared demo
   network during judging — treat it as semi-public.
2. Validate all external input with Pydantic models — never accept raw
   untyped dicts from a request body.
3. Check for injection risk — this project scans arbitrary repo paths/URLs;
   sanitize and restrict scan targets:
   - Reject path traversal (`..`, absolute paths outside an allowed root)
   - Never pass user input directly into a shell command
   - If cloning a remote repo URL, allow-list `https://github.com/...` only
     and cap clone size/depth to avoid a demo-breaking slow clone
4. Check resource consumption — a scan-trigger endpoint should run scans as a
   background task (FastAPI `BackgroundTasks`), not block the request thread
   on a large repo.
5. Ensure errors don't leak internals — return structured error responses,
   not raw tracebacks.
6. Write/update a test for the endpoint (happy path + at least one
   invalid-input case) before considering the task done.

## Forbidden behaviors
- No accepting raw shell commands or unsanitized file paths from request
  input.
- No returning stack traces or internal exceptions directly in API responses.
- No hardcoded credentials or connection strings — read from environment
  variables only.
- No blocking, synchronous long-running scans on the main request thread.
- No sending source code to an external LLM by default (remediation calls
  must operate on already-extracted findings, not raw file contents — see
  `remediation-copy/SKILL.md`).

## Minimum endpoints for this build
- `POST /scans` — trigger a scan against a given repo path/URL (background task)
- `GET /scans/{id}` — fetch scan status and findings
- `GET /scans/{id}/cbom` — export the CBOM JSON for a completed scan
- `GET /scans/{id}/remediation` — fetch remediation text for a finding
  (Shreyanshi's route — depends on `cbom-quantum-risk` output existing first)

## Route ownership (agreed Day 1 — do not duplicate work)
- Shashank → `/scans` (trigger)
- Ronak → `/scans/{id}` and underlying findings storage
- Shreyanshi → `/scans/{id}/remediation`
- Whoever adds `/cbom` export — coordinate live, this depends on Maitreyi's
  CycloneDX shape being locked first (Day 3 joint session)
