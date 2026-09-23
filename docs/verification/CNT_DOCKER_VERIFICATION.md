# CNT — Docker/3.11 verification queue

## What I could not verify, and why
- Step 7 migration idempotency and fresh-initdb execution in true PostgreSQL 16 container (`docker compose down -v && docker compose up -d db` and `psql` execution require Docker daemon, missing on this Windows workstation).
- Multi-container docker compose runtime environment for container image scanning (requires Docker daemon).

## Exact commands to run, in order

### 1. Run container engine unit and integration tests
```bash
docker compose run --rm backend pytest tests/test_container_engine.py -v
```

### 2. Verify rules file loads
```bash
docker compose run --rm backend python -c "from pathlib import Path; from scanner import container_engine; rules = container_engine.load_rules(Path('scanner/rules')); assert isinstance(rules, dict) and rules"
```

### 3. CLI smoke — certificate detector on debian_rsa1024.tar fixture image
```bash
docker compose run --rm backend python -m scanner.cli --scan-type container --image-tar tests/fixtures/container/debian_rsa1024.tar
```

### 4. CLI smoke — package detector on alpine_libcrypto.tar fixture image
```bash
docker compose run --rm backend python -m scanner.cli --scan-type container --image-tar tests/fixtures/container/alpine_libcrypto.tar
```

### 5. Policy gate integration — CRITICAL trips --fail-on
```bash
docker compose run --rm backend python -m scanner.cli --scan-type container --image-tar tests/fixtures/container/debian_rsa1024.tar --fail-on CRITICAL
```

### 6. Migration idempotency in PostgreSQL
```bash
docker compose down -v && docker compose up -d db
docker compose exec -T db psql -U ecdat -d ecdat -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='findings' AND column_name IN ('artifact_type','artifact_ref','image_digest','layer_digest','package_ecosystem','package_name','package_version') ORDER BY column_name;"
docker compose exec -T db psql -U ecdat -d ecdat -f /docker-entrypoint-initdb.d/04_artifact_scanning.sql
```

### 7. Size limit enforcement
```bash
docker compose run --rm -e SCAN_MAX_ARTIFACT_BYTES=1024 backend python -m scanner.cli --scan-type container --image-tar tests/fixtures/container/alpine_libcrypto.tar
```

### 8. Whole-suite regression
```bash
docker compose run --rm backend pytest -q
```

## Expected output for each

### For Command 1:
- `tests/test_container_engine.py` passes all 15 tests, exit code 0.

### For Command 2:
- Exit code 0, no output.

### For Command 3:
- JSON array on stdout with at least one finding having:
  - `"detection_method": "certificate_parse"`
  - `"algorithm": "RSA"`
  - `"key_size": 1024`
  - `"artifact_type": "CONTAINER_LAYER"`
  - `"risk_tier": "CRITICAL"`
- Exit code 0.

### For Command 4:
- JSON array on stdout with at least one finding having:
  - `"detection_method": "container_package_inventory"`
  - `"package_ecosystem": "apk"`
  - `"package_name": "libcrypto3"`
  - `"artifact_type": "CONTAINER_LAYER"`
- Exit code 0.

### For Command 5:
- Exit code 2 (policy violation due to CRITICAL RSA-1024 certificate).

### For Command 6:
- Output lists exactly the seven column names:
  ```
   column_name
  -------------------
   artifact_ref
   artifact_type
   image_digest
   layer_digest
   package_ecosystem
   package_name
   package_version
  (7 rows)
  ```
- Second psql command exits 0 without error (NOTICE "column already exists, skipping").

### For Command 7:
- Exit code 1 (error).
- Stderr contains `ImageSizeLimitExceeded`.

### For Command 8:
- Entire test suite passes without new failures (218 passed, 1 skipped).

## What to do if it fails

- **If Command 1 fails at `test_pem_cert_rsa1024_detected_weak` or `test_apk_package_inventory_detected`:**
  - Check `scanner/container_engine.py:165` (`ContainerFinding` creation in `_parse_certificate_data`) or line 365 (`_match_packages`).
- **If Command 3 or 4 fails with empty output:**
  - Check `scanner/cli.py:54` (`_scan_container`). Ensure `image_tar` resolution and `container_engine.scan_image_tar` correctly receive the path.
- **If Command 5 returns exit code 0 instead of 2:**
  - Check `_violates_policy()` in `scanner/cli.py:155` and `risk_engine.score_findings` for RSA-1024.
- **If Command 6 fails on column presence:**
  - Check `db/migrations/003_artifact_scanning.sql` and the initdb mount `./db/migrations/003_artifact_scanning.sql:/docker-entrypoint-initdb.d/04_artifact_scanning.sql:ro` in `docker-compose.yml:17`.
- **If Command 7 does not exit 1 or stderr does not contain ImageSizeLimitExceeded:**
  - Check `scanner/cli.py:55` where `SCAN_MAX_ARTIFACT_BYTES` is read from `os.environ` and passed to `scan_image_tar`.

## Files I touched that Postgres behaviour depends on
- `db/crud.py`: added `image_digest` and `layer_digest` to `_FINDING_KEY_ALIASES` so container findings correctly persist `image_digest` and `layer_digest` columns alongside `artifact_type`, `artifact_ref`, `package_ecosystem`, `package_name`, and `package_version`.
- `docker-compose.yml`: documented the read-only bind mount comment for container image tarballs under the `backend` service.
- `scanner/cli.py`: emits `ContainerFinding` dicts with `artifact_type="CONTAINER_LAYER"`, `image_digest`, and `layer_digest`.
