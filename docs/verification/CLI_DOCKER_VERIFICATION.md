# CLI — Docker/3.11 verification queue

## What I could not verify, and why

- Docker image build and container invocations — Docker is unavailable on the implementation machine.
- Python 3.11 dependency installation — only Python 3.13 is installed here; editable install with dependencies stops at `tree-sitter-languages==1.10.2`, which has no compatible Python 3.13 distribution.

## Exact commands to run, in order

Run these from the repository root on a machine with Docker and Python 3.11 support.

1. `docker build -t ecdat-scanner .`
2. `docker run --rm ecdat-scanner ecdat --help`
3. `docker run --rm ecdat-scanner ecdat scan /app/scanner/python_engine.py`
4. ```sh
   docker run --rm ecdat-scanner sh -c "printf '%s' '[{\"file\":\"src/crypto.py\",\"line\":42,\"library\":\"cryptography\",\"algorithm\":\"RSA\",\"confidence\":\"high\",\"risk_tier\":\"HIGH\",\"risk_reason\":\"RSA is quantum-vulnerable.\",\"primitive\":\"pke\"}]' > /tmp/findings.json && printf '%s' '{\"total\":1,\"CRITICAL\":0,\"HIGH\":1,\"MEDIUM\":0,\"LOW\":0,\"UNSCORED\":0}' > /tmp/summary.json && ecdat cbom /tmp/findings.json --summary /tmp/summary.json"
   ```
5. `docker run --rm ecdat-scanner python -m pytest tests/test_ecdat_cli.py -v`

## Expected output for each

1. Image build exits `0` and ends with `Successfully built` or `writing image` for `ecdat-scanner`.
2. Exit `0`; usage lists exactly the required subcommands `{scan,cbom,sync}`.
3. Exit `0`; standard output is a JSON array of finding objects (it may be empty), with no human-readable text mixed into stdout.
4. Exit `0`; standard output is one CycloneDX document with `bomFormat` equal to `CycloneDX`, `specVersion` equal to `1.6`, one component named `RSA`, and risk summary total `1` / `HIGH` `1`.
5. Exit `0`; all 8 CLI tests pass.

## What to do if it fails

1. Check `Dockerfile:15` (editable install), then `pyproject.toml:8-42` (dependencies and setuptools package discovery).
2. Check `pyproject.toml:31-32` (console script) and `scanner/ecdat_cli.py:19` (`build_parser`).
3. Check `scanner/ecdat_cli.py:73` (`cmd_scan` argument translation), then `scanner/cli.py:235` (`main` parser and scan flow).
4. Check `scanner/ecdat_cli.py:110` (`cmd_cbom` input/output), then `api/services/cbom_generator.py:125` (`build_cbom_from_findings`).
5. Check the first failing assertion in `tests/test_ecdat_cli.py`, then the corresponding handler at `scanner/ecdat_cli.py:73`, `:110`, or `:131`.

## Files I touched that Postgres behaviour depends on

- `api/services/cbom_generator.py:89-125` — `generate_cbom()` still obtains rows through `db.crud`; the new pure builder and CLI CBOM path use no database connection. No schema, migration, or Postgres-specific behavior was added.
