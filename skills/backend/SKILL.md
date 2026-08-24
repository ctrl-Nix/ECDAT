# Backend Engineer Skill (FastAPI, SQLAlchemy 2.0, Pydantic v2)

Comprehensive guidance and operational standards for engineers building and maintaining the ECDAT backend API service layer.

---

## 1. Territory & Architecture Layout

The backend territory encompasses the entire `api/` directory tree and coordinates with `db/`:

```text
api/
├── __init__.py
├── main.py                     # FastAPI application factory, middleware, router inclusions
├── database.py                 # Engine & sessionmaker dependency injection (get_db)
├── models.py                   # Pydantic v2 request/response schemas
├── core/
│   ├── __init__.py
│   ├── config.py               # pydantic-settings environment variables & settings
│   └── security.py             # API key validation (X-API-Key header dependency)
├── routers/
│   ├── __init__.py
│   ├── scans.py                # POST /scans, GET /scans/{id}, GET /health
│   ├── findings.py             # GET /scans/{id}/findings, GET /scans/{id}/risk-summary
│   ├── cbom.py                 # GET /scans/{id}/cbom
│   └── remediation.py          # GET /scans/{id}/remediation/{finding_id} (Working reference)
└── services/
    ├── __init__.py
    ├── scan_runner.py          # Scanner subprocess execution & result persistence
    ├── risk_engine.py          # Quantum vulnerability scoring & tier assignment
    └── cbom_generator.py       # CycloneDX 1.6 Cryptographic BOM generation
```

---

## 2. Core Engineering Rules & Constraints

1. **Framework & Typing**:
   - Use **FastAPI** exclusively with async endpoints where I/O operations occur.
   - Use **Pydantic v2** (`BaseModel`, `ConfigDict(from_attributes=True)`) for all request/response models.
   - Use **SQLAlchemy 2.0** syntax (`select()`, `session.scalars()`, `Mapped[...]`, `mapped_column()`).
2. **Thin Router Pattern**:
   - Routers are strictly presentation & HTTP translation layers.
   - Business logic, algorithms, subprocess invocations, and calculations belong in `api/services/`.
   - Database operations must call `db/crud.py` functions; routers must NOT write ad-hoc raw SQL or execute direct table mutations.
3. **Execution Safety**:
   - Never accept raw shell command strings from API clients.
   - Scan requests must run asynchronously via `BackgroundTasks` or background workers, returning `202 Accepted` immediately.
   - Execute scanner CLI via parameter lists (`shell=False`) with strict path canonicalization (`os.path.abspath`, `os.path.realpath`) to prevent traversal.
4. **Security & Resilience**:
   - Guard protected routes with the `get_api_key` dependency (`X-API-Key` header).
   - Global exception handling must sanitize 500 errors and avoid leaking stack traces or internal environment variables.
   - **CBOM On Demand**: Generate CycloneDX CBOMs dynamically from persisted scan findings rather than storing static duplicate JSON in the DB.

---

## 3. Working Reference Pattern

Study [api/routers/remediation.py](file:///c:/Users/KIIT/ECDAT/api/routers/remediation.py) as the gold standard for:
- Router declaration with `APIRouter()`
- Explicit type annotations on request parameters and return types
- Safe fallback mechanism (AI service → deterministic static table fallback)
- Clean error raising with `fastapi.HTTPException`

---

## 4. Endpoint Specifications

| Method | Endpoint | Status | Auth Required | Description |
|---|---|---|---|---|
| `POST` | `/scans` | `202 Accepted` | Yes | Initiates a repository crypto scan via background task. |
| `GET` | `/scans/{id}` | `200 OK` | Yes | Retrieves scan metadata, status, findings, and summary. |
| `GET` | `/scans/{id}/findings` | `200 OK` | Yes | Paginated findings query (supports `risk_tier`, `limit`, `offset`). |
| `GET` | `/scans/{id}/risk-summary`| `200 OK` | Yes | Aggregated counts by risk tier (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`). |
| `GET` | `/scans/{id}/cbom` | `200 OK` | Yes | CycloneDX 1.6 JSON Cryptographic Bill of Materials export. |
| `GET` | `/scans/{id}/remediation/{finding_id}` | `200 OK` | Yes | Deterministic / AI-assisted remediation advice for a finding. |
| `GET` | `/health` | `200 OK` | No | Liveness and health check endpoint. |

---

## 5. Implementation Code Patterns

### 5.1 Pydantic Model Pattern (Pydantic v2)
```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
import datetime as dt

class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: int
    file: str
    line: int
    algorithm: str
    key_size: Optional[int] = None
    confidence: str
    risk_tier: Optional[str] = None
    risk_reason: Optional[str] = None
    criticality: str

class ScanCreateRequest(BaseModel):
    repo_name: str = Field(..., description="Logical repository name")
    repo_path: str = Field(..., description="Filesystem directory path to scan")
    repo_url: Optional[str] = None

class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: Optional[int]
    started_at: dt.datetime
    status: str
```

### 5.2 Router Pattern for `POST /scans` (202 Accepted + BackgroundTask)
```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from api.database import get_db
from api.core.security import verify_api_key
from api.models import ScanCreateRequest, ScanResponse
from api.services.scan_runner import run_scan_pipeline
import db.crud as crud

router = APIRouter(prefix="/scans", tags=["Scans"], dependencies=[Depends(verify_api_key)])

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    payload: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Deduplicate or create repository entry
    repo = crud.get_or_create_repository(db, name=payload.repo_name, url=payload.repo_url)
    
    # Initialize scan record in running state
    scan = crud.start_scan(db, repo_id=repo.id, status="running")
    db.commit()

    # Dispatch background execution
    background_tasks.add_task(
        run_scan_pipeline,
        scan_id=scan.id,
        repo_path=payload.repo_path
    )

    return {"scan_id": scan.id, "status": "running", "message": "Scan dispatched successfully"}
```

### 5.3 Scan Runner Service Pattern (`api/services/scan_runner.py`)
```python
import subprocess
import json
import os
import sys
from pathlib import Path
from api.database import SessionLocal
import db.crud as crud
from api.services.risk_engine import score_findings

def run_scan_pipeline(scan_id: int, repo_path: str):
    """Executes scanner CLI as a subprocess and persists scored findings."""
    db = SessionLocal()
    try:
        # Validate path
        target = Path(repo_path).resolve()
        if not target.exists() or not target.is_dir():
            crud.complete_scan(db, scan_id=scan_id, status="failed")
            db.commit()
            return

        # Execute scanner CLI safely
        cmd = [sys.executable, "-m", "scanner.cli", str(target), "--json"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        raw_findings = json.loads(result.stdout)
        
        # Enrich findings with quantum risk evaluation
        scored_findings = score_findings(raw_findings)
        
        # Bulk persist
        crud.save_findings(db, scan_id=scan_id, findings=scored_findings)
        crud.complete_scan(db, scan_id=scan_id, status="completed")
        db.commit()
    except Exception as exc:
        db.rollback()
        crud.complete_scan(db, scan_id=scan_id, status="failed")
        db.commit()
    finally:
        db.close()
```

### 5.4 Sanitized Error Response Pattern
```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("ecdat.api")

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "An internal server error occurred. Please contact an administrator."}
    )
```

---

## 6. Database CRUD Function Catalog (`db/crud.py`)

Always use the tested functions from `db/crud.py`:
- `get_or_create_repository(session, name, url=None)`
- `start_scan(session, repo_id, status="running")`
- `complete_scan(session, scan_id, status="completed")`
- `get_scan(session, scan_id)`
- `get_scan_with_findings(session, scan_id)`
- `list_scans(session, repo_id=None, limit=50)`
- `save_finding(session, scan_id, finding_dict)`
- `save_findings(session, scan_id, findings_list)`
- `get_findings_for_scan(session, scan_id, risk_tier=None, limit=None, offset=0)`
- `count_findings(session, scan_id)`
- `get_risk_summary(session, scan_id)`

---

## 7. What NOT To Do

| Anti-Pattern | Why It Is Prohibited | Correct Approach |
|---|---|---|
| Direct SQL queries in routers | Breaks database abstraction and test isolation | Use `db/crud.py` functions |
| Blocking subprocess calls in routes | Freezes the async event loop and hangs all requests | Use `BackgroundTasks` or Celery workers |
| `shell=True` in subprocess calls | Severe remote code execution vulnerability | Use argument arrays with `shell=False` |
| Returning raw exception strings | Leaks stack traces and system architecture to attackers | Log internally, return sanitized generic JSON |
| Pydantic v1 `class Config: orm_mode = True` | Deprecated in Pydantic v2 | Use `ConfigDict(from_attributes=True)` |
| Storing static CBOM JSON in DB | Creates schema synchronization drift | Generate CBOM on demand via service transform |

---

## 8. Verification & Testing

Run the test suite during development:
```bash
# Run all backend unit and integration tests
pytest

# Test API endpoints specifically
pytest tests/test_api.py tests/test_remediation.py

# Test CRUD layer
pytest tests/test_crud.py
```

---

## 9. Definition of Done Checklist

- [ ] Route uses `APIRouter()` and is mounted in `api/main.py`.
- [ ] Protected endpoints enforce `X-API-Key` security dependency.
- [ ] Request and response models use Pydantic v2 schemas.
- [ ] Database read/write logic calls `db/crud.py`.
- [ ] Subprocess calls validate target paths and run in background tasks.
- [ ] Unit/integration tests added under `tests/` and pass with 100% success.
- [ ] No internal traceback or schema leaks in HTTP error responses.
