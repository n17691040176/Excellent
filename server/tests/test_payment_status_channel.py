from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1 import orders as orders_module
from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import PaymentChannel, PaymentStatus, PayStatus
from app.schemas.product import OrderPaymentStatusRequest


def _order():
    return SimpleNamespace(id=42, pay_status=PayStatus.UNPAID)


def _transaction(channel, out_trade_no='PAY-42'):
    return SimpleNamespace(
        channel=channel,
        status=PaymentStatus.PENDING,
        out_trade_no=out_trade_no,
    )


def _result(order, transaction, provider_status='NOTPAY'):
    return {
        'order': order,
        'transaction': transaction,
        'provider_status': provider_status,
    }


def test_status_sync_uses_channel_recorded_by_exact_trade_number():
    order = _order()
    transaction = _transaction(PaymentChannel.WECHAT)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = transaction

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order),
        patch.object(orders_module.PaymentService, 'reconcile_wechat_payment', return_value=_result(order, transaction)) as reconcile_wechat,
        patch.object(orders_module.PaymentService, 'reconcile_alipay_payment') as reconcile_alipay,
        patch.object(orders_module, 'serialize_order', return_value={'id': order.id}),
    ):
        response = orders_module.sync_order_payment_status(
            order.id,
            OrderPaymentStatusRequest(out_trade_no=transaction.out_trade_no),
            db,
            SimpleNamespace(id=7),
        )

    reconcile_wechat.assert_called_once_with(db, order, transaction.out_trade_no)
    reconcile_alipay.assert_not_called()
    assert response['data']['provider_status'] == 'NOTPAY'


def test_status_sync_rejects_unknown_trade_number_without_provider_fallback():
    order = _order()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order),
        patch.object(orders_module.PaymentService, 'reconcile_wechat_payment') as reconcile_wechat,
        patch.object(orders_module.PaymentService, 'reconcile_alipay_payment') as reconcile_alipay,
        pytest.raises(NotFoundError, match='transaction not found'),
    ):
        orders_module.sync_order_payment_status(
            order.id,
            OrderPaymentStatusRequest(out_trade_no='UNKNOWN-TRADE-NO'),
            db,
            SimpleNamespace(id=7),
        )

    reconcile_wechat.assert_not_called()
    reconcile_alipay.assert_not_called()


def test_status_sync_infers_latest_active_channel_when_trade_number_is_omitted():
    order = _order()
    transaction = _transaction(PaymentChannel.ALIPAY)
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.order_by.return_value.first.return_value = transaction

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order),
        patch.object(orders_module.PaymentService, 'reconcile_alipay_payment', return_value=_result(order, transaction, 'WAIT_BUYER_PAY')) as reconcile_alipay,
        patch.object(orders_module.PaymentService, 'reconcile_wechat_payment') as reconcile_wechat,
        patch.object(orders_module, 'serialize_order', return_value={'id': order.id}),
    ):
        response = orders_module.sync_order_payment_status(
            order.id,
            OrderPaymentStatusRequest(),
            db,
            SimpleNamespace(id=7),
        )

    reconcile_alipay.assert_called_once_with(db, order, None)
    reconcile_wechat.assert_not_called()
    assert response['data']['provider_status'] == 'WAIT_BUYER_PAY'


def test_status_sync_rejects_return_parameters_for_a_wechat_transaction():
    order = _order()
    transaction = _transaction(PaymentChannel.WECHAT)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = transaction

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order),
        pytest.raises(ConflictError, match='Payment channel mismatch'),
    ):
        orders_module.sync_order_payment_status(
            order.id,
            OrderPaymentStatusRequest(
                out_trade_no=transaction.out_trade_no,
                return_params={'out_trade_no': transaction.out_trade_no, 'sign': 'signed'},
            ),
            db,
            SimpleNamespace(id=7),
        )
