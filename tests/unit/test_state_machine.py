"""Unit tests for availability state machine."""

from __future__ import annotations

from app.domain.entities import CheckResult
from app.domain.enums import CheckerType, CheckOutcome, LocationStatus
from app.monitoring.state_machine import AvailabilityStateMachine


def _result(outcome: CheckOutcome) -> CheckResult:
    return CheckResult(outcome=outcome, checker_type=CheckerType.BROWSER, reason="test")


def test_no_slots_to_possibly_no_notify() -> None:
    sm = AvailabilityStateMachine(availability_confirmations=2)
    decision = sm.transition(
        current_status=LocationStatus.NO_SLOTS,
        consecutive_available_checks=0,
        consecutive_failed_checks=0,
        result=_result(CheckOutcome.AVAILABLE),
        armed_from_no_slots=True,
    )
    assert decision.new_status == LocationStatus.POSSIBLY_AVAILABLE
    assert decision.should_notify_subscribers is False
    assert decision.consecutive_available_checks == 1


def test_confirmed_transition_notifies() -> None:
    sm = AvailabilityStateMachine(availability_confirmations=2)
    decision = sm.transition(
        current_status=LocationStatus.POSSIBLY_AVAILABLE,
        consecutive_available_checks=1,
        consecutive_failed_checks=0,
        result=_result(CheckOutcome.AVAILABLE),
        armed_from_no_slots=True,
    )
    assert decision.new_status == LocationStatus.AVAILABLE
    assert decision.should_notify_subscribers is True


def test_no_repeat_notify_while_still_available() -> None:
    sm = AvailabilityStateMachine(availability_confirmations=2)
    decision = sm.transition(
        current_status=LocationStatus.AVAILABLE,
        consecutive_available_checks=5,
        consecutive_failed_checks=0,
        result=_result(CheckOutcome.AVAILABLE),
        armed_from_no_slots=True,
    )
    assert decision.new_status == LocationStatus.AVAILABLE
    assert decision.should_notify_subscribers is False


def test_renotify_requires_return_to_no_slots_path() -> None:
    sm = AvailabilityStateMachine(availability_confirmations=2)
    # Without arming (e.g. after UNKNOWN), no notify.
    decision = sm.transition(
        current_status=LocationStatus.POSSIBLY_AVAILABLE,
        consecutive_available_checks=1,
        consecutive_failed_checks=0,
        result=_result(CheckOutcome.AVAILABLE),
        armed_from_no_slots=False,
    )
    assert decision.should_notify_subscribers is False


def test_unknown_never_becomes_available() -> None:
    sm = AvailabilityStateMachine(availability_confirmations=1)
    decision = sm.transition(
        current_status=LocationStatus.NO_SLOTS,
        consecutive_available_checks=0,
        consecutive_failed_checks=0,
        result=_result(CheckOutcome.UNKNOWN),
        armed_from_no_slots=True,
    )
    assert decision.new_status == LocationStatus.UNKNOWN
    assert decision.should_notify_subscribers is False


def test_network_error_increments_failures() -> None:
    sm = AvailabilityStateMachine(availability_confirmations=2)
    decision = sm.transition(
        current_status=LocationStatus.NO_SLOTS,
        consecutive_available_checks=0,
        consecutive_failed_checks=4,
        result=_result(CheckOutcome.NETWORK_ERROR),
        armed_from_no_slots=True,
    )
    assert decision.new_status == LocationStatus.ERROR
    assert decision.consecutive_failed_checks == 5
    assert decision.should_alert_admin is True
