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


def parse_pasport_queue_html(
    html: str,
    *,
    checker_config: dict[str, Any] | None = None,
) -> tuple[CheckOutcome, str]:
    """Classify queue page HTML into a CheckOutcome.

    False AVAILABLE is worse than a miss: unknown/captcha/empty never become AVAILABLE.
    """
    config = checker_config or {}
    if not html or not html.strip():
        return CheckOutcome.EMPTY_RESPONSE, "empty_body"

    lower = html.lower()
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)

    captcha_markers = config.get("captcha_markers") or [
        "hcaptcha",
        "cf-challenge",
        "just a moment",
        "attention required",
    ]
    for marker in captcha_markers:
        if marker.lower() in lower or marker.lower() in text.lower():
            # Cloudflare interstitial before real content.
            if "наразі всі місця зайняті" in text.lower():
                break
            if "just a moment" in lower or "cf-challenge" in lower:
                return CheckOutcome.CAPTCHA, f"captcha_or_challenge:{marker}"

    no_slots_markers = config.get("no_slots_markers") or [
        "Наразі всі місця зайняті",
        "все места заняты",
        "all slots are taken",
        "Вибачте, на даний момент всі місця зайняті",
    ]
    for marker in no_slots_markers:
        if marker.lower() in text.lower():
            return CheckOutcome.NO_SLOTS, f"marker:{marker}"

    available_markers = config.get("available_markers") or [
        "Оберіть послугу",
        "Выберите услугу",
        "Select a service",
        'name="services"',
        'id="countries_phone"',
    ]
    hits = [
        marker
        for marker in available_markers
        if marker.lower() in lower or marker.lower() in text.lower()
    ]
    if hits:
        # Single marker hit → possibly; strong combination → available signal for SM confirmation.
        if len(hits) >= 2 or any(
            "services" in h.lower() or "countries_phone" in h.lower() for h in hits
        ):
            return CheckOutcome.AVAILABLE, f"markers:{','.join(hits[:3])}"
        return CheckOutcome.POSSIBLY_AVAILABLE, f"markers:{','.join(hits[:3])}"

    # Page loaded but neither no-slots nor booking form — structure may have changed.
    if "електронна черга" in text.lower() or "электронная очередь" in text.lower():
        return CheckOutcome.STRUCTURE_CHANGED, "queue_page_without_known_markers"

    return CheckOutcome.UNKNOWN, "unrecognized_page"
