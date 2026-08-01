from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.payment_config import enabled_external_payment_channels
from app.models.address import UserAddress
from app.models.asset import UserAssetAccount, UserAssetLedger, UserPowerBank
from app.models.commerce import ShoppingCartItem, UserFavoriteProduct, UserProductFootprint
from app.models.commission import CommissionFlow, WithdrawRequest
from app.models.enums import AssetDirection, OrderStatus, OrderType, PayStatus, ZoneType
from app.models.local_life import LocalLifeMerchant, LocalLifeOrder, LocalLifeService, MerchantStore
from app.models.order import Order, OrderAssetDeduction, OrderItem
from app.models.package import Package
from app.models.product import Product, ProductCategory, ProductZoneConfig
from app.models.supplier import Supplier
from app.models.team import Team
from app.models.user import User
from app.utils.helpers import iso_datetime


def enum_value(value: Any) -> Any:
    return value.value if hasattr(value, 'value') else value


def money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


TAG_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')
LEGACY_FILE_BASE_URL = 'https://file.hoh516.com/huohonghuo'


def page_slice(rows: list[Any], page: int = 1, page_size: int = 20) -> list[Any]:
    safe_page = max(page, 1)
    safe_page_size = max(1, min(page_size, 100))
    start = (safe_page - 1) * safe_page_size
    return rows[start:start + safe_page_size]


def normalize_asset_type(asset_type: str):
    from app.models.enums import AssetType

    return AssetType(asset_type.upper())


def serialize_package(package: Package) -> dict[str, Any]:
    price = money(package.package_price)
    package_type = str(package.package_type or '')
    return {
        'id': package.id,
        'package_id': package.id,
        'package_name': package.package_name,
        'name': package.package_name,
        'title': package.package_name,
        'package_price': price,
        'price': price,
        'sale_price': price,
        'package_type': package_type,
        'tag': package_type,
        'category_name': package_type,
        'description': f'{package_type} package' if package_type else '',
        'desc': f'{package_type} package' if package_type else '',
        'voucher_reward_rate': money(package.voucher_reward_rate),
        'referral_voucher_rate': money(package.referral_voucher_rate),
        'ai_coupon_max_deduct_rate': money(package.ai_coupon_max_deduct_rate),
        'grants_product_quota': package.grants_product_quota,
        'points_subsidy_enabled': package.points_subsidy_enabled,
        'status': enum_value(package.status),
        'features': [
            f'Voucher reward {money(package.voucher_reward_rate)}%',
            f'Referral reward {money(package.referral_voucher_rate)}%',
            f'Product quota {package.grants_product_quota}',
        ],
        'items': [
            f'AI coupon max deduction {money(package.ai_coupon_max_deduct_rate)}%',
            f'Points subsidy {"enabled" if package.points_subsidy_enabled else "disabled"}',
        ],
        'created_at': iso_datetime(getattr(package, 'created_at', None)),
        'updated_at': iso_datetime(getattr(package, 'updated_at', None)),
    }


def _product_owner_name(db: Session, product: Product) -> str | None:
    owner_type = enum_value(product.owner_type)
    if owner_type == 'SUPPLIER' and product.owner_id:
        supplier = db.get(Supplier, product.owner_id)
        return supplier.supplier_name if supplier else None
    if owner_type == 'LOCAL_MERCHANT' and product.owner_id:
        merchant = db.get(LocalLifeMerchant, product.owner_id)
        return merchant.merchant_name if merchant else None
    return None


def _split_media(value: str | None) -> list[str]:
    if not value:
        return []
    urls: list[str] = []
    for item in value.split(','):
        normalized = _normalize_media_url(item.strip()) if item and item.strip() else None
        if normalized:
            urls.append(normalized)
    return urls


def _normalize_media_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith(('http://', 'https://')):
        return value
    if value.startswith('/profile/'):
        return f'{LEGACY_FILE_BASE_URL}{value}'
    return value


def _plain_text(value: str | None, fallback: str = '') -> str:
    if not value:
        return fallback
    text = TAG_RE.sub(' ', value)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    return WHITESPACE_RE.sub(' ', text).strip()


def _truncate(value: str, limit: int = 76) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."


def _product_category_name(db: Session, product: Product) -> str:
    if product.category_id:
        category = db.get(ProductCategory, product.category_id)
        if category:
            return category.name
    if product.brand:
        return product.brand
    if product.column_type is not None:
        return f'分类 {product.column_type}'
    if product.zone_type:
        return enum_value(product.zone_type)
    return '精选商品'


def _product_tag(product: Product, category_name: str) -> str:
    if product.is_hot:
        return '爆款'
    if product.group_buy:
        return '拼团'
    if product.is_flash_kill:
        return '秒杀'
    return category_name


def _product_features(product: Product) -> list[str]:
    features: list[str] = []
    if product.feature:
        features.append(_plain_text(product.feature))
    if product.brand:
        features.append(f'品牌 {product.brand}')
    if product.discount_rate is not None:
        features.append(f'折扣率 {money(product.discount_rate):g}')
    if product.direct_rate is not None:
        features.append(f'直推比例 {money(product.direct_rate):g}')
    if product.group_buy:
        features.append(f'拼团人数 {product.group_buy_num or 0}')
    if product.is_flash_kill:
        features.append('限时秒杀')
    if product.requires_shipping:
        features.append('支持发货')
    return [item for item in features if item][:4] or ['精选商品', '支持下单', '库存同步']


def _product_items(product: Product) -> list[str]:
    items: list[str] = []
    if product.profile:
        items.append(_truncate(_plain_text(product.profile)))
    if product.detail:
        items.append(_truncate(_plain_text(product.detail), 120))
    if product.hehuoren_price is not None:
        items.append(f'合伙人价 {money(product.hehuoren_price):.2f}')
    if product.xiaofeijin_price is not None:
        items.append(f'消费金 {money(product.xiaofeijin_price):.2f}')
    if product.sales_volume is not None:
        items.append(f'历史销量 {product.sales_volume}')
    return [item for item in items if item][:4] or ['暂无更多说明']


def _product_payment_flags(db: Session, product: Product) -> dict[str, bool]:
    config = db.query(ProductZoneConfig).filter(ProductZoneConfig.product_id == product.id).first()
    default_points_enabled = {
        ZoneType.REPURCHASE: True,
        ZoneType.SELF_OPERATED: False,
        ZoneType.HOT_SALE: True,
        ZoneType.LOCAL_LIFE: True,
    }
    default_balance_enabled = dict.fromkeys(ZoneType, True)

    points_enabled = default_points_enabled.get(product.zone_type, True)
    balance_enabled = default_balance_enabled.get(product.zone_type, True)
    points_only_enabled = False
    points_cash_enabled = True
    cash_only_enabled = True
    balance_only_enabled = True
    balance_points_enabled = True
    alipay_enabled = True
    wechat_enabled = False
    if config:
        points_enabled = bool(config.points_purchase_enabled)
        if product.zone_type in {ZoneType.HOT_SALE, ZoneType.SELF_OPERATED, ZoneType.LOCAL_LIFE, ZoneType.REPURCHASE}:
            balance_enabled = bool(config.balance_purchase_enabled)
        points_only_enabled = bool(config.points_only_enabled)
        points_cash_enabled = bool(config.points_cash_enabled)
        cash_only_enabled = bool(config.cash_only_enabled)
        balance_only_enabled = bool(getattr(config, 'balance_only_enabled', True))
        balance_points_enabled = bool(getattr(config, 'balance_points_enabled', True))
        alipay_enabled = bool(getattr(config, 'alipay_purchase_enabled', True))
        wechat_enabled = bool(getattr(config, 'wechat_purchase_enabled', False))

    return {
        'points_purchase_enabled': points_enabled,
        'balance_purchase_enabled': balance_enabled,
        'points_only_enabled': points_only_enabled,
        'points_cash_enabled': points_cash_enabled,
        'cash_only_enabled': cash_only_enabled,
        'balance_only_enabled': balance_only_enabled,
        'balance_points_enabled': balance_points_enabled,
        'alipay_purchase_enabled': alipay_enabled,
        'wechat_purchase_enabled': wechat_enabled,
    }


def _payment_option(channel: str, purchase_mode: str) -> dict[str, Any]:
    label_map = {
        ('BALANCE', 'CASH_ONLY'): '余额支付',
        ('WECHAT', 'CASH_ONLY'): '微信支付',
        ('ALIPAY', 'CASH_ONLY'): '支付宝支付',
    }
    desc_map = {
        ('BALANCE', 'CASH_ONLY'): '全部使用账户余额完成支付',
        ('WECHAT', 'CASH_ONLY'): '全部使用微信支付',
        ('ALIPAY', 'CASH_ONLY'): '全部使用支付宝支付',
    }
    return {
        'value': channel,
        'label': label_map.get((channel, purchase_mode), channel),
        'desc': desc_map.get((channel, purchase_mode), '按当前方式支付'),
        'purchase_mode': purchase_mode,
        'supports_points': False,
    }


def _product_payment_options(_product: Product, payment_flags: dict[str, bool]) -> list[dict[str, Any]]:
    active_channels = set(enabled_external_payment_channels())
    balance_available = bool(payment_flags.get('balance_purchase_enabled'))
    alipay_product_enabled = bool(payment_flags.get('alipay_purchase_enabled'))
    alipay_provider_ready = 'ALIPAY' in active_channels
    return [
        {
            **_payment_option('BALANCE', 'CASH_ONLY'),
            'label': '余额支付',
            'available': balance_available,
            'unavailable_reason': '' if balance_available else '后台未开启余额支付',
        },
        {
            **_payment_option('WECHAT', 'CASH_ONLY'),
            'desc': '正在开发',
            'available': False,
            'unavailable_reason': '微信支付正在开发',
        },
        {
            **_payment_option('ALIPAY', 'CASH_ONLY'),
            'available': alipay_product_enabled and alipay_provider_ready,
            'unavailable_reason': (
                ''
                if alipay_product_enabled and alipay_provider_ready
                else '后台未开启支付宝支付'
                if not alipay_product_enabled
                else '支付宝全局配置未就绪'
            ),
        },
    ]


def serialize_product(db: Session, product: Product) -> dict[str, Any]:
    owner_name = _product_owner_name(db, product)
    payment_flags = _product_payment_flags(db, product)
    payment_options = _product_payment_options(product, payment_flags)
    available_payment_options = [item for item in payment_options if item.get('available')]
    sale_price = money(product.sale_price if product.sale_price is not None else product.legacy_price)
    market_price = product.market_price if product.market_price is not None else product.old_price
    cost_price = product.cost_price if product.cost_price is not None else product.hehuoren_price
    gallery = _split_media(product.icons)
    image = _normalize_media_url(product.main_image) or _normalize_media_url(product.cover) or (gallery[0] if gallery else None)
    summary = _plain_text(product.profile) or _plain_text(product.detail) or ''
    category_name = _product_category_name(db, product)
    tag = _product_tag(product, category_name)
    return {
        'id': product.id,
        'product_id': product.id,
        'product_name': product.product_name,
        'name': product.product_name,
        'title': product.product_name,
        'description': _truncate(summary, 88) if summary else '',
        'desc': _truncate(summary, 88) if summary else '',
        'product_type': enum_value(product.product_type),
        'owner_type': enum_value(product.owner_type),
        'owner_id': product.owner_id,
        'zone_type': enum_value(product.zone_type),
        'category_id': product.category_id,
        'market_price': money(market_price) if market_price is not None else None,
        'sale_price': sale_price,
        'price': sale_price,
        'cost_price': money(cost_price) if cost_price is not None else None,
        'stock': product.stock,
        'sold_count': product.sold_count or product.sales_volume or 0,
        'main_image': image,
        'image': image,
        'cover': _normalize_media_url(product.cover) or image,
        'icons': product.icons,
        'gallery': gallery,
        'profile': product.profile,
        'detail': product.detail,
        'content': _product_items(product),
        'items': _product_items(product),
        'features': _product_features(product),
        'tag': tag,
        'category_name': category_name,
        'sort': product.order_by,
        'supplier_name': owner_name,
        'merchant_name': owner_name,
        'status': enum_value(product.status),
        'requires_shipping': product.requires_shipping,
        'drop_shipping_enabled': product.drop_shipping_enabled,
        'payment_options': payment_options,
        'supported_pay_channels': list(dict.fromkeys(item['value'] for item in available_payment_options)),
        'default_pay_channel': available_payment_options[0]['value'] if available_payment_options else None,
        'points_purchase_enabled': bool(payment_flags['points_purchase_enabled']),
        'balance_purchase_enabled': bool(payment_flags['balance_purchase_enabled']),
        'points_only_enabled': bool(payment_flags['points_only_enabled']),
        'points_cash_enabled': bool(payment_flags['points_cash_enabled']),
        'cash_only_enabled': bool(payment_flags['cash_only_enabled']),
        'balance_only_enabled': bool(payment_flags['balance_only_enabled']),
        'balance_points_enabled': bool(payment_flags['balance_points_enabled']),
        'alipay_purchase_enabled': bool(payment_flags['alipay_purchase_enabled']),
        'wechat_purchase_enabled': bool(payment_flags['wechat_purchase_enabled']),
        'old_name': product.legacy_name,
        'old_type': product.legacy_type,
        'old_price': money(product.old_price) if product.old_price is not None else None,
        'legacy_price': money(product.legacy_price) if product.legacy_price is not None else None,
        'hehuoren_price': money(product.hehuoren_price) if product.hehuoren_price is not None else None,
        'xiaofeijin_price': money(product.xiaofeijin_price) if product.xiaofeijin_price is not None else None,
        'verify_state': product.verify_state,
        'verify_by': product.verify_by,
        'verify_time': iso_datetime(product.verify_time),
        'verify_remark': product.verify_remark,
        'is_hot': product.is_hot,
        'is_integral': product.is_integral,
        'group_buy': product.group_buy,
        'group_buy_num': product.group_buy_num,
        'group_buy_rate': money(product.group_buy_rate) if product.group_buy_rate is not None else None,
        'is_flash_kill': product.is_flash_kill,
        'flash_kill_rate': money(product.flash_kill_rate) if product.flash_kill_rate is not None else None,
        'sales_volume': product.sales_volume,
        'use_num': product.use_num,
        'discount_rate': money(product.discount_rate) if product.discount_rate is not None else None,
        'feature': product.feature,
        'direct_rate': money(product.direct_rate) if product.direct_rate is not None else None,
        'created_at': iso_datetime(getattr(product, 'created_at', None)),
        'updated_at': iso_datetime(getattr(product, 'updated_at', None)),
    }


def serialize_local_life_merchant(merchant: LocalLifeMerchant) -> dict[str, Any]:
    return {
        'id': merchant.id,
        'merchant_id': merchant.id,
        'merchant_name': merchant.merchant_name,
        'name': merchant.merchant_name,
        'title': merchant.merchant_name,
        'category_name': merchant.category_name,
        'tag': merchant.category_name,
        'contact_phone': merchant.contact_phone,
        'city_code': merchant.city_code,
        'status': merchant.status,
        'created_at': iso_datetime(getattr(merchant, 'created_at', None)),
        'updated_at': iso_datetime(getattr(merchant, 'updated_at', None)),
    }


def serialize_store(store: MerchantStore) -> dict[str, Any]:
    return {
        'id': store.id,
        'store_id': store.id,
        'merchant_id': store.merchant_id,
        'store_name': store.store_name,
        'name': store.store_name,
        'title': store.store_name,
        'contact_phone': store.contact_phone,
        'province': store.province,
        'city': store.city,
        'district': store.district,
        'detail_address': store.detail_address,
        'latitude': money(store.latitude) if store.latitude is not None else None,
        'longitude': money(store.longitude) if store.longitude is not None else None,
        'status': store.status,
        'created_at': iso_datetime(store.created_at),
    }


def serialize_local_life_service(db: Session, service: LocalLifeService) -> dict[str, Any]:
    merchant = db.get(LocalLifeMerchant, service.merchant_id) if service.merchant_id else None
    store = db.get(MerchantStore, service.store_id) if service.store_id else None
    sale_price = money(service.sale_price)
    return {
        'id': service.id,
        'service_id': service.id,
        'merchant_id': service.merchant_id,
        'store_id': service.store_id,
        'service_name': service.service_name,
        'name': service.service_name,
        'title': service.service_name,
        'description': service.service_type,
        'desc': service.service_type,
        'market_price': money(service.market_price) if service.market_price is not None else None,
        'sale_price': sale_price,
        'price': sale_price,
        'service_type': service.service_type,
        'verification_type': service.verification_type,
        'tag': service.service_type,
        'status': service.status,
        'merchant_name': merchant.merchant_name if merchant else None,
        'store_name': store.store_name if store else None,
        'content': [service.service_type, service.verification_type],
        'items': [service.service_type, service.verification_type],
        'created_at': iso_datetime(service.created_at),
    }


def serialize_asset_account(account: UserAssetAccount) -> dict[str, Any]:
    asset_type = enum_value(account.asset_type)
    return {
        'id': account.id,
        'user_id': account.user_id,
        'asset_type': asset_type,
        'total_amount': money(account.total_amount),
        'available_amount': money(account.available_amount),
        'frozen_amount': money(account.frozen_amount),
        'consumed_amount': money(account.consumed_amount),
        'withdrawn_amount': money(account.withdrawn_amount),
        'updated_at': iso_datetime(account.updated_at),
    }


def serialize_asset_ledger(ledger: UserAssetLedger) -> dict[str, Any]:
    direction = enum_value(ledger.direction)
    change = money(ledger.change_amount)
    signed_amount = -change if direction == AssetDirection.EXPENSE.value else change
    biz_name = {
        'DAILY_SIGNIN': '每日签到奖励',
        'POINTS_TRANSFER_OUT': '积分转出',
        'POINTS_TRANSFER_IN': '积分转入',
        'BALANCE_WITHDRAW_APPROVE': '余额提现',
        'BALANCE_WITHDRAW_VOUCHER': '余额提现转消费金',
        'POINTS_WITHDRAW_APPROVE': '积分提现',
        'POWER_BANK_BIND': '充电宝绑定',
        'POWER_BANK_ENABLE': '充电宝启用',
        'POWER_BANK_DISABLE': '充电宝停用',
        'POWER_BANK_DAILY_INCOME': '充电宝每日收益',
        'POWER_BANK_REFERRAL_INCOME': '充电宝推荐收益',
        'BALANCE_WITHDRAW_APPLY': '余额提现申请',
        'BALANCE_WITHDRAW_REJECT': '余额提现退回',
        'POINTS_WITHDRAW_APPLY': '积分提现申请',
        'POINTS_WITHDRAW_REJECT': '积分提现退回',
        'ORDER_DEDUCT': '下单抵扣',
        'ORDER_CANCEL_REFUND': '订单取消/退款退回',
        'ORDER_REFUND_REWARD_REVOKE': '订单退款扣回奖励',
        'SELF_OPERATED_REWARD': '自营专区奖励',
        'TEST_SEED': '测试资产初始化',
        'PAYFLOW_SMOKE_SEED': '支付流程测试充值',
    }.get(ledger.business_type, ledger.business_type)
    return {
        'id': ledger.id,
        'user_id': ledger.user_id,
        'asset_type': enum_value(ledger.asset_type),
        'direction': direction,
        'change_amount': change,
        'amount': signed_amount,
        'before_amount': money(ledger.before_amount),
        'after_amount': money(ledger.after_amount),
        'business_type': ledger.business_type,
        'biz_name': biz_name,
        'source_id': ledger.source_id,
        'source_no': ledger.source_no,
        'remark': ledger.remark,
        'created_at': iso_datetime(ledger.created_at),
    }


def serialize_power_bank(power_bank: UserPowerBank) -> dict[str, Any]:
    return {
        'id': power_bank.id,
        'user_id': power_bank.user_id,
        'device_code': power_bank.device_code,
        'device_name': power_bank.device_name,
        'status': enum_value(power_bank.status),
        'bound_at': iso_datetime(power_bank.bound_at),
        'last_income_date': power_bank.last_income_date.isoformat() if power_bank.last_income_date else None,
        'total_income_amount': money(power_bank.total_income_amount),
        'total_referral_income_amount': money(power_bank.total_referral_income_amount),
        'remark': power_bank.remark,
        'created_at': iso_datetime(power_bank.created_at),
        'updated_at': iso_datetime(power_bank.updated_at),
    }


def serialize_address(address: UserAddress) -> dict[str, Any]:
    return {
        'id': address.id,
        'address_id': address.id,
        'user_id': address.user_id,
        'receiver_name': address.receiver_name,
        'receiver_phone': address.receiver_phone,
        'province': address.province,
        'city': address.city,
        'district': address.district,
        'detail_address': address.detail_address,
        'full_address': ' '.join(
            [
                item
                for item in [address.province, address.city, address.district, address.detail_address]
                if item
            ]
        ),
        'is_default': bool(address.is_default),
        'created_at': iso_datetime(address.created_at),
        'updated_at': iso_datetime(address.updated_at),
    }


def serialize_commission_flow(flow: CommissionFlow) -> dict[str, Any]:
    return {
        'id': flow.id,
        'beneficiary_user_id': flow.beneficiary_user_id,
        'source_user_id': flow.source_user_id,
        'order_id': flow.order_id,
        'team_id': flow.team_id,
        'level': flow.level,
        'rate': money(flow.rate),
        'base_amount': money(flow.base_amount),
        'commission_amount': money(flow.commission_amount),
        'amount': money(flow.commission_amount),
        'status': enum_value(flow.status),
        'status_text': enum_value(flow.status),
        'settled_at': iso_datetime(flow.settled_at),
        'created_at': iso_datetime(flow.created_at),
        'title': f'Commission order {flow.order_id}',
        'biz_name': f'Commission order {flow.order_id}',
    }


def serialize_withdraw_request(record: WithdrawRequest) -> dict[str, Any]:
    amount = money(record.amount)
    withdraw_type = enum_value(record.withdraw_type)
    voucher_amount = 0.0
    net_amount = amount

    if withdraw_type == 'BALANCE':
        voucher_amount = round(amount * 0.2, 2)
        net_amount = round(amount - voucher_amount, 2)

    return {
        'id': record.id,
        'user_id': record.user_id,
        'team_id': record.team_id,
        'withdraw_type': withdraw_type,
        'source_no': f'WD-{record.id}',
        'amount': amount,
        'gross_amount': amount,
        'net_amount': net_amount,
        'voucher_amount': voucher_amount,
        'status': enum_value(record.status),
        'status_text': enum_value(record.status),
        'remark': record.remark,
        'reviewed_by': record.reviewed_by,
        'reviewed_at': iso_datetime(record.reviewed_at),
        'paid_by': record.paid_by,
        'paid_at': iso_datetime(record.paid_at),
        'created_at': iso_datetime(record.created_at),
    }


def _order_status_text(status: str, pay_status: str | None = None) -> str:
    if status == 'REFUND':
        return '已退款' if pay_status == 'REFUNDED' else '已取消'
    return {
        'PENDING_PAYMENT': '待支付',
        'PENDING_SHIP': '待发货',
        'SHIPPED': '已发货',
        'COMPLETED': '已完成',
        'PENDING_REVIEW': '待评价',
        'REFUND': '已取消',
    }.get(status, status)


def _payment_combo(order: Order, deductions: list[OrderAssetDeduction] | None = None) -> str:
    status = enum_value(order.order_status)
    pay_status = enum_value(order.pay_status)
    if status == enum_value(OrderStatus.REFUND):
        return '已退款' if pay_status == enum_value(PayStatus.REFUNDED) else '订单已取消'

    rows = deductions or []
    deduction_types = {str(item.asset_type) for item in rows}
    payable_amount = money(order.payable_amount)
    if 'BALANCE' in deduction_types and 'POINTS' in deduction_types:
        return '余额 + 积分'
    if 'VOUCHER' in deduction_types and 'POINTS' in deduction_types:
        return '消费金 + 积分'
    if 'POINTS' in deduction_types and payable_amount <= 0:
        return '纯积分'
    if 'BALANCE' in deduction_types:
        return '余额支付'
    if 'VOUCHER' in deduction_types:
        return '消费金支付'
    if 'POINTS' in deduction_types and payable_amount > 0:
        return '外部支付 + 积分'
    if money(order.total_amount) > 0 and payable_amount > 0:
        return '待支付'
    return '已完成支付'


def _order_channel(order: Order) -> tuple[str, str]:
    order_type = enum_value(order.order_type)
    if order_type == OrderType.LOCAL_LIFE_ORDER.value:
        return 'local_life', '本地生活'
    if order_type == OrderType.PACKAGE_ORDER.value:
        return 'package', '套餐订单'
    return 'mall', '商城订单'


def _order_pay_channel_options(order: Order, deductions: list[OrderAssetDeduction] | None = None) -> list[str]:
    order_type = enum_value(order.order_type)
    deduction_types = {str(item.asset_type) for item in (deductions or [])}
    if 'POINTS' in deduction_types and money(order.payable_amount) <= 0:
        return ['POINTS']
    if 'BALANCE' in deduction_types:
        return ['BALANCE']
    if 'VOUCHER' in deduction_types:
        return ['VOUCHER']
    if order_type == OrderType.PACKAGE_ORDER.value:
        return ['BALANCE']
    external_channels = enabled_external_payment_channels()
    return ['BALANCE', *external_channels]


def _default_order_pay_channel(order: Order, pay_channel_options: list[str]) -> str | None:
    if money(order.payable_amount) > 0:
        for channel in pay_channel_options:
            if channel in {'ALIPAY', 'WECHAT'}:
                return channel
    return pay_channel_options[0] if pay_channel_options else None


def _order_title(db: Session, order: Order) -> str:
    order_type = enum_value(order.order_type)
    if order_type == OrderType.PACKAGE_ORDER.value and order.source_ref_id:
        package = db.get(Package, order.source_ref_id)
        if package:
            return package.package_name
    if order_type == OrderType.LOCAL_LIFE_ORDER.value:
        local_order = db.query(LocalLifeOrder).filter(LocalLifeOrder.order_id == order.id).first()
        service = db.get(LocalLifeService, local_order.service_id) if local_order else None
        if service:
            return service.service_name
    item = db.query(OrderItem).filter(OrderItem.order_id == order.id).order_by(OrderItem.id.asc()).first()
    return item.product_name if item else f'Order {order.order_no}'


def _order_requires_shipping(db: Session, order: Order) -> bool:
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    if not items:
        return False
    product_ids = [item.product_id for item in items]
    return bool(db.query(Product.id).filter(Product.id.in_(product_ids), Product.requires_shipping.is_(True)).first())


def serialize_order(db: Session, order: Order, include_detail: bool = False) -> dict[str, Any]:
    biz_type, channel_text = _order_channel(order)
    status = enum_value(order.order_status)
    pay_status = enum_value(order.pay_status)
    is_local_life = enum_value(order.order_type) == enum_value(OrderType.LOCAL_LIFE_ORDER)
    total_amount = money(order.total_amount)
    payable_amount = money(order.payable_amount)
    requires_shipping = _order_requires_shipping(db, order)
    can_pay = not is_local_life and pay_status != enum_value(PayStatus.PAID) and status not in {enum_value(OrderStatus.COMPLETED), enum_value(OrderStatus.REFUND)}
    can_confirm = not is_local_life and pay_status == enum_value(PayStatus.PAID) and status == enum_value(OrderStatus.SHIPPED)
    can_cancel = not is_local_life and pay_status == enum_value(PayStatus.UNPAID) and status == enum_value(OrderStatus.PENDING_PAYMENT)
    can_refund = not is_local_life and pay_status == enum_value(PayStatus.PAID) and status in {
        enum_value(OrderStatus.PENDING_SHIP),
        enum_value(OrderStatus.SHIPPED),
    } or (
        not is_local_life
        and pay_status == enum_value(PayStatus.PAID)
        and status == enum_value(OrderStatus.COMPLETED)
        and not requires_shipping
    )
    pay_channel_options = _order_pay_channel_options(order)
    data: dict[str, Any] = {
        'id': order.id,
        'order_id': order.id,
        'order_no': order.order_no,
        'no': order.order_no,
        'user_id': order.user_id,
        'team_id': order.team_id,
        'order_type': enum_value(order.order_type),
        'zone_type': enum_value(order.zone_type),
        'source_ref_id': order.source_ref_id,
        'total_amount': total_amount,
        'discount_amount': money(order.discount_amount),
        'payable_amount': payable_amount,
        'paid_amount': money(order.paid_amount),
        'amount': total_amount,
        'pay_amount': total_amount,
        'cash_due': payable_amount,
        'pay_status': pay_status,
        'order_status': status,
        'status': status,
        'status_text': _order_status_text(status, pay_status),
        'title': _order_title(db, order),
        'channel': channel_text,
        'channel_text': channel_text,
        'biz_type': biz_type,
        'can_pay': can_pay,
        'can_confirm': can_confirm,
        'can_cancel': can_cancel,
        'can_refund': can_refund,
        'requires_shipping': requires_shipping,
        'pay_channel_options': pay_channel_options,
        'default_pay_channel': _default_order_pay_channel(order, pay_channel_options),
        'created_at': iso_datetime(order.created_at),
        'updated_at': iso_datetime(order.updated_at),
        'paid_at': iso_datetime(order.paid_at),
        'confirmed_at': iso_datetime(order.confirmed_at),
        'timeline': _order_timeline(order),
        'steps': _order_timeline(order),
    }

    if include_detail:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).order_by(OrderItem.id.asc()).all()
        deductions = db.query(OrderAssetDeduction).filter(
            OrderAssetDeduction.order_id == order.id
        ).order_by(OrderAssetDeduction.id.asc()).all()
        data['order'] = data.copy()
        data['items'] = [serialize_order_item(item, db) for item in items]
        data['asset_deductions'] = [serialize_order_asset_deduction(item) for item in deductions]
        data['payment_combo'] = _payment_combo(order, deductions)
        data['pay_channel_options'] = _order_pay_channel_options(order, deductions)
        data['default_pay_channel'] = _default_order_pay_channel(order, data['pay_channel_options'])
        if status == enum_value(OrderStatus.REFUND):
            data['payment_message'] = '订单已退款。' if pay_status == enum_value(PayStatus.REFUNDED) else '订单已取消。'
        else:
            data['payment_message'] = '支付单已生成，请按所选渠道完成支付。' if payable_amount > 0 else '订单已完成支付。'
        address = db.get(UserAddress, order.legacy_address_id) if order.legacy_address_id else None
        data['address_id'] = order.legacy_address_id
        data['shipping_address'] = serialize_address(address) if address else None
        data['shipment'] = serialize_shipment(db, order, include_detail=True) if data['requires_shipping'] else None
    else:
        data['payment_combo'] = _payment_combo(order)
    return data


def _order_timeline(order: Order) -> list[dict[str, Any]]:
    steps = [
        {'title': '订单已创建', 'time': iso_datetime(order.created_at), 'active': True},
    ]
    if order.paid_at:
        steps.append({'title': '支付成功', 'time': iso_datetime(order.paid_at), 'active': True})
    status = enum_value(order.order_status)
    if status == enum_value(OrderStatus.PENDING_SHIP):
        steps.append({'title': '等待发货', 'time': iso_datetime(order.updated_at), 'active': True})
    if status == enum_value(OrderStatus.SHIPPED):
        steps.append({'title': '商家已发货', 'time': iso_datetime(order.updated_at), 'active': True})
    if order.confirmed_at:
        steps.append({'title': '订单已完成', 'time': iso_datetime(order.confirmed_at), 'active': True})
    if status == enum_value(OrderStatus.REFUND):
        title = '订单已退款' if enum_value(order.pay_status) == enum_value(PayStatus.REFUNDED) else '订单已取消'
        steps.append({'title': title, 'time': iso_datetime(order.updated_at), 'active': True})
    elif len(steps) == 1:
        steps.append({'title': '等待支付', 'time': iso_datetime(order.updated_at), 'active': False})
    return steps


def serialize_order_item(item: OrderItem, db: Session | None = None) -> dict[str, Any]:
    data = {
        'id': item.id,
        'order_id': item.order_id,
        'product_id': item.product_id,
        'sku_id': item.sku_id,
        'product_name': item.product_name,
        'sku_name': item.sku_name,
        'unit_price': money(item.unit_price),
        'quantity': item.quantity,
        'total_amount': money(item.total_amount),
        'created_at': iso_datetime(item.created_at),
    }
    if db:
        product = db.get(Product, item.product_id)
        data['image'] = (
            _normalize_media_url(product.main_image) or _normalize_media_url(product.cover)
            if product
            else None
        )
    return data


def serialize_order_asset_deduction(item: OrderAssetDeduction) -> dict[str, Any]:
    return {
        'id': item.id,
        'order_id': item.order_id,
        'asset_type': item.asset_type,
        'deduct_amount': money(item.deduct_amount),
        'deduct_rate': money(item.deduct_rate) if item.deduct_rate is not None else None,
        'created_at': iso_datetime(item.created_at),
    }


def serialize_favorite_product(db: Session, favorite: UserFavoriteProduct) -> dict[str, Any]:
    product = db.get(Product, favorite.product_id)
    if not product:
        return {
            'id': favorite.id,
            'favorite_id': favorite.id,
            'product_id': favorite.product_id,
            'created_at': iso_datetime(favorite.created_at),
        }
    data = serialize_product(db, product)
    data.update({
        'favorite_id': favorite.id,
        'favorited_at': iso_datetime(favorite.created_at),
        'is_favorite': True,
    })
    return data


def serialize_footprint(db: Session, footprint: UserProductFootprint) -> dict[str, Any]:
    product = db.get(Product, footprint.product_id)
    if not product:
        return {
            'id': footprint.id,
            'footprint_id': footprint.id,
            'product_id': footprint.product_id,
            'view_count': footprint.view_count,
            'last_viewed_at': iso_datetime(footprint.last_viewed_at),
        }
    data = serialize_product(db, product)
    data.update({
        'footprint_id': footprint.id,
        'view_count': footprint.view_count,
        'last_viewed_at': iso_datetime(footprint.last_viewed_at),
    })
    return data


def serialize_cart_item(db: Session, item: ShoppingCartItem) -> dict[str, Any]:
    product = db.get(Product, item.product_id)
    subtotal = money(Decimal(str(product.sale_price)) * item.quantity) if product else 0
    payload: dict[str, Any] = {
        'id': item.id,
        'cart_item_id': item.id,
        'product_id': item.product_id,
        'sku_id': item.sku_id,
        'quantity': item.quantity,
        'selected': bool(item.selected),
        'created_at': iso_datetime(item.created_at),
        'updated_at': iso_datetime(item.updated_at),
        'subtotal_amount': subtotal,
    }
    if not product:
        return payload
    payload.update({
        'product': serialize_product(db, product),
        'title': product.product_name,
        'name': product.product_name,
        'price': money(product.sale_price),
        'image': _normalize_media_url(product.main_image) or _normalize_media_url(product.cover),
        'stock': product.stock,
        'zone_type': enum_value(product.zone_type),
    })
    return payload


def _shipment_items(db: Session, order: Order) -> list[OrderItem]:
    return db.query(OrderItem).filter(OrderItem.order_id == order.id).order_by(OrderItem.id.asc()).all()


def _shipment_status(order: Order) -> tuple[str, str]:
    order_status = enum_value(order.order_status)
    if order_status == enum_value(OrderStatus.COMPLETED):
        return 'delivered', '已签收'
    if order_status == enum_value(OrderStatus.SHIPPED):
        return 'shipping', '运输中'
    return 'pending', '待发货'


def _shipment_contact_info(db: Session, items: list[OrderItem]) -> tuple[str, str | None, str]:
    for item in items:
        product = db.get(Product, item.product_id)
        if not product:
            continue

        owner_type = enum_value(product.owner_type)
        if owner_type == 'SUPPLIER' and product.owner_id:
            supplier = db.get(Supplier, product.owner_id)
            if supplier:
                return supplier.supplier_name or '商家发货', supplier.contact_phone, '商家发货'

        if owner_type == 'LOCAL_MERCHANT' and product.owner_id:
            merchant = db.get(LocalLifeMerchant, product.owner_id)
            if merchant:
                return merchant.merchant_name or '同城配送', merchant.contact_phone, '同城配送'

    return 'Excellent 配送', None, '平台配送'


def _shipment_title(items: list[OrderItem], fallback: str) -> str:
    names = [item.product_name for item in items if item.product_name]
    if not names:
        return fallback
    if len(names) == 1:
        return names[0]
    return f'{names[0]} 等{len(names)}件商品'


def _shipment_status_hint(status: str) -> str:
    return {
        'pending': '订单已支付，商家正在备货，请留意后续更新。',
        'shipping': '包裹已发出，请保持电话畅通并留意物流更新。',
        'delivered': '包裹已签收，感谢你的耐心等待。',
    }[status]


def _shipment_progress(status: str) -> int:
    return {
        'pending': 36,
        'shipping': 72,
        'delivered': 100,
    }[status]


def _shipment_timeline(order: Order) -> list[dict[str, Any]]:
    status, _ = _shipment_status(order)
    return [
        {'title': '订单创建', 'time': iso_datetime(order.created_at), 'active': True},
        {'title': '支付成功', 'time': iso_datetime(order.paid_at or order.updated_at), 'active': enum_value(order.pay_status) == enum_value(PayStatus.PAID)},
        {'title': '包裹运输中', 'time': iso_datetime(order.updated_at), 'active': status in {'shipping', 'delivered'}},
        {'title': '包裹已签收', 'time': iso_datetime(order.confirmed_at), 'active': status == 'delivered'},
    ]


def serialize_shipment(db: Session, order: Order, include_detail: bool = False) -> dict[str, Any]:
    items = _shipment_items(db, order)
    status, status_text = _shipment_status(order)
    quantity = sum(int(item.quantity or 0) for item in items)
    carrier_name, carrier_phone, delivery_mode_text = _shipment_contact_info(db, items)
    latest_message = _shipment_status_hint(status)

    data = {
        'order_id': order.id,
        'order_no': order.order_no,
        'tracking_no': order.legacy_logistics_no,
        'carrier_name': order.legacy_logistics_name or carrier_name,
        'carrier_phone': carrier_phone,
        'delivery_mode_text': delivery_mode_text,
        'status': status,
        'status_text': status_text,
        'status_hint': latest_message,
        'title': _shipment_title(items, _order_title(db, order)),
        'quantity': quantity,
        'item_count': quantity,
        'item_names': [item.product_name for item in items if item.product_name],
        'amount': money(order.total_amount),
        'latest_message': latest_message,
        'updated_at': iso_datetime(order.updated_at),
        'created_at': iso_datetime(order.created_at),
        'paid_at': iso_datetime(order.paid_at),
        'confirmed_at': iso_datetime(order.confirmed_at),
        'timeline': _shipment_timeline(order),
        'progress_percent': _shipment_progress(status),
        'can_confirm': status == 'shipping',
    }
    if include_detail:
        data['items'] = [serialize_order_item(item, db) for item in items]
    return data


def serialize_admin_order(db: Session, order: Order, include_detail: bool = False) -> dict[str, Any]:
    user = db.get(User, order.user_id)
    team = db.get(Team, order.team_id) if order.team_id else None
    items = _shipment_items(db, order)
    products = [db.get(Product, item.product_id) for item in items]
    item_count = sum(int(item.quantity or 0) for item in items)
    item_names = [item.product_name for item in items if item.product_name]
    requires_shipping = any(bool(product.requires_shipping) for product in products if product)
    shipment = serialize_shipment(db, order, include_detail=include_detail) if requires_shipping else None

    data = serialize_order(db, order, include_detail=include_detail)
    data.update(
        {
            'user_nickname': user.nickname if user else None,
            'user_phone': user.phone if user else None,
            'user_status': enum_value(user.status) if user else None,
            'team_name': team.name if team else None,
            'item_count': item_count,
            'item_names': item_names,
            'products_summary': ' / '.join(item_names[:3]),
            'requires_shipping': requires_shipping,
            'can_ship': requires_shipping
            and enum_value(order.pay_status) == enum_value(PayStatus.PAID)
            and enum_value(order.order_status) == enum_value(OrderStatus.PENDING_SHIP),
            'shipment': shipment,
            'delivery_status': shipment['status'] if shipment else 'not_required',
            'delivery_status_text': shipment['status_text'] if shipment else '无需物流',
            'tracking_no': shipment['tracking_no'] if shipment else None,
            'delivery_mode_text': shipment['delivery_mode_text'] if shipment else None,
            'carrier_name': shipment['carrier_name'] if shipment else None,
            'carrier_phone': shipment['carrier_phone'] if shipment else None,
        }
    )

    if include_detail:
        data['user'] = {
            'id': user.id if user else None,
            'nickname': user.nickname if user else None,
            'phone': user.phone if user else None,
            'status': enum_value(user.status) if user else None,
            'global_role': enum_value(user.global_role) if user else None,
        }
        data['team'] = {
            'id': team.id if team else None,
            'name': team.name if team else None,
            'status': enum_value(team.status) if team else None,
        }
    return data
