"""Reserved API checker — no public API discovered during Stage 0."""

from __future__ import annotations

from datetime import UTC, datetime

from app.database.models import Location
from app.domain.entities import CheckResult
from app.domain.enums import CheckerType, CheckOutcome


class ApiAvailabilityChecker:
    async def check(self, location: Location) -> CheckResult:
        return CheckResult(
            outcome=CheckOutcome.UNKNOWN,
            checker_type=CheckerType.API,
            reason="no_public_api",
            checked_at=datetime.now(UTC),
            details={"slug": location.slug},
        )
