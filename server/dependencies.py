"""FastAPI dependency injection functions."""

from __future__ import annotations

import ipaddress
from collections.abc import Sequence
from typing import cast

from fastapi import HTTPException, Request

from server.config import AppConfig
from server.utils.session import validate_session


def get_config(request: Request) -> AppConfig:
    """Inject application config from app state."""
    return cast(AppConfig, request.app.state.config)


def get_client_ip(request: Request, trusted_proxies: Sequence[str]) -> str:
    """Extract the real client IP, trusting proxy headers only from trusted peers."""
    peer_ip = normalize_ip(request.client.host if request.client else "unknown")
    if not is_trusted_proxy(peer_ip, trusted_proxies):
        return peer_ip

    forwarded_ip = request.headers.get("CF-Connecting-IP")
    if not forwarded_ip:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            forwarded_ip = xff.split(",", 1)[0].strip()

    return normalize_ip(forwarded_ip or peer_ip)


def require_auth(request: Request) -> str:
    """Verify the current session from a secure cookie or fallback header.

    Returns the validated token string.
    Raises 401 if missing or invalid.
    """
    config = get_config(request)
    token = request.cookies.get(config.auth.session_cookie_name) or request.headers.get("X-Session-Token", "")
    if not token or not validate_session(token):
        raise HTTPException(
            status_code=401,
            detail={"error": "UNAUTHORIZED"},
        )
    return token


def is_trusted_proxy(peer_ip: str, trusted_proxies: Sequence[str]) -> bool:
    """Return whether the immediate peer is a trusted reverse proxy."""
    try:
        ip_obj = ipaddress.ip_address(peer_ip)
    except ValueError:
        return False

    for raw_network in trusted_proxies:
        try:
            if ip_obj in ipaddress.ip_network(raw_network, strict=False):
                return True
        except ValueError:
            continue
    return False


def normalize_ip(ip: str) -> str:
    """Normalize an IP-ish string and strip an attached IPv4 port when present."""
    if ":" in ip and not ip.startswith("["):
        parts = ip.rsplit(":", 1)
        if parts[-1].isdigit():
            ip = parts[0]
    return ip.strip()
