from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.address import UserAddress
from app.models.enums import AssetType, OrderStatus, OrderType, PayStatus, ProductStatus, ZoneType
from app.models.order import Order, OrderAssetDeduction, OrderItem
from app.models.product import Product, ProductZoneConfig
from app.models.user import User
from app.services.asset_service import AssetService
from app.services.catalog_service import ProductService
from app.services.commission_service import CommissionService
from app.utils.helpers import generate_order_no, now, quantize_amount


INTERNAL_PAY_CHANNELS = {'BALANCE', 'VOUCHER'}
EXTERNAL_PAY_CHANNELS = {'WECHAT', 'ALIPAY'}
SUPPORTED_PAY_CHANNELS = INTERNAL_PAY_CHANNELS | EXTERNAL_PAY_CHANNELS

ZONE_ORDER_TYPE_MAP = {
    ZoneType.REPURCHASE: OrderType.REPURCHASE_ORDER,
    ZoneType.SELF_OPERATED: OrderType.SELF_OPERATED_ORDER,
    ZoneType.HOT_SALE: OrderType.HOT_SALE_ORDER,
    ZoneType.LOCAL_LIFE: OrderType.LOCAL_LIFE_ORDER,
}

PAY_CHANNEL_ASSET_MAP = {
    'BALANCE': AssetType.BALANCE,
    'VOUCHER': AssetType.VOUCHER,
}


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
                'points_purchase_enabled': True,
                'balance_purchase_enabled': True,
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
        expected = ZONE_ORDER_TYPE_MAP.get(zone_type)
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
    def _resolve_pay_channel(channel: str | None) -> str:
        value = str(channel or 'BALANCE').strip().upper()
        if value not in SUPPORTED_PAY_CHANNELS:
            raise ConflictError('Unsupported pay channel')
        return value

    @staticmethod
    def _normalize_asset_deductions(deductions: list[dict] | None) -> dict[AssetType, Decimal]:
        result: dict[AssetType, Decimal] = {}
        for deduction in deductions or []:
            asset_type = AssetType(str(deduction['asset_type']).upper())
            amount = quantize_amount(deduction['amount'])
            if amount <= 0:
                continue
            result[asset_type] = result.get(asset_type, Decimal('0')) + amount
        return result

    @staticmethod
    def _deductions_payload(deductions_by_type: dict[AssetType, Decimal]) -> list[dict]:
        return [
            {'asset_type': asset_type.value, 'amount': amount}
            for asset_type, amount in deductions_by_type.items()
            if amount > 0
        ]

    @staticmethod
    def _get_default_address(db: Session, user_id: int) -> UserAddress | None:
        return db.query(UserAddress).filter(
            UserAddress.user_id == user_id,
            UserAddress.is_default.is_(True),
        ).first()

    @staticmethod
    def _validate_address(db: Session, user_id: int, address_id: int | None, requires_shipping: bool) -> int | None:
        if not requires_shipping:
            return None
        target_id = address_id
        if target_id is None:
            address = OrderService._get_default_address(db, user_id)
            return address.id if address else None
        address = db.query(UserAddress).filter(
            UserAddress.id == target_id,
            UserAddress.user_id == user_id,
        ).first()
        if not address:
            raise NotFoundError('Address not found')
        return address.id

    @staticmethod
    def _validate_payment_rules(
        zone_type: ZoneType,
        total_amount: Decimal,
        configs: list[ProductZoneConfig | None],
        deductions_by_type: dict[AssetType, Decimal],
        pay_channel: str,
    ) -> None:
        allowed_assets = {AssetType.POINTS}
        if pay_channel == 'BALANCE':
            allowed_assets.add(AssetType.BALANCE)
        if pay_channel == 'VOUCHER':
            allowed_assets.add(AssetType.VOUCHER)

        invalid_assets = set(deductions_by_type) - allowed_assets
        if invalid_assets:
            raise ConflictError('Current payment combination only supports points with selected pay channel')

        if pay_channel in INTERNAL_PAY_CHANNELS and not deductions_by_type.get(PAY_CHANNEL_ASSET_MAP[pay_channel], Decimal('0')):
            raise ConflictError('Internal payment channel must provide deduction amount')

        if zone_type == ZoneType.REPURCHASE and pay_channel != 'BALANCE':
            raise ConflictError('Repurchase zone only supports balance + points')

        if zone_type == ZoneType.SELF_OPERATED and pay_channel not in {'VOUCHER', 'WECHAT', 'ALIPAY'}:
            raise ConflictError('Self-operated zone supports voucher + points or external pay + points')

        if zone_type == ZoneType.HOT_SALE and pay_channel not in {'BALANCE', 'WECHAT', 'ALIPAY'}:
            raise ConflictError('Hot sale zone supports balance + points or external pay + points')

        if zone_type == ZoneType.LOCAL_LIFE and pay_channel not in {'BALANCE', 'WECHAT', 'ALIPAY'}:
            raise ConflictError('Local life zone supports balance + points or external pay + points')

        points_amount = deductions_by_type.get(AssetType.POINTS, Decimal('0'))
        if points_amount > total_amount:
            raise ConflictError('Points deduction exceeds order total')

        if zone_type in {ZoneType.HOT_SALE, ZoneType.REPURCHASE, ZoneType.SELF_OPERATED}:
            points_enabled = bool(OrderService._resolve_config_value(configs, zone_type, 'points_purchase_enabled'))
            if points_amount > 0 and not points_enabled:
                raise ConflictError('Points payment is disabled for current product')

        if pay_channel == 'BALANCE' and zone_type in {ZoneType.HOT_SALE, ZoneType.SELF_OPERATED, ZoneType.LOCAL_LIFE}:
            balance_enabled = True
            if zone_type in {ZoneType.HOT_SALE, ZoneType.SELF_OPERATED}:
                balance_enabled = bool(OrderService._resolve_config_value(configs, zone_type, 'balance_purchase_enabled'))
            if not balance_enabled:
                raise ConflictError('Balance payment is disabled for current product')

        voucher_amount = deductions_by_type.get(AssetType.VOUCHER, Decimal('0'))
        if pay_channel == 'VOUCHER' and voucher_amount <= 0:
            raise ConflictError('Voucher payment amount is required')

        total_deduction = sum(deductions_by_type.values(), Decimal('0.00'))
        if total_deduction > total_amount:
            raise ConflictError('Asset deductions exceed order total')

    @staticmethod
    def build_payment_plan(
        db: Session,
        current_user: User,
        products_data: list[dict],
        deductions_by_type: dict[AssetType, Decimal],
        pay_channel: str,
        address_id: int | None = None,
    ) -> dict:
        zone_type = products_data[0]['product'].zone_type
        configs = [item['config'] for item in products_data]
        total_amount = quantize_amount(sum((item['line_total'] for item in products_data), Decimal('0.00')))
        requires_shipping = any(bool(item['product'].requires_shipping) for item in products_data)
        resolved_address_id = OrderService._validate_address(db, current_user.id, address_id, requires_shipping)

        OrderService._validate_payment_rules(zone_type, total_amount, configs, deductions_by_type, pay_channel)

        points_amount = deductions_by_type.get(AssetType.POINTS, Decimal('0.00'))
        channel_asset_type = PAY_CHANNEL_ASSET_MAP.get(pay_channel)
        internal_amount = deductions_by_type.get(channel_asset_type, Decimal('0.00')) if channel_asset_type else Decimal('0.00')
        total_deduction = quantize_amount(points_amount + internal_amount)
        cash_due = max(total_amount - total_deduction, Decimal('0.00'))

        if pay_channel in INTERNAL_PAY_CHANNELS and cash_due > 0:
            raise ConflictError('Selected internal assets are insufficient to complete payment')

        payment_combo = (
            ('EXTERNAL' if pay_channel in EXTERNAL_PAY_CHANNELS else pay_channel) + '+POINTS'
            if points_amount > 0
            else ('EXTERNAL' if pay_channel in EXTERNAL_PAY_CHANNELS else pay_channel)
        )

        return {
            'zone_type': zone_type,
            'total_amount': total_amount,
            'discount_amount': total_deduction,
            'cash_due': cash_due,
            'deductions_by_type': deductions_by_type,
            'pay_channel': pay_channel,
            'payment_combo': payment_combo,
            'requires_shipping': requires_shipping,
            'address_id': resolved_address_id,
        }

    @staticmethod
    def _build_external_payment_payload(order: Order, pay_channel: str) -> dict:
        channel_text = '微信支付' if pay_channel == 'WECHAT' else '支付宝支付'
        return {
            'pay_channel': pay_channel,
            'pay_channel_text': channel_text,
            'status': 'RESERVED',
            'trade_no': f'{pay_channel[:2]}{order.order_no}',
            'prepay_id': f'prepay_{order.id}',
            'cash_due': float(order.payable_amount),
            'mocked': True,
            'message': f'{channel_text}接口已预留，当前返回模拟支付参数',
        }

    @staticmethod
    def create_order(db: Session, current_user: User, payload: dict) -> Order:
        items_payload = payload['items']
        if not items_payload:
            raise ConflictError('Order items required')

        order_type = payload['order_type']
        payload_zone_type = payload.get('zone_type')
        pay_channel = OrderService._resolve_pay_channel(payload.get('pay_channel'))
        deductions_by_type = OrderService._normalize_asset_deductions(payload.get('asset_deductions'))

        products_data: list[dict] = []
        zone_types: set[ZoneType] = set()

        for item in items_payload:
            product = db.get(Product, item['product_id'])
            if not product:
                raise NotFoundError('Product not found')
            if not ProductService.is_visible_to_user(db, current_user, product):
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
            package_required = bool(OrderService._resolve_config_value(configs, actual_zone_type, 'package_required'))
            if package_required:
                OrderService._require_package_qualification(db, current_user, configs)

        if actual_zone_type == ZoneType.HOT_SALE:
            for item in products_data:
                per_user_limit = OrderService._resolve_config_value([item['config']], actual_zone_type, 'per_user_limit')
                OrderService._validate_hot_sale_limit(
                    db,
                    current_user,
                    item['product'].id,
                    item['quantity'],
                    per_user_limit,
                )

        payment_plan = OrderService.build_payment_plan(
            db,
            current_user,
            products_data,
            deductions_by_type,
            pay_channel,
            payload.get('address_id'),
        )

        total_amount = payment_plan['total_amount']
        discount_amount = payment_plan['discount_amount']
        cash_due = payment_plan['cash_due']

        order = Order(
            order_no=generate_order_no('OD'),
            user_id=current_user.id,
            team_id=current_user.team_id,
            order_type=order_type,
            zone_type=actual_zone_type,
            total_amount=total_amount,
            discount_amount=discount_amount,
            payable_amount=cash_due,
            paid_amount=max(total_amount - cash_due, Decimal('0.00')),
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

        for asset_type, amount in payment_plan['deductions_by_type'].items():
            AssetService.consume_amount(
                db,
                current_user.id,
                asset_type,
                amount,
                'ORDER_DEDUCT',
                source_id=order.id,
                source_no=order.order_no,
            )
            db.add(
                OrderAssetDeduction(
                    order_id=order.id,
                    asset_type=asset_type.value,
                    deduct_amount=amount,
                    created_at=now(),
                )
            )

        db.commit()
        db.refresh(order)
        if cash_due <= 0:
            order = OrderService._mark_paid(db, order, external_paid_amount=Decimal('0.00'))
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
    def _mark_paid(db: Session, order: Order, external_paid_amount: Decimal | None = None) -> Order:
        if order.pay_status == PayStatus.PAID:
            return order
        if external_paid_amount is not None:
            order.paid_amount = quantize_amount(Decimal(str(order.discount_amount)) + external_paid_amount)
            order.payable_amount = Decimal('0.00')
        else:
            order.paid_amount = quantize_amount(order.total_amount)
            order.payable_amount = Decimal('0.00')

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

    @staticmethod
    def preview_order_payment(
        db: Session,
        current_user: User,
        payload: dict,
    ) -> dict:
        order_type = OrderType(payload['order_type'])
        zone_type = ZoneType(payload['zone_type']) if payload.get('zone_type') else None
        items_payload = payload.get('items') or []
        if not items_payload:
            raise ConflictError('Order items required')

        products_data: list[dict] = []
        zone_types: set[ZoneType] = set()
        for item in items_payload:
            product = db.get(Product, item['product_id'])
            if not product:
                raise NotFoundError('Product not found')
            if not ProductService.is_visible_to_user(db, current_user, product):
                raise NotFoundError('Product not found')
            quantity = max(1, int(item.get('quantity', 1)))
            zone_types.add(product.zone_type)
            products_data.append(
                {
                    'product': product,
                    'quantity': quantity,
                    'config': OrderService._get_zone_config(db, product.id, product.zone_type),
                    'line_total': quantize_amount(Decimal(str(product.sale_price)) * Decimal(str(quantity))),
                }
            )

        if len(zone_types) != 1:
            raise ConflictError('Mixed zone products are not allowed in one order')
        actual_zone_type = zone_types.pop()
        if zone_type and zone_type != actual_zone_type:
            raise ConflictError('Zone type does not match products')
        OrderService._validate_order_type(actual_zone_type, order_type)

        plan = OrderService.build_payment_plan(
            db,
            current_user,
            products_data,
            OrderService._normalize_asset_deductions(payload.get('asset_deductions')),
            OrderService._resolve_pay_channel(payload.get('pay_channel')),
            payload.get('address_id'),
        )
        return {
            'zone_type': actual_zone_type.value,
            'address_id': plan['address_id'],
            'requires_shipping': plan['requires_shipping'],
            'total_amount': float(plan['total_amount']),
            'discount_amount': float(plan['discount_amount']),
            'cash_due': float(plan['cash_due']),
            'pay_channel': plan['pay_channel'],
            'payment_combo': plan['payment_combo'],
            'asset_deductions': [
                {'asset_type': asset_type.value, 'amount': float(amount)}
                for asset_type, amount in plan['deductions_by_type'].items()
            ],
            'pay_channel_options': [
                {'value': 'BALANCE', 'label': '余额 + 积分'},
                {'value': 'VOUCHER', 'label': '消费金 + 积分'},
                {'value': 'WECHAT', 'label': '微信支付 + 积分'},
                {'value': 'ALIPAY', 'label': '支付宝支付 + 积分'},
            ],
        }

    @staticmethod
    def pay_order(
        db: Session,
        current_user: User,
        order_id: int,
        pay_channel: str,
        points_amount: float = 0,
        auto_complete: bool = True,
    ) -> dict:
        order = OrderService.get_order(db, current_user.id, order_id)
        if order.order_status == OrderStatus.CLOSED:
            raise ConflictError('Closed order cannot be paid')
        if order.pay_status == PayStatus.PAID:
            return {'order': order, 'payment': {'status': 'PAID', 'message': 'Order already paid'}}

        resolved_channel = OrderService._resolve_pay_channel(pay_channel)
        points_amount_decimal = quantize_amount(points_amount)

        if points_amount_decimal > 0:
            raise ConflictError('Points deduction must be selected during order creation')

        if resolved_channel in INTERNAL_PAY_CHANNELS:
            if quantize_amount(order.payable_amount) > 0:
                raise ConflictError('Current order cannot be completed with internal assets')
            order = OrderService._mark_paid(db, order, external_paid_amount=Decimal('0.00'))
            return {'order': order, 'payment': {'status': 'PAID', 'message': 'Internal asset payment completed'}}

        payment = OrderService._build_external_payment_payload(order, resolved_channel)
        if auto_complete:
            order = OrderService._mark_paid(db, order, external_paid_amount=quantize_amount(order.payable_amount))
            payment['status'] = 'PAID'
            payment['message'] = 'Mock external payment completed'
            payment['cash_due'] = 0
        return {'order': order, 'payment': payment}
