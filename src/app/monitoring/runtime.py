"""Shared monitoring runtime state (heartbeat for healthchecks)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MonitoringRuntimeState:
    last_cycle_finished_at: datetime | None = None
    last_successful_check_at: datetime | None = None
    last_cycle_error: str | None = None
    cycles_completed: int = 0
    # slug -> armed_from_no_slots
    armed_from_no_slots: dict[str, bool] = field(default_factory=dict)
