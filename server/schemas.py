"""Shared Pydantic schemas and typed records."""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field


class ParsedIPResult(TypedDict):
    """Normalized CloudflareST row used internally across the backend."""

    ip: str
    avg_latency: float
    loss_rate: float
    speed_kbps: float
    score: float
    colo: str


class IPResult(BaseModel):
    ip: str
    avg_latency: float
    loss_rate: float
    speed_kbps: float
    score: float
    colo: str = ""


class PostResultsResponse(BaseModel):
    key: str
    expires_at: int
    is_cached: bool
    sub_url: str
    results: list[IPResult] = Field(default_factory=list)


class LoginRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginResponse(BaseModel):
    expires_in: int
    expires_at: int


class VerifyResponse(BaseModel):
    valid: bool
