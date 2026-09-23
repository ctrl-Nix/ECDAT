"""Username/password login and JWT issuance."""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import db.crud as crud
from api.core.rbac import Principal, encode_token
from api.database import get_session

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_role: str


class LoginErrorResponse(BaseModel):
    detail: str


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"model": LoginErrorResponse}},
)
async def login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_session)],
) -> LoginResponse:
    user = crud.get_user_by_username(db, body.username)
    if user is None or not user.is_active:
        log.warning("login_failed username=%s reason=user_not_found_or_inactive", body.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not crud.verify_password(body.password, user.password_hash):
        log.warning("login_failed username=%s reason=invalid_password", body.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    principal = Principal(user.id, user.username, user.role, user.organization_id)
    token = encode_token(principal)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    log.info("login_success username=%s role=%s", user.username, user.role)
    return LoginResponse(access_token=token, username=user.username, user_role=user.role)