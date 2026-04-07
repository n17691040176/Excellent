from datetime import datetime

from sqlalchemy import BigInteger, DECIMAL, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ProductStatus, ProductType, ZoneType


class Package(TimestampMixin, Base):
    __tablename__ = 'packages'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    package_name: Mapped[str] = mapped_column(String(100), nullable=False)
    package_price: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    package_type: Mapped[str] = mapped_column(String(32), nullable=False)
    voucher_reward_rate: Mapped[float] = mapped_column(DECIMAL(5, 2), default=100.00, nullable=False)
    referral_voucher_rate: Mapped[float] = mapped_column(DECIMAL(5, 2), default=50.00, nullable=False)
    ai_coupon_max_deduct_rate: Mapped[float] = mapped_column(DECIMAL(5, 2), default=20.00, nullable=False)
    grants_product_quota: Mapped[int] = mapped_column(default=0, nullable=False)
    points_subsidy_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.ON_SHELF, nullable=False)


class PackageBenefit(Base):
    __tablename__ = 'package_benefits'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    package_id: Mapped[int] = mapped_column(ForeignKey('packages.id'), nullable=False)
    benefit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    benefit_value: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
