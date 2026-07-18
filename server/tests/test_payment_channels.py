from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.api.v1.mobile_serializers import _product_payment_options
from app.core.exceptions import ConflictError
from app.core.payment_config import AlipayConfig, PaymentConfig, WechatPayConfig, enabled_external_payment_channels
from app.models.enums import AssetType, ZoneType
from app.services.order_service import OrderService


def test_only_alipay_can_be_enabled_as_external_channel():
    config = PaymentConfig(
        mock_external_payment=False,
        wechat=WechatPayConfig(enabled=True),
        alipay=AlipayConfig(enabled=True),
    )

    assert enabled_external_payment_channels(config) == ['ALIPAY']


def test_mock_mode_keeps_wechat_disabled():
    assert enabled_external_payment_channels(PaymentConfig(mock_external_payment=True)) == ['ALIPAY']


def test_product_payment_options_are_fixed_and_report_availability():
    with patch('app.api.v1.mobile_serializers.enabled_external_payment_channels', return_value=['ALIPAY']):
        options = _product_payment_options(None, {})

    assert [item['value'] for item in options] == ['BALANCE', 'WECHAT', 'ALIPAY']
    assert [item['available'] for item in options] == [True, False, True]
    assert options[1]['desc'] == '正在开发'


def test_wechat_is_rejected_while_under_development():
    with (
        patch('app.services.order_service.enabled_external_payment_channels', return_value=['ALIPAY']),
        pytest.raises(ConflictError, match='under development'),
    ):
        OrderService._validate_payment_rules(
            ZoneType.SELF_OPERATED,
            Decimal('10.00'),
            [],
            {},
            'WECHAT',
        )


def test_balance_cash_payment_is_available_independent_of_legacy_zone_switches():
    legacy_config = SimpleNamespace(
        balance_purchase_enabled=False,
        balance_only_enabled=False,
        cash_only_enabled=False,
    )

    OrderService._validate_payment_rules(
        ZoneType.SELF_OPERATED,
        Decimal('10.00'),
        [legacy_config],
        {AssetType.BALANCE: Decimal('10.00')},
        'BALANCE',
    )
