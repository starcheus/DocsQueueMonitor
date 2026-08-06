"""One-shot test: send a real slots-available notification for Prague."""

from __future__ import annotations

import asyncio
import sys

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.bot.texts import t
from app.bot.timefmt import format_user_datetime
from app.config import clear_settings_cache, get_settings
from app.database.models import Location, Subscription, User
from app.database.session import create_engine, create_session_factory


async def main() -> int:
    clear_settings_cache()
    settings = get_settings()
    if not settings.has_bot_token:
        print("TELEGRAM_BOT_TOKEN missing", file=sys.stderr)
        return 1

    engine = create_engine(settings)
    factory = create_session_factory(engine)
    async with factory() as session:
        location = await session.scalar(
            select(Location)
            .where(Location.slug == "prague")
            .options(selectinload(Location.country)),
        )
        if location is None:
            print("prague not found", file=sys.stderr)
            return 1
        rows = (
            await session.execute(
                select(Subscription, User)
                .join(User, User.id == Subscription.user_id)
                .where(
                    Subscription.location_id == location.id,
                    Subscription.is_active.is_(True),
                    User.is_active.is_(True),
                    User.is_blocked.is_(False),
                ),
            )
        ).all()

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    sent = 0
    try:
        for sub, user in rows:
            lang = user.language_code or "uk"
            checked = format_user_datetime(
                location.last_checked_at,
                lang=lang,
                with_date=False,
            )
            text = t(
                lang,
                "notify.slots_available",
                city=location.display_name,
                country=location.country.name if location.country else "",
                checked_at=checked,
            )
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=t(lang, "notify.btn_open_site"),
                            url=location.queue_url,
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=t(lang, "notify.btn_unsubscribe", city=location.display_name),
                            callback_data=f"unsub:{location.slug}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text=t(lang, "notify.btn_status"),
                            callback_data=f"status:{location.slug}",
                        ),
                    ],
                ],
            )
            await bot.send_message(user.telegram_id, text, reply_markup=markup)
            print(f"sent to telegram_id={user.telegram_id} lang={lang}")
            sent += 1
    finally:
        await bot.session.close()
        await engine.dispose()

    print(f"done sent={sent}")
    return 0 if sent else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
