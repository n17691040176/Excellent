from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import AssetType, OrderStatus, OrderType, PayStatus, ProductStatus, ZoneType
from app.models.order import Order, OrderAssetDeduction, OrderItem
from app.models.product import Product, ProductZoneConfig
from app.models.user import User
from app.services.asset_service import AssetService
from app.services.commission_service import CommissionService
from app.utils.helpers import generate_order_no, now, quantize_amount


class OrderService:
    @staticmethod
    def _zone_config_defaults(zone_type: ZoneType) -> dict:
        if zone_type == ZoneType.REPURCHASE:
            return {
                'package_required': True,
                'voucher_deduct_min_rate': None,
                'voucher_deduct_max_rate': None,
                'ai_coupon_max_deduct_rate': None,
                'ai_coupon_reward_rate': None,
                'points_purchase_enabled': True,
                'balance_purchase_enabled': False,
                'flash_sale_enabled': False,
                'per_user_limit': None,
            }
        if zone_type == ZoneType.SELF_OPERATED:
            return {
                'package_required': False,
                'voucher_deduct_min_rate': Decimal('50'),
                'voucher_deduct_max_rate': Decimal('70'),
                'ai_coupon_max_deduct_rate': Decimal('20'),
                'ai_coupon_reward_rate': Decimal('20'),
                'points_purchase_enabled': False,
                'balance_purchase_enabled': False,
                'flash_sale_enabled': False,
                'per_user_limit': None,
            }
        if zone_type == ZoneType.HOT_SALE:
            return {
                'package_required': False,
                'voucher_deduct_min_rate': None,
                'voucher_deduct_max_rate': None,
                'ai_coupon_max_deduct_rate': None,
                'ai_coupon_reward_rate': None,
                'points_purchase_enabled': True,
                'balance_purchase_enabled': True,
                'flash_sale_enabled': True,
                'per_user_limit': 1,
            }
        return {
            'package_required': False,
            'voucher_deduct_min_rate': None,
            'voucher_deduct_max_rate': None,
            'ai_coupon_max_deduct_rate': None,
            'ai_coupon_reward_rate': None,
            'points_purchase_enabled': True,
            'balance_purchase_enabled': True,
            'flash_sale_enabled': False,
            'per_user_limit': None,
        }

    @staticmethod
    def _get_zone_config(db: Session, product_id: int, zone_type: ZoneType) -> ProductZoneConfig | None:
        return db.query(ProductZoneConfig).filter(
            ProductZoneConfig.product_id == product_id,
            ProductZoneConfig.zone_type == zone_type,
        ).first()

    @staticmethod
    def _resolve_config_value(configs: list[ProductZoneConfig | None], zone_type: ZoneType, field: str):
        defaults = OrderService._zone_config_defaults(zone_type)
        values = [getattr(config, field) for config in configs if config and getattr(config, field) is not None]
        if not values:
            return defaults.get(field)
        if field in {'voucher_deduct_max_rate', 'ai_coupon_max_deduct_rate', 'per_user_limit'}:
            return min(values)
        if field in {'voucher_deduct_min_rate', 'ai_coupon_reward_rate'}:
            return max(values)
        return any(bool(value) for value in values)

    @staticmethod
    def _validate_order_type(zone_type: ZoneType, order_type: OrderType) -> None:
        expected = {
            ZoneType.REPURCHASE: OrderType.REPURCHASE_ORDER,
            ZoneType.SELF_OPERATED: OrderType.SELF_OPERATED_ORDER,
            ZoneType.HOT_SALE: OrderType.HOT_SALE_ORDER,
        }.get(zone_type)
        if expected and order_type != expected:
            raise ConflictError(f'Order type must match zone {zone_type.value}')

    @staticmethod
    def _require_package_qualification(db: Session, current_user: User, configs: list[ProductZoneConfig | None]) -> None:
        package_ids = [config.package_id for config in configs if config and config.package_required and config.package_id]
        query = db.query(func.count(Order.id)).filter(
            Order.user_id == current_user.id,
            Order.order_type == OrderType.PACKAGE_ORDER,
            Order.pay_status == PayStatus.PAID,
        )
        if package_ids:
            query = query.filter(Order.source_ref_id.in_(package_ids))
        if (query.scalar() or 0) <= 0:
            raise ConflictError('Repurchase zone requires package qualification')

    @staticmethod
    def _validate_hot_sale_limit(
        db: Session,
        current_user: User,
        product_id: int,
        quantity: int,
        per_user_limit: int | None,
    ) -> None:
        if not per_user_limit:
            return
        purchased = db.query(func.coalesce(func.sum(OrderItem.quantity), 0)).join(
            Order,
            OrderItem.order_id == Order.id,
        ).filter(
            Order.user_id == current_user.id,
            OrderItem.product_id == product_id,
            Order.order_status != OrderStatus.CLOSED,
        ).scalar() or 0
        if int(purchased) + quantity > per_user_limit:
            raise ConflictError('Hot sale product purchase limit exceeded')

    @staticmethod
    def _validate_asset_rules(
        zone_type: ZoneType,
        total_amount: Decimal,
        configs: list[ProductZoneConfig | None],
        deductions_by_type: dict[AssetType, Decimal],
    ) -> None:
        if zone_type == ZoneType.REPURCHASE:
            invalid_assets = set(deductions_by_type) - {AssetType.POINTS}
            if invalid_assets:
                raise ConflictError('Repurchase zone only supports points deduction')
            return

        if zone_type == ZoneType.SELF_OPERATED:
            invalid_assets = set(deductions_by_type) - {AssetType.VOUCHER, AssetType.AI_COUPON}
            if invalid_assets:
                raise ConflictError('Self-operated zone only supports voucher and AI coupon deductions')

            voucher_amount = deductions_by_type.get(AssetType.VOUCHER, Decimal('0'))
            ai_amount = deductions_by_type.get(AssetType.AI_COUPON, Decimal('0'))

            if voucher_amount > 0:
                min_rate = Decimal(str(OrderService._resolve_config_value(configs, zone_type, 'voucher_deduct_min_rate') or 0))
                max_rate = Decimal(str(OrderService._resolve_config_value(configs, zone_type, 'voucher_deduct_max_rate') or 0))
                min_amount = quantize_amount(total_amount * min_rate / Decimal('100'))
                max_amount = quantize_amount(total_amount * max_rate / Decimal('100'))
                if voucher_amount < min_amount or voucher_amount > max_amount:
                    raise ConflictError('Voucher deduction must stay within configured self-operated ratio')

            if ai_amount > 0:
                ai_rate = Decimal(str(OrderService._resolve_config_value(configs, zone_type, 'ai_coupon_max_deduct_rate') or 0))
                ai_max_amount = quantize_amount(total_amount * ai_rate / Decimal('100'))
                if ai_amount > ai_max_amount:
                    raise ConflictError('AI coupon deduction exceeds configured self-operated limit')
            return

        if zone_type == ZoneType.HOT_SALE:
            invalid_assets = set(deductions_by_type) - {AssetType.POINTS, AssetType.BALANCE}
            if invalid_assets:
                raise ConflictError('Hot sale zone only supports points or balance deductions')
            if not deductions_by_type:
                raise ConflictError('Hot sale zone requires points or balance for rush purchase')

            points_enabled = bool(OrderService._resolve_config_value(configs, zone_type, 'points_purchase_enabled'))
            balance_enabled = bool(OrderService._resolve_config_value(configs, zone_type, 'balance_purchase_enabled'))
            if deductions_by_type.get(AssetType.POINTS, Decimal('0')) > 0 and not points_enabled:
                raise ConflictError('Hot sale zone points payment is disabled')
            if deductions_by_type.get(AssetType.BALANCE, Decimal('0')) > 0 and not balance_enabled:
                raise ConflictError('Hot sale zone balance payment is disabled')
            return

    @staticmethod
    def _reward_self_operated_ai_coupon(db: Session, order: Order) -> None:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        if not items:
            return

        total_reward = Decimal('0')
        for item in items:
            config = OrderService._get_zone_config(db, item.product_id, ZoneType.SELF_OPERATED)
            rate = config.ai_coupon_reward_rate if config and config.ai_coupon_reward_rate is not None else Decimal('20')
            reward_amount = quantize_amount(Decimal(str(item.total_amount)) * Decimal(str(rate)) / Decimal('100'))
            total_reward += reward_amount

        total_reward = quantize_amount(total_reward)
        if total_reward > 0:
            AssetService.add_amount(
                db,
                order.user_id,
                AssetType.AI_COUPON,
                total_reward,
                'SELF_OPERATED_REWARD',
                source_id=order.id,
                source_no=order.order_no,
            )

    @staticmethod
    def create_order(db: Session, current_user: User, payload: dict) -> Order:
        items_payload = payload['items']
        if not items_payload:
            raise ConflictError('Order items required')

        order_type = payload['order_type']
        payload_zone_type = payload.get('zone_type')

        products_data: list[dict] = []
        zone_types: set[ZoneType] = set()
        total_amount = Decimal('0.00')

        for item in items_payload:
            product = db.get(Product, item['product_id'])
            if not product:
                raise NotFoundError('Product not found')
            if product.status != ProductStatus.ON_SHELF:
                raise ConflictError('Product unavailable')

            quantity = int(item.get('quantity', 1))
            if quantity <= 0:
                raise ConflictError('Quantity must be positive')
            if product.stock < quantity:
                raise ConflictError('Stock insufficient')

            zone_types.add(product.zone_type)
            config = OrderService._get_zone_config(db, product.id, product.zone_type)
            line_total = quantize_amount(Decimal(str(product.sale_price)) * Decimal(str(quantity)))
            total_amount += line_total
            products_data.append(
                {
                    'product': product,
                    'quantity': quantity,
                    'config': config,
                    'line_total': line_total,
                    'sku_id': item.get('sku_id'),
                }
            )

        if len(zone_types) != 1:
            raise ConflictError('Mixed zone products are not allowed in one order')
        actual_zone_type = zone_types.pop()
        if payload_zone_type and payload_zone_type != actual_zone_type:
            raise ConflictError('Zone type does not match products')

        OrderService._validate_order_type(actual_zone_type, order_type)

        configs = [item['config'] for item in products_data]
        if actual_zone_type == ZoneType.REPURCHASE:
            package_required = any(
                config.package_required for config in configs if config is not None
            ) or bool(OrderService._zone_config_defaults(actual_zone_type)['package_required'])
            if package_required:
                OrderService._require_package_qualification(db, current_user, configs)

        if actual_zone_type == ZoneType.HOT_SALE:
            flash_sale_enabled = OrderService._resolve_config_value(configs, actual_zone_type, 'flash_sale_enabled')
            if not flash_sale_enabled:
                raise ConflictError('Hot sale product flash sale is disabled')
            for item in products_data:
                per_user_limit = OrderService._resolve_config_value([item['config']], actual_zone_type, 'per_user_limit')
                OrderService._validate_hot_sale_limit(
                    db,
                    current_user,
                    item['product'].id,
                    item['quantity'],
                    per_user_limit,
                )

        deductions_by_type: dict[AssetType, Decimal] = {}
        for deduction in payload.get('asset_deductions', []):
            asset_type = AssetType(deduction['asset_type'])
            amount = quantize_amount(deduction['amount'])
            if amount <= 0:
                continue
            deductions_by_type[asset_type] = deductions_by_type.get(asset_type, Decimal('0')) + amount

        OrderService._validate_asset_rules(actual_zone_type, total_amount, configs, deductions_by_type)

        order = Order(
            order_no=generate_order_no('OD'),
            user_id=current_user.id,
            team_id=current_user.team_id,
            order_type=order_type,
            zone_type=actual_zone_type,
            total_amount=0,
            discount_amount=0,
            payable_amount=0,
            paid_amount=0,
            pay_status=PayStatus.UNPAID,
            order_status=OrderStatus.CREATED,
        )
        db.add(order)
        db.flush()

        for item in products_data:
            product = item['product']
            product.stock -= item['quantity']
            product.sold_count += item['quantity']
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    sku_id=item['sku_id'],
                    product_name=product.product_name,
                    sku_name=None,
                    unit_price=product.sale_price,
                    quantity=item['quantity'],
                    total_amount=item['line_total'],
                    created_at=now(),
                )
            )

        discount_amount = Decimal('0.00')
        for asset_type, amount in deductions_by_type.items():
            AssetService.consume_amount(
                db,
                current_user.id,
                asset_type,
                amount,
                'ORDER_DEDUCT',
                source_id=order.id,
                source_no=order.order_no,
            )
            discount_amount += amount
            db.add(
                OrderAssetDeduction(
                    order_id=order.id,
                    asset_type=asset_type.value,
                    deduct_amount=amount,
                    created_at=now(),
                )
            )

        payable_amount = max(total_amount - discount_amount, Decimal('0.00'))
        order.total_amount = total_amount
        order.discount_amount = discount_amount
        order.payable_amount = payable_amount
        order.paid_amount = payable_amount
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def list_orders(db: Session, user_id: int) -> list[Order]:
        return db.query(Order).filter(Order.user_id == user_id).order_by(Order.id.desc()).all()

    @staticmethod
    def get_order(db: Session, user_id: int, order_id: int) -> Order:
        order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
        if not order:
            raise NotFoundError('Order not found')
        return order

    @staticmethod
    def get_order_detail(db: Session, user_id: int, order_id: int) -> dict:
        order = OrderService.get_order(db, user_id, order_id)
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).order_by(OrderItem.id.asc()).all()
        deductions = db.query(OrderAssetDeduction).filter(
            OrderAssetDeduction.order_id == order.id
        ).order_by(OrderAssetDeduction.id.asc()).all()
        return {
            'order': order,
            'items': items,
            'asset_deductions': deductions,
        }

    @staticmethod
    def _mark_paid(db: Session, order: Order) -> Order:
        if order.pay_status == PayStatus.PAID:
            return order
        order.pay_status = PayStatus.PAID
        order.order_status = OrderStatus.PAID
        order.paid_at = now()

        buyer = db.get(User, order.user_id)
        if buyer:
            CommissionService.freeze_for_order(db, order, buyer)

        if order.order_type == OrderType.PACKAGE_ORDER:
            from app.services.catalog_service import PackageService

            PackageService.handle_paid_package_order(db, order)

        if order.zone_type == ZoneType.SELF_OPERATED:
            OrderService._reward_self_operated_ai_coupon(db, order)

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def mark_paid(db: Session, order_id: int) -> Order:
        order = db.get(Order, order_id)
        if not order:
            raise NotFoundError('Order not found')
        return OrderService._mark_paid(db, order)

    @staticmethod
    def pay_order_for_user(db: Session, user_id: int, order_id: int) -> Order:
        order = OrderService.get_order(db, user_id, order_id)
        return OrderService._mark_paid(db, order)

    @staticmethod
    def confirm_order(db: Session, user_id: int, order_id: int) -> Order:
        order = OrderService.get_order(db, user_id, order_id)
        order.order_status = OrderStatus.CONFIRMED
        order.confirmed_at = now()
        db.commit()
        CommissionService.settle_for_order(db, order.id)
        db.refresh(order)
        return order
