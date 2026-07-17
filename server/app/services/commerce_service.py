from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.commerce import ShoppingCartItem, UserFavoriteProduct, UserProductFootprint
from app.models.enums import AssetType, OrderType, PayStatus, ZoneType
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.services.catalog_service import ProductService
from app.services.order_service import OrderService
from app.utils.helpers import now, quantize_amount

ZONE_ORDER_TYPE_MAP = {
    ZoneType.REPURCHASE: OrderType.REPURCHASE_ORDER,
    ZoneType.SELF_OPERATED: OrderType.SELF_OPERATED_ORDER,
    ZoneType.HOT_SALE: OrderType.HOT_SALE_ORDER,
    ZoneType.LOCAL_LIFE: OrderType.LOCAL_LIFE_ORDER,
}


class CommerceService:
    @staticmethod
    def _get_product(db: Session, product_id: int, current_user: User | None = None) -> Product:
        product = db.get(Product, product_id)
        if not product:
            raise NotFoundError('Product not found')
        if current_user and not ProductService.is_visible_to_user(db, current_user, product):
            raise NotFoundError('Product not found')
        return product

    @staticmethod
    def _get_cart_item(db: Session, user_id: int, item_id: int) -> ShoppingCartItem:
        item = db.query(ShoppingCartItem).filter(
            ShoppingCartItem.id == item_id,
            ShoppingCartItem.user_id == user_id,
        ).first()
        if not item:
            raise NotFoundError('Cart item not found')
        return item

    @staticmethod
    def get_product_status(db: Session, user: User, product_id: int) -> dict:
        CommerceService._get_product(db, product_id, user)
        favorite = db.query(UserFavoriteProduct).filter(
            UserFavoriteProduct.user_id == user.id,
            UserFavoriteProduct.product_id == product_id,
        ).first()
        cart_item = db.query(ShoppingCartItem).filter(
            ShoppingCartItem.user_id == user.id,
            ShoppingCartItem.product_id == product_id,
        ).first()
        footprint = db.query(UserProductFootprint).filter(
            UserProductFootprint.user_id == user.id,
            UserProductFootprint.product_id == product_id,
        ).first()
        return {
            'is_favorite': favorite is not None,
            'cart_quantity': int(cart_item.quantity) if cart_item else 0,
            'view_count': int(footprint.view_count) if footprint else 0,
        }

    @staticmethod
    def add_favorite(db: Session, user: User, product_id: int) -> UserFavoriteProduct:
        CommerceService._get_product(db, product_id, user)
        favorite = db.query(UserFavoriteProduct).filter(
            UserFavoriteProduct.user_id == user.id,
            UserFavoriteProduct.product_id == product_id,
        ).first()
        if favorite:
            return favorite
        favorite = UserFavoriteProduct(user_id=user.id, product_id=product_id)
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        return favorite

    @staticmethod
    def remove_favorite(db: Session, user_id: int, product_id: int) -> None:
        favorite = db.query(UserFavoriteProduct).filter(
            UserFavoriteProduct.user_id == user_id,
            UserFavoriteProduct.product_id == product_id,
        ).first()
        if not favorite:
            return
        db.delete(favorite)
        db.commit()

    @staticmethod
    def list_favorites(db: Session, user: User) -> list[UserFavoriteProduct]:
        rows = db.query(UserFavoriteProduct).filter(
            UserFavoriteProduct.user_id == user.id,
        ).order_by(UserFavoriteProduct.id.desc()).all()
        return [
            item for item in rows
            if ProductService.is_visible_to_user(db, user, db.get(Product, item.product_id))
        ]

    @staticmethod
    def record_footprint(db: Session, user: User, product_id: int) -> UserProductFootprint:
        CommerceService._get_product(db, product_id, user)
        footprint = db.query(UserProductFootprint).filter(
            UserProductFootprint.user_id == user.id,
            UserProductFootprint.product_id == product_id,
        ).first()
        if footprint:
            footprint.view_count = int(footprint.view_count or 0) + 1
            footprint.last_viewed_at = now()
        else:
            footprint = UserProductFootprint(
                user_id=user.id,
                product_id=product_id,
                view_count=1,
                last_viewed_at=now(),
            )
            db.add(footprint)
        db.commit()
        db.refresh(footprint)
        return footprint

    @staticmethod
    def remove_footprint(db: Session, user_id: int, product_id: int) -> None:
        footprint = db.query(UserProductFootprint).filter(
            UserProductFootprint.user_id == user_id,
            UserProductFootprint.product_id == product_id,
        ).first()
        if not footprint:
            return
        db.delete(footprint)
        db.commit()

    @staticmethod
    def list_footprints(db: Session, user: User) -> list[UserProductFootprint]:
        rows = db.query(UserProductFootprint).filter(
            UserProductFootprint.user_id == user.id,
        ).order_by(UserProductFootprint.last_viewed_at.desc(), UserProductFootprint.id.desc()).all()
        return [
            item for item in rows
            if ProductService.is_visible_to_user(db, user, db.get(Product, item.product_id))
        ]

    @staticmethod
    def list_cart_items(db: Session, user: User) -> list[ShoppingCartItem]:
        rows = db.query(ShoppingCartItem).filter(
            ShoppingCartItem.user_id == user.id,
        ).order_by(ShoppingCartItem.updated_at.desc(), ShoppingCartItem.id.desc()).all()
        return [
            item for item in rows
            if ProductService.is_visible_to_user(db, user, db.get(Product, item.product_id))
        ]

    @staticmethod
    def add_cart_item(db: Session, user: User, product_id: int, quantity: int = 1) -> ShoppingCartItem:
        product = CommerceService._get_product(db, product_id, user)
        qty = max(1, int(quantity or 1))
        item = db.query(ShoppingCartItem).filter(
            ShoppingCartItem.user_id == user.id,
            ShoppingCartItem.product_id == product_id,
        ).first()
        if item:
            item.quantity = min(product.stock or qty, int(item.quantity) + qty) if product.stock else int(item.quantity) + qty
            item.selected = True
        else:
            item = ShoppingCartItem(
                user_id=user.id,
                product_id=product_id,
                quantity=min(product.stock or qty, qty) if product.stock else qty,
                selected=True,
            )
            db.add(item)
        item.updated_at = now()
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_cart_item(
        db: Session,
        user: User,
        item_id: int,
        quantity: int | None = None,
        selected: bool | None = None,
    ) -> ShoppingCartItem:
        item = CommerceService._get_cart_item(db, user.id, item_id)
        product = CommerceService._get_product(db, item.product_id, user)
        if quantity is not None:
            next_quantity = max(1, int(quantity))
            if product.stock and next_quantity > product.stock:
                raise ConflictError('Stock insufficient')
            item.quantity = next_quantity
        if selected is not None:
            item.selected = bool(selected)
        item.updated_at = now()
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def remove_cart_item(db: Session, user_id: int, item_id: int) -> None:
        item = CommerceService._get_cart_item(db, user_id, item_id)
        db.delete(item)
        db.commit()

    @staticmethod
    def checkout_cart(
        db: Session,
        current_user: User,
        item_ids: list[int] | None,
        address_id: int | None = None,
        points_amount: float = 0,
        pay_channel: str = 'BALANCE',
        auto_complete: bool = True,
    ) -> dict:
        rows = db.query(ShoppingCartItem).filter(ShoppingCartItem.user_id == current_user.id)
        if item_ids:
            rows = rows.filter(ShoppingCartItem.id.in_(item_ids))
        else:
            rows = rows.filter(ShoppingCartItem.selected.is_(True))
        cart_items = rows.order_by(ShoppingCartItem.id.asc()).all()
        if not cart_items:
            raise ConflictError('No cart items selected')

        first_product = CommerceService._get_product(db, cart_items[0].product_id, current_user)
        zone_type = first_product.zone_type
        if zone_type not in ZONE_ORDER_TYPE_MAP:
            raise ConflictError('Unsupported zone type for cart checkout')

        total_amount = Decimal('0.00')
        for item in cart_items:
            product = CommerceService._get_product(db, item.product_id, current_user)
            total_amount += quantize_amount(Decimal(str(product.sale_price)) * Decimal(str(item.quantity)))

        points_decimal = quantize_amount(points_amount)
        if points_decimal < 0:
            raise ConflictError('Points amount cannot be negative')
        if points_decimal > total_amount:
            raise ConflictError('Points deduction exceeds order total')

        resolved_pay_channel = OrderService._resolve_pay_channel(pay_channel)
        deductions = []
        if points_decimal > 0:
            deductions.append({'asset_type': AssetType.POINTS.value, 'amount': points_decimal})
        if resolved_pay_channel == 'BALANCE':
            balance_amount = quantize_amount(total_amount - points_decimal)
            if balance_amount > 0:
                deductions.append({'asset_type': AssetType.BALANCE.value, 'amount': balance_amount})
        if resolved_pay_channel == 'VOUCHER':
            voucher_amount = quantize_amount(total_amount - points_decimal)
            if voucher_amount > 0:
                deductions.append({'asset_type': AssetType.VOUCHER.value, 'amount': voucher_amount})

        payload = {
            'order_type': ZONE_ORDER_TYPE_MAP[zone_type],
            'zone_type': zone_type,
            'pay_channel': resolved_pay_channel,
            'address_id': address_id,
            'items': [{'product_id': item.product_id, 'sku_id': item.sku_id, 'quantity': item.quantity} for item in cart_items],
            'asset_deductions': deductions,
        }
        order = OrderService.create_order(db, current_user, payload)
        payment = None
        if resolved_pay_channel in {'WECHAT', 'ALIPAY'}:
            try:
                result = OrderService.pay_order(
                    db,
                    current_user,
                    order.id,
                    resolved_pay_channel,
                    points_amount=0,
                    auto_complete=auto_complete,
                )
                order = result['order']
                payment = result['payment']
            except AppError as exc:
                payment = {
                    'status': 'FAILED',
                    'message': exc.message,
                }

        for item in cart_items:
            db.delete(item)
        db.commit()
        db.refresh(order)
        return {'order': order, 'payment': payment}

    @staticmethod
    def list_shipments(db: Session, user_id: int) -> list[Order]:
        orders = db.query(Order).filter(
            Order.user_id == user_id,
            Order.pay_status == PayStatus.PAID,
        ).order_by(Order.id.desc()).all()
        return [order for order in orders if CommerceService.order_requires_shipping(db, order.id)]

    @staticmethod
    def get_shipment(db: Session, user_id: int, order_id: int) -> Order:
        order = OrderService.get_order(db, user_id, order_id)
        if not CommerceService.order_requires_shipping(db, order.id):
            raise NotFoundError('Shipment not found')
        return order

    @staticmethod
    def order_requires_shipping(db: Session, order_id: int) -> bool:
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        if not items:
            return False
        products = db.query(Product).filter(Product.id.in_([item.product_id for item in items])).all()
        return any(bool(product.requires_shipping) for product in products)
