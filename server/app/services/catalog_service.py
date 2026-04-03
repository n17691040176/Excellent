from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
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
from app.models.product import Product, ProductQualification, ProductZoneConfig
from app.models.supplier import Supplier, SupplierAgreement
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService
from app.utils.helpers import generate_order_no, now, quantize_amount


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
            order_status=OrderStatus.CREATED,
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
        order.paid_amount = order.payable_amount
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def handle_paid_package_order(db: Session, order: Order) -> None:
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
                'balance_purchase_enabled': False,
                'flash_sale_enabled': False,
                'per_user_limit': None,
                'merchant_commission_rule_id': None,
                'device_revenue_enabled': False,
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
                'balance_purchase_enabled': False,
                'flash_sale_enabled': False,
                'per_user_limit': None,
                'merchant_commission_rule_id': None,
                'device_revenue_enabled': False,
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
                'flash_sale_enabled': True,
                'per_user_limit': 1,
                'merchant_commission_rule_id': None,
                'device_revenue_enabled': False,
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
            'flash_sale_enabled': False,
            'per_user_limit': None,
            'merchant_commission_rule_id': None,
            'device_revenue_enabled': True,
        }

    @staticmethod
    def list_by_zone(db: Session, zone_type: str):
        return db.query(Product).filter(
            Product.zone_type == zone_type,
            Product.status == ProductStatus.ON_SHELF,
        ).order_by(Product.id.desc()).all()

    @staticmethod
    def get_product(db: Session, product_id: int):
        return db.get(Product, product_id)

    @staticmethod
    def _validate_product_payload(payload: dict) -> None:
        if not payload.get('product_name'):
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

    @staticmethod
    def _resolve_owner(db: Session, current_user: User, owner_type: ProductOwnerType, owner_id: int | None) -> tuple[ProductOwnerType, int]:
        if owner_type == ProductOwnerType.SELF_OPERATED:
            resolved_owner_id = owner_id or current_user.id
            owner_user = db.get(User, resolved_owner_id)
            if not owner_user:
                raise NotFoundError('Owner user not found')
            if not AdminScopeService.is_super_admin(current_user):
                AdminScopeService.ensure_user_visible(current_user, owner_user)
            return owner_type, resolved_owner_id

        if owner_type == ProductOwnerType.SUPPLIER:
            if not owner_id:
                raise ConflictError('Supplier owner_id required')
            supplier = db.get(Supplier, owner_id)
            if not supplier:
                raise NotFoundError('Supplier not found')
            supplier_user = db.get(User, supplier.user_id)
            if supplier_user and not AdminScopeService.is_super_admin(current_user):
                AdminScopeService.ensure_user_visible(current_user, supplier_user)
            return owner_type, supplier.id

        if not owner_id:
            raise ConflictError('Local merchant owner_id required')
        merchant = db.get(LocalLifeMerchant, owner_id)
        if not merchant:
            raise NotFoundError('Local merchant not found')
        merchant_owner = db.get(User, merchant.owner_user_id)
        if merchant_owner and not AdminScopeService.is_super_admin(current_user):
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
    def _serialize_product_for_admin(db: Session, product: Product) -> dict:
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

        return {
            'id': product.id,
            'product_name': product.product_name,
            'product_type': product.product_type.value,
            'owner_type': product.owner_type.value,
            'owner_id': product.owner_id,
            'owner_name': owner_name,
            'zone_type': product.zone_type.value,
            'market_price': float(product.market_price) if product.market_price is not None else None,
            'sale_price': float(product.sale_price),
            'cost_price': float(product.cost_price) if product.cost_price is not None else None,
            'stock': product.stock,
            'sold_count': product.sold_count,
            'main_image': product.main_image,
            'status': product.status.value,
            'requires_shipping': bool(product.requires_shipping),
            'drop_shipping_enabled': bool(product.drop_shipping_enabled),
            'publish_guard': ProductService._build_supplier_publish_guard(db, product),
        }

    @staticmethod
    def create_for_admin(db: Session, current_user: User, payload: dict) -> Product:
        ProductService._validate_product_payload(payload)
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
            market_price=payload.get('market_price'),
            sale_price=payload['sale_price'],
            cost_price=payload.get('cost_price'),
            stock=payload['stock'],
            sold_count=0,
            main_image=payload.get('main_image'),
            status=ProductStatus.DRAFT,
            requires_shipping=requires_shipping,
            drop_shipping_enabled=payload.get('drop_shipping_enabled', False),
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update_for_admin(db: Session, product_id: int, current_user: User, payload: dict) -> Product:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        ProductService._validate_product_payload(payload)

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
        product.market_price = payload.get('market_price')
        product.sale_price = payload['sale_price']
        product.cost_price = payload.get('cost_price')
        product.stock = payload['stock']
        product.main_image = payload.get('main_image')
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
    def list_by_zone_for_admin(db: Session, zone_type: str, current_user: User):
        query = db.query(Product).filter(Product.zone_type == zone_type)
        if not AdminScopeService.is_super_admin(current_user):
            team_user_ids = AdminScopeService.team_user_ids_subquery(current_user)
            supplier_ids = select(Supplier.id).where(Supplier.user_id.in_(team_user_ids))
            merchant_ids = select(LocalLifeMerchant.id).where(LocalLifeMerchant.owner_user_id.in_(team_user_ids))
            query = query.filter(
                or_(
                    (Product.owner_type == ProductOwnerType.SELF_OPERATED) & (Product.owner_id.in_(team_user_ids)),
                    (Product.owner_type == ProductOwnerType.SUPPLIER) & (Product.owner_id.in_(supplier_ids)),
                    (Product.owner_type == ProductOwnerType.LOCAL_MERCHANT) & (Product.owner_id.in_(merchant_ids)),
                )
            )
        rows = query.order_by(Product.id.desc()).all()
        return [ProductService._serialize_product_for_admin(db, item) for item in rows]

    @staticmethod
    def _ensure_product_visible_for_admin(db: Session, product_id: int, current_user: User) -> Product:
        product = ProductService.get_product(db, product_id)
        if not product:
            raise NotFoundError('Product not found')
        if AdminScopeService.is_super_admin(current_user):
            return product
        visible_ids = {item.id for item in ProductService.list_by_zone_for_admin(db, product.zone_type, current_user)}
        if product.id not in visible_ids:
            raise ConflictError('Product out of team scope')
        return product

    @staticmethod
    def get_zone_config_for_admin(db: Session, product_id: int, current_user: User) -> dict:
        product = ProductService._ensure_product_visible_for_admin(db, product_id, current_user)
        config = db.query(ProductZoneConfig).filter(ProductZoneConfig.product_id == product.id).first()
        defaults = ProductService.zone_config_defaults(product.zone_type)
        data = {'product_id': product.id, 'zone_type': product.zone_type.value}
        for key, value in defaults.items():
            data[key] = getattr(config, key) if config and getattr(config, key) is not None else value
        return data

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

        if product.zone_type == ZoneType.REPURCHASE and payload.get('flash_sale_enabled'):
            raise ConflictError('Repurchase zone does not support flash sale')
        if product.zone_type == ZoneType.HOT_SALE and payload.get('package_required'):
            raise ConflictError('Hot-sale zone does not support package qualification')

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
