"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    AdminRole,
    CheckerType,
    LocationStatus,
    NotificationStatus,
    NotificationType,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default="uk")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="user")
    notification_events: Mapped[list[NotificationEvent]] = relationship(back_populates="user")


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    locations: Mapped[list[Location]] = relationship(back_populates="country")


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        Index("ix_locations_is_active", "is_active"),
        Index("ix_locations_country_id", "country_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    official_url: Mapped[str] = mapped_column(String(512), nullable=False)
    queue_url: Mapped[str] = mapped_column(String(512), nullable=False)
    checker_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CheckerType.BROWSER.value,
    )
    checker_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    current_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=LocationStatus.UNKNOWN.value,
    )
    previous_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=LocationStatus.UNKNOWN.value,
    )
    consecutive_available_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_failed_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_available_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    country: Mapped[Country] = relationship(back_populates="locations")
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="location")
    check_events: Mapped[list[CheckEvent]] = relationship(back_populates="location")
    notification_events: Mapped[list[NotificationEvent]] = relationship(back_populates="location")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "location_id", name="uq_subscriptions_user_location"),
        Index("ix_subscriptions_user_id", "user_id"),
        Index("ix_subscriptions_location_id", "location_id"),
        Index("ix_subscriptions_location_active", "location_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="subscriptions")
    location: Mapped[Location] = relationship(back_populates="subscriptions")


class CheckEvent(Base):
    __tablename__ = "check_events"
    __table_args__ = (Index("ix_check_events_location_created", "location_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    final_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    checker_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    location: Mapped[Location] = relationship(back_populates="check_events")


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        Index("ix_notification_events_user_created", "user_id", "created_at"),
        Index("ix_notification_events_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    notification_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=NotificationType.SLOTS_AVAILABLE.value,
    )
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=NotificationStatus.PENDING.value,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(back_populates="notification_events")
    location: Mapped[Location | None] = relationship(back_populates="notification_events")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=AdminRole.ADMIN.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
