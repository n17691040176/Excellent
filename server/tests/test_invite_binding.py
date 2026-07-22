import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.api.v1 import users as users_api
from app.core.exceptions import ConflictError, NotFoundError
from app.db.base import Base
from app.models.enums import BusinessIdentity, GlobalRole, UserStatus
from app.models.user import InviteRecord, User
from app.services.auth_service import AuthService

UserService = users_api.UserService


@compiles(BigInteger, 'sqlite')
def compile_big_integer_as_integer(_element, _compiler, **_kwargs):
    return 'INTEGER'


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def create_user(db: Session, suffix: str, *, parent_id: int | None = None) -> User:
    user = User(
        phone=f'1380000{suffix.zfill(4)}',
        password_hash='test',
        nickname=f'用户{suffix}',
        global_role=GlobalRole.USER,
        business_identity=BusinessIdentity.NORMAL_MEMBER,
        status=UserStatus.ENABLED,
        invite_code=f'INV{suffix.zfill(5)}',
        parent_id=parent_id,
    )
    db.add(user)
    db.flush()
    return user


def test_bind_inviter_writes_direct_and_indirect_relationships(db: Session):
    grandparent = create_user(db, '1')
    inviter = create_user(db, '2', parent_id=grandparent.id)
    invitee = create_user(db, '3')
    existing_child = create_user(db, '4', parent_id=invitee.id)
    db.commit()

    result = UserService.bind_inviter(db, invitee, inviter.invite_code)

    db.refresh(invitee)
    db.refresh(existing_child)
    assert result['already_bound'] is False
    assert invitee.parent_id == inviter.id
    assert invitee.grandparent_id == grandparent.id
    assert existing_child.grandparent_id == inviter.id
    assert {
        (record.inviter_user_id, record.invitee_user_id, record.level)
        for record in db.query(InviteRecord).all()
    } == {
        (inviter.id, invitee.id, 1),
        (grandparent.id, invitee.id, 2),
        (inviter.id, existing_child.id, 2),
    }


def test_repeated_scan_is_idempotent_and_rebinding_is_rejected(db: Session):
    inviter = create_user(db, '1')
    other_inviter = create_user(db, '2')
    invitee = create_user(db, '3')
    db.commit()

    UserService.bind_inviter(db, invitee, inviter.invite_code)
    repeated = UserService.bind_inviter(db, invitee, inviter.invite_code)

    assert repeated['already_bound'] is True
    assert db.query(InviteRecord).count() == 1
    with pytest.raises(ConflictError, match='不能重复绑定'):
        UserService.bind_inviter(db, invitee, other_inviter.invite_code)


def test_self_and_descendant_binding_are_rejected(db: Session):
    user = create_user(db, '1')
    child = create_user(db, '2', parent_id=user.id)
    db.commit()

    with pytest.raises(ConflictError, match='不能绑定自己'):
        UserService.bind_inviter(db, user, user.invite_code)
    with pytest.raises(ConflictError, match='不能绑定自己的下级'):
        UserService.bind_inviter(db, user, child.invite_code)


def test_registration_binds_optional_invite_code_case_insensitively(db: Session, monkeypatch):
    grandparent = create_user(db, '1')
    inviter = create_user(db, '2', parent_id=grandparent.id)
    db.commit()
    monkeypatch.setattr('app.services.auth_service.init_user_assets', lambda _db, _user_id: None)

    invitee = AuthService._create_user(
        db,
        phone='13900000003',
        password='test-password',
        nickname='新用户',
        invite_code=inviter.invite_code.lower(),
    )
    db.commit()

    assert invitee.parent_id == inviter.id
    assert invitee.grandparent_id == grandparent.id
    assert {
        (record.inviter_user_id, record.invitee_user_id, record.level, record.invite_code)
        for record in db.query(InviteRecord).filter(InviteRecord.invitee_user_id == invitee.id).all()
    } == {
        (inviter.id, invitee.id, 1, inviter.invite_code),
        (grandparent.id, invitee.id, 2, inviter.invite_code),
    }


def test_registration_rejects_an_invalid_optional_invite_code(db: Session):
    with pytest.raises(NotFoundError, match='邀请码无效'):
        AuthService._create_user(
            db,
            phone='13900000004',
            password='test-password',
            nickname='新用户',
            invite_code='NOT-FOUND',
        )

    assert db.query(User).filter(User.phone == '13900000004').first() is None
