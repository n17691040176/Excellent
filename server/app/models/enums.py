from enum import StrEnum


class GlobalRole(StrEnum):
    SUPER_ADMIN = 'SUPER_ADMIN'
    TEAM_ADMIN = 'TEAM_ADMIN'
    USER = 'USER'


class BusinessIdentity(StrEnum):
    NORMAL_MEMBER = 'NORMAL_MEMBER'
    VIP_MEMBER = 'VIP_MEMBER'
    DEALER = 'DEALER'
    MASTER_DEALER = 'MASTER_DEALER'
    SUPPLIER = 'SUPPLIER'
    COUNTY_AGENT = 'COUNTY_AGENT'
    CITY_AGENT = 'CITY_AGENT'
    LOCAL_MERCHANT = 'LOCAL_MERCHANT'


class UserStatus(StrEnum):
    ENABLED = 'ENABLED'
    DISABLED = 'DISABLED'


class TeamStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISBANDED = 'DISBANDED'


class TeamRole(StrEnum):
    OWNER = 'OWNER'
    MEMBER = 'MEMBER'


class CommissionStatus(StrEnum):
    FROZEN = 'FROZEN'
    SETTLED = 'SETTLED'
    CANCELED = 'CANCELED'


class WithdrawStatus(StrEnum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    PAID = 'PAID'


class WithdrawType(StrEnum):
    COMMISSION = 'COMMISSION'
    BALANCE = 'BALANCE'
    POINTS = 'POINTS'


class AssetType(StrEnum):
    BALANCE = 'BALANCE'
    POINTS = 'POINTS'
    VOUCHER = 'VOUCHER'
    AI_COUPON = 'AI_COUPON'
    POWER_BANK = 'POWER_BANK'


class PowerBankStatus(StrEnum):
    ACTIVE = 'ACTIVE'
    DISABLED = 'DISABLED'


class AssetDirection(StrEnum):
    INCOME = 'INCOME'
    EXPENSE = 'EXPENSE'


class ProductType(StrEnum):
    PHYSICAL = 'PHYSICAL'
    PACKAGE = 'PACKAGE'
    SERVICE = 'SERVICE'
    ACTIVITY = 'ACTIVITY'


class ProductOwnerType(StrEnum):
    SELF_OPERATED = 'SELF_OPERATED'
    SUPPLIER = 'SUPPLIER'
    LOCAL_MERCHANT = 'LOCAL_MERCHANT'


class ZoneType(StrEnum):
    REPURCHASE = 'REPURCHASE'
    SELF_OPERATED = 'SELF_OPERATED'
    HOT_SALE = 'HOT_SALE'
    LOCAL_LIFE = 'LOCAL_LIFE'


class ProductStatus(StrEnum):
    DRAFT = 'DRAFT'
    PENDING_REVIEW = 'PENDING_REVIEW'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    ON_SHELF = 'ON_SHELF'
    OFF_SHELF = 'OFF_SHELF'


class OrderType(StrEnum):
    NORMAL_PRODUCT = 'NORMAL_PRODUCT'
    PACKAGE_ORDER = 'PACKAGE_ORDER'
    REPURCHASE_ORDER = 'REPURCHASE_ORDER'
    SELF_OPERATED_ORDER = 'SELF_OPERATED_ORDER'
    HOT_SALE_ORDER = 'HOT_SALE_ORDER'
    LOCAL_LIFE_ORDER = 'LOCAL_LIFE_ORDER'
    SUPPLIER_ENTRY_ORDER = 'SUPPLIER_ENTRY_ORDER'


class OrderStatus(StrEnum):
    PENDING_PAYMENT = 'PENDING_PAYMENT'   # 待支付
    PENDING_SHIP = 'PENDING_SHIP'         # 待发货
    SHIPPED = 'SHIPPED'                   # 已发货
    COMPLETED = 'COMPLETED'               # 已完成
    PENDING_REVIEW = 'PENDING_REVIEW'      # 待评价（预留）
    REFUND = 'REFUND'                     # 退款（预留）


class PayStatus(StrEnum):
    UNPAID = 'UNPAID'
    PAID = 'PAID'
    REFUNDED = 'REFUNDED'


class PaymentChannel(StrEnum):
    WECHAT = 'WECHAT'
    ALIPAY = 'ALIPAY'


class PaymentStatus(StrEnum):
    PENDING = 'PENDING'
    PAID = 'PAID'
    FAILED = 'FAILED'
    CLOSED = 'CLOSED'


class QualificationStatus(StrEnum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'


class QualificationType(StrEnum):
    ENTRY_FEE = 'ENTRY_FEE'
    PACKAGE_QUOTA = 'PACKAGE_QUOTA'
    AGENT_QUALIFICATION = 'AGENT_QUALIFICATION'


class SupplierStatus(StrEnum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    ACTIVE = 'ACTIVE'


class AgentLevelCode(StrEnum):
    COUNTY_AGENT = 'COUNTY_AGENT'
    CITY_AGENT = 'CITY_AGENT'
