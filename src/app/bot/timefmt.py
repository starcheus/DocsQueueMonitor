"""User-facing datetime formatting."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# Default display: Central European Time (CET/CEST) — matches EU hubs.
_DISPLAY_TZ = ZoneInfo("Europe/Berlin")


def format_user_datetime(
    value: datetime | None,
    *,
    lang: str = "uk",
    with_date: bool = True,
) -> str:
    """Format a UTC (or naive-UTC) timestamp for chat display in CET/CEST."""
    _ = lang  # reserved for future locale-specific labels
    if value is None:
        return "—"
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    local = aware.astimezone(_DISPLAY_TZ)
    pattern = "%Y-%m-%d %H:%M" if with_date else "%H:%M"
    # %Z → CET or CEST depending on DST
    return f"{local.strftime(pattern)} ({local.strftime('%Z')})"
