from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal
from random import choices
from string import ascii_uppercase, digits
from typing import Any
from uuid import uuid4

SHANGHAI_TIMEZONE = timezone(timedelta(hours=8))


def now() -> datetime:
    """Return the canonical database timestamp: naive UTC."""
    return datetime.now(UTC).replace(tzinfo=None)


def business_now() -> datetime:
    """Return the current China business time with an explicit offset."""
    return datetime.now(SHANGHAI_TIMEZONE)


def today() -> date:
    """Return the China business date, independent of the server timezone."""
    return business_now().date()


def unix_timestamp() -> int:
    """Return epoch seconds without depending on the host timezone."""
    return int(datetime.now(UTC).timestamp())


def utc_naive(value: datetime | None, *, naive_timezone=UTC) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=naive_timezone)
    return value.astimezone(UTC).replace(tzinfo=None)


def iso_datetime(value: Any) -> str | None:
    """Serialize database datetimes with an explicit offset.

    MySQL DATETIME values are stored as naive UTC in this project. Explicitly
    adding the UTC offset prevents clients from treating them as local time.
    """
    if not value:
        return None
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def generate_code(prefix: str = '', length: int = 8) -> str:
    body = ''.join(choices(ascii_uppercase + digits, k=length))
    return f'{prefix}{body}'


def generate_order_no(prefix: str) -> str:
    china_time = business_now()
    return f'{prefix}{china_time.strftime("%Y%m%d%H%M%S")}{uuid4().hex[:8].upper()}'


def quantize_amount(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
