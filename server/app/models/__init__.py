from app.db.base import Base
from app.db.session import engine
from app.models.address import UserAddress
from app.models.asset import (
    DailySigninRecord,
    UserAssetAccount,
    UserAssetLedger,
    UserPowerBank,
    UserPowerBankIncomeRecord,
)
from app.models.commerce import ShoppingCartItem, UserFavoriteProduct, UserProductFootprint
from app.models.commission import CommissionConfig, CommissionFlow, UserCommission, WithdrawRequest
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
from app.models.order import Order, OrderAssetDeduction, OrderItem
from app.models.package import Package, PackageBenefit
from app.models.page_decoration import PageDecoration
from app.models.payment import PaymentTransaction
from app.models.product import Product, ProductQualification, ProductSku, ProductZoneConfig
from app.models.supplier import (
    AgentLevel,
    AgentQualification,
    Supplier,
    SupplierAgreement,
    SupplierEntryOrder,
    SupplierReferralReward,
)
from app.models.team import Team, TeamMember
from app.models.user import InviteRecord, User, UserLegacyProfile

__all__ = [
    'Base', 'User', 'UserLegacyProfile', 'InviteRecord', 'Team', 'TeamMember', 'CommissionConfig', 'UserCommission',
    'CommissionFlow', 'WithdrawRequest', 'Package', 'PackageBenefit', 'Product', 'ProductSku',
    'ProductZoneConfig', 'ProductQualification', 'UserAssetAccount', 'UserAssetLedger',
    'DailySigninRecord', 'UserPowerBank', 'UserPowerBankIncomeRecord', 'UserFavoriteProduct', 'UserProductFootprint', 'ShoppingCartItem',
    'Order', 'OrderItem', 'OrderAssetDeduction', 'PaymentTransaction', 'UserAddress', 'Supplier',
    'SupplierEntryOrder', 'SupplierAgreement', 'SupplierReferralReward', 'AgentLevel',
    'AgentQualification', 'LocalLifeMerchant', 'MerchantStore', 'LocalLifeService',
    'LocalLifeOrder', 'MerchantCommissionRule', 'DeviceRevenueFlow', 'AdRevenueFlow',
    'PageDecoration', 'EarningRule'
]
