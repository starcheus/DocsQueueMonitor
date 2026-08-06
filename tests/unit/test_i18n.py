"""Localization helpers."""

from __future__ import annotations

from app.bot.texts import resolve_language, t


def test_resolve_language_defaults_to_uk() -> None:
    assert resolve_language(None) == "uk"
    assert resolve_language("de") == "uk"
    assert resolve_language("ru-RU") == "ru"
    assert resolve_language("en-US") == "en"
    assert resolve_language("uk") == "uk"


def test_translation_interpolation() -> None:
    text = t("uk", "cities.subscribed", city="Прага")
    assert "Прага" in text
    assert t("en", "menu.title") == "Main menu"
