# DFS — Docker/3.11 verification queue

## What I could not verify, and why

- Fresh PostgreSQL initdb ordering and PostgreSQL index creation were not run because Docker is unavailable on the implementation machine.
- The dashboard browser smoke checks were not run because no Docker stack or browser session is available here.
- The full suite could not complete here: an existing oversized binary fixture exhausted available disk, and an existing mixed-language scan test requires unavailable tree-sitter Java/JavaScript parsing.
- The repository's existing `tests/test_crud.py` was deleted in the pre-existing worktree state. The committed version was read for context but was not restored or changed; DFS CRUD coverage is in `tests/test_findings_filter_sort.py`.
- DFS §7's route example uses `get_api_key`; the implementation retains the current `require_role` dependency because §3 forbids authentication changes. This deviation was explicitly directed by the user.

## Exact commands to run, in order

Run from the repository root with Python 3.11 and the project dependencies installed:

1. `python -m pytest tests/ -q --disable-warnings --maxfail=1`
2. `python -m pytest tests/test_findings_filter_sort.py -v`
3. `python -m pytest tests/test_api.py -k "findings" -v`
4. `cd dashboard && npm run build`
5. In a Docker-capable checkout with its normal `.env`, create a separate disposable compose project so an existing database volume is not changed:
   `docker compose -p ecdat-dfs-verification up -d db`
6. Check the three DFS/TRD indexes in that fresh database:
   `docker compose -p ecdat-dfs-verification exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT indexname FROM pg_indexes WHERE schemaname = \$\$public\$\$ AND indexname IN (\$\$idx_findings_scan_tier\$\$, \$\$idx_findings_scan_lang\$\$, \$\$idx_scans_repo_started\$\$) ORDER BY indexname;"'`
7. Remove only the disposable compose project's resources after preserving the output:
   `docker compose -p ecdat-dfs-verification down -v`
8. Start the full stack with `docker compose up -d`, authenticate in the browser, then perform the manual smoke checks below.

## Expected output for each

1. Exit code `0`; all collected tests pass. The pre-existing deleted test files are absent from this checkout and therefore are not included in collection.
2. Exit code `0`; four DFS CRUD tests pass, covering multi-tier OR, cross-category AND, descending algorithm order, empty-list handling, and stable default ordering.
3. Exit code `0`; the repeated-risk-tier, default response, invalid `sort_by`, and invalid `sort_dir` API tests pass.
4. Exit code `0`; Vite reports a successful production build.
5. Exit code `0`; the `db` service becomes healthy under the isolated project name.
6. Exit code `0` and exactly these three newline-separated names, in this order:
   `idx_findings_scan_lang`
   `idx_findings_scan_tier`
   `idx_scans_repo_started`
7. Exit code `0`; only the `ecdat-dfs-verification` project and its named volume are removed.
8. Exit code `0` for compose startup and a reachable dashboard/backend.

## What to do if it fails

- Command 1: check the first failing test's implementation path; CRUD behavior is in `db/crud.py`, API behavior is in `api/routers/findings.py`, and auth setup is in the existing `api/core/rbac.py` dependency.
- Command 2: inspect `db/crud.py::get_findings_for_scan()` and fixture setup in `tests/test_findings_filter_sort.py`.
- Command 3: inspect `api/core/params.py`, `api/routers/findings.py`, and the `findings_api` fixture in `tests/test_api.py`.
- Command 4: inspect `dashboard/src/components/FindingsTable.jsx`, `dashboard/src/hooks/useFindings.js`, then the first Vite-reported import or JSX location.
- Command 5: inspect Compose interpolation in `docker-compose.yml` and the `.env` values for the database service.
- Command 6: inspect the initdb mount in `docker-compose.yml`, then compare `db/migrations/008_query_indexes.sql` with the mirrored index statements in `db/schema.sql`.
- Command 7: confirm the exact project name is `ecdat-dfs-verification`; do not remove any other project's volumes.
- Command 8: inspect dashboard/backend service health and the `/scans` and `/scans/{scan_id}/findings` requests in the browser network panel.

## Manual smoke checks

- In `/dashboard`, open the Findings tab and Live Scan tab; both should use the shared `FindingsTable` and show live findings from the most recent scan.
- Select multiple risk tiers; matching tiers should be combined with OR semantics. Enter primitive, algorithm, and language text filters; they should narrow the currently loaded page.
- Click sortable column headings and confirm the request uses `sort_by` and toggles `sort_dir`.
- Open `/dashboard/findings` directly; it should be protected by the existing auth route and show the same shared table.
- Confirm a finding with `line === 0` displays an em dash.
- Confirm the UI has no scan-start action added by DFS; the view only reads scan and finding APIs.

## Files I touched that Postgres behaviour depends on

- `db/schema.sql` — fresh volumes create the same three indexes as the migration.
- `db/migrations/008_query_indexes.sql` — additive indexes on `(scan_id, risk_tier)`, `(scan_id, language)`, and `(repo_id, started_at DESC)`.
- `docker-compose.yml` — mounts migration 008 as initdb file `09_query_indexes.sql`.
- `db/crud.py` — SQLAlchemy `IN` predicates and the chosen sort column run on PostgreSQL; null sorting follows PostgreSQL's default ordering as specified.

## Deviations from the specification

- §7 showed `get_api_key`; retained `require_role` per §3 and contract §3.9.
- `dashboard/src/hooks/useFindings.js` serializes array filters as repeated query keys because Axios's default bracketed array format does not match FastAPI's repeated query parameter interface.
