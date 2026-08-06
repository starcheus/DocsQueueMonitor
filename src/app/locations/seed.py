"""Seed data for MVP locations.

Sources verified on 2026-08-06 from official center selector on
https://prague.pasport.org.ua/solutions/e-queue and related city subdomains.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Country, Location
from app.domain.enums import CheckerType, LocationStatus
from app.locations.markers import DEFAULT_PASPORT_MARKERS

# MVP: Prague + Warsaw + Berlin + Kraków (high-demand EU hubs).
MVP_COUNTRIES: list[dict[str, Any]] = [
    {"code": "CZ", "name": "Чехія", "sort_order": 10},
    {"code": "PL", "name": "Польща", "sort_order": 20},
    {"code": "DE", "name": "Німеччина", "sort_order": 30},
]

MVP_LOCATIONS: list[dict[str, Any]] = [
    {
        "country_code": "CZ",
        "slug": "prague",
        "city": "Prague",
        "display_name": "Прага",
        "timezone": "Europe/Prague",
        "official_url": "https://prague.pasport.org.ua/",
        "queue_url": "https://prague.pasport.org.ua/solutions/e-queue",
        "is_active": True,
        "checker_type": CheckerType.BROWSER.value,
    },
    {
        "country_code": "PL",
        "slug": "warsaw",
        "city": "Warsaw",
        "display_name": "Варшава",
        "timezone": "Europe/Warsaw",
        "official_url": "https://warszawa.pasport.org.ua/",
        "queue_url": "https://warszawa.pasport.org.ua/solutions/e-queue",
        "is_active": True,
        "checker_type": CheckerType.BROWSER.value,
    },
    {
        "country_code": "DE",
        "slug": "berlin",
        "city": "Berlin",
        "display_name": "Берлін",
        "timezone": "Europe/Berlin",
        "official_url": "https://berlin.pasport.org.ua/",
        "queue_url": "https://berlin.pasport.org.ua/solutions/e-queue",
        "is_active": True,
        "checker_type": CheckerType.BROWSER.value,
    },
    {
        "country_code": "PL",
        "slug": "krakow",
        "city": "Kraków",
        "display_name": "Краків",
        "timezone": "Europe/Warsaw",
        "official_url": "https://krakow.pasport.org.ua/",
        "queue_url": "https://krakow.pasport.org.ua/solutions/e-queue",
        "is_active": True,
        "checker_type": CheckerType.BROWSER.value,
    },
]


async def seed_countries_and_locations(session: AsyncSession) -> dict[str, int]:
    """Idempotently insert MVP countries and locations.

    Returns counts: {"countries_created": N, "locations_created": M}.
    """
    countries_created = 0
    locations_created = 0

    code_to_country: dict[str, Country] = {}
    for payload in MVP_COUNTRIES:
        existing = await session.scalar(
            select(Country).where(Country.code == payload["code"]),
        )
        if existing is None:
            country = Country(
                code=payload["code"],
                name=payload["name"],
                is_active=True,
                sort_order=payload["sort_order"],
            )
            session.add(country)
            await session.flush()
            countries_created += 1
            code_to_country[payload["code"]] = country
        else:
            existing.name = payload["name"]
            existing.sort_order = payload["sort_order"]
            existing.is_active = True
            code_to_country[payload["code"]] = existing

    for payload in MVP_LOCATIONS:
        existing = await session.scalar(
            select(Location).where(Location.slug == payload["slug"]),
        )
        if existing is not None:
            continue
        country = code_to_country[payload["country_code"]]
        location = Location(
            country_id=country.id,
            slug=payload["slug"],
            city=payload["city"],
            display_name=payload["display_name"],
            timezone=payload["timezone"],
            official_url=payload["official_url"],
            queue_url=payload["queue_url"],
            checker_type=payload["checker_type"],
            checker_config=dict(DEFAULT_PASPORT_MARKERS),
            is_active=payload["is_active"],
            current_status=LocationStatus.UNKNOWN.value,
            previous_status=LocationStatus.UNKNOWN.value,
        )
        session.add(location)
        locations_created += 1

    await session.flush()
    return {
        "countries_created": countries_created,
        "locations_created": locations_created,
    }
