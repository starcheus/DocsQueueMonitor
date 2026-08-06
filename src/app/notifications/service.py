"""High-level notification orchestration."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.texts import t
from app.database.models import Location
from app.database.repositories import SubscriptionRepository
from app.domain.enums import NotificationType
from app.logging import get_logger
from app.notifications.queue import NotificationQueue, OutboundMessage

log = get_logger(__name__)


class NotificationService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        queue: NotificationQueue,
        admin_telegram_ids: list[int],
    ) -> None:
        self._session_factory = session_factory
        self._queue = queue
        self._admin_ids = admin_telegram_ids

    async def notify_slots_available(self, location_id: int) -> int:
        async with self._session_factory() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            location = await session.scalar(
                select(Location)
                .where(Location.id == location_id)
                .options(selectinload(Location.country)),
            )
            if location is None:
                return 0
            repo = SubscriptionRepository(session)
            subscriptions = await repo.list_active_for_location(location_id)
            payloads: list[tuple[int, int, str, str]] = []
            for sub in subscriptions:
                user = sub.user
                if not user.is_active or user.is_blocked:
                    continue
                lang = user.language_code or "uk"
                checked = (
                    location.last_checked_at.strftime("%H:%M") if location.last_checked_at else "—"
                )
                text = t(
                    lang,
                    "notify.slots_available",
                    city=location.display_name,
                    country=location.country.name if location.country else "",
                    checked_at=checked,
                )
                payloads.append((user.id, user.telegram_id, lang, text))

            queue_url = location.queue_url
            slug = location.slug
            city = location.display_name

        for user_id, telegram_id, lang, text in payloads:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=t(lang, "notify.btn_open_site"),
                            url=queue_url,
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=t(lang, "notify.btn_unsubscribe", city=city),
                            callback_data=f"unsub:{slug}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=t(lang, "notify.btn_status"),
                            callback_data=f"status:{slug}",
                        ),
                    ],
                ],
            )
            await self._queue.enqueue(
                OutboundMessage(
                    user_id=user_id,
                    telegram_id=telegram_id,
                    location_id=location_id,
                    notification_type=NotificationType.SLOTS_AVAILABLE,
                    text=text,
                    reply_markup=markup,
                ),
            )
        log.info("slots_notifications_enqueued", location_id=location_id, count=len(payloads))
        return len(payloads)

    async def alert_admins(self, *, text: str) -> None:
        for telegram_id in self._admin_ids:
            await self._queue.enqueue(
                OutboundMessage(
                    user_id=None,
                    telegram_id=telegram_id,
                    location_id=None,
                    notification_type=NotificationType.ADMIN_ALERT,
                    text=text,
                ),
            )
