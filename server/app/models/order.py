from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
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
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    payable_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    pay_status: Mapped[PayStatus] = mapped_column(Enum(PayStatus), default=PayStatus.UNPAID, nullable=False)
    order_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    legacy_total_price: Mapped[float | None] = mapped_column('total_price', DECIMAL(18, 2), nullable=True)
    legacy_pay_price: Mapped[float | None] = mapped_column('pay_price', DECIMAL(18, 2), nullable=True)
    legacy_create_time: Mapped[datetime | None] = mapped_column('create_time', DateTime, nullable=True)
    legacy_create_by: Mapped[int | None] = mapped_column('create_by', BigInteger, nullable=True)
    legacy_update_by: Mapped[int | None] = mapped_column('update_by', BigInteger, nullable=True)
    legacy_update_time: Mapped[datetime | None] = mapped_column('update_time', DateTime, nullable=True)
    legacy_address_id: Mapped[int | None] = mapped_column('address_id', BigInteger, nullable=True)
    legacy_is_delete: Mapped[int | None] = mapped_column('is_delete', Integer, nullable=True)
    legacy_state: Mapped[int | None] = mapped_column('state', Integer, nullable=True)
    legacy_bank_card_id: Mapped[int | None] = mapped_column('bank_card_id', BigInteger, nullable=True)
    legacy_pay_time: Mapped[datetime | None] = mapped_column('pay_time', DateTime, nullable=True)
    legacy_pay_way: Mapped[int | None] = mapped_column('pay_way', Integer, nullable=True)
    legacy_trade_no: Mapped[str | None] = mapped_column('trade_no', String(128), nullable=True)
    legacy_remark: Mapped[str | None] = mapped_column('remark', Text, nullable=True)
    legacy_dept_id: Mapped[int | None] = mapped_column('dept_id', BigInteger, nullable=True)
    legacy_write_off_qr_code: Mapped[str | None] = mapped_column('write_off_qr_code', String(255), nullable=True)
    legacy_order_type: Mapped[int | None] = mapped_column('legacy_order_type', Integer, nullable=True)
    legacy_is_seperate: Mapped[int | None] = mapped_column('is_seperate', Integer, nullable=True)
    legacy_xiaofeijin_price: Mapped[float | None] = mapped_column('xiaofeijin_price', DECIMAL(18, 2), nullable=True)
    legacy_logistics_name: Mapped[str | None] = mapped_column('logistics_name', String(128), nullable=True)
    legacy_logistics_no: Mapped[str | None] = mapped_column('logistics_no', String(128), nullable=True)
    legacy_evaluate: Mapped[int | None] = mapped_column('evaluate', Integer, nullable=True)
    legacy_refund_state: Mapped[int | None] = mapped_column('refund_state', Integer, nullable=True)
    legacy_refund_no: Mapped[str | None] = mapped_column('refund_no', String(128), nullable=True)
    legacy_refund_time: Mapped[datetime | None] = mapped_column('refund_time', DateTime, nullable=True)
    legacy_refund_price: Mapped[float | None] = mapped_column('refund_price', DECIMAL(18, 2), nullable=True)
    legacy_refund_remark: Mapped[str | None] = mapped_column('refund_remark', Text, nullable=True)
    legacy_refund_real_price: Mapped[float | None] = mapped_column('refund_real_price', DECIMAL(18, 2), nullable=True)
    legacy_refund_trade_no: Mapped[str | None] = mapped_column('refund_trade_no', String(128), nullable=True)
    legacy_refund_by: Mapped[int | None] = mapped_column('refund_by', BigInteger, nullable=True)
    legacy_refund_verify_state: Mapped[int | None] = mapped_column('refund_verify_state', Integer, nullable=True)
    legacy_refund_verify_time: Mapped[datetime | None] = mapped_column('refund_verify_time', DateTime, nullable=True)
    legacy_writeoff_by: Mapped[int | None] = mapped_column('writeoff_by', BigInteger, nullable=True)
    legacy_writeoff_time: Mapped[datetime | None] = mapped_column('writeoff_time', DateTime, nullable=True)
    legacy_is_send: Mapped[int | None] = mapped_column('is_send', Integer, nullable=True)
    legacy_order_by: Mapped[int | None] = mapped_column('order_by', BigInteger, nullable=True)
    legacy_is_bonus: Mapped[int | None] = mapped_column('is_bonus', Integer, nullable=True)
    legacy_bonus_amount: Mapped[float | None] = mapped_column('bonus_amount', DECIMAL(18, 2), nullable=True)
    legacy_re_order_by_reason: Mapped[str | None] = mapped_column('re_order_by_reason', String(255), nullable=True)
    legacy_is_re_order_by: Mapped[int | None] = mapped_column('is_re_order_by', Integer, nullable=True)
    legacy_imported_at: Mapped[datetime | None] = mapped_column('legacy_imported_at', DateTime, nullable=True)
    legacy_source_file: Mapped[str | None] = mapped_column('legacy_source_file', String(255), nullable=True)


class OrderStatusView(Base):
    __tablename__ = 'order_status_views'
    __table_args__ = (UniqueConstraint('user_id', 'status_key', name='uq_order_status_views_user_status'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    status_key: Mapped[str] = mapped_column(String(32), nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OrderItem(Base):
    __tablename__ = 'order_items'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey('product_skus.id'), nullable=True)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sku_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OrderAssetDeduction(Base):
    __tablename__ = 'order_asset_deductions'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    deduct_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    deduct_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
