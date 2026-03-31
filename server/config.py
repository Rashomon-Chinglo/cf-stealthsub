"""Application configuration — Pydantic models + YAML loader."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ServerConfig(StrictModel):
    host: str = "127.0.0.1"
    port: int = 3001
    base_url: str  # required — used for subscription URL generation
    trusted_proxies: list[str] = Field(default_factory=lambda: ["127.0.0.1/32", "::1/128"])


class AuthConfig(StrictModel):
    totp_secret: str  # required — base32 encoded
    session_duration_hours: int = 24
    session_cookie_name: str = "cf_session"
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "strict"


class ProxyConfig(StrictModel):
    protocol: str = "vless"
    uuid: str  # required
    domain: str  # required — CDN domain for SNI
    port: int = 443
    path: str = "/"
    network: str = "ws"
    tls: bool = True
    door_key: Optional[str] = None


class SubscriptionConfig(StrictModel):
    top_n: int = 10
    cache_duration_hours: int = 24
    storage_path: str = "data/subscriptions"
    max_upload_size_mb: int = 5


class AppConfig(StrictModel):
    server: ServerConfig
    auth: AuthConfig
    proxy: ProxyConfig
    subscription: SubscriptionConfig = SubscriptionConfig()


def load_config() -> AppConfig:
    """Load and validate config from YAML file.

    Priority: CF_OPTIMIZER_CONFIG env var → ./config.yaml
    """
    import os

    config_path = Path(os.environ.get("CF_STEALTHSUB_CONFIG", "config.yaml"))

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        print("   Copy config.example.yaml → config.yaml and fill in your values.")
        sys.exit(1)

    try:
        with open(config_path, encoding="utf-8") as f:
            raw: object = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"❌ Failed to parse {config_path}: {e}")
        sys.exit(1)

    if not isinstance(raw, dict):
        print(f"❌ Config file must be a YAML mapping, got {type(raw).__name__}")
        sys.exit(1)

    try:
        return AppConfig(**raw)
    except ValidationError as e:
        print("❌ Config validation failed:")
        for err in e.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            print(f"   {loc}: {err['msg']}")
        sys.exit(1)
