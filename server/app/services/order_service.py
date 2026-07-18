from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import cast

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.payment_config import enabled_external_payment_channels, payment_config
from app.models.address import UserAddress
from app.models.asset import UserAssetLedger
from app.models.enums import AssetType, OrderStatus, OrderType, PaymentStatus, PayStatus, ProductStatus, ZoneType
from app.models.order import Order, OrderAssetDeduction, OrderItem
from app.models.payment import PaymentTransaction
from app.models.product import Product, ProductZoneConfig
from app.models.user import User
from app.services.admin_scope import AdminScopeService
from app.services.asset_service import AssetService
from app.services.catalog_service import ProductService
from app.services.commission_service import CommissionService
from app.services.region_dividend_service import RegionDividendService
from app.utils.helpers import generate_order_no, now, quantize_amount

INTERNAL_PAY_CHANNELS = {'BALANCE', 'VOUCHER', 'POINTS'}
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

UNPAID_ORDER_EXPIRE_MINUTES = 30


class OrderService:
    @staticmethod
    def _base_admin_query(db: Session, current_user: User):
        query = db.query(Order).join(User, User.id == Order.user_id)
        if not AdminScopeService.has_global_scope(current_user):
            team_id = AdminScopeService.require_team_id(current_user)
            query = query.filter(Order.team_id == team_id)
        return query

    @staticmethod
    def list_orders_for_admin(
        db: Session,
        current_user: User,
        *,
        keyword: str | None = None,
        order_status: str | None = None,
        pay_status: str | None = None,
        order_type: str | None = None,
        zone_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        OrderService.expire_pending_orders(db)
        query = OrderService._base_admin_query(db, current_user)

        if keyword:
            like = f'%{keyword.strip()}%'
            query = query.filter(
                or_(
                    Order.order_no.ilike(like),
                    User.phone.ilike(like),
                    User.nickname.ilike(like),
                )
            )

        if order_status:
            query = query.filter(Order.order_status == OrderStatus(order_status))
        if pay_status:
            query = query.filter(Order.pay_status == PayStatus(pay_status))
        if order_type:
            query = query.filter(Order.order_type == OrderType(order_type))
        if zone_type:
            query = query.filter(Order.zone_type == ZoneType(zone_type))

        safe_page = max(page, 1)
        safe_page_size = max(1, min(page_size, 100))
        total = query.order_by(None).count()
        rows = (
            query.order_by(Order.id.desc())
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
            .all()
        )
        return {
            'items': rows,
            'total': total,
            'page': safe_page,
            'page_size': safe_page_size,
        }

    @staticmethod
    def get_order_for_admin(db: Session, order_id: int, current_user: User) -> Order:
        OrderService.expire_pending_orders(db)
        order = db.get(Order, order_id)
        if not order:
            raise NotFoundError('Order not found')
        AdminScopeService.ensure_team_visible(current_user, order.team_id)
        return order

    @staticmethod
    def order_requires_shipping(db: Session, order_id: int) -> bool:
        product_ids = [
            product_id
            for (product_id,) in db.query(OrderItem.product_id).filter(OrderItem.order_id == order_id).all()
        ]
        if not product_ids:
            return False
        return bool(
            db.query(Product.id).filter(
                Product.id.in_(product_ids),
                Product.requires_shipping.is_(True),
            ).first()
        )

    @staticmethod
    def _restore_order_inventory(db: Session, order: Order) -> None:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        for item in items:
            product = db.get(Product, item.product_id)
            if not product:
                continue
            quantity = max(int(item.quantity or 0), 0)
            product.stock = int(product.stock or 0) + quantity
            product.sold_count = max(int(product.sold_count or 0) - quantity, 0)

    @staticmethod
    def _refund_order_deductions(db: Session, order: Order) -> None:
        deductions = db.query(OrderAssetDeduction).filter(OrderAssetDeduction.order_id == order.id).all()
        for deduction in deductions:
            AssetService.refund_consumed_amount(
                db,
                order.user_id,
                AssetType(str(deduction.asset_type).upper()),
                deduction.deduct_amount,
                'ORDER_CANCEL_REFUND',
                source_id=order.id,
                source_no=order.order_no,
                remark='Order canceled or refunded',
            )

    @staticmethod
    def _revoke_order_rewards(db: Session, order: Order) -> None:
        reward_business_types = {
            'SELF_OPERATED_REWARD',
            'PACKAGE_REWARD',
            'POINTS_SUBSIDY',
            'PACKAGE_REFERRAL_REWARD',
        }
        rewards = db.query(UserAssetLedger).filter(
            UserAssetLedger.business_type.in_(reward_business_types),
            UserAssetLedger.source_id == order.id,
        ).all()
        for reward in rewards:
            AssetService.revoke_added_amount(
                db,
                reward.user_id,
                reward.asset_type,
                reward.change_amount,
                'ORDER_REFUND_REWARD_REVOKE',
                source_id=order.id,
                source_no=order.order_no,
                remark='Reward revoked after order refund',
            )

    @staticmethod
    def _close_refunded_payment_transactions(db: Session, order: Order) -> None:
        transactions = db.query(PaymentTransaction).filter(
            PaymentTransaction.order_id == order.id,
            PaymentTransaction.status == PaymentStatus.PAID,
        ).all()
        for transaction in transactions:
            notify_payload = transaction.notify_payload or {}
            if not bool(notify_payload.get('mocked')):
                raise ConflictError('External payment refund must be completed through the payment provider')
            transaction.status = PaymentStatus.CLOSED
            transaction.failed_reason = 'Mock payment refunded'

    @staticmethod
    def _close_pending_payment_transactions(db: Session, order: Order) -> None:
        transactions = db.query(PaymentTransaction).filter(
            PaymentTransaction.order_id == order.id,
            PaymentTransaction.status == PaymentStatus.PENDING,
        ).all()
        for transaction in transactions:
            transaction.status = PaymentStatus.CLOSED
            transaction.failed_reason = 'Order canceled or expired'

    @staticmethod
    def _cancel_order_instance(
        db: Session,
        order: Order,
        *,
        refunded: bool,
        commit: bool = True,
    ) -> Order:
        if order.order_status == OrderStatus.REFUND:
            return order
        if order.order_type == OrderType.LOCAL_LIFE_ORDER:
            raise ConflictError('Local-life orders use the verification workflow')
        requires_shipping = OrderService.order_requires_shipping(db, order.id)
        if order.order_status == OrderStatus.COMPLETED and (not refunded or requires_shipping):
            raise ConflictError('Completed shipping order cannot be canceled or directly refunded')
        if refunded:
            if order.pay_status != PayStatus.PAID:
                raise ConflictError('Only paid orders can be refunded')
            allowed_statuses = {OrderStatus.PENDING_SHIP, OrderStatus.SHIPPED}
            if not requires_shipping:
                allowed_statuses.add(OrderStatus.COMPLETED)
            if order.order_status not in allowed_statuses:
                raise ConflictError('Current order status cannot be refunded')
            OrderService._close_refunded_payment_transactions(db, order)
            CommissionService.cancel_for_order(db, order.id)
            OrderService._revoke_order_rewards(db, order)
        else:
            if order.pay_status != PayStatus.UNPAID or order.order_status != OrderStatus.PENDING_PAYMENT:
                raise ConflictError('Only unpaid pending orders can be canceled')

        OrderService._close_pending_payment_transactions(db, order)
        OrderService._refund_order_deductions(db, order)
        OrderService._restore_order_inventory(db, order)
        order.order_status = OrderStatus.REFUND
        order.pay_status = PayStatus.REFUNDED if refunded else PayStatus.UNPAID
        order.payable_amount = Decimal('0.00')
        if not refunded:
            order.paid_amount = Decimal('0.00')
        order.confirmed_at = None

        if commit:
            db.commit()
            db.refresh(order)
        else:
            db.flush()
        return order

    @staticmethod
    def expire_pending_orders(db: Session, user_id: int | None = None) -> int:
        threshold = now() - timedelta(minutes=UNPAID_ORDER_EXPIRE_MINUTES)
        query = db.query(Order).filter(
            Order.order_status == OrderStatus.PENDING_PAYMENT,
            Order.pay_status == PayStatus.UNPAID,
            Order.order_type != OrderType.LOCAL_LIFE_ORDER,
            Order.created_at < threshold,
        )
        if user_id is not None:
            query = query.filter(Order.user_id == user_id)
        rows = query.all()
        for order in rows:
            OrderService._cancel_order_instance(db, order, refunded=False, commit=False)
        if rows:
            db.commit()
        return len(rows)

    @staticmethod
    def _confirm_order_instance(db: Session, order: Order) -> Order:
        if order.pay_status != PayStatus.PAID:
            raise ConflictError('Only paid orders can be confirmed')
        if order.order_status == OrderStatus.COMPLETED:
            return order
        if order.order_status == OrderStatus.REFUND:
            raise ConflictError('Refunded order cannot be confirmed')
        if order.order_status != OrderStatus.SHIPPED:
            raise ConflictError('Only shipped orders can be confirmed')
        order.order_status = OrderStatus.COMPLETED
        order.confirmed_at = now()
        db.commit()

        # 结算分销佣金
        CommissionService.settle_for_order(db, order.id)

        # 处理区域订单分红（订单完成后立刻分红）
        if order.legacy_address_id:
            address = db.get(UserAddress, order.legacy_address_id)
            if address:
                RegionDividendService.process_order_dividend(
                    db, order,
                    {'province': address.province, 'city': address.city, 'district': address.district}
                )

        db.refresh(order)
        return order

    @staticmethod
    def confirm_order_for_admin(db: Session, order_id: int, current_user: User) -> Order:
        order = OrderService.get_order_for_admin(db, order_id, current_user)
        return OrderService._confirm_order_instance(db, order)

    @staticmethod
    def close_order_for_admin(db: Session, order_id: int, current_user: User) -> Order:
        order = OrderService.get_order_for_admin(db, order_id, current_user)
        return OrderService._cancel_order_instance(db, order, refunded=False)

    @staticmethod
    def refund_order_for_admin(db: Session, order_id: int, current_user: User) -> Order:
        order = OrderService.get_order_for_admin(db, order_id, current_user)
        return OrderService._cancel_order_instance(db, order, refunded=True)

    @staticmethod
    def mark_paid_for_admin(db: Session, order_id: int, current_user: User) -> Order:
        order = OrderService.get_order_for_admin(db, order_id, current_user)
        if order.order_status == OrderStatus.REFUND:
            raise ConflictError('Refunded order cannot be marked paid')
        return OrderService._mark_paid(db, order)

    @staticmethod
    def ship_order_for_admin(
        db: Session,
        order_id: int,
        current_user: User,
        tracking_no: str | None = None,
        tracking_company: str | None = None
    ) -> Order:
        order = OrderService.get_order_for_admin(db, order_id, current_user)
        if order.order_status not in (OrderStatus.PENDING_SHIP,):
            raise ConflictError('Only pending-ship orders can be shipped')
        if not str(tracking_no or '').strip():
            raise ConflictError('Tracking number is required')
        order.order_status = OrderStatus.SHIPPED
        order.legacy_logistics_no = str(tracking_no).strip()
        if tracking_company:
            order.legacy_logistics_name = str(tracking_company).strip() or None
        db.commit()
        db.refresh(order)
        return order

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
            }
        if zone_type == ZoneType.SELF_OPERATED:
            return {
                'package_required': False,
                'voucher_deduct_min_rate': Decimal('50'),
                'voucher_deduct_max_rate': Decimal('70'),
                'ai_coupon_max_deduct_rate': Decimal('20'),
                'ai_coupon_reward_rate': Decimal('20'),
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
                'alipay_purchase_enabled': True,
                'wechat_purchase_enabled': False,
                'points_only_enabled': False,
                'points_cash_enabled': True,
                'cash_only_enabled': True,
                'balance_only_enabled': True,
                'balance_points_enabled': True,
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
            'alipay_purchase_enabled': True,
            'wechat_purchase_enabled': False,
            'points_only_enabled': False,
            'points_cash_enabled': True,
            'cash_only_enabled': True,
            'balance_only_enabled': True,
            'balance_points_enabled': True,
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
            Order.order_status != OrderStatus.REFUND,
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
    def _config_value(config: ProductZoneConfig | None, zone_type: ZoneType, field: str):
        default_value = OrderService._zone_config_defaults(zone_type).get(field)
        if config and getattr(config, field, None) is not None:
            return getattr(config, field)
        return default_value

    @staticmethod
    def _purchase_mode(
        total_amount: Decimal,
        deductions_by_type: dict[AssetType, Decimal],
        pay_channel: str,
    ) -> str:
        points_amount = quantize_amount(deductions_by_type.get(AssetType.POINTS, Decimal('0')))
        non_points_amount = quantize_amount(
            sum((amount for asset_type, amount in deductions_by_type.items() if asset_type != AssetType.POINTS), Decimal('0'))
        )
        total_deduction = quantize_amount(points_amount + non_points_amount)
        cash_due = max(quantize_amount(total_amount) - total_deduction, Decimal('0'))
        if points_amount > 0 and cash_due == 0 and non_points_amount == 0:
            return 'POINTS_ONLY'
        if points_amount > 0:
            return 'POINTS_CASH'
        return 'CASH_ONLY'

    @staticmethod
    def _validate_purchase_mode(
        zone_type: ZoneType,
        configs: list[ProductZoneConfig | None],
        purchase_mode: str,
    ) -> None:
        field_map = {
            'POINTS_ONLY': 'points_only_enabled',
            'POINTS_CASH': 'points_cash_enabled',
            'CASH_ONLY': 'cash_only_enabled',
        }
        field = field_map[purchase_mode]
        if not all(bool(OrderService._config_value(config, zone_type, field)) for config in configs):
            label = {
                'POINTS_ONLY': 'pure points',
                'POINTS_CASH': 'points + cash',
                'CASH_ONLY': 'cash only',
            }[purchase_mode]
            raise ConflictError(f'Current product does not support {label} purchase')

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
            if not address:
                raise ConflictError('Shipping address required')
            return address.id
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
        if pay_channel == 'POINTS':
            allowed_assets = {AssetType.POINTS}

        invalid_assets = set(deductions_by_type) - allowed_assets
        if invalid_assets:
            raise ConflictError('Current payment combination only supports points with selected pay channel')

        if pay_channel in PAY_CHANNEL_ASSET_MAP and not deductions_by_type.get(PAY_CHANNEL_ASSET_MAP[pay_channel], Decimal('0')):
            raise ConflictError('Internal payment channel must provide deduction amount')
        if pay_channel == 'POINTS' and deductions_by_type.get(AssetType.POINTS, Decimal('0')) <= 0:
            raise ConflictError('Points payment amount is required')

        if pay_channel == 'VOUCHER' and zone_type != ZoneType.SELF_OPERATED:
            raise ConflictError('Voucher payment only supports self-operated zone')

        if pay_channel in EXTERNAL_PAY_CHANNELS and pay_channel not in enabled_external_payment_channels():
            if pay_channel == 'WECHAT':
                raise ConflictError('Wechat payment is under development')
            raise ConflictError('Alipay payment is not enabled')

        if pay_channel == 'BALANCE' and not all(
            bool(OrderService._config_value(config, zone_type, 'balance_purchase_enabled')) for config in configs
        ):
            raise ConflictError('Balance payment is disabled for current product')

        if pay_channel == 'ALIPAY' and not all(
            bool(OrderService._config_value(config, zone_type, 'alipay_purchase_enabled')) for config in configs
        ):
            raise ConflictError('Alipay payment is disabled for current product')

        points_amount = deductions_by_type.get(AssetType.POINTS, Decimal('0'))
        if points_amount > total_amount:
            raise ConflictError('Points deduction exceeds order total')
        if points_amount > 0 and not all(bool(OrderService._config_value(config, zone_type, 'points_purchase_enabled')) for config in configs):
            raise ConflictError('Points payment is disabled for current product')

        voucher_amount = deductions_by_type.get(AssetType.VOUCHER, Decimal('0'))
        if pay_channel == 'VOUCHER' and voucher_amount <= 0:
            raise ConflictError('Voucher payment amount is required')

        total_deduction = sum(deductions_by_type.values(), Decimal('0.00'))
        if total_deduction > total_amount:
            raise ConflictError('Asset deductions exceed order total')
        purchase_mode = OrderService._purchase_mode(total_amount, deductions_by_type, pay_channel)
        if purchase_mode != 'CASH_ONLY':
            OrderService._validate_purchase_mode(zone_type, configs, purchase_mode)

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
        for asset_type, amount in deductions_by_type.items():
            account = AssetService.get_account(db, current_user.id, asset_type)
            if quantize_amount(account.available_amount) < quantize_amount(amount):
                raise ConflictError(f'{asset_type.value} insufficient')

        points_amount = deductions_by_type.get(AssetType.POINTS, Decimal('0.00'))
        channel_asset_type = PAY_CHANNEL_ASSET_MAP.get(pay_channel)
        internal_amount = deductions_by_type.get(channel_asset_type, Decimal('0.00')) if channel_asset_type else Decimal('0.00')
        total_deduction = quantize_amount(points_amount + internal_amount)
        cash_due = max(total_amount - total_deduction, Decimal('0.00'))

        if pay_channel in INTERNAL_PAY_CHANNELS and cash_due > 0:
            raise ConflictError('Selected internal assets are insufficient to complete payment')

        purchase_mode = OrderService._purchase_mode(total_amount, deductions_by_type, pay_channel)
        payment_combo = {
            'POINTS_ONLY': 'POINTS',
            'POINTS_CASH': 'POINTS+CASH',
            'CASH_ONLY': 'CASH',
        }[purchase_mode]

        return {
            'zone_type': zone_type,
            'total_amount': total_amount,
            'discount_amount': total_deduction,
            'cash_due': cash_due,
            'deductions_by_type': deductions_by_type,
            'pay_channel': pay_channel,
            'payment_combo': payment_combo,
            'purchase_mode': purchase_mode,
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
        OrderService.expire_pending_orders(db)
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
            product = db.query(Product).filter(Product.id == item['product_id']).with_for_update().first()
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
            order_status=OrderStatus.PENDING_PAYMENT,
            legacy_address_id=payment_plan['address_id'],
        )
        db.add(order)
        db.flush()

        for item in products_data:
            product = cast(Product, item['product'])
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
        OrderService.expire_pending_orders(db, user_id=user_id)
        return db.query(Order).filter(Order.user_id == user_id).order_by(Order.id.desc()).all()

    @staticmethod
    def get_order(db: Session, user_id: int, order_id: int) -> Order:
        OrderService.expire_pending_orders(db, user_id=user_id)
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
        if order.order_status == OrderStatus.REFUND:
            raise ConflictError('Canceled or refunded order cannot be paid')
        if external_paid_amount is not None:
            order.paid_amount = quantize_amount(Decimal(str(order.discount_amount)) + external_paid_amount)
            order.payable_amount = Decimal('0.00')
        else:
            order.paid_amount = quantize_amount(order.total_amount)
            order.payable_amount = Decimal('0.00')

        order.pay_status = PayStatus.PAID
        requires_shipping = OrderService.order_requires_shipping(db, order.id)
        order.order_status = OrderStatus.PENDING_SHIP if requires_shipping else OrderStatus.COMPLETED
        order.paid_at = now()
        if not requires_shipping:
            order.confirmed_at = order.paid_at

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
        if not requires_shipping:
            CommissionService.settle_for_order(db, order.id)
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
        if not payment_config.mock_external_payment:
            raise ConflictError('Demo payment is disabled')
        order = OrderService.get_order(db, user_id, order_id)
        return OrderService._mark_paid(db, order)

    @staticmethod
    def confirm_order(db: Session, user_id: int, order_id: int) -> Order:
        order = OrderService.get_order(db, user_id, order_id)
        return OrderService._confirm_order_instance(db, order)

    @staticmethod
    def cancel_order(db: Session, user_id: int, order_id: int) -> Order:
        order = OrderService.get_order(db, user_id, order_id)
        return OrderService._cancel_order_instance(db, order, refunded=False)

    @staticmethod
    def refund_order(db: Session, user_id: int, order_id: int) -> Order:
        order = OrderService.get_order(db, user_id, order_id)
        return OrderService._cancel_order_instance(db, order, refunded=True)

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
        configs = [item['config'] for item in products_data]
        balance_available = all(
            bool(OrderService._config_value(config, actual_zone_type, 'balance_purchase_enabled')) for config in configs
        )
        alipay_product_enabled = all(
            bool(OrderService._config_value(config, actual_zone_type, 'alipay_purchase_enabled')) for config in configs
        )
        alipay_provider_ready = 'ALIPAY' in enabled_external_payment_channels()
        return {
            'zone_type': actual_zone_type.value,
            'address_id': plan['address_id'],
            'requires_shipping': plan['requires_shipping'],
            'total_amount': float(plan['total_amount']),
            'discount_amount': float(plan['discount_amount']),
            'cash_due': float(plan['cash_due']),
            'pay_channel': plan['pay_channel'],
            'payment_combo': plan['payment_combo'],
            'purchase_mode': plan['purchase_mode'],
            'asset_deductions': [
                {'asset_type': asset_type.value, 'amount': float(amount)}
                for asset_type, amount in plan['deductions_by_type'].items()
            ],
            'pay_channel_options': [
                {
                    'value': 'BALANCE',
                    'label': '余额支付',
                    'available': balance_available,
                    'unavailable_reason': '' if balance_available else '后台未开启余额支付',
                },
                {'value': 'WECHAT', 'label': '微信支付', 'available': False, 'desc': '正在开发'},
                {
                    'value': 'ALIPAY',
                    'label': '支付宝支付',
                    'available': alipay_product_enabled and alipay_provider_ready,
                    'unavailable_reason': (
                        ''
                        if alipay_product_enabled and alipay_provider_ready
                        else '后台未开启支付宝支付'
                        if not alipay_product_enabled
                        else '支付宝全局配置未就绪'
                    ),
                },
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
        if order.order_status == OrderStatus.REFUND:
            raise ConflictError('Refunded order cannot be paid')
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

        from app.services.payment_service import PaymentService

        payment_result = PaymentService.prepare_external_payment(db, order, resolved_channel)
        payment = payment_result['payment']
        if auto_complete and payment.get('mocked'):
            order = PaymentService.confirm_paid_order(db, payment_result['transaction'], notify_payload={'mocked': True})
            payment = {
                **payment,
                'status': 'PAID',
                'message': 'Mock external payment completed',
                'cash_due': 0,
            }
        return {'order': order, 'payment': payment}
