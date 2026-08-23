# Database Layer — PS 26164 (Ronak)

> "Gives the system memory — without this, every scan result vanishes when the
> terminal closes."

The relational store for the Cryptographic Discovery platform: **repositories →
scans → findings**, plus the data-access functions the FastAPI backend calls
instead of writing raw SQL.

## Layout

```
db/
├── schema.sql              # canonical Postgres DDL (source of truth for the DB)
├── docker-compose.yml      # Postgres-only, one-command dev DB
├── requirements.txt        # SQLAlchemy, psycopg, pytest
├── .env.example            # copy to .env
├── cbom_db/                # the Python package the backend imports
│   ├── database.py         #   engine + get_session() FastAPI dependency
│   ├── models.py           #   SQLAlchemy ORM models (mirror schema.sql)
│   ├── crud.py             #   save_scan / save_finding / get_findings_for_scan …
│   ├── schemas.py          #   Pydantic response models for /scans, /findings
│   └── cbom.py             #   findings → CycloneDX components (with Maitreyi)
├── scripts/
│   ├── seed_and_benchmark.py   # Day-5: seed N findings, time the hot query
│   └── export_schema.py        # drift guard: models vs schema.sql (CI-ready)
└── tests/test_crud.py      # offline suite, runs on SQLite (no Docker needed)
```

## Run the database (Day 1)

From `db/`, one command:

```bash
docker compose up -d
```

`schema.sql` is applied automatically on first start. To re-apply after editing
it, reset the volume:

```bash
docker compose down -v && docker compose up -d
```

## Run the tests (no Docker required)

The whole layer is verifiable offline against in-memory SQLite:

```bash
pip install -r requirements.txt
python -m pytest
```

## The data model

| table | key columns |
|-------|-------------|
| `repositories` | `id`, `name`, `url`, `default_branch`, `created_at` |
| `scans` | `id`, `repo_id→repositories`, `commit_sha`, `status`, `total_findings`, `started_at`, `finished_at` |
| `findings` | `id`, `scan_id→scans`, `file_path`, `line`, `algorithm`, `primitive`, `key_size`, `asset_type`, `severity`, `quantum_risk`, `deprecated`, `evidence`, `remediation`, `recommended_replacement`, `raw` |

- `scans.status` ∈ `queued | running | completed | failed`
- `findings.severity` ∈ `info | low | medium | high | critical`
- `findings.quantum_risk` ∈ `low | medium | high | critical` (nullable)
- Deleting a repo or scan cascades to its children.
- **Day-4 indexes:** `ix_findings_scan_id`, `ix_findings_severity`, and the
  composite `ix_findings_scan_severity` that serves the dashboard's
  "findings for this scan, filtered by severity" query.

## The finding contract (Day-3 lock-in)

`save_finding()` / `save_findings()` accept **either** agreed shape — whichever
the trio settles on just works, and unknown keys are preserved verbatim in
`findings.raw` for lossless CBOM export:

```jsonc
// scanner (Shashank)
{ "algorithm": "MD5", "file": "hash.py", "line": 42, "severity": "high" }

// CBOM fields (Maitreyi)
{ "algorithm": "RSA", "filePath": "keys.py", "keyLength": 1024,
  "assetType": "algorithm", "severity": "critical", "quantum_risk": "critical" }
```

Missing/garbage fields never crash a scan write: `algorithm`/`file_path` fall
back to `"UNKNOWN"`, `severity` to `"medium"`.

## How the backend trio uses it

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from cbom_db.database import get_session
from cbom_db import crud
from cbom_db.schemas import ScanDetail, FindingOut

# Ronak owns /scans/{id} and /findings
@app.get("/scans/{scan_id}", response_model=ScanDetail)
def read_scan(scan_id: int, db: Session = Depends(get_session)):
    scan = crud.get_scan(db, scan_id)
    return ScanDetail(
        **scan.__dict__,
        repository=scan.repository,
        summary=crud.get_scan_summary(db, scan_id),
    )

@app.get("/findings", response_model=list[FindingOut])
def list_findings(scan_id: int, severity: str | None = None,
                  db: Session = Depends(get_session)):
    return crud.get_findings_for_scan(db, scan_id, severity=severity)
```

The scanner side persists a run like this:

```python
repo = crud.get_or_create_repository(db, name="demo", url=repo_url)
scan = crud.start_scan(db, repo.id, commit_sha=sha)
crud.save_findings(db, scan.id, scanner_output)   # list of finding dicts
crud.complete_scan(db, scan.id)                    # sets status + total_findings
db.commit()
```

## crud reference

| function | purpose |
|----------|---------|
| `get_or_create_repository(db, name, url=…)` | dedupe repos by url (else name) |
| `start_scan(db, repo_id, …)` / `save_scan(…)` | open a scan row (`running`) |
| `complete_scan(db, scan_id, status=…)` | mark finished + refresh count |
| `save_finding(db, scan_id, finding)` | persist one finding (either contract) |
| `save_findings(db, scan_id, findings)` | bulk persist + roll up count |
| `get_scan(db, scan_id)` | one scan |
| `get_findings_for_scan(db, scan_id, severity=…)` | findings, optional filter |
| `get_scan_summary(db, scan_id)` | severity histogram for the dashboard header |
| `list_scans(db, repo_id=…)` / `get_latest_scan_for_repo(db, repo_id)` | scan lists |

## Day-by-day status (Ronak's card)

- [x] **Day 1** — three tables sketched; Postgres runs in Docker (one command)
- [x] **Day 2** — `schema.sql` with CREATE TABLE + foreign keys
- [x] **Day 3** — `save_scan()`, `save_finding()`, `get_findings_for_scan()` for the API
- [x] **Day 4** — indexes on `findings.scan_id` and `severity`
- [x] **Day 5** — seed script + benchmark of the dashboard query
- [ ] **Day 6** — freeze: bug-fix only

> **Open Day-1 decision (with the backend trio):** this layer uses **SQLAlchemy**
> (not raw SQL) because it gives FastAPI clean session dependency-injection and
> the query logic lives in one reviewed place. `schema.sql` stays the canonical
> DDL, so raw-SQL fans still get a readable schema. Easy to revisit.
