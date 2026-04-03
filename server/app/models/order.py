from datetime import datetime

from sqlalchemy import BigInteger, DECIMAL, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import OrderStatus, OrderType, PayStatus, ZoneType


class Order(TimestampMixin, Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType), nullable=False)
    zone_type: Mapped[ZoneType | None] = mapped_column(Enum(ZoneType), nullable=True)
    source_ref_id: Mapped[int | None] = mapped_column(nullable=True)
    total_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    payable_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    paid_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    pay_status: Mapped[PayStatus] = mapped_column(Enum(PayStatus), default=PayStatus.UNPAID, nullable=False)
    order_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.CREATED, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OrderItem(Base):
    __tablename__ = 'order_items'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey('product_skus.id'), nullable=True)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sku_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    total_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OrderAssetDeduction(Base):
    __tablename__ = 'order_asset_deductions'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    deduct_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    deduct_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
