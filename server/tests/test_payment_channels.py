from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.mobile_serializers import _product_payment_flags, _product_payment_options
from app.core.exceptions import ConflictError
from app.core.payment_config import AlipayConfig, PaymentConfig, WechatPayConfig, enabled_external_payment_channels
from app.models.enums import AssetType, ZoneType
from app.services.catalog_service import ProductService
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
        options = _product_payment_options(
            None,
            {'balance_purchase_enabled': True, 'alipay_purchase_enabled': True},
        )

    assert [item['value'] for item in options] == ['BALANCE', 'WECHAT', 'ALIPAY']
    assert [item['available'] for item in options] == [True, False, True]
    assert options[1]['desc'] == '正在开发'


def test_product_payment_options_require_admin_and_provider_alipay_configuration():
    with patch('app.api.v1.mobile_serializers.enabled_external_payment_channels', return_value=['ALIPAY']):
        admin_disabled = _product_payment_options(
            None,
            {'balance_purchase_enabled': True, 'alipay_purchase_enabled': False},
        )
    with patch('app.api.v1.mobile_serializers.enabled_external_payment_channels', return_value=[]):
        provider_disabled = _product_payment_options(
            None,
            {'balance_purchase_enabled': True, 'alipay_purchase_enabled': True},
        )

    assert admin_disabled[2]['available'] is False
    assert admin_disabled[2]['unavailable_reason'] == '后台未开启支付宝支付'
    assert provider_disabled[2]['available'] is False
    assert provider_disabled[2]['unavailable_reason'] == '支付宝全局配置未就绪'


def test_product_payment_flags_use_admin_channel_switches():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
        points_purchase_enabled=True,
        balance_purchase_enabled=False,
        alipay_purchase_enabled=True,
        wechat_purchase_enabled=False,
        points_only_enabled=False,
        points_cash_enabled=True,
        cash_only_enabled=True,
        balance_only_enabled=True,
        balance_points_enabled=True,
    )
    product = SimpleNamespace(id=1, zone_type=ZoneType.SELF_OPERATED)

    flags = _product_payment_flags(db, product)

    assert flags['balance_purchase_enabled'] is False
    assert flags['alipay_purchase_enabled'] is True
    assert flags['wechat_purchase_enabled'] is False


def test_admin_zone_summary_hides_legacy_payment_modes():
    summary = ProductService._zone_config_summary(
        {
            'configured': True,
            'zone_type': ZoneType.SELF_OPERATED.value,
            'balance_purchase_enabled': True,
            'alipay_purchase_enabled': True,
            'points_purchase_enabled': True,
            'points_only_enabled': True,
            'points_cash_enabled': True,
            'cash_only_enabled': True,
            'voucher_deduct_min_rate': 50,
            'voucher_deduct_max_rate': 70,
            'ai_coupon_reward_rate': 20,
            'ai_coupon_max_deduct_rate': 20,
        }
    )

    assert summary['badges'][:3] == ['余额支付', '支付宝支付', '微信开发中']
    assert all('积分' not in badge and '现金' not in badge for badge in summary['badges'])


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


def test_balance_payment_requires_admin_switch():
    config = SimpleNamespace(
        balance_purchase_enabled=False,
        balance_only_enabled=False,
        cash_only_enabled=False,
    )

    with pytest.raises(ConflictError, match='Balance payment is disabled'):
        OrderService._validate_payment_rules(
            ZoneType.SELF_OPERATED,
            Decimal('10.00'),
            [config],
            {AssetType.BALANCE: Decimal('10.00')},
            'BALANCE',
        )


def test_alipay_payment_requires_admin_switch():
    config = SimpleNamespace(alipay_purchase_enabled=False)

    with (
        patch('app.services.order_service.enabled_external_payment_channels', return_value=['ALIPAY']),
        pytest.raises(ConflictError, match='Alipay payment is disabled'),
    ):
        OrderService._validate_payment_rules(
            ZoneType.SELF_OPERATED,
            Decimal('10.00'),
            [config],
            {},
            'ALIPAY',
        )
