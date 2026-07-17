from sqlalchemy import Select, select

from app.core.exceptions import ForbiddenError
from app.models.enums import GlobalRole
from app.models.user import User


class AdminScopeService:
    @staticmethod
    def is_super_admin(current_user: User) -> bool:
        return current_user.global_role == GlobalRole.SUPER_ADMIN

    @staticmethod
    def is_team_admin(current_user: User) -> bool:
        return current_user.global_role == GlobalRole.TEAM_ADMIN

    @staticmethod
    def has_global_scope(current_user: User) -> bool:
        if AdminScopeService.is_super_admin(current_user):
            return True
        role = getattr(current_user, 'admin_role', None)
        return bool(role and role.status == 'ENABLED' and role.data_scope == 'ALL')

    @staticmethod
    def require_team_id(current_user: User) -> int:
        if AdminScopeService.has_global_scope(current_user):
            return current_user.team_id or 0
        if not current_user.team_id:
            raise ForbiddenError('Team admin not bound to a team')
        return current_user.team_id

    @staticmethod
    def team_user_ids_subquery(current_user: User) -> Select:
        team_id = AdminScopeService.require_team_id(current_user)
        return select(User.id).where(User.team_id == team_id)

    @staticmethod
    def ensure_user_visible(current_user: User, target_user: User) -> None:
        if AdminScopeService.has_global_scope(current_user):
            return
        team_id = AdminScopeService.require_team_id(current_user)
        if target_user.team_id != team_id:
            raise ForbiddenError('No permission to access cross-team user data')

    @staticmethod
    def ensure_team_visible(current_user: User, team_id: int | None) -> None:
        if AdminScopeService.has_global_scope(current_user):
            return
        scoped_team_id = AdminScopeService.require_team_id(current_user)
        if team_id != scoped_team_id:
            raise ForbiddenError('No permission to access cross-team data')
