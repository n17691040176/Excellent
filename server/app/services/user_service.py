from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import UserStatus
from app.models.user import InviteRecord, User
from app.services.admin_scope import AdminScopeService


class UserService:
    @staticmethod
    def update_profile(db: Session, current_user: User, payload: dict) -> User:
        for field, value in payload.items():
            if value is not None and hasattr(current_user, field):
                setattr(current_user, field, value)
        db.commit()
        db.refresh(current_user)
        return current_user

    @staticmethod
    def list_users(db: Session, current_user: User) -> list[User]:
        query = db.query(User)
        if not AdminScopeService.is_super_admin(current_user):
            query = query.filter(User.team_id == AdminScopeService.require_team_id(current_user))
        return query.order_by(User.id.desc()).all()

    @staticmethod
    def get_user(db: Session, user_id: int, current_user: User | None = None) -> User:
        user = db.get(User, user_id)
        if not user:
            raise NotFoundError('User not found')
        if current_user:
            AdminScopeService.ensure_user_visible(current_user, user)
        return user

    @staticmethod
    def update_user_status(db: Session, user_id: int, status: UserStatus) -> User:
        user = UserService.get_user(db, user_id)
        user.status = status
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_invite_tree(db: Session, user_id: int, current_user: User | None = None) -> dict:
        user = UserService.get_user(db, user_id, current_user)
        level1 = db.query(User).filter(User.parent_id == user.id).all()
        level2 = db.query(User).filter(User.grandparent_id == user.id).all()
        if current_user and not AdminScopeService.is_super_admin(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            level1 = [item for item in level1 if item.team_id == team_id]
            level2 = [item for item in level2 if item.team_id == team_id]
        return {
            'user_id': user.id,
            'phone': user.phone,
            'level1': [{'id': item.id, 'phone': item.phone, 'nickname': item.nickname} for item in level1],
            'level2': [{'id': item.id, 'phone': item.phone, 'nickname': item.nickname} for item in level2],
        }
