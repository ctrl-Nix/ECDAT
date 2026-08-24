You are the codebase restructuring agent for ECDAT (Enterprise Cryptographic Discovery & Analysis Tool), a Smart India Hackathon 2026 project. The codebase is currently fragmented and does not follow the agreed architecture. Your job is to reorganize ALL existing files into the correct directory structure, update imports, fix configuration files, create skill files for team members, and update documentation. 

**CRITICAL: Do NOT write new business logic. Only reorganize, move, rename, and update imports/paths. The only new files you create are: empty __init__.py files, skill .md files in skills/, and updates to existing config/docs files.**

## Step 0: Read Current State

Before moving anything, read these files to understand the current state:
1. `CODEBASE_AUDIT.md` — the audit report
2. `ARCHITECTURE.md` — the target architecture (note: it may not match current code)
3. `.clinerules` — agent rules
4. `AGENTS_AND_SKILLS.md` — current skill registry
5. `requirements.txt` — current dependencies
6. `docker-compose.yml` — current orchestration
7. `backend/db/models.py` — current DB model
8. `scanner/finding.py` — scanner dataclass (the contract)
9. `backend/db/schemas.py` — current Pydantic schemas
10. `main.py` — current root-level FastAPI app
11. `backend/db/crud.py` — current CRUD layer
12. `backend/db/database.py` — current DB connection

## Step 1: Create Target Directory Structure

Create these directories (some may already exist):

```
ecdat/
├── api/
│   ├── routers/
│   ├── services/
│   └── core/
├── scanner/          # already exists
├── db/               # will be created from backend/db/
├── dashboard/        # rename from frontend/
├── tests/            # consolidate all tests here
├── skills/
│   ├── db/
│   ├── backend/
│   ├── frontend/
│   ├── scanner/
│   ├── cbom-quantum-risk/
│   ├── ci-cd-gate/
│   └── remediation-copy/
└── docs/             # create if not exists
```

## Step 2: Move and Rename Files

Execute these moves EXACTLY:

### A. Backend Restructure
1. Move `backend/db/schema.sql` → `db/schema.sql`
2. Move `backend/db/models.py` → `db/models.py`
3. Move `backend/db/crud.py` → `db/crud.py`
4. Move `backend/db/database.py` → `api/database.py`
5. Move `backend/db/schemas.py` → `api/models.py`
6. Move `backend/db/seed.py` → `db/seed.py`
7. Move `backend/db/README.md` → `db/README.md`
8. Move `backend/db/__init__.py` → `db/__init__.py`
9. Move `backend/tests/test_crud.py` → `tests/test_crud.py`
10. Move `backend/Dockerfile` → `Dockerfile` (at repo root, overwrite if exists)
11. Delete `backend/` directory entirely (including `backend/__init__.py`, `backend/tests/__init__.py`)

### B. Root-Level File Cleanup
12. Move `remediation.py` → `api/routers/remediation.py`
13. Move `remediation_table.py` → keep at root for now (it will be moved to api/services/ later when that file is written)
14. Move `test_main.py` → `tests/test_api.py`
15. Move `test_remediation.py` → `tests/test_remediation.py`
16. Move `test_remediation_table.py` → `tests/test_remediation_table.py`
17. Move `test_llm.py` → `tests/test_llm.py`
18. Keep `conftest.py` at root (pytest needs it there)
19. Keep `main.py` at root BUT rewrite it to be a thin launcher:
    ```python
    # main.py — thin launcher for backward compatibility
    from api.main import app

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    ```
    OR if `api/main.py` doesn't exist yet, create it as a minimal FastAPI factory and make root `main.py` import from it.

### C. Frontend Rename
20. Rename `frontend/` directory → `dashboard/`
21. Update any internal references from `frontend/` to `dashboard/` in docker-compose.yml, .dockerignore, etc.

### D. Scanner Package Fix
22. Update `scanner/__init__.py` to export the public API:
    ```python
    from scanner.cli import main as scan_cli
    from scanner.finding import Finding
    from scanner.python_engine import scan_file as scan_python
    from scanner.multilang_engine import scan_file as scan_multilang

    __all__ = ["scan_cli", "Finding", "scan_python", "scan_multilang"]
    ```

## Step 3: Update Imports in ALL Moved Files

After moving files, EVERY import statement that references old paths must be updated:

### In `api/database.py` (was `backend/db/database.py`):
- Change `from backend.db.models import Base` → `from db.models import Base`

### In `db/crud.py` (was `backend/db/crud.py`):
- Change `from backend.db.models import ...` → `from db.models import ...`
- Change `from backend.db.database import ...` → `from api.database import ...` (if it imports database)

### In `db/__init__.py` (was `backend/db/__init__.py`):
- Change `from backend.db.crud import ...` → `from db.crud import ...`
- Change `from backend.db.database import ...` → `from api.database import ...`
- Change `from backend.db.models import ...` → `from db.models import ...`

### In `tests/test_crud.py` (was `backend/tests/test_crud.py`):
- Change `from backend.db.crud import ...` → `from db.crud import ...`
- Change `from backend.db.models import ...` → `from db.models import ...`

### In `api/routers/remediation.py` (was `remediation.py`):
- Update relative imports as needed
- If it imports `remediation_table`, the import path may need adjustment

### In `tests/test_api.py` (was `test_main.py`):
- Change `from main import app` → `from api.main import app` OR `from main import app` depending on how you structure root main.py

## Step 4: Fix requirements.txt

Replace the current `requirements.txt` with this exact content:

```
# ============================================================
# ECDAT — Enterprise Cryptographic Discovery & Analysis Tool
# Python Dependencies
# Install: pip install -r requirements.txt
# ============================================================

# ── SCANNER CORE ────────────────────────────────────────────
tree-sitter==0.21.3           # CRITICAL: pinned — 0.22+ breaks tree-sitter-languages
tree-sitter-languages==1.10.2 # Prebuilt grammar bundle (~40 languages)
PyYAML>=6.0                   # Rule file parsing (rules/*.yaml)

# ── BACKEND API ─────────────────────────────────────────────
fastapi>=0.111.0              # Web framework
uvicorn[standard]>=0.30.0     # ASGI server (includes websockets, httptools)
pydantic>=2.7.0               # Data validation
pydantic-settings>=2.3.0       # Environment-based config
python-multipart>=0.0.9       # Form data parsing (file uploads if needed)

# ── DATABASE ────────────────────────────────────────────────
SQLAlchemy>=2.0,<2.1          # ORM + SQL toolkit
psycopg[binary]>=3.1          # PostgreSQL driver (postgresql+psycopg://)

# ── ENV & CONFIG ────────────────────────────────────────────
python-dotenv>=1.0            # Load .env in local dev

# ── TESTING ────────────────────────────────────────────────
pytest>=8.0                   # Test runner
httpx>=0.27.0                 # HTTP client for FastAPI TestClient

# ── DEV / OPTIONAL ────────────────────────────────────────
# alembic>=1.13.0             # DB migrations (future — not needed for hackathon)
# black>=24.0                 # Code formatter (optional)
# ruff>=0.5.0                 # Linter (optional)
```

## Step 5: Create Skill Files

Create the following files with the EXACT content provided below:

### A. `skills/db/SKILL.md`
Write this file with content about database engineering for ECDAT. Include:
- Territory: `db/` and `api/database.py`
- Rules: PostgreSQL only, SQLAlchemy 2.0, TIMESTAMPTZ, TEXT not VARCHAR, ON DELETE CASCADE, check constraints match enums, model must match scanner Finding dataclass (all 12 fields), no multi-DBMS support, indexes on foreign keys and filter columns
- SQLAlchemy model pattern example
- CRUD layer pattern (normalize input dicts, handle aliases like filePath -> file)
- Database URL from env var
- Testing with SQLite in-memory
- What NOT to do table

### B. `skills/backend/SKILL.md`
Write this file with content about backend engineering for ECDAT. Include:
- Territory: `api/` directory
- Rules: FastAPI only, Pydantic v2, SQLAlchemy 2.0, APIRouter pattern, thin routers, business logic in services/, never accept raw shell commands, background tasks for scans, never leak tracebacks, API key auth with X-API-Key header, CBOM generated on demand not stored
- Pydantic model pattern with from_attributes=True
- Scan runner service pattern (subprocess call to scanner CLI, validate paths with pathlib, timeout, parse findings.json)
- Error response pattern with exception handlers
- Essential endpoints table: POST /scans (202), GET /scans/{id}, GET /scans/{id}/findings, GET /scans/{id}/cbom, GET /scans/{id}/risk-summary, GET /health
- What NOT to do table

### C. `skills/frontend/SKILL.md`
Write this file with content about frontend engineering for ECDAT. Include:
- Territory: `dashboard/` directory
- Rules: React 18 + Vite, Recharts for all charts, TailwindCSS, dark theme mandatory, IBM Plex Mono for code/data, Space Grotesk for headings, IBM Plex Sans for body, all data from API (no mock data), Axios for HTTP, loading states everywhere, error handling, polling for scan status every 3s, monospace for file paths and code
- Design system: colors (bg-primary #0B0E14, bg-card #111827, risk-critical #EF4444, risk-high #F97316, risk-medium #EAB308, risk-low #22C55E), font imports, tailwind config extension
- API client pattern in api.js with baseURL, headers, interceptors
- Component patterns: StatCards (4 cards), FindingsTable (columns, filters, pagination), ChartsPanel (Recharts BarChart + PieChart), RiskBadge (colored pills), ConfidenceStamp (shield icon)
- Pages: ScanList (/), ScanDetail (/scans/:id) with react-router-dom
- Environment variables (VITE_API_URL, VITE_API_KEY)
- What NOT to do table

### D. `skills/scanner/SKILL.md`
Write this file with content about scanner engineering. Include:
- Territory: `scanner/` directory
- Rules: ast module for Python, tree-sitter 0.21.3 for Java/JS, NEVER regex, unified Finding dataclass, externalized YAML rules, import resolution for confidence scoring, key_size extraction where possible
- The Finding dataclass contract (all 12 fields)
- Engine architecture: python_engine.py (ast.NodeVisitor), multilang_engine.py (tree-sitter queries + import tracking)
- Rule file structure (match_object, match_method, match_arg_contains, expected_import/expected_module, canonical_library, algorithm, primitive, weak_by_default)
- Confidence tiers: "high" (import verified) vs "unverified" (import not verified)
- What NOT to do table

### E. Keep existing skills
Keep `skills/cbom-quantum-risk/SKILL.md`, `skills/ci-cd-gate/SKILL.md`, and `skills/remediation-copy/SKILL.md` as they are. Do not modify them unless they reference old paths.

## Step 6: Update ARCHITECTURE.md

Rewrite `ARCHITECTURE.md` to reflect the ACTUAL directory structure after your reorganization. Use the target structure as the source of truth. Update:
- The directory tree to match what you created
- File paths in all descriptions
- The data flow diagram to use correct paths
- Technology stack section
- Component contracts section

## Step 7: Update AGENTS_AND_SKILLS.md

Rewrite `AGENTS_AND_SKILLS.md` to be a clean registry:

```markdown
# ECDAT Agents & Skills Registry

| Skill | Owner | Path | Status |
|---|---|---|---|
| Database | Ronak | `skills/db/SKILL.md` | Active |
| Backend API | Shreyanshi | `skills/backend/SKILL.md` | Active |
| Frontend | Karan + Satyam | `skills/frontend/SKILL.md` | Active |
| Scanner | Shashank | `skills/scanner/SKILL.md` | Active |
| CBOM + Quantum Risk | Maitreyi | `skills/cbom-quantum-risk/SKILL.md` | Active |
| CI/CD Gate | Shashank | `skills/ci-cd-gate/SKILL.md` | Active |
| Remediation Copy | Shreyanshi | `skills/remediation-copy/SKILL.md` | Active |
```

Remove any placeholder text like "[fill in...]".

## Step 8: Update .clinerules

Replace `.clinerules` with this updated version:

```
# Agent Constitution — ECDAT (PS 26164)
# Cline reads this file automatically from the workspace root.

## Non-negotiable rules

1. Crypto detection uses Python's `ast` module for Python files and tree-sitter
   for Java/JavaScript files. NEVER use regex for code scanning.
2. CBOM output MUST be valid CycloneDX JSON. Never invent a custom report format.
3. NEVER call an algorithm "vulnerable" without a documented reason.
4. NEVER fabricate scan evidence. If a file can't be parsed, log it as a
   `parse_error` finding.
5. Preserve the original discovered value alongside the normalized form.
6. NEVER commit secrets, API keys, or `.env` contents to the repo.
7. NEVER auto-accept your own generated code. Human review is mandatory.
8. Commit continuously in small, reviewable chunks.
9. Scope: source-code scanning for Python, Java, JavaScript. Binary/container
   scanning is out of scope.
10. Do not claim "zero false positives". Use "false positives minimized through
    AST context-awareness".
11. Quantum-risk score MUST be a documented, rule-based formula.
12. PQC recommendations MUST be mapped by cryptographic purpose.
13. NEVER say "DPDP violation detected". Use "cryptographic weakness detected".
14. NEVER claim 100% detection coverage.
15. Every new detection rule needs a unit test AND a negative test.
16. Do not hand-roll PQC primitives. Recommend standards only.
17. Every finding MUST be classified by type, lifetime, and business criticality.
18. The project uses a strict directory structure (see ARCHITECTURE.md). NEVER
    create files at the repository root unless explicitly allowed.
19. The backend is FastAPI with SQLAlchemy 2.0. NEVER use Flask or Django.
20. The frontend is React 18 with Vite. NEVER use Create React App or Next.js.

## Tech stack

- Scanner: Python 3.11+, ast (Python) + tree-sitter 0.21.3 (Java/JS)
- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL
- Frontend: React 18 + Vite + TailwindCSS + Recharts
- CI/CD: GitHub Actions
- Packaging: Docker / Docker Compose
- Report format: CycloneDX JSON (CBOM)

## Directory structure

```
ecdat/
├── api/              # FastAPI backend ONLY
├── scanner/          # Scanner engines ONLY
├── db/               # Database schema, models, CRUD ONLY
├── dashboard/        # React frontend ONLY
├── tests/            # All tests consolidated here
├── skills/           # AI agent skill files
├── docs/             # Documentation
├── .clinerules       # This file
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Before touching any file

- Read ARCHITECTURE.md and the relevant skills/*/SKILL.md first.
- If moving a file, update ALL imports that reference it.

## Definition of done

- Code builds and runs
- Unit test exists and passes
- No secrets in diff
- Commit message is specific
- Import paths are correct after any file moves
```

## Step 9: Update docker-compose.yml

Update `docker-compose.yml` to:
1. Reference `Dockerfile` at root (not `backend/Dockerfile`)
2. Uncomment or add the dashboard service if it was commented out
3. Ensure volume mounts point to correct paths (e.g., `db/schema.sql` not `backend/db/schema.sql`)
4. Ensure the backend service command uses `uvicorn api.main:app` (not `uvicorn main:app`)

## Step 10: Update README.md

Update `README.md` to reflect:
1. The new directory structure
2. Correct run commands (`python -m scanner.cli`, `uvicorn api.main:app`, `cd dashboard && npm run dev`)
3. Correct Docker Compose command
4. Reference to `ARCHITECTURE.md` for full details

## Step 11: Update CODEBASE_AUDIT.md

After completing ALL reorganization, rewrite `CODEBASE_AUDIT.md` with:
1. New directory tree
2. Updated file inventory showing where each file now lives
3. Updated import graph showing correct relationships
4. Status of each file after reorganization
5. Any remaining issues (e.g., "api/routers/scans.py does not exist yet — to be built by backend team")
6. Clear statement: "This audit reflects the state AFTER restructuring on <date>"

## Step 12: Verify No Broken Imports

Run this verification:
1. Check that `python -c "from scanner.finding import Finding; print('scanner OK')"` works
2. Check that `python -c "from db.models import Base; print('db OK')"` works
3. Check that `python -c "from api.models import FindingOut; print('api models OK')"` works
4. Check that pytest can discover tests: `python -m pytest --collect-only` (don't need to run, just collect)
5. If any import fails, fix it before finishing.

## Final Checklist

Before declaring done, verify:
- [ ] `backend/` directory no longer exists
- [ ] `frontend/` directory renamed to `dashboard/`
- [ ] `api/`, `db/`, `scanner/`, `dashboard/`, `tests/`, `skills/` all exist
- [ ] All Python files have correct imports after moves
- [ ] `requirements.txt` has all necessary dependencies
- [ ] `.clinerules` is updated
- [ ] `ARCHITECTURE.md` reflects actual structure
- [ ] `AGENTS_AND_SKILLS.md` is clean and current
- [ ] `CODEBASE_AUDIT.md` is rewritten for post-restructure state
- [ ] `skills/db/SKILL.md`, `skills/backend/SKILL.md`, `skills/frontend/SKILL.md`, `skills/scanner/SKILL.md` all exist with complete content
- [ ] No merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) in any file
- [ ] `docker-compose.yml` references correct paths

## Output

When done, produce a summary of:
1. Every file you moved and its new location
2. Every import path you updated
3. Every new file you created
4. Any files you deleted
5. Any issues you could not resolve
