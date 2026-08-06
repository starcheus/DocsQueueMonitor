"""Repository helpers for core entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Country, Location, Subscription, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id),
        )
        return result.scalar_one_or_none()

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user


class LocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[Location]:
        result = await self._session.execute(
            select(Location)
            .where(Location.is_active.is_(True))
            .options(selectinload(Location.country))
            .order_by(Location.id),
        )
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Location | None:
        result = await self._session.execute(
            select(Location).where(Location.slug == slug).options(selectinload(Location.country)),
        )
        return result.scalar_one_or_none()

    async def list_by_country_code(self, country_code: str) -> list[Location]:
        result = await self._session.execute(
            select(Location)
            .join(Country)
            .where(Country.code == country_code)
            .options(selectinload(Location.country))
            .order_by(Location.city),
        )
        return list(result.scalars().all())


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int, location_id: int) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.location_id == location_id,
            ),
        )
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: int) -> list[Subscription]:
        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.is_active.is_(True))
            .options(selectinload(Subscription.location).selectinload(Location.country))
            .order_by(Subscription.id),
        )
        return list(result.scalars().all())

    async def list_active_for_location(self, location_id: int) -> list[Subscription]:
        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.location_id == location_id, Subscription.is_active.is_(True))
            .options(selectinload(Subscription.user)),
        )
        return list(result.scalars().all())

    async def add(self, subscription: Subscription) -> Subscription:
        self._session.add(subscription)
        await self._session.flush()
        return subscription
