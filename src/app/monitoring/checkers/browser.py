"""Playwright-based availability checker for Cloudflare-protected pages."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.database.models import Location
from app.domain.entities import CheckResult
from app.domain.enums import CheckerType, CheckOutcome
from app.logging import get_logger
from app.monitoring.parsers.pasport_html import hash_normalized_html, parse_pasport_queue_html

log = get_logger(__name__)


class BrowserAvailabilityChecker:
    """Fetch queue HTML via a real Chromium session (handles CF challenge)."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        timeout_seconds: float = 45.0,
        user_agent: str,
        headless: bool = True,
    ) -> None:
        self._enabled = enabled
        self._timeout_ms = int(timeout_seconds * 1000)
        self._user_agent = user_agent
        self._headless = headless
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None

    async def start(self) -> None:
        if not self._enabled:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is not installed; sync with --extra browser",
            ) from exc

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=["--disable-dev-shm-usage"],
        )
        self._context = await self._browser.new_context(
            user_agent=self._user_agent,
            locale="uk-UA",
            viewport={"width": 1280, "height": 720},
        )
        self._context.set_default_timeout(self._timeout_ms)
        log.info("browser_checker_started", headless=self._headless)

    async def stop(self) -> None:
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        log.info("browser_checker_stopped")

    async def check(self, location: Location) -> CheckResult:
        if not self._enabled:
            return CheckResult(
                outcome=CheckOutcome.UNKNOWN,
                checker_type=CheckerType.BROWSER,
                reason="playwright_disabled",
                checked_at=datetime.now(UTC),
                details={"slug": location.slug},
            )
        if self._context is None:
            return CheckResult(
                outcome=CheckOutcome.UNKNOWN,
                checker_type=CheckerType.BROWSER,
                reason="browser_not_started",
                checked_at=datetime.now(UTC),
                details={"slug": location.slug},
            )

        started = datetime.now(UTC)
        page = await self._context.new_page()
        try:
            response = await page.goto(
                location.queue_url,
                wait_until="domcontentloaded",
                timeout=self._timeout_ms,
            )
            # Allow CF JS challenge / Alpine hydrate a bit.
            await page.wait_for_timeout(2500)
            html = await page.content()
            final_url = page.url
            status = response.status if response is not None else None
            elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)

            outcome, reason = parse_pasport_queue_html(
                html,
                checker_config=location.checker_config or {},
            )
            if status is not None and status >= 500:
                outcome = CheckOutcome.SERVER_ERROR
                reason = f"http_{status}:{reason}"

            return CheckResult(
                outcome=outcome,
                checker_type=CheckerType.BROWSER,
                reason=reason,
                response_status=status,
                response_time_ms=elapsed_ms,
                response_hash=hash_normalized_html(html),
                final_url=final_url,
                checked_at=datetime.now(UTC),
            )
        except Exception as exc:
            name = type(exc).__name__
            outcome = CheckOutcome.TIMEOUT if "Timeout" in name else CheckOutcome.NETWORK_ERROR
            return CheckResult(
                outcome=outcome,
                checker_type=CheckerType.BROWSER,
                reason=name,
                response_time_ms=int((datetime.now(UTC) - started).total_seconds() * 1000),
                checked_at=datetime.now(UTC),
                details={"slug": location.slug},
            )
        finally:
            await page.close()
