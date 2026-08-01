import pytest
from pydantic import ValidationError
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.exceptions import UnauthorizedError
from app.db.base import Base
from app.models.enums import GlobalRole, UserStatus
from app.models.user import User
from app.schemas.auth import AppLoginRequest
from app.services.auth_service import AuthService


@compiles(BigInteger, 'sqlite')
def compile_big_integer_as_integer(_element, _compiler, **_kwargs):
    return 'INTEGER'


@pytest.fixture
def db(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    monkeypatch.setattr('app.services.auth_service.init_user_assets', lambda _db, _user_id: None)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_app_phone_login_registers_then_reuses_the_same_user(db: Session):
    token, user, is_new_user = AuthService.login_or_register_app_user(db, '17612345678')

    assert token
    assert is_new_user is True
    assert user.phone == '17612345678'
    assert user.nickname == '用户5678'
    assert user.is_phone_verified is True
    assert user.last_login_at is not None

    second_token, second_user, is_new_user = AuthService.login_or_register_app_user(db, '17612345678')

    assert second_token
    assert is_new_user is False
    assert second_user.id == user.id
    assert db.query(User).filter(User.phone == '17612345678').count() == 1


def test_app_phone_login_rejects_a_disabled_user(db: Session):
    user = User(
        phone='17612345678',
        password_hash='unused',
        nickname='禁用用户',
        global_role=GlobalRole.USER,
        status=UserStatus.DISABLED,
        invite_code='DISABLED',
    )
    db.add(user)
    db.commit()

    with pytest.raises(UnauthorizedError, match='Account disabled'):
        AuthService.login_or_register_app_user(db, user.phone)


@pytest.mark.parametrize('phone', ['176xxxxxxxx', '12345678901', '1761234567a', ''])
def test_app_phone_login_validates_mainland_mobile_number(phone: str):
    with pytest.raises(ValidationError):
        AppLoginRequest(phone=phone)


def test_app_phone_login_normalizes_surrounding_whitespace():
    payload = AppLoginRequest(phone=' 17612345678 ')

    assert payload.phone == '17612345678'
