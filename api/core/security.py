"""
API Security Module for ECDAT.

Provides timing-safe API key validation (X-API-Key header) for protecting endpoints.
"""

import secrets
from typing import Optional
from fastapi import Header, HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader

from api.core.config import settings
from api.core.rbac import require_role

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key_header: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Validate the X-API-Key header against configured API_KEY in a timing-safe manner.
    Fails closed if the service was not configured with an API key. This is a
    transitional control for local/admin endpoints; browser applications must
    use a real identity provider rather than embed this key.
    """
    expected_key = settings.API_KEY

    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        )

    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Use constant-time comparison to protect against side-channel timing attacks
    if not secrets.compare_digest(api_key_header, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or unauthorized API key",
        )

    return api_key_header


async def get_report_sync_agent(
    request: Request,
    agent_id: Optional[str] = Header(None, alias="X-ECDAT-Agent-ID"),
) -> tuple[str, str]:
    """Authenticate an enrolled scanning agent for a signed report bundle.

    A TLS terminator validates the client certificate and forwards the
    configured verification header only across the private proxy-to-API
    network. The bundle signature supplies end-to-end integrity and authentic
    agent identity. The API must not be published directly when this control is
    enabled, otherwise a client could forge the proxy header.
    """
    if not agent_id or agent_id not in settings.REPORT_SYNC_AGENT_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown report-sync agent")
    mtls_verified = request.headers.get(settings.REPORT_SYNC_MTLS_HEADER)
    if settings.REPORT_SYNC_REQUIRE_MTLS and mtls_verified != "SUCCESS":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mutual TLS verification required")
    return agent_id, settings.REPORT_SYNC_AGENT_KEYS[agent_id]

