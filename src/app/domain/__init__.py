"""Domain package exports."""

from app.domain.entities import CheckResult, TransitionDecision
from app.domain.enums import (
    AdminRole,
    CheckerType,
    CheckOutcome,
    LocationStatus,
    NotificationStatus,
    NotificationType,
)
from app.domain.errors import (
    AppError,
    ConfigurationError,
    DomainError,
    ForbiddenError,
    NotFoundError,
)

__all__ = [
    "AdminRole",
    "AppError",
    "CheckOutcome",
    "CheckResult",
    "CheckerType",
    "ConfigurationError",
    "DomainError",
    "ForbiddenError",
    "LocationStatus",
    "NotFoundError",
    "NotificationStatus",
    "NotificationType",
    "TransitionDecision",
]
