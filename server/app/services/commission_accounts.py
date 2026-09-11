from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.commission import UserCommission
from app.models.enums import UserStatus
from app.models.user import User
from app.utils.helpers import generate_code, now


def system_account(db: Session, account_type: str) -> User:
    users = db.query(User).filter(User.system_account_type == account_type).with_for_update(read=True).all()
    if len(users) != 1:
        raise ConflictError(f'Exactly one {account_type} settlement account must be configured')
    return users[0]


def ensure_system_accounts(db: Session) -> None:
    """Create non-login internal accounts; never reassign existing account balances."""
    for kind, name in [('COMPANY', '公司结算账户'), ('OPERATIONS', '运维结算账户')]:
        if not db.query(User.id).filter(User.system_account_type == kind).first():
            try:
                with db.begin_nested():
                    db.add(
                        User(
                            nickname=name,
                            password_hash='!',
                            invite_code=generate_code(length=16),
                            status=UserStatus.DISABLED,
                            system_account_type=kind,
                        )
                    )
                    db.flush()
            except IntegrityError:
                # Another startup process may have inserted the unique account.
                # The current read below must find exactly one account or fail.
                pass
        account = system_account(db, kind)
        if not db.query(UserCommission.id).filter(UserCommission.user_id == account.id).first():
            try:
                with db.begin_nested():
                    db.add(UserCommission(user_id=account.id, updated_at=now()))
                    db.flush()
            except IntegrityError:
                if (
                    not db.query(UserCommission.id)
                    .filter(UserCommission.user_id == account.id)
                    .with_for_update()
                    .first()
                ):
                    raise
