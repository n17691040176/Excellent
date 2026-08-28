from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.exceptions import ConflictError
from app.core.payment_config import (
    AlipayConfig,
    PaymentConfig,
    WechatPayConfig,
    enabled_external_payment_channels,
    validate_payment_config,
)
from app.models.enums import OrderType
from app.services.payment_service import PaymentService


def _wechat_config(**overrides) -> WechatPayConfig:
    values = {
        'enabled': True,
        'app_id': 'wx-test-app',
        'mchid': 'test-mchid',
        'api_v3_key': 'x' * 32,
        'merchant_serial_no': 'test-serial',
        'merchant_private_key_path': '/run/secrets/wechat-merchant-private-key.pem',
        'platform_cert_path': '/run/secrets/wechat-platform-cert.pem',
        'notify_url': 'https://pay.example.test/api/v1/payments/wechat/notify',
        'refund_notify_url': 'https://pay.example.test/api/v1/payments/wechat/refund-notify',
    }
    values.update(overrides)
    return WechatPayConfig(**values)


def _config(wechat: WechatPayConfig) -> PaymentConfig:
    return PaymentConfig(
        mock_external_payment=False,
        wechat=wechat,
        alipay=AlipayConfig(enabled=False),
    )


def test_disabled_wechat_with_empty_values_is_valid_for_production():
    validate_payment_config(
        'production',
        _config(
            WechatPayConfig(
                enabled=False,
                app_id='',
                mchid='',
                api_v3_key='',
                merchant_serial_no='',
                merchant_private_key_path='',
                platform_cert_path='',
                notify_url='',
            )
        ),
    )


@pytest.mark.parametrize(
    'field',
    [
        'app_id',
        'mchid',
        'api_v3_key',
        'merchant_serial_no',
        'merchant_private_key_path',
        'platform_cert_path',
        'notify_url',
        'refund_notify_url',
    ],
)
def test_enabled_wechat_with_missing_required_value_fails_clearly(field):
    config = _config(_wechat_config(**{field: ''}))

    with pytest.raises((RuntimeError, ValueError, ConflictError)) as error:
        validate_payment_config('production', config)

    message = str(error.value)
    assert 'WECHAT' in message
    assert field.upper() in message or f'WECHAT_PAY_{field.upper()}' in message


def test_enabled_wechat_requires_a_32_byte_api_v3_key():
    config = _config(_wechat_config(api_v3_key='x' * 31))

    with pytest.raises((RuntimeError, ValueError, ConflictError)) as error:
        validate_payment_config('production', config)

    assert 'WECHAT' in str(error.value)
    assert 'API_V3_KEY' in str(error.value)


def test_enabled_non_mock_wechat_is_exposed_as_an_external_channel():
    channels = enabled_external_payment_channels(_config(_wechat_config()))

    assert 'WECHAT' in channels


def test_wechat_h5_type_defaults_to_wap_when_omitted():
    config = _wechat_config(h5_type='', h5_info_type='')

    assert PaymentService._wechat_h5_type(config) == 'Wap'


def test_wechat_h5_request_uses_mweb_endpoint_without_real_credentials():
    order = SimpleNamespace(
        id=42,
        order_no='ORDER-42',
        order_type=OrderType.SELF_OPERATED_ORDER,
    )
    transaction = SimpleNamespace(
        amount=Decimal('12.34'),
        currency='CNY',
        out_trade_no='PAYWE42000001',
        request_payload={
            'payer_client_ip': '203.0.113.7',
            'user_agent': '  test-browser  ',
        },
    )
    config = _wechat_config(
        h5_return_url='https://pay.example.test/orders/{order_id}/result',
    )

    with patch.object(
        PaymentService,
        '_wechat_request_json',
        return_value={'h5_url': 'https://pay.example.test/wechat/h5?token=mock'},
    ) as request:
        payment = PaymentService._wechat_build_request_payment(order, transaction, config)

    request_url, payload, passed_config = request.call_args.args
    assert request_url.endswith('/v3/pay/transactions/h5')
    assert passed_config is config
    assert payload['out_trade_no'] == transaction.out_trade_no
    assert payload['amount'] == {'total': 1234, 'currency': 'CNY'}
    assert payload['scene_info'] == {
        'payer_client_ip': '203.0.113.7',
        'h5_info': {'type': 'Wap'},
    }
    assert payload['time_expire']
    assert payment['h5_url'] == 'https://pay.example.test/wechat/h5?token=mock'
    assert 'redirect_url=' in payment['payment_url']
    assert 'order_id%3D42' in payment['payment_url']


def test_canonical_h5_type_takes_precedence_over_legacy_alias():
    assert PaymentService._wechat_h5_type(
        _wechat_config(h5_type='WAP', h5_info_type='IOS')
    ) == 'Wap'
    assert PaymentService._wechat_h5_type(
        _wechat_config(h5_type='', h5_info_type='IOS')
    ) == 'iOS'


def test_config_validation_keeps_canonical_h5_type_ahead_of_legacy_alias():
    """A stale legacy value must not invalidate an explicit canonical type."""
    config = _config(
        _wechat_config(
            h5_type='WAP',
            h5_info_type='NOT_A_TYPE',
            merchant_private_key_path='',
            platform_cert_path='',
        )
    )

    # The fixture intentionally leaves certificate paths empty; assert that
    # validation reports those material errors without adding a false H5-type
    # error from the legacy alias.
    with pytest.raises(RuntimeError) as error:
        validate_payment_config('production', config)

    assert 'WECHAT_PAY_H5_TYPE' not in str(error.value)


def test_wechat_h5_payment_url_replaces_an_existing_redirect_parameter():
    result = PaymentService._wechat_h5_payment_url(
        'https://pay.example.test/h5?token=abc&redirect_url=old',
        'https://shop.example.test/#/orders/42',
    )

    assert result.count('redirect_url=') == 1
    assert 'token=abc' in result
    assert 'shop.example.test' in result


@pytest.mark.parametrize(
    'return_url',
    [
        'https://pay.example.test/{}',
        'https://pay.example.test/{unknown}',
        'https://pay.example.test/{order_id!r}',
        'https://pay.example.test/{order_id:100000}',
        'https://pay.example.test/{order_id.__class__}',
    ],
)
def test_wechat_h5_return_url_rejects_unsupported_placeholders(return_url):
    order = SimpleNamespace(id=42)
    transaction = SimpleNamespace(out_trade_no='PAYWE42000001')

    with pytest.raises(ConflictError, match='unsupported placeholder'):
        PaymentService._wechat_redirect_url(
            order,
            transaction,
            _wechat_config(h5_return_url=return_url),
        )


@pytest.mark.parametrize(
    'url',
    [
        'javascript:alert(1)',
        'data:text/html,not-payment',
        '/relative/payment',
        'ftp://pay.example.test/h5',
        'https://[malformed/h5',
    ],
)
def test_wechat_h5_payment_url_rejects_non_http_absolute_urls(url):
    with pytest.raises(ConflictError, match=r'HTTP\(S\)'):
        PaymentService._wechat_h5_payment_url(url, None)


@pytest.mark.parametrize('scheme', ['ftp', 'javascript'])
def test_development_wechat_urls_still_require_http_or_https(scheme):
    config = _wechat_config(notify_url=f'{scheme}://pay.example.test/notify')
    with pytest.raises((RuntimeError, ValueError, ConflictError), match=r'HTTP\(S\)'):
        validate_payment_config('development', _config(config))


@pytest.mark.parametrize(
    'refund_notify_url',
    [
        'http://pay.example.test/api/v1/payments/wechat/refund-notify',
        'https://pay.example.test/api/v1/payments/wechat/refund-notify?token=secret',
        'https://pay.example.test/api/v1/payments/wechat/refund-notify#fragment',
        'https://pay.example.test/' + ('x' * 240),
    ],
)
def test_production_wechat_refund_notify_url_has_strict_callback_shape(refund_notify_url):
    config = _config(
        _wechat_config(
            refund_notify_url=refund_notify_url,
            merchant_private_key_path='',
            platform_cert_path='',
        )
    )

    with pytest.raises(RuntimeError) as error:
        validate_payment_config('production', config)

    assert 'WECHAT_PAY_REFUND_NOTIFY_URL' in str(error.value)


def test_production_wechat_refund_notify_url_accepts_plain_https_callback():
    config = _config(
        _wechat_config(
            refund_notify_url='https://pay.example.test/api/v1/payments/wechat/refund-notify',
            merchant_private_key_path='',
            platform_cert_path='',
        )
    )

    with pytest.raises(RuntimeError) as error:
        validate_payment_config('production', config)

    assert 'WECHAT_PAY_REFUND_NOTIFY_URL' not in str(error.value)
