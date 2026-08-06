"""Minimal health checks for process liveness."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class HealthReport:
    ok: bool
    checks: dict[str, bool]
    details: dict[str, str]
    checked_at: datetime


async def check_database(engine: AsyncEngine) -> tuple[bool, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        return False, type(exc).__name__


def check_disk(path: Path, *, min_free_mb: int = 100) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        disk = shutil.disk_usage(path)
        free_mb = disk.free // (1024 * 1024)
        return free_mb >= min_free_mb, f"free_mb={free_mb}"
    except Exception as exc:
        return False, type(exc).__name__


async def build_health_report(
    engine: AsyncEngine,
    *,
    data_dir: Path,
    monitoring_heartbeat_at: datetime | None,
    monitoring_stale_after_seconds: int = 300,
) -> HealthReport:
    db_ok, db_detail = await check_database(engine)
    disk_ok, disk_detail = check_disk(data_dir)

    now = datetime.now(UTC)
    if monitoring_heartbeat_at is None:
        mon_ok = False
        mon_detail = "never"
    else:
        age = (now - monitoring_heartbeat_at).total_seconds()
        mon_ok = age <= monitoring_stale_after_seconds
        mon_detail = f"age_seconds={int(age)}"

    checks = {
        "database": db_ok,
        "disk": disk_ok,
        "monitoring_heartbeat": mon_ok,
    }
    return HealthReport(
        ok=all(checks.values()),
        checks=checks,
        details={
            "database": db_detail,
            "disk": disk_detail,
            "monitoring_heartbeat": mon_detail,
        },
        checked_at=now,
    )
