"""Datetime helpers (SQLite drops tzinfo even on DateTime(timezone=True))."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time as an aware UTC datetime (portable across SQLite/PG)."""
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Return an aware UTC datetime; naive values are assumed to be UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_expired(expires_at: datetime | None, now: datetime | None = None) -> bool:
    """True when expires_at is missing or in the past (tz-safe)."""
    if expires_at is None:
        return True
    current = now or datetime.now(timezone.utc)
    return as_utc(expires_at) < current
