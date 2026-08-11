"""Monitoring schedule helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.monitoring.service import should_check_location


def test_subscribed_always_checked() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    assert (
        should_check_location(
            has_subscribers=True,
            last_checked_at=now,
            now=now,
            unsubscribed_interval_seconds=3600,
        )
        is True
    )


def test_unsubscribed_skipped_within_hour() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    recent = now - timedelta(minutes=10)
    assert (
        should_check_location(
            has_subscribers=False,
            last_checked_at=recent,
            now=now,
            unsubscribed_interval_seconds=3600,
        )
        is False
    )


def test_unsubscribed_checked_after_idle() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    old = now - timedelta(hours=2)
    assert (
        should_check_location(
            has_subscribers=False,
            last_checked_at=old,
            now=now,
            unsubscribed_interval_seconds=3600,
        )
        is True
    )


def test_never_checked_unsubscribed_is_checked() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    assert (
        should_check_location(
            has_subscribers=False,
            last_checked_at=None,
            now=now,
            unsubscribed_interval_seconds=3600,
        )
        is True
    )


def test_subscribed_rate_limited_skipped_during_backoff() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    recent = now - timedelta(seconds=120)
    assert (
        should_check_location(
            has_subscribers=True,
            last_checked_at=recent,
            last_error="http_429_rate_limited",
            now=now,
            unsubscribed_interval_seconds=3600,
            rate_limit_backoff_seconds=300,
        )
        is False
    )


def test_subscribed_rate_limited_checked_after_backoff() -> None:
    now = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    old = now - timedelta(seconds=360)
    assert (
        should_check_location(
            has_subscribers=True,
            last_checked_at=old,
            last_error="http_429_rate_limited",
            now=now,
            unsubscribed_interval_seconds=3600,
            rate_limit_backoff_seconds=300,
        )
        is True
    )
