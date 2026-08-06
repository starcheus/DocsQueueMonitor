"""Core user-facing handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.context import AppContext
from app.bot.keyboards import (
    cities_keyboard,
    confirm_privacy_delete_keyboard,
    confirm_unsubscribe_all_keyboard,
    countries_keyboard,
    language_keyboard,
    main_menu_keyboard,
    privacy_keyboard,
    subscriptions_keyboard,
)
from app.bot.texts import resolve_language, t
from app.database.models import Country, Location
from app.domain.enums import LocationStatus
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService

router = Router(name="user")


def _callback_message(callback: CallbackQuery) -> Message | None:
    if isinstance(callback.message, Message):
        return callback.message
    return None


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, app: AppContext) -> None:
    assert message.from_user is not None
    service = SubscriptionService(session)
    lang = resolve_language(message.from_user.language_code)
    user = await service.ensure_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        language_code=lang,
        source="telegram",
    )
    await message.answer(t(user.language_code, "start.welcome"))
    await message.answer(
        t(user.language_code, "start.choose_language"),
        reply_markup=language_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def on_language(callback: CallbackQuery, session: AsyncSession, app: AppContext) -> None:
    assert callback.from_user is not None
    assert callback.data is not None
    lang = callback.data.split(":", 1)[1]
    if lang not in {"uk", "ru", "en"}:
        await callback.answer()
        return
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=lang,
    )
    user.language_code = lang
    await session.flush()
    message = _callback_message(callback)
    if message is not None:
        await message.answer(
            f"{t(lang, 'start.welcome')}\n\n{t(lang, 'disclaimer.short')}",
            reply_markup=main_menu_keyboard(lang),
        )
        await message.answer(t(lang, "menu.title"))
    await callback.answer()


@router.message(F.text)
async def on_menu_text(message: Message, session: AsyncSession, app: AppContext) -> None:
    assert message.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        language_code=resolve_language(message.from_user.language_code),
    )
    lang = user.language_code
    text = message.text or ""

    # Match any language labels so switching language mid-session still works.
    all_labels = {
        key: {t(code, key) for code in ("uk", "ru", "en")}
        for key in [
            "menu.choose_cities",
            "menu.my_subs",
            "menu.status",
            "menu.language",
            "menu.how",
            "menu.privacy",
            "menu.contact",
        ]
    }

    if text in all_labels["menu.choose_cities"]:
        countries = list(
            (
                await session.scalars(
                    select(Country).where(Country.is_active.is_(True)).order_by(Country.sort_order),
                )
            ).all(),
        )
        await message.answer(
            t(lang, "countries.title"),
            reply_markup=countries_keyboard(lang, countries),
        )
        return

    if text in all_labels["menu.my_subs"]:
        await _send_subscriptions(message, session, user.id, lang)
        return

    if text in all_labels["menu.status"]:
        await _send_status(message, session, user.id, lang)
        return

    if text in all_labels["menu.language"]:
        await message.answer(t(lang, "start.choose_language"), reply_markup=language_keyboard())
        return

    if text in all_labels["menu.how"]:
        await message.answer(f"{t(lang, 'how.body')}\n\n{t(lang, 'disclaimer.short')}")
        return

    if text in all_labels["menu.privacy"]:
        await message.answer(
            t(lang, "privacy.body"),
            reply_markup=privacy_keyboard(lang),
        )
        return

    if text in all_labels["menu.contact"]:
        await message.answer(t(lang, "contact.body", contact=app.developer_contact))
        return


@router.callback_query(F.data == "countries")
async def on_countries(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    countries = list(
        (
            await session.scalars(
                select(Country).where(Country.is_active.is_(True)).order_by(Country.sort_order),
            )
        ).all(),
    )
    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(
            t(user.language_code, "countries.title"),
            reply_markup=countries_keyboard(user.language_code, countries),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("country:"))
async def on_country(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    assert callback.data is not None
    code = callback.data.split(":", 1)[1]
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    country = await session.scalar(select(Country).where(Country.code == code))
    if country is None:
        await callback.answer()
        return
    locations = list(
        (
            await session.scalars(
                select(Location)
                .where(Location.country_id == country.id, Location.is_active.is_(True))
                .order_by(Location.city),
            )
        ).all(),
    )
    subs = await service.list_active(user_id=user.id)
    subscribed = {s.location.slug for s in subs}
    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(
            t(user.language_code, "cities.title", country=country.name),
            reply_markup=cities_keyboard(
                user.language_code,
                country_code=country.code,
                country_name=country.name,
                locations=locations,
                subscribed_slugs=subscribed,
            ),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle:"))
async def on_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    assert callback.data is not None
    slug = callback.data.split(":", 1)[1]
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    location = await session.scalar(
        select(Location).where(Location.slug == slug).options(selectinload(Location.country)),
    )
    if location is None:
        await callback.answer()
        return

    existing = None
    for sub in await service.list_active(user_id=user.id):
        if sub.location_id == location.id:
            existing = sub
            break
    if existing is not None:
        await service.unsubscribe(user_id=user.id, location_slug=slug)
        await callback.answer(
            t(user.language_code, "cities.unsubscribed", city=location.display_name)
        )
    else:
        await service.subscribe(user_id=user.id, location_slug=slug)
        await callback.answer(
            t(user.language_code, "cities.subscribed", city=location.display_name)
        )

    # Refresh city keyboard
    country = location.country
    locations = list(
        (
            await session.scalars(
                select(Location)
                .where(Location.country_id == country.id, Location.is_active.is_(True))
                .order_by(Location.city),
            )
        ).all(),
    )
    subs = await service.list_active(user_id=user.id)
    subscribed = {s.location.slug for s in subs}
    message = _callback_message(callback)
    if message is not None:
        await message.edit_reply_markup(
            reply_markup=cities_keyboard(
                user.language_code,
                country_code=country.code,
                country_name=country.name,
                locations=locations,
                subscribed_slugs=subscribed,
            ),
        )


@router.callback_query(F.data.startswith("unsub:"))
async def on_unsub(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    assert callback.data is not None
    slug = callback.data.split(":", 1)[1]
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    await service.unsubscribe(user_id=user.id, location_slug=slug)
    if _callback_message(callback) is not None:
        await _edit_or_send_subscriptions(callback, session, user.id, user.language_code)
    await callback.answer()


@router.callback_query(F.data == "unsub_all:ask")
async def on_unsub_all_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(
            t(user.language_code, "subs.confirm_all"),
            reply_markup=confirm_unsubscribe_all_keyboard(user.language_code),
        )
    await callback.answer()


@router.callback_query(F.data == "unsub_all:yes")
async def on_unsub_all_yes(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    await service.unsubscribe_all(user_id=user.id)
    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(t(user.language_code, "subs.all_removed"))
    await callback.answer()


@router.callback_query(F.data == "unsub_all:no")
async def on_unsub_all_no(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    if _callback_message(callback) is not None:
        await _edit_or_send_subscriptions(callback, session, user.id, user.language_code)
    await callback.answer()


@router.callback_query(F.data.startswith("status:"))
async def on_status_one(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    assert callback.data is not None
    slug = callback.data.split(":", 1)[1]
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    location = await session.scalar(select(Location).where(Location.slug == slug))
    if location is None:
        await callback.answer()
        return
    text = _format_status_item(user.language_code, location)
    message = _callback_message(callback)
    if message is not None:
        await message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "privacy:ask")
async def on_privacy_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(
            t(user.language_code, "privacy.confirm"),
            reply_markup=confirm_privacy_delete_keyboard(user.language_code),
        )
    await callback.answer()


@router.callback_query(F.data == "privacy:yes")
async def on_privacy_yes(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    users = UserService(session)
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    await users.anonymize_user(telegram_id=callback.from_user.id)
    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(t(user.language_code, "privacy.deleted"))
    await callback.answer()


@router.callback_query(F.data == "privacy:no")
async def on_privacy_no(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    message = _callback_message(callback)
    if message is not None:
        await message.edit_text(
            t(user.language_code, "privacy.body"),
            reply_markup=privacy_keyboard(user.language_code),
        )
    await callback.answer()


@router.callback_query(F.data == "menu:home")
async def on_menu_home(callback: CallbackQuery, session: AsyncSession) -> None:
    assert callback.from_user is not None
    service = SubscriptionService(session)
    user = await service.ensure_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        language_code=resolve_language(callback.from_user.language_code),
    )
    message = _callback_message(callback)
    if message is not None:
        await message.answer(
            t(user.language_code, "menu.title"),
            reply_markup=main_menu_keyboard(user.language_code),
        )
    await callback.answer()


async def _send_subscriptions(
    message: Message,
    session: AsyncSession,
    user_id: int,
    lang: str,
) -> None:
    service = SubscriptionService(session)
    subs = await service.list_active(user_id=user_id)
    if not subs:
        await message.answer(t(lang, "subs.empty"))
        return
    lines = [t(lang, "subs.title")]
    for sub in subs:
        lines.append(t(lang, "subs.item", city=sub.location.display_name))
    await message.answer("\n".join(lines), reply_markup=subscriptions_keyboard(lang, subs))


async def _edit_or_send_subscriptions(
    callback: CallbackQuery,
    session: AsyncSession,
    user_id: int,
    lang: str,
) -> None:
    service = SubscriptionService(session)
    subs = await service.list_active(user_id=user_id)
    message = _callback_message(callback)
    if message is None:
        return
    if not subs:
        await message.edit_text(t(lang, "subs.empty"))
        return
    lines = [t(lang, "subs.title")]
    for sub in subs:
        lines.append(t(lang, "subs.item", city=sub.location.display_name))
    await message.edit_text(
        "\n".join(lines),
        reply_markup=subscriptions_keyboard(lang, subs),
    )


async def _send_status(message: Message, session: AsyncSession, user_id: int, lang: str) -> None:
    service = SubscriptionService(session)
    subs = await service.list_active(user_id=user_id)
    if not subs:
        await message.answer(t(lang, "status.empty"))
        return
    lines = [t(lang, "status.title")]
    for sub in subs:
        lines.append(_format_status_item(lang, sub.location))
        lines.append("")
    await message.answer("\n".join(lines).strip())


def _format_status_item(lang: str, location: Location) -> str:
    status_key = f"status.{LocationStatus(location.current_status).value}"
    checked = (
        location.last_checked_at.strftime("%Y-%m-%d %H:%M") if location.last_checked_at else "—"
    )
    available = (
        location.last_available_at.strftime("%Y-%m-%d %H:%M") if location.last_available_at else "—"
    )
    return t(
        lang,
        "status.item",
        city=location.display_name,
        status=t(lang, status_key),
        checked=checked,
        available=available,
    )
