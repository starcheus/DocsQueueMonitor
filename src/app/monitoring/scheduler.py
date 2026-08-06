"""Async monitoring scheduler with jitter and concurrency limits."""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime

from app.config import Settings
from app.logging import get_logger
from app.monitoring.runtime import MonitoringRuntimeState
from app.monitoring.service import MonitoringService

log = get_logger(__name__)


class MonitoringScheduler:
    def __init__(
        self,
        *,
        service: MonitoringService,
        settings: Settings,
        runtime: MonitoringRuntimeState,
    ) -> None:
        self._service = service
        self._settings = settings
        self._runtime = runtime
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="monitoring-scheduler")
        log.info("monitoring_scheduler_started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None
        log.info("monitoring_scheduler_stopped")

    async def _run(self) -> None:
        # Stagger first cycle slightly so bot can come online.
        await asyncio.sleep(2)
        while not self._stop.is_set():
            try:
                count = await self._service.check_all_active()
                self._runtime.cycles_completed += 1
                self._runtime.last_cycle_finished_at = datetime.now(UTC)
                self._runtime.last_cycle_error = None
                log.info("monitoring_cycle_done", locations=count)
            except Exception as exc:
                self._runtime.last_cycle_error = type(exc).__name__
                log.exception("monitoring_cycle_failed", error=type(exc).__name__)

            delay = self._settings.monitoring_interval_seconds
            jitter = random.uniform(0, self._settings.monitoring_jitter_seconds)
            # Backoff when the last cycle failed.
            if self._runtime.last_cycle_error:
                delay = min(delay * 2, 600)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay + jitter)
            except TimeoutError:
                continue
