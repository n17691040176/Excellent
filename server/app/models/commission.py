from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CommissionStatus, WithdrawStatus, WithdrawType


class CommissionConfig(Base):
    __tablename__ = 'commission_configs'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    level1_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    level2_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    withdraw_fee_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    withdraw_min_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=1)
    withdraw_max_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=50000)
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
    fee_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    fee_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    net_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    bank_card_id: Mapped[int | None] = mapped_column(ForeignKey('user_bank_cards.id'), nullable=True)
    bank_holder_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_branch_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_card_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_card_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    status: Mapped[WithdrawStatus] = mapped_column(Enum(WithdrawStatus), default=WithdrawStatus.PENDING, nullable=False)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    review_remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CommissionAccountLedger(Base):
    __tablename__ = 'commission_account_ledgers'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    withdraw_request_id: Mapped[int] = mapped_column(ForeignKey('withdraw_requests.id'), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    available_before: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    available_after: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    frozen_before: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    frozen_after: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    withdrawn_before: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    withdrawn_after: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
