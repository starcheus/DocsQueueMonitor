"""Playwright-based availability checker for Cloudflare-protected pages."""

from __future__ import annotations

import contextlib
import re
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
      || body.includes('Выберите услугу')
      || body.includes('Вибачте, на даний момент')) {
    return true;
  }
  if (document.querySelector(
    'form[name="services"], form#services, #queue_form, #form_queue, select#service'
  )) {
    return true;
  }
  if (body.includes('Just a moment') || html.includes('cf-challenge-running')) {
    return false;
  }
  return false;
}"""

_ALPINE_STATE_JS = """() => {
  const form = document.querySelector('form#services, form[name="services"]');
  const alpine = form && form._x_dataStack ? form._x_dataStack[0] : null;
  const alert = form
    ? form.querySelector('[role="alert"]')
    : document.querySelector('[role="alert"]');
  let alertVisible = false;
  if (alert) {
    const style = window.getComputedStyle(alert);
    alertVisible = style.display !== 'none'
      && style.visibility !== 'hidden'
      && alert.offsetParent !== null;
  }
  const dateSelect = document.querySelector('select#date, select[name="date"]');
  const optionDates = dateSelect
    ? [...dateSelect.options]
        .filter(o => o.value)
        .map(o => ({
          value: o.value,
          label: (o.textContent || o.value || '').trim(),
        }))
    : [];
  const alpineDates = (alpine && Array.isArray(alpine.dates))
    ? alpine.dates.map(d => ({
        value: String(d.datePart || d.value || ''),
        label: String(d.date || d.label || d.datePart || d.value || '').trim(),
      })).filter(d => d.value || d.label)
    : [];
  const dates = alpineDates.length ? alpineDates : optionDates;
  if (!alpine) {
    return {
      mode: 'no_alpine',
      loading: false,
      show_message_dates: false,
      message_dates_txt: '',
      dates_len: dates.length,
      dates,
      alert_visible: alertVisible,
      alert_text: alert ? (alert.innerText || '').trim() : '',
    };
  }
  return {
    mode: 'alpine',
    loading: !!alpine.loading,
    show_message_dates: !!alpine.show_message_dates,
    message_dates_txt: alpine.message_dates_txt || '',
    dates_len: dates.length,
    dates,
    alert_visible: alertVisible || !!alpine.show_message_dates,
    alert_text: (alpine.message_dates_txt || (alert ? alert.innerText : '') || '').trim(),
  };
}"""

_DEFAULT_SERVICE_PATTERNS = (
    "паспорт",
    "id-карт",
    "id карт",
    "passport",
)



def _normalize_date_labels(raw_dates: Any) -> list[str]:
    """Turn Alpine/select date payloads into short human labels."""
    labels: list[str] = []
    seen: set[str] = set()
    if not isinstance(raw_dates, list):
        return labels
    for item in raw_dates:
        label = ""
        if isinstance(item, dict):
            label = str(item.get("label") or item.get("date") or item.get("value") or "").strip()
        else:
            label = str(item).strip()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return labels


class BrowserAvailabilityChecker:
    """Fetch queue HTML via Chromium (handles CF challenge with a fresh context)."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        timeout_seconds: float = 45.0,
        user_agent: str,
        headless: bool = False,
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

        await self.stop()
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        log.info("browser_checker_started", headless=self._headless)

    async def stop(self) -> None:
        if self._browser is not None:
            with contextlib.suppress(Exception):
                await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            with contextlib.suppress(Exception):
                await self._playwright.stop()
            self._playwright = None
        log.info("browser_checker_stopped")

    def _browser_alive(self) -> bool:
        if self._browser is None:
            return False
        try:
            return bool(self._browser.is_connected())
        except Exception:
            return False

    async def _ensure_browser(self) -> None:
        if self._browser_alive():
            return
        log.warning("browser_relaunching", reason="not_connected")
        await self.start()

    async def _new_context(self) -> Any:
        assert self._browser is not None
        context = await self._browser.new_context(
            user_agent=self._user_agent,
            locale="uk-UA",
            viewport={"width": 1280, "height": 720},
            extra_http_headers={"Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8"},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
        )
        return context

    async def check(self, location: Location) -> CheckResult:
        if not self._enabled:
            return CheckResult(
                outcome=CheckOutcome.UNKNOWN,
                checker_type=CheckerType.BROWSER,
                reason="playwright_disabled",
                checked_at=datetime.now(UTC),
                details={"slug": location.slug},
            )

        try:
            await self._ensure_browser()
        except Exception as exc:
            return CheckResult(
                outcome=CheckOutcome.NETWORK_ERROR,
                checker_type=CheckerType.BROWSER,
                reason=f"browser_start_failed:{type(exc).__name__}",
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
        context = None
        try:
            context = await self._new_context()
            context.set_default_timeout(self._timeout_ms)
            page = await context.new_page()
            cf_post_blocked = {"value": False}

            def _on_response(response: Any) -> None:
                try:
                    if (
                        response.request.method == "POST"
                        and "e-queue" in response.url
                        and int(response.status) in {403, 503}
                    ):
                        cf_post_blocked["value"] = True
                except Exception:
                    return

            page.on("response", _on_response)

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

            config = location.checker_config or {}
            selected = await self._select_service(page, config)
            available_dates: list[str] = []
            if selected is not None:
                outcome, reason, available_dates = await self._wait_service_availability(
                    page,
                    post_blocked=cf_post_blocked,
                )
            else:
                html = await page.content()
                outcome, reason = parse_pasport_queue_html(html, checker_config=config)

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

            if status is not None and int(status) >= 500:
                outcome = CheckOutcome.SERVER_ERROR
                reason = f"http_{status}:{reason}"

            details: dict[str, Any] = {"slug": location.slug}
            if selected is not None:
                details["selected_service"] = selected
            if available_dates:
                details["available_dates"] = available_dates

            return CheckResult(
                outcome=outcome,
                checker_type=CheckerType.BROWSER,
                reason=reason,
                response_status=int(status) if status is not None else None,
                response_time_ms=elapsed_ms,
                response_hash=hash_normalized_html(html),
                final_url=final_url,
                checked_at=datetime.now(UTC),
                details=details,
            )
        except Exception as exc:
            name = type(exc).__name__
            message = str(exc)
            if any(
                token in message
                for token in (
                    "Connection closed",
                    "Target closed",
                    "Browser.has been closed",
                    "browser has been closed",
                )
            ):
                log.warning("browser_connection_lost", error=name, slug=location.slug)
                with contextlib.suppress(Exception):
                    await self.stop()
            outcome = (
                CheckOutcome.TIMEOUT if "Timeout" in name else CheckOutcome.NETWORK_ERROR
            )
            return CheckResult(
                outcome=outcome,
                checker_type=CheckerType.BROWSER,
                reason=name,
                response_time_ms=int((datetime.now(UTC) - started).total_seconds() * 1000),
                checked_at=datetime.now(UTC),
                details={"slug": location.slug},
            )
        finally:
            if context is not None:
                with contextlib.suppress(Exception):
                    await context.close()

    async def _select_service(self, page: Any, config: dict[str, Any]) -> str | None:
        """Select the target service in the queue dropdown.

        Returns the selected option label, or None if no service select exists.
        """
        if config.get("select_service_before_check", True) is False:
            return None

        select = page.locator("select#service, select[name='service']")
        try:
            count = await select.count()
        except Exception:
            return None
        if count == 0:
            return None

        patterns = config.get("service_option_patterns") or list(_DEFAULT_SERVICE_PATTERNS)
        options = await page.evaluate(
            """() => {
              const el = document.querySelector('select#service, select[name="service"]');
              if (!el) return [];
              return [...el.options].map(o => ({
                value: o.value,
                text: (o.textContent || '').trim(),
              }));
            }""",
        )
        chosen = None
        for option in options:
            if not option.get("value"):
                continue
            text_l = str(option.get("text") or "").lower()
            if any(str(pattern).lower() in text_l for pattern in patterns):
                chosen = option
                break
        if chosen is None:
            chosen = next((o for o in options if o.get("value")), None)
        if chosen is None:
            return None

        await select.first.select_option(value=str(chosen["value"]))
        log.info(
            "service_option_selected",
            value=chosen.get("value"),
            text=chosen.get("text"),
        )
        return str(chosen.get("text") or chosen.get("value"))

    async def _wait_service_availability(
        self,
        page: Any,
        *,
        post_blocked: dict[str, bool],
    ) -> tuple[CheckOutcome, str, list[str]]:
        """Wait for Alpine getDays result after service selection."""
        wait_ms = min(max(self._timeout_ms, 10000), 45000)
        deadline = datetime.now(UTC).timestamp() + (wait_ms / 1000.0)
        last_state: dict[str, Any] = {}

        while datetime.now(UTC).timestamp() < deadline:
            last_state = await page.evaluate(_ALPINE_STATE_JS)
            if not last_state.get("loading"):
                dates = _normalize_date_labels(last_state.get("dates") or [])
                if dates:
                    return (
                        CheckOutcome.AVAILABLE,
                        f"service_selected:dates:{len(dates)}",
                        dates,
                    )
                if last_state.get("show_message_dates") or last_state.get("alert_visible"):
                    alert_text = str(last_state.get("alert_text") or "").strip()
                    alert_text = re.sub(r"<[^>]+>", " ", alert_text)
                    alert_text = re.sub(r"\s+", " ", alert_text).strip()
                    reason = alert_text[:160] if alert_text else "service_selected:no_dates"
                    return CheckOutcome.NO_SLOTS, f"service_selected:{reason}", []
                # Loading finished with neither dates nor message — treat as no slots.
                if last_state.get("mode") == "alpine":
                    return CheckOutcome.NO_SLOTS, "service_selected:empty_dates", []
            await page.wait_for_timeout(400)

        if post_blocked.get("value"):
            return CheckOutcome.CAPTCHA, "service_selected:cf_challenge_on_get_days", []
        if last_state.get("loading"):
            return CheckOutcome.TIMEOUT, "service_selected:get_days_timeout", []
        return CheckOutcome.UNKNOWN, "service_selected:unresolved", []
