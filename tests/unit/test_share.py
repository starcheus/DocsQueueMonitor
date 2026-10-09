"""Invite / share link helpers."""

from __future__ import annotations

from app.bot.share import (
    invite_bot_link,
    invite_start_payload,
    parse_invite_payload,
    telegram_share_url,
)


def test_invite_payload_roundtrip() -> None:
    assert invite_start_payload(252142674) == "ref_252142674"
    assert parse_invite_payload("ref_252142674") == 252142674
    assert parse_invite_payload("ref_0") is None
    assert parse_invite_payload("spam") is None
    assert parse_invite_payload(None) is None


def test_invite_bot_link() -> None:
    assert (
        invite_bot_link("Docs_Queue_Monitor_bot", 42)
        == "https://t.me/Docs_Queue_Monitor_bot?start=ref_42"
    )
    assert invite_bot_link("@Docs_Queue_Monitor_bot", 42).startswith("https://t.me/Docs_Queue_Monitor_bot")


def test_telegram_share_url_contains_link_and_text() -> None:
    url = telegram_share_url(
        bot_username="Docs_Queue_Monitor_bot",
        referrer_telegram_id=42,
        text="Hello bot",
    )
    assert url.startswith("https://t.me/share/url?")
    assert "Docs_Queue_Monitor_bot" in url
    assert "ref_42" in url
    assert "Hello" in url
