from __future__ import annotations

from datetime import datetime, timezone


def to_api_utc_iso(dt: datetime | None) -> str | None:
    """Serialize naive UTC datetimes with explicit Z suffix for browser clients."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")
