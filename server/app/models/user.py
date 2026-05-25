from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import BusinessIdentity, GlobalRole, UserStatus


class User(TimestampMixin, Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
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


class UserLegacyProfile(Base):
    __tablename__ = 'user_legacy_profiles'

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    legacy_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    dept_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    user_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nick_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phonenumber: Mapped[str | None] = mapped_column(String(20), nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(8), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pay_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    del_flag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    login_ip: Mapped[str | None] = mapped_column(String(128), nullable=True)
    login_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    create_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    update_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    superior: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    union_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    applet_qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wx_qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zfb_qr_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zfb_nick_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    zfb_avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zfb_open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    zfb_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    store_zfb_nick_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    store_zfb_avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    store_zfb_open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    divide_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partner: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sheng_withdraw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class InviteRecord(Base):
    __tablename__ = 'invite_records'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    inviter_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    invitee_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    level: Mapped[int] = mapped_column(nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
