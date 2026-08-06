"""User privacy operations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import UserRepository
from app.subscriptions.service import SubscriptionService


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._subscriptions = SubscriptionService(session)

    async def anonymize_user(self, *, telegram_id: int) -> bool:
        user = await self._users.get_by_telegram_id(telegram_id)
        if user is None:
            return False
        await self._subscriptions.unsubscribe_all(user_id=user.id)
        user.username = None
        user.first_name = None
        user.source = None
        user.is_active = False
        await self._session.flush()
        return True
