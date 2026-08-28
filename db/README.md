# Database Layer — ECDAT / PS 26164 (Ronak)

> "Gives the system memory — without this, every scan result vanishes when the
> terminal closes."

The relational store for ECDAT: **repositories → scans → findings**, with
per-finding **risk_assessments** and signed **reports**, plus the data-access
functions the FastAPI backend calls instead of writing raw SQL.

## Layout

```
db/
├── schema.sql                       # canonical Postgres DDL (source of truth for a FRESH db)
├── models.py                        # SQLAlchemy ORM models (mirror schema.sql)
├── crud.py                          # the ONLY module that writes to the DB
├── seed.py                          # seed N findings + benchmark the hot query
├── migrations/
│   └── 001_secure_reporting.sql     # upgrade path for an EXISTING db (idempotent ALTERs)
└── README.md
```

The engine / session live in `api/database.py` (`get_session()` FastAPI
dependency). Pydantic response models live in `api/models.py`
(`FindingOut`, `RiskAssessmentOut`, `ScanWithFindings`, …).

## Run the database

From the repo root, one command (starts Postgres + backend + dashboard):

```bash
docker compose up -d
```

For a **fresh** volume, Compose applies `db/schema.sql` then
`db/migrations/001_secure_reporting.sql` on init. To re-apply after editing the
schema, reset the volume:

```bash
docker compose down -v && docker compose up -d
```

For an **existing** database, back up first, then run the versioned migration
once (a container restart does NOT upgrade an existing volume):

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 < db/migrations/001_secure_reporting.sql
```

## Run the tests (no Docker required)

```bash
pip install -r requirements.txt
python -m pytest tests/test_crud.py
```

## Data model (5 tables)

Evidence and interpretation are kept separate: a **finding** is a raw discovery
fact; a **risk_assessment** is its (recomputable) interpretation; a **report**
is a signed custody record of a synced bundle.

| table | key columns |
|-------|-------------|
| `repositories` | `id`, `name`, `url`, `organization_id`, `external_id` |
| `scans` | `id`, `repo_id→repositories`, `started_at`, `status`, `source_scan_id`, `scan_context` |
| `findings` | `id`, `scan_id→scans`, `file`, `line`, `algorithm`, `key_size`, `confidence`, `matched_call`, `library`, `primitive`, `language`, `weak_by_default`, `detection_method`, `source_context`, `risk_tier`, `risk_reason`, `criticality` |
| `risk_assessments` | `id`, `finding_id→findings` (UNIQUE), `risk_model_version`, `classical_broken`, `quantum_vulnerable`, `hndl_exposure`, `recommended_replacement`, `recommendation_type`, `migration_effort_days`, `data_shelf_life_years`, `quantum_threat_horizon_years`, `assumption_source`, `assessed_at` |
| `reports` | `id`, `report_id` (UNIQUE), `scan_id→scans` (UNIQUE), `organization_id`, `repository_id`, `agent_id`, `bundle_digest` (UNIQUE), `signature_algorithm`, `classification`, `created_at`, `expires_at` |

Notes:
- `scans.status`: `pending | running | completed | failed`
- `findings.risk_tier`: `LOW | MEDIUM | HIGH | CRITICAL` (nullable until scored);
  `criticality`: `MEDIUM | HIGH | CRITICAL` (business criticality, per PS)
- `findings.source_context`: `SOURCE | TEST_ONLY | DEMO_ONLY` — keeps test/demo
  findings out of "deployed production exposure" claims.
- **Two independent risk axes** live on `risk_assessments`: `classical_broken`
  (broken by today's computers) vs `quantum_vulnerable` (broken by Shor's/Grover's).
  `hndl_exposure` (harvest-now-decrypt-later) is `UNKNOWN` until a data shelf-life
  assumption is supplied.
- Deleting a repo → scans → findings → risk_assessments/reports all cascade.
- **Indexes:** `idx_findings_scan_id`, `idx_findings_severity` (on `risk_tier`),
  `idx_findings_source_context`, `idx_repositories_org_external`,
  `idx_reports_org_created`.

## The finding contract

`save_finding()` / `save_findings()` store the scanner's evidence shape and
accept common aliases so small scanner-output variations don't break a write.
`save_findings()` also scores each finding (via `api.services.risk_engine`) and
writes the matching `risk_assessments` row.

```jsonc
// scanner (scanner/finding.py) produces:
{ "file": "hash.py", "line": 42, "algorithm": "MD5", "matched_call": "hashlib.md5",
  "library": "hashlib", "primitive": "hash", "language": "python",
  "weak_by_default": true, "confidence": "high", "detection_method": "static_analysis" }

// the risk engine adds the interpretation -> risk_assessments:
{ "risk_tier": "CRITICAL", "classical_broken": true, "quantum_vulnerable": false,
  "recommended_replacement": "SHA-256", "recommendation_type": "classical" }
```

Accepted aliases: `file_path`/`filePath`→`file`, `keyLength`→`key_size`,
`severity`/`tier`→`risk_tier`. Missing/garbage fields never crash a write:
`file`/`algorithm` fall back to `"UNKNOWN"`, `line` to `0`.

## How the backend uses it

```python
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from api.database import get_session
from db import crud
from api.models import ScanWithFindings

# GET /scans/{id} — status + findings + risk summary
@router.get("/scans/{scan_id}", response_model=ScanWithFindings)
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
crud.save_findings(db, scan.id, scanner_output)   # scores + writes risk_assessments too
crud.complete_scan(db, scan.id)
db.commit()
```

## crud reference

| function | purpose |
|----------|---------|
| `get_or_create_repository(db, name, url=…, organization_id=…, external_id=…)` | dedupe repos (org+external, else url, else name) |
| `start_scan(db, repo_id, …)` / `save_scan(…)` | open a scan row |
| `complete_scan(db, scan_id, status=…)` | mark finished |
| `save_finding(db, scan_id, finding)` | persist one finding |
| `save_findings(db, scan_id, findings)` | bulk persist + score + write risk_assessments |
| `get_scan(db, scan_id)` / `get_scan_with_findings(db, scan_id)` | scan, or scan + findings + summary |
| `get_findings_for_scan(db, scan_id, risk_tier=…)` | findings, optional filter |
| `get_finding(db, finding_id)` | one finding |
| `get_risk_assessments_for_scan(db, scan_id)` | `{finding_id: RiskAssessment}` for a scan |
| `get_risk_summary(db, scan_id)` | risk-tier histogram for the dashboard header |
| `ingest_signed_report(db, …)` | idempotently store a verified signed report bundle |
| `list_scans(db, repo_id=…)` / `get_latest_scan_for_repo(db, repo_id)` | scan lists |
