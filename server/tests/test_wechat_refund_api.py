import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1 import orders as orders_module
from app.api.v1 import payments as payments_module
from app.core.exceptions import ConflictError
from app.schemas.product import OrderRefundRequest, OrderRefundStatusRequest


class _Request:
    def __init__(self, raw_body: bytes, headers: dict[str, str] | None = None):
        self._raw_body = raw_body
        self.headers = headers or {}

    async def body(self) -> bytes:
        return self._raw_body


def _refund_result(order, *, provider_status='PROCESSING', completed=False):
    return {
        'order': order,
        'refund': SimpleNamespace(id=91),
        'provider_status': provider_status,
        'completed': completed,
    }


def test_wechat_refund_notify_forwards_original_body_and_signature_headers():
    payload = {
        'id': 'EVT-REFUND-1',
        'event_type': 'REFUND.SUCCESS',
        'resource': {'ciphertext': 'encrypted'},
    }
    raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    request = _Request(
        raw_body,
        {
            'Wechatpay-Timestamp': '1700000000',
            'Wechatpay-Nonce': 'nonce-1',
            'Wechatpay-Signature': 'signature-1',
            'Wechatpay-Serial': 'serial-1',
        },
    )
    db = MagicMock()

    with patch.object(payments_module.PaymentService, 'handle_wechat_refund_notify') as handle_refund:
        response = asyncio.run(payments_module.wechat_refund_notify(request, db))

    handle_refund.assert_called_once_with(
        db,
        payload,
        raw_body=raw_body,
        headers={
            'Wechatpay-Timestamp': '1700000000',
            'Wechatpay-Nonce': 'nonce-1',
            'Wechatpay-Signature': 'signature-1',
            'Wechatpay-Serial': 'serial-1',
        },
    )
    assert json.loads(response.body) == {'code': 'SUCCESS', 'message': 'success'}


def test_wechat_refund_notify_route_is_registered_at_the_configured_callback_path():
    routes = [
        route
        for route in payments_module.app_router.routes
        if route.path == '/payments/wechat/refund-notify'
    ]

    assert len(routes) == 1
    assert routes[0].methods == {'POST'}


def test_wechat_refund_notify_rejects_invalid_json_without_acknowledging():
    request = _Request(b'{not-json')

    with (
        patch.object(payments_module.PaymentService, 'handle_wechat_refund_notify') as handle_refund,
        pytest.raises(ConflictError, match='refund notify body is invalid JSON'),
    ):
        asyncio.run(payments_module.wechat_refund_notify(request, SimpleNamespace()))

    handle_refund.assert_not_called()


def test_wechat_refund_notify_rejects_non_object_json_without_acknowledging():
    request = _Request(b'[]')

    with (
        patch.object(payments_module.PaymentService, 'handle_wechat_refund_notify') as handle_refund,
        pytest.raises(ConflictError, match='refund notify payload must be a JSON object'),
    ):
        asyncio.run(payments_module.wechat_refund_notify(request, SimpleNamespace()))

    handle_refund.assert_not_called()


def test_user_refund_submission_forwards_reason_idempotency_and_requester():
    db = MagicMock()
    current_user = SimpleNamespace(id=7)
    order = SimpleNamespace(id=42)
    result = _refund_result(order)

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order) as get_order,
        patch.object(orders_module.OrderService, 'refund_order_with_result', return_value=result) as refund_order,
        patch.object(orders_module, 'serialize_order', return_value={'id': order.id, 'scope': 'app'}) as serialize_order,
        patch.object(orders_module.PaymentService, 'serialize_refund', return_value={'id': 91, 'status': 'PROCESSING'}),
    ):
        response = orders_module.refund_order(
            order.id,
            OrderRefundRequest(reason='Customer changed their mind'),
            '  refund-request-42  ',
            db,
            current_user,
        )

    get_order.assert_called_once_with(db, current_user.id, order.id)
    refund_order.assert_called_once_with(
        db,
        order,
        reason='Customer changed their mind',
        idempotency_key='refund-request-42',
        requested_by=current_user.id,
    )
    serialize_order.assert_called_once_with(db, order, include_detail=True)
    assert response == {
        'code': 0,
        'message': 'success',
        'data': {
            'order': {'id': 42, 'scope': 'app'},
            'refund': {'id': 91, 'status': 'PROCESSING'},
            'provider_status': 'PROCESSING',
            'completed': False,
        },
    }


def test_admin_refund_submission_uses_scope_checked_order_lookup():
    db = MagicMock()
    current_user = SimpleNamespace(id=17)
    order = SimpleNamespace(id=88)
    result = _refund_result(order, provider_status='SUCCESS', completed=True)

    with (
        patch.object(orders_module.OrderService, 'get_order_for_admin', return_value=order) as get_order_for_admin,
        patch.object(orders_module.OrderService, 'get_order') as get_order,
        patch.object(orders_module.OrderService, 'refund_order_with_result', return_value=result) as refund_order,
        patch.object(orders_module, 'serialize_admin_order', return_value={'id': order.id, 'scope': 'admin'}),
        patch.object(orders_module.PaymentService, 'serialize_refund', return_value={'id': 91, 'status': 'SUCCESS'}),
    ):
        response = orders_module.admin_refund_order(
            order.id,
            OrderRefundRequest(reason='admin approved'),
            'admin-refund-88',
            db,
            current_user,
        )

    get_order_for_admin.assert_called_once_with(db, order.id, current_user)
    get_order.assert_not_called()
    refund_order.assert_called_once_with(
        db,
        order,
        reason='admin approved',
        idempotency_key='admin-refund-88',
        requested_by=current_user.id,
    )
    assert response['data']['order'] == {'id': 88, 'scope': 'admin'}
    assert response['data']['refund'] == {'id': 91, 'status': 'SUCCESS'}
    assert response['data']['provider_status'] == 'SUCCESS'
    assert response['data']['completed'] is True


@pytest.mark.parametrize(
    ('provider_status', 'completed'),
    [
        ('SUCCESS', True),
        ('PROCESSING', False),
        ('FAILED', False),
    ],
)
def test_user_refund_status_sync_forwards_specific_refund_number(provider_status, completed):
    db = MagicMock()
    current_user = SimpleNamespace(id=7)
    order = SimpleNamespace(id=42)
    result = _refund_result(order, provider_status=provider_status, completed=completed)

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order) as get_order,
        patch.object(orders_module.OrderService, 'sync_wechat_refund_for_order', return_value=result) as sync_refund,
        patch.object(orders_module, 'serialize_order', return_value={'id': order.id}),
        patch.object(
            orders_module.PaymentService,
            'serialize_refund',
            return_value={'id': 91, 'status': provider_status},
        ),
    ):
        response = orders_module.sync_order_refund_status(
            order.id,
            OrderRefundStatusRequest(out_refund_no='REFUND-42'),
            db,
            current_user,
        )

    get_order.assert_called_once_with(db, current_user.id, order.id)
    sync_refund.assert_called_once_with(db, order, out_refund_no='REFUND-42')
    assert response['data'] == {
        'order': {'id': 42},
        'refund': {'id': 91, 'status': provider_status},
        'provider_status': provider_status,
        'completed': completed,
    }


def test_admin_refund_status_sync_uses_scope_checked_order_lookup():
    db = MagicMock()
    current_user = SimpleNamespace(id=17)
    order = SimpleNamespace(id=88)
    result = _refund_result(order, provider_status='PROCESSING', completed=False)

    with (
        patch.object(orders_module.OrderService, 'get_order_for_admin', return_value=order) as get_order_for_admin,
        patch.object(orders_module.OrderService, 'get_order') as get_order,
        patch.object(orders_module.OrderService, 'sync_wechat_refund_for_order', return_value=result) as sync_refund,
        patch.object(orders_module, 'serialize_admin_order', return_value={'id': order.id, 'scope': 'admin'}),
        patch.object(orders_module.PaymentService, 'serialize_refund', return_value={'id': 91, 'status': 'PROCESSING'}),
    ):
        response = orders_module.admin_sync_order_refund_status(
            order.id,
            OrderRefundStatusRequest(out_refund_no='REFUND-88'),
            db,
            current_user,
        )

    get_order_for_admin.assert_called_once_with(db, order.id, current_user)
    get_order.assert_not_called()
    sync_refund.assert_called_once_with(db, order, out_refund_no='REFUND-88')
    assert response['data']['order'] == {'id': 88, 'scope': 'admin'}
    assert response['data']['provider_status'] == 'PROCESSING'
    assert response['data']['completed'] is False


@pytest.mark.parametrize('idempotency_key', ['x' * 129, chr(0x6D4B) * 43, 'refund\nrequest'])
def test_refund_submission_rejects_invalid_idempotency_key_before_service_call(idempotency_key):
    db = MagicMock()
    current_user = SimpleNamespace(id=7)
    order = SimpleNamespace(id=42)

    with (
        patch.object(orders_module.OrderService, 'get_order', return_value=order),
        patch.object(orders_module.OrderService, 'refund_order_with_result') as refund_order,
        pytest.raises(ConflictError, match='Idempotency-Key'),
    ):
        orders_module.refund_order(
            order.id,
            OrderRefundRequest(),
            idempotency_key,
            db,
            current_user,
        )

    refund_order.assert_not_called()
