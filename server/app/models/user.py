from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import BusinessIdentity, GlobalRole, UserStatus


class User(TimestampMixin, Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    global_role: Mapped[GlobalRole] = mapped_column(Enum(GlobalRole), default=GlobalRole.USER, nullable=False)
    business_identity: Mapped[BusinessIdentity] = mapped_column(
        Enum(BusinessIdentity),
        default=BusinessIdentity.NORMAL_MEMBER,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ENABLED, nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    grandparent_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
    real_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class InviteRecord(Base):
    __tablename__ = 'invite_records'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inviter_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    invitee_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    level: Mapped[int] = mapped_column(nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
