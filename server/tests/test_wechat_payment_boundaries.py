from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1 import mobile_serializers
from app.api.v1 import orders as orders_module
from app.api.v1.mobile_serializers import serialize_order
from app.core.exceptions import ConflictError, ForbiddenError
from app.core.payment_config import AlipayConfig, PaymentConfig, WechatPayConfig
from app.models.enums import (
    OrderStatus,
    OrderType,
    PaymentChannel,
    PaymentStatus,
    PayStatus,
    ZoneType,
)
from app.models.order import Order, OrderAssetDeduction, OrderItem
from app.models.payment import PaymentTransaction
from app.models.product import Product, ProductZoneConfig
from app.schemas.product import OrderPaymentStatusRequest
from app.services import payment_service as payment_module
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


def _wechat_transaction(**overrides):
    values = {
        'id': 7,
        'order_id': 12,
        'order_no': 'ORDER-12',
        'channel': PaymentChannel.WECHAT,
        'status': PaymentStatus.PENDING,
        'currency': 'CNY',
        'amount': Decimal('9.90'),
        'out_trade_no': 'PAYWE0012ABCDEF',
        'provider_app_id': None,
        'provider_trade_no': None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _transaction(channel, out_trade_no='PAY-12'):
    """Build the lightweight transaction shape used by status-sync tests."""
    return _wechat_transaction(channel=channel, out_trade_no=out_trade_no)


def _result(order, transaction, provider_status='NOTPAY'):
    return {
        'order': order,
        'transaction': transaction,
        'provider_status': provider_status,
    }


def _payment_db(transaction):
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = transaction
    return db


def _notify_db(transaction, order):
    """Return a query double that distinguishes transaction and order locks."""
    db = MagicMock()
    transaction_query = MagicMock()
    transaction_query.filter.return_value.with_for_update.return_value.first.return_value = transaction
    order_query = MagicMock()
    order_query.filter.return_value.with_for_update.return_value.first.return_value = order

    def query(model):
        if model is PaymentTransaction:
            return transaction_query
        if model is Order:
            return order_query
        return MagicMock()

    db.query.side_effect = query
    return db


def _status_result(order, transaction, provider_status='NOTPAY'):
    return {
        'order': order,
        'transaction': transaction,
        'provider_status': provider_status,
    }


def _mock_payment_config(**wechat_overrides):
    return PaymentConfig(
        mock_external_payment=True,
        wechat=WechatPayConfig(enabled=True, **wechat_overrides),
        alipay=AlipayConfig(enabled=False),
    )


def test_explicit_mock_wechat_flat_notification_remains_compatible():
    transaction = _wechat_transaction()
    paid_order = SimpleNamespace(id=transaction.order_id, order_no=transaction.order_no)
    payload = {
        'mocked': True,
        'out_trade_no': transaction.out_trade_no,
        'trade_state': 'SUCCESS',
        'transaction_id': 'MOCK-WECHAT-TRADE-1',
        'amount': {'total': 990, 'currency': 'CNY'},
    }

    with (
        patch.object(payment_module, 'payment_config', _mock_payment_config()),
        patch.object(PaymentService, 'confirm_paid_order', return_value=paid_order) as confirm_paid,
    ):
        result = PaymentService.handle_notify(
            _payment_db(transaction),
            PaymentChannel.WECHAT.value,
            payload,
        )

    assert result['provider_status'] == 'SUCCESS'
    assert result['provider_trade_no'] == 'MOCK-WECHAT-TRADE-1'
    confirm_paid.assert_called_once()


@pytest.mark.parametrize('mocked_value', [None, 'true', 1])
def test_unmarked_flat_wechat_notification_is_rejected_in_mock_mode(mocked_value):
    transaction = _wechat_transaction()
    payload = {
        'out_trade_no': transaction.out_trade_no,
        'trade_state': 'SUCCESS',
        'transaction_id': 'MOCK-WECHAT-TRADE-1',
    }
    if mocked_value is not None:
        payload['mocked'] = mocked_value

    with (
        patch.object(payment_module, 'payment_config', _mock_payment_config()),
        pytest.raises(ConflictError, match='encrypted resource'),
    ):
        PaymentService.handle_notify(
            _payment_db(transaction),
            PaymentChannel.WECHAT.value,
            payload,
        )


def test_mock_marker_does_not_bypass_production_signature_verification():
    transaction = _wechat_transaction()
    payload = {
        'mocked': True,
        'out_trade_no': transaction.out_trade_no,
        'trade_state': 'SUCCESS',
        'transaction_id': 'MOCK-WECHAT-TRADE-1',
    }
    production_config = PaymentConfig(
        mock_external_payment=False,
        wechat=WechatPayConfig(
            enabled=True,
            app_id='wx-production',
            mchid='merchant-production',
        ),
        alipay=AlipayConfig(enabled=False),
    )

    with (
        patch.object(payment_module, 'payment_config', production_config),
        pytest.raises(ForbiddenError, match='signature headers are incomplete'),
    ):
        PaymentService.handle_notify(
            _payment_db(transaction),
            PaymentChannel.WECHAT.value,
            payload,
            raw_body=b'{}',
            headers={},
        )


def test_explicit_mock_notification_rejects_conflicting_amount():
    transaction = _wechat_transaction()
    payload = {
        'mocked': True,
        'out_trade_no': transaction.out_trade_no,
        'trade_state': 'SUCCESS',
        'transaction_id': 'MOCK-WECHAT-TRADE-1',
        'amount': {'total': 991, 'currency': 'CNY'},
    }

    with (
        patch.object(payment_module, 'payment_config', _mock_payment_config()),
        patch.object(PaymentService, 'confirm_paid_order') as confirm_paid,
        pytest.raises(ConflictError, match='amount mismatch'),
    ):
        PaymentService.handle_notify(
            _payment_db(transaction),
            PaymentChannel.WECHAT.value,
            payload,
        )
    confirm_paid.assert_not_called()


def test_late_wechat_success_for_canceled_order_is_acknowledged_for_refund():
    transaction = _wechat_transaction(status=PaymentStatus.CLOSED, out_trade_no='PAY-WX-LATE')
    order = _order(order_status=OrderStatus.REFUND, pay_status=PayStatus.UNPAID)
    payload = {
        'mocked': True,
        'out_trade_no': transaction.out_trade_no,
        'trade_state': 'SUCCESS',
        'transaction_id': 'WX-LATE-TRADE',
    }

    with (
        patch.object(payment_module, 'payment_config', _mock_payment_config()),
        patch.object(PaymentService, '_auto_refund_late_wechat_payment') as auto_refund,
    ):
        result = PaymentService.handle_notify(
            _notify_db(transaction, order),
            PaymentChannel.WECHAT.value,
            payload,
        )

    assert result['provider_status'] == 'ORDER_CANCELED_PROVIDER_PAYMENT'
    assert transaction.status == PaymentStatus.FAILED
    assert transaction.provider_trade_no == 'WX-LATE-TRADE'
    assert 'provider refund required' in transaction.failed_reason
    auto_refund.assert_called_once()
    assert auto_refund.call_args.args[1:] == (order, transaction)


def test_late_success_does_not_replace_recorded_provider_trade_number():
    transaction = _wechat_transaction(
        status=PaymentStatus.CLOSED,
        out_trade_no='PAY-WX-LATE-CONFLICT',
        provider_trade_no='WX-ORIGINAL-TRADE',
    )
    order = _order(order_status=OrderStatus.REFUND, pay_status=PayStatus.UNPAID)
    db = _notify_db(transaction, order)

    with pytest.raises(ConflictError, match='transaction id conflicts'):
        PaymentService._record_provider_success_for_closed_order(
            db,
            transaction,
            {'source': 'test'},
            'WX-DIFFERENT-TRADE',
        )

    assert transaction.status == PaymentStatus.CLOSED
    assert transaction.provider_trade_no == 'WX-ORIGINAL-TRADE'
    db.commit.assert_not_called()


def test_late_alipay_success_for_refunded_order_is_acknowledged_for_refund():
    transaction = _transaction(PaymentChannel.ALIPAY, 'PAY-ALI-LATE')
    transaction.status = PaymentStatus.CLOSED
    order = _order(order_status=OrderStatus.REFUND, pay_status=PayStatus.REFUNDED)
    payload = {
        'out_trade_no': transaction.out_trade_no,
        'trade_status': 'TRADE_SUCCESS',
        'trade_no': 'ALI-LATE-TRADE',
    }

    with patch.object(payment_module, 'payment_config', _mock_payment_config()):
        result = PaymentService.handle_notify(
            _notify_db(transaction, order),
            PaymentChannel.ALIPAY.value,
            payload,
        )

    assert result['provider_status'] == 'ORDER_CANCELED_PROVIDER_PAYMENT'
    assert transaction.status == PaymentStatus.FAILED
    assert transaction.provider_trade_no == 'ALI-LATE-TRADE'
    assert 'provider refund required' in transaction.failed_reason


class _RowsQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class _OrderSerializerDb:
    def __init__(self, item, config, transaction):
        self.item = item
        self.config = config
        self.transactions = transaction if isinstance(transaction, list) else [transaction]

    def query(self, model):
        if model is OrderItem:
            return _RowsQuery([self.item])
        if model is OrderAssetDeduction:
            return _RowsQuery([])
        if model is ProductZoneConfig:
            return _RowsQuery([self.config])
        if model is PaymentTransaction:
            return _RowsQuery(self.transactions)
        if model is Product.id:
            return _RowsQuery([])
        raise AssertionError(f'unexpected model query: {model}')

    def get(self, _model, _identifier):
        return None


def _order(**overrides):
    values = {
        'id': 12,
        'order_no': 'ORDER-12',
        'user_id': 3,
        'team_id': None,
        'order_type': OrderType.SELF_OPERATED_ORDER,
        'zone_type': ZoneType.SELF_OPERATED,
        'source_ref_id': None,
        'total_amount': Decimal('9.90'),
        'discount_amount': Decimal('0.00'),
        'payable_amount': Decimal('9.90'),
        'paid_amount': Decimal('0.00'),
        'pay_status': PayStatus.UNPAID,
        'order_status': OrderStatus.PENDING_PAYMENT,
        'created_at': None,
        'updated_at': None,
        'paid_at': None,
        'confirmed_at': None,
        'legacy_address_id': None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _order_item():
    return SimpleNamespace(
        id=1,
        order_id=12,
        product_id=22,
        sku_id=None,
        product_name='Test product',
        sku_name=None,
        unit_price=Decimal('9.90'),
        quantity=1,
        total_amount=Decimal('9.90'),
        created_at=None,
    )


def test_pending_transaction_falls_back_when_its_channel_is_no_longer_available():
    transaction = _wechat_transaction(status=PaymentStatus.PENDING)
    config = SimpleNamespace(
        wechat_purchase_enabled=False,
        alipay_purchase_enabled=True,
    )
    db = _OrderSerializerDb(_order_item(), config, transaction)

    with patch.object(
        mobile_serializers,
        'enabled_external_payment_channels',
        return_value=['WECHAT', 'ALIPAY'],
    ):
        serialized = serialize_order(db, _order(), include_detail=True)

    assert serialized['pay_channel_options'] == ['BALANCE', 'ALIPAY', 'WECHAT']
    assert serialized['pay_channel'] == 'WECHAT'
    assert serialized['default_pay_channel'] == 'WECHAT'
    assert serialized['payment_provider'] == 'wxpay'
    assert serialized['order']['pay_channel'] == 'WECHAT'
    assert serialized['order']['payment_provider'] == 'wxpay'


def test_pending_transaction_falls_back_when_global_provider_is_closed():
    transaction = _wechat_transaction(status=PaymentStatus.PENDING)
    config = SimpleNamespace(
        wechat_purchase_enabled=True,
        alipay_purchase_enabled=True,
    )
    db = _OrderSerializerDb(_order_item(), config, transaction)

    with patch.object(
        mobile_serializers,
        'enabled_external_payment_channels',
        return_value=['ALIPAY'],
    ):
        serialized = serialize_order(db, _order(), include_detail=True)

    assert serialized['pay_channel_options'] == ['BALANCE', 'ALIPAY']
    assert serialized['pay_channel'] == 'ALIPAY'
    assert serialized['default_pay_channel'] == 'ALIPAY'
    assert serialized['payment_provider'] == 'alipay'


def test_paid_transaction_keeps_its_historical_provider_when_switch_is_closed():
    transaction = _wechat_transaction(status=PaymentStatus.PAID)
    config = SimpleNamespace(
        wechat_purchase_enabled=False,
        alipay_purchase_enabled=True,
    )
    order = _order(
        pay_status=PayStatus.PAID,
        order_status=OrderStatus.COMPLETED,
        paid_amount=Decimal('9.90'),
    )
    db = _OrderSerializerDb(_order_item(), config, transaction)

    with patch.object(
        mobile_serializers,
        'enabled_external_payment_channels',
        return_value=['ALIPAY'],
    ):
        serialized = serialize_order(db, order, include_detail=True)

    assert serialized['pay_channel_options'] == ['BALANCE', 'ALIPAY']
    assert serialized['pay_channel'] == 'WECHAT'
    assert serialized['payment_provider'] == 'wxpay'
    assert serialized['order']['pay_channel'] == 'WECHAT'
    assert serialized['order']['payment_provider'] == 'wxpay'


def test_paid_transaction_wins_over_a_newer_pending_other_channel():
    pending_wechat = _wechat_transaction(id=9, status=PaymentStatus.PENDING)
    paid_alipay = SimpleNamespace(
        id=10,
        order_id=12,
        channel=PaymentChannel.ALIPAY,
        status=PaymentStatus.PAID,
        out_trade_no='PAYALI0012ABCDEF',
        provider_app_id=None,
        provider_trade_no='ALI-TRADE-1',
    )
    config = SimpleNamespace(
        wechat_purchase_enabled=True,
        alipay_purchase_enabled=True,
    )
    order = _order(
        pay_status=PayStatus.PAID,
        order_status=OrderStatus.COMPLETED,
        paid_amount=Decimal('9.90'),
    )
    db = _OrderSerializerDb(_order_item(), config, [pending_wechat, paid_alipay])

    with patch.object(
        mobile_serializers,
        'enabled_external_payment_channels',
        return_value=['WECHAT', 'ALIPAY'],
    ):
        serialized = serialize_order(db, order, include_detail=True)

    assert serialized['pay_channel'] == 'ALIPAY'
    assert serialized['payment_provider'] == 'alipay'
    assert serialized['order']['pay_channel'] == 'ALIPAY'


def test_status_sync_without_trade_number_prefers_paid_transaction():
    order = _order(pay_status=PayStatus.PAID)
    paid_transaction = _wechat_transaction(channel=PaymentChannel.ALIPAY, out_trade_no='PAY-PAID')
    paid_transaction.status = PaymentStatus.PAID
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = paid_transaction

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order),
        patch.object(
            orders_module.PaymentService,
            'reconcile_alipay_payment',
            return_value=_status_result(order, paid_transaction, 'TRADE_SUCCESS'),
        ) as reconcile_alipay,
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
    assert response['data']['payment_status'] == 'PAID'


def test_status_sync_reports_order_paid_for_stale_pending_transaction():
    order = _order(pay_status=PayStatus.PAID)
    pending_transaction = _wechat_transaction(out_trade_no='PAY-WAIT')
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = pending_transaction

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order),
        patch.object(
            orders_module.PaymentService,
            'reconcile_wechat_payment',
            return_value=_status_result(order, pending_transaction, 'ORDER_PAID_OTHER_TRANSACTION'),
        ) as reconcile_wechat,
        patch.object(orders_module, 'serialize_order', return_value={'id': order.id}),
    ):
        response = orders_module.sync_order_payment_status(
            order.id,
            OrderPaymentStatusRequest(out_trade_no=pending_transaction.out_trade_no),
            db,
            SimpleNamespace(id=7),
        )

    reconcile_wechat.assert_called_once_with(db, order, pending_transaction.out_trade_no)
    assert response['data']['payment_status'] == 'PAID'
    assert response['data']['provider_status'] == 'ORDER_PAID_OTHER_TRANSACTION'


def test_wechat_query_refreshes_transaction_before_settlement():
    order = _order()
    transaction = _wechat_transaction(status=PaymentStatus.PENDING)
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = transaction

    def refresh(instance, **_kwargs):
        if instance is transaction:
            instance.status = PaymentStatus.PAID
            instance.provider_trade_no = 'WX-ALREADY-PAID'
        elif instance is order:
            instance.pay_status = PayStatus.PAID
            instance.order_status = OrderStatus.PENDING_SHIP

    db.refresh.side_effect = refresh
    response = {
        'out_trade_no': transaction.out_trade_no,
        'transaction_id': 'WX-ALREADY-PAID',
    }

    with (
        patch.object(
            payment_module,
            'payment_config',
            PaymentConfig(
                mock_external_payment=False,
                wechat=WechatPayConfig(enabled=True),
                alipay=AlipayConfig(enabled=False),
            ),
        ),
        patch.object(PaymentService, '_wechat_query_order', return_value=response),
        patch.object(PaymentService, '_validate_wechat_trade_response', return_value='SUCCESS'),
        patch.object(PaymentService, '_record_provider_success_for_closed_order') as record_closed,
        patch.object(PaymentService, 'confirm_paid_order') as confirm_paid,
    ):
        result = PaymentService.reconcile_wechat_payment(db, order, transaction.out_trade_no)

    assert result['provider_status'] == 'SUCCESS'
    assert result['transaction'] is transaction
    assert result['order'] is order
    assert order.pay_status == PayStatus.PAID
    record_closed.assert_not_called()
    confirm_paid.assert_not_called()
    db.refresh.assert_any_call(order, with_for_update=True)


def test_wechat_query_does_not_mark_paid_transaction_failed_on_stale_closed_state():
    order = _order()
    transaction = _wechat_transaction(status=PaymentStatus.PENDING)
    db = MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = transaction

    def refresh(instance, **_kwargs):
        if instance is transaction:
            instance.status = PaymentStatus.PAID
            instance.provider_trade_no = 'WX-ALREADY-PAID'
        elif instance is order:
            instance.pay_status = PayStatus.PAID
            instance.order_status = OrderStatus.PENDING_SHIP

    db.refresh.side_effect = refresh
    response = {
        'out_trade_no': transaction.out_trade_no,
        'transaction_id': 'WX-ALREADY-PAID',
    }

    with (
        patch.object(
            payment_module,
            'payment_config',
            PaymentConfig(
                mock_external_payment=False,
                wechat=WechatPayConfig(enabled=True),
                alipay=AlipayConfig(enabled=False),
            ),
        ),
        patch.object(PaymentService, '_wechat_query_order', return_value=response),
        patch.object(PaymentService, '_validate_wechat_trade_response', return_value='CLOSED'),
    ):
        result = PaymentService.reconcile_wechat_payment(db, order, transaction.out_trade_no)

    assert result['provider_status'] == 'CLOSED'
    assert transaction.status == PaymentStatus.PAID
    assert result['order'] is order
    assert order.pay_status == PayStatus.PAID
    db.commit.assert_not_called()
    db.refresh.assert_any_call(order, with_for_update=True)


def test_existing_pending_transaction_bypasses_later_product_switch_change():
    pending = _wechat_transaction(status=PaymentStatus.PENDING)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = pending
    order = _order()

    with patch('app.services.order_service.enabled_external_payment_channels', return_value=['WECHAT']):
        # Product-level switches are intentionally not queried after a live
        # transaction has been found; the global provider gate still applies.
        OrderService._validate_existing_order_external_channel(db, order, 'WECHAT')

    assert db.query.call_args.args[0] is PaymentTransaction


def test_prepare_payment_locks_transaction_before_order_when_reusing_pending_transaction():
    order = _order()
    pending = _wechat_transaction(status=PaymentStatus.PENDING)
    pending.request_payload = {}
    events = []

    db = MagicMock()
    order_query = MagicMock()
    order_query.filter.return_value.with_for_update.return_value.first.return_value = order
    transaction_query = MagicMock()
    transaction_query.filter.return_value.order_by.return_value.first.return_value = pending

    def query(model):
        events.append(('query', model))
        if model is Order:
            return order_query
        if model is PaymentTransaction:
            return transaction_query
        raise AssertionError(f'unexpected model query: {model}')

    db.query.side_effect = query

    def refresh(instance, **kwargs):
        events.append(('refresh', instance, kwargs))

    db.refresh.side_effect = refresh

    with patch.object(payment_module, 'payment_config', _mock_payment_config()):
        result = PaymentService.prepare_external_payment(
            db,
            order,
            PaymentChannel.WECHAT.value,
            request_payload={'payer_client_ip': '203.0.113.7'},
        )

    assert result['transaction'] is pending
    assert events[0] == ('query', PaymentTransaction)
    transaction_refresh_index = next(
        index
        for index, event in enumerate(events)
        if event == ('refresh', pending, {'with_for_update': True})
    )
    order_query_index = next(
        index
        for index, event in enumerate(events)
        if event == ('query', Order)
    )
    assert transaction_refresh_index < order_query_index
    order_query.filter.return_value.with_for_update.assert_called_once()
    transaction_query.filter.return_value.order_by.return_value.first.assert_called_once()
    db.refresh.assert_any_call(pending, with_for_update=True)
