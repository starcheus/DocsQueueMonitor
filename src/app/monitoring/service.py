"""Orchestrates location checks, state transitions, and notify decisions."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.database.models import CheckEvent, Location
from app.database.repositories import LocationRepository
from app.domain.enums import LocationStatus
from app.logging import get_logger
from app.monitoring.checkers.registry import CheckerRegistry
from app.monitoring.runtime import MonitoringRuntimeState
from app.monitoring.state_machine import AvailabilityStateMachine

log = get_logger(__name__)


class MonitoringService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        checkers: CheckerRegistry,
        state_machine: AvailabilityStateMachine,
        settings: Settings,
        runtime: MonitoringRuntimeState,
        on_available: object | None = None,
        on_admin_alert: object | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._checkers = checkers
        self._state_machine = state_machine
        self._settings = settings
        self._runtime = runtime
        self._on_available = on_available
        self._on_admin_alert = on_admin_alert
        # cooldown tracking: location_id -> last notify timestamp
        self._last_notify_at: dict[int, datetime] = {}

    async def check_location(self, location_id: int) -> None:
        async with self._session_factory() as session:
            location = await session.get(Location, location_id)
            if location is None or not location.is_active:
                return

            checker = self._checkers.get(location)
            result = await checker.check(location)  # type: ignore[attr-defined]

            current = LocationStatus(location.current_status)
            armed = self._runtime.armed_from_no_slots.get(location.slug, False)
            if current == LocationStatus.NO_SLOTS:
                armed = True
                self._runtime.armed_from_no_slots[location.slug] = True
            if current in {LocationStatus.UNKNOWN, LocationStatus.ERROR, LocationStatus.DISABLED}:
                armed = False
                self._runtime.armed_from_no_slots[location.slug] = False

            decision = self._state_machine.transition(
                current_status=current,
                consecutive_available_checks=location.consecutive_available_checks,
                consecutive_failed_checks=location.consecutive_failed_checks,
                result=result,
                armed_from_no_slots=armed,
            )

            if decision.new_status == LocationStatus.NO_SLOTS:
                self._runtime.armed_from_no_slots[location.slug] = True
            elif decision.new_status in {
                LocationStatus.UNKNOWN,
                LocationStatus.ERROR,
                LocationStatus.DISABLED,
            }:
                self._runtime.armed_from_no_slots[location.slug] = False

            now = datetime.now(UTC)
            session.add(
                CheckEvent(
                    location_id=location.id,
                    status=decision.new_status.value,
                    response_status=result.response_status,
                    response_time_ms=result.response_time_ms,
                    response_hash=result.response_hash,
                    final_url=result.final_url,
                    checker_type=result.checker_type.value,
                    reason=decision.reason or result.reason,
                    created_at=now,
                ),
            )

            location.previous_status = location.current_status
            location.current_status = decision.new_status.value
            location.consecutive_available_checks = decision.consecutive_available_checks
            location.consecutive_failed_checks = decision.consecutive_failed_checks
            location.last_checked_at = now
            location.last_error = (
                decision.reason if decision.new_status == LocationStatus.ERROR else None
            )
            if decision.new_status not in {LocationStatus.ERROR, LocationStatus.UNKNOWN}:
                location.last_success_at = now
                self._runtime.last_successful_check_at = now
            if location.previous_status != location.current_status:
                location.last_status_changed_at = now
            if decision.new_status == LocationStatus.AVAILABLE:
                location.last_available_at = now

            await session.commit()

            log.info(
                "location_checked",
                slug=location.slug,
                outcome=result.outcome.value,
                status=decision.new_status.value,
                notify=decision.should_notify_subscribers,
                reason=decision.reason,
            )

            if decision.should_notify_subscribers and self._on_available is not None:
                if self._cooldown_allows(location.id, now):
                    self._last_notify_at[location.id] = now
                    await self._on_available(location.id)  # type: ignore[operator]
                else:
                    log.info("notify_skipped_cooldown", slug=location.slug)

            if decision.should_alert_admin and self._on_admin_alert is not None:
                await self._on_admin_alert(location.id, decision.reason)  # type: ignore[operator]

    async def check_all_active(self) -> int:
        async with self._session_factory() as session:
            repo = LocationRepository(session)
            locations = await repo.list_active()
            ids = [loc.id for loc in locations]

        for location_id in ids:
            await self.check_location(location_id)
        return len(ids)

    def _cooldown_allows(self, location_id: int, now: datetime) -> bool:
        last = self._last_notify_at.get(location_id)
        if last is None:
            return True
        return (now - last).total_seconds() >= self._settings.notification_cooldown_seconds
