"""Settings and seed integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Country, Location
from app.locations.seed import seed_countries_and_locations


def test_admin_ids_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "10, 20,30")
    settings = Settings()
    assert settings.admin_telegram_ids == [10, 20, 30]


def test_default_language_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEFAULT_LANGUAGE", "de")
    settings = Settings()
    assert settings.default_language == "uk"


@pytest.mark.asyncio
async def test_seed_idempotent(db_session: AsyncSession) -> None:
    first = await seed_countries_and_locations(db_session)
    await db_session.commit()
    assert first["locations_created"] == 5
    assert first["countries_created"] == 4

    second = await seed_countries_and_locations(db_session)
    await db_session.commit()
    assert second["locations_created"] == 0

    locations = (await db_session.scalars(select(Location).order_by(Location.slug))).all()
    assert [loc.slug for loc in locations] == [
        "berlin",
        "krakow",
        "prague",
        "valencia",
        "warsaw",
    ]
    assert all(loc.is_active for loc in locations)

    country_count = await db_session.scalar(select(func.count()).select_from(Country))
    assert country_count == 4
