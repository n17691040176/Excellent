from datetime import datetime

from sqlalchemy import BigInteger, DECIMAL, DateTime, Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ProductOwnerType, ProductStatus, ProductType, QualificationStatus, QualificationType, ZoneType


class Product(TimestampMixin, Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType), nullable=False)
    owner_type: Mapped[ProductOwnerType] = mapped_column(Enum(ProductOwnerType), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(nullable=True)
    zone_type: Mapped[ZoneType] = mapped_column(Enum(ZoneType), nullable=False)
    market_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    sale_price: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
    cost_price: Mapped[float | None] = mapped_column(DECIMAL(18, 2), nullable=True)
    stock: Mapped[int] = mapped_column(default=0, nullable=False)
    sold_count: Mapped[int] = mapped_column(default=0, nullable=False)
    main_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.DRAFT, nullable=False)
    requires_shipping: Mapped[bool] = mapped_column(default=True, nullable=False)
    drop_shipping_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)


class ProductSku(Base):
    __tablename__ = 'product_skus'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    sku_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sku_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sale_price: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=False)
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
    balance_purchase_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
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
