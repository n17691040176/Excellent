from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password, verify_password
from app.models.admin_role import AdminRole, AdminRolePermission
from app.models.enums import GlobalRole, UserStatus
from app.models.team import Team
from app.models.user import AdminUserPermission, User
from app.services.admin_permission_service import (
    CONFIGURED_KEY,
    DEFAULT_TEAM_ADMIN_PERMISSIONS,
    AdminPermissionService,
)
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import init_user_assets
from app.models.commission import UserCommission
from app.utils.helpers import generate_code, iso_datetime, now


class AdminRbacService:
    SYSTEM_TEAM_ROLE_CODE = 'TEAM_ADMIN'

    @staticmethod
    def ensure_system_roles(db: Session) -> None:
        role = db.query(AdminRole).filter(AdminRole.code == AdminRbacService.SYSTEM_TEAM_ROLE_CODE).first()
        if not role:
            role = AdminRole(
                code=AdminRbacService.SYSTEM_TEAM_ROLE_CODE,
                name='团队管理员',
                description='兼容原团队管理员：按所属团队隔离经营数据。',
                data_scope='TEAM',
                status='ENABLED',
                is_system=True,
            )
            db.add(role)
            db.flush()
            AdminRbacService._replace_permissions(db, role.id, sorted(DEFAULT_TEAM_ADMIN_PERMISSIONS))

        configured_user_ids = {
            row[0]
            for row in db.query(AdminUserPermission.user_id).filter(
                AdminUserPermission.permission_key == CONFIGURED_KEY,
            ).all()
        }
        query = db.query(User).filter(
            User.global_role == GlobalRole.TEAM_ADMIN,
            User.admin_role_id.is_(None),
        )
        if configured_user_ids:
            query = query.filter(User.id.notin_(configured_user_ids))
        query.update({User.admin_role_id: role.id}, synchronize_session=False)
        db.commit()

    @staticmethod
    def _replace_permissions(db: Session, role_id: int, permission_keys: list[str]) -> list[str]:
        allowed = AdminPermissionService.all_permission_keys()
        cleaned = sorted({key for key in permission_keys if key in allowed})
        db.query(AdminRolePermission).filter(AdminRolePermission.role_id == role_id).delete()
        for key in cleaned:
            db.add(AdminRolePermission(role_id=role_id, permission_key=key))
        return cleaned

    @staticmethod
    def _role(db: Session, role_id: int, enabled_only: bool = False) -> AdminRole:
        role = db.get(AdminRole, role_id)
        if not role:
            raise NotFoundError('Admin role not found')
        if enabled_only and role.status != 'ENABLED':
            raise ConflictError('Admin role disabled')
        return role

    @staticmethod
    def _role_permissions(db: Session, role_id: int) -> list[str]:
        rows = db.query(AdminRolePermission.permission_key).filter(
            AdminRolePermission.role_id == role_id,
        ).all()
        return sorted({row[0] for row in rows})

    @staticmethod
    def serialize_role(db: Session, role: AdminRole) -> dict:
        return {
            'id': role.id,
            'code': role.code,
            'name': role.name,
            'description': role.description,
            'data_scope': role.data_scope,
            'status': role.status,
            'is_system': role.is_system,
            'permissions': AdminRbacService._role_permissions(db, role.id),
            'user_count': int(db.query(func.count(User.id)).filter(User.admin_role_id == role.id).scalar() or 0),
            'created_at': iso_datetime(role.created_at),
            'updated_at': iso_datetime(role.updated_at),
        }

    @staticmethod
    def list_roles(db: Session, current_user: User, enabled_only: bool = False) -> list[dict]:
        query = db.query(AdminRole)
        if enabled_only:
            query = query.filter(AdminRole.status == 'ENABLED')
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(AdminRole.data_scope == 'TEAM', AdminRole.status == 'ENABLED')
        return [AdminRbacService.serialize_role(db, role) for role in query.order_by(AdminRole.id.asc()).all()]

    @staticmethod
    def get_role(db: Session, current_user: User, role_id: int) -> dict:
        role = AdminRbacService._role(db, role_id)
        if not AdminScopeService.has_global_scope(current_user) and role.data_scope != 'TEAM':
            raise ForbiddenError('No permission to view this role')
        return AdminRbacService.serialize_role(db, role)

    @staticmethod
    def _require_global_scope(current_user: User) -> None:
        if not AdminScopeService.has_global_scope(current_user):
            raise ForbiddenError('Global data scope required')

    @staticmethod
    def create_role(db: Session, current_user: User, payload: dict) -> dict:
        AdminRbacService._require_global_scope(current_user)
        code = payload['code'].strip().upper()
        name = payload['name'].strip()
        if code in {'SUPER_ADMIN', 'USER'}:
            raise ConflictError('Role code reserved')
        if db.query(AdminRole.id).filter((AdminRole.code == code) | (AdminRole.name == name)).first():
            raise ConflictError('Role code or name already exists')
        role = AdminRole(
            code=code,
            name=name,
            description=payload.get('description'),
            data_scope=payload.get('data_scope', 'TEAM'),
            status='ENABLED',
            is_system=False,
            created_by=current_user.id,
        )
        db.add(role)
        db.flush()
        AdminRbacService._replace_permissions(db, role.id, payload.get('permissions', []))
        db.commit()
        db.refresh(role)
        return AdminRbacService.serialize_role(db, role)

    @staticmethod
    def update_role(db: Session, current_user: User, role_id: int, payload: dict) -> dict:
        AdminRbacService._require_global_scope(current_user)
        role = AdminRbacService._role(db, role_id)
        if role.is_system and payload.get('data_scope') not in {None, role.data_scope}:
            raise ConflictError('System role data scope cannot be changed')
        name = payload.get('name')
        if name is not None:
            name = name.strip()
            duplicate = db.query(AdminRole.id).filter(AdminRole.name == name, AdminRole.id != role.id).first()
            if duplicate:
                raise ConflictError('Role name already exists')
            role.name = name
        for field in ('description', 'data_scope', 'status'):
            if field in payload and payload[field] is not None:
                setattr(role, field, payload[field])
        if payload.get('permissions') is not None:
            AdminRbacService._replace_permissions(db, role.id, payload['permissions'])
        db.commit()
        db.refresh(role)
        return AdminRbacService.serialize_role(db, role)

    @staticmethod
    def delete_role(db: Session, current_user: User, role_id: int) -> None:
        AdminRbacService._require_global_scope(current_user)
        role = AdminRbacService._role(db, role_id)
        if role.is_system:
            raise ConflictError('System role cannot be deleted')
        if db.query(User.id).filter(User.admin_role_id == role.id).first():
            raise ConflictError('Role is assigned to administrators')
        db.query(AdminRolePermission).filter(AdminRolePermission.role_id == role.id).delete()
        db.delete(role)
        db.commit()

    @staticmethod
    def _serialize_admin(db: Session, user: User) -> dict:
        role = user.admin_role
        role_payload = {
            'id': role.id,
            'code': role.code,
            'name': role.name,
            'data_scope': role.data_scope,
            'status': role.status,
        } if role else ({
            'id': None,
            'code': 'SUPER_ADMIN',
            'name': '超级管理员',
            'data_scope': 'ALL',
            'status': 'ENABLED',
        } if user.global_role == GlobalRole.SUPER_ADMIN else None)
        return {
            'id': user.id,
            'phone': user.phone,
            'nickname': user.nickname,
            'global_role': user.global_role.value,
            'role': role_payload,
            'admin_role': role_payload,
            'team_id': user.team_id,
            'status': user.status.value,
            'permissions': AdminPermissionService.effective_permissions(db, user),
            'last_login_at': iso_datetime(user.last_login_at),
            'created_at': iso_datetime(user.created_at),
        }

    @staticmethod
    def list_admins(db: Session, current_user: User, keyword: str | None = None) -> list[dict]:
        query = db.query(User).filter(User.global_role.in_([GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN]))
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(User.team_id == AdminScopeService.require_team_id(current_user))
        if keyword:
            term = f'%{keyword.strip()}%'
            query = query.filter((User.phone.ilike(term)) | (User.nickname.ilike(term)))
        return [AdminRbacService._serialize_admin(db, user) for user in query.order_by(User.id.asc()).all()]

    @staticmethod
    def list_candidates(db: Session, current_user: User, keyword: str | None = None) -> list[dict]:
        query = db.query(User).filter(User.global_role == GlobalRole.USER)
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(User.team_id == AdminScopeService.require_team_id(current_user))
        if keyword:
            term = f'%{keyword.strip()}%'
            query = query.filter((User.phone.ilike(term)) | (User.nickname.ilike(term)))
        return [
            {
                'id': user.id,
                'phone': user.phone,
                'nickname': user.nickname,
                'team_id': user.team_id,
                'status': user.status.value,
            }
            for user in query.order_by(User.id.desc()).limit(100).all()
        ]

    @staticmethod
    def list_assignable_teams(db: Session, current_user: User) -> list[dict]:
        query = db.query(Team)
        if not AdminScopeService.has_global_scope(current_user):
            query = query.filter(Team.id == AdminScopeService.require_team_id(current_user))
        return [
            {'id': team.id, 'name': team.name, 'status': team.status.value}
            for team in query.order_by(Team.id.asc()).all()
        ]

    @staticmethod
    def _validate_assignment(db: Session, current_user: User, role_id: int, team_id: int | None) -> tuple[AdminRole, int | None]:
        role = AdminRbacService._role(db, role_id, enabled_only=True)
        if not AdminScopeService.has_global_scope(current_user):
            if role.data_scope != 'TEAM':
                raise ForbiddenError('Team scoped administrator can only assign team roles')
            team_id = AdminScopeService.require_team_id(current_user)
        if role.data_scope == 'TEAM':
            if not team_id:
                raise ConflictError('Team role requires a team')
            if not db.get(Team, team_id):
                raise NotFoundError('Team not found')
        return role, team_id

    @staticmethod
    def create_admin(db: Session, current_user: User, payload: dict) -> dict:
        role, team_id = AdminRbacService._validate_assignment(
            db, current_user, payload['role_id'], payload.get('team_id'),
        )
        phone = payload['phone'].strip()
        if db.query(User.id).filter(User.phone == phone).first():
            raise ConflictError('Phone already registered; promote the existing user instead')
        user = User(
            phone=phone,
            password_hash=hash_password(payload['password']),
            nickname=payload['nickname'].strip(),
            global_role=GlobalRole.TEAM_ADMIN,
            admin_role_id=role.id,
            status=UserStatus.ENABLED,
            invite_code=generate_code(length=8),
            team_id=team_id,
            is_phone_verified=True,
        )
        db.add(user)
        db.flush()
        db.add(UserCommission(user_id=user.id, updated_at=now()))
        init_user_assets(db, user.id)
        db.commit()
        db.refresh(user)
        return AdminRbacService._serialize_admin(db, user)

    @staticmethod
    def promote_user(db: Session, current_user: User, payload: dict) -> dict:
        user = db.get(User, payload['user_id'])
        if not user:
            raise NotFoundError('User not found')
        if user.global_role != GlobalRole.USER:
            raise ConflictError('User is already an administrator')
        if not AdminScopeService.has_global_scope(current_user):
            AdminScopeService.ensure_user_visible(current_user, user)
        role, team_id = AdminRbacService._validate_assignment(
            db, current_user, payload['role_id'], payload.get('team_id') or user.team_id,
        )
        user.global_role = GlobalRole.TEAM_ADMIN
        user.admin_role_id = role.id
        user.team_id = team_id
        user.status = UserStatus.ENABLED
        db.commit()
        db.refresh(user)
        return AdminRbacService._serialize_admin(db, user)

    @staticmethod
    def _manageable_admin(db: Session, current_user: User, user_id: int) -> User:
        user = db.get(User, user_id)
        if not user or user.global_role not in {GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN}:
            raise NotFoundError('Administrator not found')
        if user.global_role == GlobalRole.SUPER_ADMIN:
            raise ForbiddenError('Root super administrator cannot be changed here')
        if not AdminScopeService.has_global_scope(current_user):
            AdminScopeService.ensure_user_visible(current_user, user)
        return user

    @staticmethod
    def update_admin(db: Session, current_user: User, user_id: int, payload: dict) -> dict:
        user = AdminRbacService._manageable_admin(db, current_user, user_id)
        role_id = payload.get('role_id', user.admin_role_id)
        team_id = payload.get('team_id', user.team_id)
        role, team_id = AdminRbacService._validate_assignment(db, current_user, role_id, team_id)
        if payload.get('nickname') is not None:
            user.nickname = payload['nickname'].strip()
        user.admin_role_id = role.id
        user.team_id = team_id
        db.commit()
        db.refresh(user)
        return AdminRbacService._serialize_admin(db, user)

    @staticmethod
    def update_admin_status(db: Session, current_user: User, user_id: int, status: str) -> dict:
        user = AdminRbacService._manageable_admin(db, current_user, user_id)
        if user.id == current_user.id and status == 'DISABLED':
            raise ConflictError('Cannot disable your own account')
        user.status = UserStatus(status)
        db.commit()
        db.refresh(user)
        return AdminRbacService._serialize_admin(db, user)

    @staticmethod
    def reset_admin_password(db: Session, current_user: User, user_id: int, new_password: str) -> None:
        user = AdminRbacService._manageable_admin(db, current_user, user_id)
        user.password_hash = hash_password(new_password)
        db.commit()

    @staticmethod
    def demote_admin(db: Session, current_user: User, user_id: int) -> None:
        user = AdminRbacService._manageable_admin(db, current_user, user_id)
        if user.id == current_user.id:
            raise ConflictError('Cannot demote your own account')
        user.global_role = GlobalRole.USER
        user.admin_role_id = None
        db.query(AdminUserPermission).filter(AdminUserPermission.user_id == user.id).delete()
        db.commit()

    @staticmethod
    def profile(db: Session, user: User) -> dict:
        data = AdminRbacService._serialize_admin(db, user)
        data.update({
            'avatar': user.avatar,
            'real_name': user.real_name,
            'member_level': user.member_level.value,
            'member_level_name': user.member_level.label,
        })
        return data

    @staticmethod
    def update_profile(db: Session, user: User, payload: dict) -> dict:
        for field, value in payload.items():
            if value is not None:
                setattr(user, field, value)
        db.commit()
        db.refresh(user)
        return AdminRbacService.profile(db, user)

    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ConflictError('Current password invalid')
        user.password_hash = hash_password(new_password)
        db.commit()
