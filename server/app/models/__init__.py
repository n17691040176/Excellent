from app.db.base import Base
from app.db.session import engine
from app.models.address import UserAddress
from app.models.admin_role import AdminRole, AdminRolePermission
from app.models.asset import (
    DailySigninRecord,
    UserAssetAccount,
    UserAssetLedger,
    UserPowerBank,
    UserPowerBankIncomeRecord,
)
from app.models.bank_card import UserBankCard
from app.models.commerce import ShoppingCartItem, UserFavoriteProduct, UserProductFootprint
from app.models.commission import (
    CommissionAccountLedger,
    CommissionConfig,
    CommissionFlow,
    UserCommission,
    WithdrawRequest,
)
from app.models.earning_rule import EarningRule
from app.models.local_life import (
    AdRevenueFlow,
    DeviceRevenueFlow,
    LocalLifeMerchant,
    LocalLifeOrder,
    LocalLifeService,
    MerchantCommissionRule,
    MerchantStore,
)
from app.models.order import Order, OrderAssetDeduction, OrderItem, OrderStatusView
from app.models.package import Package, PackageBenefit
from app.models.page_decoration import PageDecoration
from app.models.payment import PaymentRefund, PaymentTransaction
from app.models.product import Product, ProductCategory, ProductQualification, ProductSku, ProductZoneConfig
from app.models.region_agent import RegionAgent
from app.models.region_dividend import RegionDividendFlow
from app.models.supplier import (
    AgentLevel,
    AgentQualification,
    Supplier,
    SupplierAgreement,
    SupplierEntryOrder,
    SupplierReferralReward,
)
from app.models.team import Team, TeamMember
from app.models.user import AdminUserPermission, InviteRecord, User, UserLegacyProfile

__all__ = [
    'Base', 'User', 'UserLegacyProfile', 'AdminUserPermission', 'AdminRole', 'AdminRolePermission', 'InviteRecord', 'Team', 'TeamMember', 'CommissionConfig', 'UserCommission',
    'CommissionFlow', 'WithdrawRequest', 'CommissionAccountLedger', 'UserBankCard', 'Package', 'PackageBenefit', 'Product', 'ProductCategory', 'ProductSku',
    'ProductZoneConfig', 'ProductQualification', 'UserAssetAccount', 'UserAssetLedger',
    'DailySigninRecord', 'UserPowerBank', 'UserPowerBankIncomeRecord', 'UserFavoriteProduct', 'UserProductFootprint', 'ShoppingCartItem',
    'Order', 'OrderItem', 'OrderAssetDeduction', 'OrderStatusView', 'PaymentTransaction', 'PaymentRefund', 'UserAddress', 'Supplier',
    'SupplierEntryOrder', 'SupplierAgreement', 'SupplierReferralReward', 'AgentLevel',
    'AgentQualification', 'LocalLifeMerchant', 'MerchantStore', 'LocalLifeService',
    'LocalLifeOrder', 'MerchantCommissionRule', 'DeviceRevenueFlow', 'AdRevenueFlow',
    'PageDecoration', 'EarningRule', 'RegionAgent', 'RegionDividendFlow'
]
