"""Disabled checker — used for inactive or unsupported locations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.database.models import Location
from app.domain.entities import CheckResult
from app.domain.enums import CheckerType, CheckOutcome


class DisabledAvailabilityChecker:
    async def check(self, location: Location) -> CheckResult:
        return CheckResult(
            outcome=CheckOutcome.UNKNOWN,
            checker_type=CheckerType.DISABLED,
            reason="location_disabled",
            checked_at=datetime.now(UTC),
            details={"slug": location.slug},
        )
