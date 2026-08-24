# SKILL: Generate ECDAT Codebase Context Report
## Purpose: Produce a comprehensive audit file of the current local codebase for AI review and restructuring

---

## Your Task

Scan the entire local `ecdat/` repository and produce a single markdown file named `CODEBASE_AUDIT.md` at the repo root. This file will be given to another AI (me) to understand the current state, identify fragmentation, and restructure the codebase properly.

**Do NOT modify any existing code.** Only read and report.

---

## Step 1: Directory Tree

Run `tree -I 'node_modules|__pycache__|.git|*.pyc|dist|build'` (or equivalent) and include the **complete directory structure** at the top of the audit.

If `tree` is unavailable, manually list every directory and file recursively, excluding:
- `node_modules/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `.venv/`, `venv/`
- `*.pyc`, `*.pyo`, `.DS_Store`

---

## Step 2: File Inventory with Purpose Tags

For **every Python file, YAML file, SQL file, JSX file, and config file** in the repo, create an entry in this format:

```markdown
### `relative/path/to/file.py`
- **Lines of code:** (count non-empty, non-comment lines roughly)
- **Purpose:** (one sentence: what does this file do?)
- **Status:** `clean` | `fragmented` | `duplicate` | `orphan` | `conflict-marker`
- **Imports from:** (list what this file imports from OTHER project files, not external libs)
- **Imported by:** (list which OTHER project files import this one)
- **Issues found:** (list any problems: merge conflict markers `<<<<<<<`, duplicate logic, broken imports, placeholder code, TODO comments, empty functions, etc.)
- **Content summary:** (3-5 bullet points describing the actual code inside)
```

**Special attention for `__init__.py` files:**
For EVERY `__init__.py` found, explicitly note:
- What package it belongs to
- What it exports
- Whether it's empty, has imports, or has logic
- Whether it conflicts with another `__init__.py` at a different level

---

## Step 3: Backend Fragmentation Analysis

This is the most critical section. Deep-scan the backend code and report:

### 3.1 Router/Endpoint Duplication
- List every file that defines FastAPI routes/endpoints
- For each route path (e.g., `POST /scans`), note which file(s) define it
- Flag any **duplicate route definitions** across files

### 3.2 Model/Schema Duplication
- List every Pydantic model or SQLAlchemy model file
- Note if the same model is defined in multiple places
- Check if `Finding` schema is defined in scanner vs backend vs both

### 3.3 Database Connection Chaos
- Find every place a database connection/engine is created
- Note if multiple files create their own engines
- Check if SQLAlchemy sessions are managed consistently

### 3.4 Service Layer Gaps
- List files in any `services/`, `utils/`, `helpers/` directories
- Note which business logic is scattered in routers instead of services

### 3.5 Import Graph
Draw a simple text diagram showing:
```
scanner/cli.py -> scanner/python_engine.py
               -> scanner/multilang_engine.py
api/main.py -> api/routers/scans.py -> ???
```
Show the actual import relationships as they exist RIGHT NOW.

---

## Step 4: Scanner Integration Status

Since the user mentioned they "added scanner code but haven't pushed it," carefully audit:

- Where does the scanner code live? (`scanner/`? root? somewhere else?)
- Does the backend API call the scanner CLI as a subprocess? If so, where?
- Is there a `scan_runner.py` or equivalent? What does it actually do?
- Does the scanner output (`findings.json`) get ingested anywhere?
- Are the scanner's `Finding` dataclass and the backend's Pydantic model the same shape? List any field mismatches.

---

## Step 5: Configuration & Environment

- List all config files: `.env`, `.env.example`, `docker-compose.yml`, `Dockerfile`, `vite.config.js`, etc.
- For each, note: does it exist? Is it functional or placeholder?
- Check for hardcoded secrets, paths, or URLs
- Check if `requirements.txt` and `package.json` are at the correct locations per ARCHITECTURE.md

---

## Step 6: Merge Conflict Markers

**CRITICAL:** Search every file for these exact strings:
- `<<<<<<<`
- `=======`
- `>>>>>>>`

If found, list the exact file path and line numbers. Do NOT attempt to resolve them — just report.

---

## Step 7: Dashboard Status

- Where is the React dashboard code? (`dashboard/src/`? `frontend/`? somewhere else?)
- Is it using mock data or real API calls?
- What components exist? List them.
- Is it using the design system from the spec (dark theme, IBM Plex fonts, Recharts)?

---

## Step 8: Test Coverage

- List all test files
- For each, note: what does it test? Does it pass? Is it empty/placeholder?
- Check if test fixtures match the scanner's expected input

---

## Output Format

The final `CODEBASE_AUDIT.md` should be structured exactly as:

```markdown
# ECDAT Codebase Audit
Generated: <timestamp>
Repo root: <absolute path>

## 1. Directory Tree
...

## 2. File Inventory
...

## 3. Backend Fragmentation Analysis
...

## 4. Scanner Integration Status
...

## 5. Configuration & Environment
...

## 6. Merge Conflict Markers
...

## 7. Dashboard Status
...

## 8. Test Coverage
...

## 9. Summary & Red Flags
(Bullet list of the top 10 most urgent issues, ranked by severity)
```

---

## Rules

1. **Read-only.** Do not write, delete, or modify any file.
2. **Be exhaustive.** Don't skip files because they seem "obvious."
3. **Be honest.** If a file is empty, say it's empty. If imports are broken, say they're broken.
4. **Include actual code snippets** (5-10 lines) for critical/fragmented files so the reviewing AI can see the problem.
5. **Flag the 4 `__init__.py` files explicitly** — the user specifically mentioned this as a concern.
6. **If a file is large (>200 lines),** provide a detailed summary rather than full content.
