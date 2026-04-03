from datetime import date, datetime

from sqlalchemy import BigInteger, DECIMAL, Date, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import AssetDirection, AssetType


class UserAssetAccount(Base):
    __tablename__ = 'user_asset_accounts'
    __table_args__ = (UniqueConstraint('user_id', 'asset_type', name='uk_user_asset_accounts_user_asset'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    total_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    available_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    frozen_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    consumed_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    withdrawn_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class UserAssetLedger(Base):
    __tablename__ = 'user_asset_ledgers'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False)
    direction: Mapped[AssetDirection] = mapped_column(Enum(AssetDirection), nullable=False)
    change_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    before_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    after_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    business_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[int | None] = mapped_column(nullable=True)
    source_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DailySigninRecord(Base):
    __tablename__ = 'daily_signin_records'
    __table_args__ = (UniqueConstraint('user_id', 'signin_date', name='uk_daily_signin_user_date'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    signin_date: Mapped[date] = mapped_column(Date, nullable=False)
    voucher_amount: Mapped[float] = mapped_column(DECIMAL(18, 2), default=100, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
