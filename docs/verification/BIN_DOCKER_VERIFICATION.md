# BIN — Docker/3.11 verification queue

## What I could not verify, and why
- Native `lief` library parser execution against live ELF/PE/Mach-O binaries (requires `lief` wheel which is cp311 only, missing on Python 3.13 dev workstation).
- Multi-container docker compose scan flow with PostgreSQL migration 003 initdb mount (requires Docker daemon, missing on workstation).

## Exact commands to run, in order

### 1. Run all unit and integration tests including LIEF test
```bash
docker compose run --rm api pytest tests/test_binary_engine.py -v
```

### 2. Verify CLI binary scanning under Docker Python 3.11 environment with LIEF
```bash
docker compose run --rm -e SCAN_ENABLE_BINARY=true api python -m scanner.cli tests/fixtures/binaries --scan-type binary
```

### 3. Verify CLI gate policy (--fail-on CRITICAL)
```bash
docker compose run --rm -e SCAN_ENABLE_BINARY=true api python -m scanner.cli tests/fixtures/binaries --scan-type binary --fail-on CRITICAL
```

### 4. Verify shared migration 003 schema columns in PostgreSQL
```bash
docker compose exec -T db psql -U ecdat -d ecdat -c "\d findings"
```

## Expected output for each

### For Command 1:
- `tests/test_binary_engine.py` passes 16 of 16 tests (including `test_lief_engine_if_available PASSED`), exit code 0.

### For Command 2:
- JSON array on stdout containing findings from `libcrypto_positive.elf` and `crypto_sample.exe`.
- Every finding has `"artifact_type": "BINARY"` and non-empty `"artifact_ref"` (e.g. `".dynsym:MD5_Init"`, `".rodata+0x7"`).
- Exit code 0.

### For Command 3:
- Exit code 2 (since `libcrypto_positive.elf` and `crypto_sample.exe` contain weak MD5/DES classified as CRITICAL).

### For Command 4:
- Columns `artifact_type` (text, not null, default 'SOURCE_FILE'), `artifact_ref` (text), `package_ecosystem` (text), `package_name` (text), `package_version` (text), `image_digest` (text), `layer_digest` (text) present on `findings` table.

## What to do if it fails

- **If Command 1 fails at `test_lief_engine_if_available`:**
  - Look at `scanner/binary_engine.py:84` (`_scan_with_lief`). Check if `binary.symbols` or `binary.sections` attribute access differs across LIEF minor releases.
- **If Command 2 fails with error message "SCAN_ENABLE_BINARY is not enabled":**
  - Verify environment variable `SCAN_ENABLE_BINARY=true` is passed to the container. Check `scanner/cli.py:44`.
- **If Command 3 returns exit code 0 instead of 2:**
  - Check `api/services/risk_engine.py` risk scoring for MD5/DES and `_violates_policy()` in `scanner/cli.py:134`.
- **If Command 4 lacks columns:**
  - Check `db/migrations/003_artifact_scanning.sql` and `docker-compose.yml` initdb mount order (`04_artifact_scanning.sql`).

## Files I touched that Postgres behaviour depends on
- `scanner/cli.py` (emits `artifact_type="BINARY"` and `artifact_ref` which are persisted to `findings.artifact_type` and `findings.artifact_ref` in Postgres). No custom Postgres JSONB or table locking modifications were made directly.
