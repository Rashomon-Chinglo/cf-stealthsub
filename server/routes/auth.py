"""Authentication route — TOTP login → session token."""

from __future__ import annotations

import asyncio
import random
from typing import Final

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from server.config import AppConfig
from server.dependencies import get_client_ip, get_config, require_auth
from server.middleware.rate_limit import (
    check_rate_limit,
    record_failure,
    record_success,
    remaining_attempts,
)
from server.schemas import LoginRequest, LoginResponse, VerifyResponse
from server.utils.session import create_session, get_session_expiry
from server.utils.totp import verify_totp

router = APIRouter()

AUTH_DELAY_MIN_SECONDS: Final[float] = 0.3
AUTH_DELAY_MAX_SECONDS: Final[float] = 1.0


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    config: AppConfig = Depends(get_config),
) -> LoginResponse:
    """Authenticate a TOTP code and mint a session token."""
    client_ip = get_client_ip(request, config.server.trusted_proxies)
    session_duration_seconds = config.auth.session_duration_hours * 3600
    check_rate_limit(client_ip)

    await asyncio.sleep(random.uniform(AUTH_DELAY_MIN_SECONDS, AUTH_DELAY_MAX_SECONDS))

    if not verify_totp(body.totp_code, config.auth.totp_secret):
        failures = record_failure(client_ip)
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_CODE",
                "remaining": remaining_attempts(failures),
            },
        )

    record_success(client_ip)
    token = create_session(config.auth.session_duration_hours)
    expires_at = get_session_expiry(token)
    expires_at_timestamp = int(expires_at if expires_at is not None else 0)
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=config.auth.session_cookie_name,
        value=token,
        httponly=True,
        secure=config.auth.cookie_secure,
        samesite=config.auth.cookie_samesite,
        max_age=session_duration_seconds,
        expires=expires_at_timestamp,
        path="/",
    )

    return LoginResponse(
        expires_in=session_duration_seconds,
        expires_at=expires_at_timestamp,
    )


@router.get("/verify", response_model=VerifyResponse)
async def verify_session(
    response: Response,
    _: str = Depends(require_auth),
) -> VerifyResponse:
    """Validate the current session token."""
    response.headers["Cache-Control"] = "no-store"
    return VerifyResponse(valid=True)
