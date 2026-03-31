"""IP-based rate limiting for authentication endpoints."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Final

from fastapi import HTTPException


@dataclass
class IPRecord:
    failures: int = 0
    blocked_until: float | None = None


# {ip: IPRecord}
_limits: dict[str, IPRecord] = {}

MAX_FAILURES: Final[int] = 5
BLOCK_DURATION_SECONDS: Final[int] = 1800


def check_rate_limit(ip: str) -> None:
    """Raise 429 if IP is currently blocked."""
    record = _limits.get(ip)
    now = time.time()
    if record and record.blocked_until and record.blocked_until > now:
        retry_after = int(record.blocked_until - now)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "TOO_MANY_ATTEMPTS",
                "retry_after": retry_after,
            },
        )


def record_failure(ip: str) -> int:
    """Record a failed auth attempt. Returns current failure count."""
    rec = _limits.setdefault(ip, IPRecord())
    rec.failures += 1
    if rec.failures >= MAX_FAILURES:
        rec.blocked_until = time.time() + BLOCK_DURATION_SECONDS
    return rec.failures


def record_success(ip: str) -> None:
    """Clear rate limit record on successful auth."""
    _limits.pop(ip, None)


def cleanup_expired() -> int:
    """Remove expired block records. Returns count removed."""
    now = time.time()
    expired = [
        k
        for k, v in _limits.items()
        if v.blocked_until and v.blocked_until < now
    ]
    for k in expired:
        del _limits[k]
    return len(expired)


def remaining_attempts(failures: int) -> int:
    """Return the remaining attempts before the next block."""
    return max(0, MAX_FAILURES - failures)
