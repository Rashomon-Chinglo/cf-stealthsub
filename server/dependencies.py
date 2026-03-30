"""FastAPI dependency injection functions."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from server.config import AppConfig
from server.utils.session import validate_session


def get_config(request: Request) -> AppConfig:
    """Inject application config from app state."""
    return request.app.state.config


def get_client_ip(request: Request) -> str:
    """Extract the real client IP from request headers.

    Priority: CF-Connecting-IP → X-Forwarded-For (first) → client.host
    """
    ip = request.headers.get("CF-Connecting-IP")
    if not ip:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            ip = xff.split(",")[0].strip()
    if not ip:
        ip = request.client.host if request.client else "unknown"
    # Strip port if present (IPv4 only, not bracketed IPv6)
    if ":" in ip and not ip.startswith("["):
        parts = ip.rsplit(":", 1)
        # Only strip if the last part looks like a port number
        if parts[-1].isdigit():
            ip = parts[0]
    return ip


def require_auth(request: Request) -> str:
    """Verify session token from X-Session-Token header.

    Returns the validated token string.
    Raises 401 if missing or invalid.
    """
    token = request.headers.get("X-Session-Token", "")
    if not token or not validate_session(token):
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED"},
        )
    return token
