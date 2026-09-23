# Agent Enrollment (ENR) — Implementation Specification

## 1. Header

- **Feature name:** Agent Enrollment (`ENR`)
- **Owner:** ENR lane (per `SYSTEM_INTERFACE_CONTRACT.md` feature-code table)
- **Spec version:** 1.0
- **Changelog:**
  - v1.0 — Initial implementation-ready spec, derived from the Step 1 proposal
    (`agent-enrollment.md`) and reconciled against `SYSTEM_INTERFACE_CONTRACT.md`
    Draft v2. Deviations from the Step 1 proposal, forced by the contract:
    - Migration file is `db/migrations/005_agent_enrollment.sql` (not `002_*`,
      per contract §2.1 reservation table — five proposals collided on `002_`).
    - Admin endpoints (mint / list / revoke) use `require_role(SECURITY_ADMIN)`
      from `api/core/rbac.py` (RBAC), **not** an "interim `get_api_key`" as the
      proposal assumed — this is the resolved ordering in contract C-09.
    - `agents.status` and a derived `delivery_status` are kept as two separate
      API fields, never merged into one "agent status" badge — contract C-06.
      No `last_seen_at` heartbeat column is added (contract §2.3, rejected).
    - `GET /agents` lives in `api/routers/agents.py`, owned solely by ENR; ASP
      consumes it and does not create a second `agents.py` — contract C-05.
    - Certificate issuance stays manual and this feature records only the
      forwarded `$ssl_client_fingerprint`, matching the proposal's own
      assumption — unchanged, but the nginx location block and header name are
      specified concretely in §7 of this spec, since the proposal left them open.
- **Status:** Ready for implementation (blocked on RBAC merging first — see §11).
- **Reviewer sign-off:** ___________________________ (human reviewer, date)
  — required before merge per `AGENT_RULES.md` #2 and #4, and because this
  feature spans the DB, backend, deploy, and scanner lanes (per
  `agent-enrollment.md` §5, last bullet).

---

## 2. Goal & Context

PS 26164 requires ECDAT to be a deployable enterprise tool, and
`docs/SECURE_DEPLOYMENT.md`'s "Remaining production prerequisites" section
names "managed agent enrollment/revocation (rather than static environment
mapping)" as an explicit, unimplemented gap standing between the current
mTLS + Ed25519 report-sync design and a defensible production posture. Today,
`REPORT_SYNC_AGENT_KEYS` is a static JSON blob in an environment variable: a
compromised or decommissioned scanning agent's key cannot be revoked without an
operator editing `.env` and restarting the API, and there is no record of when
or by whom an agent was authorized. This feature replaces that static mapping
with a database-backed registry (`agents`, `enrollment_tokens`) fronted by an
admin-minted, single-use, expiring enrollment token, so an agent can be
enrolled and revoked as an operational action rather than a deployment. This
directly closes the named gap and gives judges a concrete, inspectable answer
to "how do you revoke a compromised scanner" — a question the current design
cannot answer without a restart.

---

## 3. Scope

**In-Scope**
- A `agents` / `enrollment_tokens` schema addition (migration `005`, per
  contract §2.1) and matching `db/schema.sql` edit.
- `POST /agent/v1/enroll` — machine route: an agent submits a valid enrollment
  token, its `agent_id`, and its locally generated Ed25519 public key; the
  server consumes the token and creates an `active` agent row.
- Admin endpoints on `api/routers/agents.py`: mint an enrollment token, list
  agents (status + derived delivery freshness), revoke an agent.
- `scanner/enroll_cli.py` — a separate CLI entrypoint that generates an
  Ed25519 keypair locally and calls `/agent/v1/enroll` over the existing mTLS
  agent vhost.
- Modifying `get_report_sync_agent` (`api/core/security.py`) to resolve an
  agent's public key from the `agents` table instead of
  `REPORT_SYNC_AGENT_KEYS`, and to reject `revoked` agents.
- Recording the nginx-forwarded client-certificate fingerprint on enrollment
  (fingerprint binding itself is out of scope — see §11).
- `deploy/nginx/nginx.conf`: adding the `/agent/v1/enroll` location to the
  existing `agent.ecdat.local` mTLS vhost and forwarding
  `$ssl_client_fingerprint`.
- `.env.example`, `docs/SECURE_DEPLOYMENT.md`, `docs/ECDAT_CLI_GUIDE.md`
  updates describing the new flow.
- Keeping `REPORT_SYNC_AGENT_KEYS` as a deprecated-in-place fallback, gated by
  `AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS` (contract §5.4: "Deprecated-in-place").

**Out-of-Scope**
- Issuing TLS client certificates. Certificate issuance stays manual per the
  existing README/`docs/SECURE_DEPLOYMENT.md`; ENR only *records* the
  fingerprint nginx forwards.
- Binding an enrolled `agent_id` to a specific certificate fingerprint at
  authentication time (today any client cert trusted by `agent-ca.crt` can
  present any enrolled `agent_id`, provided it also holds that agent's Ed25519
  private key to sign bundles) — flagged as an open question in the Step 1
  proposal and **not resolved** by the contract; see §11.
- Key rotation (multiple active keys per agent) — not addressed by the
  contract; see §11.
- Retroactively flagging reports already accepted from a since-revoked agent —
  not addressed by the contract; see §11.
- An `organizations` table. `agents.organization_id` stays free-text TEXT, per
  contract C-10 and the ground-truth correction table.
- A dashboard "agent status" view — that is `ASP`'s `AgentStatusTable.jsx` /
  `AgentStatusPage`, which *consumes* `GET /agents` but is a separate feature
  (contract C-05, §1.4).
- The `recent` vs `stale` delivery-status time threshold as a final, shipped
  product decision — contract C-06 marks this **Low confidence, needs human
  sign-off**; ENR implements the mechanism with a placeholder value (§11).
- Any change to the Ed25519 bundle-signature protocol itself
  (`api/services/report_bundle.py`). Contract C-26 records this as compatible:
  "ENR changes key *resolution*, not the protocol."
- RBAC's `Principal` contract, `users` table, or `require_role` mechanism
  itself — ENR only *consumes* them (contract C-09; `api/core/rbac.py`,
  `api/routers/auth.py` are RBAC's SOLE files).
- AUD's `audit_events` table and audit-logging calls — ENR emits the audit
  actions `ecdat.agent.enroll` / `ecdat.agent.revoke` (per contract §3.6) only
  once AUD's `api/services/audit.py` exists; until then this is a TODO (§11).

---

## 4. Required Context Files

Read these, in full, before writing any code:

- `AGENT_RULES.md` — binding on every feature; note especially #2 (file
  ownership), #3 (literal interfaces), #4 (stop on ambiguity), #5 (no regex —
  not directly relevant to ENR, which touches no source-scanning code, but
  governs the codebase generally).
- `SYSTEM_INTERFACE_CONTRACT.md` — full document. In particular: §1.2 (API
  lane ownership), §2.1–§2.3 (schema additions and rejections), §3.3 (env var
  prefixes), §3.4 (route naming), §3.6 (audit action names), C-05, C-06, C-09,
  C-10, C-26, and the `ENR` rows of §5.1–§5.4.
- `ARCHITECTURE.md` — for the documented deterministic/report-sync design ENR
  is extending.
- `docs/SECURE_DEPLOYMENT.md` — the document that names the exact gap this
  feature closes; also documents the existing migration-mount convention ENR
  must follow.
- `db/schema.sql` — the current canonical schema ENR adds tables to.
- `db/models.py` — existing ORM conventions (`CONFIDENCES`-style value tuples,
  `Mapped[...]` typing, `__tablename__` pattern) that new `Agent` /
  `EnrollmentToken` models must match.
- `db/crud.py` — existing CRUD naming (`get_*`, `list_*`, `save_*`, `record_*`)
  and the existing `ingest_signed_report` function, which is the nearest
  analog for how ENR's crud functions should be written and tested.
- `api/core/security.py` — contains `get_report_sync_agent`, the function ENR
  modifies. Its current docstring documents the exact mTLS trust assumption
  ENR must preserve.
- `api/core/config.py` — contains `REPORT_SYNC_AGENT_KEYS` and the other
  `REPORT_SYNC_*` settings ENR reads/deprecates, and the pattern for adding new
  `Settings` fields.
- `api/main.py` — router registration pattern, the existing
  `security_and_limits_middleware`, and the request-size gate keyed on
  `request.url.path.startswith(...)` that decides `REPORT_SYNC_MAX_BUNDLE_BYTES`
  vs the generic payload limit.
- `api/services/report_bundle.py` — `public_key_to_base64` /
  `public_key_from_base64` / Ed25519 helpers ENR reuses rather than
  reimplementing.
- `api/routers/report_sync.py` and `api/routers/scans.py` — the two existing
  router files closest in shape to what `api/routers/agents.py` must become
  (one machine route with a non-JWT auth dependency; one set of
  `Depends(get_session)`-based CRUD-backed routes).
- `api/models.py` — existing Pydantic response-model file ENR adds to (no
  `api/schemas/` package exists or should be created).
- `deploy/nginx/nginx.conf` — the existing `agent.ecdat.local` mTLS vhost ENR
  extends with the `/agent/v1/enroll` location.
- `.env.example` — existing variable documentation style and the exact current
  `REPORT_SYNC_AGENT_KEYS` comment ENR marks deprecated.
- `docs/ECDAT_CLI_GUIDE.md` — existing CLI documentation structure ENR adds a
  new section to, and `scanner/cli.py`'s existing `--sync-url` / `--client-cert`
  / `--client-key` / `--ca-cert` flags, whose httpx-with-mTLS pattern
  `scanner/enroll_cli.py` reuses.
- `tests/test_secure_report_sync.py` and `tests/test_security_controls.py` —
  existing test patterns for the mTLS/signed-bundle flow ENR's tests must
  match (in-memory SQLite via `StaticPool`, `app.dependency_overrides`,
  `monkeypatch.setattr(settings, ...)`).
- `conftest.py` — confirms tests run against `sqlite:///:memory:` and that
  `API_KEY` is pre-set for CI; `AGENT_ENROLLMENT_*` env vars ENR adds must not
  break this default test bootstrap.
- **Once merged ahead of ENR per the Wave 1 merge order (contract §6):**
  `api/core/rbac.py` and `api/routers/auth.py` (RBAC's SOLE files) — read
  these for the real `Principal` and `require_role` signatures before wiring
  ENR's admin routes. They do not exist in the repository at the time this
  spec is written; see §11.

---

## 5. File Ownership

Per `SYSTEM_INTERFACE_CONTRACT.md` §1.2, §1.3, §1.5, and §5.1, ENR's tier
assignments are:

**SOLE to ENR — create**
- `api/routers/agents.py`
- `api/services/enrollment.py`
- `db/migrations/005_agent_enrollment.sql`
- `scanner/enroll_cli.py`
- `tests/test_agent_enrollment.py`
- `docs/AGENT_ENROLLMENT_SCOPE.md` (per the `docs/*_SCANNING_SCOPE.md`-style
  "SOLE per file" row in §1.5 — ENR's equivalent scope-truth doc; note this is
  a new doc, distinct from `docs/SECURE_DEPLOYMENT.md`, which is COORDINATED)

**COORDINATED — ENR edits through the named lane owner, does not merge solo**
- `db/schema.sql`, `db/models.py`, `db/crud.py` — DB lane (Ronak). ENR's
  schema diff and crud additions land through §2 of the contract, never ad hoc.
- `api/core/security.py`, `api/core/config.py`, `api/main.py` — backend lane.
  Per C-09, ENR's edits here land **after** RBAC and **before** AUD.
- `api/models.py` — backend lane (Shreyanshi). ENR adds its Pydantic models
  alongside the other 6 features that touch this file; it does not restructure
  it or add a `schemas/` package.
- `deploy/nginx/nginx.conf` — deploy lane. ENR adds the enroll route and
  `$ssl_client_fingerprint` forwarding; ENR does not touch the dashboard
  gateway `location /` or `location /api/` blocks.
- `.env.example` — deploy lane. ENR adds `AGENT_ENROLLMENT_*` vars and marks
  `REPORT_SYNC_AGENT_KEYS` deprecated in its comment; ENR does not remove it.
- `docs/SECURE_DEPLOYMENT.md` — this is COORDINATED among INS, ENR, AUD (§1.5).
  ENR updates only the paragraph describing the enrollment gap (§2 above) and
  the migration list; it does not rewrite the document.
- `docs/ECDAT_CLI_GUIDE.md` — scanner lane, 6 features. ENR adds one new
  section (§7 target: after the existing "Signed Report Bundles" section) and
  does not edit other features' sections.

**Explicit do-not-touch list (other features' SOLE or FROZEN files)**
- `api/services/scan_runner.py` — **FROZEN**, owned by CONF. ENR must not edit.
- `api/services/cbom_generator.py` — COORDINATED, owned by the CBOM lane
  (Maitreyi). ENR must not edit.
- `api/services/risk_engine.py` — **FROZEN**, owned by the CBOM/risk lane. ENR
  must not edit.
- `scanner/finding.py` — **FROZEN**, scanner lane; only CONF may add fields.
  ENR does not touch scanner findings at all.
- `scanner/cli.py` — COORDINATED, scanner lane (Shashank). ENR's CLI work is
  entirely in the separate `scanner/enroll_cli.py` file specifically so it
  never needs to open this file (contract: "must not import `cli.main`").
- `scanner/constants.py` — COORDINATED, scanner lane. Not touched by ENR.
- `api/routers/auth.py`, `api/core/rbac.py` — **SOLE to RBAC**. ENR imports
  from `api/core/rbac.py` (once it exists) but must not add to or modify it.
- `api/routers/audit.py`, `api/services/audit.py` — **SOLE to AUD**. ENR calls
  into these once they exist (§11); it does not create or edit them.
- `dashboard/src/components/AgentStatusTable.jsx`, `AgentStatusCard.jsx`,
  `pages/AgentStatusPage/`, `hooks/useAgents.js` — **SOLE to ASP**. ENR ships
  no frontend code.
- `dashboard/src/lib/api.js` — COORDINATED, frontend lane. ENR does not add an
  API-client method here; that is ASP's job as the consumer of `GET /agents`.
- `db/migrations/002_*.sql`, `003_*.sql`, `004_*.sql`, `006_*.sql`,
  `007_*.sql`, `008_*.sql` — reserved to CONF, the artifact-scanning group,
  RBAC, AUD, TRI, and DFS/TRD respectively (contract §2.1). ENR uses **only**
  `005_agent_enrollment.sql`.

---

## 6. Tech Stack & Pinned Versions

All dependencies are **already present** in `requirements.txt`; ENR adds none.

| Library | Pinned constraint (`requirements.txt`) | ENR usage |
|---|---|---|
| `fastapi` | `>=0.111.0` | `api/routers/agents.py` |
| `pydantic` | `>=2.7.0` | request/response models in `api/models.py` |
| `pydantic-settings` | `>=2.3.0` | new `Settings` fields in `api/core/config.py` |
| `SQLAlchemy` | `>=2.0,<2.1` | `Agent`, `EnrollmentToken` ORM models |
| `psycopg2-binary` | `>=2.9` | Postgres driver (unchanged, no ENR-specific use) |
| `httpx` | `>=0.27.0` | `scanner/enroll_cli.py` HTTP client (mirrors `scanner/cli.py`'s existing `--sync-url` usage) |
| `pytest`, `pytest-asyncio` | `>=8.0`, `>=0.23.0` | `tests/test_agent_enrollment.py` |
| stdlib `secrets` | n/a | enrollment token generation (`secrets.token_urlsafe`) |
| stdlib `hashlib` | n/a | SHA-256 of the token (`hashlib.sha256`) |
| stdlib `argparse` | n/a | `scanner/enroll_cli.py` flag parsing |

**`cryptography`** (for Ed25519 keypair generation in `scanner/enroll_cli.py`
and key decoding in `api/services/enrollment.py`) is used today by
`api/services/report_bundle.py` but is **not currently pinned** in
`requirements.txt` — this is flagged in contract C-18 as a pre-existing
defect, to be fixed in the Wave 0 "grouped diff owned by the backend lane."
**ENR does not pin it.** ENR only confirms, before starting work, that the
Wave 0 pin has landed (it is a prerequisite for every feature that imports
`cryptography`, not an ENR-specific action) — see §11.

No new entries are added to `requirements.txt` by this feature.

---

## 7. Concrete Interface Definitions

### 7.1 SQL — `db/migrations/005_agent_enrollment.sql`

```sql
-- ============================================================================
-- 005_agent_enrollment.sql  ·  owner: ENR
-- Replaces the static REPORT_SYNC_AGENT_KEYS env mapping with a queryable
-- registry. Only the SHA-256 of an enrolment token is ever stored.
-- ============================================================================
CREATE TABLE IF NOT EXISTS agents (
    id                      SERIAL PRIMARY KEY,
    agent_id                TEXT NOT NULL UNIQUE,   -- matches reports.agent_id (TEXT, free-form today)
    organization_id         TEXT NOT NULL,
    public_key              TEXT NOT NULL,          -- base64 raw Ed25519, same encoding as REPORT_SYNC_AGENT_KEYS
    client_cert_fingerprint TEXT,                   -- forwarded by nginx; cert issuance stays manual
    status                  TEXT NOT NULL DEFAULT 'active',   -- active | revoked
    enrolled_at             TIMESTAMP DEFAULT now(),
    revoked_at              TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agents_org_status ON agents(organization_id, status);

CREATE TABLE IF NOT EXISTS enrollment_tokens (
    id                   SERIAL PRIMARY KEY,
    token_hash           TEXT NOT NULL UNIQUE,      -- SHA-256 hex. The token itself is never persisted.
    organization_id      TEXT NOT NULL,
    created_by           INTEGER REFERENCES users(id) ON DELETE SET NULL,
    expires_at           TIMESTAMP NOT NULL,
    consumed_at          TIMESTAMP,
    consumed_by_agent_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_enrollment_tokens_open
    ON enrollment_tokens(expires_at) WHERE consumed_at IS NULL;
```

`db/schema.sql` receives the identical two `CREATE TABLE IF NOT EXISTS` /
`CREATE INDEX IF NOT EXISTS` statements above, appended after the existing
`reports` table block. `docker-compose.yml` gains:

```yaml
      - ./db/migrations/005_agent_enrollment.sql:/docker-entrypoint-initdb.d/06_agent_enrollment.sql:ro
```

### 7.2 `db/models.py` additions

```python
AGENT_STATUSES = ("active", "revoked")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(Text, nullable=False)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    client_cert_fingerprint: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="active", nullable=False)
    enrolled_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_agents_org_status", "organization_id", "status"),
    )


class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    consumed_by_agent_id: Mapped[str | None] = mapped_column(Text)
```

### 7.3 `db/crud.py` additions

```python
def create_enrollment_token(
    session: Session, *, token_hash: str, organization_id: str,
    created_by: int | None, expires_at: dt.datetime,
) -> EnrollmentToken: ...

def get_open_enrollment_token(session: Session, token_hash: str) -> EnrollmentToken | None: ...

def consume_enrollment_token(
    session: Session, token_hash: str, *, consumed_by_agent_id: str,
) -> None: ...

def create_agent(
    session: Session, *, agent_id: str, organization_id: str,
    public_key: str, client_cert_fingerprint: str | None,
) -> Agent: ...

def get_agent(session: Session, agent_id: str) -> Agent | None: ...

def list_agents(
    session: Session, *, organization_id: str | None = None,
    status: str | None = None,
) -> list[Agent]: ...

def revoke_agent(session: Session, agent_id: str) -> Agent | None: ...

def get_last_report_at_by_agent(session: Session, agent_id: str) -> dt.datetime | None: ...
```

### 7.4 `api/services/enrollment.py`

```python
class EnrollmentError(ValueError):
    """Raised for an invalid, expired, or already-consumed enrollment token,
    or a duplicate agent_id enrollment attempt."""


def generate_enrollment_token() -> str: ...

def hash_enrollment_token(token: str) -> str: ...

def mint_enrollment_token(
    session: Session, *, organization_id: str, created_by: int | None,
    ttl_hours: int,
) -> tuple[EnrollmentToken, str]:
    """Returns (row, plaintext_token). plaintext_token is never persisted or logged."""


def enroll_agent(
    session: Session, *, token: str, agent_id: str, public_key_b64: str,
    client_cert_fingerprint: str | None,
) -> Agent: ...


def revoke_agent(session: Session, *, agent_id: str) -> Agent: ...


def resolve_active_agent_public_key(session: Session, agent_id: str) -> str | None:
    """Returns the base64 Ed25519 public key for an agent_id with status='active',
    or None (not enrolled, unknown, or revoked)."""


def compute_delivery_status(
    last_report_at: dt.datetime | None, *, now: dt.datetime, stale_after_hours: int,
) -> str:
    """Returns 'never_reported' | 'recent' | 'stale'."""
```

### 7.5 `api/core/config.py` additions to `Settings`

```python
AGENT_ENROLLMENT_TOKEN_TTL_HOURS: int = 24
AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS: bool = True
AGENT_ENROLLMENT_CERT_FINGERPRINT_HEADER: str = "X-ECDAT-Client-Cert-Fingerprint"
AGENT_ENROLLMENT_STALE_AFTER_HOURS: int = 24  # PLACEHOLDER — see §11, contract C-06
```

### 7.6 `api/core/security.py` — `get_report_sync_agent` (modified body, unchanged signature)

```python
async def get_report_sync_agent(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
    agent_id: Optional[str] = Header(None, alias="X-ECDAT-Agent-ID"),
) -> tuple[str, str]: ...
```

### 7.7 `api/models.py` additions

```python
class EnrollmentTokenMintRequest(BaseModel):
    organization_id: str
    ttl_hours: int | None = None


class EnrollmentTokenMintResponse(BaseModel):
    token: str
    organization_id: str
    expires_at: dt.datetime


class AgentEnrollRequest(BaseModel):
    token: str
    agent_id: str
    public_key: str


class AgentEnrollResponse(BaseModel):
    agent_id: str
    organization_id: str
    status: str
    enrolled_at: dt.datetime


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    organization_id: str
    registry_status: str
    delivery_status: str
    enrolled_at: dt.datetime
    revoked_at: dt.datetime | None


class AgentListResponse(BaseModel):
    agents: list[AgentOut]
    total: int


class AgentRevokeResponse(BaseModel):
    agent_id: str
    status: str
    revoked_at: dt.datetime
```

### 7.8 `api/routers/agents.py`

```python
router = APIRouter(prefix="/agents", tags=["agents"])
enroll_router = APIRouter(prefix="/agent/v1", tags=["agent-enrollment"])


@router.post("/enrollment-tokens", response_model=EnrollmentTokenMintResponse, status_code=201)
def mint_enrollment_token(
    body: EnrollmentTokenMintRequest,
    db: Annotated[Session, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_role(Role.SECURITY_ADMIN))],
) -> EnrollmentTokenMintResponse: ...


@router.get("", response_model=AgentListResponse)
def list_agents(
    db: Annotated[Session, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_role(Role.SECURITY_ADMIN, Role.AUDITOR))],
    status: str | None = Query(None),
    organization_id: str | None = Query(None),
) -> AgentListResponse: ...


@router.post("/{agent_id}/revoke", response_model=AgentRevokeResponse)
def revoke_agent(
    agent_id: str,
    db: Annotated[Session, Depends(get_session)],
    principal: Annotated[Principal, Depends(require_role(Role.SECURITY_ADMIN))],
) -> AgentRevokeResponse: ...


@enroll_router.post("/enroll", response_model=AgentEnrollResponse, status_code=201)
def enroll_agent(
    body: AgentEnrollRequest,
    request: Request,
    db: Annotated[Session, Depends(get_session)],
) -> AgentEnrollResponse: ...
```

Example request/response bodies:

```json
POST /agents/enrollment-tokens
{ "organization_id": "acme-corp", "ttl_hours": 24 }

201
{ "token": "AGT-1a2b3c...redacted...9z", "organization_id": "acme-corp",
  "expires_at": "2026-09-21T18:00:00Z" }
```

```json
POST /agent/v1/enroll
{ "token": "AGT-1a2b3c...redacted...9z", "agent_id": "build-agent-01",
  "public_key": "base64-raw-ed25519-public-key" }

201
{ "agent_id": "build-agent-01", "organization_id": "acme-corp",
  "status": "active", "enrolled_at": "2026-09-20T18:03:00Z" }
```

```json
GET /agents?status=active

200
{ "agents": [
    { "agent_id": "build-agent-01", "organization_id": "acme-corp",
      "registry_status": "active", "delivery_status": "recent",
      "enrolled_at": "2026-09-20T18:03:00Z", "revoked_at": null }
  ], "total": 1 }
```

```json
POST /agents/build-agent-01/revoke

200
{ "agent_id": "build-agent-01", "status": "revoked",
  "revoked_at": "2026-09-25T09:15:00Z" }
```

### 7.9 `deploy/nginx/nginx.conf` — new location on the existing `agent.ecdat.local` vhost

```nginx
        location = /agent/v1/enroll {
            limit_except POST { deny all; }
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-ECDAT-mTLS-Verified "SUCCESS";
            proxy_set_header X-ECDAT-Client-Cert-Fingerprint $ssl_client_fingerprint;
            proxy_pass http://backend:8000;
        }
```

### 7.10 `scanner/enroll_cli.py`

```python
def generate_agent_keypair() -> tuple[Ed25519PrivateKey, str]: ...

def write_private_key_pem(key: Ed25519PrivateKey, path: Path) -> None: ...

def build_enroll_payload(*, token: str, agent_id: str, public_key_b64: str) -> dict[str, Any]: ...

def submit_enrollment(
    url: str, payload: dict[str, Any], *,
    client_cert: Path, client_key: Path, ca_cert: Path, timeout: float,
) -> dict[str, Any]: ...

def build_parser() -> argparse.ArgumentParser: ...

def main(argv: list[str] | None = None) -> int: ...
```

```text
python -m scanner.enroll_cli
  --enroll-url HTTPS_URL --token TOKEN --agent-id ID
  --client-cert PEM --client-key PEM --ca-cert PEM
  --key-out PATH [--force] [--timeout SECONDS]
```

### 7.11 `.env.example` additions

```bash
AGENT_ENROLLMENT_TOKEN_TTL_HOURS=24
AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS=true
AGENT_ENROLLMENT_CERT_FINGERPRINT_HEADER=X-ECDAT-Client-Cert-Fingerprint
AGENT_ENROLLMENT_STALE_AFTER_HOURS=24
```

---

## 8. Step-by-Step Implementation Plan

1. **`db/migrations/005_agent_enrollment.sql`** — create the file with the
   exact SQL in §7.1. Confirm it is idempotent against a database that already
   has `agents`/`enrollment_tokens` (re-running must no-op).
2. **`db/schema.sql`** — append the identical `CREATE TABLE IF NOT EXISTS` /
   index statements from §7.1 after the `reports` table, through the DB lane.
3. **`docker-compose.yml`** — add the `06_agent_enrollment.sql` init mount
   from §7.1, through the deploy lane.
4. **`db/models.py`** — add `AGENT_STATUSES`, `Agent`, `EnrollmentToken` exactly
   as in §7.2, through the DB lane.
5. **`db/crud.py`** — add the eight functions in §7.3, following the file's
   existing `get_*`/`list_*`/`create_*` naming and docstring style, through
   the DB lane.
6. **`api/core/config.py`** — add the four `Settings` fields from §7.5.
7. **`api/services/enrollment.py`** — implement the module in §7.4: token
   generation (`secrets.token_urlsafe(32)`), SHA-256 hashing
   (`hashlib.sha256(token.encode()).hexdigest()`), and the enroll/revoke/
   resolve/delivery-status functions, calling only the `db/crud.py` functions
   from step 5 and the existing `public_key_from_base64` validator from
   `api/services/report_bundle.py` to reject a malformed public key at
   enrollment time (fail fast, not at first report-sync).
8. **`api/models.py`** — add the seven Pydantic models from §7.7.
9. **`api/routers/agents.py`** — implement `router` and `enroll_router` from
   §7.8, calling only `api/services/enrollment.py`. `enroll_agent` (the
   machine route) reads `client_cert_fingerprint` from the
   `AGENT_ENROLLMENT_CERT_FINGERPRINT_HEADER`-named request header, exactly as
   `get_report_sync_agent` already reads `REPORT_SYNC_MTLS_HEADER`.
10. **`api/core/security.py`** — modify `get_report_sync_agent` per §7.6:
    look up the agent via `db.crud.get_agent`, require `status == "active"`,
    return `(agent_id, agent.public_key)`; if not found and
    `settings.AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS` is true, fall back to the
    existing `REPORT_SYNC_AGENT_KEYS` dict lookup unchanged; otherwise 401.
11. **`api/main.py`** — import and `include_router(agents.router)` and
    `include_router(agents.enroll_router)`, in the position matching C-09's
    ordering comment (after RBAC's router, before AUD's).
12. **`deploy/nginx/nginx.conf`** — add the `location = /agent/v1/enroll`
    block from §7.9 inside the existing `agent.ecdat.local` server block.
13. **`.env.example`** — append the four lines from §7.11 and edit the
    existing `REPORT_SYNC_AGENT_KEYS` comment to note it is deprecated in
    favor of `POST /agent/v1/enroll`, without deleting the variable.
14. **`scanner/enroll_cli.py`** — implement the module and CLI in §7.10,
    generating the Ed25519 keypair with `cryptography`, writing the private
    key PEM with `0600` permissions, and posting to `--enroll-url` via
    `httpx.Client(cert=(client_cert, client_key), verify=ca_cert)`, mirroring
    `scanner/cli.py`'s existing `_sync_bundle` mTLS pattern without importing
    `scanner.cli`.
15. **`docs/SECURE_DEPLOYMENT.md`** — update the "Remaining production
    prerequisites" paragraph to remove "managed agent enrollment/revocation"
    from the outstanding-gaps list and describe the new flow in one paragraph,
    through the deploy lane.
16. **`docs/ECDAT_CLI_GUIDE.md`** — add a new section documenting
    `scanner/enroll_cli.py`'s flags and an end-to-end enroll-then-sync example,
    through the scanner lane.
17. **`docs/AGENT_ENROLLMENT_SCOPE.md`** — create ENR's own scope-truth doc
    (per §1.5's "SOLE per file" row), stating plainly what this feature does
    and does not authenticate (see §3 Out-of-Scope).
18. **`tests/test_agent_enrollment.py`** — write the tests specified in §12.

---

## 9. Naming & Symbol Registry

| Symbol | Kind | Location | Convention check |
|---|---|---|---|
| `agents` | DB table | migration 005 / `db/schema.sql` | plural `snake_case` — §3.8 ✓ |
| `enrollment_tokens` | DB table | migration 005 / `db/schema.sql` | plural `snake_case` — §3.8 ✓ |
| `AGENT_STATUSES` | module constant | `db/models.py` | `UPPER_SNAKE_CASE` tuple, matches `CONFIDENCES` pattern — §3.8 ✓; no collision (new name) |
| `Agent`, `EnrollmentToken` | ORM class | `db/models.py` | `PascalCase` — §3.1 ✓; no collision with existing classes |
| `create_enrollment_token`, `get_open_enrollment_token`, `consume_enrollment_token`, `create_agent`, `get_agent`, `list_agents`, `revoke_agent`, `get_last_report_at_by_agent` | function | `db/crud.py` | `create_*`/`get_*`/`list_*`/`consume_*`/`revoke_*` — extends the existing `get_*`/`list_*`/`save_*`/`record_*` set (§3.1); `consume_*` and `revoke_*` are new verbs, not yet used elsewhere in `db/crud.py` — flag to DB lane reviewer, not a collision |
| `generate_enrollment_token`, `hash_enrollment_token`, `mint_enrollment_token`, `enroll_agent`, `revoke_agent`, `resolve_active_agent_public_key`, `compute_delivery_status` | function | `api/services/enrollment.py` | `snake_case`, module-path-disambiguated (`enrollment.revoke_agent` vs `db.crud.revoke_agent`) — §3.1 ✓ |
| `EnrollmentError` | exception class | `api/services/enrollment.py` | `PascalCase`, matches `ReportBundleError` naming pattern in `report_bundle.py` |
| `EnrollmentTokenMintRequest`, `EnrollmentTokenMintResponse`, `AgentEnrollRequest`, `AgentEnrollResponse`, `AgentOut`, `AgentListResponse`, `AgentRevokeResponse` | Pydantic model | `api/models.py` | `PascalCase`, `*Out`/`*Response`/`*Request` suffixes match existing `FindingOut`/`ScanCreateResponse` style |
| `router`, `enroll_router` | `APIRouter` instance | `api/routers/agents.py` | matches existing single-`router`-per-file pattern, extended to two because ENR owns two distinct route namespaces (`/agents`, `/agent/v1`) in one SOLE file |
| `mint_enrollment_token`, `list_agents`, `revoke_agent`, `enroll_agent` | route function | `api/routers/agents.py` | `snake_case`; **name collision, not a naming defect**: `list_agents`/`revoke_agent` shadow same-named `db.crud` functions and `enrollment.revoke_agent` shadows `api.services.enrollment.revoke_agent` — disambiguated by module path per §3.1, exactly as `risk_engine.score_findings` vs. a route of the same name would be; do not rename either side to work around this |
| `AGENT_ENROLLMENT_TOKEN_TTL_HOURS` | env var | `api/core/config.py`, `.env.example` | `AGENT_ENROLLMENT_` prefix — §3.3 ✓, listed as an example in the contract |
| `AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS` | env var | `api/core/config.py`, `.env.example` | `AGENT_ENROLLMENT_` prefix — §3.3 ✓, listed as an example in the contract |
| `AGENT_ENROLLMENT_CERT_FINGERPRINT_HEADER` | env var | `api/core/config.py`, `.env.example` | `AGENT_ENROLLMENT_` prefix — §3.3 ✓; new, not in the contract's example list but follows the same prefix rule |
| `AGENT_ENROLLMENT_STALE_AFTER_HOURS` | env var | `api/core/config.py`, `.env.example` | `AGENT_ENROLLMENT_` prefix — §3.3 ✓; value is a **placeholder**, see §11 |
| `POST /agent/v1/enroll` | HTTP route | `api/routers/agents.py` | machine route, versioned `/agent/v1` namespace — §3.4 ✓; reserved **Sole** to ENR in §5.3 |
| `GET /agents`, `POST /agents/enrollment-tokens`, `POST /agents/{agent_id}/revoke` | HTTP route | `api/routers/agents.py` | plural resource noun at root — §3.4 ✓; `GET /agents` listed as shared with ASP (read-only consumer) in §5.3, C-05 |
| `ecdat.agent.enroll`, `ecdat.agent.revoke` | audit action name | emitted by `api/services/enrollment.py`, consumed by AUD once it exists | dotted `ecdat.<object>.<verb>` — §3.6 ✓, both literally named in the contract's example list |
| `X-ECDAT-Client-Cert-Fingerprint` | HTTP header | `deploy/nginx/nginx.conf`, `api/core/config.py` default | new header, does not collide with the existing `X-ECDAT-Agent-ID` / `X-ECDAT-mTLS-Verified` headers |

No symbol above renames, removes, or collides with a name in the `detection_method`
registry (§3.2), the CLI flag surface (§3.5, C-11), or any other feature's
SOLE/FROZEN naming.

---

## 10. Known Cross-Feature Risks

Pulled directly from `SYSTEM_INTERFACE_CONTRACT.md` §4 and §5; resolutions
below are the contract's, not new ones.

- **C-01 (migration collision):** Five proposals independently claimed `002_`.
  Resolved: ENR's migration is `005_agent_enrollment.sql`, mounted as
  `06_agent_enrollment.sql`, per §2.1's reservation table — non-negotiable
  without editing the contract.
- **C-05 (`api/routers/agents.py` created twice):** ENR and ASP both proposed
  this file. Resolved: ENR owns it solely and merges first; ASP consumes
  `GET /agents` and adds no second router file. ENR's implementation plan
  (§8, step 9) must not anticipate or stub any ASP-specific response fields
  beyond what §7.7's `AgentOut` already defines.
- **C-06 ("agent status" means two things):** ENR's `agents.status` (registry
  lifecycle) and ASP's delivery freshness are different facts. Resolved: two
  separate response fields, `registry_status` and `delivery_status`, never
  merged into one badge; no `last_seen_at` heartbeat column. ENR implements
  both fields on `GET /agents` (§7.7, §7.8) since it owns the endpoint, but the
  exact `recent`/`stale` threshold is **unresolved** (Low confidence) — see §11.
- **C-09 (auth rewrite ordering):** RBAC must merge and publish the
  `Principal` contract and `require_role` **before** ENR's admin routes can be
  written for real. ENR's admin endpoints use `require_role(SECURITY_ADMIN)`
  from day one — not an interim `get_api_key`, which is what the Step 1
  proposal assumed and which this spec's changelog (§1) already flags as a
  deviation. AUD records `actor_type='api_key'` before RBAC lands and
  `actor_type='user'` after, for ENR's admin actions — ENR does not implement
  this itself, it is AUD's concern once AUD exists.
- **C-10 (`organization_id` scoping assigned to nobody):** ENR's
  `agents.organization_id` and `enrollment_tokens.organization_id` are
  required, non-null TEXT columns (§7.1) — ENR does not itself invent tenant
  filtering logic; once RBAC's `Principal.organization_id` and the shared
  `db/crud.py` filter helper exist, `list_agents` should be scoped through
  that helper rather than a route-local `WHERE`. The NULL-handling policy for
  *legacy* rows is explicitly out of scope for ENR, since `agents` is a new
  table with no legacy rows — but ENR's own `list_agents` must not filter
  admin-facing results to one organization silently; see §11.
- **C-26 (agent report-sync path — compatible):** RBAC, ENR, and AUD all touch
  this path; the contract records it compatible because "ENR changes key
  *resolution*, not the protocol." ENR's modification to
  `get_report_sync_agent` (§7.6, §8 step 10) must preserve the function's
  existing signature, its mTLS-header check, and the Ed25519
  verify-in-`report_sync.py` call it feeds — only the source of the public
  key changes, from a dict to the `agents` table.
- **`REPORT_SYNC_AGENT_KEYS` (§5.4, "Deprecated-in-place"):** Not removed.
  ENR adds `AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS` as the fallback gate, per §7.5
  and §8 step 10, rather than deleting the variable or the `.env.example`
  documentation for it.
- **`API_KEY` / `X-API-Key` (§5.4, "Conflicting !"):** Shared concern across
  RBAC, ENR, AUD, INS; resolved only as an ordering (C-09), with the actual
  "does `X-API-Key` survive for CLI/service callers" question left open at
  Medium confidence. ENR's admin routes do not use `X-API-Key` — they use
  `require_role`, per C-09's ordering resolution — so ENR does not need this
  question answered to proceed; it only matters if a *different* feature's
  design depends on the answer.

---

## 11. Pre-Answered Ambiguities

1. **If `AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS` is true and an `agent_id`
   exists in both the `agents` table and `REPORT_SYNC_AGENT_KEYS`,** the DB
   row wins. `get_report_sync_agent` checks `db.crud.get_agent` first and
   only falls back to the env mapping when the DB lookup returns nothing.
   Rationale: enrollment is the newer, more specific source of truth, and a
   revoked DB row must be able to override a stale env entry for the same
   `agent_id`.
2. **If an enrollment token is presented twice (replay),** the second call to
   `POST /agent/v1/enroll` returns `401` with a generic "invalid or already
   used enrollment token" message — do not distinguish "expired" from
   "already consumed" from "never existed" in the response body (only in
   server logs), to avoid giving an attacker a token-enumeration oracle.
3. **If `POST /agent/v1/enroll` is called with an `agent_id` that is already
   enrolled and `active` (a different, valid token),** reject with `409
   Conflict` and do not overwrite the existing public key. Re-enrolling an
   existing `agent_id` under a new key must go through an explicit
   revoke-then-re-enroll, since silently accepting a new key for an existing
   `agent_id` is exactly the key-substitution risk enrollment exists to
   prevent.
4. **If `POST /agents/{agent_id}/revoke` is called on an `agent_id` that does
   not exist,** return `404`. If it is called on an agent that is already
   `revoked`, return `200` with the existing `revoked_at` unchanged
   (idempotent), not an error — matching the existing codebase's idempotent
   pattern in `crud.ingest_signed_report` (replay returns `200`/`201` with
   `accepted: false`, not an error).
5. **If `cryptography` is not yet pinned in `requirements.txt` when ENR
   implementation starts** (contract C-18, Wave 0 item, owned by the backend
   lane, not ENR): stop and flag a human per `AGENT_RULES.md` #4 rather than
   ENR pinning it unilaterally as a side effect of this feature — pinning it
   is explicitly "independent of all 17 features" per the contract's own
   wording, and ENR quietly doing it would create an uncoordinated edit to a
   COORDINATED file (§1.5, `requirements.txt`).
6. **If `api/core/rbac.py` does not yet exist when ENR implementation
   starts** (RBAC is Wave 1, ENR is Wave 2, per contract §6 — RBAC should
   already be merged): stop and flag a human. Do not write ENR's admin routes
   against a temporary `get_api_key` dependency "to unblock progress" — the
   contract's C-09 resolution is explicit that ENR uses `require_role` "from
   day one," and building against `get_api_key` first would require a second,
   avoidable PR to retrofit RBAC later.
7. **Certificate-fingerprint binding (Step 1 proposal's open question,
   restated):** "Should `X-ECDAT-Agent-ID` be bound to the cert fingerprint?
   Today any valid cert can claim any enrolled ID." **The contract does not
   answer this.** It is not listed in §7 (Open Items Requiring Human
   Sign-Off) at all — it was raised only in the Step 1 proposal and never
   picked up by the integration pass. Per this task's instructions, that
   means: do not invent a resolution. ENR's `POST /agent/v1/enroll` and the
   modified `get_report_sync_agent` both **record** `client_cert_fingerprint`
   (§7.1, §7.8) but neither **enforces** a match between it and the
   fingerprint on a later report-sync call — the recorded value is available
   for a human to decide on and for AUD to log, not to gate on. Flag this to
   a human before considering the feature complete.
8. **Key rotation (Step 1 proposal's open question, restated):** "Is key
   rotation (multiple keys per agent) in scope?" **Not addressed by the
   contract.** `agents.public_key` is a single column (§7.1) with a `UNIQUE`
   constraint on `agent_id`, not a one-to-many keys table. ENR implements
   single-key-per-agent only. If key rotation is needed, that is a schema
   change requiring a new migration number and contract-level coordination,
   not something to improvise inside migration `005`.
9. **Retroactive flagging of reports from a since-revoked agent (Step 1
   proposal's open question, restated):** **Not addressed by the contract.**
   `revoke_agent` (§7.4) only changes `agents.status`; it does not touch
   `reports` or `findings` rows already ingested under that agent's prior
   `active` status. ENR does not implement retroactive flagging. This is
   explicitly out of scope (§3) rather than silently unimplemented.
10. **The exact `recent`/`stale` delivery-status threshold (contract C-06,
    listed under §7 Open Items, "Low confidence"):** the contract states the
    *split* into two fields is decided (High confidence) but the *number of
    hours* is not — "There is no operational baseline, no SLA, and no
    heartbeat interval to derive it from. Product decision, not an
    engineering one." ENR ships `AGENT_ENROLLMENT_STALE_AFTER_HOURS=24` as a
    **placeholder**, clearly commented as such in `.env.example` and in
    `compute_delivery_status`'s docstring, and flags in this spec's changelog
    that a human must set the real value before this is demo- or
    production-ready. Do not treat `24` as a considered product decision.

---

## 12. Test Plan / Definition of Done

All commands run from the repository root, matching the existing test suite's
invocation style (`conftest.py` forces `DATABASE_URL=sqlite:///:memory:` and
`API_KEY=ci-test-key` automatically).

```bash
python -m pytest tests/test_agent_enrollment.py -v
```

Expected: all tests in the new file pass, exercising —
- Minting a token, then enrolling with it, succeeds and returns `status:
  "active"`.
- Enrolling twice with the same (now-consumed) token fails `401`.
- Enrolling with an expired token fails `401`.
- Enrolling a second time with a different token but the same, already-active
  `agent_id` fails `409` (ambiguity 3).
- `GET /agents` (as a `require_role(SECURITY_ADMIN)` principal, once RBAC test
  fixtures exist — see step below) returns the enrolled agent with
  `registry_status: "active"` and `delivery_status: "never_reported"` before
  any report has been ingested from it.
- After a signed report bundle from that `agent_id` is ingested (reusing the
  `_bundle()` helper pattern from `tests/test_secure_report_sync.py`),
  `delivery_status` becomes `"recent"`.
- `POST /agents/{agent_id}/revoke` sets `status: "revoked"`, and a subsequent
  call to `POST /agent/v1/report-bundles` signed by that agent's key now fails
  `401` via the modified `get_report_sync_agent`.
- With `AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS=true` and an `agent_id` present
  only in `REPORT_SYNC_AGENT_KEYS` (not in `agents`), report-sync still
  succeeds (legacy fallback preserved).
- With `AGENT_ENROLLMENT_ALLOW_LEGACY_KEYS=false`, the same legacy-only
  `agent_id` now fails `401`.
- Revoking an already-revoked agent returns `200` idempotently, not an error
  (ambiguity 4).
- Revoking a nonexistent `agent_id` returns `404`.

```bash
python -m pytest tests/ -v
```

Expected: the full existing suite still passes — in particular
`tests/test_secure_report_sync.py` and `tests/test_security_controls.py`,
confirming ENR's change to `get_report_sync_agent` did not break the existing
mTLS + Ed25519 report-ingestion flow for agents still configured only through
`REPORT_SYNC_AGENT_KEYS`.

```bash
python -m scanner.enroll_cli --help
```

Expected: exits `0`, prints usage listing `--enroll-url`, `--token`,
`--agent-id`, `--client-cert`, `--client-key`, `--ca-cert`, `--key-out`.

```bash
python -c "import sqlalchemy; from db.models import Base; from sqlalchemy import create_engine; \
e = create_engine('sqlite://'); Base.metadata.create_all(e); print('ok')"
```

Expected: prints `ok` — confirms `Agent`/`EnrollmentToken` ORM models import
cleanly and `create_all` succeeds against SQLite (the test-suite's DB), not
only against the Postgres-flavored migration SQL.

**Definition of Done** for this feature:
- Every command above passes with the exact expected output described.
- `AGENT_RULES.md` #7 satisfied (tests run before declaring done).
- No file outside §5's ENR-owned or ENR-COORDINATED list was modified.
- Ambiguities 5 and 6 in §11 have been confirmed *not* triggered (i.e.,
  `cryptography` is pinned and `api/core/rbac.py` exists) before this feature
  is merged — if either is still missing, this feature is **not done**; it is
  blocked, and that must be stated rather than worked around.
- A human has reviewed and signed off on ambiguities 7, 8, 9, and 10 in §11,
  per the Header's reviewer sign-off line.

---

## 13. Rollback Plan

- **Schema:** `db/migrations/005_agent_enrollment.sql` only adds new tables
  and indexes (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) and
  alters no existing table. Rollback is a straight
  `DROP TABLE IF EXISTS enrollment_tokens; DROP TABLE IF EXISTS agents;`
  run manually against the affected database; no other feature's tables
  reference `agents` or `enrollment_tokens` by foreign key, so this is safe in
  isolation. Remove the identical `CREATE TABLE` block from `db/schema.sql`
  and the `06_agent_enrollment.sql` mount from `docker-compose.yml` in the
  same revert so a fresh volume and an upgraded volume stay in lockstep
  (mirrors the discipline `docs/SECURE_DEPLOYMENT.md` already documents for
  `001_secure_reporting.sql`).
- **API:** revert `api/main.py`'s two `include_router` lines for
  `agents.router` / `agents.enroll_router`, and revert `api/core/security.py`'s
  `get_report_sync_agent` to its pre-ENR body (DB-free, `REPORT_SYNC_AGENT_KEYS`
  only). Because the DB-backed lookup is additive with a legacy fallback
  (ambiguity 1), reverting the code half while the schema half is still
  present is also safe — agents fall back to `REPORT_SYNC_AGENT_KEYS` for
  authentication as before, and the code no longer touches the new tables.
- **CLI:** `scanner/enroll_cli.py` is a standalone entrypoint; deleting the
  file has no effect on `scanner/cli.py` or any other CLI path (contract:
  "must not import `cli.main`" — the converse also holds, nothing imports
  `enroll_cli`).
- **Deploy:** revert the `location = /agent/v1/enroll` block from
  `deploy/nginx/nginx.conf`; the surrounding `agent.ecdat.local` vhost and its
  existing `/agent/v1/report-bundles` location are untouched by this feature
  and need no change.
- **Config/docs:** `.env.example`'s four new `AGENT_ENROLLMENT_*` lines and
  the deprecation comment on `REPORT_SYNC_AGENT_KEYS` can be reverted with no
  functional effect, since `pydantic-settings` fields not present in `.env`
  simply take their class defaults. `docs/SECURE_DEPLOYMENT.md`,
  `docs/ECDAT_CLI_GUIDE.md`, and `docs/AGENT_ENROLLMENT_SCOPE.md` reverts are
  documentation-only.
- **Data safety during rollback:** any `agents` rows enrolled before rollback
  are lost once the tables are dropped. If a rollback is needed after agents
  have been enrolled in a real deployment (not CI), export
  `SELECT agent_id, public_key FROM agents WHERE status='active';` first and
  manually merge those entries into `REPORT_SYNC_AGENT_KEYS` before dropping
  the tables, so report-sync continues working for already-enrolled agents
  under the legacy mapping.
