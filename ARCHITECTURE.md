# ARCHITECTURE.md — ECDAT (PS 26164)

Draft this together as a team on Day 1 (backend trio + Maitreyi). This file
is a survival-gate item — it must be committed before deep implementation
starts.

## Scope for this build
- Source-code scanning: Python only (see `.clinerules` for the full scope list)
- No ministry-provided dataset — self-contained, team supplies all test repos

## Database schema (PostgreSQL)

```sql
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT
);

CREATE TABLE scans (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id),
    started_at TIMESTAMP DEFAULT now(),
    status TEXT DEFAULT 'pending'
);

CREATE TABLE findings (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER REFERENCES scans(id),
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    algorithm TEXT NOT NULL,
    key_size INTEGER,
    confidence TEXT DEFAULT 'high',

    -- Risk fields (see skills/cbom-quantum-risk/SKILL.md)
    risk_tier TEXT,           -- LOW / MEDIUM / HIGH / CRITICAL
    risk_reason TEXT,         -- one-sentence explanation, factor-based

    -- PS 26164 explicitly requires classification by "type, lifetime and
    -- business criticality" — this column is reserved from Day 1 so no
    -- team member has to touch DB/API/frontend again later to add it.
    -- Logic for populating this can be written any day up to Day 4;
    -- the column itself must exist from Day 1.
    criticality TEXT DEFAULT 'MEDIUM'  -- CRITICAL / HIGH / MEDIUM
);
```

Indexes to add once the table has real data (Day 4, owned by Ronak):
```sql
CREATE INDEX idx_findings_scan_id ON findings(scan_id);
CREATE INDEX idx_findings_severity ON findings(risk_tier);
```

## API routes (FastAPI)

| Route | Owner | Purpose |
|---|---|---|
| `POST /scans` | Shashank | Trigger a scan against a repo path/URL (background task) |
| `GET /scans/{id}` | Ronak | Fetch scan status + findings |
| `GET /scans/{id}/cbom` | Backend trio (coordinate Day 3) | Export CycloneDX CBOM JSON |
| `GET /scans/{id}/remediation/{finding_id}` | Shreyanshi | Fetch remediation text for one finding |

## Folder structure

```
ecdat/
├── scanner/              # AST-based crypto detection engine
├── backend/               # FastAPI app
├── frontend/               # React dashboard
├── skills/                  # Agent skill definitions
├── .github/workflows/     # CI/CD compliance gate
├── ARCHITECTURE.md
├── .clinerules
└── AGENTS_AND_SKILLS.md
```

## Classification model (per PS wording)

The PS requires classification by **type, lifetime, and business criticality**,
and risk assessment via **Mosca's algorithm** — comparing data lifetime plus
migration time against the expected arrival of a quantum computer capable of
breaking current cryptography. See `skills/cbom-quantum-risk/SKILL.md` for the
exact factor-based scoring formula and the `criticality` classification logic.
