# CBV — Docker/3.11 verification queue

## What I could not verify, and why

- `docker build --tag ecdat-scanner:local .` and `docker run` container verification are deferred because Docker is unavailable on this machine.
- Multilang JavaScript/Java scanner tests (`tree-sitter-languages` AST parsing) across the whole test suite are deferred because tree-sitter wheels are cp311-only and unavailable on the local Python 3.14 environment.
- Phase B endpoint wiring (`api/routers/cbom.py` validation branch) is intentionally deferred because contract item C-14 requires human sign-off on the failure contract (HTTP 500 vs HTTP 200 with warning) before runtime behavior can be modified.

## Exact commands to run, in order

Run from the repository root on the Docker/Python 3.11 machine:

1. `pytest tests/test_cbom_validation.py -q --disable-warnings -p no:cacheprovider`
2. `python -c "from api.services.cbom_validator import CBOM_ISSUE_CODES as c; print(sorted(c))"`
3. `python -c "import re, sys; p = open('api/services/cbom_validator.py').read(); bad_re = re.search(r'^\s*(import re|from re import)|\bre\.(compile|match|search|fullmatch|sub|findall)\(', p, re.M); sys.exit(0 if bad_re is None else 1)"`
4. `python -c "import re, sys; p = open('api/services/cbom_validator.py').read() + open('requirements.txt').read(); bad = re.search(r'jsonschema|fastjsonschema|cbom_generator|import fastapi|from fastapi', p); sys.exit(0 if bad is None else 1)"`
5. `docker build --tag ecdat-scanner:local .`
6. `docker run --rm -e API_KEY=ci-test-key -e REPORT_SYNC_REQUIRE_MTLS=false --entrypoint python ecdat-scanner:local -m pytest tests/test_cbom_validation.py -q --disable-warnings --maxfail=1`
7. `docker run --rm -e API_KEY=ci-test-key -e REPORT_SYNC_REQUIRE_MTLS=false --entrypoint python ecdat-scanner:local -m pytest -q --disable-warnings --maxfail=1`

## Expected output for each

- Command 1: exits `0`; last line begins: `28 passed`.
- Command 2: exits `0`; prints:
  `['BOM_REF_DUPLICATE', 'CRITICALITY_PROPERTY_INVALID', 'DOCUMENT_NOT_OBJECT', 'FIELD_INVALID_VALUE', 'FIELD_MISSING', 'FIELD_WRONG_TYPE', 'NOT_JSON_SERIALIZABLE', 'RISK_TIER_PROPERTY_INVALID', 'RISK_TIER_PROPERTY_MISSING', 'SUMMARY_TIER_MISMATCH', 'SUMMARY_TOTAL_MISMATCH']`
- Command 3: exits `0` with no output (verifies zero `re` usage).
- Command 4: exits `0` with no output (verifies no forbidden imports or schema libraries).
- Command 5: exits `0`; image `ecdat-scanner:local` successfully built.
- Command 6: exits `0`; inside container prints `28 passed`.
- Command 7: exits `0`; full test suite passes.

## What to do if it fails

- Command 1 or 6: Inspect `api/services/cbom_validator.py` (validator logic, Pydantic models, and cross-checks) and `tests/test_cbom_validation.py`.
- Command 2: Inspect `api/services/cbom_validator.py` line 34 (`CBOM_ISSUE_CODES`).
- Command 3: Inspect `api/services/cbom_validator.py` for any accidental regex imports or calls.
- Command 4: Inspect `api/services/cbom_validator.py` and `requirements.txt` for forbidden imports (`jsonschema`, `fastjsonschema`, `cbom_generator`, or `fastapi`).
- Command 5: Inspect `Dockerfile` and `requirements.txt`.
- Command 7: Check multilang dependencies and tree-sitter installation in the Docker image.

## Files I touched that Postgres behaviour depends on

None. CBV introduces no database migrations, no schema modifications, no new models, and writes no SQL. The validator executes in-memory on CycloneDX dict objects.
