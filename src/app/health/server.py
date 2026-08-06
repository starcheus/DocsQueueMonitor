"""Minimal localhost health HTTP endpoint."""

from __future__ import annotations

import json
from pathlib import Path

from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncEngine

from app.health.checks import build_health_report
from app.logging import get_logger
from app.monitoring.runtime import MonitoringRuntimeState

log = get_logger(__name__)


async def start_health_server(
    *,
    host: str,
    port: int,
    engine: AsyncEngine,
    data_dir: Path,
    runtime: MonitoringRuntimeState,
    monitoring_stale_after_seconds: int,
) -> web.AppRunner:
    async def handle_health(_: web.Request) -> web.Response:
        report = await build_health_report(
            engine,
            data_dir=data_dir,
            monitoring_heartbeat_at=runtime.last_cycle_finished_at,
            monitoring_stale_after_seconds=monitoring_stale_after_seconds,
        )
        # For open beta / first boot, allow ok=false on monitoring until first cycle.
        payload = {
            "ok": report.ok or runtime.cycles_completed == 0,
            "checks": report.checks,
            "details": report.details,
            "checked_at": report.checked_at.isoformat(),
            "cycles_completed": runtime.cycles_completed,
        }
        status = 200 if payload["ok"] else 503
        return web.Response(
            text=json.dumps(payload, ensure_ascii=False),
            content_type="application/json",
            status=status,
        )

    app = web.Application()
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    log.info("health_server_started", host=host, port=port)
    return runner


async def stop_health_server(runner: web.AppRunner) -> None:
    await runner.cleanup()
