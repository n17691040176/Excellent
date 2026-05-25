from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import AgentLevelCode, QualificationStatus, SupplierStatus


class Supplier(TimestampMixin, Base):
    __tablename__ = 'suppliers'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(64), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    qualification_desc: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    entry_fee_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    entry_fee_paid: Mapped[bool] = mapped_column(default=False, nullable=False)
    referral_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    status: Mapped[SupplierStatus] = mapped_column(Enum(SupplierStatus), default=SupplierStatus.PENDING, nullable=False)


class SupplierEntryOrder(Base):
    __tablename__ = 'supplier_entry_orders'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'), nullable=False)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    base_product_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    entry_fee_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    referral_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    referral_reward_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SupplierAgreement(Base):
    __tablename__ = 'supplier_agreements'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'), nullable=False)
    agreement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SupplierReferralReward(Base):
    __tablename__ = 'supplier_referral_rewards'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey('suppliers.id'), nullable=False)
    referral_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    entry_order_id: Mapped[int] = mapped_column(ForeignKey('supplier_entry_orders.id'), nullable=False)
    reward_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=15.00)
    reward_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AgentLevel(TimestampMixin, Base):
    __tablename__ = 'agent_levels'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    level_code: Mapped[AgentLevelCode] = mapped_column(Enum(AgentLevelCode), unique=True, nullable=False)
    level_name: Mapped[str] = mapped_column(String(64), nullable=False)
    max_product_count: Mapped[int] = mapped_column(nullable=False)
    requires_agreement: Mapped[bool] = mapped_column(default=True, nullable=False)


class AgentQualification(Base):
    __tablename__ = 'agent_qualifications'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    agent_level_id: Mapped[int] = mapped_column(ForeignKey('agent_levels.id'), nullable=False)
    qualification_status: Mapped[QualificationStatus] = mapped_column(
        Enum(QualificationStatus),
        default=QualificationStatus.PENDING,
        nullable=False,
    )
    product_quota: Mapped[int] = mapped_column(nullable=False)
    used_quota: Mapped[int] = mapped_column(default=0, nullable=False)
    agreement_signed: Mapped[bool] = mapped_column(default=False, nullable=False)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
