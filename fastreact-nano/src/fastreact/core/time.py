"""Time helpers for timezone-aware UTC timestamps."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """Return the current UTC timestamp as seconds since epoch."""
    return utc_now().timestamp()


def utc_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return utc_now().isoformat()
