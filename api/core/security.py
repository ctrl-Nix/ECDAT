"""
API Security Module for ECDAT.

Provides timing-safe API key validation (X-API-Key header) for protecting endpoints.
"""

import secrets
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from api.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key_header: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    Validate the X-API-Key header against configured API_KEY in a timing-safe manner.
    Allows demo/dev mode bypass if DEBUG is True or no API_KEY is set.
    """
    expected_key = settings.API_KEY

    # If in debug mode or key is default, allow request if header matches or is absent during dev
    if not expected_key:
        return "dev-mode"

    if not api_key_header:
        # Check if auth bypass is allowed in DEBUG mode
        if settings.DEBUG:
            return "debug-bypass"
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

