from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, JSON, BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    ProductOwnerType,
    ProductStatus,
    ProductType,
    QualificationStatus,
    QualificationType,
    ZoneType,
)


class Product(TimestampMixin, Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False)
    owner_type: Mapped[ProductOwnerType] = mapped_column(Enum(ProductOwnerType), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(nullable=True)
    zone_type: Mapped[ZoneType] = mapped_column(
        Enum(ZoneType),
        default=ZoneType.SELF_OPERATED,
        server_default=ZoneType.SELF_OPERATED.value,
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey('product_categories.id', ondelete='RESTRICT'),
        nullable=True,
        index=True,
    )
    market_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    sale_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    stock: Mapped[int] = mapped_column(default=0, nullable=False)
    sold_count: Mapped[int] = mapped_column(default=0, nullable=False)
    main_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.DRAFT, nullable=False)
    requires_shipping: Mapped[bool] = mapped_column(default=True, nullable=False)
    drop_shipping_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    legacy_name: Mapped[str | None] = mapped_column('name', String(150), nullable=True)
    profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover: Mapped[str | None] = mapped_column(String(255), nullable=True)
    icons: Mapped[str | None] = mapped_column(Text, nullable=True)
    legacy_type: Mapped[int | None] = mapped_column('type', Integer, nullable=True)
    store_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(150), nullable=True)
    column_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_hot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    legacy_price: Mapped[float | None] = mapped_column('price', DECIMAL(18, 2), nullable=True)
    hehuoren_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    xiaofeijin_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    create_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    create_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    update_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verify_state: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verify_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    verify_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verify_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    dept_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_delete: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_integral: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_buy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_buy_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_buy_rate: Mapped[float | None] = mapped_column(DECIMAL(18, 4), nullable=True)
    is_flash_kill: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flash_kill_rate: Mapped[float | None] = mapped_column(DECIMAL(18, 4), nullable=True)
    sales_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_rate: Mapped[float | None] = mapped_column(DECIMAL(18, 4), nullable=True)
    feature: Mapped[str | None] = mapped_column(Text, nullable=True)
    direct_rate: Mapped[float | None] = mapped_column(DECIMAL(18, 4), nullable=True)


class ProductCategory(TimestampMixin, Base):
    __tablename__ = 'product_categories'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='active', nullable=False)


class ProductSku(Base):
    __tablename__ = 'product_skus'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sku_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    stock: Mapped[int] = mapped_column(default=0, nullable=False)
    spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.ON_SHELF, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ProductZoneConfig(TimestampMixin, Base):
    __tablename__ = 'product_zone_configs'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), unique=True, nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(Enum(ZoneType), nullable=False)
    package_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    package_id: Mapped[int | None] = mapped_column(ForeignKey('packages.id'), nullable=True)
    repurchase_discount_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    voucher_deduct_min_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    voucher_deduct_max_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    ai_coupon_reward_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    ai_coupon_max_deduct_rate: Mapped[float | None] = mapped_column(DECIMAL(5, 2), nullable=True)
    points_purchase_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    balance_purchase_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    alipay_purchase_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    wechat_purchase_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    points_only_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    points_cash_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    cash_only_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    balance_only_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    balance_points_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    flash_sale_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    per_user_limit: Mapped[int | None] = mapped_column(nullable=True)
    merchant_commission_rule_id: Mapped[int | None] = mapped_column(nullable=True)
    device_revenue_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)


class ProductQualification(Base):
    __tablename__ = 'product_qualifications'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    applicant_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey('suppliers.id'), nullable=True)
    qualification_type: Mapped[QualificationType] = mapped_column(Enum(QualificationType), nullable=False)
    source_ref_id: Mapped[int | None] = mapped_column(nullable=True)
    audit_status: Mapped[QualificationStatus] = mapped_column(
        Enum(QualificationStatus),
        default=QualificationStatus.PENDING,
        nullable=False,
    )
    audit_remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audited_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
