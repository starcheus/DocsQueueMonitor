"""Playwright-based availability checker for Cloudflare-protected pages."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any

from app.database.models import Location
from app.domain.entities import CheckResult
from app.domain.enums import CheckerType, CheckOutcome
from app.logging import get_logger
from app.monitoring.parsers.pasport_html import hash_normalized_html, parse_pasport_queue_html

log = get_logger(__name__)

_CONTENT_READY_JS = """() => {
  const body = document.body ? document.body.innerText : '';
  const html = document.documentElement ? document.documentElement.innerHTML : '';
  if (body.includes('Наразі всі місця зайняті')
      || body.includes('все места заняты')
      || body.includes('Оберіть послугу')
      || body.includes('Выберите услугу')) {
    return true;
  }
  if (document.querySelector('form[name="services"], form#services, #queue_form, #form_queue')) {
    return true;
  }
  if (body.includes('Just a moment') || html.includes('cf-challenge-running')) {
    return false;
  }
  return false;
}"""


class BrowserAvailabilityChecker:
    """Fetch queue HTML via Chromium (handles CF challenge with a fresh context)."""

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
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        log.info("browser_checker_started", headless=self._headless)

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        log.info("browser_checker_stopped")

    def _new_context(self) -> Any:
        assert self._browser is not None
        return self._browser.new_context(
            user_agent=self._user_agent,
            locale="uk-UA",
            viewport={"width": 1280, "height": 720},
            extra_http_headers={"Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8"},
        )

    async def check(self, location: Location) -> CheckResult:
        if not self._enabled:
            return CheckResult(
                outcome=CheckOutcome.UNKNOWN,
                checker_type=CheckerType.BROWSER,
                reason="playwright_disabled",
                checked_at=datetime.now(UTC),
                details={"slug": location.slug},
            )
        if self._browser is None:
            return CheckResult(
                outcome=CheckOutcome.UNKNOWN,
                checker_type=CheckerType.BROWSER,
                reason="browser_not_started",
                checked_at=datetime.now(UTC),
                details={"slug": location.slug},
            )

        started = datetime.now(UTC)
        context = await self._new_context()
        context.set_default_timeout(self._timeout_ms)
        page = await context.new_page()
        try:
            response = await page.goto(
                location.queue_url,
                wait_until="domcontentloaded",
                timeout=self._timeout_ms,
            )
            status = response.status if response is not None else None
            if status == 429:
                elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
                return CheckResult(
                    outcome=CheckOutcome.PAGE_UNAVAILABLE,
                    checker_type=CheckerType.BROWSER,
                    reason="http_429_rate_limited",
                    response_status=429,
                    response_time_ms=elapsed_ms,
                    final_url=page.url,
                    checked_at=datetime.now(UTC),
                )
            try:
                await page.wait_for_function(
                    _CONTENT_READY_JS,
                    timeout=min(self._timeout_ms, 20000),
                )
            except Exception:
                await page.wait_for_timeout(2500)

            html = await page.content()
            final_url = page.url
            with contextlib.suppress(Exception):
                nav_status = await page.evaluate(
                    "() => performance.getEntriesByType('navigation')[0]"
                    "?.responseStatus || null",
                )
                if nav_status is not None:
                    status = nav_status
            if status == 429:
                elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
                return CheckResult(
                    outcome=CheckOutcome.PAGE_UNAVAILABLE,
                    checker_type=CheckerType.BROWSER,
                    reason="http_429_rate_limited",
                    response_status=429,
                    response_time_ms=elapsed_ms,
                    final_url=final_url,
                    checked_at=datetime.now(UTC),
                )
            elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)

            outcome, reason = parse_pasport_queue_html(
                html,
                checker_config=location.checker_config or {},
            )
            if status is not None and int(status) >= 500:
                outcome = CheckOutcome.SERVER_ERROR
                reason = f"http_{status}:{reason}"

            return CheckResult(
                outcome=outcome,
                checker_type=CheckerType.BROWSER,
                reason=reason,
                response_status=int(status) if status is not None else None,
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
            await context.close()
