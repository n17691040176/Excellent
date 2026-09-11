from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import CityPartnerRotationStatus, CityPartnerSeatStatus, CommissionMode, CommissionStatus


class CityPartnerSeat(TimestampMixin, Base):
    """One configurable city seat; only one current holder is allowed per province/city."""

    __tablename__ = 'city_partner_seats'
    __table_args__ = (UniqueConstraint('province', 'city', name='uq_city_partner_seats_province_city'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    province: Mapped[str] = mapped_column(String(64), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    current_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    current_order_id: Mapped[int | None] = mapped_column(ForeignKey('orders.id'), nullable=True)
    initial_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    current_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    price_growth_rate: Mapped[Decimal] = mapped_column(DECIMAL(7, 4), nullable=False, default=0)
    price_cap: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    price_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False, default='city-partner-v1')
    rotation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    term_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[CityPartnerSeatStatus] = mapped_column(
        Enum(CityPartnerSeatStatus),
        nullable=False,
        default=CityPartnerSeatStatus.ACTIVE,
    )


class CityPartnerRotationFlow(TimestampMixin, Base):
    """Auditable settlement record for a city-partner seat purchase/rotation."""

    __tablename__ = 'city_partner_rotation_flows'
    __table_args__ = (UniqueConstraint('seat_id', 'order_id', name='uq_city_partner_rotation_seat_order'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey('city_partner_seats.id'), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False, index=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False)
    province: Mapped[str] = mapped_column(String(64), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    new_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    new_user_parent_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    previous_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    new_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    appreciation_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    principal_refund_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    appreciation_reward_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    company_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    parent_reward_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    operations_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    price_version_before: Mapped[int] = mapped_column(Integer, nullable=False)
    price_version_after: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_rule_version: Mapped[str] = mapped_column(String(64), nullable=False, default='v1')
    status: Mapped[CityPartnerRotationStatus] = mapped_column(
        Enum(CityPartnerRotationStatus),
        nullable=False,
        default=CityPartnerRotationStatus.PENDING,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CityPartnerCommissionFlow(Base):
    """Independent product commission ledger for CITY_PARTNER orders."""

    __tablename__ = 'city_partner_commission_flows'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False, index=True)
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey('order_items.id'), nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False, index=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False)
    commission_mode: Mapped[CommissionMode] = mapped_column(
        Enum(CommissionMode),
        nullable=False,
        default=CommissionMode.CITY_PARTNER,
    )
    commission_rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    province: Mapped[str] = mapped_column(String(64), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    city_partner_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    beneficiary_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    beneficiary_account: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    commission_role: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_sale_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    unit_cost_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    profit_pool_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    calculated_amount: Mapped[Decimal] = mapped_column(DECIMAL(48, 26), nullable=False)
    calculation_precision_known: Mapped[bool] = mapped_column(default=True, server_default='0', nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    remainder_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False, default=0)
    status: Mapped[CommissionStatus] = mapped_column(Enum(CommissionStatus), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CityPartnerPurchase(Base):
    __tablename__ = 'city_partner_purchases'

    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), primary_key=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey('city_partner_seats.id'), nullable=False, index=True)
    price_version: Mapped[int] = mapped_column(Integer, nullable=False)
    quoted_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    settlement_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
