from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import app.main  # noqa: F401 - initialize application modules in production order
from app.core.exceptions import ConflictError
from app.core.payment_config import AlipayConfig, PaymentConfig, WechatPayConfig
from app.models.enums import OrderStatus, OrderType, PaymentChannel, PaymentStatus, PayStatus, RefundStatus
from app.services import payment_service as payment_module
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService, WechatApiError


def _order(**overrides):
    values = {
        'id': 42,
        'order_no': 'ORDER-42',
        'order_type': OrderType.SELF_OPERATED_ORDER,
        'order_status': OrderStatus.PENDING_SHIP,
        'pay_status': PayStatus.PAID,
        'payable_amount': Decimal('0.00'),
        'paid_amount': Decimal('9.90'),
        'confirmed_at': None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _transaction(**overrides):
    values = {
        'id': 91,
        'order_id': 42,
        'order_no': 'ORDER-42',
        'channel': PaymentChannel.WECHAT,
        'status': PaymentStatus.PAID,
        'currency': 'CNY',
        'amount': Decimal('9.90'),
        'out_trade_no': 'PAY-WECHAT-42',
        'provider_trade_no': 'WX-TRADE-42',
        'failed_reason': None,
        'refunded_amount': Decimal('0.00'),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _refund(**overrides):
    values = {
        'id': 73,
        'order_id': 42,
        'payment_transaction_id': 91,
        'order_no': 'ORDER-42',
        'channel': PaymentChannel.WECHAT,
        'status': RefundStatus.PENDING,
        'currency': 'CNY',
        'original_amount': Decimal('9.90'),
        'refund_amount': Decimal('9.90'),
        'out_refund_no': 'RF42ABC',
        'provider_refund_id': None,
        'provider_trade_no': None,
        'provider_status': None,
        'provider_notify_id': None,
        'reason': None,
        'request_payload': None,
        'response_payload': None,
        'notify_payload': None,
        'attempt_count': 0,
        'error_code': None,
        'error_message': None,
        'last_synced_at': None,
        'next_retry_at': None,
        'processed_at': None,
        'success_at': None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _payment_config(*, mock: bool) -> PaymentConfig:
    return PaymentConfig(
        mock_external_payment=mock,
        wechat=WechatPayConfig(
            enabled=True,
            app_id='wx-test' if not mock else '',
            mchid='mch-test' if not mock else '',
        ),
        alipay=AlipayConfig(enabled=False),
    )


def _refund_response(refund, tx, *, status='SUCCESS'):
    return {
        'refund_id': 'WX-REFUND-42',
        'out_refund_no': refund.out_refund_no,
        'out_trade_no': tx.out_trade_no,
        'transaction_id': tx.provider_trade_no,
        'status': status,
        'amount': {
            'total': 990,
            'refund': 990,
            'currency': 'CNY',
        },
    }


def test_mock_wechat_refund_creates_provider_style_success_without_network():
    db = MagicMock()
    order = _order()
    tx = _transaction(provider_trade_no=None)
    refund = _refund()

    with (
        patch.object(payment_module, 'payment_config', _payment_config(mock=True)),
        patch.object(PaymentService, '_lock_wechat_refund_transaction', return_value=(order, tx)),
        patch.object(PaymentService, '_wechat_refund_record', return_value=refund),
        patch.object(PaymentService, '_apply_wechat_refund_response', return_value=refund) as apply_response,
        patch.object(PaymentService, '_wechat_request_json_with_status') as request_provider,
    ):
        result = PaymentService.request_wechat_refund(
            db,
            order,
            tx,
            reason='Customer request',
            idempotency_key='refund-42',
            requested_by=7,
        )

    assert result is refund
    request_provider.assert_not_called()
    response = apply_response.call_args.args[3]
    assert apply_response.call_args.kwargs['source'] == 'mock'
    assert response['status'] == 'SUCCESS'
    assert response['out_refund_no'] == refund.out_refund_no
    assert response['amount'] == {'total': 990, 'refund': 990, 'payer_total': 990, 'payer_refund': 990, 'currency': 'CNY'}
    assert refund.attempt_count == 1
    assert refund.request_payload['out_refund_no'] == refund.out_refund_no


def test_real_wechat_refund_keeps_processing_result_for_later_sync():
    db = MagicMock()
    order = _order()
    tx = _transaction()
    refund = _refund()
    response = _refund_response(refund, tx, status='PROCESSING')

    with (
        patch.object(payment_module, 'payment_config', _payment_config(mock=False)),
        patch.object(PaymentService, '_lock_wechat_refund_transaction', return_value=(order, tx)),
        patch.object(PaymentService, '_wechat_refund_record', return_value=refund),
        patch.object(PaymentService, '_wechat_request_json_with_status', return_value=(202, response)) as request_provider,
        patch.object(PaymentService, '_apply_wechat_refund_response', return_value=refund) as apply_response,
    ):
        result = PaymentService.request_wechat_refund(db, order, tx)

    assert result is refund
    request_provider.assert_called_once()
    assert request_provider.call_args.args[0].endswith('/v3/refund/domestic/refunds')
    assert request_provider.call_args.kwargs['method'] == 'POST'
    assert apply_response.call_args.args[3] == response
    assert apply_response.call_args.kwargs['source'] == 'request'


@pytest.mark.parametrize(
    ('http_status', 'retryable'),
    [(400, False), (500, True), (None, True)],
)
def test_wechat_refund_request_distinguishes_terminal_and_retryable_provider_errors(http_status, retryable):
    db = MagicMock()
    order = _order()
    tx = _transaction()
    refund = _refund()
    error = WechatApiError('provider failed', http_status=http_status, retryable=retryable)

    with (
        patch.object(payment_module, 'payment_config', _payment_config(mock=False)),
        patch.object(PaymentService, '_lock_wechat_refund_transaction', return_value=(order, tx)),
        patch.object(PaymentService, '_wechat_refund_record', return_value=refund),
        patch.object(PaymentService, '_wechat_request_json_with_status', side_effect=error),
        patch.object(PaymentService, '_wechat_refund_error', return_value=refund) as save_error,
    ):
        result = PaymentService.request_wechat_refund(db, order, tx)

    assert result is refund
    assert save_error.call_args.kwargs['retryable'] is retryable
    assert save_error.call_args.kwargs['response_payload'] == {}


def test_wechat_refund_sync_reuses_existing_out_refund_number():
    db = MagicMock()
    order = _order()
    tx = _transaction()
    refund = _refund(status=RefundStatus.PROCESSING)
    response = _refund_response(refund, tx, status='PROCESSING')

    with (
        patch.object(payment_module, 'payment_config', _payment_config(mock=False)),
        patch.object(PaymentService, '_lock_wechat_refund_context', return_value=(order, tx, refund)),
        patch.object(PaymentService, '_wechat_refund_query', return_value=response) as query_provider,
        patch.object(PaymentService, '_apply_wechat_refund_response', return_value=refund) as apply_response,
    ):
        result = PaymentService.sync_wechat_refund(db, refund, tx)

    assert result is refund
    query_provider.assert_called_once_with(refund, _payment_config(mock=False).wechat)
    assert apply_response.call_args.args[3]['out_refund_no'] == 'RF42ABC'
    assert apply_response.call_args.kwargs['source'] == 'query'


def test_wechat_api_success_response_is_verified_before_json_is_trusted():
    config = WechatPayConfig(enabled=True, mchid='mch-test', merchant_serial_no='merchant-serial')
    response = MagicMock()
    response.status = 200
    response.headers = {'Wechatpay-Serial': 'platform-serial'}
    response.read.return_value = b'{"status":"PROCESSING"}'
    context = MagicMock()
    context.__enter__.return_value = response

    with (
        patch.object(PaymentService, '_wechat_authorization_header', return_value='authorization'),
        patch.object(payment_module.urlrequest, 'urlopen', return_value=context),
        patch.object(PaymentService, '_wechat_verify_platform_signature') as verify,
    ):
        status, payload = PaymentService._wechat_request_json_with_status(
            'https://api.mch.weixin.qq.com/v3/refund/domestic/refunds/RF42ABC',
            None,
            config,
            method='GET',
        )

    assert status == 200
    assert payload == {'status': 'PROCESSING'}
    verify.assert_called_once_with(
        b'{"status":"PROCESSING"}',
        response.headers,
        config,
        source='response',
    )


def test_real_refund_response_requires_bound_provider_transaction_id():
    refund = _refund()
    tx = _transaction()
    response = _refund_response(refund, tx)
    response['transaction_id'] = ''

    with (
        patch.object(payment_module, 'payment_config', _payment_config(mock=False)),
        pytest.raises(ConflictError, match='transaction_id is missing'),
    ):
        PaymentService._validate_wechat_refund_response(response, refund, tx, source='notify')


def test_duplicate_success_notification_retries_local_finalization():
    db = MagicMock()
    refund = _refund(status=RefundStatus.SUCCESS, provider_notify_id='EVENT-42')
    order = _order()
    tx = _transaction()
    db.query.return_value.filter.return_value.scalar.return_value = refund.id

    with (
        patch.object(payment_module, 'payment_config', _payment_config(mock=True)),
        patch.object(PaymentService, '_lock_wechat_refund_context', return_value=(order, tx, refund)),
        patch('app.services.order_service.OrderService.finalize_external_refund') as finalize,
    ):
        result = PaymentService.handle_wechat_refund_notify(
            db,
            {
                'id': 'EVENT-42',
                'mocked': True,
                'out_refund_no': refund.out_refund_no,
                'status': 'SUCCESS',
            },
        )

    finalize.assert_called_once_with(db, refund, tx)
    assert result['refund_id'] == refund.id
    assert result['provider_status'] == 'SUCCESS'


def _finalization_db(tx, order, refund):
    db = MagicMock()

    def query(model):
        result = MagicMock()
        row = {
            payment_module.PaymentTransaction: tx,
            payment_module.Order: order,
            payment_module.PaymentRefund: refund,
        }[model]
        result.filter.return_value.with_for_update.return_value.first.return_value = row
        return result

    db.query.side_effect = query
    return db


def test_external_refund_finalization_applies_local_effects_once():
    tx = _transaction()
    order = _order()
    refund = _refund(status=RefundStatus.SUCCESS)
    db = _finalization_db(tx, order, refund)

    def apply_effects(_db, target):
        target.order_status = OrderStatus.REFUND
        target.pay_status = PayStatus.REFUNDED

    with (
        patch.object(OrderService, '_validate_paid_refund_transition'),
        patch.object(OrderService, '_apply_paid_refund_side_effects', side_effect=apply_effects) as apply_effects_mock,
    ):
        first = OrderService.finalize_external_refund(db, refund, tx)
        second = OrderService.finalize_external_refund(db, refund, tx)

    assert first is order
    assert second is order
    assert tx.refunded_amount == Decimal('9.90')
    apply_effects_mock.assert_called_once_with(db, order)


def test_late_payment_refund_finalization_only_reconciles_payment_state():
    tx = _transaction(
        status=PaymentStatus.FAILED,
        failed_reason='Provider payment succeeded after order was canceled; provider refund required',
    )
    order = _order(order_status=OrderStatus.REFUND, pay_status=PayStatus.UNPAID)
    refund = _refund(status=RefundStatus.SUCCESS)
    db = _finalization_db(tx, order, refund)

    with patch.object(OrderService, '_apply_paid_refund_side_effects') as apply_effects:
        result = OrderService.finalize_external_refund(db, refund, tx)

    assert result is order
    assert order.pay_status == PayStatus.REFUNDED
    assert tx.refunded_amount == Decimal('9.90')
    apply_effects.assert_not_called()


def test_duplicate_late_payment_refund_does_not_change_paid_order():
    tx = _transaction(
        status=PaymentStatus.FAILED,
        failed_reason='Provider payment succeeded after order was already paid; provider refund required',
    )
    order = _order(order_status=OrderStatus.SHIPPED, pay_status=PayStatus.PAID)
    refund = _refund(status=RefundStatus.SUCCESS)
    db = _finalization_db(tx, order, refund)

    with patch.object(OrderService, '_apply_paid_refund_side_effects') as apply_effects:
        result = OrderService.finalize_external_refund(db, refund, tx)

    assert result is order
    assert order.order_status == OrderStatus.SHIPPED
    assert order.pay_status == PayStatus.PAID
    assert tx.refunded_amount == Decimal('9.90')
    apply_effects.assert_not_called()


def test_automatic_late_payment_refund_finalizes_verified_success():
    db = MagicMock()
    order = _order(order_status=OrderStatus.REFUND, pay_status=PayStatus.UNPAID)
    tx = _transaction(
        status=PaymentStatus.FAILED,
        failed_reason='Provider payment succeeded after order was canceled; provider refund required',
    )
    refund = _refund(status=RefundStatus.SUCCESS)

    with (
        patch.object(PaymentService, 'request_wechat_refund', return_value=refund) as request_refund,
        patch.object(OrderService, 'finalize_external_refund') as finalize,
    ):
        result = PaymentService._auto_refund_late_wechat_payment(db, order, tx)

    assert result is refund
    request_refund.assert_called_once_with(
        db,
        order,
        tx,
        reason='支付成功晚到，自动原路退款',
    )
    finalize.assert_called_once_with(db, refund, tx)


def test_automatic_late_payment_refund_rejects_terminal_failure_ack():
    db = MagicMock()
    order = _order(order_status=OrderStatus.REFUND, pay_status=PayStatus.UNPAID)
    tx = _transaction(status=PaymentStatus.FAILED)
    refund = _refund(status=RefundStatus.CLOSED)

    with (
        patch.object(PaymentService, 'request_wechat_refund', return_value=refund),
        pytest.raises(ConflictError, match='Automatic WeChat refund failed: CLOSED'),
    ):
        PaymentService._auto_refund_late_wechat_payment(db, order, tx)
