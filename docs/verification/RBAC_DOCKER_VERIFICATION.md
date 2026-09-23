# RBAC - Docker/3.11 verification queue

## What I could not verify, and why

- `docker-compose` integration, fresh-volume migration, Postgres schema, and curl flow are deferred because Docker is unavailable on this machine.
- The browser login/logout flow is deferred because Docker is unavailable; the dashboard production build was verified locally with `npm run build`.
- JavaScript/Java scanner tests are deferred because `tree-sitter-languages` is unavailable in the local Python 3.14 environment.
- No `lief`-dependent RBAC test exists; binary tests, if added by the integrated branch, require `lief` on the Docker/Python 3.11 environment.
- The legacy remediation regression test now runs locally with a Developer JWT; API-key assertions remain only on service-caller coverage.

## Local verification status

- **IMPLEMENTED and locally verified:** `tests/test_api.py`, `tests/test_secure_report_sync.py`, `tests/test_rbac.py`, and `tests/test_security_controls.py`: `19 passed`.
- **IMPLEMENTED and locally verified:** Python-only CRUD, confidence, remediation, LLM, CLI, and Python scan-runner tests: `35 passed`.
- **IMPLEMENTED but UNVERIFIED/ENVIRONMENT-BLOCKED:** JavaScript/Java scanner tests and mixed-language scan orchestration. The full suite reports 16 failures because `tree-sitter-languages` is unavailable on Python 3.14; run them on Python 3.11 with the dependency set from `requirements.txt`.
- **UNVERIFIED/ENVIRONMENT-BLOCKED:** Docker Compose, Postgres migration/initdb ordering, backend container login, curl authorization flow, and dashboard container/browser flow. Docker is unavailable locally; use the exact commands below on the Docker/Python 3.11 machine.

## Exact commands to run, in order

Run from the repository root on the Docker/Python 3.11 machine. Items marked Docker-only are intentionally `UNVERIFIED/ENVIRONMENT-BLOCKED` locally.

1. `export AUTH_JWT_SECRET=01234567890123456789012345678901 AUTH_BOOTSTRAP_ADMIN_USERNAME=admin AUTH_BOOTSTRAP_ADMIN_PASSWORD=ChangeMe123!`
2. `python -m pytest tests/test_rbac.py -v`
3. `docker-compose up -d`
4. `sleep 5`
5. `docker-compose exec -T backend python -m db.seed --findings 0`
6. `curl -i -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"ChangeMe123!"}'`
7. `TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"ChangeMe123!"}' | python -c "import json,sys; print(json.load(sys.stdin)['access_token'])") && curl -i -X GET http://localhost:8000/scans -H "Authorization: Bearer $TOKEN"`
8. `docker-compose exec -T backend python -c "from api.database import get_sessionmaker; from db.crud import create_user; from api.core.rbac import Role; s=get_sessionmaker()(); create_user(s,'auditor01','AuditorPass123!',Role.AUDITOR.value); s.close()"`
9. `AUDITOR_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"auditor01","password":"AuditorPass123!"}' | python -c "import json,sys; print(json.load(sys.stdin)['access_token'])") && curl -i -X POST http://localhost:8000/scans -H "Authorization: Bearer $AUDITOR_TOKEN" -H "Content-Type: application/json" -d '{"target_path":"/repo"}'`
10. `curl -i -X GET http://localhost:8000/scans`
11. `curl -i -X GET http://localhost:8000/scans -H "Authorization: Bearer invalid.jwt.token"`
12. `docker-compose down -v`
13. `docker-compose up db -d`
14. `sleep 5`
15. `docker-compose exec -T db psql -U ecdat -d ecdat -c '\d users'`
16. `cd dashboard && npm run dev`

## Expected output for each

- Step 1: shell variables are set; command exits `0`.
- Step 2: all RBAC tests pass; the expected result is `11 passed` or more if integrated tests are added.
- Step 3: the `db`, `backend`, `dashboard`, and `gateway` services start and the backend becomes healthy.
- Step 4: command exits `0`.
- Step 5: seed completes without an Argon2 or database error.
- Step 6: HTTP `200`; JSON contains `access_token`, `token_type` equal to `bearer`, `username` equal to `admin`, and `user_role` equal to `SECURITY_ADMIN`.
- Step 7: HTTP `200`; JSON contains the normal `scans` list response with `scans` and `total` columns.
- Step 8: command exits `0` and creates one Auditor user.
- Step 9: HTTP `403 Forbidden`; response detail contains `not authorized` and does not run the local scan.
- Step 10: HTTP `401 Unauthorized` with `WWW-Authenticate: Bearer`.
- Step 11: HTTP `401 Unauthorized` with an invalid-token detail.
- Step 12: command exits `0` and removes the Postgres volume.
- Step 13: command exits `0` and starts only the database.
- Step 14: command exits `0`.
- Step 15: `users` exists with columns `id`, `username`, `password_hash`, `role`, `organization_id`, `is_active`, `created_at`, and `last_login_at`; index `idx_users_organization` exists.
- Step 16: Vite prints a local development URL, normally `http://localhost:5173/`; opening `/login` shows the username/password form.

## What to do if it fails

- Step 1: inspect `api/core/rbac.py`, `api/routers/auth.py`, and `tests/test_rbac.py` first.
- Steps 2-3: inspect `docker-compose.yml`, `.env`, and backend/database container logs.
- Step 4: inspect `AUTH_JWT_SECRET` in `.env`, `db/seed.py`, `api/routers/auth.py`, and `api/core/rbac.py`.
- Step 5: inspect `api/main.py`, the `scans` route dependencies in `api/routers/scans.py`, and the database health state.
- Step 6: inspect `require_role()` in `api/core/rbac.py` and the POST dependency in `api/routers/scans.py`.
- Steps 7-8: inspect `get_current_user()` and `decode_token()` in `api/core/rbac.py`.
- Steps 9-12: inspect `db/migrations/004_rbac_users.sql`, `db/schema.sql`, and the `05_rbac_users.sql` Compose mount.
- Step 13: inspect `dashboard/src/context/AuthContext.jsx`, `dashboard/src/lib/api.js`, and `dashboard/src/pages/LoginPage/LoginForm.jsx`.

## Files I touched that Postgres behaviour depends on

- `db/schema.sql`: fresh-volume `users` table and `idx_users_organization` index.
- `db/migrations/004_rbac_users.sql`: existing-volume equivalent schema; Compose mounts it as `05_rbac_users.sql`.
- `db/models.py`: SQLAlchemy `User` mapping, Boolean server default, timestamps, and indexed organization column.
- `db/crud.py`: user lookup, Argon2 verification, and committing user creation.
- `db/seed.py`: optional configured bootstrap admin creation; it fails closed when called without `AUTH_BOOTSTRAP_ADMIN_PASSWORD`.
- `docker-compose.yml`: migration ordering and `AUTH_JWT_SECRET` backend environment injection.

SQLite validates ORM behavior locally, but Postgres 16 must confirm `SERIAL`, Boolean defaults, initdb ordering, and the migration against a fresh volume.