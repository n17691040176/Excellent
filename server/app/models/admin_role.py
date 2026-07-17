from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AdminRole(TimestampMixin, Base):
    __tablename__ = 'admin_roles'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_scope: Mapped[str] = mapped_column(String(16), default='TEAM', nullable=False)
    status: Mapped[str] = mapped_column(String(16), default='ENABLED', nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)


class AdminRolePermission(TimestampMixin, Base):
    __tablename__ = 'admin_role_permissions'
    __table_args__ = (UniqueConstraint('role_id', 'permission_key', name='uq_admin_role_permission'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('admin_roles.id'), nullable=False, index=True)
    permission_key: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
