"""Helpers for invite / share deep links."""

from __future__ import annotations

from urllib.parse import quote


def invite_start_payload(referrer_telegram_id: int) -> str:
    return f"ref_{referrer_telegram_id}"


def parse_invite_payload(payload: str | None) -> int | None:
    """Return referrer telegram_id from `/start ref_<id>`, else None."""
    if not payload:
        return None
    raw = payload.strip()
    if not raw.startswith("ref_"):
        return None
    value = raw[4:]
    if not value.isdigit():
        return None
    referrer_id = int(value)
    return referrer_id if referrer_id > 0 else None


def invite_bot_link(bot_username: str, referrer_telegram_id: int) -> str:
    username = bot_username.lstrip("@")
    return f"https://t.me/{username}?start={invite_start_payload(referrer_telegram_id)}"


def telegram_share_url(*, bot_username: str, referrer_telegram_id: int, text: str) -> str:
    """Open Telegram share sheet with invite link + prefilled message."""
    link = invite_bot_link(bot_username, referrer_telegram_id)
    return f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(text, safe='')}"
