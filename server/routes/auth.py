"""Authentication route — TOTP login → session token."""

from __future__ import annotations

import asyncio
import random

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from server.config import AppConfig
from server.dependencies import get_client_ip, get_config, require_auth
from server.middleware.rate_limit import check_rate_limit, record_failure, record_success
from server.utils.session import create_session, get_session_expiry
from server.utils.totp import verify_totp

router = APIRouter()


class LoginRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginResponse(BaseModel):
    session_token: str
    expires_in: int  # seconds
    expires_at: int  # unix timestamp


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    config: AppConfig = Depends(get_config),
):
    client_ip = get_client_ip(request)
    check_rate_limit(client_ip)

    # Random delay to prevent timing attacks
    await asyncio.sleep(random.uniform(0.3, 1.0))

    if not verify_totp(body.totp_code, config.auth.totp_secret):
        failures = record_failure(client_ip)
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_CODE",
                "remaining": max(0, 5 - failures),
            },
        )

    record_success(client_ip)
    token = create_session(config.auth.session_duration_hours)
    expires_at = get_session_expiry(token)

    return LoginResponse(
        session_token=token,
        expires_in=config.auth.session_duration_hours * 3600,
        expires_at=int(expires_at if expires_at is not None else 0),
    )

@router.get("/verify", response_model=dict)
async def verify_session(_: str = Depends(require_auth)):
    return {"valid": True}
