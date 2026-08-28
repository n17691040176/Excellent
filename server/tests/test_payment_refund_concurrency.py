from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

import app.main  # noqa: F401 - initialize application modules in production order
import app.models  # noqa: F401 - register every table needed by Base.metadata
from app.core.exceptions import ConflictError
from app.core.payment_config import AlipayConfig, PaymentConfig, WechatPayConfig
from app.db.base import Base
from app.models.enums import (
    OrderStatus,
    OrderType,
    PaymentChannel,
    PaymentStatus,
    PayStatus,
    RefundStatus,
    ZoneType,
)
from app.models.order import Order
from app.models.payment import PaymentRefund, PaymentTransaction
from app.services import payment_service as payment_module
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


@compiles(BigInteger, 'sqlite')
def _compile_big_integer_as_integer(_element, _compiler, **_kwargs):
    return 'INTEGER'


def _order(**overrides):
    values = {
        'id': 12,
        'order_no': 'ORDER-12',
        'user_id': 3,
        'order_type': OrderType.SELF_OPERATED_ORDER,
        'zone_type': ZoneType.SELF_OPERATED,
        'discount_amount': Decimal('0.00'),
        'total_amount': Decimal('9.90'),
        'payable_amount': Decimal('9.90'),
        'paid_amount': Decimal('0.00'),
        'pay_status': PayStatus.UNPAID,
        'order_status': OrderStatus.PENDING_PAYMENT,
        'legacy_trade_no': None,
        'confirmed_at': None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _transaction(**overrides):
    values = {
        'id': 7,
        'order_id': 12,
        'order_no': 'ORDER-12',
        'channel': PaymentChannel.WECHAT,
        'status': PaymentStatus.PENDING,
        'currency': 'CNY',
        'amount': Decimal('9.90'),
        'out_trade_no': 'PAYWE0012ABCDEF',
        'provider_trade_no': None,
        'notify_payload': None,
        'paid_at': None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _mock_payment_config() -> PaymentConfig:
    return PaymentConfig(
        mock_external_payment=True,
        wechat=WechatPayConfig(enabled=True),
        alipay=AlipayConfig(enabled=False),
    )


def test_prepare_external_payment_rechecks_locked_order_and_rejects_refund():
    caller_order = _order()
    locked_order = _order()
    transaction_query = MagicMock()
    transaction_query.filter.return_value.order_by.return_value.first.return_value = None
    order_query = MagicMock()
    order_query.filter.return_value.with_for_update.return_value.first.return_value = locked_order
    db = MagicMock()

    def query(model):
        if model is PaymentTransaction:
            return transaction_query
        if model is Order:
            return order_query
        raise AssertionError(f'unexpected model query: {model}')

    def refresh(instance, **_kwargs):
        if instance is locked_order:
            # Simulate a concurrent refund after the caller loaded the order,
            # but before this request acquired its row lock.
            locked_order.order_status = OrderStatus.REFUND

    db.query.side_effect = query
    db.refresh.side_effect = refresh

    with (
        patch.object(payment_module, 'payment_config', _mock_payment_config()),
        patch.object(PaymentService, '_ensure_transaction') as ensure_transaction,
        pytest.raises(ConflictError, match='Refunded order cannot be paid'),
    ):
        PaymentService.prepare_external_payment(db, caller_order, PaymentChannel.WECHAT.value)

    ensure_transaction.assert_not_called()
    db.commit.assert_not_called()
    assert caller_order.order_status == OrderStatus.PENDING_PAYMENT
    assert locked_order.order_status == OrderStatus.REFUND
    db.refresh.assert_called_once_with(locked_order, with_for_update=True)


def test_confirm_paid_order_locks_and_refreshes_transaction_before_order():
    caller_transaction = _transaction(amount=Decimal('0.01'), out_trade_no='STALE-CALLER-TRANSACTION')
    locked_transaction = _transaction()
    order = _order()
    transaction_query = MagicMock()
    transaction_query.filter.return_value.with_for_update.return_value.first.return_value = locked_transaction
    order_query = MagicMock()
    order_query.filter.return_value.with_for_update.return_value.first.return_value = order
    events = []
    db = MagicMock()

    def query(model):
        events.append(('query', model))
        if model is PaymentTransaction:
            return transaction_query
        if model is Order:
            return order_query
        raise AssertionError(f'unexpected model query: {model}')

    def refresh(instance, **kwargs):
        events.append(('refresh', instance, kwargs))

    db.query.side_effect = query
    db.refresh.side_effect = refresh

    with patch.object(OrderService, '_mark_paid', return_value=order) as mark_paid:
        result = PaymentService.confirm_paid_order(
            db,
            caller_transaction,
            notify_payload={'source': 'test'},
            provider_trade_no='WX-TRADE-12',
        )

    assert result is order
    assert events[0] == ('query', PaymentTransaction)
    assert events[1][0] == 'refresh'
    assert events[1][1] is locked_transaction
    assert events[1][2] == {'with_for_update': True}
    assert events[2] == ('query', Order)
    assert events[3][0] == 'refresh'
    assert events[3][1] is order
    assert events[3][2] == {'with_for_update': True}
    transaction_query.filter.return_value.with_for_update.assert_called_once()
    order_query.filter.return_value.with_for_update.assert_called_once()
    mark_paid.assert_called_once_with(db, order, external_paid_amount=Decimal('9.90'))


def test_cancellation_commits_before_conditional_pending_transaction_cleanup():
    order = _order()
    db = MagicMock()
    cleanup_query = db.query.return_value
    events = []

    db.commit.side_effect = lambda: events.append('commit')

    def conditional_update(values, **kwargs):
        events.append(('conditional-update', values, kwargs))

    cleanup_query.filter.return_value.update.side_effect = conditional_update

    with (
        patch.object(OrderService, '_lock_order_for_transition', return_value=order),
        patch.object(OrderService, 'order_requires_shipping', return_value=True),
        patch.object(OrderService, '_refund_order_deductions'),
        patch.object(OrderService, '_restore_order_inventory'),
    ):
        result = OrderService._cancel_order_instance(db, order, refunded=False)

    assert result is order
    assert order.order_status == OrderStatus.REFUND
    assert order.pay_status == PayStatus.UNPAID
    assert [event if isinstance(event, str) else event[0] for event in events] == [
        'commit',
        'conditional-update',
        'commit',
    ]
    update_values = events[1][1]
    assert update_values[PaymentTransaction.status] == PaymentStatus.CLOSED
    assert events[1][2] == {'synchronize_session': False}

    criteria = cleanup_query.filter.call_args.args
    assert len(criteria) == 2
    assert criteria[0].left.table is PaymentTransaction.__table__
    assert criteria[0].left.key == 'order_id'
    assert criteria[0].right.value == order.id
    assert criteria[1].left.table is PaymentTransaction.__table__
    assert criteria[1].left.key == 'status'
    assert criteria[1].right.value == PaymentStatus.PENDING


@pytest.fixture
def refund_guard_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _add_successful_refund(
    db: Session,
    *,
    order_id: int,
    transaction_status: PaymentStatus,
    failed_reason: str | None = None,
) -> None:
    transaction = PaymentTransaction(
        order_id=order_id,
        order_no=f'ORDER-{order_id}',
        channel=PaymentChannel.WECHAT,
        status=transaction_status,
        currency='CNY',
        amount=Decimal('9.90'),
        out_trade_no=f'PAY-{order_id}',
        provider_trade_no=f'WX-TRADE-{order_id}',
        failed_reason=failed_reason,
    )
    db.add(transaction)
    db.flush()
    db.add(
        PaymentRefund(
            order_id=order_id,
            payment_transaction_id=transaction.id,
            order_no=transaction.order_no,
            channel=PaymentChannel.WECHAT,
            status=RefundStatus.SUCCESS,
            currency='CNY',
            original_amount=Decimal('9.90'),
            refund_amount=Decimal('9.90'),
            out_refund_no=f'RF-{order_id}',
        )
    )
    db.commit()


def test_fulfillment_guard_blocks_primary_success_refund_but_allows_late_duplicate(refund_guard_db: Session):
    _add_successful_refund(
        refund_guard_db,
        order_id=101,
        transaction_status=PaymentStatus.PAID,
    )
    _add_successful_refund(
        refund_guard_db,
        order_id=102,
        transaction_status=PaymentStatus.FAILED,
        failed_reason='Provider payment succeeded after order was already paid; provider refund required',
    )

    with pytest.raises(ConflictError, match='Order refund is processing'):
        OrderService._ensure_no_active_external_refund(refund_guard_db, 101)

    OrderService._ensure_no_active_external_refund(refund_guard_db, 102)
