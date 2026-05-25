from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.earning_rule import EarningRuleCreateRequest, EarningRuleStatusRequest, EarningRuleUpdateRequest
from app.services.earning_rule_service import EarningRuleService

admin_router = APIRouter(prefix='/admin')


@admin_router.get('/earning-rules')
def list_rules(
    rule_type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    EarningRuleService.ensure_default_rules(db)
    return {'code': 0, 'message': 'success', 'data': EarningRuleService.list_rules(db, rule_type=rule_type, is_active=is_active)}


@admin_router.post('/earning-rules')
def create_rule(
    payload: EarningRuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': EarningRuleService.create_rule(db, current_user, payload)}


@admin_router.put('/earning-rules/{rule_id}')
def update_rule(
    rule_id: int,
    payload: EarningRuleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': EarningRuleService.update_rule(db, rule_id, current_user, payload)}


@admin_router.patch('/earning-rules/{rule_id}/status')
def update_rule_status(
    rule_id: int,
    payload: EarningRuleStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': EarningRuleService.update_status(db, rule_id, current_user, payload.is_active)}


@admin_router.delete('/earning-rules/{rule_id}')
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    EarningRuleService.delete_rule(db, rule_id)
    return {'code': 0, 'message': 'success', 'data': True}
