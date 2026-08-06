"""Datetime display helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from app.bot.timefmt import format_user_datetime


def test_format_user_datetime_converts_utc_to_cet() -> None:
    # 22:42 UTC on 6 Aug → 00:42 next day in Central Europe (CEST, UTC+2)
    value = datetime(2026, 8, 6, 22, 42, tzinfo=UTC)
    assert format_user_datetime(value, lang="uk") == "2026-08-07 00:42 (CEST)"
    assert format_user_datetime(value, lang="en", with_date=False) == "00:42 (CEST)"
    assert format_user_datetime(None) == "—"


def test_format_user_datetime_winter_cet() -> None:
    # 22:42 UTC in January → 23:42 CET (UTC+1)
    value = datetime(2026, 1, 15, 22, 42, tzinfo=UTC)
    assert format_user_datetime(value, lang="uk") == "2026-01-15 23:42 (CET)"
