from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole, UserStatus
from app.models.user import User
from app.schemas.user import UpdateProfileRequest, UpdateUserStatusRequest
from app.services.asset_service import AssetService
from app.services.user_service import UserService

app_router = APIRouter(prefix='/app/users')
admin_router = APIRouter(prefix='/admin/users')


@app_router.get('/profile')
def get_profile(current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': current_user}


@app_router.put('/profile')
def update_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = UserService.update_profile(db, current_user, payload.model_dump(exclude_none=True))
    return {'code': 0, 'message': 'success', 'data': user}


@app_router.get('/invite-code')
def invite_code(current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': {'invite_code': current_user.invite_code}}


@app_router.get('/invite-records')
def invite_records(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tree = UserService.get_invite_tree(db, current_user.id)
    return {'code': 0, 'message': 'success', 'data': tree}


@app_router.get('/team-summary')
def team_summary(current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': {'team_id': current_user.team_id}}


@admin_router.get('')
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    users = UserService.list_users(db, current_user)
    return {'code': 0, 'message': 'success', 'data': users}


@admin_router.get('/{user_id}')
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    user = UserService.get_user(db, user_id, current_user)
    return {'code': 0, 'message': 'success', 'data': user}


@admin_router.patch('/{user_id}/status')
def update_user_status(
    user_id: int,
    payload: UpdateUserStatusRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    user = UserService.update_user_status(db, user_id, UserStatus(payload.status))
    return {'code': 0, 'message': 'success', 'data': user}


@admin_router.get('/{user_id}/invite-tree')
def invite_tree(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    return {'code': 0, 'message': 'success', 'data': UserService.get_invite_tree(db, user_id, current_user)}
