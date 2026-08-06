"""Domain enumerations shared across the application."""

from __future__ import annotations

from enum import StrEnum


class LocationStatus(StrEnum):
    UNKNOWN = "unknown"
    NO_SLOTS = "no_slots"
    POSSIBLY_AVAILABLE = "possibly_available"
    AVAILABLE = "available"
    ERROR = "error"
    DISABLED = "disabled"


class CheckerType(StrEnum):
    BROWSER = "browser"
    HTML = "html"
    API = "api"
    DISABLED = "disabled"


class NotificationType(StrEnum):
    SLOTS_AVAILABLE = "slots_available"
    ADMIN_ALERT = "admin_alert"
    BROADCAST = "broadcast"
    TEST = "test"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AdminRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"


class CheckOutcome(StrEnum):
    """Fine-grained checker outcome before state-machine mapping."""

    NO_SLOTS = "no_slots"
    POSSIBLY_AVAILABLE = "possibly_available"
    AVAILABLE = "available"
    PAGE_UNAVAILABLE = "page_unavailable"
    STRUCTURE_CHANGED = "structure_changed"
    CAPTCHA = "captcha"
    SERVER_ERROR = "server_error"
    EMPTY_RESPONSE = "empty_response"
    REDIRECT = "redirect"
    LOCATION_GONE = "location_gone"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"
