from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.asset import UserAssetAccount
from app.models.commission import UserCommission
from app.models.enums import AssetType, GlobalRole, UserStatus
from app.models.user import InviteRecord, User
from app.services.asset_service import init_user_assets
from app.utils.helpers import generate_code, now


class AuthService:
    @staticmethod
    def register(db: Session, phone: str, password: str, nickname: str, invite_code: str | None = None) -> tuple[str, User]:
        existing = db.query(User).filter(User.phone == phone).first()
        if existing:
            raise ConflictError('Phone already registered')

        parent = db.query(User).filter(User.invite_code == invite_code).first() if invite_code else None
        user = User(
            phone=phone,
            password_hash=hash_password(password),
            nickname=nickname,
            global_role=GlobalRole.USER,
            status=UserStatus.ENABLED,
            invite_code=generate_code(length=8),
            parent_id=parent.id if parent else None,
            grandparent_id=parent.parent_id if parent else None,
        )
        db.add(user)
        db.flush()

        if parent:
            db.add(
                InviteRecord(
                    inviter_user_id=parent.id,
                    invitee_user_id=user.id,
                    level=1,
                    invite_code=invite_code or '',
                    bound_at=now(),
                )
            )
            if parent.parent_id:
                db.add(
                    InviteRecord(
                        inviter_user_id=parent.parent_id,
                        invitee_user_id=user.id,
                        level=2,
                        invite_code=invite_code or '',
                        bound_at=now(),
                    )
                )

        db.add(UserCommission(user_id=user.id, updated_at=now()))
        init_user_assets(db, user.id)
        db.commit()
        db.refresh(user)
        token = create_access_token(str(user.id), {'role': user.global_role.value})
        return token, user

    @staticmethod
    def login(db: Session, phone: str, password: str, admin_only: bool = False) -> tuple[str, User]:
        user = db.query(User).filter(User.phone == phone).first()
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError('Phone or password invalid')
        if user.status != UserStatus.ENABLED:
            raise UnauthorizedError('Account disabled')
        if admin_only and user.global_role not in {GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN}:
            raise UnauthorizedError('Admin account required')

        user.last_login_at = now()
        db.commit()
        token = create_access_token(str(user.id), {'role': user.global_role.value})
        return token, user

    @staticmethod
    def reset_password(db: Session, phone: str, new_password: str) -> None:
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            raise UnauthorizedError('User not found')
        user.password_hash = hash_password(new_password)
        db.commit()
