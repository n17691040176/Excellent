from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

import app.main  # noqa: F401 - initialize application modules in production order
from app.core.exceptions import ConflictError
from app.models.enums import OrderStatus, OrderType, PayStatus, ZoneType
from app.services.order_service import OrderService


def build_order(**overrides):
    values = {
        'id': 100,
        'user_id': 1,
        'order_no': 'OD-TEST-100',
        'order_type': OrderType.HOT_SALE_ORDER,
        'zone_type': ZoneType.HOT_SALE,
        'discount_amount': Decimal('0.00'),
        'total_amount': Decimal('100.00'),
        'payable_amount': Decimal('100.00'),
        'paid_amount': Decimal('0.00'),
        'pay_status': PayStatus.UNPAID,
        'order_status': OrderStatus.PENDING_PAYMENT,
        'paid_at': None,
        'confirmed_at': None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class OrderLifecycleTest(TestCase):
    def test_physical_payment_enters_pending_ship(self):
        db = MagicMock()
        db.get.return_value = None
        order = build_order()

        with (
            patch.object(OrderService, '_lock_order_for_transition', return_value=order),
            patch.object(OrderService, 'order_requires_shipping', return_value=True),
        ):
            result = OrderService._mark_paid(db, order, external_paid_amount=Decimal('100.00'))

        self.assertIs(result, order)
        self.assertEqual(order.pay_status, PayStatus.PAID)
        self.assertEqual(order.order_status, OrderStatus.PENDING_SHIP)
        self.assertIsNone(order.confirmed_at)
        db.commit.assert_called_once()

    def test_non_shipping_payment_completes_and_settles(self):
        db = MagicMock()
        db.get.return_value = None
        order = build_order()

        with (
            patch.object(OrderService, '_lock_order_for_transition', return_value=order),
            patch.object(OrderService, 'order_requires_shipping', return_value=False),
            patch('app.services.order_service.CommissionService.settle_for_order') as settle,
        ):
            OrderService._mark_paid(db, order, external_paid_amount=Decimal('100.00'))

        self.assertEqual(order.order_status, OrderStatus.COMPLETED)
        self.assertEqual(order.confirmed_at, order.paid_at)
        settle.assert_called_once_with(db, order.id, commit=False)

    def test_pending_ship_order_cannot_be_confirmed(self):
        db = MagicMock()
        order = build_order(pay_status=PayStatus.PAID, order_status=OrderStatus.PENDING_SHIP)

        with self.assertRaisesRegex(ConflictError, 'Only shipped orders can be confirmed'):
            OrderService._confirm_order_instance(db, order)

    def test_shipping_requires_tracking_number(self):
        db = MagicMock()
        user = SimpleNamespace()
        order = build_order(pay_status=PayStatus.PAID, order_status=OrderStatus.PENDING_SHIP)

        with (
            patch.object(OrderService, 'get_order_for_admin', return_value=order),
            self.assertRaisesRegex(ConflictError, 'Tracking number is required'),
        ):
            OrderService.ship_order_for_admin(db, order.id, user, '  ')

    def test_physical_order_requires_address(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaisesRegex(ConflictError, 'Shipping address required'):
            OrderService._validate_address(db, user_id=1, address_id=None, requires_shipping=True)
