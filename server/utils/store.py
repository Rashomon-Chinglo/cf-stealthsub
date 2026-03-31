"""YAML file storage with in-memory index.

Subscription YAML files are saved directly to a configurable directory
(can be mapped to Google Drive). Metadata is embedded in YAML comment headers
and an in-memory index is maintained for fast lookups.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


@dataclass
class SubEntry:
    key: str
    session_id: str
    created_at: int
    expires_at: int
    filepath: Path


# In-memory index: {key: SubEntry}
_index: dict[str, SubEntry] = {}

# Session → key mapping (for per-session cache lookup)
_session_keys: dict[str, str] = {}  # {session_id: key}


class SubscriptionMeta(TypedDict):
    key: str
    session_id: str
    created_at: int
    expires_at: int


def init_store(storage_path: str) -> None:
    """Initialize storage directory and rebuild index from existing files."""
    path = Path(storage_path)
    path.mkdir(parents=True, exist_ok=True)

    _index.clear()
    _session_keys.clear()

    for f in path.glob("*.yaml"):
        try:
            meta = parse_yaml_meta(f)
            if not meta:
                continue

            entry = SubEntry(
                key=meta["key"],
                session_id=meta.get("session_id", "unknown"),
                created_at=meta["created_at"],
                expires_at=meta["expires_at"],
                filepath=f,
            )

            if entry.expires_at > time.time():
                _index[entry.key] = entry
                _session_keys[entry.session_id] = entry.key
            else:
                f.unlink(missing_ok=True)
                logger.debug("Removed expired file: %s", f.name)

        except Exception as e:
            logger.warning("Failed to parse %s: %s", f.name, e)

    logger.info("Store initialized: %d active subscriptions", len(_index))


def save_yaml(
    session_id: str,
    yaml_content: str,
    storage_path: str,
    duration_hours: int,
) -> SubEntry:
    """Save a YAML subscription file and return its SubEntry."""
    key = uuid.uuid4().hex[:12]
    now = int(time.time())
    expires_at = now + duration_hours * 3600
    filepath = Path(storage_path) / f"{key}.yaml"

    header = (
        f"# cf-optimizer-meta\n"
        f"# key: {key}\n"
        f"# session_id: {session_id}\n"
        f"# created_at: {now}\n"
        f"# expires_at: {expires_at}\n"
        f"# ---\n"
    )
    filepath.write_text(header + yaml_content, encoding="utf-8")

    entry = SubEntry(
        key=key,
        session_id=session_id,
        created_at=now,
        expires_at=expires_at,
        filepath=filepath,
    )

    old_key = _session_keys.get(session_id)
    if old_key and old_key in _index:
        old_entry = _index.pop(old_key)
        old_entry.filepath.unlink(missing_ok=True)
        logger.debug("Replaced old sub for session %s: %s", session_id[:8], old_key)

    _index[key] = entry
    _session_keys[session_id] = key
    logger.info("Saved subscription %s for session %s", key, session_id[:8])
    return entry


def get_by_key(key: str) -> SubEntry | None:
    """Look up a subscription by its key."""
    return _index.get(key)


def get_by_session(session_id: str) -> SubEntry | None:
    """Look up a valid (non-expired) subscription for a session."""
    key = _session_keys.get(session_id)
    if not key:
        return None
    entry = _index.get(key)
    if entry and entry.expires_at > time.time():
        return entry
    return None


def read_yaml(entry: SubEntry) -> str:
    """Read YAML file content, stripping the metadata comment header."""
    content = entry.filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    start = 0
    for i, line in enumerate(lines):
        if line.strip() == "# ---":
            start = i + 1
            break
    return "\n".join(lines[start:])


def cleanup_expired(storage_path: str) -> int:
    """Remove expired files and index entries. Returns count removed."""
    now = time.time()
    expired_keys = [k for k, v in _index.items() if v.expires_at < now]
    for k in expired_keys:
        entry = _index.pop(k)
        entry.filepath.unlink(missing_ok=True)
        _session_keys.pop(entry.session_id, None)
    if expired_keys:
        logger.info("Cleaned up %d expired subscriptions", len(expired_keys))
    return len(expired_keys)


def parse_yaml_meta(filepath: Path) -> SubscriptionMeta | None:
    """Parse metadata from YAML file comment header."""
    meta: dict[str, str | int] = {}
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line == "# ---":
                break
            if line == "# cf-optimizer-meta":
                continue
            if line.startswith("# ") and ": " in line:
                k, v = line[2:].split(": ", 1)
                if k in ("created_at", "expires_at"):
                    meta[k] = int(v)
                else:
                    meta[k] = v
    required_keys = {"key", "session_id", "created_at", "expires_at"}
    if not required_keys.issubset(meta):
        return None
    return SubscriptionMeta(
        key=str(meta["key"]),
        session_id=str(meta["session_id"]),
        created_at=int(meta["created_at"]),
        expires_at=int(meta["expires_at"]),
    )
