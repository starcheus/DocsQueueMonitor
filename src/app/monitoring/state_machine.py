"""Availability state machine.

Subscriber notifications are emitted only for a confirmed transition
from an armed NO_SLOTS path into AVAILABLE.
"""

from __future__ import annotations

from app.domain.entities import CheckResult, TransitionDecision
from app.domain.enums import CheckOutcome, LocationStatus

_FAILURE_OUTCOMES = {
    CheckOutcome.PAGE_UNAVAILABLE,
    CheckOutcome.STRUCTURE_CHANGED,
    CheckOutcome.CAPTCHA,
    CheckOutcome.SERVER_ERROR,
    CheckOutcome.EMPTY_RESPONSE,
    CheckOutcome.REDIRECT,
    CheckOutcome.LOCATION_GONE,
    CheckOutcome.TIMEOUT,
    CheckOutcome.NETWORK_ERROR,
}

_AVAILABILITY_OUTCOMES = {
    CheckOutcome.POSSIBLY_AVAILABLE,
    CheckOutcome.AVAILABLE,
}


class AvailabilityStateMachine:
    def __init__(self, *, availability_confirmations: int = 1) -> None:
        if availability_confirmations < 1:
            raise ValueError("availability_confirmations must be >= 1")
        self._confirmations = availability_confirmations

    def transition(
        self,
        *,
        current_status: LocationStatus,
        consecutive_available_checks: int,
        consecutive_failed_checks: int,
        result: CheckResult,
        armed_from_no_slots: bool,
    ) -> TransitionDecision:
        """Apply one check result.

        `armed_from_no_slots` must be True only after the location was observed
        in NO_SLOTS and has not since entered UNKNOWN/ERROR/DISABLED.
        The monitoring service owns persistence of that flag (via previous_status
        / consecutive counters); this method is pure.
        """
        if result.outcome in _FAILURE_OUTCOMES:
            return TransitionDecision(
                new_status=LocationStatus.ERROR,
                previous_status=current_status,
                should_notify_subscribers=False,
                should_alert_admin=consecutive_failed_checks + 1 >= 5,
                consecutive_available_checks=0,
                consecutive_failed_checks=consecutive_failed_checks + 1,
                reason=result.reason or result.outcome.value,
            )

        if result.outcome == CheckOutcome.UNKNOWN:
            return TransitionDecision(
                new_status=LocationStatus.UNKNOWN,
                previous_status=current_status,
                should_notify_subscribers=False,
                should_alert_admin=False,
                consecutive_available_checks=0,
                consecutive_failed_checks=consecutive_failed_checks + 1,
                reason=result.reason or result.outcome.value,
            )

        if result.outcome == CheckOutcome.NO_SLOTS:
            return TransitionDecision(
                new_status=LocationStatus.NO_SLOTS,
                previous_status=current_status,
                should_notify_subscribers=False,
                should_alert_admin=False,
                consecutive_available_checks=0,
                consecutive_failed_checks=0,
                reason=result.reason,
            )

        if result.outcome in _AVAILABILITY_OUTCOMES:
            available_count = consecutive_available_checks + 1
            if available_count < self._confirmations:
                return TransitionDecision(
                    new_status=LocationStatus.POSSIBLY_AVAILABLE,
                    previous_status=current_status,
                    should_notify_subscribers=False,
                    should_alert_admin=False,
                    consecutive_available_checks=available_count,
                    consecutive_failed_checks=0,
                    reason=result.reason or "awaiting_confirmation",
                )

            should_notify = armed_from_no_slots and current_status in {
                LocationStatus.NO_SLOTS,
                LocationStatus.POSSIBLY_AVAILABLE,
            }
            return TransitionDecision(
                new_status=LocationStatus.AVAILABLE,
                previous_status=current_status,
                should_notify_subscribers=should_notify,
                should_alert_admin=False,
                consecutive_available_checks=available_count,
                consecutive_failed_checks=0,
                reason=result.reason,
            )

        return TransitionDecision(
            new_status=LocationStatus.UNKNOWN,
            previous_status=current_status,
            should_notify_subscribers=False,
            should_alert_admin=False,
            consecutive_available_checks=0,
            consecutive_failed_checks=consecutive_failed_checks,
            reason=result.reason or "unhandled_outcome",
        )
