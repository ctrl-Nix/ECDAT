# 1. Header

| Field | Value |
|---|---|
| Feature name | Audit logging (contract code `AUD`, action prefix `ecdat.`) |
| Feature slug | `audit-logging` |
| Owner | **Not named in `SYSTEM_INTERFACE_CONTRACT.md`.** The contract assigns AUD the SOLE files below but no individual. Integration owners for its COORDINATED files: DB lane (Ronak), backend lane (Shreyanshi), deploy lane (unnamed). A human must assign the feature owner. |
| Spec version | v1.0-draft |
| Status | **DRAFT. BLOCKED, do not start implementation.** Blockers: (1) RBAC merged (Wave 1), (2) ENR merged before the shared `security.py` / `config.py` / `main.py` edits, (3) human sign-off on C-22 (a), (b), (c), (4) human sign-off on C-10 (NULL `organization_id`) before step 13, (5) human sign-off on C-09 (`X-API-Key`). See §11. |
| Merge-order position (contract §6, verbatim) | `\| **2** \| AUD \| — \|` (Wave 2). Contract C-09: "RBAC first, then ENR, then AUD". |
| Authority | Subordinate to `ARCHITECTURE.md`, `db/schema.sql`, `AGENT_RULES.md`; `SYSTEM_INTERFACE_CONTRACT.md` is a hard constraint. |

**Changelog**

| Version | Change |
|---|---|
| v1.0-draft | First full spec. Deviations from the Step 1 proposal (`docs/proposals/audit-logging.md`), all made to follow the contract: |
| | 1. Migration `db/migrations/002_audit_events.sql` becomes `db/migrations/006_audit_events.sql` (contract §2.1); compose mount prefix `07_`, not the proposal's "mount migration 002". |
| | 2. Immutability by Postgres triggers becomes `CREATE RULE ... DO INSTEAD NOTHING`, as in contract §2.2 (with one idempotency fix, see §11 item 8). |
| | 3. The proposal's unspecified columns become the contract's exact `audit_events` schema (`BIGSERIAL`, `actor_type`, `actor_ref`, and so on). |
| | 4. The proposal's `api/main.py` note "stop relying on the log-only middleware" is dropped. The middleware is left unchanged; `main.py` only gains a router registration and one exception handler. |
| | 5. The proposal said the endpoint serves "auditors". The contract assigns no role to it; see §11 item 7. |
| | 6. The proposal's open questions (fail-closed, retention, external sink) are now cited as contract C-22 items and remain **unresolved**. The spec does not resolve them. |
| | 7. The proposal named `deploy/nginx/nginx.conf` as an input only. The contract says "AUD needs `X-Forwarded-For`"; the header is already set, so no edit is planned. |

**Reviewer sign-off**

| Role | Name | Decision | Date |
|---|---|---|---|
| DB lane | Ronak | ☐ | |
| Backend lane | Shreyanshi | ☐ | |
| Deploy lane | (unnamed in contract) | ☐ | |
| Product / C-22 sign-off (a)(b)(c) | (human) | ☐ | |
| C-10 and C-09 sign-off | (human) | ☐ | |

---

### Step 5 integration-audit corrections (v1.1)

| # | Was | Now | Why |
|---|---|---|---|
| 1 | `require_role(SECURITY_ADMIN)` with `# import path PENDING RBAC` | `require_role(Role.AUDITOR, Role.SECURITY_ADMIN)`, imported from `api/core/rbac.py` | RBAC now publishes a `Role` str-Enum and a matrix entry `("audit", "read"): (Role.AUDITOR, Role.SECURITY_ADMIN)`. A bare `SECURITY_ADMIN` name would not resolve, and restricting audit reads to admins would contradict RBAC |
| 2 | `principal: Annotated[Any, ...]` | `principal: Annotated[Principal, ...]` | `Principal` is now a published, importable symbol |
| 3 | §11 item 7 open | marked RESOLVED, with the wave-ordering fallback retained | The gap it described is closed |

*Confirmed correct and left unchanged:* migration `006_audit_events.sql` at compose prefix `07_`, `actor_from_principal` reading `.username` (matches the corrected RBAC `Principal`, which moved from `email` to `username`), and this spec's §11 item 8 — the contract's `CREATE RULE` is genuinely not idempotent and `CREATE OR REPLACE RULE` is the right call. That item is a defect in `SYSTEM_INTERFACE_CONTRACT.md` §2.2, not in this spec.

---

# 2. Goal & Context

ECDAT's pitch rests on the claim that "We treat our findings data with the same rigor we're asking enterprises to apply to their own cryptography" (`PRODUCT_DESCRIPTION.md` §7, *On Self-Hosting*), and on the DPDP §8(a) "reasonable security safeguards" angle (§10). Today the only trace of who read a scan, exported a CBOM or submitted a report is a stdout line from the `ecdat.audit` logger in `api/main.py`, lost on container restart. `docs/SECURE_DEPLOYMENT.md` already lists "durable audit-event storage" as a prerequisite before public dashboard launch. This feature adds a durable, append-only `audit_events` table with a hash chain, written from the scan, CBOM, remediation and report-ingest routes and from authentication failures. Audit logging is not one of the five PS 26164 requirements (Discovery, Identification, Cataloguing, Quantum-risk scoring, Recommendation & reporting); it supports the self-hosted trust and compliance judging criteria. The hash chain is **tamper-evident, not tamper-proof**: a database superuser can rewrite the whole chain. Nothing in the pitch may say otherwise.

---

# 3. Scope

**In scope**
- New table `audit_events` (contract §2.2, migration `006_audit_events.sql`, mirrored in `db/schema.sql` and `db/models.py`).
- Hash-chained append with a Postgres advisory lock (the first of the two options in contract C-22).
- `record_audit_event` and related helpers in `db/crud.py`; orchestration in `api/services/audit.py`.
- Event calls in `api/routers/scans.py`, `cbom.py`, `remediation.py`, `report_sync.py`, using only these contract §3.6 actions: `ecdat.scan.create`, `ecdat.scan.read`, `ecdat.cbom.export`, `ecdat.remediation.generate`, `ecdat.report.ingest`, `ecdat.auth.denied`.
- `ecdat.auth.denied` events for HTTP 401/403 raised in `api/core/security.py`.
- Read endpoints `GET /audit/events` (contract §5.3) and `GET /audit/events/verify` (see §11 item 9).
- Config `AUDIT_FAIL_CLOSED` (the value and semantics are gated on C-22(a)).
- `tests/test_audit.py`, `docs/SECURE_DEPLOYMENT.md` update.

**Out of scope**
- Emitting `ecdat.auth.login`, `ecdat.agent.enroll`, `ecdat.agent.revoke`, `ecdat.triage.update`. These names are reserved by contract §3.6; the owning features (RBAC, ENR, TRI) call `write_audit_event` from their SOLE files. AUD does not edit those files.
- `ecdat.auth.denied` from `require_role` (it lives in RBAC's SOLE `api/core/rbac.py`).
- Retention or purge (C-22(b) unresolved). No `AUDIT_RETENTION_DAYS` variable is introduced.
- External write-once sink or log shipping (C-22(c) unresolved).
- Any dashboard UI (the contract lists no AUD frontend file).
- Editing `api/routers/findings.py` (AUD is not a listed editor) or `deploy/nginx/nginx.conf`.
- Auditing reads of the audit log itself (no such action name exists in §3.6).
- Any scanner change. No source-code detection is added, so `AGENT_RULES.md` #5 and #6 are not implicated; the sanitizer uses no regex regardless.

---

# 4. Required Context Files

Read in full before writing anything (`AGENT_RULES.md` #1). Every path below exists in the attached repository, except the two marked.

1. `SYSTEM_INTERFACE_CONTRACT.md` (attached; its location inside the repo is not confirmed)
2. `AGENT_RULES.md`
3. `ARCHITECTURE.md`
4. `PRODUCT_DESCRIPTION.md`
5. `docs/proposals/audit-logging.md` (Step 1 proposal)
6. `docs/SECURE_DEPLOYMENT.md`
7. `db/schema.sql`
8. `db/models.py`
9. `db/crud.py`
10. `db/migrations/001_secure_reporting.sql`
11. `api/database.py`
12. `api/core/config.py`
13. `api/core/security.py`
14. `api/main.py`
15. `api/models.py`
16. `api/routers/scans.py`
17. `api/routers/cbom.py`
18. `api/routers/remediation.py`
19. `api/routers/report_sync.py`
20. `api/services/report_bundle.py`
21. `docker-compose.yml`
22. `.env.example`
23. `deploy/nginx/nginx.conf`
24. `Dockerfile`
25. `requirements.txt`
26. `conftest.py`
27. `tests/test_security_controls.py`
28. `tests/test_secure_report_sync.py`
29. `tests/test_crud.py`
30. `api/core/rbac.py`: **created by RBAC (contract §1.2, SOLE); does not exist in the attached repo.** Read after RBAC merges.
31. `api/routers/auth.py`: same status as 30.

---

# 5. File Ownership

**Tier: SOLE (AUD creates). Contract §1.2 and §1.3: "`api/routers/audit.py`, `api/services/audit.py` | SOLE | AUD | new"; "`db/migrations/002–008_*.sql` | SOLE per file | allocated in §2.1".**

| Path | Action |
|---|---|
| `api/routers/audit.py` | create |
| `api/services/audit.py` | create |
| `db/migrations/006_audit_events.sql` | create |
| `tests/test_audit.py` | create (new file; the contract's ownership map lists no new test files, so this is a gap, see §11 item 16) |

**Tier: COORDINATED (AUD edits through the named integration owner, in §6 merge order).**

| Path | Integration owner | AUD's edit |
|---|---|---|
| `db/schema.sql`, `db/models.py`, `db/crud.py` | DB lane (Ronak) | add `audit_events`, `AuditEvent`, audit helpers |
| `api/models.py` | backend lane (Shreyanshi) | add three Pydantic models |
| `api/routers/scans.py`, `cbom.py`, `remediation.py`, `report_sync.py` | backend lane | "AUD adds event calls" |
| `api/core/security.py`, `api/core/config.py`, `api/main.py` | backend lane; order RBAC, ENR, AUD | denied-event calls, `AUDIT_FAIL_CLOSED`, router and handler |
| `docker-compose.yml` | deploy lane | one initdb mount |
| `.env.example` | deploy lane | one variable |
| `docs/SECURE_DEPLOYMENT.md` | contract §5.1 lists INS ENR AUD, "Compatible" | audit section |

**Verify only, do not edit:** `deploy/nginx/nginx.conf` (contract §1.5: "AUD needs `X-Forwarded-For`"). It already sets `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` at lines 36 and 80. `requirements.txt`: no change.

**DO NOT TOUCH. FROZEN:** `scanner/finding.py`, `api/services/scan_runner.py`, `api/services/risk_engine.py`.

**DO NOT TOUCH. Other features' SOLE files:** `api/routers/auth.py`, `api/core/rbac.py` (RBAC); `api/routers/agents.py`, `api/services/enrollment.py`, `scanner/enroll_cli.py` (ENR); `api/routers/triage.py` (TRI); `api/routers/trends.py` (TRD); `api/routers/compliance.py` (CMP); `api/services/cbom_validator.py` (CBV); `scanner/confidence.py` (CONF); `scanner/dependency_engine.py`, `scanner/container_engine.py`, `scanner/image_layers.py`, `scanner/binary_engine.py`, `scanner/config_engine.py` and their `scanner/rules/*.yaml`; `scanner/ecdat_cli.py`, `pyproject.toml` (CLI); `scripts/install.sh`, `scripts/install.ps1`, `.github/workflows/install-smoke.yml` (INS); everything under `dashboard/` that is listed SOLE; migrations `002`, `003`, `004`, `005`, `007`, `008`.

**DO NOT TOUCH. Other COORDINATED files AUD is not a listed editor of:** `api/routers/findings.py`, `api/services/cbom_generator.py`, `scanner/cli.py`, `scanner/constants.py`, `PRODUCT_DESCRIPTION.md` (C-19), `requirements.txt`.

---

# 6. Tech Stack & Pinned Versions

**No new dependency. `requirements.txt` is not modified.** The repo pins by range, not exact version; those ranges are quoted and left as they are.

| Component | Constraint in repo | Source |
|---|---|---|
| Python | 3.11 (`FROM python:3.11-slim`) | `Dockerfile` |
| PostgreSQL | `postgres:16-alpine` | `docker-compose.yml` |
| SQLAlchemy | `SQLAlchemy>=2.0,<2.1` | `requirements.txt` |
| psycopg2 | `psycopg2-binary>=2.9` | `requirements.txt` |
| FastAPI | `fastapi>=0.111.0` | `requirements.txt` |
| Pydantic | `pydantic>=2.7.0`, `pydantic-settings>=2.3.0` | `requirements.txt` |
| pytest | `pytest>=8.0` | `requirements.txt` |
| Standard library | `hashlib`, `json`, `datetime`, `dataclasses`, `logging` | n/a |

`cryptography` is unpinned (contract C-18); that is a Wave 0 item for the backend lane and is not fixed here. Baseline measured on the unmodified attached repo: `python -m pytest -q` gives `64 passed`.

---

# 7. Concrete Interface Definitions

```sql
-- db/migrations/006_audit_events.sql  (AND the identical statements appended to db/schema.sql)
-- 006_audit_events.sql  ·  owner: AUD
-- Append-only. detail MUST NOT contain source code, file paths, or secrets.
CREATE TABLE IF NOT EXISTS audit_events (
    id              BIGSERIAL PRIMARY KEY,
    occurred_at     TIMESTAMP NOT NULL DEFAULT now(),
    actor_type      TEXT NOT NULL,      -- user | agent | api_key | anonymous
    actor_ref       TEXT,               -- username | agent_id | key-fingerprint prefix. NEVER the key.
    organization_id TEXT,
    action          TEXT NOT NULL,      -- dotted verb, see §3.6
    object_type     TEXT,               -- scan | finding | cbom | report | agent | user
    object_id       TEXT,
    outcome         TEXT NOT NULL,      -- allowed | denied | error
    client_ip       TEXT,               -- from X-Forwarded-For; trustworthy only behind the gateway
    detail          JSONB,
    prev_hash       TEXT,               -- entry_hash of the preceding row
    entry_hash      TEXT NOT NULL       -- SHA-256 over canonical JSON of this row + prev_hash
);
CREATE INDEX IF NOT EXISTS idx_audit_events_org_time ON audit_events(organization_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_action   ON audit_events(action, occurred_at DESC);

-- DEVIATION (see §11 item 8): contract text is `CREATE RULE`, which errors on re-run.
CREATE OR REPLACE RULE audit_events_no_update AS ON UPDATE TO audit_events DO INSTEAD NOTHING;
CREATE OR REPLACE RULE audit_events_no_delete AS ON DELETE TO audit_events DO INSTEAD NOTHING;
```

```yaml
# docker-compose.yml, services.db.volumes, appended after the existing 02_secure_reporting.sql mount
      - ./db/migrations/006_audit_events.sql:/docker-entrypoint-initdb.d/07_audit_events.sql:ro
```

```bash
# .env.example
# PENDING C-22(a) sign-off. Value below is the contract's recommendation, not a decision.
AUDIT_FAIL_CLOSED=true
```

```python
# api/core/config.py  (inside class Settings)
AUDIT_FAIL_CLOSED: bool = True  # PENDING C-22(a) sign-off
```

```python
# db/models.py  (new imports: BigInteger, JSON from sqlalchemy; JSONB from sqlalchemy.dialects.postgresql)
ACTOR_TYPES = ("user", "agent", "api_key", "anonymous")
AUDIT_OUTCOMES = ("allowed", "denied", "error")
AUDIT_OBJECT_TYPES = ("scan", "finding", "cbom", "report", "agent", "user")
AUDIT_ACTIONS = (
    "ecdat.scan.create", "ecdat.scan.read", "ecdat.cbom.export",
    "ecdat.remediation.generate", "ecdat.report.ingest", "ecdat.agent.enroll",
    "ecdat.agent.revoke", "ecdat.auth.login", "ecdat.auth.denied", "ecdat.triage.update",
)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(Text)
    organization_id: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    object_type: Mapped[str | None] = mapped_column(Text)
    object_id: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    client_ip: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    prev_hash: Mapped[str | None] = mapped_column(Text)
    entry_hash: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_audit_events_org_time", "organization_id", "occurred_at"),
        Index("idx_audit_events_action", "action", "occurred_at"),
    )
```

```python
# db/crud.py
def get_audit_chain_tail(session: Session, *, for_append: bool) -> str | None: ...
    # for_append=True on PostgreSQL executes: SELECT pg_advisory_xact_lock(1096107057)
    # then returns entry_hash of the row with the greatest id, or None if the table is empty.
    # No-op lock on SQLite.

def record_audit_event(
    session: Session, *,
    occurred_at: dt.datetime, actor_type: str, actor_ref: str | None,
    organization_id: str | None, action: str, object_type: str | None,
    object_id: str | None, outcome: str, client_ip: str | None,
    detail: dict[str, Any] | None, prev_hash: str | None, entry_hash: str,
) -> AuditEvent: ...

def list_audit_events(
    session: Session, *,
    organization_id: str | None,          # None semantics PENDING C-10; must use the shared org-filter helper in this module (name assigned by RBAC, not in contract)
    action: str | None = None, outcome: str | None = None, actor_ref: str | None = None,
    since: dt.datetime | None = None, until: dt.datetime | None = None,
    after_id: int | None = None, ascending: bool = False,
    limit: int = 50, offset: int = 0,
) -> list[AuditEvent]: ...

def count_audit_events(
    session: Session, *,
    organization_id: str | None, action: str | None = None, outcome: str | None = None,
    actor_ref: str | None = None, since: dt.datetime | None = None,
    until: dt.datetime | None = None,
) -> int: ...
```

```python
# api/models.py
class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: dt.datetime
    actor_type: str
    actor_ref: str | None = None
    organization_id: str | None = None
    action: str
    object_type: str | None = None
    object_id: str | None = None
    outcome: str
    client_ip: str | None = None
    detail: dict[str, Any] | None = None
    prev_hash: str | None = None
    entry_hash: str


class AuditEventListResponse(BaseModel):
    events: list[AuditEventOut]
    total: int
    limit: int
    offset: int


class AuditChainVerification(BaseModel):
    ok: bool
    checked: int
    first_bad_id: int | None = None
    reason: str | None = None
```

```python
# api/services/audit.py
AUDIT_CHAIN_LOCK_KEY: int = 1096107057  # int.from_bytes(b"AUD1", "big")
AUDIT_DETAIL_ALLOWED_KEYS: frozenset[str] = frozenset({
    "status_code", "reason", "route", "method", "download", "provider",
    "bundle_digest", "finding_count", "accepted",
})
AUDIT_DETAIL_PATH_EXEMPT_KEYS: frozenset[str] = frozenset({"route"})
AUDIT_DETAIL_MAX_STR_LEN: int = 128


class AuditWriteError(RuntimeError): ...


@dataclass(frozen=True)
class AuditActor:
    actor_type: str
    actor_ref: str | None
    organization_id: str | None


ANONYMOUS_ACTOR: AuditActor = AuditActor("anonymous", None, None)


@dataclass(frozen=True)
class AuditChainResult:
    ok: bool
    checked: int
    first_bad_id: int | None
    reason: str | None


def actor_from_api_key(api_key: str) -> AuditActor: ...        # ("api_key", sha256(key).hexdigest()[:12], None)
def actor_from_principal(principal: Any) -> AuditActor: ...    # reads .username, .role, .organization_id; ("user", username, organization_id)
def actor_from_agent(agent_id: str, organization_id: str | None = None) -> AuditActor: ...
def actor_from_auth(auth: Any) -> AuditActor: ...              # str -> actor_from_api_key; object with .username -> actor_from_principal; else ANONYMOUS_ACTOR
def client_ip_from_request(request: Request) -> str | None: ...  # rightmost X-Forwarded-For element; never request.client.host
def sanitize_audit_detail(detail: dict[str, Any] | None) -> dict[str, str | int | bool | None] | None: ...  # raises ValueError
def canonical_json(value: Any) -> str: ...                     # json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
def compute_audit_entry_hash(
    *, occurred_at: dt.datetime, actor_type: str, actor_ref: str | None,
    organization_id: str | None, action: str, object_type: str | None,
    object_id: str | None, outcome: str, client_ip: str | None,
    detail: dict[str, Any] | None, prev_hash: str | None,
) -> str: ...                                                   # sha256(canonical_json({...11 keys, occurred_at.isoformat(timespec="microseconds")})).hexdigest()
def audit_write_must_succeed(*, is_mutation: bool) -> bool: ... # PENDING C-22(a): body returns settings.AUDIT_FAIL_CLOSED and is_mutation
def write_audit_event(
    session: Session | None, *,
    action: str, outcome: str, actor: AuditActor,
    object_type: str | None = None, object_id: str | None = None,
    request: Request | None = None,
    detail: dict[str, Any] | None = None,
    is_mutation: bool,
) -> AuditEvent | None: ...                                     # commits its own transaction; session=None opens a standalone session
def verify_audit_chain(session: Session, *, batch_size: int = 1000) -> AuditChainResult: ...
def _open_audit_session() -> Session: ...                       # get_sessionmaker()(); init_db(engine) once when dialect is sqlite
```

```python
# api/routers/audit.py
router = APIRouter(prefix="/audit", tags=["audit"])

# from api.core.rbac import Principal, Role, require_role

@router.get("/events", response_model=AuditEventListResponse)
def list_events(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_role(Role.AUDITOR, Role.SECURITY_ADMIN))],
    action: str | None = Query(None),
    outcome: str | None = Query(None),
    actor_ref: str | None = Query(None),
    since: dt.datetime | None = Query(None),
    until: dt.datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AuditEventListResponse: ...

@router.get("/events/verify", response_model=AuditChainVerification)
def verify_events(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_role(Role.AUDITOR, Role.SECURITY_ADMIN))],
) -> AuditChainVerification: ...
```

```python
# api/main.py additions
from api.routers import audit
from api.services.audit import AuditWriteError

@app.exception_handler(AuditWriteError)
async def audit_write_error_handler(request: Request, exc: AuditWriteError) -> JSONResponse: ...
    # returns JSONResponse(status_code=503, content={"detail": "Audit log unavailable"})

app.include_router(audit.router)
```

```python
# Signature deltas only: add `request: Request` (from fastapi import Request) to each existing route; nothing else in the signature changes.
# api/routers/scans.py
def create_scan(body: ScanCreateRequest, background_tasks: BackgroundTasks, request: Request, db: ..., _key: ...) -> ScanCreateResponse: ...
def list_scans(request: Request, db: ..., _key: ..., repo_id: ..., limit: ...) -> ScanListResponse: ...
def get_scan(scan_id: int, request: Request, db: ..., _key: ..., risk_tier: ..., limit: ..., offset: ...) -> Any: ...
# api/routers/cbom.py
def get_cbom(scan_id: int, request: Request, db: ..., _key: ..., download: bool = ...) -> Response: ...
# api/routers/remediation.py
async def get_remediation_for_finding(scan_id: int, finding_id: int, request: Request, provider: ..., model: ..., db: ..., _key: ...): ...
async def generate_remediation_direct(req: RemediationRequest, request: Request, _key: str = ...): ...
# api/routers/report_sync.py
def ingest_report_bundle(bundle: dict[str, Any], request: Request, agent: ..., db: ...) -> ReportIngestResponse: ...

# Call shapes (identical in every router; the action/object_type/object_id/detail/is_mutation values are fixed by the table below)
write_audit_event(db, action=..., outcome=..., actor=actor_from_auth(_key),
                  object_type=..., object_id=..., request=request, detail={...}, is_mutation=...)
```

```text
# Event matrix (route, action, object_type, object_id, outcome rules, detail keys, is_mutation)
POST /scans                              ecdat.scan.create          scan   str(scan_id)|None   allowed(202) denied(403 local API off) error(422)   status_code, reason      True
GET  /scans                              ecdat.scan.read            None   None                allowed                                              status_code              False
GET  /scans/{scan_id}                    ecdat.scan.read            scan   str(scan_id)        allowed  error(404)                                  status_code              False
GET  /scans/{scan_id}/cbom               ecdat.cbom.export          cbom   str(scan_id)        allowed  error(404, 400)                             status_code, download    True
GET  /scans/{scan_id}/remediation/{fid}  ecdat.remediation.generate finding str(fid)           allowed  error(404)                                  status_code, provider    False
POST /scans/remediation/generate         ecdat.remediation.generate None    None                allowed                                              status_code, provider    False
POST /agent/v1/report-bundles            ecdat.report.ingest        report str(report_id)|None allowed(201) denied(422 verify fail, 403 agent mismatch) bundle_digest, finding_count, accepted, status_code  True
security.py 401/403                      ecdat.auth.denied          None   None                denied                                               status_code, reason, route, method   False
```

```jsonc
// GET /audit/events?limit=2  -> 200
{
  "events": [
    {
      "id": 42,
      "occurred_at": "2026-09-21T10:16:02.000001",
      "actor_type": "user",
      "actor_ref": "alice",
      "organization_id": "org-example",
      "action": "ecdat.scan.read",
      "object_type": "scan",
      "object_id": "17",
      "outcome": "allowed",
      "client_ip": "203.0.113.7",
      "detail": {"status_code": 200},
      "prev_hash": "fc85dfba61415035a847533654322b3f0e467a32f263816bcf93ed0fb69ee2f8",
      "entry_hash": "673a1e688934843d60a0c3482fbbb45cd58ffa77877e7934ee087d409ab4c898"
    },
    {
      "id": 41,
      "occurred_at": "2026-09-21T10:15:30.123456",
      "actor_type": "user",
      "actor_ref": "alice",
      "organization_id": "org-example",
      "action": "ecdat.cbom.export",
      "object_type": "cbom",
      "object_id": "17",
      "outcome": "allowed",
      "client_ip": "203.0.113.7",
      "detail": {"download": true, "status_code": 200},
      "prev_hash": null,
      "entry_hash": "fc85dfba61415035a847533654322b3f0e467a32f263816bcf93ed0fb69ee2f8"
    }
  ],
  "total": 2,
  "limit": 2,
  "offset": 0
}
```

```jsonc
// GET /audit/events/verify -> 200 (intact)
{"ok": true, "checked": 2, "first_bad_id": null, "reason": null}
// GET /audit/events/verify -> 200 (tampered)
{"ok": false, "checked": 1, "first_bad_id": 42, "reason": "entry_hash mismatch"}
// any fail-closed audit write failure -> 503
{"detail": "Audit log unavailable"}
// actor_type=api_key row, before RBAC (fingerprint of the key "ci-test-key")
{"actor_type": "api_key", "actor_ref": "3c1926cc058b", "organization_id": null}
```

```text
# Test vector 1: canonical JSON (prev_hash null)
{"action":"ecdat.cbom.export","actor_ref":"alice","actor_type":"user","client_ip":"203.0.113.7","detail":{"download":true,"status_code":200},"object_id":"17","object_type":"cbom","occurred_at":"2026-09-21T10:15:30.123456","organization_id":"org-example","outcome":"allowed","prev_hash":null}
# SHA-256
fc85dfba61415035a847533654322b3f0e467a32f263816bcf93ed0fb69ee2f8
# Test vector 2: same actor/org/ip; action=ecdat.scan.read, object_type=scan, object_id="17", occurred_at=2026-09-21T10:16:02.000001, detail={"status_code":200}, prev_hash=<vector 1 hash>
673a1e688934843d60a0c3482fbbb45cd58ffa77877e7934ee087d409ab4c898
```

---

# 8. Step-by-Step Implementation Plan

**Preconditions (not steps). Do not begin until each is recorded in §1's changelog:** RBAC merged and its `Principal` contract published; ENR merged; C-22 (a)(b)(c) answered; C-09 answered; C-10 answered (needed only for step 13). If any is missing, stop and ask a human (`AGENT_RULES.md` #4). Then rebase §7's `security.py` and route snippets onto the post-RBAC and post-ENR files.

1. **`db/migrations/006_audit_events.sql`**: create with the SQL block in §7.
2. **`db/schema.sql`**: append the identical statements (same table, indexes, rules) after the `reports` block. Effect must equal step 1 (contract §2: "Missing either half is the defect this project has already been bitten by").
3. **`db/models.py`**: add the four value tuples and `AuditEvent` exactly as in §7.
4. **`db/crud.py`**: add `get_audit_chain_tail`, `record_audit_event`, `list_audit_events`, `count_audit_events`. Wire `list_audit_events` and `count_audit_events` to the shared org-filter helper RBAC added; do not write a new `WHERE organization_id` in a router.
5. **`api/core/config.py`**: add `AUDIT_FAIL_CLOSED` to `Settings`.
6. **`api/models.py`**: add `AuditEventOut`, `AuditEventListResponse`, `AuditChainVerification` (add `Any` to the typing import).
7. **`api/services/audit.py`**: create every symbol in §7. `write_audit_event` runs `sanitize_audit_detail`, opens `_open_audit_session()` when `session` is `None`, calls `get_audit_chain_tail(for_append=True)`, computes the hash with `occurred_at = datetime.now(timezone.utc).replace(tzinfo=None)`, calls `record_audit_event`, then `session.commit()` immediately so the advisory lock is held only for the insert. On a database error it consults `audit_write_must_succeed`: raise `AuditWriteError`, or log via `logging.getLogger("ecdat.audit")` and return `None`.
8. **`api/core/security.py`**: on the 401 and 403 branches of `get_api_key` and on the 401 branches of `get_report_sync_agent`, call `write_audit_event(None, action="ecdat.auth.denied", outcome="denied", ...)` before raising. Do not audit the 503 "not configured" branch. Add `request: Request` to `get_api_key`.
9. **`api/routers/scans.py`**: add the `request` parameter and event calls per the §7 matrix, on both success and error branches, before each `raise HTTPException`.
10. **`api/routers/cbom.py`**: same, per the matrix.
11. **`api/routers/remediation.py`**: same, per the matrix; `generate_remediation_direct` passes `session=None`.
12. **`api/routers/report_sync.py`**: same; on success use `actor_from_agent(agent_id, verified["organization_id"])`; on the 422 and 403 branches use `actor_from_agent(agent_id)`.
13. **`api/routers/audit.py`**: create both endpoints. **Gated on C-10 sign-off.**
14. **`api/main.py`**: register `audit.router` and the `AuditWriteError` handler. Leave the existing middleware and logger unchanged.
15. **`docker-compose.yml`**: add the `07_audit_events.sql` mount line.
16. **`.env.example`**: add `AUDIT_FAIL_CLOSED`.
17. **`docs/SECURE_DEPLOYMENT.md`**: add the audit section: the manual migration command for existing volumes, the tamper-evident (not tamper-proof) statement, and `AUDIT_FAIL_CLOSED`.
18. **`tests/test_audit.py`**: implement the 16 tests named in §12.

---

# 9. Naming & Symbol Registry

Conventions checked against contract §3.1 (snake_case functions, PascalCase classes, `get_*/list_*/count_*/record_*` CRUD verbs), §3.3 (`AUDIT_` prefix), §3.4 (plural noun routes), §3.6 (action names), §3.8 (DB). Collision check: searched the attached repo and contract §5 indexes; the only pre-existing "audit" identifier is the `ecdat.audit` logger name in `api/main.py`, which the service reuses on purpose.

| Symbol | Kind | File | Convention / collision result |
|---|---|---|---|
| `audit_events` | table | `db/schema.sql`, `006` | contract §2.2 verbatim; no collision |
| `id, occurred_at, actor_type, actor_ref, organization_id, action, object_type, object_id, outcome, client_ip, detail, prev_hash, entry_hash` | columns | same | contract §2.2 verbatim |
| `idx_audit_events_org_time`, `idx_audit_events_action` | indexes | same | `idx_<table>_<cols>`; contract names |
| `audit_events_no_update`, `audit_events_no_delete` | rules | same | contract names |
| `AUDIT_FAIL_CLOSED` | env var | `config.py`, `.env.example` | `AUDIT_` prefix (§3.3); not in frozen list |
| `AuditEvent` | ORM class | `db/models.py` | PascalCase |
| `ACTOR_TYPES`, `AUDIT_OUTCOMES`, `AUDIT_OBJECT_TYPES`, `AUDIT_ACTIONS` | tuples | `db/models.py` | matches `CONFIDENCES` pattern (§3.8) |
| `get_audit_chain_tail`, `record_audit_event`, `list_audit_events`, `count_audit_events` | CRUD | `db/crud.py` | allowed verbs; no existing name |
| `AuditEventOut`, `AuditEventListResponse`, `AuditChainVerification` | Pydantic | `api/models.py` | no `api/schemas/` package (§0.1) |
| `AuditActor`, `AuditChainResult`, `AuditWriteError` | classes | `api/services/audit.py` | PascalCase |
| `ANONYMOUS_ACTOR`, `AUDIT_CHAIN_LOCK_KEY`, `AUDIT_DETAIL_ALLOWED_KEYS`, `AUDIT_DETAIL_PATH_EXEMPT_KEYS`, `AUDIT_DETAIL_MAX_STR_LEN` | constants | same | UPPER_SNAKE; no advisory lock used elsewhere in repo |
| `actor_from_api_key`, `actor_from_principal`, `actor_from_agent`, `actor_from_auth`, `client_ip_from_request`, `sanitize_audit_detail`, `canonical_json`, `compute_audit_entry_hash`, `audit_write_must_succeed`, `write_audit_event`, `verify_audit_chain`, `_open_audit_session` | functions | same | snake_case; module path disambiguates (§3.1) |
| `router` (`/audit`), `list_events`, `verify_events` | router | `api/routers/audit.py` | plural noun route (§3.4); `GET /audit/events` per §5.3; `/audit/events/verify` see §11 item 9 |
| `audit_write_error_handler` | handler | `api/main.py` | no collision |
| `test_*` (16) | tests | `tests/test_audit.py` | no collision |
| CLI flags | none | n/a | none introduced |

Action names used are only those of contract §3.6, verbatim, and only the six listed in §3.

---

# 10. Known Cross-Feature Risks

Pulled from contract §4 and §5. Each states the resolution the contract already decided.

- **C-09, authentication rewrite (shared: `api/core/security.py`, `api/main.py`, `api/core/config.py`).** Decided: "RBAC merges first and publishes the `Principal` contract (`username`, `role`, `organization_id`) before the others start. AUD records `actor_type='api_key'` with a key-fingerprint prefix before RBAC lands and `actor_type='user'` after." Agent report-sync (mTLS + Ed25519) is untouched by RBAC. Edit order in shared files: RBAC, ENR, AUD. Handled by `actor_from_auth` and the step 8 rebase precondition.
- **C-22, hash chain under concurrent writes.** Decided: "Serialise appends through a Postgres advisory lock held only for the insert, or derive the chain from `id` ordering with a periodic verification job rather than at write time." This spec uses the first option. The sign-off questions (a) fail-closed vs open, (b) retention, (c) external sink remain open (§11).
- **C-10, `organization_id` scoping.** Decided: "A single shared filter helper in `db/crud.py` applies it; no router writes its own `WHERE organization_id = …`." NULL-org visibility remains open.
- **C-01, migration numbering.** Decided: `006_audit_events.sql`, mount prefix `07_`; the same change must land in `db/schema.sql` in the same PR.
- **Shared Resource Index rows naming AUD:**
  - `api/routers/scans.py` (CNT RBAC AUD): CNT changes `ScanCreateRequest` later (Wave 3); AUD merges first, CNT rebases.
  - `api/routers/cbom.py` (CBV RBAC AUD): compatible.
  - `api/models.py` (7 features): additive models only.
  - `db/crud.py` (8 features): additive functions only.
  - `docker-compose.yml`: additive mount only.
  - `deploy/nginx/nginx.conf` (ENR AUD INS): compatible; no AUD edit.
  - `.env.example`, `docs/SECURE_DEPLOYMENT.md`: compatible.
  - `audit_events` (RBAC ENR AUD): compatible, flagged `!` for C-22.
  - `reports` (ENR ASP AUD): compatible; AUD only reads `report_id` and `bundle_digest` values already in hand.
  - `users` (RBAC ENR AUD TRI): AUD stores `username` as text; no FK.
  - `organization_id` scoping: conflicting, flagged `!`.
  - `GET /scans/{scan_id}` (CMP RBAC AUD), `POST /scans` (CNT RBAC AUD), `GET /scans/{scan_id}/cbom` (CBV RBAC AUD): compatible.
  - `GET /audit/events`: sole.
  - `API_KEY` / `X-API-Key`: flagged `!` for C-09.
  - `AUDIT_*`: compatible.
- **§1.2 ownership note.** `api/services/scan_runner.py` is FROZEN for CONF. AUD does not audit scan execution inside it.

---

# 11. Pre-Answered Ambiguities

**Contract sign-off items touching AUD.** The contract's §7 states "Nothing below is decided", so **no team-resolved answer exists** for any of them. This spec does not supply one. Where behavior must be defined, it is parameterized and marked PENDING; the human's answer must be recorded in §1's changelog before implementation.

1. **C-22(a) fail-closed or fail-open.** The contract only says: "Recommended: fail-closed for mutations and exports, fail-open for reads." That is a recommendation, not a resolution. *If sign-off is missing, stop.* *If the answer matches the recommendation, leave `audit_write_must_succeed` as written in §7 (returns `settings.AUDIT_FAIL_CLOSED and is_mutation`). If it differs, change only that function body and the `AUDIT_FAIL_CLOSED` default.* Note: event calls sit after the domain `db.commit()`, so fail-closed returns 503 after the mutation has already committed. The 503 cannot undo it; the human must accept or redesign this as part of (a).
2. **C-22(b) retention.** Unresolved. The `audit_events_no_delete` rule makes deletion impossible, so *if anyone asks for purge or TTL, do not add `AUDIT_RETENTION_DAYS` and do not drop the rule; stop and ask.*
3. **C-22(c) external write-once sink.** Unresolved. *If asked to ship events elsewhere, do not add a sink; the hash chain is the only tamper mechanism in this spec.*
4. **C-09 does `X-API-Key` survive.** Unresolved. `actor_from_auth` supports both: *if the dependency yields a `str`, record `actor_type='api_key'`; if it yields an object with `.username`, record `actor_type='user'`.* Never store the key; store `sha256(key).hexdigest()[:12]`.
5. **C-10 NULL `organization_id`.** Unresolved, and the contract does not name the shared org-filter helper. *Do not implement step 13 until both are answered.* *If `Principal.organization_id` is `None` and no answer exists, do not return rows; stop and ask.*
6. **Chain mechanism.** The contract offers two options; this spec uses the advisory lock. *If the DB lane objects, do not silently switch to write-time-free chaining; raise it as a spec change.*

**Gaps the contract does not cover (stated, not resolved):**

7. **RBAC symbols — RESOLVED at Step 5.** `Principal`, `Role` and `require_role` are all exported from `api/core/rbac.py` (RBAC spec §7). `Role` is a `str`-Enum with members `SECURITY_ADMIN`, `AUDITOR`, `DEVELOPER`; there is no `ANALYST` or `Admin`. RBAC's permission matrix carries `("audit", "read"): (Role.AUDITOR, Role.SECURITY_ADMIN)`, so audit reads are Auditor **and** Security Admin — this spec's routes use `require_role(Role.AUDITOR, Role.SECURITY_ADMIN)` accordingly. *If an implementing agent finds `api/core/rbac.py` does not yet exist (AUD merges in wave 2, RBAC in wave 1), stop and wait — do not define a local `Role` or fall back to `get_api_key` permanently.*
8. **Contract SQL defect.** Contract §2.2 uses `CREATE RULE`, which fails on a second run ("rule already exists"); on a fresh volume `schema.sql` runs first and the `07_` migration then re-runs it, and the postgres entrypoint stops on error. This spec uses `CREATE OR REPLACE RULE`, which is equivalent in effect and idempotent (matching contract §2's own rule). *DB lane must confirm; if rejected, the rules go only in the migration and `schema.sql` loses lockstep, so escalate.*
9. **`GET /audit/events/verify`.** Contract §5.3 lists only `GET /audit/events`. The extra route lives inside AUD's SOLE router, so it cannot collide, but it is an addition. *If the reviewer rejects it, delete `verify_events` and keep `verify_audit_chain` as an internal function.*
10. **Events reserved for other features.** *If RBAC, ENR or TRI ask AUD to emit `ecdat.auth.login`, `ecdat.agent.enroll`, `ecdat.agent.revoke`, `ecdat.triage.update`, refuse and point them to `write_audit_event`; those files are their SOLE files.* The names must be usable in `AUDIT_ACTIONS` from day one.
11. **Client IP.** *If tempted to use `request.client.host`:* the Dockerfile starts uvicorn with `--proxy-headers --forwarded-allow-ips=*`, which lets a caller spoof it. `deploy/nginx/nginx.conf` uses `$proxy_add_x_forwarded_for`, which appends the real peer as the rightmost element. Use the rightmost `X-Forwarded-For` element; the value is trustworthy only behind the gateway, as the contract column comment says.
12. **Test database.** Tests run on SQLite (`conftest.py`), which has neither rules nor advisory locks. *`get_audit_chain_tail` must skip the lock on non-PostgreSQL dialects; rule and concurrency tests are PostgreSQL-only and skipped otherwise.*
13. **404 and 400 responses.** The contract's outcomes are `allowed | denied | error`. *If a route returns 404 or 400, record `outcome="error"` with `status_code` in `detail`; if it returns 401/403/422-from-verification, record `denied`.*
14. **Session choice.** Existing tests replace `get_session` with their own engine. *Where a route has a request session, pass it to `write_audit_event`; use `session=None` only in `security.py` and `generate_remediation_direct`.* Otherwise those tests would write to a different database.
15. **Reading the audit log.** No action name exists for it in §3.6. *Do not audit `GET /audit/events`; adding an action needs a contract edit.*
16. **New test file.** The contract's ownership map lists no new test files. *`tests/test_audit.py` is created on the assumption that a new file conflicts with nobody; flag it in the PR.*
17. **What goes in `detail`.** *If a value contains `/` or `\` (except key `route`, which holds a FastAPI route template), is longer than 128 characters, is a float or is not `str|int|bool|None`, `sanitize_audit_detail` raises `ValueError`.* Never put file paths, `repo_name`, `target_path`, findings text, keys or tokens in `detail`.

---

# 12. Test Plan / Definition of Done

Run from the repository root after all steps are done. Baseline on the unmodified repo: `64 passed`.

**Tests in `tests/test_audit.py` (16):**
1. `test_entry_hash_matches_published_vector`
2. `test_second_entry_hash_chains_prev_hash`
3. `test_actor_from_api_key_never_contains_key`
4. `test_sanitize_detail_rejects_unlisted_key`
5. `test_sanitize_detail_rejects_path_like_value`
6. `test_client_ip_uses_rightmost_forwarded_for`
7. `test_write_audit_event_links_chain`
8. `test_verify_audit_chain_detects_tampering`
9. `test_scan_create_disabled_records_denied_event`
10. `test_report_ingest_records_agent_event`
11. `test_invalid_api_key_records_auth_denied`
12. `test_fail_closed_mutation_returns_503`
13. `test_fail_open_read_still_returns_response`
14. `test_audit_events_endpoint_rejects_unauthenticated`
15. `test_postgres_rules_block_update_and_delete` (skipped unless `DATABASE_URL` starts with `postgresql`)
16. `test_postgres_concurrent_writes_do_not_fork_chain` (same skip condition)

**Commands and expected output**

```bash
python -m pytest tests/test_audit.py -v
# last line: ==== 14 passed, 2 skipped in <time> ====

python -m pytest tests/test_security_controls.py tests/test_secure_report_sync.py -q
# last line: 6 passed   (existing tests still green, unmodified)

python -m pytest -q
# last line: 78 passed, 2 skipped   (= baseline 64 + 14; adjust the baseline if RBAC/CONF changed existing tests first)

docker compose config -q
# no output, exit code 0

grep -n "07_audit_events.sql" docker-compose.yml
# one line: ./db/migrations/006_audit_events.sql:/docker-entrypoint-initdb.d/07_audit_events.sql:ro

git diff --stat -- requirements.txt
# no output

git diff --name-only origin/main...HEAD | sort
# must be a subset of:
# .env.example / api/core/config.py / api/core/security.py / api/main.py / api/models.py
# api/routers/audit.py / api/routers/cbom.py / api/routers/remediation.py / api/routers/report_sync.py / api/routers/scans.py
# api/services/audit.py / db/crud.py / db/migrations/006_audit_events.sql / db/models.py / db/schema.sql
# docker-compose.yml / docs/SECURE_DEPLOYMENT.md / tests/test_audit.py
```

**PostgreSQL verification** (fresh volume: `docker compose down -v && docker compose up -d db`):

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 < db/migrations/006_audit_events.sql
# expected (already applied by schema.sql, so every statement is a no-op or replace):
# NOTICE:  relation "audit_events" already exists, skipping
# CREATE TABLE
# NOTICE:  relation "idx_audit_events_org_time" already exists, skipping
# CREATE INDEX
# NOTICE:  relation "idx_audit_events_action" already exists, skipping
# CREATE INDEX
# CREATE RULE
# CREATE RULE

docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "INSERT INTO audit_events(actor_type,action,outcome,entry_hash) VALUES ('anonymous','ecdat.auth.denied','denied','x');" \
  -c "UPDATE audit_events SET outcome='allowed';" \
  -c "DELETE FROM audit_events;"
# expected: INSERT 0 1 / UPDATE 0 / DELETE 0
```

The spec-time claim "the SQL parses under the PostgreSQL grammar" was checked with `pglast`; execution against a live PostgreSQL 16 was **not** run while writing this spec, so the expected psql output above is unverified.

**Definition of Done:** every command above matches; step 13 either done with C-10 answered or explicitly deferred in the PR; §1 changelog records each sign-off; reviewers in §1 have ticked; no file outside §5 changed.

---

# 13. Rollback Plan

1. **Code:** `git revert` the AUD merge commit(s). Nothing else in the codebase imports the new modules, and every route change is additive.
2. **Verify:** `python -m pytest -q` returns to the pre-feature count (baseline `64 passed`, or the count on `main` before the merge); `docker compose config -q` exits 0.
3. **Database:** the migration is additive, so after a code revert the `audit_events` table is harmless and can stay. Do not drop it casually, because it is the only durable audit record. If it must go, export first, then drop (rules do not block `DROP TABLE`):
   ```bash
   docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\copy audit_events TO STDOUT CSV HEADER" > audit_events_backup.csv
   docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP TABLE IF EXISTS audit_events;"
   ```
4. **Fresh volumes:** reverting removes the `07_` mount and the `schema.sql` block together, so a new volume never creates the table.
5. **Live outage caused by fail-closed (audit DB writes failing, requests returning 503 `Audit log unavailable`):** without reverting code, set `AUDIT_FAIL_CLOSED=false` in `.env` and restart the backend. This is a stopgap that must be reported to the C-22(a) sign-off owner.
6. **Order if the build is red on `main`:** revert the AUD commits first; do not revert RBAC/ENR shared-file changes to fix an AUD failure.
