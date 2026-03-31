"""API routes — CF results CSV upload submission."""

from __future__ import annotations

import csv
import io
import time
from collections.abc import Sequence
from typing import Final

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from server.config import AppConfig
from server.dependencies import get_config, require_auth
from server.schemas import IPResult, ParsedIPResult, PostResultsResponse
from server.utils.store import save_yaml
from server.utils.subscription import generate_clash_yaml

router = APIRouter()

IP_COLUMN: Final[str] = "IP 地址"
LATENCY_COLUMN: Final[str] = "平均延迟"
LOSS_COLUMN: Final[str] = "丢包率"
SPEED_COLUMN: Final[str] = "下载速度(MB/s)"
COLO_COLUMNS: Final[tuple[str, ...]] = ("地区码", "colo")
MAX_SUBSCRIPTION_NODES: Final[int] = 50
CSV_CHUNK_SIZE_BYTES: Final[int] = 64 * 1024
ALLOWED_CSV_CONTENT_TYPES: Final[frozenset[str]] = frozenset({
    "",
    "application/csv",
    "application/octet-stream",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
})


@router.post("/results", response_model=PostResultsResponse)
async def post_results(
    file: UploadFile = File(...),
    session_id: str = Depends(require_auth),
    config: AppConfig = Depends(get_config),
) -> PostResultsResponse:
    """Accept CloudflareST result.csv and generate/return a subscription."""
    validate_upload(file)
    file_bytes = await read_limited_upload(file, config.subscription.max_upload_size_mb)
    try:
        csv_text = decode_csv_content(file_bytes)
        parsed_results = parse_results(csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not parsed_results:
        raise HTTPException(status_code=400, detail="No valid IP records found in CSV")

    selected_count = min(config.subscription.top_n, len(parsed_results), MAX_SUBSCRIPTION_NODES)
    selected_results = parsed_results[:selected_count]

    duration = config.subscription.cache_duration_hours
    expires_at = int(time.time()) + duration * 3600

    yaml_content = generate_clash_yaml(selected_results, config, expires_at=expires_at)

    entry = save_yaml(
        session_id=session_id,
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
        results=[IPResult.model_validate(item) for item in selected_results],
    )


def decode_csv_content(content: bytes) -> str:
    """Decode CloudflareST CSV content from common encodings."""
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Cannot decode CSV format")


async def read_limited_upload(file: UploadFile, max_upload_size_mb: int) -> bytes:
    """Read an uploaded CSV with an explicit byte limit."""
    limit_bytes = max_upload_size_mb * 1024 * 1024
    file_buffer = bytearray()

    while True:
        chunk = await file.read(CSV_CHUNK_SIZE_BYTES)
        if not chunk:
            return bytes(file_buffer)

        file_buffer.extend(chunk)
        if len(file_buffer) > limit_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"CSV file too large (limit: {max_upload_size_mb} MB)",
            )


def validate_upload(file: UploadFile) -> None:
    """Validate the uploaded file metadata before reading it."""
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CSV_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported CSV content type: {content_type}",
        )


def parse_results(text: str) -> list[ParsedIPResult]:
    """Normalize CloudflareST CSV rows into typed backend records."""
    reader = csv.DictReader(io.StringIO(text))
    parsed_results: list[ParsedIPResult] = []

    try:
        for row in reader:
            parsed_row = parse_csv_row(row)
            if parsed_row is not None:
                parsed_results.append(parsed_row)
    except Exception as exc:  # pragma: no cover - defensive boundary for malformed CSV
        raise ValueError(f"CSV Parsing Error: {exc}") from exc

    return parsed_results


def parse_csv_row(row: dict[str, str | None]) -> ParsedIPResult | None:
    """Parse a single CSV row, skipping blank records."""
    ip = (row.get(IP_COLUMN) or "").strip()
    if not ip:
        return None

    latency = parse_float_cell(row.get(LATENCY_COLUMN), default=999.0)
    loss = parse_percentage_cell(row.get(LOSS_COLUMN), default=1.0)
    speed_mbps = parse_float_cell(row.get(SPEED_COLUMN), default=0.0)
    colo = first_non_empty_value(row, COLO_COLUMNS)

    return ParsedIPResult(
        ip=ip,
        avg_latency=latency,
        loss_rate=loss,
        speed_kbps=speed_mbps * 1024,
        score=latency if latency > 0 else 999.0,
        colo=colo,
    )


def first_non_empty_value(row: dict[str, str | None], keys: Sequence[str]) -> str:
    """Return the first non-empty CSV column value."""
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def parse_float_cell(raw: str | None, default: float) -> float:
    """Parse a float cell with a safe fallback."""
    try:
        return float((raw or "").strip())
    except ValueError:
        return default


def parse_percentage_cell(raw: str | None, default: float) -> float:
    """Parse a percent-like cell into a ratio."""
    cleaned = (raw or "").replace("%", "").strip()
    if not cleaned:
        return default
    try:
        return float(cleaned) / 100.0
    except ValueError:
        return default
