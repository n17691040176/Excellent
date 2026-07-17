from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.admin_permission import AdminPermissionUpdateRequest
from app.services.admin_permission_service import AdminPermissionService

router = APIRouter(prefix='/admin/permissions')


@router.get('/options')
def permission_options(_: User = Depends(require_roles(GlobalRole.SUPER_ADMIN))):
    return {'code': 0, 'message': 'success', 'data': AdminPermissionService.options()}


@router.get('/admins')
def list_permission_admins(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': AdminPermissionService.list_admins(db)}


@router.get('/admins/{user_id}')
def get_permission_admin(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': AdminPermissionService.get_admin_permissions(db, user_id)}


@router.put('/admins/{user_id}')
def update_permission_admin(
    user_id: int,
    payload: AdminPermissionUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    data = AdminPermissionService.save_admin_permissions(db, user_id, payload.permissions)
    return {'code': 0, 'message': 'success', 'data': data}
