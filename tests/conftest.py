"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Settings, clear_settings_cache
from app.database.models import Base
from app.database.session import create_engine, create_session_factory
from app.locations.seed import seed_countries_and_locations


@pytest.fixture()
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "1,2")
    monkeypatch.setenv("DEFAULT_LANGUAGE", "uk")
    monkeypatch.setenv("LOG_FORMAT", "console")
    clear_settings_cache()
    return Settings()


@pytest.fixture()
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture()
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def seeded_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        await seed_countries_and_locations(session)
        await session.commit()
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "html"
