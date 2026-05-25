from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CommissionStatus, WithdrawStatus, WithdrawType


class CommissionConfig(Base):
    __tablename__ = 'commission_configs'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    level1_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=5.00)
    level2_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=2.00)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserCommission(Base):
    __tablename__ = 'user_commissions'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, nullable=False)
    frozen_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    available_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    withdrawn_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CommissionFlow(Base):
    __tablename__ = 'commission_flows'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    beneficiary_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    source_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
    level: Mapped[int] = mapped_column(nullable=False)
    rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    status: Mapped[CommissionStatus] = mapped_column(Enum(CommissionStatus), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WithdrawRequest(Base):
    __tablename__ = 'withdraw_requests'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
    withdraw_type: Mapped[WithdrawType] = mapped_column(Enum(WithdrawType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    status: Mapped[WithdrawStatus] = mapped_column(Enum(WithdrawStatus), default=WithdrawStatus.PENDING, nullable=False)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
