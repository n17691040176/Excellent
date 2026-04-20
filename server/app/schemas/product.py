from app.models.enums import ProductOwnerType, ProductStatus, ProductType, ZoneType
from app.schemas.common import AppBaseModel


class ProductQuery(AppBaseModel):
    keyword: str | None = None


class ProductOrderItemRequest(AppBaseModel):
    product_id: int
    sku_id: int | None = None
    quantity: int = 1


class AssetDeductionRequest(AppBaseModel):
    asset_type: str
    amount: float


class CreateOrderRequest(AppBaseModel):
    order_type: str
    zone_type: str | None = None
    address_id: int | None = None
    pay_channel: str = 'BALANCE'
    items: list[ProductOrderItemRequest]
    asset_deductions: list[AssetDeductionRequest] = []


class OrderPayRequest(AppBaseModel):
    pay_channel: str
    points_amount: float = 0
    auto_complete: bool = True


class ProductZoneConfigUpdateRequest(AppBaseModel):
    package_required: bool = False
    package_id: int | None = None
    repurchase_discount_rate: float | None = None
    voucher_deduct_min_rate: float | None = None
    voucher_deduct_max_rate: float | None = None
    ai_coupon_reward_rate: float | None = None
    ai_coupon_max_deduct_rate: float | None = None
    points_purchase_enabled: bool = False
    balance_purchase_enabled: bool = False
    flash_sale_enabled: bool = False
    per_user_limit: int | None = None
    merchant_commission_rule_id: int | None = None
    device_revenue_enabled: bool = False


class AdminProductPayload(AppBaseModel):
    product_name: str
    product_type: ProductType
    zone_type: ZoneType
    owner_type: ProductOwnerType = ProductOwnerType.SELF_OPERATED
    owner_id: int | None = None
    market_price: float | None = None
    sale_price: float
    cost_price: float | None = None
    stock: int = 0
    main_image: str | None = None
    cover: str | None = None
    icons: str | None = None
    brand: str | None = None
    profile: str | None = None
    detail: str | None = None
    feature: str | None = None
    order_by: int | None = None
    is_hot: bool = False
    requires_shipping: bool = True
    drop_shipping_enabled: bool = False


class AdminProductCreateRequest(AdminProductPayload):
    pass


class AdminProductUpdateRequest(AdminProductPayload):
    pass


class AdminProductBatchMerchandiseRequest(AppBaseModel):
    product_ids: list[int]
    is_hot: bool | None = None
    order_by_start: int | None = None
    order_by_step: int = 1


class AdminProductBatchStatusRequest(AppBaseModel):
    product_ids: list[int]
    operation: str


class AdminProductAuditRequest(AppBaseModel):
    audit_status: ProductStatus


class AdminProductStatusRequest(AppBaseModel):
    status: ProductStatus
