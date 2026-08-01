from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.session import get_db
from app.models.enums import GlobalRole
from app.models.user import User
from app.utils.helpers import iso_datetime

admin_router = APIRouter(prefix='/admin/invites')


@admin_router.get('/summary')
def invite_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    # Count total users with invite codes
    total_invite_codes = db.query(func.count(User.id)).filter(
        User.invite_code.isnot(None),
        User.invite_code != ''
    ).scalar() or 0

    # Count users who were invited (have inviter)
    total_invited_users = db.query(func.count(User.id)).filter(
        User.parent_id.isnot(None)
    ).scalar() or 0

    # Count level 1 invites
    level1_count = db.query(func.count(User.id)).filter(
        User.parent_id.isnot(None)
    ).scalar() or 0

    # Count level 2 invites
    level2_count = db.query(func.count(User.id)).filter(
        User.grandparent_id.isnot(None)
    ).scalar() or 0

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'total_invite_codes': total_invite_codes,
            'total_invited_users': total_invited_users,
            'level1_count': level1_count,
            'level2_count': level2_count,
        }
    }


@admin_router.get('/users')
def list_users_with_invites(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = db.query(User)

    if keyword:
        query = query.filter(
            or_(
                User.nickname.contains(keyword),
                User.phone.contains(keyword),
                User.invite_code.contains(keyword)
            )
        )

    total = query.count()
    rows = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for user in rows:
        # Count direct invites (level 1)
        level1 = db.query(func.count(User.id)).filter(
            User.parent_id == user.id
        ).scalar() or 0

        # Count indirect invites (level 2)
        level2 = db.query(func.count(User.id)).filter(
            User.grandparent_id == user.id
        ).scalar() or 0

        # Get inviter info
        inviter = None
        if user.parent_id:
            inviter_user = db.query(User).filter(User.id == user.parent_id).first()
            if inviter_user:
                inviter = {
                    'id': inviter_user.id,
                    'username': inviter_user.nickname,
                    'invite_code': inviter_user.invite_code,
                }

        items.append({
            'id': user.id,
            'username': user.nickname,
            'phone': user.phone or '',
            'invite_code': user.invite_code or '',
            'level1_count': level1,
            'level2_count': level2,
            'total_invites': level1 + level2,
            'inviter': inviter,
            'created_at': iso_datetime(user.created_at),
        })

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        }
    }


@admin_router.get('/records')
def list_invite_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    level: int | None = Query(default=None, ge=1, le=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = db.query(User)

    if level == 1:
        query = query.filter(User.parent_id.isnot(None), User.grandparent_id.is_(None))
    elif level == 2:
        query = query.filter(User.grandparent_id.isnot(None))

    if keyword:
        query = query.filter(
            or_(
                User.nickname.contains(keyword),
                User.phone.contains(keyword)
            )
        )

    total = query.count()
    rows = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for user in rows:
        inviter = None
        if user.parent_id:
            inviter_user = db.query(User).filter(User.id == user.parent_id).first()
            if inviter_user:
                inviter = {
                    'id': inviter_user.id,
                    'username': inviter_user.nickname,
                }

        grand_inviter = None
        if user.grandparent_id:
            grand_user = db.query(User).filter(User.id == user.grandparent_id).first()
            if grand_user:
                grand_inviter = {
                    'id': grand_user.id,
                    'username': grand_user.nickname,
                }

        items.append({
            'id': user.id,
            'username': user.nickname,
            'phone': user.phone or '',
            'invite_level': 1 if user.grandparent_id is None else 2,
            'inviter': inviter,
            'grand_inviter': grand_inviter,
            'created_at': iso_datetime(user.created_at),
        })

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        }
    }


@admin_router.get('/tree/{user_id}')
def get_user_invite_tree(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        return {'code': 404, 'message': 'User not found', 'data': None}

    # Get level 1 invites
    level1 = db.query(User).filter(User.parent_id == user_id).all()

    # Get level 2 invites
    level1_ids = [u.id for u in level1]
    level2 = []
    if level1_ids:
        level2 = db.query(User).filter(User.parent_id.in_(level1_ids)).all()

    def serialize_user(u):
        return {
            'id': u.id,
            'username': u.nickname,
            'phone': u.phone or '',
            'created_at': iso_datetime(u.created_at),
        }

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'user': serialize_user(target_user),
            'level1': [serialize_user(u) for u in level1],
            'level2': [serialize_user(u) for u in level2],
        }
    }
