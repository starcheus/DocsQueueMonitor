"""Telegram send queue with concurrency limits and RetryAfter handling."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.models import NotificationEvent, User
from app.domain.enums import NotificationStatus, NotificationType
from app.logging import get_logger

log = get_logger(__name__)

SendCallable = Callable[[], Awaitable[Any]]


@dataclass(slots=True)
class OutboundMessage:
    user_id: int | None
    telegram_id: int
    location_id: int | None
    notification_type: NotificationType
    text: str
    reply_markup: Any | None = None


class NotificationQueue:
    def __init__(
        self,
        *,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
        concurrency: int = 5,
    ) -> None:
        self._bot = bot
        self._session_factory = session_factory
        self._sem = asyncio.Semaphore(concurrency)
        self._queue: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._stop = asyncio.Event()

    def start(self, worker_count: int | None = None) -> None:
        count = worker_count or max(1, self._sem._value)
        for index in range(count):
            self._workers.append(
                asyncio.create_task(self._worker(), name=f"notify-worker-{index}"),
            )
        log.info("notification_queue_started", workers=count)

    async def stop(self) -> None:
        self._stop.set()
        for _ in self._workers:
            await self._queue.put(
                OutboundMessage(
                    user_id=None,
                    telegram_id=0,
                    location_id=None,
                    notification_type=NotificationType.TEST,
                    text="",
                ),
            )
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        log.info("notification_queue_stopped")

    async def enqueue(self, message: OutboundMessage) -> None:
        await self._queue.put(message)

    async def _worker(self) -> None:
        while not self._stop.is_set():
            message = await self._queue.get()
            if self._stop.is_set() and not message.text:
                self._queue.task_done()
                break
            if not message.text:
                self._queue.task_done()
                continue
            async with self._sem:
                await self._send(message)
            self._queue.task_done()

    async def _send(self, message: OutboundMessage) -> None:
        event_id = await self._create_event(message)
        try:
            sent = await self._bot.send_message(
                chat_id=message.telegram_id,
                text=message.text,
                reply_markup=message.reply_markup,
                disable_web_page_preview=True,
            )
            await self._finalize_event(
                event_id,
                status=NotificationStatus.SENT,
                telegram_message_id=sent.message_id,
            )
        except TelegramRetryAfter as exc:
            log.warning("telegram_retry_after", seconds=exc.retry_after)
            await asyncio.sleep(exc.retry_after + 0.5)
            await self.enqueue(message)
            await self._finalize_event(
                event_id,
                status=NotificationStatus.CANCELLED,
                error="retried",
            )
        except TelegramForbiddenError:
            await self._mark_user_blocked(message.telegram_id)
            await self._finalize_event(
                event_id,
                status=NotificationStatus.FAILED,
                error="forbidden",
            )
        except Exception as exc:
            log.exception("telegram_send_failed", error=type(exc).__name__)
            await self._finalize_event(
                event_id,
                status=NotificationStatus.FAILED,
                error=type(exc).__name__,
            )

    async def _create_event(self, message: OutboundMessage) -> int:
        async with self._session_factory() as session:
            event = NotificationEvent(
                user_id=message.user_id,
                location_id=message.location_id,
                notification_type=message.notification_type.value,
                status=NotificationStatus.PENDING.value,
            )
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event.id

    async def _finalize_event(
        self,
        event_id: int,
        *,
        status: NotificationStatus,
        telegram_message_id: int | None = None,
        error: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            event = await session.get(NotificationEvent, event_id)
            if event is None:
                return
            event.status = status.value
            event.telegram_message_id = telegram_message_id
            event.error = error
            if status == NotificationStatus.SENT:
                event.sent_at = datetime.now(UTC)
            await session.commit()

    async def _mark_user_blocked(self, telegram_id: int) -> None:
        async with self._session_factory() as session:
            from sqlalchemy import select

            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                return
            user.is_blocked = True
            user.is_active = False
            await session.commit()
            log.info("user_marked_blocked", telegram_id=telegram_id)
