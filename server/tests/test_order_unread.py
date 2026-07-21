from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.api.v1.mobile_serializers import _payment_combo
from app.models.enums import OrderStatus, PayStatus
from app.services.order_service import ORDER_STATUS_BUCKETS, OrderService


def make_order(status: OrderStatus, updated_at: datetime):
    return SimpleNamespace(
        order_status=status,
        pay_status=PayStatus.UNPAID,
        payable_amount=0,
        updated_at=updated_at,
    )


def test_unread_counts_only_include_orders_newer_than_status_view():
    viewed_at = datetime(2026, 7, 21, 10, 0)
    orders = [
        make_order(OrderStatus.PENDING_PAYMENT, viewed_at - timedelta(minutes=1)),
        make_order(OrderStatus.PENDING_PAYMENT, viewed_at + timedelta(minutes=1)),
        make_order(OrderStatus.REFUND, viewed_at + timedelta(minutes=2)),
    ]
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        SimpleNamespace(status_key='pending_payment', viewed_at=viewed_at),
        SimpleNamespace(status_key='refund', viewed_at=viewed_at),
    ]

    with patch.object(OrderService, 'list_orders', return_value=orders):
        counts = OrderService.order_unread_counts(db, user_id=7)

    assert counts == {
        'pending_payment': 1,
        'pending_ship': 0,
        'shipped': 0,
        'completed': 0,
        'refund': 1,
    }


def test_marking_all_statuses_viewed_creates_each_marker():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    with patch.object(OrderService, 'order_unread_counts', return_value=dict.fromkeys(ORDER_STATUS_BUCKETS, 0)):
        counts = OrderService.mark_order_status_viewed(db, user_id=8, status_key='all')

    assert db.add.call_count == len(ORDER_STATUS_BUCKETS)
    assert {call.args[0].status_key for call in db.add.call_args_list} == set(ORDER_STATUS_BUCKETS)
    assert all(call.args[0].user_id == 8 for call in db.add.call_args_list)
    assert counts == dict.fromkeys(ORDER_STATUS_BUCKETS, 0)
    db.commit.assert_called_once()


def test_canceled_and_refunded_orders_do_not_claim_payment_completed():
    canceled = make_order(OrderStatus.REFUND, datetime.now())
    refunded = make_order(OrderStatus.REFUND, datetime.now())
    refunded.pay_status = PayStatus.REFUNDED

    assert _payment_combo(canceled) == '订单已取消'
    assert _payment_combo(refunded) == '已退款'
