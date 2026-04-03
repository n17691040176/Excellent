from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole, OrderStatus, OrderType, ZoneType
from app.models.user import User
from app.schemas.product import CreateOrderRequest
from app.services.order_service import OrderService

app_router = APIRouter(prefix='/app/orders')
admin_router = APIRouter(prefix='/admin/orders')


@app_router.post('')
def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order_payload = payload.model_dump()
    order_payload['order_type'] = OrderType(order_payload['order_type'])
    if order_payload.get('zone_type'):
        order_payload['zone_type'] = ZoneType(order_payload['zone_type'])
    order = OrderService.create_order(db, current_user, order_payload)
    return {'code': 0, 'message': 'success', 'data': order}


@app_router.get('')
def list_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': OrderService.list_orders(db, current_user.id)}


@app_router.get('/{order_id}')
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': OrderService.get_order_detail(db, current_user.id, order_id)}


@app_router.post('/{order_id}/confirm')
def confirm_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': OrderService.confirm_order(db, current_user.id, order_id)}


@app_router.post('/{order_id}/cancel')
def cancel_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = OrderService.get_order(db, current_user.id, order_id)
    order.order_status = OrderStatus.CLOSED
    db.commit()
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.post('/{order_id}/pay-demo')
def pay_demo(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': OrderService.pay_order_for_user(db, current_user.id, order_id)}


@admin_router.post('/{order_id}/pay')
def mark_paid(order_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': OrderService.mark_paid(db, order_id)}

