from __future__ import annotations

import base64
import binascii
import ipaddress
import json
from collections.abc import Mapping
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from string import Formatter
from typing import Any, cast
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import parse_qsl, quote, quote_plus, urlencode, urlparse, urlsplit, urlunsplit
from uuid import uuid4

from cryptography import x509
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.payment_config import (
    UNPAID_ORDER_EXPIRE_MINUTES,
    AlipayConfig,
    WechatPayConfig,
    alipay_certificate_sn,
    alipay_root_certificate_sn,
    alipay_sandbox_query_bypass_enabled,
    load_alipay_certificates,
    payment_config,
)
from app.models.enums import OrderStatus, OrderType, PaymentChannel, PaymentStatus, PayStatus, RefundStatus
from app.models.order import Order
from app.models.payment import PaymentRefund, PaymentTransaction
from app.utils.helpers import business_now, now, quantize_amount, unix_timestamp

WECHAT_API_BASE_URL = 'https://api.mch.weixin.qq.com'
WECHAT_NOTIFY_TIMESTAMP_TOLERANCE_SECONDS = 300
WECHAT_DEFAULT_PAYER_CLIENT_IP = '127.0.0.1'
WECHAT_DEFAULT_USER_AGENT = 'Mozilla/5.0 (compatible; Excellent/1.0)'
WECHAT_DEFAULT_H5_TYPE = 'WAP'
WECHAT_REFUND_DEFAULT_REASON = '订单退款'
WECHAT_REFUND_MAX_REASON_BYTES = 80
WECHAT_REFUND_RETRY_MINUTES = 1
WECHAT_REFUND_RECONCILE_BATCH_SIZE = 50
WECHAT_H5_TYPE_ALIASES = {
    'WAP': 'Wap',
    'WEB': 'Wap',
    'IOS': 'iOS',
    'APP': 'Android',
    'ANDROID': 'Android',
}


class WechatApiError(ConflictError):
    """A provider request failure with enough context for refund retries."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        retryable: bool = False,
        response_payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.retryable = retryable
        self.response_payload = response_payload or {}


class PaymentService:
    @staticmethod
    def _provider_name(channel: PaymentChannel) -> str:
        return 'wxpay' if channel == PaymentChannel.WECHAT else 'alipay'

    @staticmethod
    def _make_out_trade_no(order: Order, channel: PaymentChannel) -> str:
        suffix = uuid4().hex[:16].upper()
        return f'PAY{channel.value[:2]}{order.id:06d}{suffix}'

    @staticmethod
    def _provider_config(channel: PaymentChannel) -> WechatPayConfig | AlipayConfig:
        return payment_config.wechat if channel == PaymentChannel.WECHAT else payment_config.alipay

    @staticmethod
    def _subject(order: Order) -> str:
        prefix = payment_config.wechat.app_pay_subject_prefix or payment_config.alipay.app_pay_subject_prefix or 'Excellent'
        if order.order_type == OrderType.PACKAGE_ORDER:
            return f'{prefix} 套餐支付'
        if order.order_type == OrderType.LOCAL_LIFE_ORDER:
            return f'{prefix} 本地生活支付'
        return f'{prefix} 订单支付'

    @staticmethod
    def _ensure_transaction(
        db: Session,
        order: Order,
        channel: PaymentChannel,
        request_payload: dict | None = None,
    ) -> PaymentTransaction:
        tx = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.order_id == order.id,
                PaymentTransaction.channel == channel,
                PaymentTransaction.status == PaymentStatus.PENDING,
            )
            .order_by(PaymentTransaction.id.desc())
            .first()
        )
        if tx:
            tx.request_payload = request_payload or tx.request_payload
            return tx

        tx = PaymentTransaction(
            order_id=order.id,
            order_no=order.order_no,
            channel=channel,
            status=PaymentStatus.PENDING,
            currency=payment_config.default_currency,
            amount=quantize_amount(order.payable_amount),
            out_trade_no=PaymentService._make_out_trade_no(order, channel),
            request_payload=request_payload or {},
        )
        db.add(tx)
        db.flush()
        return tx

    @staticmethod
    def _key_candidates(path: str, labels: tuple[str, ...]) -> list[bytes]:
        key_path = Path(path)
        if not key_path.is_file():
            raise ConflictError(f'Payment key not found: {path}')
        raw = key_path.read_bytes()
        try:
            text = raw.decode('utf-8-sig').strip()
        except UnicodeDecodeError:
            return [raw]
        if text.startswith('-----BEGIN'):
            return [text.encode('utf-8')]

        compact = ''.join(text.split())
        return [
            f'-----BEGIN {label}-----\n{compact}\n-----END {label}-----\n'.encode()
            for label in labels
        ]

    @staticmethod
    def _load_private_key(path: str):
        last_error: Exception | None = None
        for candidate in PaymentService._key_candidates(path, ('PRIVATE KEY', 'RSA PRIVATE KEY')):
            try:
                return serialization.load_pem_private_key(candidate, password=None)
            except (TypeError, ValueError) as exc:
                last_error = exc
        raise ConflictError('Payment private key format is invalid') from last_error

    @staticmethod
    def _load_certificate_public_key(path: str, certificate_sn: str | None = None):
        certificate_path = Path(path)
        if not certificate_path.is_file():
            raise ConflictError(f'Payment certificate not found: {path}')
        try:
            certificates = x509.load_pem_x509_certificates(certificate_path.read_bytes())
        except ValueError as exc:
            raise ConflictError('Payment certificate format is invalid') from exc
        if not certificates:
            raise ConflictError('Payment certificate is empty')
        normalized_sn = str(certificate_sn or '').strip().lower()
        if normalized_sn:
            for certificate in certificates:
                if alipay_certificate_sn(certificate).lower() == normalized_sn:
                    return certificate.public_key()
            available_sns = ','.join(alipay_certificate_sn(certificate) for certificate in certificates)
            raise ConflictError(
                'Alipay response certificate does not match ALIPAY_PUBLIC_CERT_PATH '
                f'(response={normalized_sn}, configured={available_sns})'
            )
        return certificates[0].public_key()

    @staticmethod
    def _rsa_sign(private_key, message: str) -> str:
        signature = private_key.sign(
            message.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def _wechat_authorization_header(
        method: str,
        canonical_url: str,
        body: str,
        config: WechatPayConfig,
        nonce: str,
        timestamp: str,
    ) -> str:
        private_key = PaymentService._load_private_key(config.merchant_private_key_path)
        message = f'{method}\n{canonical_url}\n{timestamp}\n{nonce}\n{body}\n'
        signature = PaymentService._rsa_sign(private_key, message)
        return (
            'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{config.mchid}",nonce_str="{nonce}",timestamp="{timestamp}",'
            f'serial_no="{config.merchant_serial_no}",signature="{signature}"'
        )

    @staticmethod
    def _wechat_request_json(
        url: str,
        body: dict[str, Any] | None,
        config: WechatPayConfig,
        *,
        method: str = 'POST',
    ) -> dict[str, Any]:
        """Call a WeChat API endpoint and return its decoded JSON object."""
        _status, response = PaymentService._wechat_request_json_with_status(
            url,
            body,
            config,
            method=method,
        )
        return response

    @staticmethod
    def _wechat_request_json_with_status(
        url: str,
        body: dict[str, Any] | None,
        config: WechatPayConfig,
        *,
        method: str = 'POST',
    ) -> tuple[int, dict[str, Any]]:
        """Call a WeChat API and preserve HTTP/retry information.

        Refund requests are idempotent but may time out after the provider has
        accepted them.  The regular payment helper keeps its historical
        ``ConflictError`` contract; this companion exposes a typed error so a
        refund can retain the same ``out_refund_no`` and be queried later.
        """
        normalized_method = str(method or 'POST').upper()
        if normalized_method not in {'GET', 'POST'}:
            raise ConflictError(f'Unsupported WeChat request method: {normalized_method}')
        payload = (
            json.dumps(body, ensure_ascii=False, separators=(',', ':'))
            if body is not None
            else ''
        )
        nonce = uuid4().hex
        timestamp = str(unix_timestamp())
        parsed = urlparse(url)
        canonical_url = parsed.path or '/'
        if parsed.query:
            canonical_url = f'{canonical_url}?{parsed.query}'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': PaymentService._wechat_authorization_header(
                normalized_method,
                canonical_url,
                payload,
                config,
                nonce,
                timestamp,
            ),
            'Wechatpay-Serial': config.merchant_serial_no,
        }
        req = urlrequest.Request(
            url,
            data=payload.encode('utf-8') if normalized_method != 'GET' else None,
            headers=headers,
            method=normalized_method,
        )
        try:
            with urlrequest.urlopen(req, timeout=payment_config.request_timeout_seconds) as resp:
                response_bytes = resp.read()
                response_status = int(getattr(resp, 'status', 200) or 200)
                PaymentService._wechat_verify_platform_signature(
                    response_bytes,
                    getattr(resp, 'headers', None),
                    config,
                    source='response',
                )
                try:
                    response_body = response_bytes.decode('utf-8')
                except UnicodeDecodeError as exc:
                    raise WechatApiError(
                        'WeChat payment response is not valid UTF-8',
                        http_status=response_status,
                        retryable=True,
                    ) from exc
        except urlerror.HTTPError as exc:
            response_bytes = exc.read()
            PaymentService._wechat_verify_platform_signature(
                response_bytes,
                getattr(exc, 'headers', None),
                config,
                source='response',
            )
            response_body = response_bytes.decode('utf-8', errors='replace')
            try:
                error_payload = json.loads(response_body) if response_body else {}
            except json.JSONDecodeError:
                error_payload = {}
            if not isinstance(error_payload, dict):
                error_payload = {}
            status = int(getattr(exc, 'code', 0) or 0) or None
            raise WechatApiError(
                f'WeChat payment request failed: {response_body or exc.reason}',
                http_status=status,
                retryable=bool(status is None or status >= 500 or status in {408, 409, 429}),
                response_payload=error_payload,
            ) from exc
        except urlerror.URLError as exc:
            raise WechatApiError(
                f'WeChat payment request failed: {exc.reason}',
                retryable=True,
            ) from exc
        except TimeoutError as exc:
            raise WechatApiError(
                'WeChat payment request timed out',
                retryable=True,
            ) from exc
        if not response_body:
            return response_status, {}
        try:
            parsed_response = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise WechatApiError(
                'WeChat payment response is invalid JSON',
                http_status=response_status,
                retryable=True,
            ) from exc
        if not isinstance(parsed_response, dict):
            raise WechatApiError(
                'WeChat payment response must be a JSON object',
                http_status=response_status,
                retryable=True,
            )
        return response_status, parsed_response

    @staticmethod
    def _wechat_request_context(tx: PaymentTransaction) -> tuple[str, str]:
        """Extract the client context captured when the payment was started."""
        context = tx.request_payload if isinstance(tx.request_payload, dict) else {}
        raw_ip = (
            context.get('payer_client_ip')
            or context.get('client_ip')
            or context.get('remote_addr')
            or context.get('ip')
            or context.get('x-real-ip')
            or context.get('x-forwarded-for')
        )
        payer_client_ip = str(raw_ip or '').strip()
        # A forwarded header can contain a comma-separated chain.  The first
        # value is the originating client address, but only use it when it is
        # a syntactically valid IPv4/IPv6 address.
        if ',' in payer_client_ip:
            payer_client_ip = payer_client_ip.split(',', 1)[0].strip()
        try:
            ipaddress.ip_address(payer_client_ip)
        except ValueError:
            payer_client_ip = WECHAT_DEFAULT_PAYER_CLIENT_IP

        user_agent = context.get('user_agent') or context.get('user-agent')
        normalized_user_agent = str(user_agent).strip() if user_agent else WECHAT_DEFAULT_USER_AGENT
        normalized_user_agent = normalized_user_agent[:512]
        return payer_client_ip, normalized_user_agent

    @staticmethod
    def _wechat_h5_type(config: WechatPayConfig) -> str:
        value = str(getattr(config, 'h5_type', '') or '').strip().upper()
        legacy_value = str(getattr(config, 'h5_info_type', '') or '').strip().upper()
        if not value:
            value = legacy_value
        value = value or WECHAT_DEFAULT_H5_TYPE
        canonical = WECHAT_H5_TYPE_ALIASES.get(value)
        if canonical is None:
            raise ConflictError('WeChat H5 type must be Wap, iOS, or Android')
        return canonical

    @staticmethod
    def _wechat_h5_return_base(config: WechatPayConfig) -> str:
        # ``h5_redirect_url`` was used by an early integration draft.  Keep it
        # as a fallback so deployments can roll forward without changing code.
        return str(
            getattr(config, 'h5_return_url', '')
            or getattr(config, 'h5_redirect_url', '')
            or ''
        ).strip()

    @staticmethod
    def _wechat_http_url(value: str, field_name: str) -> str:
        """Return an absolute HTTP(S) URL suitable for a provider redirect."""
        candidate = str(value or '').strip()
        # Backslashes and raw control/whitespace characters are normalized
        # differently by browsers and URL parsers, so accepting them here can
        # change the destination after validation.
        if '\\' in candidate or any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F for char in candidate):
            raise ConflictError(f'WeChat {field_name} must be an absolute HTTP(S) URL')
        try:
            parts = urlsplit(candidate)
            hostname = parts.hostname
            # Accessing ``port`` validates that it is numeric and in range.
            _parsed_port = parts.port
        except ValueError as exc:
            # ``urlsplit`` raises for malformed bracketed IPv6 hosts.  Expose
            # the same provider-facing validation error as other bad URLs.
            raise ConflictError(f'WeChat {field_name} must be an absolute HTTP(S) URL') from exc
        if (
            parts.scheme.lower() not in {'http', 'https'}
            or not parts.netloc
            or not hostname
            or parts.username is not None
            or parts.password is not None
        ):
            raise ConflictError(f'WeChat {field_name} must be an absolute HTTP(S) URL')
        return candidate

    @staticmethod
    def _wechat_redirect_url(order: Order, tx: PaymentTransaction, config: WechatPayConfig) -> str | None:
        base_url = PaymentService._wechat_h5_return_base(config)
        if not base_url:
            return None
        try:
            format_parts = list(Formatter().parse(base_url))
        except ValueError as exc:
            raise ConflictError('WeChat H5 return URL contains an unsupported placeholder') from exc
        allowed_fields = {'order_id', 'out_trade_no'}
        for _literal, field_name, format_spec, conversion in format_parts:
            if (
                field_name is not None
                and (
                    field_name not in allowed_fields
                    or format_spec
                    or conversion is not None
                )
            ):
                raise ConflictError('WeChat H5 return URL contains an unsupported placeholder')
        try:
            formatted = base_url.format(order_id=order.id, out_trade_no=tx.out_trade_no)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ConflictError('WeChat H5 return URL contains an unsupported placeholder') from exc
        formatted = PaymentService._wechat_http_url(formatted, 'H5 return URL')
        parts = urlsplit(formatted)
        identifier_query = urlencode({'order_id': str(order.id), 'out_trade_no': tx.out_trade_no})
        if parts.fragment:
            # Uni-app routes are commonly carried in the URL fragment.  Put
            # identifiers after the route so the SPA can read them; placing
            # them before ``#`` would send them only to the web server.
            joiner = '&' if '?' in parts.fragment else '?'
            fragment = f'{parts.fragment}{joiner}{identifier_query}'
            return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, fragment))
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.update({'order_id': str(order.id), 'out_trade_no': tx.out_trade_no})
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    @staticmethod
    def _wechat_h5_payment_url(h5_url: str, redirect_url: str | None) -> str:
        h5_url = PaymentService._wechat_http_url(h5_url, 'h5_url')
        if not redirect_url:
            return h5_url
        redirect_url = PaymentService._wechat_http_url(redirect_url, 'redirect URL')
        parts = urlsplit(h5_url)
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key != 'redirect_url'
        ]
        query.append(('redirect_url', redirect_url))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    @staticmethod
    def _wechat_build_request_payment(order: Order, tx: PaymentTransaction, config: WechatPayConfig) -> dict[str, Any]:
        if not config.app_id:
            raise ConflictError('WeChat app_id is not configured')
        if not config.mchid:
            raise ConflictError('WeChat mchid is not configured')
        if not config.api_v3_key:
            raise ConflictError('WeChat API v3 key is not configured')
        if len(config.api_v3_key.encode('utf-8')) != 32:
            raise ConflictError('WeChat API v3 key must be exactly 32 bytes')
        if not config.merchant_serial_no:
            raise ConflictError('WeChat merchant serial no is not configured')
        if not config.merchant_private_key_path:
            raise ConflictError('WeChat merchant private key path is not configured')
        if not config.notify_url:
            raise ConflictError('WeChat notify url is not configured')

        payer_client_ip, user_agent = PaymentService._wechat_request_context(tx)
        h5_type = PaymentService._wechat_h5_type(config)
        redirect_url = PaymentService._wechat_redirect_url(order, tx, config)
        expire_at = (business_now() + timedelta(minutes=UNPAID_ORDER_EXPIRE_MINUTES)).replace(microsecond=0)
        payload = {
            'appid': config.app_id,
            'mchid': config.mchid,
            'description': PaymentService._subject(order),
            'out_trade_no': tx.out_trade_no,
            'notify_url': config.notify_url,
            'time_expire': expire_at.isoformat(),
            'amount': {
                'total': int(quantize_amount(tx.amount) * 100),
                'currency': tx.currency,
            },
            'scene_info': {
                'payer_client_ip': payer_client_ip,
                'h5_info': {'type': h5_type},
            },
        }
        response = PaymentService._wechat_request_json(
            f'{WECHAT_API_BASE_URL}/v3/pay/transactions/h5',
            payload,
            config,
        )
        h5_url = str(response.get('h5_url') or '').strip()
        if not h5_url:
            raise ConflictError('WeChat payment h5_url is missing')
        return {
            'provider': 'wxpay',
            'mocked': False,
            'status': 'PENDING',
            'order_no': order.order_no,
            'out_trade_no': tx.out_trade_no,
            'amount': float(tx.amount),
            'currency': tx.currency,
            'subject': PaymentService._subject(order),
            # Keep request_payment as an alias for clients that already
            # consume the generic external-payment response shape.
            'request_payment': h5_url,
            'h5_url': h5_url,
            'payment_url': PaymentService._wechat_h5_payment_url(h5_url, redirect_url),
            'redirect_url': redirect_url,
            'payer_client_ip': payer_client_ip,
            'user_agent': user_agent,
            'h5_type': h5_type,
            'provider_payload': response,
            'notify_url': config.notify_url,
        }

    @staticmethod
    def _alipay_sign_string(params: dict[str, Any], *, exclude_sign_type: bool = False) -> str:
        ordered_parts = []
        for key in sorted(params):
            value = params[key]
            if value is None or key == 'sign' or (exclude_sign_type and key == 'sign_type'):
                continue
            ordered_parts.append(f'{key}={value}')
        return '&'.join(ordered_parts)

    @staticmethod
    def _alipay_verify_api_response(raw_body: str, response_key: str, config: AlipayConfig) -> dict[str, Any]:
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ConflictError('Alipay query response is invalid') from exc

        response = payload.get(response_key)
        signature = str(payload.get('sign') or '').strip()
        if not isinstance(response, dict) or not signature:
            raise ConflictError('Alipay query response is incomplete')

        marker = f'"{response_key}"'
        key_start = raw_body.find(marker)
        value_start = raw_body.find(':', key_start + len(marker)) if key_start >= 0 else -1
        if value_start < 0:
            raise ConflictError('Alipay query response payload is missing')
        value_start += 1
        while value_start < len(raw_body) and raw_body[value_start].isspace():
            value_start += 1
        try:
            _, value_end = json.JSONDecoder().raw_decode(raw_body, value_start)
        except json.JSONDecodeError as exc:
            raise ConflictError('Alipay query response payload is invalid') from exc

        if not config.alipay_public_cert_path:
            raise ConflictError('Alipay public certificate path is not configured')
        certificate_sn = str(payload.get('alipay_cert_sn') or '').strip()
        public_key = PaymentService._load_certificate_public_key(
            config.alipay_public_cert_path,
            certificate_sn,
        )
        try:
            public_key.verify(
                base64.b64decode(signature, validate=True),
                raw_body[value_start:value_end].encode(config.charset),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except InvalidSignature as exc:
            if alipay_sandbox_query_bypass_enabled(config):
                response = dict(response)
                response['_signature_verification'] = 'sandbox_https_bypass'
                return response
            raise ForbiddenError('Alipay query response signature is invalid') from exc
        except (binascii.Error, ValueError) as exc:
            raise ForbiddenError('Alipay query response signature is invalid') from exc
        return response

    @staticmethod
    def _alipay_query_trade(out_trade_no: str, config: AlipayConfig) -> dict[str, Any]:
        biz_content = {'out_trade_no': out_trade_no}
        params = {
            'app_id': config.app_id,
            'method': 'alipay.trade.query',
            'format': 'JSON',
            'charset': config.charset,
            'sign_type': config.sign_type,
            'timestamp': business_now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'biz_content': json.dumps(biz_content, ensure_ascii=False, separators=(',', ':')),
        }
        app_certificates = load_alipay_certificates(config.app_cert_path)
        root_certificates = load_alipay_certificates(config.root_cert_path)
        params['app_cert_sn'] = alipay_certificate_sn(app_certificates[0])
        params['alipay_root_cert_sn'] = alipay_root_certificate_sn(root_certificates)
        private_key = PaymentService._load_private_key(config.private_key_path)
        params['sign'] = PaymentService._rsa_sign(private_key, PaymentService._alipay_sign_string(params))

        request_body = urlencode(params).encode(config.charset)
        gateway_separator = '&' if '?' in config.gateway_url else '?'
        gateway_url = f'{config.gateway_url}{gateway_separator}{urlencode({"charset": config.charset})}'
        request = urlrequest.Request(
            gateway_url,
            data=request_body,
            headers={'Content-Type': f'application/x-www-form-urlencoded;charset={config.charset}'},
            method='POST',
        )
        try:
            with urlrequest.urlopen(request, timeout=payment_config.request_timeout_seconds) as response:
                raw_body = response.read().decode(config.charset)
        except urlerror.HTTPError as exc:
            response_body = exc.read().decode(config.charset, errors='ignore')
            raise ConflictError(f'Alipay query request failed: {response_body or exc.reason}') from exc
        except urlerror.URLError as exc:
            raise ConflictError(f'Alipay query request failed: {exc.reason}') from exc
        return PaymentService._alipay_verify_api_response(
            raw_body,
            'alipay_trade_query_response',
            config,
        )

    @staticmethod
    def _alipay_return_url(order: Order, config: AlipayConfig) -> str:
        if not config.return_url:
            return ''
        base_url, separator, fragment = config.return_url.partition('#')
        query = urlencode({'order_id': order.id})
        if separator:
            joiner = '&' if '?' in fragment else '?'
            return f'{base_url}#{fragment}{joiner}{query}'
        joiner = '&' if '?' in base_url else '?'
        return f'{base_url}{joiner}{query}'

    @staticmethod
    def _alipay_build_request_payment(order: Order, tx: PaymentTransaction, config: AlipayConfig) -> dict[str, Any]:
        if not config.app_id:
            raise ConflictError('Alipay app_id is not configured')
        if not config.private_key_path:
            raise ConflictError('Alipay private key path is not configured')
        if not config.notify_url:
            raise ConflictError('Alipay notify url is not configured')
        if not config.app_cert_path or not config.alipay_public_cert_path or not config.root_cert_path:
            raise ConflictError('Alipay certificate paths are not configured')

        is_h5 = config.payment_method == 'alipay.trade.wap.pay'
        return_url = PaymentService._alipay_return_url(order, config)
        biz_content = {
            'subject': PaymentService._subject(order),
            'out_trade_no': tx.out_trade_no,
            'total_amount': f'{quantize_amount(tx.amount):.2f}',
            'product_code': 'QUICK_WAP_WAP' if is_h5 else 'QUICK_MSECURITY_PAY',
            'timeout_express': f'{UNPAID_ORDER_EXPIRE_MINUTES}m',
        }
        params = {
            'app_id': config.app_id,
            'method': config.payment_method,
            'format': 'JSON',
            'charset': config.charset,
            'sign_type': config.sign_type,
            'timestamp': business_now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'notify_url': config.notify_url,
            'biz_content': json.dumps(biz_content, ensure_ascii=False, separators=(',', ':')),
        }
        app_certificates = load_alipay_certificates(config.app_cert_path)
        root_certificates = load_alipay_certificates(config.root_cert_path)
        params['app_cert_sn'] = alipay_certificate_sn(app_certificates[0])
        params['alipay_root_cert_sn'] = alipay_root_certificate_sn(root_certificates)
        if return_url:
            params['return_url'] = return_url
        unsigned = PaymentService._alipay_sign_string(params)
        private_key = PaymentService._load_private_key(config.private_key_path)
        sign = PaymentService._rsa_sign(private_key, unsigned)
        form_params = {key: str(value) for key, value in params.items() if value is not None}
        form_params['sign'] = sign
        form_action_separator = '&' if '?' in config.gateway_url else '?'
        form_action = f'{config.gateway_url}{form_action_separator}{urlencode({"charset": config.charset})}'
        form_body_params = {key: value for key, value in form_params.items() if key != 'charset'}
        request_payment = '&'.join(
            f'{key}={quote_plus(value, safe="")}' for key, value in form_params.items()
        )
        return {
            'provider': 'alipay',
            'mocked': False,
            'status': 'PENDING',
            'order_no': order.order_no,
            'out_trade_no': tx.out_trade_no,
            'amount': float(tx.amount),
            'currency': tx.currency,
            'subject': PaymentService._subject(order),
            'request_payment': request_payment,
            'payment_method': config.payment_method,
            'payment_url': f'{config.gateway_url}?{request_payment}' if is_h5 else None,
            'payment_form': {
                'action': form_action,
                'method': 'POST',
                'params': form_body_params,
            } if is_h5 else None,
            'provider_payload': {
                'biz_content': biz_content,
                'order_string': request_payment,
                'gateway_url': config.gateway_url,
                'payment_method': config.payment_method,
            },
            'notify_url': config.notify_url,
            'return_url': return_url or None,
        }

    @staticmethod
    def _mock_payment_payload(order: Order, channel: PaymentChannel, tx: PaymentTransaction) -> dict[str, Any]:
        provider = PaymentService._provider_name(channel)
        request_payment: dict[str, Any] | str
        h5_url: str | None = None
        redirect_url: str | None = None
        if channel == PaymentChannel.WECHAT:
            config = cast(WechatPayConfig, PaymentService._provider_config(channel))
            request_payment = {
                'appid': 'mock-appid',
                'partnerid': 'mock-mchid',
                'prepayid': f'mock-prepay-{tx.out_trade_no}',
                'package': 'Sign=WXPay',
                'noncestr': uuid4().hex,
                'timestamp': str(unix_timestamp()),
                'sign': 'MOCK-WECHAT-SIGN',
            }
            h5_url = f'https://mock.weixin.qq.com/h5/pay?trade_no={quote(tx.out_trade_no, safe="")}'
            redirect_url = PaymentService._wechat_redirect_url(order, tx, config)
        else:
            request_payment = f'mock-order-string-{tx.out_trade_no}'

        payment: dict[str, Any] = {
            'provider': provider,
            'mocked': True,
            'status': 'PENDING',
            'order_no': order.order_no,
            'out_trade_no': tx.out_trade_no,
            'amount': float(tx.amount),
            'currency': tx.currency,
            'subject': PaymentService._subject(order),
            'request_payment': request_payment,
            'notify_url': PaymentService._provider_config(channel).notify_url,
        }
        if channel == PaymentChannel.WECHAT:
            payment.update(
                {
                    'h5_url': h5_url,
                    'payment_url': PaymentService._wechat_h5_payment_url(h5_url or '', redirect_url),
                    'redirect_url': redirect_url,
                    'h5_type': PaymentService._wechat_h5_type(
                        cast(WechatPayConfig, PaymentService._provider_config(channel))
                    ),
                }
            )
        return payment

    @staticmethod
    def prepare_external_payment(
        db: Session,
        order: Order,
        channel: str,
        request_payload: dict | None = None,
    ) -> dict[str, Any]:
        if order.pay_status == PayStatus.PAID:
            raise ConflictError('Order already paid')

        pay_channel = PaymentChannel(channel)
        provider_config = PaymentService._provider_config(pay_channel)
        if not payment_config.mock_external_payment and not provider_config.enabled:
            raise ConflictError(f'{PaymentService._provider_name(pay_channel)} payment is not enabled')

        # Reconciliation and callbacks lock the transaction before the order.
        # Lock an existing pending transaction first so a payment preparation
        # cannot hold the order while waiting for the same transaction row.
        tx = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.order_id == order.id,
                PaymentTransaction.channel == pay_channel,
                PaymentTransaction.status == PaymentStatus.PENDING,
            )
            .order_by(PaymentTransaction.id.desc())
            .first()
        )
        if tx:
            # A caller may already have the row in this Session's identity
            # map; refresh is required for a current read and row lock.
            db.refresh(tx, with_for_update=True)

        # Serialize transaction lookup/creation for one order.  The order-row
        # lock still prevents two requests with no existing transaction from
        # creating duplicate pending provider orders.
        locked_order = (
            db.query(Order)
            .filter(Order.id == order.id)
            .with_for_update()
            .first()
        )
        if not locked_order:
            raise NotFoundError('Order not found')
        # A caller may have loaded this order earlier in the same Session;
        # refresh under the lock so a concurrent payment cannot be hidden by
        # the identity map.
        db.refresh(locked_order, with_for_update=True)
        order = locked_order
        if order.pay_status == PayStatus.PAID:
            raise ConflictError('Order already paid')
        if order.order_status == OrderStatus.REFUND:
            raise ConflictError('Refunded order cannot be paid')
        if order.pay_status != PayStatus.UNPAID or order.order_status != OrderStatus.PENDING_PAYMENT:
            raise ConflictError('Only unpaid pending orders can be paid')

        # The transaction may have changed while the order was acquired (for
        # example, a callback could have completed it).  Re-query when the
        # pre-locked row is no longer reusable; the order lock serializes the
        # no-row/create case with other payment preparations.
        if not tx or tx.status != PaymentStatus.PENDING:
            tx = PaymentService._ensure_transaction(db, order, pay_channel, request_payload)
        else:
            tx.request_payload = request_payload or tx.request_payload

        if payment_config.mock_external_payment:
            payment = PaymentService._mock_payment_payload(order, pay_channel, tx)
        else:
            if pay_channel == PaymentChannel.WECHAT:
                wechat_config = cast(WechatPayConfig, provider_config)
                payment = PaymentService._wechat_build_request_payment(order, tx, wechat_config)
            else:
                alipay_config = cast(AlipayConfig, provider_config)
                payment = PaymentService._alipay_build_request_payment(order, tx, alipay_config)

        tx.status = PaymentStatus.PENDING
        tx.provider_app_id = getattr(provider_config, 'app_id', '') or None
        tx.provider_payload = payment.get('provider_payload')
        db.commit()
        db.refresh(tx)
        return {'transaction': tx, 'payment': payment}

    @staticmethod
    def confirm_paid_order(
        db: Session,
        tx: PaymentTransaction,
        notify_payload: dict | None = None,
        provider_trade_no: str | None = None,
    ) -> Order:
        # All external payment transitions lock transaction then order. The
        # notify/query paths already hold this row, while mock auto-complete
        # reaches this method without a prior transaction lock.
        if not getattr(tx, 'id', None):
            raise NotFoundError('Payment transaction not found')
        locked_tx = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.id == tx.id)
            .with_for_update()
            .first()
        )
        if not locked_tx:
            raise NotFoundError('Payment transaction not found')
        db.refresh(locked_tx, with_for_update=True)
        tx = locked_tx

        # Serialize settlement across payment callbacks for the same order.
        # Without an order lock, a WeChat callback and a provider query can
        # both observe UNPAID and run inventory/commission settlement twice.
        order = db.query(Order).filter(Order.id == tx.order_id).with_for_update().first()
        if not order:
            raise NotFoundError('Order not found')
        # ``order`` may already be present in this Session (for example, a
        # status-poll request loaded it before acquiring the lock).  A plain
        # SELECT ... FOR UPDATE does not refresh an unexpired identity-map
        # object, so explicitly reload it before checking pay/order status.
        db.refresh(order, with_for_update=True)
        if tx.status == PaymentStatus.PAID and order.pay_status == PayStatus.PAID:
            if provider_trade_no and getattr(tx, 'provider_trade_no', None) and tx.provider_trade_no != provider_trade_no:
                raise ConflictError('Payment transaction id conflicts with the recorded transaction')
            return order
        if order.pay_status == PayStatus.PAID:
            raise ConflictError('Order is already paid by another payment transaction')

        if provider_trade_no and getattr(tx, 'provider_trade_no', None) and tx.provider_trade_no != provider_trade_no:
            raise ConflictError('Payment transaction id conflicts with the recorded transaction')
        tx.status = PaymentStatus.PAID
        if provider_trade_no:
            tx.provider_trade_no = provider_trade_no
        tx.notify_payload = notify_payload or tx.notify_payload
        tx.paid_at = now()

        from app.services.order_service import OrderService

        paid_order = OrderService._mark_paid(db, order, external_paid_amount=quantize_amount(tx.amount))
        paid_order.legacy_trade_no = provider_trade_no or paid_order.legacy_trade_no
        db.commit()
        db.refresh(paid_order)
        return paid_order

    @staticmethod
    def _record_provider_success_for_closed_order(
        db: Session,
        tx: PaymentTransaction,
        notify_payload: dict[str, Any] | None,
        provider_trade_no: str,
    ) -> str | None:
        """Record a verified provider payment that cannot settle this order.

        A provider callback can arrive after a user or administrator canceled
        an order, or after another payment already settled it.  Such a payment
        must be acknowledged and retained for refund/manual review instead of
        being retried indefinitely or accidentally settling the order again.
        The order row is locked here so the decision is made against the
        current state, not the stale object held by a status-poll request.
        """
        order_state = (
            db.query(Order)
            .filter(Order.id == tx.order_id)
            .with_for_update()
            .first()
        )
        if not order_state:
            return None
        # The caller may have loaded the same order earlier in this Session;
        # refresh under the row lock so a concurrent settlement/cancellation
        # cannot be hidden by SQLAlchemy's identity map.
        db.refresh(order_state, with_for_update=True)

        raw_pay_status = getattr(order_state, 'pay_status', None)
        raw_order_status = getattr(order_state, 'order_status', None)
        pay_status = getattr(raw_pay_status, 'value', raw_pay_status)
        order_status = getattr(raw_order_status, 'value', raw_order_status)
        if pay_status == PayStatus.PAID.value:
            provider_status = 'ORDER_PAID_OTHER_TRANSACTION'
            state_description = 'already paid'
        elif pay_status == PayStatus.REFUNDED.value or order_status == OrderStatus.REFUND.value:
            provider_status = 'ORDER_CANCELED_PROVIDER_PAYMENT'
            state_description = 'canceled or refunded'
        else:
            return None

        existing_trade_no = str(getattr(tx, 'provider_trade_no', '') or '').strip()
        incoming_trade_no = str(provider_trade_no or '').strip()
        if existing_trade_no and incoming_trade_no and existing_trade_no != incoming_trade_no:
            raise ConflictError('Payment transaction id conflicts with the recorded transaction')
        tx.status = PaymentStatus.FAILED
        tx.provider_trade_no = incoming_trade_no or existing_trade_no or None
        tx.notify_payload = notify_payload or tx.notify_payload
        tx.failed_reason = (
            f'Provider payment succeeded after order was {state_description}; '
            'provider refund required'
        )
        db.commit()
        if tx.channel == PaymentChannel.WECHAT:
            PaymentService._auto_refund_late_wechat_payment(db, order_state, tx)
        return provider_status

    @staticmethod
    def _refresh_locked_payment_order(db: Session, order: Order) -> Order:
        """Reload the order under a row lock before returning a payment result.

        Reconciliation locks the transaction first, matching the callback
        path.  A status-poll request may still hold an older ``Order`` object
        in the same SQLAlchemy identity map, so a plain query would not be
        enough to expose a concurrent settlement.
        """
        db.refresh(order, with_for_update=True)
        return order

    @staticmethod
    def _wechat_query_order(out_trade_no: str, config: WechatPayConfig) -> dict[str, Any]:
        normalized = str(out_trade_no or '').strip()
        if not normalized:
            raise NotFoundError('Payment transaction not found')
        encoded_trade_no = quote(normalized, safe='')
        url = (
            f'{WECHAT_API_BASE_URL}/v3/pay/transactions/out-trade-no/'
            f'{encoded_trade_no}?mchid={quote(str(config.mchid), safe="")}'
        )
        return PaymentService._wechat_request_json(url, None, config, method='GET')

    @staticmethod
    def _refund_status_value(refund: PaymentRefund | Any) -> str:
        raw = getattr(refund, 'status', refund)
        return str(getattr(raw, 'value', raw) or '').strip().upper()

    @staticmethod
    def _lock_wechat_refund_transaction(
        db: Session,
        transaction_id: int,
    ) -> tuple[Order, PaymentTransaction]:
        """Lock a refund's transaction and order in the payment lock order.

        Payment settlement already serializes work as payment transaction then
        order.  Refund request, query, and finalization paths use the same
        order so a payment callback cannot race a local refund transition.
        """
        tx = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.id == transaction_id)
            .with_for_update()
            .first()
        )
        if not tx:
            raise NotFoundError('Payment transaction not found')
        db.refresh(tx, with_for_update=True)
        if tx.channel != PaymentChannel.WECHAT:
            raise ConflictError('Payment transaction is not a WeChat transaction')

        order = (
            db.query(Order)
            .filter(Order.id == tx.order_id)
            .with_for_update()
            .first()
        )
        if not order:
            raise NotFoundError('Order not found')
        db.refresh(order, with_for_update=True)
        return order, tx

    @staticmethod
    def _lock_wechat_refund_context(
        db: Session,
        refund_id: int,
    ) -> tuple[Order, PaymentTransaction, PaymentRefund]:
        """Lock transaction, order, then refund for a known refund row.

        The first scalar lookup intentionally does not lock the refund row;
        it only resolves the transaction id needed to acquire the canonical
        transaction -> order -> refund lock sequence.
        """
        identity = (
            db.query(PaymentRefund.payment_transaction_id, PaymentRefund.order_id)
            .filter(PaymentRefund.id == refund_id)
            .first()
        )
        if not identity:
            raise NotFoundError('Payment refund not found')
        transaction_id, refund_order_id = identity
        order, tx = PaymentService._lock_wechat_refund_transaction(db, transaction_id)
        refund = (
            db.query(PaymentRefund)
            .filter(PaymentRefund.id == refund_id)
            .with_for_update()
            .first()
        )
        if not refund:
            raise NotFoundError('Payment refund not found')
        db.refresh(refund, with_for_update=True)
        if refund.payment_transaction_id != tx.id or refund.order_id != order.id or refund_order_id != order.id:
            raise ConflictError('Payment refund does not match its payment transaction')
        if refund.channel != PaymentChannel.WECHAT:
            raise ConflictError('Payment refund is not a WeChat refund')
        return order, tx, refund

    @staticmethod
    def _wechat_refund_reason(reason: str | None) -> str:
        """Normalize a reason to WeChat's 80-byte, single-line limit."""
        value = str(reason or WECHAT_REFUND_DEFAULT_REASON).strip()
        if not value:
            value = WECHAT_REFUND_DEFAULT_REASON
        if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
            raise ConflictError('WeChat refund reason contains unsupported control characters')
        while len(value.encode('utf-8')) > WECHAT_REFUND_MAX_REASON_BYTES:
            value = value[:-1]
        return value or WECHAT_REFUND_DEFAULT_REASON

    @staticmethod
    def _wechat_refund_no(order: Order, tx: PaymentTransaction) -> str:
        """Build a deterministic provider idempotency number (<=64 bytes)."""
        seed = f'{getattr(order, "id", 0)}:{getattr(tx, "id", 0)}:{tx.out_trade_no}'
        digest = sha256(seed.encode('utf-8')).hexdigest()[:24].upper()
        order_id = str(getattr(order, 'id', 0) or 0)
        return f'RF{order_id}{digest}'[:64]

    @staticmethod
    def _wechat_refund_payload(
        order: Order,
        tx: PaymentTransaction,
        refund: PaymentRefund,
        config: WechatPayConfig,
    ) -> dict[str, Any]:
        total_cents = int(quantize_amount(tx.amount) * 100)
        refund_cents = int(quantize_amount(refund.refund_amount) * 100)
        payload: dict[str, Any] = {
            'out_refund_no': refund.out_refund_no,
            'amount': {
                'refund': refund_cents,
                'total': total_cents,
                'currency': str(tx.currency).strip().upper(),
            },
        }
        if tx.provider_trade_no:
            payload['transaction_id'] = str(tx.provider_trade_no).strip()
        else:
            payload['out_trade_no'] = str(tx.out_trade_no).strip()
        if refund.reason:
            payload['reason'] = refund.reason
        if config.refund_notify_url:
            payload['notify_url'] = config.refund_notify_url
        return payload

    @staticmethod
    def _wechat_refund_query(refund: PaymentRefund, config: WechatPayConfig) -> dict[str, Any]:
        encoded_refund_no = quote(str(refund.out_refund_no), safe='')
        return PaymentService._wechat_request_json(
            f'{WECHAT_API_BASE_URL}/v3/refund/domestic/refunds/{encoded_refund_no}',
            None,
            config,
            method='GET',
        )

    @staticmethod
    def _validate_wechat_refund_response(
        response: dict[str, Any],
        refund: PaymentRefund,
        tx: PaymentTransaction,
        *,
        source: str,
    ) -> tuple[str, str | None]:
        if not isinstance(response, dict):
            raise ConflictError(f'WeChat {source} refund response is invalid')
        response_out_refund_no = str(response.get('out_refund_no') or '').strip()
        if response_out_refund_no != str(refund.out_refund_no).strip():
            raise ConflictError(f'WeChat {source} refund out_refund_no mismatch')

        response_out_trade_no = str(response.get('out_trade_no') or '').strip()
        if not response_out_trade_no or response_out_trade_no != str(tx.out_trade_no).strip():
            raise ConflictError(f'WeChat {source} refund out_trade_no mismatch')
        response_transaction_id = str(response.get('transaction_id') or '').strip()
        recorded_transaction_id = str(getattr(tx, 'provider_trade_no', '') or '').strip()
        strict_provider_identifiers = not payment_config.mock_external_payment and source != 'mock'
        if strict_provider_identifiers and not response_transaction_id:
            raise ConflictError(f'WeChat {source} refund transaction_id is missing')
        if strict_provider_identifiers and not recorded_transaction_id:
            raise ConflictError(f'WeChat {source} payment transaction_id is missing')
        if recorded_transaction_id and response_transaction_id != recorded_transaction_id:
            raise ConflictError(f'WeChat {source} refund transaction_id mismatch')

        amount = response.get('amount')
        if not isinstance(amount, dict):
            raise ConflictError(f'WeChat {source} refund amount is missing')
        total_cents = PaymentService._wechat_amount_cents(
            amount.get('total'),
            field_name=f'{source} refund amount.total',
        )
        refund_cents = PaymentService._wechat_amount_cents(
            amount.get('refund'),
            field_name=f'{source} refund amount.refund',
        )
        expected_total_cents = int(quantize_amount(tx.amount) * 100)
        expected_refund_cents = int(quantize_amount(refund.refund_amount) * 100)
        if total_cents != expected_total_cents:
            raise ConflictError(f'WeChat {source} refund total amount mismatch')
        if refund_cents != expected_refund_cents:
            raise ConflictError(f'WeChat {source} refund amount mismatch')
        response_currency = str(amount.get('currency') or '').strip().upper()
        if response_currency != str(tx.currency).strip().upper():
            raise ConflictError(f'WeChat {source} refund currency mismatch')

        provider_refund_id = str(response.get('refund_id') or '').strip() or None
        raw_status = response.get('status') or response.get('refund_status')
        status = str(raw_status or '').strip().upper()
        if status not in {'SUCCESS', 'PROCESSING', 'CLOSED', 'ABNORMAL'}:
            raise ConflictError(f'WeChat {source} refund returned unknown status: {status or "missing status"}')
        if (strict_provider_identifiers or status == 'SUCCESS') and not provider_refund_id:
            raise ConflictError(f'WeChat {source} refund_id is missing')
        return status, provider_refund_id

    @staticmethod
    def _apply_wechat_refund_response(
        db: Session,
        refund: PaymentRefund,
        tx: PaymentTransaction,
        response: dict[str, Any],
        *,
        source: str,
        notify_payload: dict[str, Any] | None = None,
        provider_notify_id: str | None = None,
    ) -> PaymentRefund:
        # The provider request runs without database locks. Reacquire the
        # canonical context before applying its response so a callback or
        # status poll cannot overwrite a newer SUCCESS state.
        _order, tx, refund = PaymentService._lock_wechat_refund_context(db, refund.id)
        status, provider_refund_id = PaymentService._validate_wechat_refund_response(
            response,
            refund,
            tx,
            source=source,
        )
        current_status = PaymentService._refund_status_value(refund)
        if current_status == RefundStatus.SUCCESS.value:
            # Provider state is monotonic for this full-refund workflow. A
            # delayed PROCESSING/CLOSED response must never undo an already
            # verified success or cause the local order to be reopened.
            if (
                provider_refund_id
                and refund.provider_refund_id
                and provider_refund_id != refund.provider_refund_id
            ):
                raise ConflictError('WeChat refund_id conflicts with the recorded refund')
            if provider_notify_id:
                refund.provider_notify_id = provider_notify_id
            if source == 'notify' or notify_payload is not None:
                refund.notify_payload = notify_payload or response
            db.commit()
            db.refresh(refund)
            return refund

        refund.status = RefundStatus(status)
        refund.provider_status = status
        refund.provider_refund_id = provider_refund_id or refund.provider_refund_id
        if response.get('transaction_id'):
            refund.provider_trade_no = str(response['transaction_id']).strip()
        if source == 'notify' or notify_payload is not None:
            refund.notify_payload = notify_payload or response
        else:
            refund.response_payload = response
        if provider_notify_id:
            refund.provider_notify_id = provider_notify_id
        refund.last_synced_at = now()
        if status == 'SUCCESS':
            refund.success_at = refund.success_at or now()
            refund.processed_at = refund.processed_at or now()
            refund.error_code = None
            refund.error_message = None
            tx.refunded_amount = quantize_amount(refund.refund_amount)
            refund.next_retry_at = None
        elif status == 'PROCESSING':
            refund.next_retry_at = now() + timedelta(minutes=WECHAT_REFUND_RETRY_MINUTES)
        else:
            refund.processed_at = refund.processed_at or now()
            refund.next_retry_at = None
        db.commit()
        db.refresh(refund)
        return refund

    @staticmethod
    def _wechat_refund_error(
        db: Session,
        refund: PaymentRefund,
        error: Exception,
        *,
        retryable: bool,
        response_payload: dict[str, Any] | None = None,
    ) -> PaymentRefund:
        """Persist a retryable or terminal provider failure without losing the
        original ``out_refund_no``.
        """
        _order, _tx, refund = PaymentService._lock_wechat_refund_context(db, refund.id)
        if PaymentService._refund_status_value(refund) == RefundStatus.SUCCESS.value:
            # A status poll can fail after a webhook already completed the
            # refund. Preserve the verified success rather than regressing it
            # to PROCESSING/FAILED.
            db.commit()
            db.refresh(refund)
            return refund
        refund.status = RefundStatus.PROCESSING if retryable else RefundStatus.FAILED
        refund.provider_status = 'PROCESSING' if retryable else 'FAILED'
        refund.error_code = str(getattr(error, 'http_status', '') or '') or None
        message = str(error).strip() or error.__class__.__name__
        refund.error_message = message[:255]
        if response_payload:
            refund.response_payload = response_payload
        refund.last_synced_at = now()
        refund.next_retry_at = now() + timedelta(minutes=WECHAT_REFUND_RETRY_MINUTES) if retryable else None
        refund.processed_at = None if retryable else (refund.processed_at or now())
        db.commit()
        db.refresh(refund)
        return refund

    @staticmethod
    def _wechat_refund_record(
        db: Session,
        order: Order,
        tx: PaymentTransaction,
        *,
        reason: str | None,
        idempotency_key: str | None,
        requested_by: int | None,
    ) -> PaymentRefund:
        query = (
            db.query(PaymentRefund)
            .filter(PaymentRefund.payment_transaction_id == tx.id)
            .with_for_update()
        )
        record = query.first()
        normalized_key = str(idempotency_key or '').strip() or None
        if normalized_key and len(normalized_key.encode('utf-8')) > 128:
            raise ConflictError('Idempotency-Key must be at most 128 bytes')
        if record:
            if quantize_amount(record.refund_amount) != quantize_amount(tx.amount):
                raise ConflictError('Refund idempotency key parameters mismatch')
            if reason and record.reason and reason != record.reason:
                raise ConflictError('Refund reason conflicts with the existing refund')
            if normalized_key and record.idempotency_key and normalized_key != record.idempotency_key:
                raise ConflictError('A refund is already in progress for this payment')
            if normalized_key and not record.idempotency_key:
                record.idempotency_key = normalized_key

            status = PaymentService._refund_status_value(record)
            if status in {RefundStatus.SUCCESS.value, RefundStatus.PROCESSING.value, RefundStatus.PENDING.value}:
                # Commit only when a missing idempotency key was attached; it
                # also releases the row lock before returning an in-progress
                # provider operation to the caller.
                db.commit()
                db.refresh(record)
                return record

            # Reuse the same merchant refund number after a terminal provider
            # failure. WeChat treats the number as the idempotency key.
            record.status = RefundStatus.PENDING
            record.provider_status = None
            record.error_code = None
            record.error_message = None
            record.next_retry_at = None
            record.processed_at = None
            if reason:
                record.reason = reason
            if requested_by is not None:
                record.requested_by = requested_by
            record.requested_at = now()
            db.commit()
            db.refresh(record)
            return record

        record = PaymentRefund(
            order_id=order.id,
            payment_transaction_id=tx.id,
            order_no=order.order_no,
            channel=PaymentChannel.WECHAT,
            status=RefundStatus.PENDING,
            currency=tx.currency,
            original_amount=quantize_amount(tx.amount),
            refund_amount=quantize_amount(tx.amount),
            out_refund_no=PaymentService._wechat_refund_no(order, tx),
            idempotency_key=normalized_key,
            reason=reason,
            requested_by=requested_by,
            requested_at=now(),
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError as exc:
            # A second request can pass the initial empty lookup before the
            # first one commits. The unique payment_transaction_id key turns
            # that race into an ordinary idempotent read.
            db.rollback()
            record = (
                db.query(PaymentRefund)
                .filter(PaymentRefund.payment_transaction_id == tx.id)
                .with_for_update()
                .first()
            )
            if not record:
                raise
            if reason and record.reason and reason != record.reason:
                raise ConflictError('Refund reason conflicts with the existing refund') from exc
            if normalized_key and record.idempotency_key and normalized_key != record.idempotency_key:
                raise ConflictError('A refund is already in progress for this payment') from exc
            db.commit()
            db.refresh(record)
            return record
        db.refresh(record)
        return record

    @staticmethod
    def request_wechat_refund(
        db: Session,
        order: Order,
        tx: PaymentTransaction,
        *,
        reason: str | None = None,
        idempotency_key: str | None = None,
        requested_by: int | None = None,
    ) -> PaymentRefund:
        """Submit (or safely retry) a full WeChat refund for one paid tx.

        The local refund row is committed before the network call.  A timeout
        therefore leaves a durable ``PROCESSING`` record that can be queried
        with the same merchant refund number instead of creating a second
        refund request.
        """
        requested_order_id = getattr(order, 'id', None)
        if not getattr(tx, 'id', None):
            raise NotFoundError('Payment transaction not found')
        order, tx = PaymentService._lock_wechat_refund_transaction(db, tx.id)
        if order.id != requested_order_id:
            raise ConflictError('Payment transaction does not match order')
        late_success_needing_refund = (
            tx.status == PaymentStatus.FAILED
            and bool(str(tx.provider_trade_no or '').strip())
            and 'provider refund required' in str(tx.failed_reason or '').lower()
        )
        if tx.status != PaymentStatus.PAID and not late_success_needing_refund:
            raise ConflictError('Only a completed WeChat payment can be refunded')
        if late_success_needing_refund:
            if order.order_status != OrderStatus.REFUND and order.pay_status != PayStatus.PAID:
                raise ConflictError('Late WeChat payment is not attached to a refundable order')
        else:
            # Revalidate only after the canonical transaction -> order lock is
            # held. A shipping/confirmation request uses the same order lock
            # and will subsequently see the active refund row.
            from app.services.order_service import OrderService

            OrderService._validate_paid_refund_transition(db, order)
        if quantize_amount(tx.amount) <= 0:
            raise ConflictError('WeChat refund amount must be greater than zero')

        config = cast(WechatPayConfig, PaymentService._provider_config(PaymentChannel.WECHAT))
        if not payment_config.mock_external_payment and not config.enabled:
            raise ConflictError('WeChat payment is not enabled')
        normalized_reason = PaymentService._wechat_refund_reason(reason)
        normalized_key = str(idempotency_key or '').strip() or None
        refund = PaymentService._wechat_refund_record(
            db,
            order,
            tx,
            reason=normalized_reason,
            idempotency_key=normalized_key,
            requested_by=requested_by,
        )
        status = PaymentService._refund_status_value(refund)
        if status == RefundStatus.SUCCESS.value:
            return refund
        if status == RefundStatus.PROCESSING.value:
            return refund

        payload = PaymentService._wechat_refund_payload(order, tx, refund, config)
        refund.request_payload = payload
        refund.attempt_count = int(refund.attempt_count or 0) + 1
        refund.status = RefundStatus.PENDING
        db.commit()
        db.refresh(refund)

        if payment_config.mock_external_payment:
            response = {
                'refund_id': f'MOCK-REFUND-{refund.out_refund_no}',
                'out_refund_no': refund.out_refund_no,
                'out_trade_no': tx.out_trade_no,
                'transaction_id': tx.provider_trade_no or None,
                'status': 'SUCCESS',
                'amount': {
                    'total': int(quantize_amount(tx.amount) * 100),
                    'refund': int(quantize_amount(refund.refund_amount) * 100),
                    'payer_total': int(quantize_amount(tx.amount) * 100),
                    'payer_refund': int(quantize_amount(refund.refund_amount) * 100),
                    'currency': str(tx.currency).strip().upper(),
                },
            }
            return PaymentService._apply_wechat_refund_response(
                db,
                refund,
                tx,
                response,
                source='mock',
            )

        try:
            _status_code, response = PaymentService._wechat_request_json_with_status(
                f'{WECHAT_API_BASE_URL}/v3/refund/domestic/refunds',
                payload,
                config,
                method='POST',
            )
        except WechatApiError as exc:
            return PaymentService._wechat_refund_error(
                db,
                refund,
                exc,
                retryable=exc.retryable,
                response_payload=exc.response_payload,
            )
        try:
            return PaymentService._apply_wechat_refund_response(
                db,
                refund,
                tx,
                response,
                source='request',
            )
        except ConflictError as exc:
            return PaymentService._wechat_refund_error(
                db,
                refund,
                exc,
                retryable=False,
            )

    @staticmethod
    def _auto_refund_late_wechat_payment(
        db: Session,
        order: Order,
        tx: PaymentTransaction,
    ) -> PaymentRefund:
        """Durably refund a verified WeChat charge that cannot settle locally."""
        refund = PaymentService.request_wechat_refund(
            db,
            order,
            tx,
            reason='支付成功晚到，自动原路退款',
        )
        status = PaymentService._refund_status_value(refund)
        if status == RefundStatus.SUCCESS.value:
            from app.services.order_service import OrderService

            OrderService.finalize_external_refund(db, refund, tx)
        elif status not in {RefundStatus.PENDING.value, RefundStatus.PROCESSING.value}:
            # Do not acknowledge the payment notification when the automatic
            # refund was rejected. The durable refund row is reused when the
            # provider retries the same verified notification.
            raise ConflictError(f'Automatic WeChat refund failed: {status}')
        return refund

    @staticmethod
    def sync_wechat_refund(
        db: Session,
        refund: PaymentRefund,
        tx: PaymentTransaction,
    ) -> PaymentRefund:
        """Query a pending refund while retaining its original idempotency key."""
        if not getattr(refund, 'id', None):
            raise NotFoundError('Payment refund not found')
        _order, tx, refund = PaymentService._lock_wechat_refund_context(db, refund.id)
        status = PaymentService._refund_status_value(refund)
        if status in {
            RefundStatus.SUCCESS.value,
            RefundStatus.FAILED.value,
            RefundStatus.CLOSED.value,
            RefundStatus.ABNORMAL.value,
        }:
            db.commit()
            db.refresh(refund)
            return refund
        config = cast(WechatPayConfig, PaymentService._provider_config(PaymentChannel.WECHAT))
        if not payment_config.mock_external_payment and not config.enabled:
            raise ConflictError('WeChat payment is not enabled')
        # The provider query is an outbound request; release the row locks
        # acquired for the state snapshot before making it.
        db.commit()
        if payment_config.mock_external_payment:
            response = {
                'refund_id': f'MOCK-REFUND-{refund.out_refund_no}',
                'out_refund_no': refund.out_refund_no,
                'out_trade_no': tx.out_trade_no,
                'transaction_id': tx.provider_trade_no or None,
                'status': 'SUCCESS',
                'amount': {
                    'total': int(quantize_amount(tx.amount) * 100),
                    'refund': int(quantize_amount(refund.refund_amount) * 100),
                    'currency': str(tx.currency).strip().upper(),
                },
            }
            return PaymentService._apply_wechat_refund_response(
                db,
                refund,
                tx,
                response,
                source='query',
            )
        try:
            response = PaymentService._wechat_refund_query(refund, config)
        except WechatApiError as exc:
            # A just-created refund can be briefly unavailable to the query
            # endpoint. Treat 404 as retryable rather than issuing a new number.
            retryable = exc.retryable or exc.http_status == 404
            return PaymentService._wechat_refund_error(
                db,
                refund,
                exc,
                retryable=retryable,
                response_payload=exc.response_payload,
            )
        try:
            return PaymentService._apply_wechat_refund_response(
                db,
                refund,
                tx,
                response,
                source='query',
            )
        except ConflictError as exc:
            return PaymentService._wechat_refund_error(db, refund, exc, retryable=False)

    @staticmethod
    def reconcile_due_wechat_refunds(
        db: Session,
        *,
        batch_size: int = WECHAT_REFUND_RECONCILE_BATCH_SIZE,
    ) -> int:
        """Reconcile due real-WeChat refunds when a provider callback is lost.

        Each refund operation retains its provider idempotency number, so
        this method is safe to run from more than one application process.
        Pending records are submitted again with that same number; processing
        records are queried. A verified success always passes through the
        normal idempotent order finalizer.
        """
        config = cast(WechatPayConfig, PaymentService._provider_config(PaymentChannel.WECHAT))
        if payment_config.mock_external_payment or not config.enabled:
            return 0
        limit = max(1, min(int(batch_size), WECHAT_REFUND_RECONCILE_BATCH_SIZE))
        due_refund_ids = [
            int(refund_id)
            for (refund_id,) in (
                db.query(PaymentRefund.id)
                .filter(
                    PaymentRefund.channel == PaymentChannel.WECHAT,
                    PaymentRefund.status.in_((RefundStatus.PENDING, RefundStatus.PROCESSING)),
                    or_(
                        PaymentRefund.next_retry_at.is_(None),
                        PaymentRefund.next_retry_at <= now(),
                    ),
                )
                .order_by(PaymentRefund.next_retry_at.asc(), PaymentRefund.id.asc())
                .limit(limit)
                .all()
            )
        ]
        reconciled_count = 0
        for refund_id in due_refund_ids:
            try:
                refund = db.get(PaymentRefund, refund_id)
                if not refund or refund.channel != PaymentChannel.WECHAT:
                    continue
                tx = db.get(PaymentTransaction, refund.payment_transaction_id)
                order = db.get(Order, refund.order_id)
                if not tx or not order or tx.order_id != order.id:
                    continue

                status = PaymentService._refund_status_value(refund)
                if status == RefundStatus.PENDING.value:
                    refund = PaymentService.request_wechat_refund(db, order, tx)
                elif status == RefundStatus.PROCESSING.value:
                    refund = PaymentService.sync_wechat_refund(db, refund, tx)
                else:
                    continue

                if PaymentService._refund_status_value(refund) == RefundStatus.SUCCESS.value:
                    from app.services.order_service import OrderService

                    OrderService.finalize_external_refund(db, refund, tx)
                reconciled_count += 1
            except Exception:
                # A single malformed/provider-failed record must not prevent
                # another due refund from being reconciled on this pass.
                db.rollback()
        return reconciled_count

    @staticmethod
    def _wechat_amount_cents(value: Any, *, field_name: str) -> int:
        # WeChat returns ``amount.total`` as an integer number of fen.  Do not
        # accept floating point or decimal strings here: coercing those values
        # could turn a malformed notification into a valid payment.
        if isinstance(value, bool):
            raise ConflictError(f'WeChat {field_name} is invalid')
        try:
            text = str(value).strip()
            if not text or text.startswith(('+', '-')) or not text.isdigit():
                raise ValueError
            cents = int(text)
        except (TypeError, ValueError) as exc:
            raise ConflictError(f'WeChat {field_name} is invalid') from exc
        if cents < 0:
            raise ConflictError(f'WeChat {field_name} is invalid')
        return cents

    @staticmethod
    def _validate_wechat_trade_response(
        response: dict[str, Any],
        config: WechatPayConfig,
        tx: PaymentTransaction,
        *,
        source: str,
    ) -> str:
        if not isinstance(response, dict):
            raise ConflictError(f'WeChat {source} response is invalid')

        response_trade_no = str(response.get('out_trade_no') or '').strip()
        if response_trade_no != tx.out_trade_no:
            raise ConflictError(f'WeChat {source} out_trade_no mismatch')

        response_app_id = str(response.get('appid') or '').strip()
        if not response_app_id or response_app_id != config.app_id:
            raise ConflictError(f'WeChat {source} appid mismatch')
        if getattr(tx, 'provider_app_id', None) and tx.provider_app_id != response_app_id:
            raise ConflictError(f'WeChat {source} transaction appid mismatch')
        response_mchid = str(response.get('mchid') or '').strip()
        if not response_mchid or response_mchid != config.mchid:
            raise ConflictError(f'WeChat {source} mchid mismatch')

        amount = response.get('amount')
        if not isinstance(amount, dict):
            raise ConflictError(f'WeChat {source} amount is missing')
        response_cents = PaymentService._wechat_amount_cents(
            amount.get('total'),
            field_name=f'{source} amount.total',
        )
        expected_cents = int(quantize_amount(tx.amount) * 100)
        if response_cents != expected_cents:
            raise ConflictError(f'WeChat {source} amount mismatch')
        response_currency = str(amount.get('currency') or '').strip().upper()
        if not response_currency or response_currency != str(tx.currency).strip().upper():
            raise ConflictError(f'WeChat {source} currency mismatch')

        return str(response.get('trade_state') or '').strip().upper()

    @staticmethod
    def reconcile_wechat_payment(
        db: Session,
        order: Order,
        out_trade_no: str | None = None,
    ) -> dict[str, Any]:
        normalized_trade_no = str(out_trade_no or '').strip()
        query = db.query(PaymentTransaction).filter(
            PaymentTransaction.order_id == order.id,
            PaymentTransaction.channel == PaymentChannel.WECHAT,
        )
        if normalized_trade_no:
            tx = query.filter(PaymentTransaction.out_trade_no == normalized_trade_no).first()
        else:
            tx = query.order_by(PaymentTransaction.id.desc()).first()
        if not tx:
            if normalized_trade_no:
                raise NotFoundError('Payment transaction not found')
            return {
                'order': order,
                'transaction': None,
                'provider_status': 'NO_TRANSACTION',
            }

        # Never query a different payment after the order has already been
        # settled.  A repeated client poll is idempotent and returns the local
        # success state immediately.
        if tx.status == PaymentStatus.PAID:
            return {
                'order': order,
                'transaction': tx,
                'provider_status': 'SUCCESS',
            }
        if order.pay_status == PayStatus.PAID:
            return {
                'order': order,
                'transaction': tx,
                'provider_status': 'ORDER_PAID_OTHER_TRANSACTION',
            }

        config = cast(WechatPayConfig, PaymentService._provider_config(PaymentChannel.WECHAT))
        if payment_config.mock_external_payment:
            return {'order': order, 'transaction': tx, 'provider_status': 'NOTPAY'}
        if not config.enabled:
            raise ConflictError('WeChat payment is not enabled')

        response = PaymentService._wechat_query_order(tx.out_trade_no, config)
        provider_status = PaymentService._validate_wechat_trade_response(
            response,
            config,
            tx,
            source='query',
        )
        # The provider request above runs outside the database lock. Refresh
        # under a row lock before handling any provider state so a concurrent
        # callback cannot be overwritten by a stale CLOSED/REVOKED result.
        db.refresh(tx, with_for_update=True)
        transaction_paid_after_refresh = tx.status == PaymentStatus.PAID
        response_trade_no = str(response.get('transaction_id') or '').strip()
        recorded_trade_no = getattr(tx, 'provider_trade_no', None)
        if (
            tx.status == PaymentStatus.PAID
            and response_trade_no
            and recorded_trade_no
            and recorded_trade_no != response_trade_no
        ):
            raise ConflictError('Payment transaction id conflicts with the recorded transaction')
        if provider_status == 'SUCCESS':
            provider_trade_no = response_trade_no
            if not provider_trade_no:
                raise ConflictError('WeChat query transaction_id is missing')
            if transaction_paid_after_refresh:
                if recorded_trade_no and recorded_trade_no != provider_trade_no:
                    raise ConflictError('Payment transaction id conflicts with the recorded transaction')
            else:
                notify_payload = {'source': 'trade_query', **response}
                closed_order_status = PaymentService._record_provider_success_for_closed_order(
                    db,
                    tx,
                    notify_payload,
                    provider_trade_no,
                )
                if closed_order_status:
                    provider_status = closed_order_status
                    # ``_record_provider_success_for_closed_order`` locks a
                    # fresh order internally, but the caller may still hold a
                    # stale identity-mapped instance for serialization.
                    order = PaymentService._refresh_locked_payment_order(db, order)
                else:
                    order = PaymentService.confirm_paid_order(
                        db,
                        tx,
                        notify_payload=notify_payload,
                        provider_trade_no=provider_trade_no,
                    )
        elif provider_status == 'CLOSED':
            if tx.status != PaymentStatus.PAID:
                tx.status = PaymentStatus.FAILED
                tx.failed_reason = provider_status
                tx.notify_payload = {'source': 'trade_query', **response}
                db.commit()
        elif provider_status not in {
            'NOTPAY',
            'USERPAYING',
            'PAYERROR',
            'REFUND',
            'REVOKED',
        }:
            raise ConflictError(
                f'WeChat query returned unknown status: {provider_status or "missing status"}'
            )

        if transaction_paid_after_refresh:
            order = PaymentService._refresh_locked_payment_order(db, order)

        return {
            'order': order,
            'transaction': tx,
            'provider_status': provider_status,
        }

    @staticmethod
    def reconcile_alipay_payment(
        db: Session,
        order: Order,
        out_trade_no: str | None = None,
    ) -> dict[str, Any]:
        normalized_trade_no = str(out_trade_no or '').strip()
        query = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.order_id == order.id,
                PaymentTransaction.channel == PaymentChannel.ALIPAY,
            )
        )
        if normalized_trade_no:
            tx = query.filter(PaymentTransaction.out_trade_no == normalized_trade_no).first()
            # Alipay may return a slightly different query string after the
            # browser leaves its hosted payment page. The authenticated order
            # is still the source of truth, so fall back to its latest active
            # Alipay transaction instead of failing before provider reconciliation.
            if not tx:
                tx = (
                    query.filter(
                        PaymentTransaction.status.in_(
                            (PaymentStatus.PENDING, PaymentStatus.PAID)
                        )
                    )
                    .order_by(PaymentTransaction.id.desc())
                    .first()
                )
        else:
            tx = query.order_by(PaymentTransaction.id.desc()).first()
        if not tx:
            if normalized_trade_no:
                raise NotFoundError('Payment transaction not found')
            return {
                'order': order,
                'transaction': None,
                'provider_status': 'NO_TRANSACTION',
            }
        normalized_trade_no = tx.out_trade_no
        if tx.status == PaymentStatus.PAID:
            return {
                'order': order,
                'transaction': tx,
                'provider_status': 'TRADE_SUCCESS',
            }
        if order.pay_status == PayStatus.PAID:
            return {
                'order': order,
                'transaction': tx,
                'provider_status': 'ORDER_PAID_OTHER_TRANSACTION',
            }

        config = cast(AlipayConfig, PaymentService._provider_config(PaymentChannel.ALIPAY))
        if payment_config.mock_external_payment:
            return {'order': order, 'transaction': tx, 'provider_status': 'WAIT_BUYER_PAY'}
        if not config.enabled:
            raise ConflictError('Alipay payment is not enabled')

        query_result = PaymentService._alipay_query_trade(normalized_trade_no, config)
        code = str(query_result.get('code') or '').strip()
        sub_code = str(query_result.get('sub_code') or '').strip()
        if code != '10000':
            if sub_code == 'ACQ.TRADE_NOT_EXIST':
                return {'order': order, 'transaction': tx, 'provider_status': 'WAIT_BUYER_PAY'}
            message = str(query_result.get('sub_msg') or query_result.get('msg') or 'unknown error')
            raise ConflictError(f'Alipay query failed: {message}')

        response_trade_no = str(query_result.get('out_trade_no') or '').strip()
        if response_trade_no != normalized_trade_no:
            raise ConflictError('Alipay query out_trade_no mismatch')
        try:
            queried_amount = Decimal(str(query_result.get('total_amount') or ''))
        except InvalidOperation as exc:
            raise ConflictError('Alipay query total_amount is invalid') from exc
        if quantize_amount(queried_amount) != quantize_amount(tx.amount):
            raise ConflictError('Alipay query amount mismatch')

        provider_status = str(query_result.get('trade_status') or '').upper()
        # The provider request above runs outside the database lock. Refresh
        # under a row lock before handling any provider state so a concurrent
        # callback cannot be overwritten by a stale TRADE_CLOSED result.
        db.refresh(tx, with_for_update=True)
        transaction_paid_after_refresh = tx.status == PaymentStatus.PAID
        response_trade_no = str(query_result.get('trade_no') or '').strip()
        recorded_trade_no = getattr(tx, 'provider_trade_no', None)
        if (
            tx.status == PaymentStatus.PAID
            and response_trade_no
            and recorded_trade_no
            and recorded_trade_no != response_trade_no
        ):
            raise ConflictError('Payment transaction id conflicts with the recorded transaction')
        if provider_status in {'TRADE_SUCCESS', 'TRADE_FINISHED'}:
            provider_trade_no = response_trade_no
            if not provider_trade_no:
                raise ConflictError('Alipay query trade_no is missing')
            if transaction_paid_after_refresh:
                if recorded_trade_no and recorded_trade_no != provider_trade_no:
                    raise ConflictError('Payment transaction id conflicts with the recorded transaction')
            else:
                notify_payload = {'source': 'trade_query', **query_result}
                closed_order_status = PaymentService._record_provider_success_for_closed_order(
                    db,
                    tx,
                    notify_payload,
                    provider_trade_no,
                )
                if closed_order_status:
                    provider_status = closed_order_status
                    order = PaymentService._refresh_locked_payment_order(db, order)
                else:
                    order = PaymentService.confirm_paid_order(
                        db,
                        tx,
                        notify_payload=notify_payload,
                        provider_trade_no=provider_trade_no,
                    )
        elif provider_status == 'TRADE_CLOSED':
            if tx.status != PaymentStatus.PAID:
                tx.status = PaymentStatus.FAILED
                tx.notify_payload = {'source': 'trade_query', **query_result}
                tx.failed_reason = provider_status
                db.commit()
        elif provider_status != 'WAIT_BUYER_PAY':
            raise ConflictError(f'Alipay query returned unknown status: {provider_status or "missing status"}')

        if transaction_paid_after_refresh:
            order = PaymentService._refresh_locked_payment_order(db, order)

        return {
            'order': order,
            'transaction': tx,
            'provider_status': provider_status,
        }

    @staticmethod
    def reconcile_alipay_return(
        db: Session,
        order: Order,
        payload: dict[str, str],
    ) -> dict[str, Any]:
        config = cast(AlipayConfig, PaymentService._provider_config(PaymentChannel.ALIPAY))
        if payment_config.mock_external_payment:
            raise ConflictError('Signed Alipay return is unavailable in mock payment mode')
        if not config.enabled:
            raise ConflictError('Alipay payment is not enabled')

        try:
            PaymentService._alipay_verify_signature(payload, config)
        except ForbiddenError:
            if not alipay_sandbox_query_bypass_enabled(config):
                raise
            return PaymentService.reconcile_alipay_payment(
                db,
                order,
                str(payload.get('out_trade_no') or '').strip(),
            )
        if str(payload.get('method') or '').strip() != 'alipay.trade.wap.pay.return':
            raise ConflictError('Alipay return method mismatch')

        out_trade_no = str(payload.get('out_trade_no') or '').strip()
        if not out_trade_no:
            raise NotFoundError('Payment transaction not found')
        tx = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.order_id == order.id,
                PaymentTransaction.channel == PaymentChannel.ALIPAY,
                PaymentTransaction.out_trade_no == out_trade_no,
            )
            .with_for_update()
            .first()
        )
        if not tx:
            raise NotFoundError('Payment transaction not found')

        PaymentService._validate_alipay_transaction_payload(payload, config, tx, source='return')
        trade_status = str(payload.get('trade_status') or '').strip().upper()
        if not trade_status:
            # The synchronous WAP return documented by Alipay does not always
            # include ``trade_status``.  A signed return without that optional
            # field must be confirmed through the authenticated server-side
            # trade query instead of being treated as success.
            return PaymentService.reconcile_alipay_payment(db, order, out_trade_no)
        if trade_status not in {'TRADE_SUCCESS', 'TRADE_FINISHED'}:
            raise ConflictError(
                f'Alipay return not successful: {trade_status}'
            )
        provider_trade_no = str(payload.get('trade_no') or '').strip()
        if not provider_trade_no:
            raise ConflictError('Alipay return trade_no is missing')
        if tx.status != PaymentStatus.PAID:
            closed_order_status = PaymentService._record_provider_success_for_closed_order(
                db,
                tx,
                {'source': 'signed_return', **payload},
                provider_trade_no,
            )
            if closed_order_status:
                return {
                    'order': order,
                    'transaction': tx,
                    'provider_status': closed_order_status,
                }
        paid_order = PaymentService.confirm_paid_order(
            db,
            tx,
            notify_payload={'source': 'signed_return', **payload},
            provider_trade_no=provider_trade_no,
        )
        return {
            'order': paid_order,
            'transaction': tx,
            'provider_status': 'TRADE_SUCCESS',
        }

    @staticmethod
    def _wechat_decrypt_notify_payload(payload: dict[str, Any], config: WechatPayConfig) -> dict[str, Any]:
        resource = payload.get('resource')
        if not isinstance(resource, dict):
            raise ConflictError('WeChat notify payload must contain encrypted resource')
        if not config.api_v3_key:
            raise ConflictError('WeChat API v3 key is not configured')
        if len(config.api_v3_key.encode('utf-8')) != 32:
            raise ConflictError('WeChat API v3 key must be exactly 32 bytes')
        ciphertext = str(resource.get('ciphertext') or '')
        nonce = str(resource.get('nonce') or '')
        associated_data = str(resource.get('associated_data') or '')
        algorithm = str(resource.get('algorithm') or 'AEAD_AES_256_GCM').strip().upper()
        if algorithm != 'AEAD_AES_256_GCM' or not ciphertext or not nonce:
            raise ConflictError('WeChat notify payload is missing encrypted data')
        try:
            encrypted_bytes = base64.b64decode(ciphertext, validate=True)
            aesgcm = AESGCM(config.api_v3_key.encode('utf-8'))
            plain_bytes = aesgcm.decrypt(
                nonce.encode('utf-8'),
                encrypted_bytes,
                associated_data.encode('utf-8'),
            )
            decrypted = json.loads(plain_bytes.decode('utf-8'))
        except (binascii.Error, InvalidTag, UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ForbiddenError('WeChat notify resource decryption failed') from exc
        if not isinstance(decrypted, dict):
            raise ConflictError('WeChat notify resource must be a JSON object')
        return decrypted

    @staticmethod
    def _wechat_validate_mock_notification_payload(
        payload: dict[str, Any],
        config: WechatPayConfig,
        tx: PaymentTransaction,
    ) -> tuple[str, str]:
        """Validate the explicit flat callback shape used by local mocks.

        Real WeChat callbacks always go through platform-signature
        verification and API-v3 resource decryption.  A local mock has no
        platform certificate, so it may opt into this compatibility path with
        an exact boolean ``mocked: true`` marker.  We still bind the callback
        to the known transaction and reject supplied identity/amount fields
        that contradict the local record.
        """
        out_trade_no = str(
            payload.get('out_trade_no')
            or payload.get('outTradeNo')
            or ''
        ).strip()
        if out_trade_no != tx.out_trade_no:
            raise ConflictError('WeChat mock out_trade_no mismatch')

        status = str(
            payload.get('trade_state')
            or payload.get('trade_status')
            or payload.get('tradeState')
            or payload.get('tradeStatus')
            or ''
        ).strip().upper()
        status = {
            'TRADE_SUCCESS': 'SUCCESS',
            'TRADE_FINISHED': 'SUCCESS',
            'TRADE_CLOSED': 'CLOSED',
        }.get(status, status)
        if status not in {
            'SUCCESS',
            'NOTPAY',
            'USERPAYING',
            'PAYERROR',
            'CLOSED',
            'REFUND',
            'REVOKED',
        }:
            raise ConflictError(f'WeChat mock notify returned unknown status: {status or "missing status"}')

        # Optional fields are checked when supplied, while older local tools
        # that only sent out_trade_no/trade_state remain compatible.
        app_id = str(payload.get('appid') or payload.get('app_id') or '').strip()
        if app_id:
            if config.app_id and app_id != config.app_id:
                raise ConflictError('WeChat mock appid mismatch')
            if tx.provider_app_id and app_id != tx.provider_app_id:
                raise ConflictError('WeChat mock transaction appid mismatch')
        mchid = str(payload.get('mchid') or payload.get('merchant_id') or '').strip()
        if mchid and config.mchid and mchid != config.mchid:
            raise ConflictError('WeChat mock mchid mismatch')

        amount = payload.get('amount')
        if amount is not None:
            if isinstance(amount, dict):
                response_cents = PaymentService._wechat_amount_cents(
                    amount.get('total'),
                    field_name='mock notify amount.total',
                )
                response_currency = str(amount.get('currency') or '').strip().upper()
            else:
                # Accept the legacy scalar ``total_amount`` shape only in the
                # explicitly marked mock path.
                try:
                    response_cents = int(quantize_amount(Decimal(str(amount))) * 100)
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise ConflictError('WeChat mock notify amount is invalid') from exc
                response_currency = str(payload.get('currency') or '').strip().upper()
            expected_cents = int(quantize_amount(tx.amount) * 100)
            if response_cents != expected_cents:
                raise ConflictError('WeChat mock notify amount mismatch')
            if response_currency and response_currency != str(tx.currency).strip().upper():
                raise ConflictError('WeChat mock notify currency mismatch')
        elif payload.get('total_amount') is not None:
            try:
                response_amount = quantize_amount(Decimal(str(payload.get('total_amount'))))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ConflictError('WeChat mock notify total_amount is invalid') from exc
            if response_amount != quantize_amount(tx.amount):
                raise ConflictError('WeChat mock notify amount mismatch')

        provider_trade_no = str(
            payload.get('transaction_id')
            or payload.get('trade_no')
            or payload.get('tradeNo')
            or ''
        ).strip()
        if status == 'SUCCESS' and not provider_trade_no:
            raise ConflictError('WeChat mock notify transaction_id is missing')
        return status, provider_trade_no

    @staticmethod
    def _wechat_header(headers: Mapping[str, Any] | None, name: str) -> str:
        if not headers:
            return ''
        target = name.lower()
        for key, value in headers.items():
            if str(key).lower() == target:
                return str(value or '').strip()
        return ''

    @staticmethod
    def _wechat_serial_matches(value: str, certificate: x509.Certificate) -> bool:
        normalized = str(value or '').strip().upper()
        if not normalized:
            return False
        if normalized.startswith('0X'):
            normalized = normalized[2:]
        normalized = normalized.lstrip('0') or '0'
        serial_decimal = str(certificate.serial_number).upper()
        serial_hex = format(certificate.serial_number, 'X').upper()
        return normalized in {
            serial_decimal.lstrip('0') or '0',
            serial_hex.lstrip('0') or '0',
        }

    @staticmethod
    def _wechat_platform_certificate(config: WechatPayConfig, serial: str) -> x509.Certificate:
        certificate_path = Path(str(config.platform_cert_path or ''))
        if not certificate_path.is_file():
            raise ConflictError(f'WeChat platform certificate not found: {config.platform_cert_path}')
        try:
            certificates = x509.load_pem_x509_certificates(certificate_path.read_bytes())
        except (OSError, ValueError) as exc:
            raise ConflictError('WeChat platform certificate format is invalid') from exc
        for certificate in certificates:
            if PaymentService._wechat_serial_matches(serial, certificate):
                public_key = certificate.public_key()
                if not isinstance(public_key, RSAPublicKey):
                    raise ForbiddenError('WeChat platform certificate key type is invalid')
                return certificate
        raise ForbiddenError('WeChat platform certificate serial does not match notification')

    @staticmethod
    def _wechat_verify_notify_signature(
        raw_body: bytes | str,
        headers: Mapping[str, Any] | None,
        config: WechatPayConfig,
    ) -> None:
        PaymentService._wechat_verify_platform_signature(
            raw_body,
            headers,
            config,
            source='notify',
        )

    @staticmethod
    def _wechat_verify_platform_signature(
        raw_body: bytes | str,
        headers: Mapping[str, Any] | None,
        config: WechatPayConfig,
        *,
        source: str,
    ) -> None:
        """Verify a callback or API response with a WeChat platform cert."""
        label = f'WeChat {source}'
        timestamp = PaymentService._wechat_header(headers, 'Wechatpay-Timestamp')
        nonce = PaymentService._wechat_header(headers, 'Wechatpay-Nonce')
        signature = PaymentService._wechat_header(headers, 'Wechatpay-Signature')
        serial = PaymentService._wechat_header(headers, 'Wechatpay-Serial')
        if not timestamp or not nonce or not signature or not serial:
            raise ForbiddenError(f'{label} signature headers are incomplete')
        try:
            timestamp_int = int(timestamp)
        except ValueError as exc:
            raise ForbiddenError(f'{label} timestamp is invalid') from exc
        if abs(unix_timestamp() - timestamp_int) > WECHAT_NOTIFY_TIMESTAMP_TOLERANCE_SECONDS:
            raise ForbiddenError(f'{label} timestamp is outside the allowed window')
        if isinstance(raw_body, str):
            body_bytes = raw_body.encode('utf-8')
        elif isinstance(raw_body, bytes):
            body_bytes = raw_body
        else:
            raise ForbiddenError(f'{label} body is invalid')

        certificate = PaymentService._wechat_platform_certificate(config, serial)
        message = f'{timestamp}\n{nonce}\n'.encode() + body_bytes + b'\n'
        try:
            decoded_signature = base64.b64decode(signature, validate=True)
            public_key = certificate.public_key()
            public_key.verify(
                decoded_signature,
                message,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (binascii.Error, InvalidSignature, ValueError, TypeError) as exc:
            raise ForbiddenError(f'{label} signature is invalid') from exc

    @staticmethod
    def _validate_wechat_notification_payload(
        payload: dict[str, Any],
        config: WechatPayConfig,
        tx: PaymentTransaction,
    ) -> tuple[str, str]:
        state = PaymentService._validate_wechat_trade_response(
            payload,
            config,
            tx,
            source='notify',
        )
        if state not in {
            'SUCCESS',
            'NOTPAY',
            'USERPAYING',
            'PAYERROR',
            'CLOSED',
            'REFUND',
            'REVOKED',
        }:
            raise ConflictError(f'WeChat notify returned unknown status: {state or "missing status"}')
        provider_trade_no = str(payload.get('transaction_id') or '').strip()
        if state == 'SUCCESS' and not provider_trade_no:
            raise ConflictError('WeChat notify transaction_id is missing')
        return state, provider_trade_no

    @staticmethod
    def serialize_refund(refund: PaymentRefund | None) -> dict[str, Any] | None:
        if refund is None:
            return None
        return {
            'id': refund.id,
            'refund_id': refund.id,
            'order_id': refund.order_id,
            'payment_transaction_id': refund.payment_transaction_id,
            'order_no': refund.order_no,
            'channel': str(getattr(refund.channel, 'value', refund.channel)),
            'status': PaymentService._refund_status_value(refund),
            'currency': refund.currency,
            'original_amount': float(refund.original_amount),
            'refund_amount': float(refund.refund_amount),
            'out_refund_no': refund.out_refund_no,
            'provider_refund_id': refund.provider_refund_id,
            'provider_trade_no': refund.provider_trade_no,
            'provider_status': refund.provider_status,
            'reason': refund.reason,
            'error_code': refund.error_code,
            'error_message': refund.error_message,
            'requested_at': refund.requested_at.isoformat() if refund.requested_at else None,
            'processed_at': refund.processed_at.isoformat() if refund.processed_at else None,
            'success_at': refund.success_at.isoformat() if refund.success_at else None,
            'last_synced_at': refund.last_synced_at.isoformat() if refund.last_synced_at else None,
            'next_retry_at': refund.next_retry_at.isoformat() if refund.next_retry_at else None,
            'attempt_count': refund.attempt_count,
        }

    @staticmethod
    def handle_wechat_refund_notify(
        db: Session,
        payload: dict[str, Any],
        *,
        raw_body: bytes | str | None = None,
        headers: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify, decrypt and apply a WeChat refund notification."""
        if not isinstance(payload, dict):
            raise ConflictError('WeChat refund notify payload must be a JSON object')
        config = cast(WechatPayConfig, PaymentService._provider_config(PaymentChannel.WECHAT))
        event_type = str(payload.get('event_type') or '').strip().upper()
        if event_type and event_type not in {'REFUND.SUCCESS', 'REFUND.ABNORMAL', 'REFUND.CLOSED'}:
            raise ConflictError(f'Unsupported WeChat refund notify event: {event_type}')
        if not payment_config.mock_external_payment:
            if not config.enabled:
                raise ConflictError('WeChat payment is not enabled')
            if raw_body is None:
                raise ForbiddenError('WeChat refund notify raw body is required')
            PaymentService._wechat_verify_notify_signature(raw_body, headers, config)

        normalized_payload = payload
        if payment_config.mock_external_payment and 'resource' not in payload:
            if payload.get('mocked') is not True:
                normalized_payload = PaymentService._wechat_decrypt_notify_payload(payload, config)
        else:
            normalized_payload = PaymentService._wechat_decrypt_notify_payload(payload, config)

        out_refund_no = str(normalized_payload.get('out_refund_no') or '').strip()
        if not out_refund_no:
            raise NotFoundError('Payment refund not found')
        refund_id = (
            db.query(PaymentRefund.id)
            .filter(PaymentRefund.out_refund_no == out_refund_no)
            .scalar()
        )
        if not refund_id:
            raise NotFoundError('Payment refund not found')
        _order, tx, refund = PaymentService._lock_wechat_refund_context(db, int(refund_id))
        provider_notify_id = str(payload.get('id') or '').strip() or None
        if provider_notify_id and refund.provider_notify_id == provider_notify_id:
            status = PaymentService._refund_status_value(refund)
            if status == RefundStatus.SUCCESS.value:
                # A prior attempt may have persisted provider success but
                # failed during local finalization. Re-run the idempotent
                # finalizer so this duplicate notification can repair that
                # gap instead of acknowledging it forever.
                from app.services.order_service import OrderService

                OrderService.finalize_external_refund(db, refund, tx)
            else:
                db.commit()
            return {
                'refund_id': refund.id,
                'out_refund_no': refund.out_refund_no,
                'provider_status': status,
            }
        status, provider_refund_id = PaymentService._validate_wechat_refund_response(
            normalized_payload,
            refund,
            tx,
            source='notify',
        )
        if event_type and status != event_type.rsplit('.', 1)[-1]:
            raise ConflictError('WeChat refund notify event does not match refund status')
        PaymentService._apply_wechat_refund_response(
            db,
            refund,
            tx,
            normalized_payload,
            source='notify',
            notify_payload=normalized_payload,
            provider_notify_id=provider_notify_id,
        )
        if status == 'SUCCESS':
            from app.services.order_service import OrderService

            OrderService.finalize_external_refund(db, refund, tx)
        return {
            'refund_id': refund.id,
            'out_refund_no': refund.out_refund_no,
            'provider_refund_no': provider_refund_id,
            'provider_status': status,
        }

    @staticmethod
    def _alipay_verify_signature(payload: dict[str, Any], config: AlipayConfig) -> None:
        if not config.alipay_public_cert_path:
            raise ConflictError('Alipay public certificate path is not configured')
        if 'sign' not in payload:
            raise ConflictError('Alipay payload is missing sign')
        if str(payload.get('sign_type') or '').upper() != 'RSA2':
            raise ForbiddenError('Alipay sign_type is invalid')
        public_key = PaymentService._load_certificate_public_key(
            config.alipay_public_cert_path,
            str(payload.get('alipay_cert_sn') or '').strip(),
        )
        unsigned_payload = {
            key: value
            for key, value in payload.items()
            if key not in {'sign', 'sign_type'}
        }
        message = PaymentService._alipay_sign_string(unsigned_payload, exclude_sign_type=True)
        try:
            signature = base64.b64decode(str(payload['sign']), validate=True)
            public_key.verify(
                signature,
                message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except (binascii.Error, InvalidSignature, ValueError) as exc:
            raise ForbiddenError('Alipay signature is invalid') from exc

    @staticmethod
    def _validate_alipay_transaction_payload(
        payload: dict[str, Any],
        config: AlipayConfig,
        tx: PaymentTransaction,
        *,
        source: str,
    ) -> None:
        app_id = str(payload.get('app_id') or '').strip()
        if not app_id or app_id != config.app_id:
            raise ConflictError(f'Alipay {source} app_id mismatch')
        if tx.provider_app_id and tx.provider_app_id != app_id:
            raise ConflictError(f'Alipay {source} transaction app_id mismatch')

        total_amount = str(payload.get('total_amount') or '').strip()
        try:
            notified_amount = Decimal(total_amount)
        except InvalidOperation as exc:
            raise ConflictError(f'Alipay {source} total_amount is invalid') from exc
        if quantize_amount(notified_amount) != quantize_amount(tx.amount):
            raise ConflictError(f'Alipay {source} amount mismatch')

        seller_id = str(payload.get('seller_id') or '').strip()
        if config.seller_id and seller_id != config.seller_id:
            raise ConflictError(f'Alipay {source} seller_id mismatch')

    @staticmethod
    def handle_notify(
        db: Session,
        channel: str,
        payload: dict[str, Any],
        *,
        raw_body: bytes | str | None = None,
        headers: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        pay_channel = PaymentChannel(str(channel).upper())
        if not isinstance(payload, dict):
            raise ConflictError('Payment notify payload must be a JSON object')

        normalized_payload = payload
        wechat_config: WechatPayConfig | None = None
        alipay_config: AlipayConfig | None = None
        mock_flat_wechat_notification = False

        if pay_channel == PaymentChannel.WECHAT:
            wechat_config = cast(WechatPayConfig, PaymentService._provider_config(pay_channel))
            event_type = str(payload.get('event_type') or '').strip().upper()
            if event_type and event_type != 'TRANSACTION.SUCCESS':
                raise ConflictError(f'Unsupported WeChat notify event: {event_type}')
            if not payment_config.mock_external_payment:
                if not wechat_config.enabled:
                    raise ConflictError('WeChat payment is not enabled')
                if raw_body is None:
                    raise ForbiddenError('WeChat notify raw body is required')
                PaymentService._wechat_verify_notify_signature(raw_body, headers, wechat_config)
            if payment_config.mock_external_payment and 'resource' not in payload:
                # Keep a deliberately explicit local-test escape hatch for
                # legacy tools.  Production mode never reaches this branch,
                # and a truthy string such as ``"true"`` is not accepted.
                if payload.get('mocked') is not True:
                    normalized_payload = PaymentService._wechat_decrypt_notify_payload(payload, wechat_config)
                else:
                    mock_flat_wechat_notification = True
                    normalized_payload = payload
            else:
                normalized_payload = PaymentService._wechat_decrypt_notify_payload(payload, wechat_config)
        elif pay_channel == PaymentChannel.ALIPAY and not payment_config.mock_external_payment:
            alipay_config = cast(AlipayConfig, PaymentService._provider_config(pay_channel))
            if not alipay_config.enabled:
                raise ConflictError('Alipay payment is not enabled')
            PaymentService._alipay_verify_signature(payload, alipay_config)

        out_trade_no = str(
            normalized_payload.get('out_trade_no')
            or normalized_payload.get('outTradeNo')
            or (payload.get('out_trade_no') if pay_channel == PaymentChannel.ALIPAY else '')
            or (payload.get('outTradeNo') if pay_channel == PaymentChannel.ALIPAY else '')
            or ''
        ).strip()
        if not out_trade_no:
            raise NotFoundError('Payment transaction not found')

        tx = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.out_trade_no == out_trade_no)
            .with_for_update()
            .first()
        )
        if not tx:
            raise NotFoundError('Payment transaction not found')
        if tx.channel != pay_channel:
            raise ConflictError('Payment channel mismatch')

        if pay_channel == PaymentChannel.WECHAT:
            assert wechat_config is not None
            if mock_flat_wechat_notification:
                status, provider_trade_no = PaymentService._wechat_validate_mock_notification_payload(
                    normalized_payload,
                    wechat_config,
                    tx,
                )
            else:
                status, provider_trade_no = PaymentService._validate_wechat_notification_payload(
                    normalized_payload,
                    wechat_config,
                    tx,
                )
            if status != 'SUCCESS':
                if status in {'CLOSED', 'REVOKED'} and tx.status != PaymentStatus.PAID:
                    tx.status = PaymentStatus.FAILED
                    tx.notify_payload = normalized_payload
                    tx.failed_reason = status
                    db.commit()
                return {
                    'order_id': tx.order_id,
                    'order_no': tx.order_no,
                    'out_trade_no': tx.out_trade_no,
                    'provider_trade_no': provider_trade_no,
                    'provider_status': status or 'UNKNOWN',
                }

            if tx.status != PaymentStatus.PAID:
                closed_order_status = PaymentService._record_provider_success_for_closed_order(
                    db,
                    tx,
                    normalized_payload,
                    provider_trade_no,
                )
                if closed_order_status:
                    return {
                        'order_id': tx.order_id,
                        'order_no': tx.order_no,
                        'out_trade_no': tx.out_trade_no,
                        'provider_trade_no': provider_trade_no,
                        'provider_status': closed_order_status,
                    }

            recorded_trade_no = getattr(tx, 'provider_trade_no', None)
            if tx.status == PaymentStatus.PAID or recorded_trade_no:
                if recorded_trade_no and recorded_trade_no != provider_trade_no:
                    raise ConflictError('Payment transaction id conflicts with the recorded transaction')
                # A repeated SUCCESS notification is acknowledged without
                # running order settlement a second time.
                if tx.status == PaymentStatus.PAID:
                    return {
                        'order_id': tx.order_id,
                        'order_no': tx.order_no,
                        'out_trade_no': tx.out_trade_no,
                        'provider_trade_no': provider_trade_no,
                        'provider_status': 'SUCCESS',
                    }

            order = PaymentService.confirm_paid_order(
                db,
                tx,
                notify_payload=normalized_payload,
                provider_trade_no=provider_trade_no,
            )
            return {
                'order_id': order.id,
                'order_no': order.order_no,
                'out_trade_no': tx.out_trade_no,
                'provider_trade_no': provider_trade_no,
                'provider_status': 'SUCCESS',
            }

        if alipay_config is not None:
            PaymentService._validate_alipay_transaction_payload(payload, alipay_config, tx, source='notify')

        status = str(
            normalized_payload.get('trade_state')
            or normalized_payload.get('trade_status')
            or normalized_payload.get('tradeState')
            or normalized_payload.get('tradeStatus')
            or ''
        ).upper()
        if status not in {'SUCCESS', 'TRADE_SUCCESS', 'TRADE_FINISHED'}:
            if status in {'CLOSED', 'TRADE_CLOSED'} and tx.status != PaymentStatus.PAID:
                tx.status = PaymentStatus.FAILED
                tx.notify_payload = normalized_payload
                tx.failed_reason = status
                db.commit()
            raise ConflictError(f'Payment not successful: {status or "missing status"}')

        provider_trade_no = str(
            normalized_payload.get('transaction_id')
            or normalized_payload.get('trade_no')
            or normalized_payload.get('tradeNo')
            or ''
        ).strip() or None
        if not provider_trade_no:
            raise ConflictError('Alipay notify trade_no is missing')
        if tx.status != PaymentStatus.PAID:
            closed_order_status = PaymentService._record_provider_success_for_closed_order(
                db,
                tx,
                normalized_payload,
                provider_trade_no,
            )
            if closed_order_status:
                return {
                    'order_id': tx.order_id,
                    'order_no': tx.order_no,
                    'out_trade_no': tx.out_trade_no,
                    'provider_trade_no': provider_trade_no,
                    'provider_status': closed_order_status,
                }
        order = PaymentService.confirm_paid_order(
            db,
            tx,
            notify_payload=normalized_payload,
            provider_trade_no=provider_trade_no,
        )
        return {
            'order_id': order.id,
            'order_no': order.order_no,
            'out_trade_no': tx.out_trade_no,
            'provider_trade_no': provider_trade_no,
        }
