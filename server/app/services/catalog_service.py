import csv
import io
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.payment_config import enabled_external_payment_channels
from app.models.enums import (
    AssetType,
    OrderStatus,
    OrderType,
    PayStatus,
    ProductOwnerType,
    ProductStatus,
    ProductType,
    QualificationStatus,
    SupplierStatus,
    ZoneType,
)
from app.models.local_life import LocalLifeMerchant
from app.models.order import Order, OrderAssetDeduction, OrderItem
from app.models.package import Package
from app.models.product import Product, ProductCategory, ProductQualification, ProductZoneConfig
from app.models.supplier import Supplier, SupplierAgreement
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService
from app.services.user_service import UserService
from app.utils.helpers import generate_order_no, now, quantize_amount
from app.utils.spreadsheet import load_tabular_rows


class PackageService:
    @staticmethod
    def list_packages(db: Session) -> list[Package]:
        return db.query(Package).filter(Package.status == ProductStatus.ON_SHELF).order_by(Package.id.desc()).all()

    @staticmethod
    def list_packages_for_admin(db: Session) -> list[Package]:
        return db.query(Package).order_by(Package.id.desc()).all()

    @staticmethod
    def get_package(db: Session, package_id: int) -> Package:
        package = db.get(Package, package_id)
        if not package:
            raise NotFoundError('Package not found')
        return package

    @staticmethod
    def _validate_package_payload(payload: dict) -> None:
        if not payload.get('package_name'):
            raise ConflictError('Package name required')
        if payload['package_price'] <= 0:
            raise ConflictError('Package price must be greater than 0')
        for field in ['voucher_reward_rate', 'referral_voucher_rate', 'ai_coupon_max_deduct_rate']:
            value = payload[field]
            if value < 0 or value > 100:
                raise ConflictError(f'{field} must be between 0 and 100')
        if payload['grants_product_quota'] < 0:
            raise ConflictError('grants_product_quota cannot be negative')

    @staticmethod
    def _package_order_count(db: Session, package_id: int) -> int:
        return int(
            db.query(func.count(Order.id)).filter(
                Order.order_type == OrderType.PACKAGE_ORDER,
                Order.source_ref_id == package_id,
            ).scalar() or 0
        )

    @staticmethod
    def create_for_admin(db: Session, payload: dict) -> Package:
        PackageService._validate_package_payload(payload)
        package = Package(
            package_name=payload['package_name'],
            package_price=payload['package_price'],
            package_type=payload['package_type'],
            voucher_reward_rate=payload['voucher_reward_rate'],
            referral_voucher_rate=payload['referral_voucher_rate'],
            ai_coupon_max_deduct_rate=payload['ai_coupon_max_deduct_rate'],
            grants_product_quota=payload['grants_product_quota'],
            points_subsidy_enabled=payload['points_subsidy_enabled'],
            status=ProductStatus.DRAFT,
        )
        db.add(package)
        db.commit()
        db.refresh(package)
        return package

    @staticmethod
    def update_for_admin(db: Session, package_id: int, payload: dict) -> Package:
        package = PackageService.get_package(db, package_id)
        PackageService._validate_package_payload(payload)
        package.package_name = payload['package_name']
        package.package_price = payload['package_price']
        package.package_type = payload['package_type']
        package.voucher_reward_rate = payload['voucher_reward_rate']
        package.referral_voucher_rate = payload['referral_voucher_rate']
        package.ai_coupon_max_deduct_rate = payload['ai_coupon_max_deduct_rate']
        package.grants_product_quota = payload['grants_product_quota']
        package.points_subsidy_enabled = payload['points_subsidy_enabled']
        db.commit()
        db.refresh(package)
        return package

    @staticmethod
    def update_status_for_admin(db: Session, package_id: int, status: ProductStatus) -> Package:
        package = PackageService.get_package(db, package_id)
        if status not in {ProductStatus.ON_SHELF, ProductStatus.OFF_SHELF}:
            raise ConflictError('Package status only supports ON_SHELF or OFF_SHELF')
        if status == ProductStatus.ON_SHELF and package.status not in {ProductStatus.DRAFT, ProductStatus.OFF_SHELF, ProductStatus.APPROVED}:
            raise ConflictError('Package cannot be put on shelf from current status')
        if status == ProductStatus.OFF_SHELF and package.status != ProductStatus.ON_SHELF:
            raise ConflictError('Only on-shelf package can be taken off shelf')
        package.status = status
        db.commit()
        db.refresh(package)
        return package

    @staticmethod
    def delete_for_admin(db: Session, package_id: int) -> None:
        package = PackageService.get_package(db, package_id)
        if package.status == ProductStatus.ON_SHELF:
            raise ConflictError('On-shelf package cannot be deleted')
        if PackageService._package_order_count(db, package.id) > 0:
            raise ConflictError('Package with orders cannot be deleted')
        db.delete(package)
        db.commit()

    @staticmethod
    def my_qualifications(db: Session, user_id: int) -> list[dict]:
        rows = db.query(Order, Package).join(Package, Order.source_ref_id == Package.id).filter(
            Order.user_id == user_id,
            Order.order_type == OrderType.PACKAGE_ORDER,
            Order.pay_status == PayStatus.PAID,
        ).order_by(Order.id.desc()).all()
        return [
            {
                'order_id': order.id,
                'package_id': package.id,
                'package_name': package.package_name,
                'paid_amount': float(order.paid_amount),
                'paid_at': order.paid_at.isoformat() if order.paid_at else None,
                'order_status': order.order_status.value,
                'grants_product_quota': package.grants_product_quota,
            }
            for order, package in rows
        ]

    @staticmethod
    def create_package_order(db: Session, current_user_id: int, package_id: int, use_ai_coupon_amount: float = 0) -> Order:
        package = PackageService.get_package(db, package_id)
        if package.status != ProductStatus.ON_SHELF:
            raise ConflictError('Package unavailable')

        package_price = quantize_amount(package.package_price)
        ai_limit = quantize_amount(Decimal(str(package.package_price)) * Decimal(str(package.ai_coupon_max_deduct_rate)) / Decimal('100'))
        requested_ai = quantize_amount(use_ai_coupon_amount)
        use_ai = min(ai_limit, requested_ai)

        order = Order(
            order_no=generate_order_no('PK'),
            user_id=current_user_id,
            order_type=OrderType.PACKAGE_ORDER,
            source_ref_id=package.id,
            total_amount=package_price,
            discount_amount=0,
            payable_amount=package_price,
            paid_amount=0,
            pay_status=PayStatus.UNPAID,
            order_status=OrderStatus.PENDING_PAYMENT,
        )
        db.add(order)
        db.flush()

        if use_ai > 0:
            AssetService.consume_amount(
                db,
                current_user_id,
                AssetType.AI_COUPON,
                use_ai,
                'PACKAGE_AI_DEDUCT',
                source_id=order.id,
                source_no=order.order_no,
            )
            db.add(
                OrderAssetDeduction(
                    order_id=order.id,
                    asset_type=AssetType.AI_COUPON.value,
                    deduct_amount=use_ai,
                    deduct_rate=package.ai_coupon_max_deduct_rate,
                    created_at=now(),
                )
            )

        order.discount_amount = use_ai
        order.payable_amount = max(package_price - use_ai, Decimal('0.00'))
        order.paid_amount = Decimal('0.00')
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def handle_paid_package_order(db: Session, order: Order) -> None:
        if order.source_ref_id is None:
            raise NotFoundError('Package not found')
        package = PackageService.get_package(db, int(order.source_ref_id))
        voucher_reward = quantize_amount(Decimal(str(order.total_amount)) * Decimal(str(package.voucher_reward_rate)) / Decimal('100'))
        if voucher_reward > 0:
            AssetService.add_amount(
                db,
                order.user_id,
                AssetType.VOUCHER,
                voucher_reward,
                'PACKAGE_REWARD',
                source_id=order.id,
                source_no=order.order_no,
            )

        if package.points_subsidy_enabled:
            AssetService.add_amount(
                db,
                order.user_id,
                AssetType.POINTS,
                order.total_amount,
                'POINTS_SUBSIDY',
                source_id=order.id,
                source_no=order.order_no,
            )

        buyer = db.get(User, order.user_id)
        if buyer and buyer.parent_id:
            referral_voucher = quantize_amount(Decimal(str(order.total_amount)) * Decimal(str(package.referral_voucher_rate)) / Decimal('100'))
            if referral_voucher > 0:
                AssetService.add_amount(
                    db,
                    buyer.parent_id,
                    AssetType.VOUCHER,
                    referral_voucher,
                    'PACKAGE_REFERRAL_REWARD',
                    source_id=order.id,
                    source_no=order.order_no,
                    remark=f'from user {buyer.id}',
                )


class ProductService:
    SUPPLIER_PRICE_LIMIT_RATE = Decimal('0.20')
    IMPORT_TEMPLATE_HEADERS = [
        '商品ID',
        '商品名称',
        '分类ID',
        '专区',
        '商品类型',
        '归属类型',
        '归属ID',
        '售价',
        '市场价',
        '成本价',
        '库存',
        '主图',
        '封面图',
        '轮播图',
        '品牌',
        '简介',
        '详情',
        '卖点',
        '排序',
        '爆款推荐标记',
        '需要物流',
        '一件代发',
    ]
    IMPORT_TEMPLATE_HEADERS += [
        '是否需套餐资格',
        '套餐ID',
        '复购折扣率',
        '兑换券最低抵扣比例',
        '兑换券最高抵扣比例',
        '购物返AI券比例',
        'AI券最大抵扣比例',
        '余额支付',
        '支付宝支付',
        '微信支付',
        '开启闪购',
        '每人限购件数',
        '分佣规则ID',
        '设备收益联动',
    ]
    IMPORT_FIELD_ALIASES = {
        'id': ['商品ID', 'ID', 'id', 'product_id'],
        'product_name': ['商品名称', '名称', 'product_name', 'name', 'title'],
        'category_id': ['分类ID', '商品分类ID', 'category_id'],
        'zone_type': ['专区', '专区类型', 'zone_type', 'zone'],
        'product_type': ['商品类型', '类型', 'product_type'],
        'owner_type': ['归属类型', 'owner_type'],
        'owner_id': ['归属ID', '归属id', 'owner_id'],
        'sale_price': ['售价', '销售价', 'sale_price', 'price'],
        'market_price': ['市场价', '原价', 'market_price'],
        'cost_price': ['成本价', 'cost_price'],
        'stock': ['库存', 'stock'],
        'main_image': ['主图', '主图地址', 'main_image', 'image'],
        'cover': ['封面图', 'cover'],
        'icons': ['轮播图', '图集', 'icons', 'gallery'],
        'brand': ['品牌', 'brand'],
        'profile': ['简介', '商品简介', 'profile', 'summary'],
        'detail': ['详情', '商品详情', 'detail', 'description'],
        'feature': ['卖点', '特色', 'feature'],
        'order_by': ['排序', '排序值', 'order_by', 'sort'],
        'is_hot': ['爆款推荐标记', '爆款推荐', '爆款', '热门商品', '热门', 'is_hot', 'hot'],
        'requires_shipping': ['需要物流', 'requires_shipping', 'shipping'],
        'drop_shipping_enabled': ['一件代发', '代发', 'drop_shipping_enabled'],
    }
    IMPORT_ZONE_MAPPING = {
        'REPURCHASE': ZoneType.REPURCHASE,
        '复购区': ZoneType.REPURCHASE,
        'SELF_OPERATED': ZoneType.SELF_OPERATED,
        '自营商城': ZoneType.SELF_OPERATED,
        '平台自营': ZoneType.SELF_OPERATED,
        'HOT_SALE': ZoneType.HOT_SALE,
        '爆款区': ZoneType.HOT_SALE,
        'LOCAL_LIFE': ZoneType.LOCAL_LIFE,
        '本地生活': ZoneType.LOCAL_LIFE,
    }
    IMPORT_PRODUCT_TYPE_MAPPING = {
        'PHYSICAL': ProductType.PHYSICAL,
        '实物商品': ProductType.PHYSICAL,
        'SERVICE': ProductType.SERVICE,
        '服务商品': ProductType.SERVICE,
        'ACTIVITY': ProductType.ACTIVITY,
        '活动商品': ProductType.ACTIVITY,
    }
    IMPORT_OWNER_TYPE_MAPPING = {
        'SELF_OPERATED': ProductOwnerType.SELF_OPERATED,
        '平台自营': ProductOwnerType.SELF_OPERATED,
        'SUPPLIER': ProductOwnerType.SUPPLIER,
        '供应商商品': ProductOwnerType.SUPPLIER,
        'LOCAL_MERCHANT': ProductOwnerType.LOCAL_MERCHANT,
        '本地商家': ProductOwnerType.LOCAL_MERCHANT,
    }
    IMPORT_FIELD_ALIASES.update({
        'package_required': ['是否需套餐资格', 'package_required'],
        'package_id': ['套餐ID', 'package_id'],
        'repurchase_discount_rate': ['复购折扣率', 'repurchase_discount_rate'],
        'voucher_deduct_min_rate': ['兑换券最低抵扣比例', 'voucher_deduct_min_rate'],
        'voucher_deduct_max_rate': ['兑换券最高抵扣比例', 'voucher_deduct_max_rate'],
        'ai_coupon_reward_rate': ['购物返AI券比例', 'ai_coupon_reward_rate'],
        'ai_coupon_max_deduct_rate': ['AI券最大抵扣比例', 'ai_coupon_max_deduct_rate'],
        'points_purchase_enabled': ['积分支付', 'points_purchase_enabled'],
        'balance_purchase_enabled': ['余额支付', 'balance_purchase_enabled'],
        'alipay_purchase_enabled': ['支付宝支付', 'alipay_purchase_enabled'],
        'wechat_purchase_enabled': ['微信支付', 'wechat_purchase_enabled'],
        'points_only_enabled': ['纯积分购买', 'points_only_enabled'],
        'points_cash_enabled': ['积分加现金购买', 'points_cash_enabled'],
        'cash_only_enabled': ['纯现金购买', 'cash_only_enabled'],
        'balance_only_enabled': ['余额纯支付', 'balance_only_enabled'],
        'balance_points_enabled': ['余额加积分支付', 'balance_points_enabled'],
        'flash_sale_enabled': ['开启闪购', 'flash_sale_enabled'],
        'per_user_limit': ['每人限购件数', 'per_user_limit'],
        'merchant_commission_rule_id': ['分佣规则ID', 'merchant_commission_rule_id'],
        'device_revenue_enabled': ['设备收益联动', 'device_revenue_enabled'],
        'custom_commission_enabled': ['专属分润', 'custom_commission_enabled'],
        'custom_commission_method': ['专属分润方式', 'custom_commission_method'],
        'custom_commission_level1_rate': ['一级分润比例', 'custom_commission_level1_rate'],
        'custom_commission_level2_rate': ['二级分润比例', 'custom_commission_level2_rate'],
        'custom_commission_level3_rate': ['三级分润比例', 'custom_commission_level3_rate'],
        'custom_commission_level1_amount': ['一级固定分润', 'custom_commission_level1_amount'],
        'custom_commission_level2_amount': ['二级固定分润', 'custom_commission_level2_amount'],
        'custom_commission_level3_amount': ['三级固定分润', 'custom_commission_level3_amount'],
    })

    @staticmethod
    def zone_config_defaults(zone_type: ZoneType) -> dict:
        if zone_type == ZoneType.REPURCHASE:
            return {
                'package_required': True,
                'package_id': None,
                'repurchase_discount_rate': 60.0,
                'voucher_deduct_min_rate': None,
                'voucher_deduct_max_rate': None,
                'ai_coupon_reward_rate': None,
                'ai_coupon_max_deduct_rate': None,
                'points_purchase_enabled': True,
                'balance_purchase_enabled': True,
                'alipay_purchase_enabled': True,
                'wechat_purchase_enabled': False,
                'points_only_enabled': False,
                'points_cash_enabled': True,
                'cash_only_enabled': True,
                'balance_only_enabled': True,
                'balance_points_enabled': True,
                'flash_sale_enabled': False,
                'per_user_limit': None,
                'merchant_commission_rule_id': None,
                'device_revenue_enabled': False,
                'custom_commission_enabled': False,
                'custom_commission_method': 'RATE',
                'custom_commission_level1_rate': 0.0,
                'custom_commission_level2_rate': 0.0,
                'custom_commission_level3_rate': 0.0,
                'custom_commission_level1_amount': 0.0,
                'custom_commission_level2_amount': 0.0,
                'custom_commission_level3_amount': 0.0,
            }
        if zone_type == ZoneType.SELF_OPERATED:
            return {
                'package_required': False,
                'package_id': None,
                'repurchase_discount_rate': None,
                'voucher_deduct_min_rate': 50.0,
                'voucher_deduct_max_rate': 70.0,
                'ai_coupon_reward_rate': 20.0,
                'ai_coupon_max_deduct_rate': 20.0,
                'points_purchase_enabled': False,
                'balance_purchase_enabled': True,
                'alipay_purchase_enabled': True,
                'wechat_purchase_enabled': False,
                'points_only_enabled': False,
                'points_cash_enabled': True,
                'cash_only_enabled': True,
                'balance_only_enabled': True,
                'balance_points_enabled': True,
                'flash_sale_enabled': False,
                'per_user_limit': None,
                'merchant_commission_rule_id': None,
                'device_revenue_enabled': False,
                'custom_commission_enabled': False,
                'custom_commission_method': 'RATE',
                'custom_commission_level1_rate': 0.0,
                'custom_commission_level2_rate': 0.0,
                'custom_commission_level3_rate': 0.0,
                'custom_commission_level1_amount': 0.0,
                'custom_commission_level2_amount': 0.0,
                'custom_commission_level3_amount': 0.0,
            }
        if zone_type == ZoneType.HOT_SALE:
            return {
                'package_required': False,
                'package_id': None,
                'repurchase_discount_rate': None,
                'voucher_deduct_min_rate': None,
                'voucher_deduct_max_rate': None,
                'ai_coupon_reward_rate': None,
                'ai_coupon_max_deduct_rate': None,
                'points_purchase_enabled': True,
                'balance_purchase_enabled': True,
                'alipay_purchase_enabled': True,
                'wechat_purchase_enabled': False,
                'points_only_enabled': False,
                'points_cash_enabled': True,
                'cash_only_enabled': True,
                'balance_only_enabled': True,
                'balance_points_enabled': True,
                'flash_sale_enabled': True,
                'per_user_limit': 1,
                'merchant_commission_rule_id': None,
                'device_revenue_enabled': False,
                'custom_commission_enabled': False,
                'custom_commission_method': 'RATE',
                'custom_commission_level1_rate': 0.0,
                'custom_commission_level2_rate': 0.0,
                'custom_commission_level3_rate': 0.0,
                'custom_commission_level1_amount': 0.0,
                'custom_commission_level2_amount': 0.0,
                'custom_commission_level3_amount': 0.0,
            }
        return {
            'package_required': False,
            'package_id': None,
            'repurchase_discount_rate': None,
            'voucher_deduct_min_rate': None,
            'voucher_deduct_max_rate': None,
            'ai_coupon_reward_rate': None,
            'ai_coupon_max_deduct_rate': None,
            'points_purchase_enabled': True,
            'balance_purchase_enabled': True,
            'alipay_purchase_enabled': True,
            'wechat_purchase_enabled': False,
            'points_only_enabled': False,
            'points_cash_enabled': True,
            'cash_only_enabled': True,
            'balance_only_enabled': True,
            'balance_points_enabled': True,
            'flash_sale_enabled': False,
            'per_user_limit': None,
            'merchant_commission_rule_id': None,
            'device_revenue_enabled': True,
            'custom_commission_enabled': False,
            'custom_commission_method': 'RATE',
            'custom_commission_level1_rate': 0.0,
            'custom_commission_level2_rate': 0.0,
            'custom_commission_level3_rate': 0.0,
            'custom_commission_level1_amount': 0.0,
            'custom_commission_level2_amount': 0.0,
            'custom_commission_level3_amount': 0.0,
        }

    @staticmethod
    def is_legacy_product(product: Product | None) -> bool:
        if not product:
            return False
        return any((
            product.legacy_name,
            product.legacy_type is not None,
            product.legacy_price is not None,
        ))

    @staticmethod
    def is_visible_to_user(db: Session, current_user: User | None, product: Product | None) -> bool:
        if not product:
            return False
        if not ProductService.is_legacy_product(product):
            return True
        if not current_user:
            return False
        return UserService.is_legacy_user(db, current_user)

    @staticmethod
    def list_by_zone(db: Session, zone_type: str, current_user: User | None = None):
        rows = db.query(Product).filter(
            Product.zone_type == zone_type,
            Product.status == ProductStatus.ON_SHELF,
        ).order_by(Product.id.desc()).all()
        if not current_user:
            return rows
        return [item for item in rows if ProductService.is_visible_to_user(db, current_user, item)]

    @staticmethod
    def list_app_products(db: Session, keyword: str | None = None, current_user: User | None = None):
        query = db.query(Product).filter(Product.status == ProductStatus.ON_SHELF)
        if keyword:
            query = query.filter(Product.product_name.like(f'%{keyword.strip()}%'))
        rows = query.order_by(Product.is_hot.desc(), Product.order_by.desc(), Product.id.desc()).all()
        if not current_user:
            return rows
        return [item for item in rows if ProductService.is_visible_to_user(db, current_user, item)]

    @staticmethod
    def get_product(db: Session, product_id: int, current_user: User | None = None):
        product = db.get(Product, product_id)
        if current_user and product and not ProductService.is_visible_to_user(db, current_user, product):
            return None
        return product

    @staticmethod
    def _validate_product_payload(payload: dict) -> None:
        payload['zone_type'] = payload.get('zone_type') or ZoneType.SELF_OPERATED
        payload['product_name'] = str(payload.get('product_name') or '').strip()
        if not payload['product_name']:
            raise ConflictError('Product name required')
        if payload['product_type'] == ProductType.PACKAGE:
            raise ConflictError('Package should be managed in package module')
        if payload['sale_price'] <= 0:
            raise ConflictError('Sale price must be greater than 0')
        if payload.get('market_price') is not None and payload['market_price'] <= 0:
            raise ConflictError('Market price must be greater than 0')
        if payload.get('cost_price') is not None and payload['cost_price'] < 0:
            raise ConflictError('Cost price cannot be negative')
        if payload['stock'] < 0:
            raise ConflictError('Stock cannot be negative')
        if payload.get('market_price') is not None and payload['market_price'] < payload['sale_price']:
            raise ConflictError('Market price cannot be less than sale price')
        if payload['zone_type'] == ZoneType.LOCAL_LIFE and payload['product_type'] != ProductType.SERVICE:
            raise ConflictError('Local-life zone must use service product type')
        if payload.get('order_by') is not None and payload['order_by'] < 0:
            raise ConflictError('Order_by cannot be negative')
        for field in ('main_image', 'cover', 'icons', 'brand', 'profile', 'detail', 'feature'):
            if field in payload:
                value = payload.get(field)
                payload[field] = str(value).strip() if value is not None and str(value).strip() else None

    @staticmethod
    def _ensure_active_category(db: Session, category_id: int | None) -> ProductCategory:
        if not category_id:
            raise ConflictError('Product category required')
        category = db.get(ProductCategory, category_id)
        if not category:
            raise NotFoundError('Product category not found')
        if category.status != 'active':
            raise ConflictError('Product category is disabled')
        return category

    @staticmethod
    def _admin_product_query(db: Session, current_user: User):
        query = db.query(Product)
        if AdminScopeService.has_global_scope(current_user):
            return query

        team_user_ids = AdminScopeService.team_user_ids_subquery(current_user)
        supplier_ids = select(Supplier.id).where(Supplier.user_id.in_(team_user_ids))
        merchant_ids = select(LocalLifeMerchant.id).where(LocalLifeMerchant.owner_user_id.in_(team_user_ids))
        return query.filter(
            or_(
                (Product.owner_type == ProductOwnerType.SELF_OPERATED) & (Product.owner_id.in_(team_user_ids)),
                (Product.owner_type == ProductOwnerType.SUPPLIER) & (Product.owner_id.in_(supplier_ids)),
                (Product.owner_type == ProductOwnerType.LOCAL_MERCHANT) & (Product.owner_id.in_(merchant_ids)),
            )
        )

    @staticmethod
    def _resolve_owner(db: Session, current_user: User, owner_type: ProductOwnerType, owner_id: int | None) -> tuple[ProductOwnerType, int]:
        if owner_type == ProductOwnerType.SELF_OPERATED:
            resolved_owner_id = owner_id or current_user.id
            owner_user = db.get(User, resolved_owner_id)
            if not owner_user:
                raise NotFoundError('Owner user not found')
            if not AdminScopeService.has_global_scope(current_user):
                AdminScopeService.ensure_user_visible(current_user, owner_user)
            return owner_type, resolved_owner_id

        if owner_type == ProductOwnerType.SUPPLIER:
            if not owner_id:
                raise ConflictError('Supplier owner_id required')
            supplier = db.get(Supplier, owner_id)
            if not supplier:
                raise NotFoundError('Supplier not found')
            supplier_user = db.get(User, supplier.user_id)
            if supplier_user and not AdminScopeService.has_global_scope(current_user):
                AdminScopeService.ensure_user_visible(current_user, supplier_user)
            return owner_type, supplier.id

        if not owner_id:
            raise ConflictError('Local merchant owner_id required')
        merchant = db.get(LocalLifeMerchant, owner_id)
        if not merchant:
            raise NotFoundError('Local merchant not found')
        merchant_owner = db.get(User, merchant.owner_user_id)
        if merchant_owner and not AdminScopeService.has_global_scope(current_user):
            AdminScopeService.ensure_user_visible(current_user, merchant_owner)
        return owner_type, merchant.id

    @staticmethod
    def _product_order_count(db: Session, product_id: int) -> int:
        return int(
            db.query(func.count(OrderItem.id)).filter(OrderItem.product_id == product_id).scalar() or 0
        )

    @staticmethod
    def _supplier_active_agreement(db: Session, supplier_id: int) -> SupplierAgreement | None:
        return db.query(SupplierAgreement).filter(
            SupplierAgreement.supplier_id == supplier_id,
            SupplierAgreement.is_active.is_(True),
        ).order_by(SupplierAgreement.id.desc()).first()

    @staticmethod
    def _approved_supplier_product_qualification(db: Session, product_id: int, supplier_id: int) -> ProductQualification | None:
        return db.query(ProductQualification).filter(
            ProductQualification.product_id == product_id,
            ProductQualification.supplier_id == supplier_id,
            ProductQualification.audit_status == QualificationStatus.APPROVED,
        ).order_by(ProductQualification.id.desc()).first()

    @staticmethod
    def _build_supplier_publish_guard(db: Session, product: Product) -> dict:
        if product.owner_type != ProductOwnerType.SUPPLIER or not product.owner_id:
            return {
                'required': False,
                'eligible': True,
                'reason': '非招商商品无需资格校验',
                'supplier_id': None,
                'supplier_status': None,
                'agreement_active': None,
                'qualification_id': None,
                'qualification_type': None,
                'price_ratio': None,
                'drop_shipping_enabled': bool(product.drop_shipping_enabled),
            }

        supplier = db.get(Supplier, product.owner_id)
        if not supplier:
            return {
                'required': True,
                'eligible': False,
                'reason': '供应商不存在',
                'supplier_id': product.owner_id,
                'supplier_status': None,
                'agreement_active': False,
                'qualification_id': None,
                'qualification_type': None,
                'price_ratio': None,
                'drop_shipping_enabled': bool(product.drop_shipping_enabled),
            }

        agreement = ProductService._supplier_active_agreement(db, supplier.id)
        qualification = ProductService._approved_supplier_product_qualification(db, product.id, supplier.id)

        price_ratio = None
        price_ok = False
        if product.market_price is not None and Decimal(str(product.market_price)) > 0:
            price_ratio = (
                quantize_amount(product.sale_price) / quantize_amount(product.market_price) * Decimal('100')
            ).quantize(Decimal('0.01'))
            price_ok = quantize_amount(product.sale_price) <= quantize_amount(
                Decimal(str(product.market_price)) * ProductService.SUPPLIER_PRICE_LIMIT_RATE
            )

        if supplier.status not in {SupplierStatus.APPROVED, SupplierStatus.ACTIVE}:
            reason = '供应商状态未通过'
            eligible = False
        elif not agreement:
            reason = '缺少有效供应商协议'
            eligible = False
        elif not product.drop_shipping_enabled:
            reason = '未开启一件代发'
            eligible = False
        elif not price_ok:
            reason = '未满足市场价 2 折红线'
            eligible = False
        elif not qualification:
            reason = '缺少已通过的上架资格'
            eligible = False
        else:
            reason = '可提审/上架'
            eligible = True

        return {
            'required': True,
            'eligible': eligible,
            'reason': reason,
            'supplier_id': supplier.id,
            'supplier_status': supplier.status.value,
            'agreement_active': bool(agreement),
            'qualification_id': qualification.id if qualification else None,
            'qualification_type': qualification.qualification_type.value if qualification else None,
            'price_ratio': float(price_ratio) if price_ratio is not None else None,
            'drop_shipping_enabled': bool(product.drop_shipping_enabled),
        }

    @staticmethod
    def _ensure_supplier_product_publishable(db: Session, product: Product) -> None:
        guard = ProductService._build_supplier_publish_guard(db, product)
        if guard['required'] and not guard['eligible']:
            raise ConflictError(guard['reason'])

    @staticmethod
    def _serialize_zone_config_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        return value

    @staticmethod
    def _zone_config_snapshot(db: Session, product: Product) -> dict[str, Any]:
        config = db.query(ProductZoneConfig).filter(ProductZoneConfig.product_id == product.id).first()
        defaults = ProductService.zone_config_defaults(product.zone_type)
        data: dict[str, Any] = {
            'product_id': product.id,
            'zone_type': product.zone_type.value,
            'configured': bool(config),
            'alipay_provider_ready': 'ALIPAY' in enabled_external_payment_channels(),
            'wechat_provider_ready': False,
        }
        for key, value in defaults.items():
            current = getattr(config, key) if config and getattr(config, key) is not None else value
            data[key] = ProductService._serialize_zone_config_value(current)
        return data

    @staticmethod
    def _zone_config_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
        zone_type = snapshot['zone_type']
        badges: list[str] = []
        description = ''
        headline = '默认规则'

        if zone_type == ZoneType.REPURCHASE.value:
            headline = '复购资格与支付规则'
            badges.append('需套餐资格' if snapshot.get('package_required') else '无需套餐资格')
            if snapshot.get('repurchase_discount_rate') is not None:
                badges.append(f"复购折扣 {snapshot['repurchase_discount_rate']:g}%")
            description = '影响复购专区的资格校验、折扣和支付方式。'
        elif zone_type == ZoneType.SELF_OPERATED.value:
            headline = '券抵扣与 AI 券规则'
            if snapshot.get('voucher_deduct_min_rate') is not None and snapshot.get('voucher_deduct_max_rate') is not None:
                badges.append(
                    f"兑换券 {snapshot['voucher_deduct_min_rate']:g}-{snapshot['voucher_deduct_max_rate']:g}%"
                )
            if snapshot.get('ai_coupon_reward_rate') is not None:
                badges.append(f"购物返 AI 券 {snapshot['ai_coupon_reward_rate']:g}%")
            if snapshot.get('ai_coupon_max_deduct_rate') is not None:
                badges.append(f"AI 券最高抵扣 {snapshot['ai_coupon_max_deduct_rate']:g}%")
            description = '影响自营商城的券类抵扣、返券比例和转化玩法。'
        elif zone_type == ZoneType.HOT_SALE.value:
            headline = '限购与闪购规则'
            if snapshot.get('flash_sale_enabled'):
                badges.append('开启闪购')
            if snapshot.get('per_user_limit') is not None:
                badges.append(f"每人限购 {snapshot['per_user_limit']} 件")
            description = '影响爆款区的活动玩法、支付方式和限购约束。'
        else:
            headline = '本地生活分佣规则'
            if snapshot.get('merchant_commission_rule_id'):
                badges.append(f"分佣规则 #{snapshot['merchant_commission_rule_id']}")
            if snapshot.get('device_revenue_enabled'):
                badges.append('联动设备收益')
            description = '影响到店服务的分佣、设备收益和支付规则。'

        payment_badges = [
            '余额支付' if snapshot.get('balance_purchase_enabled') else None,
            '支付宝支付' if snapshot.get('alipay_purchase_enabled') else None,
            '微信开发中',
        ]
        commission_badges = []
        if snapshot.get('custom_commission_enabled'):
            method = snapshot.get('custom_commission_method')
            suffix = '%' if method == 'RATE' else '元/件'
            values = [snapshot.get(f'custom_commission_level{level}_{"rate" if method == "RATE" else "amount"}', 0) for level in range(1, 4)]
            commission_badges.append(f'专属分润 {"/".join(f"{value:g}" for value in values)}{suffix}')
        else:
            commission_badges.append('未配置分润')
        badges = [item for item in payment_badges if item] + commission_badges + badges

        return {
            'configured': bool(snapshot.get('configured')),
            'headline': headline,
            'badges': badges[:4],
            'description': description,
        }

    @staticmethod
    def _serialize_product_for_admin(db: Session, product: Product) -> dict:
        from app.api.v1.mobile_serializers import serialize_product

        owner_name = None
        if product.owner_type == ProductOwnerType.SELF_OPERATED and product.owner_id:
            owner = db.get(User, product.owner_id)
            owner_name = owner.nickname if owner else None
        elif product.owner_type == ProductOwnerType.SUPPLIER and product.owner_id:
            supplier = db.get(Supplier, product.owner_id)
            owner_name = supplier.supplier_name if supplier else None
        elif product.owner_type == ProductOwnerType.LOCAL_MERCHANT and product.owner_id:
            merchant = db.get(LocalLifeMerchant, product.owner_id)
            owner_name = merchant.merchant_name if merchant else None

        mobile_payload = serialize_product(db, product)
        zone_config = ProductService._zone_config_snapshot(db, product)

        return {
            'id': product.id,
            'is_legacy_product': ProductService.is_legacy_product(product),
            'product_name': product.product_name,
            'product_type': product.product_type.value,
            'owner_type': product.owner_type.value,
            'owner_id': product.owner_id,
            'owner_name': owner_name,
            'zone_type': product.zone_type.value,
            'category_id': product.category_id,
            'market_price': float(product.market_price) if product.market_price is not None else None,
            'sale_price': float(product.sale_price),
            'cost_price': float(product.cost_price) if product.cost_price is not None else None,
            'stock': product.stock,
            'sold_count': product.sold_count,
            'main_image': product.main_image,
            'image': product.main_image or product.cover,
            'status': product.status.value,
            'requires_shipping': bool(product.requires_shipping),
            'drop_shipping_enabled': bool(product.drop_shipping_enabled),
            'name': product.legacy_name,
            'profile': product.profile,
            'detail': product.detail,
            'description': mobile_payload.get('description') or product.profile,
            'cover': mobile_payload.get('cover') or product.cover,
            'icons': product.icons,
            'type': product.legacy_type,
            'store_id': product.store_id,
            'brand': product.brand,
            'column_type': product.column_type,
            'order_by': product.order_by,
            'state': product.state,
            'is_hot': product.is_hot,
            'old_price': float(product.old_price) if product.old_price is not None else None,
            'price': float(product.legacy_price) if product.legacy_price is not None else None,
            'hehuoren_price': float(product.hehuoren_price) if product.hehuoren_price is not None else None,
            'xiaofeijin_price': float(product.xiaofeijin_price) if product.xiaofeijin_price is not None else None,
            'create_by': product.create_by,
            'create_time': product.create_time.isoformat() if product.create_time else None,
            'update_by': product.update_by,
            'update_time': product.update_time.isoformat() if product.update_time else None,
            'verify_state': product.verify_state,
            'verify_by': product.verify_by,
            'verify_time': product.verify_time.isoformat() if product.verify_time else None,
            'verify_remark': product.verify_remark,
            'dept_id': product.dept_id,
            'is_delete': product.is_delete,
            'is_integral': product.is_integral,
            'group_buy': product.group_buy,
            'group_buy_num': product.group_buy_num,
            'group_buy_rate': float(product.group_buy_rate) if product.group_buy_rate is not None else None,
            'is_flash_kill': product.is_flash_kill,
            'flash_kill_rate': float(product.flash_kill_rate) if product.flash_kill_rate is not None else None,
            'sales_volume': product.sales_volume,
            'use_num': product.use_num,
            'discount_rate': float(product.discount_rate) if product.discount_rate is not None else None,
            'feature': product.feature,
            'direct_rate': float(product.direct_rate) if product.direct_rate is not None else None,
            'tag': mobile_payload.get('tag'),
            'category_name': mobile_payload.get('category_name'),
            'gallery': mobile_payload.get('gallery') or [],
            'gallery_count': len(mobile_payload.get('gallery') or []),
            'features': mobile_payload.get('features') or [],
            'items': mobile_payload.get('items') or [],
            'mobile_preview': {
                'title': mobile_payload.get('title') or product.product_name,
                'description': mobile_payload.get('description') or '',
                'image': mobile_payload.get('image') or product.main_image or product.cover,
                'price': mobile_payload.get('price'),
                'market_price': mobile_payload.get('market_price'),
                'tag': mobile_payload.get('tag'),
                'category_name': mobile_payload.get('category_name'),
                'gallery_count': len(mobile_payload.get('gallery') or []),
                'features': mobile_payload.get('features') or [],
                'items': mobile_payload.get('items') or [],
                'requires_shipping': bool(mobile_payload.get('requires_shipping')),
                'drop_shipping_enabled': bool(mobile_payload.get('drop_shipping_enabled')),
            },
            'zone_config': zone_config,
            'points_only_enabled': bool(zone_config.get('points_only_enabled')),
            'points_cash_enabled': bool(zone_config.get('points_cash_enabled')),
            'cash_only_enabled': bool(zone_config.get('cash_only_enabled')),
            'balance_only_enabled': bool(zone_config.get('balance_only_enabled')),
            'balance_points_enabled': bool(zone_config.get('balance_points_enabled')),
            'zone_rule_summary': ProductService._zone_config_summary(zone_config),
            'created_at': product.created_at.isoformat() if product.created_at else None,
            'updated_at': product.updated_at.isoformat() if product.updated_at else None,
            'publish_guard': ProductService._build_supplier_publish_guard(db, product),
        }

    @staticmethod
    def create_for_admin(db: Session, current_user: User, payload: dict) -> Product:
        ProductService._validate_product_payload(payload)
        category = ProductService._ensure_active_category(db, payload.get('category_id'))
        owner_type, owner_id = ProductService._resolve_owner(
            db,
            current_user,
            payload.get('owner_type', ProductOwnerType.SELF_OPERATED),
            payload.get('owner_id'),
        )
        requires_shipping = payload['requires_shipping'] if payload['zone_type'] != ZoneType.LOCAL_LIFE else False

        product = Product(
            product_name=payload['product_name'],
            product_type=payload['product_type'],
            owner_type=owner_type,
            owner_id=owner_id,
            zone_type=payload['zone_type'],
            category_id=category.id,
            market_price=payload.get('market_price'),
            sale_price=payload['sale_price'],
            cost_price=payload.get('cost_price'),
            stock=payload['stock'],
            sold_count=0,
            main_image=payload.get('main_image'),
            cover=payload.get('cover') or payload.get('main_image'),
            icons=payload.get('icons'),
            brand=payload.get('brand'),
            profile=payload.get('profile'),
            detail=payload.get('detail'),
            feature=payload.get('feature'),
            order_by=payload.get('order_by'),
            is_hot=1 if payload.get('is_hot') else 0,
            status=ProductStatus.DRAFT,
            requires_shipping=requires_shipping,
            drop_shipping_enabled=payload.get('drop_shipping_enabled', False),
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def batch_update_merchandise_for_admin(db: Session, current_user: User, payload: dict[str, Any]) -> dict[str, Any]:
        product_ids = [int(item) for item in payload.get('product_ids', []) if item]
        if not product_ids:
            raise ConflictError('product_ids required')

        is_hot = payload.get('is_hot')
        order_by_start = payload.get('order_by_start')
        order_by_step = int(payload.get('order_by_step') or 1)
        if is_hot is None and order_by_start is None:
            raise ConflictError('At least one batch merchandise change is required')
        if order_by_step <= 0:
            raise ConflictError('order_by_step must be greater than 0')

        rows = ProductService._admin_product_query(db, current_user).filter(Product.id.in_(product_ids)).all()
        row_map = {item.id: item for item in rows}
        visible_ids = [product_id for product_id in product_ids if product_id in row_map]
        if len(visible_ids) != len(dict.fromkeys(product_ids)):
            raise ConflictError('Some selected products are not visible or do not exist')

        for index, product_id in enumerate(visible_ids):
            product = row_map[product_id]
            if is_hot is not None:
                product.is_hot = 1 if is_hot else 0
            if order_by_start is not None:
                next_order = order_by_start - index * order_by_step
                if next_order < 0:
                    raise ConflictError('Calculated order_by cannot be negative')
                product.order_by = next_order

        db.commit()
        return {'updated_count': len(visible_ids), 'product_ids': visible_ids}

    @staticmethod
    def update_for_admin(db: Session, product_id: int, current_user: User, payload: dict) -> Product:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        ProductService._validate_product_payload(payload)
        category = ProductService._ensure_active_category(db, payload.get('category_id'))

        order_count = ProductService._product_order_count(db, product.id)
        if order_count > 0 and payload['zone_type'] != product.zone_type:
            raise ConflictError('Product with orders cannot change zone type')
        if order_count > 0 and payload['product_type'] != product.product_type:
            raise ConflictError('Product with orders cannot change product type')

        owner_type, owner_id = ProductService._resolve_owner(
            db,
            current_user,
            payload.get('owner_type', product.owner_type),
            payload.get('owner_id') or product.owner_id,
        )
        if order_count > 0 and (owner_type != product.owner_type or owner_id != product.owner_id):
            raise ConflictError('Product with orders cannot change owner')

        product.product_name = payload['product_name']
        product.product_type = payload['product_type']
        product.owner_type = owner_type
        product.owner_id = owner_id
        product.zone_type = payload['zone_type']
        product.category_id = category.id
        product.market_price = payload.get('market_price')
        product.sale_price = payload['sale_price']
        product.cost_price = payload.get('cost_price')
        product.stock = payload['stock']
        product.main_image = payload.get('main_image')
        product.cover = payload.get('cover') or payload.get('main_image')
        product.icons = payload.get('icons')
        product.brand = payload.get('brand')
        product.profile = payload.get('profile')
        product.detail = payload.get('detail')
        product.feature = payload.get('feature')
        product.order_by = payload.get('order_by')
        product.is_hot = 1 if payload.get('is_hot') else 0
        product.requires_shipping = payload['requires_shipping'] if payload['zone_type'] != ZoneType.LOCAL_LIFE else False
        product.drop_shipping_enabled = payload.get('drop_shipping_enabled', False)

        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def submit_review_for_admin(db: Session, product_id: int, current_user: User) -> Product:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        if product.status not in {ProductStatus.DRAFT, ProductStatus.REJECTED}:
            raise ConflictError('Only draft or rejected products can submit review')
        ProductService._ensure_supplier_product_publishable(db, product)
        product.status = ProductStatus.PENDING_REVIEW
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def audit_for_admin(db: Session, product_id: int, current_user: User, audit_status: ProductStatus) -> Product:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        if product.status != ProductStatus.PENDING_REVIEW:
            raise ConflictError('Only pending-review products can be audited')
        if audit_status not in {ProductStatus.APPROVED, ProductStatus.REJECTED}:
            raise ConflictError('Audit status must be APPROVED or REJECTED')
        if audit_status == ProductStatus.APPROVED:
            ProductService._ensure_supplier_product_publishable(db, product)
        product.status = audit_status
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update_status_for_admin(db: Session, product_id: int, current_user: User, target_status: ProductStatus) -> Product:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        if target_status not in {ProductStatus.ON_SHELF, ProductStatus.OFF_SHELF}:
            raise ConflictError('Status update only supports ON_SHELF or OFF_SHELF')
        if target_status == ProductStatus.ON_SHELF and product.status not in {ProductStatus.APPROVED, ProductStatus.OFF_SHELF}:
            raise ConflictError('Only approved or off-shelf products can be put on shelf')
        if target_status == ProductStatus.OFF_SHELF and product.status != ProductStatus.ON_SHELF:
            raise ConflictError('Only on-shelf products can be taken off shelf')
        if target_status == ProductStatus.ON_SHELF:
            ProductService._ensure_supplier_product_publishable(db, product)
        product.status = target_status
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def batch_update_status_for_admin(db: Session, current_user: User, payload: dict[str, Any]) -> dict[str, Any]:
        product_ids = [int(item) for item in payload.get('product_ids', []) if item]
        operation = str(payload.get('operation') or '').strip().upper()
        if not product_ids:
            raise ConflictError('product_ids required')
        if operation not in {'SUBMIT_REVIEW', 'ON_SHELF', 'OFF_SHELF'}:
            raise ConflictError('operation must be SUBMIT_REVIEW, ON_SHELF or OFF_SHELF')

        updated_ids: list[int] = []
        for product_id in product_ids:
            if operation == 'SUBMIT_REVIEW':
                product = ProductService.submit_review_for_admin(db, product_id, current_user)
            elif operation == 'ON_SHELF':
                product = ProductService.update_status_for_admin(db, product_id, current_user, ProductStatus.ON_SHELF)
            else:
                product = ProductService.update_status_for_admin(db, product_id, current_user, ProductStatus.OFF_SHELF)
            updated_ids.append(product.id)

        return {'updated_count': len(updated_ids), 'product_ids': updated_ids, 'operation': operation}

    @staticmethod
    def delete_for_admin(db: Session, product_id: int, current_user: User) -> None:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        if product.status == ProductStatus.ON_SHELF:
            raise ConflictError('On-shelf product cannot be deleted')
        if ProductService._product_order_count(db, product.id) > 0:
            raise ConflictError('Product with orders cannot be deleted')

        db.query(ProductZoneConfig).filter(ProductZoneConfig.product_id == product.id).delete()
        db.delete(product)
        db.commit()

    @staticmethod
    def list_for_admin(
        db: Session,
        current_user: User,
        keyword: str | None = None,
        zone_type: ZoneType | None = None,
        status: ProductStatus | None = None,
        owner_type: ProductOwnerType | None = None,
    ) -> list[dict]:
        query = ProductService._admin_product_query(db, current_user)
        if keyword:
            term = keyword.strip()
            query = query.filter(or_(Product.product_name.like(f'%{term}%'), Product.brand.like(f'%{term}%')))
        if zone_type is not None:
            query = query.filter(Product.zone_type == zone_type)
        if status is not None:
            query = query.filter(Product.status == status)
        if owner_type is not None:
            query = query.filter(Product.owner_type == owner_type)
        rows = query.order_by(Product.order_by.is_(None), Product.order_by.desc(), Product.id.desc()).all()
        return [ProductService._serialize_product_for_admin(db, item) for item in rows]

    @staticmethod
    def list_by_zone_for_admin(db: Session, zone_type: str, current_user: User):
        return ProductService.list_for_admin(db, current_user, zone_type=ZoneType(zone_type))

    @staticmethod
    def _ensure_product_visible_for_admin(db: Session, product_id: int, current_user: User) -> Product:
        product = ProductService._admin_product_query(db, current_user).filter(Product.id == product_id).first()
        if not product:
            raise NotFoundError('Product not found')
        return product

    @staticmethod
    def build_import_template_csv() -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(ProductService.IMPORT_TEMPLATE_HEADERS)
        writer.writerow([
            '',
            '示例商品-复购区',
            '1',
            'REPURCHASE',
            'PHYSICAL',
            'SELF_OPERATED',
            '',
            '199.00',
            '299.00',
            '120.00',
            '50',
            'https://cdn.example.com/products/sample-main.jpg',
            'https://cdn.example.com/products/sample-cover.jpg',
            'https://cdn.example.com/products/sample-1.jpg,https://cdn.example.com/products/sample-2.jpg',
            '示例品牌',
            '移动端卡片简介示例',
            '这里填写商品详情说明',
            '这里填写商品卖点',
            '100',
            '1',
            '1',
            '0',
            '1',
            '2001',
            '65',
            '',
            '',
            '',
            '',
            '1',
            '0',
            '0',
            '1',
            '1',
            '0',
            '',
            '',
            '0',
        ])
        writer.writerow([
            '10001',
            '示例商品-更新已有商品',
            '1',
            'SELF_OPERATED',
            'PHYSICAL',
            'SUPPLIER',
            '1',
            '299.00',
            '399.00',
            '180.00',
            '120',
            '',
            '',
            '',
            '更新品牌',
            '更新后的简介',
            '更新后的详情',
            '更新后的卖点',
            '80',
            '0',
            '1',
            '1',
            '0',
            '',
            '',
            '55',
            '70',
            '20',
            '20',
            '0',
            '0',
            '0',
            '1',
            '1',
            '0',
            '',
            '',
            '0',
        ])
        return f'\ufeff{buffer.getvalue()}'.encode()

    @staticmethod
    def _extract_import_value(row: dict[str, Any], field_name: str) -> str:
        for alias in ProductService.IMPORT_FIELD_ALIASES.get(field_name, []):
            value = row.get(alias)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ''

    @staticmethod
    def _parse_import_enum(label: str, mapping: dict[str, Any], field_name: str):
        value = label.strip()
        if not value:
            return None
        key = value.upper()
        if key in mapping:
            return mapping[key]
        if value in mapping:
            return mapping[value]
        raise ConflictError(f'Invalid {field_name}: {value}')

    @staticmethod
    def _parse_import_int(label: str, field_name: str, default: int | None = None) -> int | None:
        if not label:
            return default
        try:
            return int(float(label))
        except ValueError as exc:
            raise ConflictError(f'Invalid {field_name}: {label}') from exc

    @staticmethod
    def _parse_import_float(label: str, field_name: str, default: float | None = None) -> float | None:
        if not label:
            return default
        try:
            return float(label)
        except ValueError as exc:
            raise ConflictError(f'Invalid {field_name}: {label}') from exc

    @staticmethod
    def _parse_import_bool(label: str, default: bool = False) -> bool:
        if not label:
            return default
        normalized = label.strip().lower()
        if normalized in {'1', 'true', 'yes', 'y', 'on', '是'}:
            return True
        if normalized in {'0', 'false', 'no', 'n', 'off', '否'}:
            return False
        raise ConflictError(f'Invalid boolean value: {label}')

    @staticmethod
    def _parse_import_optional_bool(label: str) -> bool | None:
        if not label:
            return None
        return ProductService._parse_import_bool(label, default=False)

    @staticmethod
    def _zone_config_payload_from_import_row(zone_type: ZoneType, row: dict[str, Any]) -> dict[str, Any] | None:
        payload = {
            'package_required': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'package_required')),
            'package_id': ProductService._parse_import_int(ProductService._extract_import_value(row, 'package_id'), 'package_id'),
            'repurchase_discount_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'repurchase_discount_rate'), 'repurchase_discount_rate'),
            'voucher_deduct_min_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'voucher_deduct_min_rate'), 'voucher_deduct_min_rate'),
            'voucher_deduct_max_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'voucher_deduct_max_rate'), 'voucher_deduct_max_rate'),
            'ai_coupon_reward_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'ai_coupon_reward_rate'), 'ai_coupon_reward_rate'),
            'ai_coupon_max_deduct_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'ai_coupon_max_deduct_rate'), 'ai_coupon_max_deduct_rate'),
            'points_purchase_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'points_purchase_enabled')),
            'balance_purchase_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'balance_purchase_enabled')),
            'alipay_purchase_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'alipay_purchase_enabled')),
            'wechat_purchase_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'wechat_purchase_enabled')),
            'points_only_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'points_only_enabled')),
            'points_cash_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'points_cash_enabled')),
            'cash_only_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'cash_only_enabled')),
            'balance_only_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'balance_only_enabled')),
            'balance_points_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'balance_points_enabled')),
            'flash_sale_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'flash_sale_enabled')),
            'per_user_limit': ProductService._parse_import_int(ProductService._extract_import_value(row, 'per_user_limit'), 'per_user_limit'),
            'merchant_commission_rule_id': ProductService._parse_import_int(ProductService._extract_import_value(row, 'merchant_commission_rule_id'), 'merchant_commission_rule_id'),
            'device_revenue_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'device_revenue_enabled')),
            'custom_commission_enabled': ProductService._parse_import_optional_bool(ProductService._extract_import_value(row, 'custom_commission_enabled')),
            'custom_commission_method': ProductService._extract_import_value(row, 'custom_commission_method') or None,
            'custom_commission_level1_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'custom_commission_level1_rate'), 'custom_commission_level1_rate'),
            'custom_commission_level2_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'custom_commission_level2_rate'), 'custom_commission_level2_rate'),
            'custom_commission_level3_rate': ProductService._parse_import_float(ProductService._extract_import_value(row, 'custom_commission_level3_rate'), 'custom_commission_level3_rate'),
            'custom_commission_level1_amount': ProductService._parse_import_float(ProductService._extract_import_value(row, 'custom_commission_level1_amount'), 'custom_commission_level1_amount'),
            'custom_commission_level2_amount': ProductService._parse_import_float(ProductService._extract_import_value(row, 'custom_commission_level2_amount'), 'custom_commission_level2_amount'),
            'custom_commission_level3_amount': ProductService._parse_import_float(ProductService._extract_import_value(row, 'custom_commission_level3_amount'), 'custom_commission_level3_amount'),
        }
        if not any(value is not None for value in payload.values()):
            return None

        defaults = ProductService.zone_config_defaults(zone_type)
        merged: dict[str, Any] = {}
        for key, default_value in defaults.items():
            merged[key] = payload[key] if payload.get(key) is not None else default_value
        return merged

    @staticmethod
    def _payload_from_import_row(row: dict[str, Any]) -> tuple[int | None, dict, dict[str, Any] | None]:
        product_id = ProductService._parse_import_int(ProductService._extract_import_value(row, 'id'), 'id')
        zone_type = ProductService._parse_import_enum(
            ProductService._extract_import_value(row, 'zone_type'),
            ProductService.IMPORT_ZONE_MAPPING,
            'zone_type',
        )
        if zone_type is None:
            if product_id:
                raise ConflictError('zone_type is required when updating a product')
            zone_type = ZoneType.SELF_OPERATED

        product_type = ProductService._parse_import_enum(
            ProductService._extract_import_value(row, 'product_type'),
            ProductService.IMPORT_PRODUCT_TYPE_MAPPING,
            'product_type',
        )
        if product_type is None:
            product_type = ProductType.SERVICE if zone_type == ZoneType.LOCAL_LIFE else ProductType.PHYSICAL

        owner_type = ProductService._parse_import_enum(
            ProductService._extract_import_value(row, 'owner_type'),
            ProductService.IMPORT_OWNER_TYPE_MAPPING,
            'owner_type',
        ) or ProductOwnerType.SELF_OPERATED

        payload = {
            'product_name': ProductService._extract_import_value(row, 'product_name'),
            'category_id': ProductService._parse_import_int(
                ProductService._extract_import_value(row, 'category_id'),
                'category_id',
            ),
            'zone_type': zone_type,
            'product_type': product_type,
            'owner_type': owner_type,
            'owner_id': ProductService._parse_import_int(ProductService._extract_import_value(row, 'owner_id'), 'owner_id'),
            'sale_price': ProductService._parse_import_float(ProductService._extract_import_value(row, 'sale_price'), 'sale_price'),
            'market_price': ProductService._parse_import_float(ProductService._extract_import_value(row, 'market_price'), 'market_price'),
            'cost_price': ProductService._parse_import_float(ProductService._extract_import_value(row, 'cost_price'), 'cost_price'),
            'stock': ProductService._parse_import_int(ProductService._extract_import_value(row, 'stock'), 'stock', default=0) or 0,
            'main_image': ProductService._extract_import_value(row, 'main_image') or None,
            'cover': ProductService._extract_import_value(row, 'cover') or None,
            'icons': ProductService._extract_import_value(row, 'icons') or None,
            'brand': ProductService._extract_import_value(row, 'brand') or None,
            'profile': ProductService._extract_import_value(row, 'profile') or None,
            'detail': ProductService._extract_import_value(row, 'detail') or None,
            'feature': ProductService._extract_import_value(row, 'feature') or None,
            'order_by': ProductService._parse_import_int(ProductService._extract_import_value(row, 'order_by'), 'order_by'),
            'is_hot': ProductService._parse_import_bool(ProductService._extract_import_value(row, 'is_hot'), default=False),
            'requires_shipping': ProductService._parse_import_bool(
                ProductService._extract_import_value(row, 'requires_shipping'),
                default=zone_type != ZoneType.LOCAL_LIFE,
            ),
            'drop_shipping_enabled': ProductService._parse_import_bool(
                ProductService._extract_import_value(row, 'drop_shipping_enabled'),
                default=False,
            ),
        }
        if payload['sale_price'] is None:
            raise ConflictError('sale_price is required')
        return product_id, payload, ProductService._zone_config_payload_from_import_row(zone_type, row)

    @staticmethod
    def import_products_for_admin(db: Session, current_user: User, filename: str, data: bytes) -> dict[str, Any]:
        rows = load_tabular_rows(filename, data)
        if not rows:
            raise ConflictError('Import file has no product rows')

        created_count = 0
        updated_count = 0
        failed_rows: list[dict[str, Any]] = []

        for index, row in enumerate(rows, start=2):
            try:
                product_id, payload, zone_config_payload = ProductService._payload_from_import_row(row)
                if product_id:
                    product = ProductService.update_for_admin(db, product_id, current_user, payload)
                    updated_count += 1
                else:
                    product = ProductService.create_for_admin(db, current_user, payload)
                    created_count += 1
                if zone_config_payload:
                    ProductService.update_zone_config_for_admin(db, product.id, current_user, zone_config_payload)
            except Exception as exc:
                db.rollback()
                failed_rows.append({
                    'row_number': index,
                    'product_name': ProductService._extract_import_value(row, 'product_name') or '--',
                    'reason': str(exc),
                    'raw_row': {key: str(value or '') for key, value in row.items()},
                })

        return {
            'total_rows': len(rows),
            'created_count': created_count,
            'updated_count': updated_count,
            'failed_count': len(failed_rows),
            'failed_rows': failed_rows,
        }

    @staticmethod
    def get_zone_config_for_admin(db: Session, product_id: int, current_user: User) -> dict:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        return ProductService._zone_config_snapshot(db, product)

    @staticmethod
    def _validate_zone_config_payload(product: Product, payload: dict) -> None:
        rate_fields = [
            'repurchase_discount_rate',
            'voucher_deduct_min_rate',
            'voucher_deduct_max_rate',
            'ai_coupon_reward_rate',
            'ai_coupon_max_deduct_rate',
        ]
        for field in rate_fields:
            value = payload.get(field)
            if value is not None and (value < 0 or value > 100):
                raise ConflictError(f'{field} must be between 0 and 100')

        min_rate = payload.get('voucher_deduct_min_rate')
        max_rate = payload.get('voucher_deduct_max_rate')
        if min_rate is not None and max_rate is not None and min_rate > max_rate:
            raise ConflictError('voucher_deduct_min_rate cannot exceed voucher_deduct_max_rate')

        per_user_limit = payload.get('per_user_limit')
        if per_user_limit is not None and per_user_limit <= 0:
            raise ConflictError('per_user_limit must be greater than 0')

        commission_method = str(payload.get('custom_commission_method') or 'RATE').strip().upper()
        if commission_method not in {'RATE', 'FIXED_AMOUNT'}:
            raise ConflictError('custom_commission_method must be RATE or FIXED_AMOUNT')
        payload['custom_commission_method'] = commission_method

        commission_rates = [payload.get(f'custom_commission_level{level}_rate', 0) for level in range(1, 4)]
        commission_amounts = [payload.get(f'custom_commission_level{level}_amount', 0) for level in range(1, 4)]
        if any(value < 0 or value > 100 for value in commission_rates):
            raise ConflictError('Custom commission rates must be between 0 and 100')
        if any(value < 0 for value in commission_amounts):
            raise ConflictError('Custom commission amounts cannot be negative')
        if payload.get('custom_commission_enabled'):
            selected_values = commission_rates if commission_method == 'RATE' else commission_amounts
            if sum(selected_values) <= 0:
                raise ConflictError('At least one custom commission value must be greater than 0')
            if commission_method == 'RATE' and sum(commission_rates) > 100:
                raise ConflictError('Custom commission total rate cannot exceed 100')

        if product.zone_type == ZoneType.REPURCHASE and payload.get('flash_sale_enabled'):
            raise ConflictError('Repurchase zone does not support flash sale')
        if product.zone_type == ZoneType.HOT_SALE and payload.get('package_required'):
            raise ConflictError('Hot-sale zone does not support package qualification')
        if not any((
            payload.get('points_only_enabled'),
            payload.get('points_cash_enabled'),
            payload.get('cash_only_enabled'),
        )):
            raise ConflictError('At least one purchase mode must be enabled')
        if payload.get('points_purchase_enabled') and not any((
            payload.get('points_only_enabled'),
            payload.get('points_cash_enabled'),
        )):
            raise ConflictError('Points payment must enable at least one points purchase mode')
        if payload.get('balance_purchase_enabled') and not any((
            payload.get('balance_only_enabled'),
            payload.get('balance_points_enabled'),
        )):
            raise ConflictError('Balance payment must enable at least one balance purchase mode')

    @staticmethod
    def update_zone_config_for_admin(db: Session, product_id: int, current_user: User, payload: dict) -> ProductZoneConfig:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        ProductService._validate_zone_config_payload(product, payload)
        config = db.query(ProductZoneConfig).filter(ProductZoneConfig.product_id == product.id).first()
        if not config:
            config = ProductZoneConfig(product_id=product.id, zone_type=product.zone_type)
            db.add(config)
            db.flush()

        for field, value in payload.items():
            if hasattr(config, field):
                setattr(config, field, value)

        config.zone_type = product.zone_type
        db.commit()
        db.refresh(config)
        return config
