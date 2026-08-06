"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return
    # sqlite+aiosqlite:///data/bot.db → relative path data/bot.db
    prefix = "sqlite+aiosqlite:///"
    if database_url.startswith(prefix):
        raw_path = database_url.removeprefix(prefix)
        if raw_path and raw_path != ":memory:" and not raw_path.startswith("//"):
            path = Path(raw_path)
            path.parent.mkdir(parents=True, exist_ok=True)


def create_engine(settings: Settings) -> AsyncEngine:
    _ensure_sqlite_parent(settings.database_url)
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_async_engine(
        settings.database_url,
        echo=False,
        connect_args=connect_args,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
