"""Default HTML markers shared by pasport.org.ua e-queue pages."""

from __future__ import annotations

from typing import Any

DEFAULT_PASPORT_MARKERS: dict[str, Any] = {
    "no_slots_markers": [
        "Наразі всі місця зайняті",
        "все места заняты",
        "all slots are taken",
        "Вибачте, на даний момент всі місця зайняті",
    ],
    "available_markers": [
        "Оберіть послугу",
        "Выберите услугу",
        "Select a service",
        "form_queue",
        'name="services"',
        'id="countries_phone"',
    ],
    "captcha_markers": [
        "hcaptcha",
        "cf-challenge",
        "Just a moment",
        "Attention Required",
    ],
    "source": "official-ui-2026-08-06",
}
