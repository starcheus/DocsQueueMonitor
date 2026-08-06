"""Monitoring service transition notification gating."""

from __future__ import annotations

from app.domain.entities import CheckResult
from app.domain.enums import CheckerType, CheckOutcome, LocationStatus
from app.monitoring.state_machine import AvailabilityStateMachine


def test_full_no_slots_to_available_path() -> None:
    sm = AvailabilityStateMachine(availability_confirmations=2)

    first = sm.transition(
        current_status=LocationStatus.NO_SLOTS,
        consecutive_available_checks=0,
        consecutive_failed_checks=0,
        result=CheckResult(outcome=CheckOutcome.AVAILABLE, checker_type=CheckerType.BROWSER),
        armed_from_no_slots=True,
    )
    assert first.new_status == LocationStatus.POSSIBLY_AVAILABLE
    assert first.should_notify_subscribers is False

    second = sm.transition(
        current_status=LocationStatus.POSSIBLY_AVAILABLE,
        consecutive_available_checks=first.consecutive_available_checks,
        consecutive_failed_checks=0,
        result=CheckResult(outcome=CheckOutcome.AVAILABLE, checker_type=CheckerType.BROWSER),
        armed_from_no_slots=True,
    )
    assert second.new_status == LocationStatus.AVAILABLE
    assert second.should_notify_subscribers is True

    third = sm.transition(
        current_status=LocationStatus.AVAILABLE,
        consecutive_available_checks=second.consecutive_available_checks,
        consecutive_failed_checks=0,
        result=CheckResult(outcome=CheckOutcome.AVAILABLE, checker_type=CheckerType.BROWSER),
        armed_from_no_slots=True,
    )
    assert third.should_notify_subscribers is False

    back = sm.transition(
        current_status=LocationStatus.AVAILABLE,
        consecutive_available_checks=third.consecutive_available_checks,
        consecutive_failed_checks=0,
        result=CheckResult(outcome=CheckOutcome.NO_SLOTS, checker_type=CheckerType.BROWSER),
        armed_from_no_slots=True,
    )
    assert back.new_status == LocationStatus.NO_SLOTS
