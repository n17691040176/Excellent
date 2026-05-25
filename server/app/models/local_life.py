from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MerchantStatus(str):
    PENDING = 'PENDING'
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class LocalLifeMerchant(TimestampMixin, Base):
    __tablename__ = 'local_life_merchants'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    merchant_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category_name: Mapped[str] = mapped_column(String(64), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    city_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='PENDING')


class MerchantStore(Base):
    __tablename__ = 'merchant_stores'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey('local_life_merchants.id'), nullable=False)
    store_name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    province: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(DECIMAL(10, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='ACTIVE')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class LocalLifeService(Base):
    __tablename__ = 'local_life_services'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey('local_life_merchants.id'), nullable=False)
    store_id: Mapped[int | None] = mapped_column(ForeignKey('merchant_stores.id'), nullable=True)
    service_name: Mapped[str] = mapped_column(String(150), nullable=False)
    market_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    sale_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    service_type: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='ON_SHELF')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class LocalLifeOrder(Base):
    __tablename__ = 'local_life_orders'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), unique=True, nullable=False)
    merchant_id: Mapped[int] = mapped_column(ForeignKey('local_life_merchants.id'), nullable=False)
    store_id: Mapped[int | None] = mapped_column(ForeignKey('merchant_stores.id'), nullable=True)
    service_id: Mapped[int] = mapped_column(ForeignKey('local_life_services.id'), nullable=False)
    verification_code: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MerchantCommissionRule(TimestampMixin, Base):
    __tablename__ = 'merchant_commission_rules'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey('local_life_merchants.id'), nullable=True)
    county_agent_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    city_agent_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    user_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    merchant_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    device_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    ad_rate: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class DeviceRevenueFlow(Base):
    __tablename__ = 'device_revenue_flows'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False)
    business_ref_no: Mapped[str] = mapped_column(String(64), nullable=False)
    beneficiary_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    source_desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AdRevenueFlow(Base):
    __tablename__ = 'ad_revenue_flows'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ad_ref_no: Mapped[str] = mapped_column(String(64), nullable=False)
    beneficiary_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    source_desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
