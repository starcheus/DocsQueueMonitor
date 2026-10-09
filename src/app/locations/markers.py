"""Default HTML markers shared by pasport.org.ua e-queue pages."""

from __future__ import annotations

from typing import Any

DEFAULT_PASPORT_MARKERS: dict[str, Any] = {
    "no_slots_markers": [
        "Наразі всі місця зайняті",
        "все места заняты",
        "all slots are taken",
        "Вибачте, на даний момент всі місця зайняті",
        "Вільні слоти з'являються у довільний час",
        # Note: do NOT add Alpine's hidden default
        # "На даний момент відсутні місця..." — it is always present in DOM.
    ],
    # Post-service-select signals only. Presence of the service form alone is NOT
    # availability — slots are confirmed only after choosing a service.
    "available_markers": [
        "Обрати день",
        "Выберите день",
        "Обрати час",
        "Выберите время",
    ],
    "captcha_markers": [
        "hcaptcha",
        "cf-challenge",
        "Just a moment",
        "Attention Required",
    ],
    "service_option_patterns": [
        "паспорт",
        "ID-карт",
        "id-карт",
        "passport",
    ],
    "select_service_before_check": True,
    "source": "official-ui-2026-10-05",
}
