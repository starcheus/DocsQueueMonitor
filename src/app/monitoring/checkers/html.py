"""HTML availability checker (secondary; requires reachable page without CF block)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.database.models import Location
from app.domain.entities import CheckResult
from app.domain.enums import CheckerType, CheckOutcome
from app.monitoring.parsers.pasport_html import hash_normalized_html, parse_pasport_queue_html


class HtmlAvailabilityChecker:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        timeout_seconds: float = 45.0,
        user_agent: str,
    ) -> None:
        self._client = client
        self._timeout = timeout_seconds
        self._user_agent = user_agent

    async def check(self, location: Location) -> CheckResult:
        started = datetime.now(UTC)
        try:
            response = await self._client.get(
                location.queue_url,
                timeout=self._timeout,
                headers={"User-Agent": self._user_agent},
                follow_redirects=True,
            )
        except httpx.TimeoutException:
            return CheckResult(
                outcome=CheckOutcome.TIMEOUT,
                checker_type=CheckerType.HTML,
                reason="timeout",
                checked_at=datetime.now(UTC),
            )
        except httpx.HTTPError as exc:
            return CheckResult(
                outcome=CheckOutcome.NETWORK_ERROR,
                checker_type=CheckerType.HTML,
                reason=type(exc).__name__,
                checked_at=datetime.now(UTC),
            )

        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        if response.status_code >= 500:
            return CheckResult(
                outcome=CheckOutcome.SERVER_ERROR,
                checker_type=CheckerType.HTML,
                reason=f"http_{response.status_code}",
                response_status=response.status_code,
                response_time_ms=elapsed_ms,
                final_url=str(response.url),
                checked_at=datetime.now(UTC),
            )

        outcome, reason = parse_pasport_queue_html(
            response.text,
            checker_config=location.checker_config or {},
        )
        # Cloudflare challenge often returns 403 with challenge HTML.
        if response.status_code == 403 and outcome == CheckOutcome.CAPTCHA:
            pass
        elif response.status_code >= 400 and outcome not in {
            CheckOutcome.NO_SLOTS,
            CheckOutcome.AVAILABLE,
            CheckOutcome.POSSIBLY_AVAILABLE,
        }:
            outcome = CheckOutcome.PAGE_UNAVAILABLE
            reason = f"http_{response.status_code}:{reason}"

        return CheckResult(
            outcome=outcome,
            checker_type=CheckerType.HTML,
            reason=reason,
            response_status=response.status_code,
            response_time_ms=elapsed_ms,
            response_hash=hash_normalized_html(response.text),
            final_url=str(response.url),
            checked_at=datetime.now(UTC),
        )
