# Database Layer — ECDAT / PS 26164 (Ronak)

> "Gives the system memory — without this, every scan result vanishes when the
> terminal closes."

The relational store: **repositories → scans → findings**, plus the data-access
functions the FastAPI backend calls instead of writing raw SQL. Schema matches
[`ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Layout

```
backend/
├── db/
│   ├── schema.sql     # canonical Postgres DDL (source of truth, = ARCHITECTURE.md)
│   ├── models.py      # SQLAlchemy ORM models (mirror schema.sql)
│   ├── database.py    # engine + get_session() FastAPI dependency
│   ├── crud.py        # save_scan / save_finding / get_findings_for_scan …
│   ├── schemas.py     # Pydantic response models for GET /scans/{id}
│   └── seed.py        # Day-5: seed N findings + benchmark the hot query
└── tests/test_crud.py # offline suite, runs on SQLite (no Docker needed)
```

## Run the database (Day 1)

From the repo root, one command:

```bash
docker compose up -d
```

`backend/db/schema.sql` is applied automatically on first start. To re-apply
after editing it, reset the volume:

```bash
docker compose down -v && docker compose up -d
```

## Run the tests (no Docker required)

```bash
pip install -r requirements.txt
python -m pytest
```

## Data model (matches ARCHITECTURE.md)

| table | columns |
|-------|---------|
| `repositories` | `id`, `name`, `url` |
| `scans` | `id`, `repo_id→repositories`, `started_at`, `status` |
| `findings` | `id`, `scan_id→scans`, `file`, `line`, `algorithm`, `key_size`, `confidence`, `risk_tier`, `risk_reason`, `criticality` |

- `scans.status`: `pending | running | completed | failed`
- `findings.risk_tier`: `LOW | MEDIUM | HIGH | CRITICAL` (nullable until scored)
- `findings.criticality`: `MEDIUM | HIGH | CRITICAL` (business criticality, per PS)
- Deleting a repo or scan cascades to its children.
- **Day-4 indexes:** `idx_findings_scan_id`, `idx_findings_severity` (on `risk_tier`).

## The finding contract

`save_finding()` / `save_findings()` follow the ARCHITECTURE.md shape and also
accept common aliases so small scanner-output variations don't break a write:

```jsonc
// scanner (Shashank) produces:
{ "file": "hash.py", "line": 42, "algorithm": "MD5",
  "key_size": null, "confidence": "high" }

// the CBOM/quantum-risk step (Maitreyi/Shashank) adds:
{ "risk_tier": "CRITICAL", "risk_reason": "MD5 is broken…",
  "criticality": "HIGH" }
```

Accepted aliases: `file_path`/`filePath`→`file`, `keyLength`→`key_size`,
`severity`/`tier`→`risk_tier`. Missing/garbage fields never crash a write:
`file`/`algorithm` fall back to `"UNKNOWN"`, `line` to `0`.

## How the backend uses it

```python
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.database import get_session
from backend.db import crud
from backend.db.schemas import ScanWithFindings

# Ronak owns GET /scans/{id} (status + findings) per ARCHITECTURE.md
@app.get("/scans/{scan_id}", response_model=ScanWithFindings)
def read_scan(scan_id: int, db: Session = Depends(get_session)):
    data = crud.get_scan_with_findings(db, scan_id)
    if data is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return data
```

Scanner side persists a run:

```python
repo = crud.get_or_create_repository(db, name="demo", url=repo_url)
scan = crud.start_scan(db, repo.id)
crud.save_findings(db, scan.id, scanner_output)   # list of finding dicts
crud.complete_scan(db, scan.id)
db.commit()
```

## crud reference

| function | purpose |
|----------|---------|
| `get_or_create_repository(db, name, url=…)` | dedupe repos by url (else name) |
| `start_scan(db, repo_id)` / `save_scan(…)` | open a scan row (`running`) |
| `complete_scan(db, scan_id, status=…)` | mark finished |
| `save_finding(db, scan_id, finding)` | persist one finding |
| `save_findings(db, scan_id, findings)` | bulk persist |
| `get_scan(db, scan_id)` | one scan |
| `get_scan_with_findings(db, scan_id)` | scan + findings + risk summary (route payload) |
| `get_findings_for_scan(db, scan_id, risk_tier=…)` | findings, optional filter |
| `get_risk_summary(db, scan_id)` | risk-tier histogram for the dashboard header |
| `list_scans(db, repo_id=…)` / `get_latest_scan_for_repo(db, repo_id)` | scan lists |

## Day-by-day status (Ronak's card)

- [x] **Day 1** — three tables; Postgres runs in Docker (one command)
- [x] **Day 2** — `schema.sql` with CREATE TABLE + foreign keys
- [x] **Day 3** — `save_scan()`, `save_finding()`, `get_findings_for_scan()` + route payload
- [x] **Day 4** — indexes on `findings.scan_id` and `risk_tier`
- [x] **Day 5** — seed script + benchmark of the dashboard query
- [ ] **Day 6** — freeze: bug-fix only
