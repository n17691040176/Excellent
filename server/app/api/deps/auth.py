from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import GlobalRole, UserStatus
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


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


def require_roles(*roles: GlobalRole):
    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if roles and current_user.global_role not in roles:
            raise ForbiddenError('No permission')
        return current_user

    return _dependency
