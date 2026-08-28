from __future__ import annotations

import base64
import io
import json
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from app.core.exceptions import ForbiddenError
from app.core.payment_config import AlipayConfig, PaymentConfig, WechatPayConfig
from app.services import payment_service as payment_module
from app.services.payment_service import PaymentService, WechatApiError

WECHAT_API_URL = 'https://api.mch.weixin.qq.com/v3/pay/transactions/h5'
WECHAT_RESPONSE_TIMESTAMP = 1_700_000_000


def _certificate(private_key: rsa.RSAPrivateKey, serial_number: int) -> x509.Certificate:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'WeChat Platform')])
    issued_at = datetime.now(UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(serial_number)
        .not_valid_before(issued_at - timedelta(days=1))
        .not_valid_after(issued_at + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )


@pytest.fixture
def wechat_response_credentials(tmp_path: Path):
    merchant_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    platform_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    platform_certificate = _certificate(platform_private_key, serial_number=987654321)

    merchant_key_path = tmp_path / 'merchant-private-key.pem'
    merchant_key_path.write_bytes(
        merchant_private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    platform_cert_path = tmp_path / 'wechat-platform-cert.pem'
    platform_cert_path.write_bytes(platform_certificate.public_bytes(serialization.Encoding.PEM))

    config = WechatPayConfig(
        enabled=True,
        app_id='wx-test-app',
        mchid='test-mchid',
        api_v3_key='x' * 32,
        merchant_serial_no='merchant-serial',
        merchant_private_key_path=str(merchant_key_path),
        platform_cert_path=str(platform_cert_path),
        notify_url='https://pay.example.test/api/v1/payments/wechat/notify',
        refund_notify_url='https://pay.example.test/api/v1/payments/wechat/refund-notify',
    )
    return config, platform_private_key, str(platform_certificate.serial_number)


def _response_headers(
    platform_private_key: rsa.RSAPrivateKey,
    serial: str,
    raw_body: bytes,
    *,
    timestamp: int = WECHAT_RESPONSE_TIMESTAMP,
) -> dict[str, str]:
    nonce = 'wechat-response-nonce'
    message = f'{timestamp}\n{nonce}\n'.encode() + raw_body + b'\n'
    signature = platform_private_key.sign(
        message,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return {
        'Wechatpay-Timestamp': str(timestamp),
        'Wechatpay-Nonce': nonce,
        'Wechatpay-Signature': base64.b64encode(signature).decode('ascii'),
        'Wechatpay-Serial': serial,
    }


def _http_headers(values: dict[str, str]) -> Message:
    headers = Message()
    for name, value in values.items():
        headers[name] = value
    return headers


def _success_response(raw_body: bytes, headers: dict[str, str]) -> MagicMock:
    response = MagicMock()
    response.status = 200
    response.headers = _http_headers(headers)
    response.read.return_value = raw_body
    return response


def _payment_config(config: WechatPayConfig) -> PaymentConfig:
    return PaymentConfig(
        mock_external_payment=False,
        wechat=config,
        alipay=AlipayConfig(enabled=False),
    )


def _request_with_response(response: MagicMock, config: WechatPayConfig):
    with (
        patch.object(payment_module, 'payment_config', _payment_config(config)),
        patch.object(payment_module, 'unix_timestamp', return_value=WECHAT_RESPONSE_TIMESTAMP),
        patch.object(payment_module.urlrequest, 'urlopen') as urlopen,
    ):
        urlopen.return_value.__enter__.return_value = response
        return PaymentService._wechat_request_json_with_status(
            WECHAT_API_URL,
            {'description': 'signature test'},
            config,
        )


def test_wechat_api_success_response_requires_and_accepts_valid_platform_signature(
    wechat_response_credentials,
):
    config, platform_private_key, serial = wechat_response_credentials
    payload = {'h5_url': 'https://wx.tenpay.com/cgi-bin/mmpayweb-bin/checkmweb?prepay_id=wx-test'}
    raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    response = _success_response(raw_body, _response_headers(platform_private_key, serial, raw_body))

    status, result = _request_with_response(response, config)

    assert status == 200
    assert result == payload


@pytest.mark.parametrize(
    'missing_header',
    [
        'Wechatpay-Timestamp',
        'Wechatpay-Nonce',
        'Wechatpay-Signature',
        'Wechatpay-Serial',
    ],
)
def test_wechat_api_success_response_rejects_missing_signature_headers(
    wechat_response_credentials,
    missing_header,
):
    config, platform_private_key, serial = wechat_response_credentials
    raw_body = b'{"h5_url":"https://wx.tenpay.com/payment"}'
    headers = _response_headers(platform_private_key, serial, raw_body)
    headers.pop(missing_header)

    with pytest.raises(ForbiddenError, match='signature headers are incomplete'):
        _request_with_response(_success_response(raw_body, headers), config)


def test_wechat_api_success_response_rejects_corrupted_platform_signature(
    wechat_response_credentials,
):
    config, platform_private_key, serial = wechat_response_credentials
    raw_body = b'{"h5_url":"https://wx.tenpay.com/payment"}'
    headers = _response_headers(platform_private_key, serial, raw_body)
    headers['Wechatpay-Signature'] = base64.b64encode(b'corrupted-signature').decode('ascii')

    with pytest.raises(ForbiddenError, match='signature is invalid'):
        _request_with_response(_success_response(raw_body, headers), config)


def _request_with_http_error(error: HTTPError, config: WechatPayConfig):
    with (
        patch.object(payment_module, 'payment_config', _payment_config(config)),
        patch.object(payment_module, 'unix_timestamp', return_value=WECHAT_RESPONSE_TIMESTAMP),
        patch.object(payment_module.urlrequest, 'urlopen', side_effect=error),
    ):
        return PaymentService._wechat_request_json_with_status(
            WECHAT_API_URL,
            {'description': 'signature test'},
            config,
        )


def test_wechat_api_unsigned_http_error_is_rejected_before_provider_error_classification(
    wechat_response_credentials,
):
    config, _platform_private_key, _serial = wechat_response_credentials
    raw_body = b'{"code":"OUT_TRADE_NO_USED","message":"duplicate"}'
    error = HTTPError(
        WECHAT_API_URL,
        400,
        'Bad Request',
        _http_headers({}),
        io.BytesIO(raw_body),
    )

    with pytest.raises(ForbiddenError, match='signature headers are incomplete'):
        _request_with_http_error(error, config)


def test_wechat_api_validly_signed_http_error_preserves_provider_error_details(
    wechat_response_credentials,
):
    config, platform_private_key, serial = wechat_response_credentials
    payload = {'code': 'OUT_TRADE_NO_USED', 'message': 'duplicate'}
    raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    error = HTTPError(
        WECHAT_API_URL,
        400,
        'Bad Request',
        _http_headers(_response_headers(platform_private_key, serial, raw_body)),
        io.BytesIO(raw_body),
    )

    with pytest.raises(WechatApiError) as raised:
        _request_with_http_error(error, config)

    assert raised.value.http_status == 400
    assert raised.value.retryable is False
    assert raised.value.response_payload == payload
