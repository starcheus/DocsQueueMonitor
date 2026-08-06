"""Checker protocol and shared result helpers."""

from __future__ import annotations

from typing import Protocol

from app.database.models import Location
from app.domain.entities import CheckResult


class AvailabilityChecker(Protocol):
    async def check(self, location: Location) -> CheckResult:
        """Return a structured availability result for one location."""
