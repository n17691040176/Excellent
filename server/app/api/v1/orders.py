from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.api.v1.mobile_serializers import enum_value, page_slice, serialize_admin_order, serialize_order
from app.db.session import get_db
from app.models.enums import GlobalRole, OrderStatus, OrderType, PayStatus, ZoneType
from app.models.user import User
from app.schemas.product import CreateOrderRequest, OrderPaymentStatusRequest, OrderPayRequest
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

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
def refund_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = OrderService.refund_order(db, current_user.id, order_id)
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, order, include_detail=True)}


@app_router.post('/{order_id}/pay-demo')
def pay_demo(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, OrderService.pay_order_for_user(db, current_user.id, order_id))}


@app_router.post('/{order_id}/pay')
def pay_order(
    order_id: int,
    payload: OrderPayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = OrderService.pay_order(
        db,
        current_user,
        order_id,
        payload.pay_channel,
        points_amount=payload.points_amount,
        auto_complete=payload.auto_complete,
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
    result = PaymentService.reconcile_alipay_payment(db, order, payload.out_trade_no)
    transaction = result['transaction']
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'order': serialize_order(db, result['order'], include_detail=True),
            'payment_status': enum_value(transaction.status) if transaction else enum_value(result['order'].pay_status),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = OrderService.refund_order_for_admin(db, order_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_admin_order(db, order, include_detail=True)}
