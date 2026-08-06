"""Bot dependency container stored in workflow_data."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.monitoring.runtime import MonitoringRuntimeState
from app.monitoring.service import MonitoringService
from app.notifications.service import NotificationService


@dataclass(slots=True)
class AppContext:
    settings: Settings
    monitoring: MonitoringService
    notifications: NotificationService
    runtime: MonitoringRuntimeState
    developer_contact: str = "@proigor"
