"""Subscription delivery route — serves YAML files by key."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from server.utils.store import get_by_key, read_yaml

router = APIRouter()


@router.get("/{key}")
async def get_subscription(key: str):
    """Serve a subscription YAML file by its key.

    No authentication required — the key itself acts as a bearer token.
    """
    entry = get_by_key(key)
    if not entry:
        raise HTTPException(status_code=404, detail="订阅链接不存在")

    if entry.expires_at < time.time():
        raise HTTPException(status_code=410, detail="订阅链接已过期，请重新运行优化器")

    yaml_content = read_yaml(entry)

    return Response(
        content=yaml_content,
        media_type="text/yaml",
        headers={
            "Content-Disposition": 'attachment; filename="cf_optimized.yaml"',
            "Profile-Update-Interval": "24",
            "Cache-Control": "no-cache",
        },
    )
