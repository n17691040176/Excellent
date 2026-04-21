from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.api.v1.mobile_serializers import page_slice, serialize_commission_flow, serialize_withdraw_request
from app.core.exceptions import ForbiddenError
from app.db.session import get_db
from app.models.enums import GlobalRole, WithdrawType
from app.models.user import User
from app.schemas.commission import WithdrawCreateRequest
from app.services.commission_service import CommissionService
from app.services.user_service import UserService
from app.utils.helpers import now

app_router = APIRouter(prefix='/app')
admin_router = APIRouter(prefix='/admin')


@app_router.get('/commission/summary')
def commission_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not UserService.is_legacy_user(db, current_user):
        return {
            'code': 0,
            'message': 'success',
            'data': {'frozen_amount': 0, 'available_amount': 0, 'total_amount': 0, 'withdrawn_amount': 0, 'withdrawable_amount': 0},
        }
    data = CommissionService.summary(db, current_user.id)
    data['withdrawable_amount'] = data.get('available_amount', 0)
    return {'code': 0, 'message': 'success', 'data': data}


@app_router.get('/commission/flows')
def commission_flows(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not UserService.is_legacy_user(db, current_user):
        return {'code': 0, 'message': 'success', 'data': []}
    rows = page_slice(CommissionService.flows(db, current_user.id), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_commission_flow(item) for item in rows]}


@app_router.post('/withdraws')
def create_withdraw(payload: WithdrawCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.withdraw_type == WithdrawType.COMMISSION.value and not UserService.is_legacy_user(db, current_user):
        raise ForbiddenError('Commission feature is only available for legacy users')
    record = CommissionService.create_withdraw(db, current_user.id, WithdrawType(payload.withdraw_type), payload.amount, payload.remark)
    return {'code': 0, 'message': 'success', 'data': serialize_withdraw_request(record)}


@app_router.get('/withdraws')
def my_withdraws(
    recent_days: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = CommissionService.list_withdraws(db, current_user.id)
    if recent_days and recent_days > 0:
        cutoff = now() - timedelta(days=recent_days)
        rows = [item for item in rows if item.created_at and item.created_at >= cutoff]
    return {'code': 0, 'message': 'success', 'data': [serialize_withdraw_request(item) for item in rows]}


@admin_router.get('/commission/config')
def commission_config(db: Session = Depends(get_db), _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': CommissionService.get_config(db)}


@admin_router.get('/commission/flows')
def admin_commission_flows(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': CommissionService.list_flows_for_admin(db, current_user)}


@admin_router.get('/commission/users')
def admin_commission_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    data = CommissionService.list_user_commissions_page_for_admin(
        db,
        current_user,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.get('/withdraws')
def admin_withdraws(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    rows = CommissionService.list_withdraws_for_admin(db, current_user)
    return {'code': 0, 'message': 'success', 'data': [serialize_withdraw_request(item) for item in rows]}


@admin_router.patch('/withdraws/{withdraw_id}/approve')
def approve_withdraw(
    withdraw_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    record = CommissionService.approve_withdraw(db, withdraw_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_withdraw_request(record)}


@admin_router.patch('/withdraws/{withdraw_id}/reject')
def reject_withdraw(
    withdraw_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    record = CommissionService.reject_withdraw(db, withdraw_id, current_user)
    return {'code': 0, 'message': 'success', 'data': serialize_withdraw_request(record)}
