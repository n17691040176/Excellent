from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.city_partner import (
    CityPartnerOrderRequest,
    CityPartnerPurchaseRequest,
    CityPartnerSeatCreateRequest,
    CityPartnerSeatUpdateRequest,
)
from app.services.city_partner_service import CityPartnerService

router = APIRouter(prefix='/admin/city-partners', tags=['后台城市合伙人'])


@router.get('/unsettled-purchases')
def unsettled_purchases(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                        db: Session = Depends(get_db), _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN))):
    from app.models.city_partner import CityPartnerPurchase, CityPartnerSeat
    from app.models.enums import PayStatus
    from app.models.order import Order
    from app.utils.helpers import iso_datetime
    query = db.query(CityPartnerPurchase, Order, CityPartnerSeat).join(
        Order, Order.id == CityPartnerPurchase.order_id,
    ).join(CityPartnerSeat, CityPartnerSeat.id == CityPartnerPurchase.seat_id).filter(
        Order.pay_status == PayStatus.PAID, CityPartnerPurchase.settled_at.is_(None),
    )
    total = query.count()
    rows = query.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {'code': 0, 'message': 'success', 'data': {'total': total, 'items': [
        {'order_id': order.id, 'order_no': order.order_no, 'user_id': order.user_id,
         'province': seat.province, 'city': seat.city, 'paid_amount': str(order.paid_amount),
         'paid_at': iso_datetime(order.paid_at), 'settlement_error': purchase.settlement_error,
         'price_version': purchase.price_version, 'current_price_version': seat.price_version}
        for purchase, order, seat in rows
    ]}}


@router.get('/list')
def list_city_partner_seats(
    province: str | None = Query(None),
    city: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    items = CityPartnerService.list_seats(db, province, city)
    return {
        'code': 0,
        'message': 'success',
        'data': {'items': [CityPartnerService.serialize_seat(db, x, admin=True) for x in items], 'total': len(items)},
    }


@router.post('')
def create_city_partner_seat(
    payload: CityPartnerSeatCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    seat = CityPartnerService.create_seat(db, operator_id=_.id, **payload.model_dump())
    return {'code': 0, 'message': '城市合伙人席位已创建', 'data': CityPartnerService.serialize_seat(db, seat, admin=True)}


@router.put('/{seat_id}')
def update_city_partner_seat(
    seat_id: int,
    payload: CityPartnerSeatUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    seat = CityPartnerService.update_seat(seat_id=seat_id, db=db, operator_id=_.id, **payload.model_dump())
    return {'code': 0, 'message': '城市合伙人席位已更新', 'data': CityPartnerService.serialize_seat(db, seat, admin=True)}


@router.get('/{seat_id}/rule-history')
def seat_rule_history(seat_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                      db: Session = Depends(get_db), _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN))):
    from app.services.commission_audit import list_rule_changes
    return {'code': 0, 'message': 'success', 'data': list_rule_changes(db, 'SEAT', seat_id, page, page_size)}


@router.get('/{seat_id}/rotations')
def list_rotations(
    seat_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    from app.models.city_partner import CityPartnerRotationFlow

    rows = (
        db.query(CityPartnerRotationFlow)
        .filter(CityPartnerRotationFlow.seat_id == seat_id)
        .order_by(CityPartnerRotationFlow.id.desc())
        .all()
    )
    return {
        'code': 0,
        'message': 'success',
        'data': {'items': [CityPartnerService.serialize_flow(x) for x in rows], 'total': len(rows)},
    }


user_router = APIRouter(prefix='/city-partners', tags=['城市合伙人'])


@user_router.get('/availability')
def city_partner_availability(response: Response, db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    return {'code': 0, 'message': 'success', 'data': {'enabled': CityPartnerService.mobile_enabled(db)}}


@user_router.get('/seats')
def list_public_seats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if not CityPartnerService.mobile_enabled(db):
        return {'code': 0, 'message': 'success', 'data': {'enabled': False, 'items': [], 'total': 0}}
    items = CityPartnerService.list_seats(db)
    return {
        'code': 0,
        'message': 'success',
        'data': {'enabled': True, 'items': [CityPartnerService.serialize_seat(db, x, viewer_id=_.id) for x in items], 'total': len(items)},
    }


@user_router.post('/seats/{seat_id}/purchase')
def purchase_city_partner_seat(
    seat_id: int,
    payload: CityPartnerPurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    seat, flow = CityPartnerService.purchase_or_rotate(db, seat_id, current_user, payload.order_id)
    return {
        'code': 0,
        'message': '城市合伙人席位购买/轮换成功',
        'data': {
            'seat': CityPartnerService.serialize_seat(db, seat, viewer_id=current_user.id),
            'rotation': CityPartnerService.serialize_flow(flow),
        },
    }


@user_router.post('/seats/{seat_id}/orders')
def create_city_partner_order(
    seat_id: int, payload: CityPartnerOrderRequest, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.api.v1.mobile_serializers import serialize_order
    order = CityPartnerService.create_purchase_order(db, seat_id, current_user, payload.price_version)
    return {'code': 0, 'message': 'success', 'data': serialize_order(db, order)}
