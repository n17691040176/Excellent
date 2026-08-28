from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.api.v1.mobile_serializers import enum_value, page_slice, serialize_admin_order, serialize_order
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.models.enums import GlobalRole, OrderStatus, OrderType, PaymentChannel, PaymentStatus, PayStatus, ZoneType
from app.models.payment import PaymentTransaction
from app.models.user import User
from app.schemas.product import (
    CreateOrderRequest,
    OrderPaymentStatusRequest,
    OrderPayRequest,
    OrderRefundRequest,
    OrderRefundStatusRequest,
)
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.utils.request_context import build_payment_request_context

app_router = APIRouter(prefix='/app/orders')
admin_router = APIRouter(prefix='/admin/orders')


APP_ORDER_STATUS_MAP = {
    'pending_payment': OrderStatus.PENDING_PAYMENT,
    'pending_ship': OrderStatus.PENDING_SHIP,
    'shipped': OrderStatus.SHIPPED,
    'completed': OrderStatus.COMPLETED,
    'canceled': OrderStatus.REFUND,
    'refund': OrderStatus.REFUND,
}


class MarkOrdersViewedRequest(BaseModel):
    status: str = 'all'


def _refund_idempotency_key(value: str | None) -> str | None:
    normalized = str(value or '').strip()
    if not normalized:
        return None
    if len(normalized.encode('utf-8')) > 128:
        raise ConflictError('Idempotency-Key must not exceed 128 bytes')
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in normalized):
        raise ConflictError('Idempotency-Key contains unsupported control characters')
    return normalized


def _serialize_refund_result(db: Session, result: dict, serializer) -> dict:
    return {
        'order': serializer(db, result['order'], include_detail=True),
        'refund': PaymentService.serialize_refund(result.get('refund')),
        'provider_status': result.get('provider_status'),
        'completed': bool(result.get('completed')),
    }


@app_router.post('')
def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order_payload = payload.model_dump()
    order_payload['order_type'] = OrderType(order_payload['order_type'])
    if order_payload.get('zone_type'):
        order_payload['zone_type'] = ZoneType(order_payload['zone_type'])
    order = OrderService.create_order(db, current_user, order_payload)
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, order)}


@app_router.post('/preview')
def preview_order(payload: CreateOrderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    preview_payload = payload.model_dump()
    preview_payload['order_type'] = OrderType(preview_payload['order_type'])
    if preview_payload.get('zone_type'):
        preview_payload['zone_type'] = ZoneType(preview_payload['zone_type'])
    return {'code': 0, 'message': 'success', 'data': OrderService.preview_order_payment(db, current_user, preview_payload)}


@app_router.get('')
def list_orders(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    order_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = OrderService.list_orders(db, current_user.id)
    if status:
        target_status = enum_value(APP_ORDER_STATUS_MAP.get(status) or status)
        rows = [item for item in rows if enum_value(item.order_status) == target_status]
    if order_type:
        rows = [item for item in rows if enum_value(item.order_type) == order_type]
    rows = page_slice(rows, page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_order(db, item) for item in rows]}


@app_router.get('/unread-counts')
def unread_order_counts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': OrderService.order_unread_counts(db, current_user.id)}


@app_router.get('/status-counts')
def order_status_counts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': OrderService.order_status_counts(db, current_user.id)}


@app_router.post('/viewed')
def mark_orders_viewed(
    payload: MarkOrdersViewedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    counts = OrderService.mark_order_status_viewed(db, current_user.id, payload.status)
    return {'code': 0, 'message': 'success', 'data': {'unread_counts': counts}}


@app_router.get('/{order_id}')
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = OrderService.get_order(db, current_user.id, order_id)
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, order, include_detail=True)}


@app_router.post('/{order_id}/confirm')
def confirm_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, OrderService.confirm_order(db, current_user.id, order_id))}


@app_router.post('/{order_id}/cancel')
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = OrderService.cancel_order(db, current_user.id, order_id)
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, order, include_detail=True)}


@app_router.post('/{order_id}/refund')
def refund_order(
    order_id: int,
    payload: OrderRefundRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = OrderService.get_order(db, current_user.id, order_id)
    result = OrderService.refund_order_with_result(
        db,
        order,
        reason=payload.reason if payload else None,
        idempotency_key=_refund_idempotency_key(idempotency_key),
        requested_by=current_user.id,
    )
    return {'code': 0, 'message': 'success', 'data': _serialize_refund_result(db, result, serialize_order)}


@app_router.post('/{order_id}/refund-status')
def sync_order_refund_status(
    order_id: int,
    payload: OrderRefundStatusRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = OrderService.get_order(db, current_user.id, order_id)
    result = OrderService.sync_wechat_refund_for_order(
        db,
        order,
        out_refund_no=payload.out_refund_no if payload else None,
    )
    return {'code': 0, 'message': 'success', 'data': _serialize_refund_result(db, result, serialize_order)}


@app_router.post('/{order_id}/pay-demo')
def pay_demo(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, OrderService.pay_order_for_user(db, current_user.id, order_id))}


@app_router.post('/{order_id}/pay')
def pay_order(
    order_id: int,
    payload: OrderPayRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ignore client-supplied request_payload values.  Provider context must be
    # derived from the actual request to avoid spoofing payer_client_ip.
    request_payload = build_payment_request_context(request)
    result = OrderService.pay_order(
        db,
        current_user,
        order_id,
        payload.pay_channel,
        points_amount=payload.points_amount,
        auto_complete=payload.auto_complete,
        request_payload=request_payload or None,
    )
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'order': serialize_order(db, result['order'], include_detail=True),
            'payment': result['payment'],
        },
    }


@app_router.post('/{order_id}/payment-status')
def sync_order_payment_status(
    order_id: int,
    payload: OrderPaymentStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = OrderService.get_order(db, current_user.id, order_id)
    requested_channel = str(payload.pay_channel or '').strip().upper()
    if requested_channel and requested_channel not in {'WECHAT', 'ALIPAY'}:
        raise ConflictError('Unsupported pay channel')
    if payload.return_params and requested_channel == 'WECHAT':
        raise ConflictError('WeChat payment cannot use Alipay return parameters')

    normalized_trade_no = str(payload.out_trade_no or '').strip()
    return_trade_no = str((payload.return_params or {}).get('out_trade_no') or '').strip()
    if normalized_trade_no and return_trade_no and normalized_trade_no != return_trade_no:
        raise ConflictError('Payment transaction mismatch')

    lookup_trade_no = normalized_trade_no or return_trade_no
    transaction_hint = None
    if lookup_trade_no:
        transaction_hint = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.order_id == order.id,
                PaymentTransaction.out_trade_no == lookup_trade_no,
            )
            .first()
        )
        # A caller that supplied a trade number must identify a transaction
        # belonging to this order.  Do not fall through to the other provider
        # or silently reconcile a different local transaction.
        if transaction_hint is None and not payload.return_params:
            raise NotFoundError('Payment transaction not found')
    elif not requested_channel and not payload.return_params:
        # A client may poll immediately after returning from the provider
        # without echoing out_trade_no. Infer the channel from the latest
        # active local transaction instead of assuming one provider. Settled
        # orders must prefer their paid transaction over any stale pending
        # transaction created through another channel.
        transaction_statuses = (
            (PaymentStatus.PAID,)
            if order.pay_status == PayStatus.PAID
            else (PaymentStatus.PENDING, PaymentStatus.PAID)
        )
        transaction_hint = (
            db.query(PaymentTransaction)
            .filter(
                PaymentTransaction.order_id == order.id,
                PaymentTransaction.status.in_(transaction_statuses),
            )
            .order_by(PaymentTransaction.id.desc())
            .first()
        )
    if requested_channel and transaction_hint is not None:
        hinted_channel = str(getattr(transaction_hint.channel, 'value', transaction_hint.channel)).upper()
        if hinted_channel != requested_channel:
            raise ConflictError('Payment channel mismatch')
    if payload.return_params and transaction_hint is not None:
        hinted_channel = str(getattr(transaction_hint.channel, 'value', transaction_hint.channel)).upper()
        if hinted_channel != PaymentChannel.ALIPAY.value:
            raise ConflictError('Payment channel mismatch')

    inferred_channel = requested_channel
    if not inferred_channel and transaction_hint is not None:
        inferred_channel = str(getattr(transaction_hint.channel, 'value', transaction_hint.channel)).upper()
    if payload.return_params:
        result = PaymentService.reconcile_alipay_return(db, order, payload.return_params)
    elif inferred_channel == PaymentChannel.WECHAT.value:
        result = PaymentService.reconcile_wechat_payment(db, order, normalized_trade_no or None)
    elif inferred_channel == PaymentChannel.ALIPAY.value:
        result = PaymentService.reconcile_alipay_payment(db, order, normalized_trade_no or None)
    else:
        result = {
            'order': order,
            'transaction': None,
            'provider_status': 'NO_TRANSACTION',
        }
    transaction = result['transaction']
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'order': serialize_order(db, result['order'], include_detail=True),
            'payment_status': (
                enum_value(result['order'].pay_status)
                if result['order'].pay_status == PayStatus.PAID
                else enum_value(transaction.status) if transaction else enum_value(result['order'].pay_status)
            ),
            'provider_status': result['provider_status'],
            'out_trade_no': transaction.out_trade_no if transaction else None,
        },
    }


@admin_router.get('')
def admin_list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    order_status: OrderStatus | None = Query(default=None),
    pay_status: PayStatus | None = Query(default=None),
    order_type: OrderType | None = Query(default=None),
    zone_type: ZoneType | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    result = OrderService.list_orders_for_admin(
        db,
        current_user,
        keyword=keyword,
        order_status=enum_value(order_status),
        pay_status=enum_value(pay_status),
        order_type=enum_value(order_type),
        zone_type=enum_value(zone_type),
        page=page,
        page_size=page_size,
    )
    return {
        'code': 0,
        'message': 'success',
        'data': {
            **result,
            'items': [serialize_admin_order(db, row) for row in result['items']],
        },
    }


@admin_router.get('/{order_id}')
def admin_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.get_order_for_admin(db, order_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_admin_order(db, order, include_detail=True)}


@admin_router.post('/{order_id}/pay')
def mark_paid(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.mark_paid_for_admin(db, order_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_admin_order(db, order, include_detail=True)}


@admin_router.post('/{order_id}/ship')
def mark_shipped(
    order_id: int,
    tracking_no: str | None = Query(default=None, description='物流单号'),
    tracking_company: str | None = Query(default=None, description='物流公司'),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.ship_order_for_admin(db, order_id, current_user, tracking_no, tracking_company)
    return {'code': 0, 'message': 'success', 'data': serialize_admin_order(db, order, include_detail=True)}


@admin_router.post('/{order_id}/confirm')
def admin_confirm_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.confirm_order_for_admin(db, order_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_admin_order(db, order, include_detail=True)}


@admin_router.post('/{order_id}/close')
def admin_close_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.close_order_for_admin(db, order_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_admin_order(db, order, include_detail=True)}


@admin_router.post('/{order_id}/refund')
def admin_refund_order(
    order_id: int,
    payload: OrderRefundRequest | None = None,
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.get_order_for_admin(db, order_id, current_user)
    result = OrderService.refund_order_with_result(
        db,
        order,
        reason=payload.reason if payload else None,
        idempotency_key=_refund_idempotency_key(idempotency_key),
        requested_by=current_user.id,
    )
    return {'code': 0, 'message': 'success', 'data': _serialize_refund_result(db, result, serialize_admin_order)}


@admin_router.post('/{order_id}/refund-status')
def admin_sync_order_refund_status(
    order_id: int,
    payload: OrderRefundStatusRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.get_order_for_admin(db, order_id, current_user)
    result = OrderService.sync_wechat_refund_for_order(
        db,
        order,
        out_refund_no=payload.out_refund_no if payload else None,
    )
    return {
        'code': 0,
        'message': 'success',
        'data': _serialize_refund_result(db, result, serialize_admin_order),
    }
