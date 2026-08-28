"""Helpers for deriving provider request context from an HTTP request.

The payment endpoints need a client IP for WeChat H5 orders.  Keep the
extraction in one place so the order and cart paths apply the same validation
and precedence rules.  Values supplied in a JSON request body are deliberately
not considered here; they are not trustworthy network context.
"""

from __future__ import annotations

import ipaddress
from typing import Any


def _valid_ip(value: Any) -> str | None:
    """Return a canonical IP string when *value* is a bare valid address."""
    candidate = str(value or '').strip().strip('"\'')
    if not candidate or '%' in candidate:
        return None
    # X-Forwarded-For normally contains bare addresses.  Accept bracketed
    # IPv6 as a small interoperability concession, but do not guess at
    # arbitrary host:port formats because that can turn malformed input into
    # a different address.
    if candidate.startswith('[') and candidate.endswith(']'):
        candidate = candidate[1:-1].strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _header_values(request: Any, name: str) -> list[str]:
    headers = getattr(request, 'headers', None)
    if headers is None:
        return []
    try:
        raw = headers.get(name, '')
    except (AttributeError, TypeError):
        return []
    # Starlette's ``Headers`` is case-insensitive, while lightweight request
    # doubles and a few ASGI adapters expose a regular mapping.  Keep the
    # behavior identical for both forms.
    if not raw:
        try:
            raw = next(
                (value for key, value in headers.items() if str(key).lower() == name),
                '',
            )
        except (AttributeError, TypeError):
            raw = ''
    if not raw:
        return []
    raw_values = raw if isinstance(raw, list | tuple) else (raw,)
    values: list[str] = []
    for raw_value in raw_values:
        values.extend(part.strip() for part in str(raw_value).split(',') if part.strip())
    return values


def get_request_client_ip(request: Any) -> str:
    """Extract a valid client IP from a FastAPI/Starlette request.

    The deployment proxy's ``X-Real-IP`` is preferred, followed by the first
    valid address in ``X-Forwarded-For``.  If neither header contains a valid
    address, the direct socket peer is used.  An empty string is returned when
    no usable address is available.
    """
    for header_name in ('x-real-ip', 'x-forwarded-for'):
        for candidate in _header_values(request, header_name):
            normalized = _valid_ip(candidate)
            if normalized:
                return normalized

    peer = getattr(getattr(request, 'client', None), 'host', None)
    return _valid_ip(peer) or ''


def build_payment_request_context(request: Any) -> dict[str, str]:
    """Build the non-spoofable context persisted with an external payment."""
    context: dict[str, str] = {}
    client_ip = get_request_client_ip(request)
    if client_ip:
        context['client_ip'] = client_ip
    headers = getattr(request, 'headers', None)
    try:
        user_agent = str((headers.get('user-agent', '') if headers is not None else '') or '').strip()
    except (AttributeError, TypeError):
        user_agent = ''
    if user_agent:
        context['user_agent'] = user_agent[:512]
    return context
