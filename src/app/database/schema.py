"""Lightweight schema fixes for SQLite without full Alembic churn."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.logging import get_logger

log = get_logger(__name__)


async def ensure_runtime_schema(engine: AsyncEngine) -> None:
    """Add columns introduced after the initial migration when missing."""
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(locations)"))
        columns = {row[1] for row in result.fetchall()}
        if "last_available_dates" not in columns:
            await conn.execute(
                text("ALTER TABLE locations ADD COLUMN last_available_dates JSON"),
            )
            log.info("schema_column_added", table="locations", column="last_available_dates")
