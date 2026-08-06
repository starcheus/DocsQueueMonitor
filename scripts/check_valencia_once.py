"""Manual Valencia check using production BrowserAvailabilityChecker."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.config import clear_settings_cache, get_settings
from app.database.models import Location
from app.database.session import create_engine, create_session_factory
from app.monitoring.checkers.browser import BrowserAvailabilityChecker


async def main() -> None:
    clear_settings_cache()
    settings = get_settings()
    print("UA:", settings.user_agent)
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    async with factory() as session:
        loc = await session.scalar(select(Location).where(Location.slug == "valencia"))
        assert loc is not None
        print("url:", loc.queue_url)

    checker = BrowserAvailabilityChecker(
        enabled=True,
        timeout_seconds=settings.request_timeout_seconds,
        user_agent=settings.user_agent,
        headless=True,
    )
    await checker.start()
    try:
        result = await checker.check(loc)
        print(
            "result",
            result.outcome.value,
            result.reason,
            result.response_status,
            result.response_time_ms,
            result.final_url,
        )
    finally:
        await checker.stop()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
