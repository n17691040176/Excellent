from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole, PowerBankStatus, UserStatus
from app.models.team import TeamMember
from app.models.user import User
from app.schemas.asset import AdminPowerBankCreateRequest, AdminPowerBankUpdateRequest
from app.schemas.user import UpdateProfileRequest, UpdateUserStatusRequest
from app.services.asset_service import AssetService
from app.services.user_service import UserService

app_router = APIRouter(prefix='/app/users')
admin_router = APIRouter(prefix='/admin/users')


@app_router.get('/profile')
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': UserService.serialize_app_user(db, current_user)}


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
    if not UserService.is_legacy_user(db, current_user):
        return {'code': 0, 'message': 'success', 'data': {'user_id': current_user.id, 'level1': [], 'level2': [], 'items': []}}
    tree = UserService.get_invite_tree(db, current_user.id)
    tree['items'] = [
        {**item, 'level': 1, 'status': 'valid', 'status_text': 'valid'}
        for item in tree.get('level1', [])
    ] + [
        {**item, 'level': 2, 'status': 'valid', 'status_text': 'valid'}
        for item in tree.get('level2', [])
    ]
    return {'code': 0, 'message': 'success', 'data': tree}


@app_router.get('/team-summary')
def team_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not UserService.is_legacy_user(db, current_user):
        return {
            'code': 0,
            'message': 'success',
            'data': {
                'team_id': current_user.team_id,
                'member_count': 0,
                'total_members': 0,
            },
        }
    member_count = 0
    if current_user.team_id:
        member_count = int(
            db.query(func.count(TeamMember.id)).filter(TeamMember.team_id == current_user.team_id).scalar() or 0
        )
    else:
        member_count = int(
            db.query(func.count(User.id)).filter(
                (User.parent_id == current_user.id) | (User.grandparent_id == current_user.id)
            ).scalar() or 0
        )
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'team_id': current_user.team_id,
            'member_count': member_count,
            'total_members': member_count,
        },
    }


@admin_router.get('')
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    role: str | None = Query(default=None),
    source: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    role_filter = GlobalRole(role) if role else None
    data = UserService.list_users_page(
        db,
        current_user,
        keyword=keyword,
        role=role_filter,
        source=source,
        page=page,
        page_size=page_size,
    )
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.get('/{user_id}')
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    user = UserService.get_user_for_admin(db, user_id, current_user)
    return {'code': 0, 'message': 'success', 'data': user}


@admin_router.get('/{user_id}/legacy-profile')
def get_user_legacy_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    data = UserService.get_user_legacy_profile(db, user_id, current_user)
    return {'code': 0, 'message': 'success', 'data': data}


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


@admin_router.get('/{user_id}/power-banks')
def list_user_power_banks(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    user = UserService.get_user(db, user_id, current_user)
    return {'code': 0, 'message': 'success', 'data': AssetService.list_power_banks(db, user.id)}


@admin_router.post('/{user_id}/power-banks')
def bind_user_power_bank(
    user_id: int,
    payload: AdminPowerBankCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    user = UserService.get_user(db, user_id, current_user)
    data = AssetService.bind_power_bank(
        db,
        user.id,
        payload.device_code,
        device_name=payload.device_name,
        remark=payload.remark,
    )
    return {'code': 0, 'message': 'success', 'data': data}


@admin_router.patch('/{user_id}/power-banks/{power_bank_id}')
def update_user_power_bank(
    user_id: int,
    power_bank_id: int,
    payload: AdminPowerBankUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    user = UserService.get_user(db, user_id, current_user)
    data = AssetService.update_power_bank_status(db, user.id, power_bank_id, PowerBankStatus(payload.status))
    return {'code': 0, 'message': 'success', 'data': data}
