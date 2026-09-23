"""Role-based access control and short-lived JWT bearer tokens."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.core.config import settings


class Role(str, Enum):
    SECURITY_ADMIN = "SECURITY_ADMIN"
    AUDITOR = "AUDITOR"
    DEVELOPER = "DEVELOPER"


ROLES: tuple[str, ...] = tuple(role.value for role in Role)

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


@dataclass
class Principal:
    user_id: int
    username: str
    role: str
    organization_id: Optional[str] = None


def _secret() -> str:
    if not settings.AUTH_JWT_SECRET:
        raise ValueError("AUTH_JWT_SECRET is not configured")
    return settings.AUTH_JWT_SECRET


def encode_token(principal: Principal, expires_in_minutes: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    ttl = settings.AUTH_JWT_TTL_MINUTES if expires_in_minutes is None else expires_in_minutes
    payload = {
        "user_id": principal.user_id,
        "username": principal.username,
        "role": principal.role,
        "organization_id": principal.organization_id,
        "iat": now,
        "exp": now + timedelta(minutes=ttl),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> Principal:
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
        role = Role(payload["role"])
        return Principal(
            user_id=int(payload["user_id"]),
            username=str(payload["username"]),
            role=role.value,
            organization_id=payload.get("organization_id"),
        )
    except ValueError:
        raise
    except (KeyError, TypeError, jwt.InvalidTokenError) as exc:
        raise jwt.InvalidTokenError("Invalid token") from exc


http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
) -> Principal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header (Bearer token required)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_token(credentials.credentials)
    except (ValueError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_role(*allowed_roles: Role):
    async def enforce_role(
        user: Annotated[Principal, Depends(get_current_user)],
    ) -> Principal:
        if user.role not in {role.value for role in allowed_roles}:
            required = ", ".join(role.value for role in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{user.role}' not authorized for this resource. Required: {required}",
            )
        return user

    return enforce_role