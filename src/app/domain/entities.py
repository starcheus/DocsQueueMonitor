"""Immutable domain entities used by services (not ORM models)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums import CheckerType, CheckOutcome, LocationStatus


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of a single availability check for a location."""

    outcome: CheckOutcome
    checker_type: CheckerType
    reason: str | None = None
    response_status: int | None = None
    response_time_ms: int | None = None
    response_hash: str | None = None
    final_url: str | None = None
    checked_at: datetime | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_location_status(self) -> LocationStatus:
        mapping: dict[CheckOutcome, LocationStatus] = {
            CheckOutcome.NO_SLOTS: LocationStatus.NO_SLOTS,
            CheckOutcome.POSSIBLY_AVAILABLE: LocationStatus.POSSIBLY_AVAILABLE,
            CheckOutcome.AVAILABLE: LocationStatus.AVAILABLE,
            CheckOutcome.PAGE_UNAVAILABLE: LocationStatus.ERROR,
            CheckOutcome.STRUCTURE_CHANGED: LocationStatus.ERROR,
            CheckOutcome.CAPTCHA: LocationStatus.ERROR,
            CheckOutcome.SERVER_ERROR: LocationStatus.ERROR,
            CheckOutcome.EMPTY_RESPONSE: LocationStatus.ERROR,
            CheckOutcome.REDIRECT: LocationStatus.ERROR,
            CheckOutcome.LOCATION_GONE: LocationStatus.ERROR,
            CheckOutcome.TIMEOUT: LocationStatus.ERROR,
            CheckOutcome.NETWORK_ERROR: LocationStatus.ERROR,
            CheckOutcome.UNKNOWN: LocationStatus.UNKNOWN,
        }
        return mapping[self.outcome]


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    """Outcome of applying a check result to the location state machine."""

    new_status: LocationStatus
    previous_status: LocationStatus
    should_notify_subscribers: bool
    should_alert_admin: bool
    consecutive_available_checks: int
    consecutive_failed_checks: int
    reason: str | None = None
