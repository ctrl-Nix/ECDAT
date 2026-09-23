# RBAC - Docker/3.11 verification queue

## What I could not verify, and why

- `docker-compose` integration, fresh-volume migration, Postgres schema, and curl flow are deferred because Docker is unavailable on this machine.
- The browser login/logout flow is deferred because Docker is unavailable; the dashboard production build was verified locally with `npm run build`.
- JavaScript/Java scanner tests are deferred because `tree-sitter-languages` is unavailable in the local Python 3.14 environment.
- No `lief`-dependent RBAC test exists; binary tests, if added by the integrated branch, require `lief` on the Docker/Python 3.11 environment.

## Exact commands to run, in order

Run from the repository root on the Docker/Python 3.11 machine.

1. `python -m pytest tests/test_rbac.py -v`
2. `docker-compose up -d`
3. `sleep 5`
4. `curl -i -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"ChangeMe123!"}'`
5. Set `TOKEN` to the `access_token` from step 4, then run `curl -i -X GET http://localhost:8000/scans -H "Authorization: Bearer $TOKEN"`.
6. Create an Auditor directly in the database for the negative authorization check:
   `docker-compose exec -T db psql -U ecdat -d ecdat -c "INSERT INTO users (username,password_hash,role) VALUES ('auditor01','<argon2 hash generated with pwdlib>','AUDITOR');"`
   Generate its token by logging in with the password used to create the hash, then run `curl -i -X POST http://localhost:8000/scans -H "Authorization: Bearer <auditor-token>" -H "Content-Type: application/json" -d '{"target_path":"/repo"}'`.
7. `curl -i -X GET http://localhost:8000/scans`
8. `curl -i -X GET http://localhost:8000/scans -H "Authorization: Bearer invalid.jwt.token"`
9. `docker-compose down -v`
10. `docker-compose up db -d`
11. `sleep 5`
12. `docker-compose exec -T db psql -U ecdat -d ecdat -c '\d users'`
13. `cd dashboard && npm run dev`

## Expected output for each

- Step 1: all RBAC tests pass; the expected result is `11 passed` or more if integrated tests are added.
- Step 2: the `db`, `backend`, `dashboard`, and `gateway` services start and the backend becomes healthy.
- Step 3: command exits `0`.
- Step 4: HTTP `200`; JSON contains `access_token`, `token_type` equal to `bearer`, `username` equal to `admin`, and `user_role` equal to `SECURITY_ADMIN`.
- Step 5: HTTP `200`; JSON contains the normal `scans` list response with `scans` and `total` columns.
- Step 6: HTTP `403 Forbidden`; response detail contains `not authorized` and does not run the local scan.
- Step 7: HTTP `401 Unauthorized` with `WWW-Authenticate: Bearer`.
- Step 8: HTTP `401 Unauthorized` with an invalid-token detail.
- Step 9: command exits `0` and removes the Postgres volume.
- Step 10: command exits `0` and starts only the database.
- Step 11: command exits `0`.
- Step 12: `users` exists with columns `id`, `username`, `password_hash`, `role`, `organization_id`, `is_active`, `created_at`, and `last_login_at`; index `idx_users_organization` exists.
- Step 13: Vite prints a local development URL, normally `http://localhost:5173/`; opening `/login` shows the username/password form.

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