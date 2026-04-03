from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole, WithdrawType
from app.models.user import User
from app.schemas.commission import WithdrawCreateRequest
from app.services.commission_service import CommissionService

app_router = APIRouter(prefix='/app')
admin_router = APIRouter(prefix='/admin')


@app_router.get('/commission/summary')
def commission_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': CommissionService.summary(db, current_user.id)}


@app_router.get('/commission/flows')
def commission_flows(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': CommissionService.flows(db, current_user.id)}


@app_router.post('/withdraws')
def create_withdraw(payload: WithdrawCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = CommissionService.create_withdraw(db, current_user.id, WithdrawType(payload.withdraw_type), payload.amount, payload.remark)
    return {'code': 0, 'message': 'success', 'data': record}


@app_router.get('/withdraws')
def my_withdraws(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': CommissionService.list_withdraws(db, current_user.id)}


@admin_router.get('/commission/config')
def commission_config(db: Session = Depends(get_db), _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': CommissionService.get_config(db)}


@admin_router.get('/commission/flows')
def admin_commission_flows(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': CommissionService.list_flows_for_admin(db, current_user)}


@admin_router.get('/commission/users')
def admin_commission_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': CommissionService.list_user_commissions_for_admin(db, current_user)}


@admin_router.get('/withdraws')
def admin_withdraws(db: Session = Depends(get_db), current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': CommissionService.list_withdraws_for_admin(db, current_user)}


@admin_router.patch('/withdraws/{withdraw_id}/approve')
def approve_withdraw(
    withdraw_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    record = CommissionService.approve_withdraw(db, withdraw_id, current_user)
    return {'code': 0, 'message': 'success', 'data': record}


@admin_router.patch('/withdraws/{withdraw_id}/reject')
def reject_withdraw(
    withdraw_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    record = CommissionService.reject_withdraw(db, withdraw_id, current_user)
    return {'code': 0, 'message': 'success', 'data': record}
