"""Subscription service unit/integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.errors import NotFoundError
from app.subscriptions.service import SubscriptionService


@pytest.mark.asyncio
async def test_subscribe_and_list(
    seeded_session: AsyncSession,
) -> None:
    service = SubscriptionService(seeded_session)
    user = await service.ensure_user(
        telegram_id=1001,
        username="tester",
        first_name="Test",
        language_code="uk",
    )
    sub = await service.subscribe(user_id=user.id, location_slug="prague")
    assert sub.is_active is True

    # Idempotent re-subscribe
    sub2 = await service.subscribe(user_id=user.id, location_slug="prague")
    assert sub2.id == sub.id
    assert sub2.is_active is True

    berlin = await service.subscribe(user_id=user.id, location_slug="berlin")
    assert berlin.is_active is True

    active = await service.list_active(user_id=user.id)
    slugs = {item.location.slug for item in active}
    assert slugs == {"prague", "berlin"}
    await seeded_session.commit()


@pytest.mark.asyncio
async def test_unsubscribe_and_unsubscribe_all(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        from app.locations.seed import seed_countries_and_locations

        await seed_countries_and_locations(session)
        await session.commit()

    async with session_factory() as session:
        service = SubscriptionService(session)
        user = await service.ensure_user(
            telegram_id=2002,
            username=None,
            first_name="A",
            language_code="ru",
        )
        await service.subscribe(user_id=user.id, location_slug="prague")
        await service.subscribe(user_id=user.id, location_slug="warsaw")
        await service.subscribe(user_id=user.id, location_slug="krakow")

        assert await service.unsubscribe(user_id=user.id, location_slug="warsaw") is True
        active = await service.list_active(user_id=user.id)
        assert {s.location.slug for s in active} == {"prague", "krakow"}

        removed = await service.unsubscribe_all(user_id=user.id)
        assert removed == 2
        assert await service.list_active(user_id=user.id) == []
        await session.commit()


@pytest.mark.asyncio
async def test_subscribe_unknown_location(seeded_session: AsyncSession) -> None:
    service = SubscriptionService(seeded_session)
    user = await service.ensure_user(
        telegram_id=3003,
        username=None,
        first_name=None,
        language_code="en",
    )
    with pytest.raises(NotFoundError):
        await service.subscribe(user_id=user.id, location_slug="toronto")


@pytest.mark.asyncio
async def test_ensure_user_preserves_language(seeded_session: AsyncSession) -> None:
    service = SubscriptionService(seeded_session)
    user = await service.ensure_user(
        telegram_id=4004,
        username="a",
        first_name="A",
        language_code="ru",
    )
    assert user.language_code == "ru"

    again = await service.ensure_user(
        telegram_id=4004,
        username="a",
        first_name="A",
        language_code="uk",
    )
    assert again.language_code == "ru"

    updated = await service.set_language(telegram_id=4004, language_code="en")
    assert updated.language_code == "en"
