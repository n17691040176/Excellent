from __future__ import annotations

import base64
import binascii
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import quote_plus, urlencode, urlparse
from uuid import uuid4

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.payment_config import (
    AlipayConfig,
    WechatPayConfig,
    alipay_certificate_sn,
    alipay_root_certificate_sn,
    load_alipay_certificates,
    payment_config,
)
from app.models.enums import OrderType, PaymentChannel, PaymentStatus, PayStatus
from app.models.order import Order
from app.models.payment import PaymentTransaction
from app.utils.helpers import now, quantize_amount


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
    def _load_public_key(path: str):
        last_error: Exception | None = None
        for candidate in PaymentService._key_candidates(path, ('PUBLIC KEY', 'RSA PUBLIC KEY')):
            try:
                return serialization.load_pem_public_key(candidate)
            except ValueError as exc:
                last_error = exc
            try:
                return x509.load_pem_x509_certificate(candidate).public_key()
            except ValueError as exc:
                last_error = exc
        raise ConflictError('Payment public key format is invalid') from last_error

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
    def _wechat_request_json(url: str, body: dict[str, Any], config: WechatPayConfig) -> dict[str, Any]:
        payload = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
        nonce = uuid4().hex
        timestamp = str(int(now().timestamp()))
        parsed = urlparse(url)
        canonical_url = parsed.path or '/'
        if parsed.query:
            canonical_url = f'{canonical_url}?{parsed.query}'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': PaymentService._wechat_authorization_header(
                'POST',
                canonical_url,
                payload,
                config,
                nonce,
                timestamp,
            ),
            'Wechatpay-Serial': config.merchant_serial_no,
        }
        req = urlrequest.Request(url, data=payload.encode('utf-8'), headers=headers, method='POST')
        try:
            with urlrequest.urlopen(req, timeout=payment_config.request_timeout_seconds) as resp:
                response_body = resp.read().decode('utf-8')
        except urlerror.HTTPError as exc:
            response_body = exc.read().decode('utf-8', errors='ignore')
            raise ConflictError(f'WeChat payment request failed: {response_body or exc.reason}') from exc
        except urlerror.URLError as exc:
            raise ConflictError(f'WeChat payment request failed: {exc.reason}') from exc
        if not response_body:
            return {}
        return json.loads(response_body)

    @staticmethod
    def _wechat_build_request_payment(order: Order, tx: PaymentTransaction, config: WechatPayConfig) -> dict[str, Any]:
        if not config.app_id:
            raise ConflictError('WeChat app_id is not configured')
        if not config.mchid:
            raise ConflictError('WeChat mchid is not configured')
        if not config.merchant_serial_no:
            raise ConflictError('WeChat merchant serial no is not configured')
        if not config.merchant_private_key_path:
            raise ConflictError('WeChat merchant private key path is not configured')
        if not config.notify_url:
            raise ConflictError('WeChat notify url is not configured')

        payload = {
            'appid': config.app_id,
            'mchid': config.mchid,
            'description': PaymentService._subject(order),
            'out_trade_no': tx.out_trade_no,
            'notify_url': config.notify_url,
            'amount': {
                'total': int(quantize_amount(tx.amount) * 100),
                'currency': tx.currency,
            },
        }
        response = PaymentService._wechat_request_json('https://api.mch.weixin.qq.com/v3/pay/transactions/app', payload, config)
        prepay_id = str(response.get('prepay_id') or '').strip()
        if not prepay_id:
            raise ConflictError('WeChat payment prepay_id is missing')

        nonce = uuid4().hex
        timestamp = str(int(now().timestamp()))
        private_key = PaymentService._load_private_key(config.merchant_private_key_path)
        sign_message = f'{config.app_id}\n{config.mchid}\n{prepay_id}\nSign=WXPay\n{nonce}\n{timestamp}\n'
        sign = PaymentService._rsa_sign(private_key, sign_message)
        request_payment = {
            'appid': config.app_id,
            'partnerid': config.mchid,
            'prepayid': prepay_id,
            'package': 'Sign=WXPay',
            'noncestr': nonce,
            'timestamp': timestamp,
            'sign': sign,
        }
        return {
            'provider': 'wxpay',
            'mocked': False,
            'status': 'PENDING',
            'order_no': order.order_no,
            'out_trade_no': tx.out_trade_no,
            'amount': float(tx.amount),
            'currency': tx.currency,
            'subject': PaymentService._subject(order),
            'request_payment': request_payment,
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
    def _alipay_return_url(order: Order, tx: PaymentTransaction, config: AlipayConfig) -> str:
        if not config.return_url:
            return ''
        base_url, separator, fragment = config.return_url.partition('#')
        query = urlencode({'order_id': order.id, 'out_trade_no': tx.out_trade_no})
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

        from app.services.order_service import UNPAID_ORDER_EXPIRE_MINUTES

        is_h5 = config.payment_method == 'alipay.trade.wap.pay'
        return_url = PaymentService._alipay_return_url(order, tx, config)
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
            'timestamp': now().strftime('%Y-%m-%d %H:%M:%S'),
            'version': '1.0',
            'notify_url': config.notify_url,
            'biz_content': json.dumps(biz_content, ensure_ascii=False, separators=(',', ':')),
        }
        if config.certificate_mode:
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
        if channel == PaymentChannel.WECHAT:
            request_payment = {
                'appid': 'mock-appid',
                'partnerid': 'mock-mchid',
                'prepayid': f'mock-prepay-{tx.out_trade_no}',
                'package': 'Sign=WXPay',
                'noncestr': uuid4().hex,
                'timestamp': str(int(now().timestamp())),
                'sign': 'MOCK-WECHAT-SIGN',
            }
        else:
            request_payment = f'mock-order-string-{tx.out_trade_no}'

        return {
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
        tx = PaymentService._ensure_transaction(db, order, pay_channel, request_payload)

        provider_config = PaymentService._provider_config(pay_channel)
        if payment_config.mock_external_payment:
            payment = PaymentService._mock_payment_payload(order, pay_channel, tx)
        elif not provider_config.enabled:
            raise ConflictError(f'{PaymentService._provider_name(pay_channel)} payment is not enabled')
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
        order = db.get(Order, tx.order_id)
        if not order:
            raise NotFoundError('Order not found')
        if tx.status == PaymentStatus.PAID and order.pay_status == PayStatus.PAID:
            return order

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
    def _wechat_decrypt_notify_payload(payload: dict[str, Any], config: WechatPayConfig) -> dict[str, Any]:
        resource = payload.get('resource')
        if not isinstance(resource, dict):
            return payload
        if not config.api_v3_key:
            raise ConflictError('WeChat API v3 key is not configured')
        ciphertext = str(resource.get('ciphertext') or '')
        nonce = str(resource.get('nonce') or '')
        associated_data = str(resource.get('associated_data') or '')
        if not ciphertext or not nonce:
            raise ConflictError('WeChat notify payload is missing encrypted data')
        aesgcm = AESGCM(config.api_v3_key.encode('utf-8'))
        plain_bytes = aesgcm.decrypt(
            nonce.encode('utf-8'),
            base64.b64decode(ciphertext),
            associated_data.encode('utf-8') if associated_data else None,
        )
        return json.loads(plain_bytes.decode('utf-8'))

    @staticmethod
    def _alipay_verify_notify(payload: dict[str, Any], config: AlipayConfig) -> None:
        public_key_path = config.alipay_public_cert_path if config.certificate_mode else config.public_key_path
        if not public_key_path:
            raise ConflictError('Alipay public key path is not configured')
        if 'sign' not in payload:
            raise ConflictError('Alipay notify payload is missing sign')
        if str(payload.get('sign_type') or '').upper() != 'RSA2':
            raise ForbiddenError('Alipay notify sign_type is invalid')
        public_key = PaymentService._load_public_key(public_key_path)
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
            raise ForbiddenError('Alipay notify signature is invalid') from exc

    @staticmethod
    def _validate_alipay_notify(
        payload: dict[str, Any],
        config: AlipayConfig,
        tx: PaymentTransaction,
    ) -> None:
        app_id = str(payload.get('app_id') or '').strip()
        if not app_id or app_id != config.app_id:
            raise ConflictError('Alipay notify app_id mismatch')
        if tx.provider_app_id and tx.provider_app_id != app_id:
            raise ConflictError('Alipay notify transaction app_id mismatch')

        total_amount = str(payload.get('total_amount') or '').strip()
        try:
            notified_amount = Decimal(total_amount)
        except InvalidOperation as exc:
            raise ConflictError('Alipay notify total_amount is invalid') from exc
        if quantize_amount(notified_amount) != quantize_amount(tx.amount):
            raise ConflictError('Alipay notify amount mismatch')

        seller_id = str(payload.get('seller_id') or '').strip()
        if config.seller_id and seller_id != config.seller_id:
            raise ConflictError('Alipay notify seller_id mismatch')

    @staticmethod
    def handle_notify(db: Session, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        pay_channel = PaymentChannel(str(channel).upper())
        normalized_payload = payload

        if pay_channel == PaymentChannel.WECHAT and not payment_config.mock_external_payment:
            wechat_config = cast(WechatPayConfig, PaymentService._provider_config(pay_channel))
            normalized_payload = PaymentService._wechat_decrypt_notify_payload(payload, wechat_config)
        if pay_channel == PaymentChannel.ALIPAY and not payment_config.mock_external_payment:
            alipay_config = cast(AlipayConfig, PaymentService._provider_config(pay_channel))
            if not alipay_config.enabled:
                raise ConflictError('Alipay payment is not enabled')
            PaymentService._alipay_verify_notify(payload, alipay_config)

        out_trade_no = str(
            normalized_payload.get('out_trade_no')
            or normalized_payload.get('outTradeNo')
            or payload.get('out_trade_no')
            or payload.get('outTradeNo')
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
        if pay_channel == PaymentChannel.ALIPAY and not payment_config.mock_external_payment:
            PaymentService._validate_alipay_notify(payload, alipay_config, tx)

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
        if pay_channel == PaymentChannel.ALIPAY and not provider_trade_no:
            raise ConflictError('Alipay notify trade_no is missing')
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
