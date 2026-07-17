from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import GlobalRole, UserStatus
from app.models.user import User
from app.services.admin_permission_service import AdminPermissionService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login', auto_error=False)


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload['sub'])
    except Exception as exc:  # noqa: BLE001
        raise UnauthorizedError('Token invalid or expired') from exc

    user = db.get(User, user_id)
    if not user:
        raise UnauthorizedError('User not found')
    if user.status != UserStatus.ENABLED:
        raise ForbiddenError('User disabled')
    return user


def get_current_user_optional(
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme_optional),
) -> User | None:
    """Optional auth: returns None if no valid token provided."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = int(payload['sub'])
    except Exception:  # noqa: BLE001
        return None
    user = db.get(User, user_id)
    if not user or user.status != UserStatus.ENABLED:
        return None
    return user


def require_roles(*roles: GlobalRole):
    def _dependency(
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if roles and current_user.global_role not in roles:
            raise ForbiddenError('No permission')
        if current_user.global_role != GlobalRole.SUPER_ADMIN:
            permission_key = AdminPermissionService.permission_for_request(request.method, request.url.path)
            AdminPermissionService.assert_permission(db, current_user, permission_key)
        return current_user

    return _dependency
