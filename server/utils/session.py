"""In-memory session management using cryptographic tokens."""

from __future__ import annotations

import secrets
import time


# {token: expires_at_timestamp}
_sessions: dict[str, float] = {}


def create_session(duration_hours: int) -> str:
    """Create a new session with a cryptographically random token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + duration_hours * 3600
    return token


def validate_session(token: str) -> bool:
    """Check if a session token is valid and not expired."""
    expires_at = _sessions.get(token)
    if not token or expires_at is None:
        return False
    if expires_at < time.time():
        _sessions.pop(token, None)
        return False
    return True


def get_session_expiry(token: str) -> float | None:
    """Get the expiry timestamp for a session, or None if invalid."""
    exp = _sessions.get(token)
    if exp and exp > time.time():
        return exp
    if exp is not None:
        _sessions.pop(token, None)
    return None


def cleanup_expired() -> int:
    """Remove expired sessions. Returns count of removed entries."""
    now = time.time()
    expired = [k for k, v in _sessions.items() if v < now]
    for k in expired:
        del _sessions[k]
    return len(expired)
