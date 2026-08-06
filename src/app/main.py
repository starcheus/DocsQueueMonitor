"""Application entrypoint: Telegram bot + monitoring + health."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys
from pathlib import Path

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp.web import AppRunner

from app.bot.context import AppContext
from app.bot.handlers.user import router as user_router
from app.bot.middlewares.db import DbSessionMiddleware
from app.config import get_settings
from app.database.session import create_engine, create_session_factory
from app.health.server import start_health_server, stop_health_server
from app.locations.seed import seed_countries_and_locations
from app.logging import get_logger, setup_logging
from app.monitoring.checkers.browser import BrowserAvailabilityChecker
from app.monitoring.checkers.html import HtmlAvailabilityChecker
from app.monitoring.checkers.registry import CheckerRegistry
from app.monitoring.runtime import MonitoringRuntimeState
from app.monitoring.scheduler import MonitoringScheduler
from app.monitoring.service import MonitoringService
from app.monitoring.state_machine import AvailabilityStateMachine
from app.notifications.queue import NotificationQueue
from app.notifications.service import NotificationService


async def run_bot() -> int:
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    log = get_logger("app.main")

    if not settings.has_bot_token:
        log.error("telegram_bot_token_missing")
        return 1

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        counts = await seed_countries_and_locations(session)
        await session.commit()
    log.info("seed_completed", **counts)

    runtime = MonitoringRuntimeState()
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    notify_queue = NotificationQueue(
        bot=bot,
        session_factory=session_factory,
        concurrency=settings.telegram_send_concurrency,
    )
    notifications = NotificationService(
        session_factory=session_factory,
        queue=notify_queue,
        admin_telegram_ids=settings.admin_telegram_ids,
    )

    browser = BrowserAvailabilityChecker(
        enabled=settings.playwright_enabled,
        timeout_seconds=settings.request_timeout_seconds,
        user_agent=settings.user_agent,
    )
    http_client = httpx.AsyncClient()
    html_checker = HtmlAvailabilityChecker(
        client=http_client,
        timeout_seconds=settings.request_timeout_seconds,
        user_agent=settings.user_agent,
    )
    registry = CheckerRegistry(settings=settings, browser=browser, html=html_checker)
    state_machine = AvailabilityStateMachine(
        availability_confirmations=settings.availability_confirmations,
    )

    async def on_available(location_id: int) -> None:
        await notifications.notify_slots_available(location_id)

    async def on_admin_alert(location_id: int, reason: str | None) -> None:
        await notifications.alert_admins(
            text=f"DocsQueueMonitor alert: location_id={location_id} reason={reason or 'n/a'}",
        )

    monitoring = MonitoringService(
        session_factory=session_factory,
        checkers=registry,
        state_machine=state_machine,
        settings=settings,
        runtime=runtime,
        on_available=on_available,
        on_admin_alert=on_admin_alert,
    )
    scheduler = MonitoringScheduler(service=monitoring, settings=settings, runtime=runtime)

    app_ctx = AppContext(
        settings=settings,
        monitoring=monitoring,
        notifications=notifications,
        runtime=runtime,
        developer_contact="@proigor",
    )
    dp["app"] = app_ctx
    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp.include_router(user_router)

    health_runner: AppRunner | None = None
    stop_event = asyncio.Event()

    def _request_stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, _request_stop)

    await browser.start()
    notify_queue.start()
    if settings.monitoring_enabled:
        scheduler.start()

    health_runner = await start_health_server(
        host="127.0.0.1",
        port=settings.healthcheck_port,
        engine=engine,
        data_dir=Path("data"),
        runtime=runtime,
        monitoring_stale_after_seconds=settings.monitoring_interval_seconds * 4,
    )

    log.info("bot_starting", monitoring=settings.monitoring_enabled)

    polling_task = asyncio.create_task(
        dp.start_polling(bot, handle_signals=False),
        name="telegram-polling",
    )
    stopper = asyncio.create_task(stop_event.wait(), name="stop-waiter")
    done, _pending = await asyncio.wait(
        {polling_task, stopper},
        return_when=asyncio.FIRST_COMPLETED,
    )

    log.info("shutdown_started")
    stop_event.set()
    await scheduler.stop()
    await notify_queue.stop()
    await browser.stop()
    await http_client.aclose()
    if health_runner is not None:
        await stop_health_server(health_runner)

    if not polling_task.done():
        await dp.stop_polling()
        try:
            await asyncio.wait_for(polling_task, timeout=15)
        except TimeoutError:
            polling_task.cancel()
    for task in done:
        if task is polling_task and task.cancelled():
            pass
        elif task is polling_task and task.exception():
            log.error("polling_failed", error=repr(task.exception()))

    await bot.session.close()
    await engine.dispose()
    log.info("shutdown_complete")
    return 0


async def run_seed_only() -> int:
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)
    log = get_logger("app.main")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        counts = await seed_countries_and_locations(session)
        await session.commit()
    await engine.dispose()
    log.info("seed_completed", **counts)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="docsqueuemonitor")
    parser.add_argument("--seed", action="store_true", help="Seed MVP locations and exit")
    parser.add_argument("--check-config", action="store_true", help="Print non-secret config")
    parser.add_argument("--run", action="store_true", help="Run bot + monitoring")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.seed and not args.run:
        raise SystemExit(asyncio.run(run_seed_only()))
    if args.check_config and not args.run:
        settings = get_settings()
        setup_logging(level=settings.log_level, log_format=settings.log_format)
        log = get_logger("app.main")
        log.info(
            "config_ok",
            has_bot_token=settings.has_bot_token,
            monitoring_enabled=settings.monitoring_enabled,
            playwright_enabled=settings.playwright_enabled,
            default_language=settings.default_language,
            admin_count=len(settings.admin_telegram_ids),
        )
        raise SystemExit(0)
    # Default: run the service.
    raise SystemExit(asyncio.run(run_bot()))


if __name__ == "__main__":
    main(sys.argv[1:])
