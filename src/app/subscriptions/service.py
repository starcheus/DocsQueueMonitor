"""Subscription domain service (Telegram-agnostic)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Subscription, User
from app.database.repositories import LocationRepository, SubscriptionRepository, UserRepository
from app.domain.errors import NotFoundError


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._locations = LocationRepository(session)
        self._subscriptions = SubscriptionRepository(session)

    async def ensure_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        language_code: str,
        source: str | None = None,
    ) -> User:
        user = await self._users.get_by_telegram_id(telegram_id)
        now = datetime.now(UTC)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                language_code=language_code,
                source=source,
                last_interaction_at=now,
            )
            return await self._users.add(user)

        user.username = username
        user.first_name = first_name
        user.language_code = language_code
        user.last_interaction_at = now
        user.is_active = True
        await self._session.flush()
        return user

    async def subscribe(self, *, user_id: int, location_slug: str) -> Subscription:
        location = await self._locations.get_by_slug(location_slug)
        if location is None or not location.is_active:
            raise NotFoundError(f"location not found: {location_slug}")

        existing = await self._subscriptions.get(user_id, location.id)
        if existing is not None:
            existing.is_active = True
            await self._session.flush()
            return existing

        subscription = Subscription(user_id=user_id, location_id=location.id, is_active=True)
        return await self._subscriptions.add(subscription)

    async def unsubscribe(self, *, user_id: int, location_slug: str) -> bool:
        location = await self._locations.get_by_slug(location_slug)
        if location is None:
            return False
        existing = await self._subscriptions.get(user_id, location.id)
        if existing is None or not existing.is_active:
            return False
        existing.is_active = False
        await self._session.flush()
        return True

    async def unsubscribe_all(self, *, user_id: int) -> int:
        items = await self._subscriptions.list_active_for_user(user_id)
        for item in items:
            item.is_active = False
        await self._session.flush()
        return len(items)

    async def list_active(self, *, user_id: int) -> list[Subscription]:
        return await self._subscriptions.list_active_for_user(user_id)
