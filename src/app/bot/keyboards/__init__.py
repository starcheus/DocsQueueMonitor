"""Inline and reply keyboards."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.bot.texts import t
from app.database.models import Country, Location, Subscription


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Українська", callback_data="lang:uk"),
                InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="English", callback_data="lang:en"),
            ],
        ],
    )


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "menu.choose_cities"))],
            [
                KeyboardButton(text=t(lang, "menu.my_subs")),
                KeyboardButton(text=t(lang, "menu.status")),
            ],
            [
                KeyboardButton(text=t(lang, "menu.language")),
                KeyboardButton(text=t(lang, "menu.how")),
            ],
            [
                KeyboardButton(text=t(lang, "menu.privacy")),
                KeyboardButton(text=t(lang, "menu.contact")),
            ],
        ],
        resize_keyboard=True,
    )


def countries_keyboard(lang: str, countries: list[Country]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=country.name, callback_data=f"country:{country.code}")]
        for country in countries
        if country.is_active
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cities_keyboard(
    lang: str,
    *,
    country_code: str,
    country_name: str,
    locations: list[Location],
    subscribed_slugs: set[str],
) -> InlineKeyboardMarkup:
    _ = country_name
    rows: list[list[InlineKeyboardButton]] = []
    for location in locations:
        if not location.is_active:
            continue
        mark = "✅ " if location.slug in subscribed_slugs else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark}{location.display_name}",
                    callback_data=f"toggle:{location.slug}",
                ),
            ],
        )
    rows.append(
        [
            InlineKeyboardButton(text=t(lang, "back"), callback_data="countries"),
            InlineKeyboardButton(text=t(lang, "done"), callback_data="menu:home"),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscriptions_keyboard(lang: str, subscriptions: list[Subscription]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for sub in subscriptions:
        city = sub.location.display_name
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "subs.unsubscribe", city=city),
                    callback_data=f"unsub:{sub.location.slug}",
                ),
            ],
        )
    if subscriptions:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "subs.unsubscribe_all"),
                    callback_data="unsub_all:ask",
                ),
            ],
        )
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_unsubscribe_all_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "subs.confirm_yes"),
                    callback_data="unsub_all:yes",
                ),
                InlineKeyboardButton(
                    text=t(lang, "subs.confirm_no"),
                    callback_data="unsub_all:no",
                ),
            ],
        ],
    )


def privacy_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "privacy.delete"), callback_data="privacy:ask")],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:home")],
        ],
    )


def confirm_privacy_delete_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "privacy.confirm_yes"),
                    callback_data="privacy:yes",
                ),
                InlineKeyboardButton(
                    text=t(lang, "privacy.confirm_no"),
                    callback_data="privacy:no",
                ),
            ],
        ],
    )
