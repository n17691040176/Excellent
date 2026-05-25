from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_DOWN, Decimal
from random import choices
from string import ascii_uppercase, digits
from uuid import uuid4


def now() -> datetime:
    return datetime.now()


def today() -> date:
    return date.today()


def generate_code(prefix: str = '', length: int = 8) -> str:
    body = ''.join(choices(ascii_uppercase + digits, k=length))
    return f'{prefix}{body}'


def generate_order_no(prefix: str) -> str:
    return f'{prefix}{datetime.now().strftime("%Y%m%d%H%M%S")}{uuid4().hex[:8].upper()}'


def quantize_amount(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
