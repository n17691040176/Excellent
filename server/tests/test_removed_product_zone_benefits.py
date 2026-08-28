import csv
import io
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

import app.main  # noqa: F401 - initialize application modules in production order
from app.core.exceptions import ConflictError
from app.models.enums import OrderStatus, OrderType, PayStatus, ProductStatus, ZoneType
from app.schemas.product import ProductZoneConfigUpdateRequest
from app.services.catalog_service import ProductService
from app.services.order_service import OrderService

REMOVED_ZONE_FIELDS = {
    'package_required',
    'package_id',
    'repurchase_discount_rate',
    'voucher_deduct_min_rate',
    'voucher_deduct_max_rate',
    'ai_coupon_reward_rate',
    'ai_coupon_max_deduct_rate',
}


@pytest.mark.parametrize('field', sorted(REMOVED_ZONE_FIELDS))
def test_product_zone_config_rejects_removed_fields(field: str):
    with pytest.raises(ValidationError, match=field):
        ProductZoneConfigUpdateRequest.model_validate({field: 1})


def test_product_zone_snapshot_ignores_removed_database_columns():
    defaults = ProductService.zone_config_defaults(ZoneType.SELF_OPERATED)
    config = SimpleNamespace(
        **defaults,
        package_required=True,
        package_id=2001,
        repurchase_discount_rate=60,
        voucher_deduct_min_rate=50,
        voucher_deduct_max_rate=70,
        ai_coupon_reward_rate=20,
        ai_coupon_max_deduct_rate=20,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = config
    product = SimpleNamespace(id=1, zone_type=ZoneType.SELF_OPERATED)

    snapshot = ProductService._zone_config_snapshot(db, product)

    assert REMOVED_ZONE_FIELDS.isdisjoint(snapshot)
    assert REMOVED_ZONE_FIELDS.isdisjoint(defaults)


def test_product_import_template_omits_removed_zone_columns():
    rows = list(csv.reader(io.StringIO(ProductService.build_import_template_csv().decode('utf-8-sig'))))

    assert all(len(row) == len(rows[0]) for row in rows)
    assert {'是否需套餐资格', '套餐ID', '复购折扣率', '兑换券最低抵扣比例'}.isdisjoint(rows[0])
    assert {'兑换券最高抵扣比例', '购物返AI券比例', 'AI券最大抵扣比例'}.isdisjoint(rows[0])
    assert ProductService._zone_config_payload_from_import_row(
        ZoneType.SELF_OPERATED,
        {'是否需套餐资格': '1', '购物返AI券比例': '20'},
    ) is None


def test_legacy_package_qualification_no_longer_blocks_repurchase_order():
    product = SimpleNamespace(
        id=1,
        zone_type=ZoneType.REPURCHASE,
        status=ProductStatus.ON_SHELF,
        stock=10,
        sold_count=0,
        sale_price=Decimal('100.00'),
        product_name='复购商品',
        requires_shipping=False,
    )
    legacy_config = SimpleNamespace(package_required=True, package_id=2001)
    current_user = SimpleNamespace(id=10, team_id=1)
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = product
    payment_plan = {
        'total_amount': Decimal('100.00'),
        'discount_amount': Decimal('0.00'),
        'cash_due': Decimal('100.00'),
        'deductions_by_type': {},
        'address_id': None,
    }

    with (
        patch.object(OrderService, 'expire_pending_orders'),
        patch.object(ProductService, 'is_visible_to_user', return_value=True),
        patch.object(OrderService, '_get_zone_config', return_value=legacy_config),
        patch.object(OrderService, 'build_payment_plan', return_value=payment_plan),
    ):
        order = OrderService.create_order(
            db,
            current_user,
            {
                'order_type': OrderType.REPURCHASE_ORDER,
                'zone_type': ZoneType.REPURCHASE,
                'pay_channel': 'BALANCE',
                'items': [{'product_id': product.id, 'quantity': 1}],
                'asset_deductions': [],
            },
        )

    assert order.order_type == OrderType.REPURCHASE_ORDER
    assert product.stock == 9


def test_voucher_is_not_a_product_payment_channel():
    with pytest.raises(ConflictError, match='Unsupported pay channel'):
        OrderService._resolve_pay_channel('VOUCHER')


def test_paid_self_operated_order_does_not_reward_ai_coupon():
    db = MagicMock()
    db.get.return_value = None
    order = SimpleNamespace(
        id=1,
        user_id=10,
        order_no='OD0001',
        order_type=OrderType.SELF_OPERATED_ORDER,
        zone_type=ZoneType.SELF_OPERATED,
        pay_status=PayStatus.UNPAID,
        order_status=OrderStatus.PENDING_PAYMENT,
        discount_amount=Decimal('0.00'),
        payable_amount=Decimal('100.00'),
        paid_amount=Decimal('0.00'),
        total_amount=Decimal('100.00'),
    )

    with (
        patch.object(OrderService, '_lock_order_for_transition', return_value=order),
        patch.object(OrderService, 'order_requires_shipping', return_value=False),
        patch('app.services.order_service.AssetService.add_amount') as add_asset,
        patch('app.services.order_service.CommissionService.settle_for_order'),
    ):
        OrderService._mark_paid(db, order, external_paid_amount=Decimal('100.00'))

    add_asset.assert_not_called()
