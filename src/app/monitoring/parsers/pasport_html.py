"""HTML marker parser for pasport.org.ua e-queue pages."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from bs4 import BeautifulSoup

from app.domain.enums import CheckOutcome

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_html(html: str) -> str:
    return _WHITESPACE_RE.sub(" ", html).strip().lower()


def hash_normalized_html(html: str) -> str:
    normalized = normalize_html(html)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _has_real_date_options(soup: BeautifulSoup) -> bool:
    select = soup.select_one('select#date, select[name="date"]')
    if select is None:
        return False
    for option in select.find_all("option"):
        value = (option.get("value") or "").strip()
        if value:
            return True
    return False


def parse_pasport_queue_html(
    html: str,
    *,
    checker_config: dict[str, Any] | None = None,
) -> tuple[CheckOutcome, str]:
    """Classify queue page HTML into a CheckOutcome.

    False AVAILABLE is worse than a miss: unknown/captcha/empty never become AVAILABLE.
    Service-form presence alone is not availability — prefer real date options.
    """
    config = checker_config or {}
    if not html or not html.strip():
        return CheckOutcome.EMPTY_RESPONSE, "empty_body"

    lower = html.lower()
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    captcha_markers = config.get("captcha_markers") or [
        "hcaptcha",
        "cf-challenge",
        "just a moment",
        "attention required",
    ]
    # Only treat as challenge if the page looks like a CF interstitial, not when
    # Cloudflare script crumbs appear alongside the real queue form.
    has_queue_signal = any(
        marker in text.lower()
        for marker in (
            "наразі всі місця зайняті",
            "все места заняты",
            "оберіть послугу",
            "выберите услугу",
            "вибачте, на даний момент",
        )
    ) or any(
        token in lower
        for token in (
            'name="services"',
            "form_queue",
            'id="queue_form"',
            'id="countries_phone"',
            'id="service"',
            'name="service"',
        )
    )
    if not has_queue_signal:
        challenge_bits = (
            "just a moment" in lower
            or "cf-challenge" in lower
            or "challenge-platform" in lower
        )
        for marker in captcha_markers:
            if challenge_bits and (
                marker.lower() in lower or marker.lower() in text.lower()
            ):
                return CheckOutcome.CAPTCHA, f"captcha_or_challenge:{marker}"

    no_slots_markers = config.get("no_slots_markers") or [
        "Наразі всі місця зайняті",
        "все места заняты",
        "all slots are taken",
        "Вибачте, на даний момент всі місця зайняті",
        "Вільні слоти з'являються у довільний час",
    ]
    for marker in no_slots_markers:
        if marker.lower() in text.lower():
            return CheckOutcome.NO_SLOTS, f"marker:{marker}"

    # Strongest available signal: date dropdown already has concrete day values.
    if _has_real_date_options(soup):
        return CheckOutcome.AVAILABLE, "date_options_present"

    available_markers = config.get("available_markers") or [
        "Обрати день",
        "Выберите день",
        "Обрати час",
        "Выберите время",
    ]
    hits = [
        marker
        for marker in available_markers
        if marker.lower() in lower or marker.lower() in text.lower()
    ]
    # "Обрати день" can appear after service select even with zero dates.
    # Without concrete option values this is only a weak signal.
    if hits and _has_real_date_options(soup):
        return CheckOutcome.AVAILABLE, f"markers:{','.join(hits[:3])}"
    if hits:
        return CheckOutcome.POSSIBLY_AVAILABLE, f"markers:{','.join(hits[:3])}"

    # Service form visible but no post-select date signal yet.
    if (
        'name="service"' in lower
        or 'id="service"' in lower
        or "оберіть послугу" in text.lower()
        or "выберите услугу" in text.lower()
    ):
        return CheckOutcome.UNKNOWN, "service_form_without_date_options"

    # Page loaded but neither no-slots nor booking form — structure may have changed.
    if "електронна черга" in text.lower() or "электронная очередь" in text.lower():
        return CheckOutcome.STRUCTURE_CHANGED, "queue_page_without_known_markers"

    return CheckOutcome.UNKNOWN, "unrecognized_page"
