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

`db/schema.sql` is applied automatically on first start. To re-apply
after editing it, reset the volume:

```bash
docker compose down -v && docker compose up -d
```

## Run the tests (no Docker required)

```bash
pip install -r requirements.txt
python -m pytest
```

## Data model

The `findings` table stores the **full pipeline output** — every scanner
evidence field plus the risk-engine interpretation — so nothing is dropped
between scan and dashboard (closes CODEBASE_AUDIT.md §3.2 / §4).

| table | columns |
|-------|---------|
| `repositories` | `id`, `name`, `url` |
| `scans` | `id`, `repo_id→repositories`, `started_at`, `status` |
| `findings` — scanner evidence | `id`, `scan_id→scans`, `file`, `line`, `algorithm`, `matched_call`, `library`, `primitive`, `language`, `weak_by_default`, `key_size`, `confidence`, `detection_method` |
| `findings` — risk interpretation | `risk_tier`, `risk_reason`, `criticality`, `quantum_vulnerable`, `classical_broken`, `recommended_replacement`, `recommendation_type`, `created_at` |

- `scans.status`: `pending | running | completed | failed`
- `findings.risk_tier`: `LOW | MEDIUM | HIGH | CRITICAL` (nullable until scored)
- `findings.criticality`: `MEDIUM | HIGH | CRITICAL` (business criticality, per PS)
- `findings.recommendation_type`: `classical | hybrid | post-quantum` (nullable)
- `quantum_vulnerable` / `classical_broken` are the **two independent risk axes**
  the pitch centres on — now persisted, so the dashboard can render both.
- CHECK constraints enforce the enum values above (match the values used in code).
- Deleting a repo or scan cascades to its children.
- **Indexes:** `idx_findings_scan_id`, `idx_findings_severity` (on `risk_tier`), `idx_scans_repo_id`.

## The finding contract

`save_finding()` / `save_findings()` store the full scanner + risk-engine shape
and accept common aliases so small scanner-output variations don't break a write:

```jsonc
// scanner (scanner/finding.py) produces:
{ "file": "hash.py", "line": 42, "matched_call": "hashlib.md5",
  "library": "hashlib", "algorithm": "MD5", "primitive": "hash",
  "language": "python", "weak_by_default": true, "confidence": "high",
  "key_size": null, "detection_method": "static_analysis" }

// risk_engine.score_finding() enriches with:
{ "risk_tier": "CRITICAL", "risk_reason": "MD5 is broken…", "criticality": "HIGH",
  "quantum_vulnerable": false, "classical_broken": true,
  "recommended_replacement": "SHA-256", "recommendation_type": "classical" }
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
