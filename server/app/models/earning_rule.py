from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EarningRule(TimestampMixin, Base):
    __tablename__ = 'earning_rules'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey('products.id'), nullable=True, index=True)
    member_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    commission_level: Mapped[int | None] = mapped_column(nullable=True, index=True)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False, default='USER')
    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False)
    calculation_basis: Mapped[str] = mapped_column(String(128), nullable=False)
    calculation_method: Mapped[str] = mapped_column(String(32), nullable=False)
    reward_rate: Mapped[Decimal] = mapped_column(DECIMAL(7, 4), nullable=False, default=0)
    reward_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    cap_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    min_condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qualification_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    settlement_cycle: Mapped[str] = mapped_column(String(32), nullable=False, default='MONTHLY')
    settlement_delay_days: Mapped[int] = mapped_column(nullable=False, default=0)
    freeze_days: Mapped[int] = mapped_column(nullable=False, default=0)
    priority: Mapped[int] = mapped_column(nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    compliance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
