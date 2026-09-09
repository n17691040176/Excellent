from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.city_partner import (
    CityPartnerPurchaseRequest,
    CityPartnerSeatCreateRequest,
    CityPartnerSeatUpdateRequest,
)
from app.services.city_partner_service import CityPartnerService

router = APIRouter(prefix='/admin/city-partners', tags=['后台城市合伙人'])


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
        'data': {'items': [CityPartnerService.serialize_seat(db, x) for x in items], 'total': len(items)},
    }


@router.post('')
def create_city_partner_seat(
    payload: CityPartnerSeatCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    seat = CityPartnerService.create_seat(db, **payload.model_dump())
    return {'code': 0, 'message': '城市合伙人席位已创建', 'data': CityPartnerService.serialize_seat(db, seat)}


@router.put('/{seat_id}')
def update_city_partner_seat(
    seat_id: int,
    payload: CityPartnerSeatUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    seat = CityPartnerService.update_seat(seat_id=seat_id, db=db, **payload.model_dump())
    return {'code': 0, 'message': '城市合伙人席位已更新', 'data': CityPartnerService.serialize_seat(db, seat)}


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


@user_router.get('/seats')
def list_public_seats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    items = CityPartnerService.list_seats(db)
    return {
        'code': 0,
        'message': 'success',
        'data': {'items': [CityPartnerService.serialize_seat(db, x) for x in items], 'total': len(items)},
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
            'seat': CityPartnerService.serialize_seat(db, seat),
            'rotation': CityPartnerService.serialize_flow(flow),
        },
    }
