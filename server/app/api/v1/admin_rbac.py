from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.schemas.admin_rbac import (
    AdminChangePasswordRequest,
    AdminCreateRequest,
    AdminProfileUpdateRequest,
    AdminPromoteRequest,
    AdminResetPasswordRequest,
    AdminRoleCreateRequest,
    AdminRoleUpdateRequest,
    AdminStatusRequest,
    AdminUpdateRequest,
)
from app.services.admin_permission_service import AdminPermissionService
from app.services.admin_rbac_service import AdminRbacService

router = APIRouter(prefix='/admin')
admin_dependency = require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)


@router.get('/roles/options')
def role_options(_: User = Depends(admin_dependency)):
    return {'code': 0, 'message': 'success', 'data': AdminPermissionService.options()}


@router.get('/roles')
def list_roles(
    enabled_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.list_roles(db, current_user, enabled_only)}


@router.get('/roles/{role_id}')
def role_detail(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.get_role(db, current_user, role_id)}


@router.post('/roles')
def create_role(
    payload: AdminRoleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    data = AdminRbacService.create_role(db, current_user, payload.model_dump())
    return {'code': 0, 'message': 'success', 'data': data}


@router.put('/roles/{role_id}')
def update_role(
    role_id: int,
    payload: AdminRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    data = AdminRbacService.update_role(db, current_user, role_id, payload.model_dump(exclude_unset=True))
    return {'code': 0, 'message': 'success', 'data': data}


@router.delete('/roles/{role_id}')
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    AdminRbacService.delete_role(db, current_user, role_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@router.get('/admins')
def list_admins(
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.list_admins(db, current_user, keyword)}


@router.get('/admins/candidates')
def list_admin_candidates(
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.list_candidates(db, current_user, keyword)}


@router.get('/admins/teams')
def list_assignable_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.list_assignable_teams(db, current_user)}


@router.post('/admins')
def create_admin(
    payload: AdminCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.create_admin(db, current_user, payload.model_dump())}


@router.post('/admins/promote')
def promote_user(
    payload: AdminPromoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.promote_user(db, current_user, payload.model_dump())}


@router.put('/admins/{user_id}')
def update_admin(
    user_id: int,
    payload: AdminUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    data = AdminRbacService.update_admin(db, current_user, user_id, payload.model_dump(exclude_unset=True))
    return {'code': 0, 'message': 'success', 'data': data}


@router.patch('/admins/{user_id}/status')
def update_admin_status(
    user_id: int,
    payload: AdminStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    data = AdminRbacService.update_admin_status(db, current_user, user_id, payload.status)
    return {'code': 0, 'message': 'success', 'data': data}


@router.post('/admins/{user_id}/reset-password')
def reset_admin_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    AdminRbacService.reset_admin_password(db, current_user, user_id, payload.new_password)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@router.post('/admins/{user_id}/demote')
def demote_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    AdminRbacService.demote_admin(db, current_user, user_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@router.get('/profile')
def admin_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    return {'code': 0, 'message': 'success', 'data': AdminRbacService.profile(db, current_user)}


@router.put('/profile')
def update_admin_profile(
    payload: AdminProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    data = AdminRbacService.update_profile(db, current_user, payload.model_dump(exclude_unset=True))
    return {'code': 0, 'message': 'success', 'data': data}


@router.post('/profile/password')
def change_admin_password(
    payload: AdminChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_dependency),
):
    AdminRbacService.change_password(db, current_user, payload.current_password, payload.new_password)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}
