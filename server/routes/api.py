"""API routes — CF results CSV upload submission."""

from __future__ import annotations

import csv
import io
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from server.config import AppConfig
from server.dependencies import get_config, require_auth
from server.utils.store import get_by_session, save_yaml
from server.utils.subscription import generate_clash_yaml

router = APIRouter()


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
    results: list[IPResult] = []


@router.post("/results", response_model=PostResultsResponse)
async def post_results(
    file: UploadFile = File(...),
    session_token: str = Depends(require_auth),
    config: AppConfig = Depends(get_config),
):
    """Accept CloudflareST result.csv and generate/return a subscription."""
    # Check for cached subscription for this session
    cached = get_by_session(session_token)
    if cached:
        sub_url = f"{config.server.base_url}/sub/{cached.key}"
        return PostResultsResponse(
            key=cached.key,
            expires_at=cached.expires_at,
            is_cached=True,
            sub_url=sub_url,
            results=[],
        )

    content = await file.read()
    try:
        # XIU2/CloudflareSpeedTest usually generates UTF-8 with BOM or GBK on Windows
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("gbk")
        except Exception:
            raise HTTPException(status_code=400, detail="Cannot decode CSV format")

    reader = csv.DictReader(io.StringIO(text))
    # Expected columns: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度 (MB/s)

    results = []
    try:
        for row in reader:
            ip = row.get("IP 地址", "").strip()
            if not ip:
                continue

            try:
                latency = float(row.get("平均延迟", 0))
            except ValueError:
                latency = 999.0

            try:
                loss_str = row.get("丢包率", "0").replace("%", "")
                loss = float(loss_str) / 100.0
            except ValueError:
                loss = 1.0

            try:
                speed_mbps = float(row.get("下载速度(MB/s)", 0))
            except ValueError:
                speed_mbps = 0.0

            speed_kbps = speed_mbps * 1024

            # Simple score: prefer lower latency
            score = latency if latency > 0 else 999

            colo = row.get("地区码", "").strip()
            if not colo:
                colo = row.get("colo", "").strip()

            results.append(
                {
                    "ip": ip,
                    "avg_latency": latency,
                    "loss_rate": loss,
                    "speed_kbps": speed_kbps,
                    "score": score,
                    "colo": colo,
                }
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV Parsing Error: {str(e)}")

    if not results:
        raise HTTPException(status_code=400, detail="No valid IP records found in CSV")

    # CloudflareST already sorts by download speed, preserve this original order

    top_n = min(config.subscription.top_n, len(results), 50)
    selected = results[:top_n]

    now = int(time.time())
    duration = config.subscription.cache_duration_hours
    expires_at = now + duration * 3600

    yaml_content = generate_clash_yaml(selected, config, expires_at=expires_at)

    entry = save_yaml(
        session_id=session_token,
        yaml_content=yaml_content,
        storage_path=config.subscription.storage_path,
        duration_hours=duration,
    )

    sub_url = f"{config.server.base_url}/sub/{entry.key}"
    return PostResultsResponse(
        key=entry.key,
        expires_at=entry.expires_at,
        is_cached=False,
        sub_url=sub_url,
        results=selected,
    )
