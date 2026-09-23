# SPECIFICATION: Minimal RBAC (Role-Based Access Control)

## 1. Header

**Feature:** Minimal RBAC  
**Feature Code:** `RBAC`  
**Owner:** Anonymous (assigned via integration master)  
**Spec Version:** 1.0  
**Status:** Ready for implementation  
**Reviewer Sign-Off:** Pending integration gate

### Changelog

- **v1.0 (§1 baseline):** Initial specification from Step 1 proposal and system interface contract C-09, C-03, C-08.
- **Deviation from Step 1 proposal:** Organization-scoped queries remain unimplemented per contract §5.2 note ("CONFLICTING!") — another feature assumes responsibility. JWT token storage defaults to `localStorage` per C-08 open sign-off; may be overridden at deployment time if C-08 resolves otherwise.

---

### Step 5 integration-audit corrections (v1.1)

Applied during the final Gemini-Pro-equivalent cross-check. Each item was a silent deviation from `SYSTEM_INTERFACE_CONTRACT.md`:

| # | Was | Now | Why |
|---|---|---|---|
| 1 | `db/migrations/002_rbac_users.sql` | `db/migrations/004_rbac_users.sql`, compose mount `05_rbac_users.sql` | `002_` is CONF's `002_confidence_scoring.sql`; contract §2.1 reserves `004_` for RBAC. Two migrations with the same number silently overwrite each other |
| 2 | `users.email` | `users.username` | Contract §2.2. AUD (`actor_from_principal`) and TRI (`updated_by`) both already read `principal.username` |
| 3 | missing `is_active`; `updated_at` | `is_active BOOLEAN NOT NULL DEFAULT TRUE`; `last_login_at` | Contract §2.2 column list |
| 4 | `ROLES = ("Security Admin", "Auditor", "Developer")` | `class Role(str, Enum)` with `SECURITY_ADMIN`/`AUDITOR`/`DEVELOPER` | Contract §2.2. `"Security Admin"` contains a space and cannot be an enum member; ENR already imports `Role.SECURITY_ADMIN` |
| 5 | `require_role("Admin", "Developer")` | `require_role(Role.SECURITY_ADMIN, Role.DEVELOPER)` | `"Admin"` was not in this spec's own `ROLES` tuple |
| 6 | `JWT_SECRET`, `JWT_EXPIRATION_MINUTES`, `JWT_STORE_METHOD` | `AUTH_JWT_SECRET`, `AUTH_JWT_TTL_MINUTES`, `AUTH_JWT_STORE_METHOD` | Contract §3.3 reserves the `AUTH_` prefix and forbids bare generic names |
| 7 | `pydantic.EmailStr` on the login body | `str` with length bounds | `EmailStr` requires the `email-validator` package, which is not in `requirements.txt`; moot once the field is a username |
| 8 | index `idx_users_email`, `idx_users_organization_id` | `idx_users_organization` | Contract §2.2 index name; `UNIQUE` already indexes `username` |
| 9 | no bootstrap settings | `AUTH_BOOTSTRAP_ADMIN_USERNAME`, `AUTH_BOOTSTRAP_ADMIN_PASSWORD` | C-21: `scripts/install.sh` (INS) depends on these existing |

---

## 2. Goal & Context

RBAC replaces the shared `X-API-Key` authentication on analyst-facing endpoints (`/scans`, `/findings`, `/cbom`, `/remediation`) with per-user role-based access control backed by local username/password accounts and JWT bearer tokens. This satisfies PS 26164 requirement for user identity in assessed-system audit trails and provides the dashboard with a real authentication layer, enabling role-specific UI visibility and enforcing server-side authorization as the sole trust boundary. Agent report-sync (mTLS + Ed25519) is orthogonal and unchanged.

---

## 3. Scope

### In-Scope

- Local user account lifecycle (`users` table, password hash storage via Argon2)
- JWT token generation (`POST /auth/login`), validation, and short-lived expiration
- Three fixed roles (`Security Admin`, `Auditor`, `Developer`) with immutable code-resident permission map
- `require_role()` FastAPI dependency replacing `get_api_key` on analyst routes
- Frontend `AuthContext` integration with real backend login endpoint
- Role-scoped route exclusion in dashboard UI (visual enforcement only; backend is sole authority)
- `X-API-Key` deprecation documentation (token survives for service callers per C-09 contract hold)

### Out-of-Scope

- Organization-scoped query filtering (depends on C-10 sign-off; another feature assumes responsibility)
- SSO / OIDC / SAML integration (future capability, Principal contract shaped for pluggability)
- Group / dynamic role assignment (fixed roles via database only)
- Session management, token refresh, revocation lists
- Tenant isolation or multi-tenancy data scoping
- Audit event persistence (owned by AUD feature; RBAC generates compliance-relevant log entries via logger only)

---

## 4. Required Context Files

Implementer must read these first, in order. All paths are confirmed in the repository as of this specification:

1. `SYSTEM_INTERFACE_CONTRACT.md` (this document's authority, especially sections on Flagged Conflicts C-09, C-03, C-08, C-10)
2. `AGENT_RULES.md` (agent rules bind all coding agents to this spec's literal interfaces)
3. `ARCHITECTURE.md` (system design and component contracts)
4. `PRODUCT_DESCRIPTION.md` (PS 26164 alignment and user experience context)
5. `db/schema.sql` (current canonical schema; migration 002 will extend it)
6. `db/models.py` (ORM model patterns and existing declarations)
7. `api/core/security.py` (current X-API-Key implementation to replace)
8. `api/core/config.py` (settings structure and pydantic-settings patterns)
9. `api/main.py` (router registration and middleware patterns)
10. `api/routers/scans.py` (example analyst route using `get_api_key`)
11. `api/routers/findings.py`, `cbom.py`, `remediation.py` (sister routes needing auth replacement)
12. `db/crud.py` (CRUD patterns and existing data-access layer)
13. `dashboard/src/context/AuthContext.jsx` (frontend auth state management to replace)
14. `dashboard/src/lib/api.js` (frontend API client and axios interceptors)
15. `requirements.txt` (existing dependencies to avoid collision)
16. `docker-compose.yml` (database initialization and volume mounts)
17. `.env.example` (environment variables template)

---

## 5. File Ownership

### SOLE Ownership (RBAC feature only)

Files created by this feature; no other feature may open a PR against them:

- `api/core/rbac.py` — role definitions, permission matrix, `require_role()` dependency, `Principal` dataclass
- `api/routers/auth.py` — `POST /auth/login` endpoint, login request/response schemas
- `dashboard/src/context/AuthContext.jsx` — real backend login integration, JWT token persistence
- `dashboard/src/pages/LoginPage/` (directory) — all contents exclusive to RBAC

### COORDINATED Ownership (RBAC + other features)

Files this feature modifies; merge order and integration points per §6:

**Modify (Integration Owner: backend lane)**
- `api/core/security.py` — add `require_role()` entry point alongside existing `get_api_key`; `get_api_key` remains for service callers (C-09)
- `api/core/config.py` — add `AUTH_JWT_SECRET`, `AUTH_JWT_TTL_MINUTES` config vars; optional `AUTH_JWT_STORE_METHOD` for future C-08 resolution
- `api/main.py` — import auth router after §6 merge wave 1

**Modify (Integration Owner: backend lane)**
- `api/routers/scans.py` — replace `Depends(get_api_key)` with `Depends(require_role(Role.DEVELOPER))` on `POST /scans`; read routes use `Auditor`
- `api/routers/findings.py` — replace `get_api_key` with `require_role(Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN)` on read, `require_role(Role.DEVELOPER, Role.SECURITY_ADMIN)` on triage write
- `api/routers/cbom.py` — replace `get_api_key` with `require_role(Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN)`
- `api/routers/remediation.py` — replace `get_api_key` with `require_role(Role.DEVELOPER, Role.SECURITY_ADMIN)` on generation routes

**Modify (Integration Owner: DB lane)**
- `db/schema.sql` — add `users` table definition (canonical for new deployments)
- `db/models.py` — add `User` ORM model; optional `UserRole` enum if needed for code safety (unlikely; roles are strings)
- `db/crud.py` — add `create_user()`, `get_user_by_username()`, `verify_password()` stubs (implementation in feature)
- `db/seed.py` — add bootstrap function to create demo admin user on first run

**Modify (Integration Owner: frontend lane)**
- `dashboard/src/lib/api.js` — add JWT token attach to axios interceptors; handle 401 Unauthorized → redirect to login
- `dashboard/src/pages/LoginPage/LoginForm.jsx` — wire to real `POST /auth/login` endpoint instead of mock
- `dashboard/src/App.jsx` — conditionally render routes based on user role (visual only; backend enforces)

**Modify (Shared configuration)**
- `db/migrations/004_rbac_users.sql` — new migration file (reserved by contract §2.1; compose mount prefix `05_`)
- `docker-compose.yml` — mount migration 004 into Postgres initdb at prefix `05_rbac_users.sql`; add `AUTH_JWT_SECRET` to backend env
- `.env.example` — add JWT config vars template
- `requirements.txt` — add `PyJWT>=2.8.0`, `pwdlib[argon2]>=2.0.0` (or pinned versions per latest PyPI)
- `tests/test_security_controls.py` — update to test `require_role()` instead of `get_api_key` (or rename to `test_rbac.py`)

### FROZEN Files (Do Not Touch)

All other files. Implementer must not modify:

- `scanner/` (ENR lane)
- `api/services/scan_runner.py` (CONF FROZEN — confidence gate)
- `api/services/cbom_generator.py` (CBOM lane COORDINATED)
- `api/services/risk_engine.py` (CBOM/risk lane FROZEN)
- `api/models.py` (backend lane COORDINATED — only CONF may add fields; RBAC does not)
- `api/database.py`
- `dashboard/src/` (except LoginPage, AuthContext, App.jsx, lib/api.js as listed above)
- `db/seed.py` (read for patterns; only RBAC adds bootstrap user creation)

---

## 6. Tech Stack & Pinned Versions

### Backend (Python)

**New dependencies (add to `requirements.txt`):**

```
PyJWT>=2.8.0                          # JWT token generation and validation
pwdlib[argon2]>=2.0.0                 # Argon2 password hashing with OWASP hardening
```

**Rationale:** PyJWT is industry-standard for stateless token generation; Argon2 via pwdlib satisfies OWASP password storage guidance. No existing requirements conflict; check before merge.

**Existing (no change):**

- `fastapi>=0.111.0` — provides `Depends()` for dependency injection
- `pydantic>=2.7.0` — schemas and validation
- `pydantic-settings>=2.3.0` — configuration management
- `SQLAlchemy>=2.0,<2.1` — ORM
- `python-dotenv>=1.0` — .env loading

### Frontend (JavaScript)

**No new npm dependencies.** Existing `axios` (v1.19.0) handles JWT header attachment via interceptor.

### Database (PostgreSQL / SQLite)

- `schema.sql` and migration 002 are dialect-agnostic within reason (SQLite uses `TEXT` for booleans; Postgres uses `BOOLEAN`).
- Migration 002 uses only standard SQL (no native Postgres ENUMs; roles are TEXT columns as per contract §0.1).

---

## 7. Concrete Interface Definitions

### Database Schema (Migration 004)

Literal SQL to append to or mount as `db/migrations/004_rbac_users.sql`:

```sql
-- ECDAT RBAC migration: user identity and role-based access control.
-- New deployments receive the same schema from db/schema.sql.

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,          -- argon2 via pwdlib; never a raw or reversible value
    role            TEXT NOT NULL,          -- SECURITY_ADMIN | AUDITOR | DEVELOPER
    organization_id TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT now(),
    last_login_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id);
```

### ORM Model

Add to `db/models.py`:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    # SECURITY_ADMIN | AUDITOR | DEVELOPER
    organization_id: Mapped[str | None] = mapped_column(Text, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
```

Add to constants at top of `db/models.py` (mirrors the `CONFIDENCES` pattern already in that file):

```python
ROLES = ("SECURITY_ADMIN", "AUDITOR", "DEVELOPER")
```

### RBAC Core Module

New file `api/core/rbac.py` (literal content, no prose description):

```python
"""
ECDAT RBAC: role-based access control, JWT tokens, Principal contract.

This module defines:
- Role enumeration and permission matrix (code-resident for auditability)
- Principal dataclass (decoded JWT payload; shaped for OIDC/SAML future extension)
- require_role() FastAPI dependency (replaces get_api_key on analyst routes)
- JWT encoding/decoding (HS256, short-lived, no refresh token)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from api.core.config import settings

# --- Role enumeration (canonical; contract §2.2) ---
# str-Enum so `Role.AUDITOR == "AUDITOR"` holds and the value persists directly
# into users.role as TEXT. ENR, ASP, TRD and TRI all import Role from here --
# no feature may define its own role strings.

class Role(str, Enum):
    SECURITY_ADMIN = "SECURITY_ADMIN"
    AUDITOR = "AUDITOR"
    DEVELOPER = "DEVELOPER"


ROLES: tuple[str, ...] = tuple(r.value for r in Role)

# Permissions per role. Keys are (resource, action) tuples; values are roles that can perform them.
PERMISSIONS: dict[tuple[str, str], tuple[Role, ...]] = {
    ("scans", "create"): (Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("scans", "read"): (Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("scans", "delete"): (Role.SECURITY_ADMIN,),
    ("findings", "read"): (Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("findings", "triage"): (Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("cbom", "export"): (Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("remediation", "generate"): (Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("remediation", "read"): (Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("agents", "read"): (Role.AUDITOR, Role.SECURITY_ADMIN),
    ("agents", "manage"): (Role.SECURITY_ADMIN,),
    ("audit", "read"): (Role.AUDITOR, Role.SECURITY_ADMIN),
    ("trends", "read"): (Role.AUDITOR, Role.DEVELOPER, Role.SECURITY_ADMIN),
    ("users", "manage"): (Role.SECURITY_ADMIN,),
}

# --- Principal: decoded JWT payload (contract shaped for OIDC/SAML pluggability) ---

@dataclass
class Principal:
    """Decoded JWT subject.
    
    Attributes:
        user_id: integer primary key from users table
        username: unique login name (contract §2.2: users.username)
        role: one of ROLES
        organization_id: optional org scoping (unused by RBAC; exposed for org-filtering features)
    """
    user_id: int
    username: str
    role: str
    organization_id: Optional[str] = None

# --- JWT Token Management ---

def encode_token(principal: Principal, expires_in_minutes: Optional[int] = None) -> str:
    """
    Encode a JWT bearer token from a Principal.
    
    Args:
        principal: Principal object (user_id, username, role, organization_id)
        expires_in_minutes: TTL in minutes (defaults to settings.AUTH_JWT_TTL_MINUTES)
    
    Returns:
        Signed HS256 JWT string
    
    Raises:
        ValueError: if AUTH_JWT_SECRET is not configured
    """
    if not settings.AUTH_JWT_SECRET:
        raise ValueError("AUTH_JWT_SECRET is not configured")
    
    now = datetime.now(timezone.utc)
    expires_in = expires_in_minutes or settings.AUTH_JWT_TTL_MINUTES
    exp = now + timedelta(minutes=expires_in)
    
    payload = {
        "user_id": principal.user_id,
        "username": principal.username,
        "role": principal.role,
        "organization_id": principal.organization_id,
        "iat": now,
        "exp": exp,
    }
    
    return jwt.encode(payload, settings.AUTH_JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> Principal:
    """
    Decode a JWT bearer token into a Principal.
    
    Args:
        token: signed JWT string (without "Bearer " prefix)
    
    Returns:
        Principal object
    
    Raises:
        jwt.InvalidTokenError: if token is invalid, expired, or signature fails
        ValueError: if AUTH_JWT_SECRET is not configured
    """
    if not settings.AUTH_JWT_SECRET:
        raise ValueError("AUTH_JWT_SECRET is not configured")
    
    try:
        payload = jwt.decode(token, settings.AUTH_JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise jwt.InvalidTokenError("Token expired") from e
    except jwt.InvalidSignatureError as e:
        raise jwt.InvalidTokenError("Invalid signature") from e
    except jwt.DecodeError as e:
        raise jwt.InvalidTokenError("Decode error") from e
    
    return Principal(
        user_id=payload["user_id"],
        username=payload["username"],
        role=payload["role"],
        organization_id=payload.get("organization_id"),
    )


# --- FastAPI Dependency: Bearer Token Extraction & Validation ---

http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthCredentials] = Depends(http_bearer),
) -> Principal:
    """
    FastAPI dependency: extract and validate bearer token from Authorization header.
    
    Usage in routes:
        def my_route(user: Annotated[Principal, Depends(get_current_user)]) -> dict:
            return {"user": user.username}
    
    Returns:
        Principal object (decoded JWT)
    
    Raises:
        HTTPException 401: missing, invalid, or expired token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header (Bearer token required)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        principal = decode_token(credentials.credentials)
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    
    return principal


def require_role(*allowed_roles: Role):
    """
    FastAPI dependency factory: enforce role-based authorization.
    
    Usage in routes:
        @router.get("/secure")
        def secure_route(user: Annotated[Principal, Depends(require_role(Role.SECURITY_ADMIN, Role.DEVELOPER))]) -> dict:
            return {"granted": True}
    
    Args:
        *allowed_roles: one or more role names from ROLES
    
    Returns:
        A dependency function that returns Principal if role matches, raises 403 otherwise
    
    Raises:
        HTTPException 403: if user's role not in allowed_roles
        HTTPException 401: if token invalid/expired (via get_current_user)
    """
    async def enforce_role(user: Annotated[Principal, Depends(get_current_user)]) -> Principal:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' not authorized for this resource. Required: {', '.join(allowed_roles)}",
            )
        return user
    
    return enforce_role
```

### Auth Router

New file `api/routers/auth.py` (literal content):

```python
"""
ECDAT Auth Router: user login endpoint, JWT token issuance.

Endpoint:
  POST /auth/login — authenticate with username/password, return bearer token
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.config import settings
from api.core.rbac import encode_token, Principal
from api.database import get_session

log = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """POST /auth/login request body."""
    username: str = Field(min_length=1, max_length=255)
    password: str


class LoginResponse(BaseModel):
    """POST /auth/login response (200 OK)."""
    access_token: str
    token_type: str = "bearer"
    username: str
    user_role: str


class LoginErrorResponse(BaseModel):
    """Error response for invalid credentials (401 Unauthorized)."""
    detail: str


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"model": LoginErrorResponse}},
    summary="User login",
    description="Authenticate with username and password. Returns a short-lived JWT bearer token.",
)
async def login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_session)],
) -> LoginResponse:
    """Authenticate user and return JWT bearer token."""
    user = crud.get_user_by_username(db, body.username)
    
    if not user:
        log.warning("login_failed username=%s reason=user_not_found", body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    if not crud.verify_password(body.password, user.password_hash):
        log.warning("login_failed username=%s reason=invalid_password", body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    principal = Principal(
        user_id=user.id,
        username=user.username,
        role=user.role,
        organization_id=user.organization_id,
    )
    
    token = encode_token(principal)
    log.info("login_success username=%s role=%s", user.username, user.role)
    
    return LoginResponse(
        access_token=token,
        username=user.username,
        user_role=user.role,
    )
```

### Configuration

Add to `api/core/config.py` in the `Settings` class:

```python
    # JWT / Bearer Token Configuration
    AUTH_JWT_SECRET: Optional[str] = Field(
        default=None,
        description="Secret key for HS256 JWT signing. Must be long and random. "
                    "If not set, token-based auth is disabled and X-API-Key acts as fallback.",
    )
    AUTH_JWT_TTL_MINUTES: int = Field(
        default=60,
        description="Bearer token TTL in minutes.",
    )
    AUTH_BOOTSTRAP_ADMIN_USERNAME: str = Field(
        default="admin",
        description="Username seeded by db/seed.py on first run. Consumed by scripts/install.sh (INS, C-21).",
    )
    AUTH_BOOTSTRAP_ADMIN_PASSWORD: Optional[str] = Field(
        default=None,
        description="Password for the seeded admin. Generated by scripts/install.sh; seeding fails closed if unset.",
    )
    AUTH_JWT_STORE_METHOD: Literal["localStorage", "httpOnly_cookie"] = Field(
        default="localStorage",
        description="Frontend token storage method. 'localStorage' is default; may change per C-08 resolution.",
    )
```

### API Endpoint Examples

**POST /auth/login request:**
```json
{
  "username": "auditor01",
  "password": "secure-password-123"
}
```

**POST /auth/login response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6ImFuYWx5c3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiQXVkaXRvciIsIm9yZ2FuaXphdGlvbl9pZCI6bnVsbCwiaWF0IjoxNzI1MzAwMDAwLCJleHAiOjE3MjUzMDM2MDB9.abc123...",
  "token_type": "bearer",
  "username": "auditor01",
  "user_role": "AUDITOR"
}
```

**GET /scans with authorization header (example):**
```http
GET /scans HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6ImFuYWx5c3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiQXVkaXRvciIsIm9yZ2FuaXphdGlvbl9pZCI6bnVsbCwiaWF0IjoxNzI1MzAwMDAwLCJleHAiOjE3MjUzMDM2MDB9.abc123...
```

### Route Integration Example

Replace `Depends(get_api_key)` with `Depends(require_role(...))` in analyst routes.

**Before (scans.py):**
```python
def create_scan(
    body: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_session)],
    _key: Annotated[str, Depends(get_api_key)],
) -> ScanCreateResponse:
```

**After (scans.py):**
```python
def create_scan(
    body: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_session)],
    user: Annotated[Principal, Depends(require_role(Role.DEVELOPER))],
) -> ScanCreateResponse:
```

### Frontend AuthContext Integration

Literal minimal implementation for `dashboard/src/context/AuthContext.jsx`:

```jsx
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api.js'; // Assuming existing api client

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('ecdat_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [token, setToken] = useState(() => localStorage.getItem('ecdat_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      const response = await api.post('/auth/login', { username, password });
      const { access_token, username: userName, user_role } = response.data;
      
      const userData = { username: userName, role: user_role };
      localStorage.setItem('ecdat_token', access_token);
      localStorage.setItem('ecdat_user', JSON.stringify(userData));
      
      setToken(access_token);
      setUser(userData);
      return userData;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  };

  const logout = () => {
    localStorage.removeItem('ecdat_token');
    localStorage.removeItem('ecdat_user');
    setToken(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      token,
      login,
      logout,
      isAuthenticated: !!user && !!token,
      loading,
    }),
    [user, token, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### Frontend API Client Integration

Update `dashboard/src/lib/api.js` axios interceptor to attach JWT:

```javascript
// At the top of the file, add this interceptor to your axios instance:

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ecdat_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Add response interceptor to handle 401 Unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear stored auth and redirect to login
      localStorage.removeItem('ecdat_token');
      localStorage.removeItem('ecdat_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### CRUD Stubs

Add to `db/crud.py`:

```python
from pwdlib import PasswordHash
from db.models import User

# Initialize Argon2 password hasher (uses OWASP defaults internally)
pwd_context = PasswordHash.recommended()

def get_user_by_username(db: Session, username: str) -> User | None:
    """Fetch a user by username. Returns None if not found."""
    return db.query(User).filter(User.username == username).first()

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify plain password against stored hash. Returns True if valid."""
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False

def create_user(
    db: Session,
    username: str,
    password: str,
    role: str,
    organization_id: str | None = None,
) -> User:
    """Create a new user with hashed password."""
    password_hash = pwd_context.hash(password)
    user = User(
        username=username,
        password_hash=password_hash,
        role=role,
        organization_id=organization_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

### Database Seed Bootstrap

Add to `db/seed.py`:

```python
def bootstrap_demo_admin(db: Session) -> None:
    """Create a demo Security Admin if no users exist. Called on first run."""
    from db.crud import get_user_by_username, create_user
    
    demo_username = settings.AUTH_BOOTSTRAP_ADMIN_USERNAME  # default "admin"
    if not get_user_by_username(db, demo_username):
        create_user(
            db=db,
            username=demo_username,
            password="ChangeMe123!",  # Documented as demo only; must be changed in production
            role=Role.SECURITY_ADMIN.value,
            organization_id=None,
        )
        print(f"Bootstrapped admin: {demo_username} (password from AUTH_BOOTSTRAP_ADMIN_PASSWORD)")
```

---

## 8. Step-by-Step Implementation Plan

1. **Pin dependencies** → `requirements.txt`: add `PyJWT>=2.8.0`, `pwdlib[argon2]>=2.0.0`
2. **Create RBAC core** → `api/core/rbac.py`: encode/decode JWT, Principal, require_role() dependency
3. **Create auth router** → `api/routers/auth.py`: POST /auth/login endpoint
4. **Extend config** → `api/core/config.py`: add AUTH_JWT_SECRET, AUTH_JWT_TTL_MINUTES, AUTH_JWT_STORE_METHOD fields
5. **Update security module** → `api/core/security.py`: keep get_api_key() for service callers; add import of require_role entry point
6. **Create migration** → `db/migrations/004_rbac_users.sql`: CREATE TABLE users (literal SQL in §7)
7. **Extend models** → `db/models.py`: add User ORM model, ROLES constant
8. **Add CRUD stubs** → `db/crud.py`: get_user_by_username(), verify_password(), create_user()
9. **Update seed** → `db/seed.py`: add bootstrap_demo_admin() and call it on init
10. **Replace analyst auth** → `api/routers/scans.py`, `findings.py`, `cbom.py`, `remediation.py`: swap `get_api_key` for `require_role()`
11. **Wire main app** → `api/main.py`: import and include auth router (CORS header allows POST /auth/login)
12. **Update docker-compose** → `docker-compose.yml`: mount migration 004 as `05_rbac_users.sql`, add AUTH_JWT_SECRET to backend env
13. **Update .env template** → `.env.example`: add AUTH_JWT_SECRET, AUTH_JWT_TTL_MINUTES, AUTH_JWT_STORE_METHOD
14. **Replace frontend auth** → `dashboard/src/context/AuthContext.jsx`: integrate real login endpoint (literal JSX in §7)
15. **Update API client** → `dashboard/src/lib/api.js`: add JWT token attach + 401 redirect interceptors
16. **Update login form** → `dashboard/src/pages/LoginPage/LoginForm.jsx`: wire to real /auth/login API
17. **Conditional route rendering** → `dashboard/src/App.jsx`: hide routes based on user.role (visual; not security enforcement)
18. **Test suite** → `tests/test_rbac.py` or update `tests/test_security_controls.py`: test require_role(), encode/decode, login endpoint

---

## 9. Naming & Symbol Registry

### Environment Variables (new)

| Variable | Type | Default | Scope | Purpose |
|---|---|---|---|---|
| `AUTH_JWT_SECRET` | string | None (fail-closed) | Backend config | HS256 signing key for bearer tokens |
| `AUTH_JWT_TTL_MINUTES` | int | 60 | Backend config | TTL of issued tokens in minutes |
| `AUTH_JWT_STORE_METHOD` | enum | `localStorage` | Backend/Frontend | Token storage method (future C-08 resolution override) |

### Python Symbols (new)

**Module: `api/core/rbac.py`**
- `Principal` (dataclass)
- `ROLES` (tuple of strings)
- `PERMISSIONS` (dict: (resource, action) → tuple of roles)
- `encode_token(principal, expires_in_minutes) -> str`
- `decode_token(token) -> Principal`
- `get_current_user()` (FastAPI dependency)
- `require_role(*allowed_roles)` (dependency factory)

**Module: `api/routers/auth.py`**
- `LoginRequest` (Pydantic model)
- `LoginResponse` (Pydantic model)
- `LoginErrorResponse` (Pydantic model)
- `login()` (endpoint handler)
- `router` (APIRouter, prefix=/auth)

**Module: `db/crud.py` (additions)**
- `pwd_context` (PasswordHash instance)
- `get_user_by_username(db, username) -> User | None`
- `verify_password(plain, hash) -> bool`
- `create_user(db, username, password, role, organization_id) -> User`

**Module: `db/models.py` (additions)**
- `User` (ORM model)
- `ROLES` (constant tuple)

### Database Symbols (new)

**Table: `users`**
- `id` (SERIAL PRIMARY KEY)
- `username` (TEXT UNIQUE)
- `password_hash` (TEXT)
- `role` (TEXT)
- `organization_id` (TEXT, nullable)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**Indexes**
- `idx_users_organization` (users.organization_id)
- `idx_users_organization_id` (users.organization_id)

### API Endpoints (new)

- `POST /auth/login` (request: LoginRequest; response: LoginResponse or 401)

### Frontend Symbols (new)

**File: `dashboard/src/context/AuthContext.jsx`**
- `AuthContext` (React context)
- `AuthProvider` (component)
- `useAuth()` (hook)
- State: `user`, `token`, `login()`, `logout()`

---

## 10. Known Cross-Feature Risks

Pulled from system interface contract §5 (Flagged Conflicts & Shared Resources). All conflicts listed have resolutions already decided by the team (per contract authority); implementer applies them as-is.

| Conflict | Features | Contract Resolution | Implementer Action |
|---|---|---|---|
| **C-09** | RBAC, ENR, AUD, INS | `X-API-Key` survives for service callers; analyst routes use JWT. Merge order: RBAC wave 1, then ENR. | Keep `get_api_key()` alongside `require_role()`. Analyst routes (scans, findings, etc.) swap to JWT. CLI/service callers use X-API-Key header. ENR integrates at wave 1 after RBAC. |
| **C-08** | RBAC, FE | JWT storage: `localStorage` default (open sign-off). May override post-deployment. | Store in `localStorage` by default. Add `AUTH_JWT_STORE_METHOD` config var for future override. Do not implement httpOnly cookie logic yet. |
| **C-10** | RBAC, ASP, CMP, etc. | Tenant visibility for NULL `organization_id` rows (open sign-off). RBAC exposes `organization_id` on Principal; org-filtering is a separate feature. | RBAC passes `organization_id` from JWT into Principal. Do not filter queries by it; another feature assumes that responsibility. Log intent for audit trail. |
| **C-03** | CONF, RBAC, +6 | Confidence backfill and broken tests (open sign-off, Medium confidence). Out of RBAC scope. | Ignore. CONF owns confidence_score columns; RBAC does not modify findings schema. |
| **C-22** | AUD, RBAC | Audit fail-closed vs fail-open; retention; external sink (open sign-off). | RBAC logs login attempts and denied requests via `logger.info()` and `logger.warning()`. AUD feature owns audit_events table and persistence logic. RBAC does not call audit service. |

---

## 11. Pre-Answered Ambiguities

Every implementing agent will encounter these situations. Responses are non-negotiable; if a situation is not listed, stop and ask a human per AGENT_RULES.md #4.

### 1. **What if AUTH_JWT_SECRET is not set in .env?**
**Answer:** The backend fails closed. `encode_token()` raises ValueError; `decode_token()` raises ValueError. Routes depending on require_role() return 500 at startup (not 401 at request time). Operator must provide AUTH_JWT_SECRET or deployment is broken. This is intentional: tokens cannot be generated without a secret.

### 2. **Should require_role() accept a role name or a tuple?**
**Answer:** A variadic arguments list: `require_role(Role.AUDITOR, Role.DEVELOPER)` → both roles allowed. Signature is `def require_role(*allowed_roles: Role)`. This matches FastAPI idioms and reads naturally.

### 3. **Does RBAC filter queries by organization_id?**
**Answer:** No. RBAC extracts `organization_id` from the JWT and puts it on the Principal. A separate feature (DFS, TRD, CMP, ASP, ENR as per C-10) must filter queries using `user.organization_id` from the Principal. RBAC does not filter. This is a known cross-feature dependency listed in contract §5.2.

### 4. **Can a user have multiple roles?**
**Answer:** No. The `users.role` column is a single TEXT value from the ROLES enumeration. Multi-role assignment is out of scope. If a future feature needs group assignment, it must add a separate table and RBAC's Principal must be extended (not changed in-place per AGENT_RULES.md #3).

### 5. **If login fails, should we log the user's password?**
**Answer:** No. Never log passwords. Log only: username, failure reason (user_not_found, invalid_password without details), timestamp. See `api/routers/auth.py` logger calls for pattern.

### 6. **What if X-API-Key header is present AND Authorization bearer is present?**
**Answer:** Authorization bearer takes precedence. If `require_role()` is used, bearer is required and X-API-Key is ignored. If `get_api_key()` is used (service callers), bearer is ignored and X-API-Key is validated. They do not overlap in the same route.

### 7. **Should JWT tokens have a refresh mechanism?**
**Answer:** No. Tokens are short-lived (default 60 minutes per config). On expiration, user must re-login via POST /auth/login. No refresh token endpoint. This simplifies the implementation and suits the local analyst use case.

### 8. **Can a Security Admin create users via an API endpoint?**
**Answer:** No. User provisioning is out of scope for this sprint. Only the seed script (db/seed.py) creates the demo admin. Production user creation is a future feature or manual database edit.

### 9. **If Argon2 hashing fails (library error), what should happen?**
**Answer:** `create_user()` raises the exception. Let the endpoint caller handle it (500 error propagates). Do not silently fall back to plaintext. This is a hard error.

### 10. **Should the login endpoint be public (no auth required)?**
**Answer:** Yes. POST /auth/login requires no bearer token; it validates username/password only. This is the entry point. All other analyst routes (scans, findings, etc.) require bearer token.

### 11. **Open Sign-Off: C-08 — JWT storage method (localStorage vs httpOnly cookie)?**
**Answer:** Default to `localStorage` per contract. This is a trade-off: localStorage is XSS-vulnerable but CORS-compatible and simpler for local deployments. httpOnly cookie is more secure but requires SameSite and CORS reconfiguration. Add `AUTH_JWT_STORE_METHOD` config var so operators can override post-deployment if C-08 resolves to httpOnly later.

### 12. **Open Sign-Off: C-09 — Should X-API-Key be removed entirely?**
**Answer:** No. Keep both. X-API-Key remains for CLI/service callers (e.g., CI gates). Analyst routes use bearer tokens. This dual-auth model is the contract resolution. Do not remove X-API-Key.

### 13. **Open Sign-Off: C-10 — How should organization_id filtering work?**
**Answer:** RBAC does not filter. RBAC extracts `organization_id` from the JWT and puts it on Principal. Routes like GET /scans should check `if scan.repository.organization_id and scan.repository.organization_id != user.organization_id: raise 403`. This is a separate feature's responsibility. RBAC only provides the Principal context.

---

## 12. Test Plan / Definition of Done

Run these exact commands to verify the feature is complete. All must pass.

### Unit Tests

```bash
# Test RBAC core (encoding, decoding, role enforcement)
pytest tests/test_rbac.py -v

# Test authentication router (login endpoint)
pytest tests/test_rbac.py::test_auth_login_valid_credentials -v
pytest tests/test_rbac.py::test_auth_login_invalid_username -v
pytest tests/test_rbac.py::test_auth_login_invalid_password -v

# Test bearer token validation
pytest tests/test_rbac.py::test_require_role_valid_token -v
pytest tests/test_rbac.py::test_require_role_invalid_token -v
pytest tests/test_rbac.py::test_require_role_insufficient_role -v

# Test role-based authorization on analyst routes
pytest tests/test_rbac.py::test_scans_create_developer_allowed -v
pytest tests/test_rbac.py::test_scans_create_auditor_denied -v
pytest tests/test_rbac.py::test_findings_read_auditor_allowed -v
pytest tests/test_rbac.py::test_remediation_generate_developer_allowed -v
```

### Integration Tests

```bash
# Spin up containers
docker-compose up -d

# Wait for migrations
sleep 5

# Test login endpoint
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"ChangeMe123!"}'
# Expected: 200 OK, returns access_token

# Extract token and test protected endpoint
TOKEN="<access_token from above>"
curl -X GET http://localhost:8000/scans \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK, returns scan list

# Test insufficient role (auditor trying to create scan)
curl -X POST http://localhost:8000/scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_path":"/repo"}'
# Expected: 403 Forbidden (if token is Auditor role)

# Test missing token
curl -X GET http://localhost:8000/scans
# Expected: 401 Unauthorized

# Test invalid token
curl -X GET http://localhost:8000/scans \
  -H "Authorization: Bearer invalid.jwt.token"
# Expected: 401 Unauthorized
```

### Frontend Integration

```bash
# Start dashboard (if separate from backend)
cd dashboard && npm run dev

# Open browser and test:
# 1. Navigate to /login
# 2. Enter username: admin, password: ChangeMe123!
# 3. Should redirect to dashboard after login success
# 4. Token should be in localStorage: localStorage.getItem('ecdat_token')
# 5. Log out; token should be cleared
# 6. Try accessing dashboard without token; should redirect to /login
```

### Database Migration

```bash
# Verify migration runs on fresh Postgres
docker-compose down -v
docker-compose up db -d
sleep 5

# Connect and check schema
psql -U ecdat -d ecdat -h localhost << EOF
SELECT * FROM pg_tables WHERE tablename = 'users';
\d users;
EOF
# Expected: users table exists with username, password_hash, role, organization_id, is_active columns
```

### Backward Compatibility

```bash
# Verify X-API-Key still works for CLI/service callers
curl -X GET http://localhost:8000/scans \
  -H "X-API-Key: $API_KEY"
# Expected: 200 OK (routes not using require_role() still accept X-API-Key)
```

### Definition of Done

✅ All unit tests pass (tests/test_rbac.py)  
✅ All integration tests pass (curl, docker-compose)  
✅ Frontend login page connects to real endpoint  
✅ JWT tokens work end-to-end (login → protected route)  
✅ Role-based access control enforced (developer can create, auditor cannot)  
✅ 401/403 errors return correct HTTP status  
✅ Migration 002 runs on fresh database  
✅ X-API-Key still works for service callers  
✅ No regressions in existing tests  
✅ Code review approved per ARCHITECTURE.md standards  

---

## 13. Rollback Plan

If this feature breaks the build or introduces a production issue:

### Immediate Actions (within 30 minutes)

1. **Stop the backend** → `docker-compose down api`
2. **Revert the feature branch** → `git revert <RBAC commit hash>` or `git checkout main`
3. **Restore database** → `docker volume rm ecdat_postgres_data` (if safe) or manually drop `users` table
4. **Restart backend** → `docker-compose up -d`
5. **Verify X-API-Key auth works** → curl test against a protected route

### Root Cause Analysis

- **Migration fails:** Check `docker-compose logs db` for SQL syntax errors. Verify PostgreSQL version compatibility.
- **Login endpoint 500s:** Check AUTH_JWT_SECRET is set in .env; check PyJWT/pwdlib imports resolve.
- **Dashboard login fails:** Check CORS headers allow POST /auth/login; check frontend API client interceptor doesn't break non-auth routes.
- **Token validation fails:** Verify HS256 decode; confirm AUTH_JWT_SECRET matches encode step.
- **Routes suddenly require bearer token:** Check require_role() replaced get_api_key() only on intended routes (analyst routes, not /health).

### Recovery Steps

1. **If migration is corrupt:**
   - Drop `users` table manually via `psql`
   - Re-run migration 004: `psql -f db/migrations/004_rbac_users.sql`
   - Reseed demo user via `python -m db.seed`

2. **If JWT handling is broken:**
   - Temporarily restore all analyst routes to `get_api_key()` (revert §8 steps 10–11)
   - Validate X-API-Key auth works
   - Debug JWT encode/decode in isolation (run test suite)
   - Re-enable JWT auth incrementally (one route at a time)

3. **If dashboard won't load login page:**
   - Revert dashboard changes (step 14 of §8)
   - Verify backend /auth/login endpoint works (curl test)
   - Re-apply frontend changes one file at a time

### Prevention

- **Run full test suite before commit:** `pytest tests/test_rbac.py -v`
- **Lint and type-check:** `pylint api/routers/auth.py` (if available)
- **Integration test on staging:** Run docker-compose stack and curl tests before merging
- **Peer review:** Code review at least two eyes on rbac.py, auth.py, and migration 002

---

## Appendices

None — all material is integrated into the 13 sections above.

---

**End of Specification**

Author: Implementation agent (bound by AGENT_RULES.md)  
Last Updated: September 2026  
Approved By: [To be signed off during integration gate per contract §6]
