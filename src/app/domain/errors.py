"""Application-level error types."""

from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class ConfigurationError(AppError):
    """Invalid or incomplete configuration."""


class DomainError(AppError):
    """Business-rule violation."""


class NotFoundError(DomainError):
    """Requested entity does not exist."""


class ForbiddenError(DomainError):
    """Caller is not allowed to perform the action."""
