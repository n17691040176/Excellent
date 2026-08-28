from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, JSON, BigInteger, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import PaymentChannel, PaymentStatus, RefundStatus


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
    refunded_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)


class PaymentRefund(TimestampMixin, Base):
    """One idempotent refund attempt against an external payment transaction."""

    __tablename__ = 'payment_refunds'
    __table_args__ = (
        # The supported provider flow is a single, full refund for one paid
        # transaction.  A unique transaction key makes the provider's
        # deterministic out_refund_no durable under concurrent requests too.
        UniqueConstraint('payment_transaction_id', name='uk_payment_refunds_payment_transaction'),
        UniqueConstraint('out_refund_no', name='uk_payment_refunds_out_refund_no'),
        UniqueConstraint('provider_refund_id', name='uk_payment_refunds_provider_refund_id'),
        UniqueConstraint('provider_notify_id', name='uk_payment_refunds_provider_notify_id'),
        UniqueConstraint(
            'payment_transaction_id',
            'idempotency_key',
            name='uk_payment_refunds_transaction_idempotency',
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey('orders.id', name='fk_payment_refunds_order_id'),
        nullable=False,
        index=True,
    )
    payment_transaction_id: Mapped[int] = mapped_column(
        ForeignKey(
            'payment_transactions.id',
            name='fk_payment_refunds_payment_transaction_id',
        ),
        nullable=False,
        index=True,
    )
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[PaymentChannel] = mapped_column(Enum(PaymentChannel), nullable=False, index=True)
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus),
        default=RefundStatus.PENDING,
        nullable=False,
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(8), default='CNY', nullable=False)
    original_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    out_refund_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_refund_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider_trade_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notify_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider_notify_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
