from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, JSON, BigInteger, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import PaymentChannel, PaymentStatus


class PaymentTransaction(TimestampMixin, Base):
    __tablename__ = 'payment_transactions'
    __table_args__ = (
        UniqueConstraint('out_trade_no', name='uk_payment_transactions_out_trade_no'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id'), nullable=False, index=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[PaymentChannel] = mapped_column(Enum(PaymentChannel), nullable=False, index=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default='CNY', nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    out_trade_no: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider_trade_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_app_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notify_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
