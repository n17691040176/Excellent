from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app.main  # noqa: F401 - initialize application modules in production order
from app.core.payment_config import AlipayConfig, PaymentConfig, WechatPayConfig
from app.models.enums import PaymentChannel, PaymentStatus, RefundStatus
from app.services import payment_service as payment_module
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService


def _payment_config(*, mock: bool = False, enabled: bool = True) -> PaymentConfig:
    return PaymentConfig(
        mock_external_payment=mock,
        wechat=WechatPayConfig(
            enabled=enabled,
            app_id='wx-test',
            mchid='mch-test',
        ),
        alipay=AlipayConfig(enabled=False),
    )


def _refund(status: RefundStatus) -> SimpleNamespace:
    return SimpleNamespace(
        id=73,
        order_id=42,
        payment_transaction_id=91,
        channel=PaymentChannel.WECHAT,
        status=status,
    )


def _transaction() -> SimpleNamespace:
    return SimpleNamespace(
        id=91,
        order_id=42,
        channel=PaymentChannel.WECHAT,
        status=PaymentStatus.PAID,
        amount=Decimal('9.90'),
    )


def _order() -> SimpleNamespace:
    return SimpleNamespace(id=42)


def _due_refund_db(refund, tx, order) -> MagicMock:
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        (refund.id,)
    ]
    db.get.side_effect = [refund, tx, order]
    return db


def test_due_reconciliation_resubmits_pending_refund_with_its_existing_number():
    refund = _refund(RefundStatus.PENDING)
    tx = _transaction()
    order = _order()
    db = _due_refund_db(refund, tx, order)
    completed_refund = _refund(RefundStatus.SUCCESS)

    with (
        patch.object(payment_module, 'payment_config', _payment_config()),
        patch.object(PaymentService, 'request_wechat_refund', return_value=completed_refund) as request_refund,
        patch.object(OrderService, 'finalize_external_refund') as finalize,
    ):
        result = PaymentService.reconcile_due_wechat_refunds(db)

    assert result == 1
    request_refund.assert_called_once_with(db, order, tx)
    finalize.assert_called_once_with(db, completed_refund, tx)


def test_due_reconciliation_queries_processing_refund_and_finalizes_success():
    refund = _refund(RefundStatus.PROCESSING)
    tx = _transaction()
    order = _order()
    db = _due_refund_db(refund, tx, order)
    completed_refund = _refund(RefundStatus.SUCCESS)

    with (
        patch.object(payment_module, 'payment_config', _payment_config()),
        patch.object(PaymentService, 'sync_wechat_refund', return_value=completed_refund) as sync_refund,
        patch.object(OrderService, 'finalize_external_refund') as finalize,
    ):
        result = PaymentService.reconcile_due_wechat_refunds(db)

    assert result == 1
    sync_refund.assert_called_once_with(db, refund, tx)
    finalize.assert_called_once_with(db, completed_refund, tx)


def test_due_reconciliation_is_inactive_for_mock_or_disabled_wechat():
    db = MagicMock()

    with patch.object(payment_module, 'payment_config', _payment_config(mock=True)):
        assert PaymentService.reconcile_due_wechat_refunds(db) == 0

    with patch.object(payment_module, 'payment_config', _payment_config(enabled=False)):
        assert PaymentService.reconcile_due_wechat_refunds(db) == 0

    db.query.assert_not_called()
