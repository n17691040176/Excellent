from app.models.enums import ProductStatus
from app.schemas.common import AppBaseModel


class PackageOrderRequest(AppBaseModel):
    use_ai_coupon_amount: float = 0
    pay_channel: str = 'cash'


class PackageQualificationOut(AppBaseModel):
    order_id: int
    package_id: int
    package_name: str
    paid_amount: float
    paid_at: str | None = None
    order_status: str


class AdminPackageCreateRequest(AppBaseModel):
    package_name: str
    package_price: float
    package_type: str
    voucher_reward_rate: float = 100
    referral_voucher_rate: float = 50
    ai_coupon_max_deduct_rate: float = 20
    grants_product_quota: int = 0
    points_subsidy_enabled: bool = True


class AdminPackageUpdateRequest(AppBaseModel):
    package_name: str
    package_price: float
    package_type: str
    voucher_reward_rate: float = 100
    referral_voucher_rate: float = 50
    ai_coupon_max_deduct_rate: float = 20
    grants_product_quota: int = 0
    points_subsidy_enabled: bool = True


class AdminPackageStatusRequest(AppBaseModel):
    status: ProductStatus
