from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.api.v1.mobile_serializers import enum_value, page_slice, serialize_order
from app.db.session import get_db
from app.models.enums import GlobalRole, OrderStatus, OrderType, ZoneType
from app.models.user import User
from app.schemas.product import CreateOrderRequest, OrderPayRequest
from app.services.order_service import OrderService

app_router = APIRouter(prefix='/app/orders')
admin_router = APIRouter(prefix='/admin/orders')


APP_ORDER_STATUS_MAP = {
    'pending_payment': OrderStatus.CREATED,
    'pending_service': OrderStatus.PAID,
    'shipping': OrderStatus.PAID,
    'completed': OrderStatus.CONFIRMED,
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
    order = OrderService.get_order(db, current_user.id, order_id)
    order.order_status = OrderStatus.CLOSED
    db.commit()
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


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


@admin_router.post('/{order_id}/pay')
def mark_paid(order_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': OrderService.mark_paid(db, order_id)}

