from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.api.deps.auth import require_roles
from app.db.session import get_db
from app.models.commerce import UserFavoriteProduct, UserProductFootprint
from app.models.enums import GlobalRole, OrderStatus
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User

admin_router = APIRouter(prefix='/admin/commerce')

SHIPMENT_ORDER_STATUSES = (
    OrderStatus.PENDING_SHIP,
    OrderStatus.SHIPPED,
    OrderStatus.COMPLETED,
    OrderStatus.REFUND,
)
SHIPMENT_STATUS_BY_ORDER_STATUS = {
    OrderStatus.PENDING_SHIP: ('pending', '待发货'),
    OrderStatus.SHIPPED: ('shipping', '运输中'),
    OrderStatus.COMPLETED: ('delivered', '已签收'),
    OrderStatus.REFUND: ('cancelled', '已取消'),
}
ORDER_STATUS_BY_SHIPMENT_STATUS = {
    'pending': OrderStatus.PENDING_SHIP,
    'shipping': OrderStatus.SHIPPED,
    'delivered': OrderStatus.COMPLETED,
    'cancelled': OrderStatus.REFUND,
}


@admin_router.get('/favorites')
def list_all_favorites(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = db.query(UserFavoriteProduct, User.nickname, Product.product_name.label('product_name')).join(
        User, UserFavoriteProduct.user_id == User.id
    ).join(
        Product, UserFavoriteProduct.product_id == Product.id
    )

    if keyword:
        query = query.filter(
            (User.nickname.contains(keyword)) | (Product.product_name.contains(keyword))
        )

    total = query.count()
    rows = query.order_by(desc(UserFavoriteProduct.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for row in rows:
        items.append({
            'id': row[0].id,
            'user_id': row[0].user_id,
            'username': row[1],
            'product_id': row[0].product_id,
            'product_name': row[2],
            'created_at': row[0].created_at.isoformat() if row[0].created_at else None,
        })

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        }
    }


@admin_router.delete('/favorites/{favorite_id}')
def delete_favorite(
    favorite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    favorite = db.query(UserFavoriteProduct).filter(UserFavoriteProduct.id == favorite_id).first()
    if not favorite:
        return {'code': 404, 'message': 'Favorite not found', 'data': None}

    db.delete(favorite)
    db.commit()
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@admin_router.get('/footprints')
def list_all_footprints(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = db.query(UserProductFootprint, User.nickname, Product.product_name.label('product_name')).join(
        User, UserProductFootprint.user_id == User.id
    ).join(
        Product, UserProductFootprint.product_id == Product.id
    )

    if keyword:
        query = query.filter(
            (User.nickname.contains(keyword)) | (Product.product_name.contains(keyword))
        )

    total = query.count()
    rows = query.order_by(desc(UserProductFootprint.last_viewed_at)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for row in rows:
        items.append({
            'id': row[0].id,
            'user_id': row[0].user_id,
            'username': row[1],
            'product_id': row[0].product_id,
            'product_name': row[2],
            'view_count': row[0].view_count,
            'first_viewed_at': row[0].first_viewed_at.isoformat() if row[0].first_viewed_at else None,
            'last_viewed_at': row[0].last_viewed_at.isoformat() if row[0].last_viewed_at else None,
        })

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        }
    }


@admin_router.delete('/footprints/{footprint_id}')
def delete_footprint(
    footprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    footprint = db.query(UserProductFootprint).filter(UserProductFootprint.id == footprint_id).first()
    if not footprint:
        return {'code': 404, 'message': 'Footprint not found', 'data': None}

    db.delete(footprint)
    db.commit()
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@admin_router.get('/shipments')
def list_all_shipments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    query = db.query(Order).filter(Order.order_status.in_(SHIPMENT_ORDER_STATUSES))

    if keyword:
        like = f'%{keyword.strip()}%'
        query = query.filter(
            or_(
                Order.order_no.ilike(like),
                Order.legacy_logistics_no.ilike(like),
            )
        )

    if status:
        target_status = ORDER_STATUS_BY_SHIPMENT_STATUS.get(status)
        if target_status:
            query = query.filter(Order.order_status == target_status)

    total = query.count()
    rows = query.order_by(desc(Order.updated_at)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for order in rows:
        shipment_status, shipment_status_text = _get_shipment_status(order)
        items.append({
            'id': order.id,
            'order_no': order.order_no,
            'user_id': order.user_id,
            'title': _get_order_title(db, order),
            'status': shipment_status,
            'status_text': shipment_status_text,
            'tracking_no': order.legacy_logistics_no or '',
            'carrier_name': order.legacy_logistics_name or '',
            'carrier_phone': '',
            'amount': float(order.total_amount or 0),
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        })

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items,
        }
    }


@admin_router.get('/shipments/{order_id}')
def shipment_admin_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN, GlobalRole.TEAM_ADMIN)),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {'code': 404, 'message': 'Order not found', 'data': None}

    user = db.query(User).filter(User.id == order.user_id).first()
    shipment_status, shipment_status_text = _get_shipment_status(order)

    return {
        'code': 0,
        'message': 'success',
        'data': {
            'id': order.id,
            'order_no': order.order_no,
            'user_id': order.user_id,
            'username': user.nickname if user else '',
            'title': _get_order_title(db, order),
            'status': shipment_status,
            'status_text': shipment_status_text,
            'status_hint': _get_shipping_hint(shipment_status),
            'tracking_no': order.legacy_logistics_no or '',
            'carrier_name': order.legacy_logistics_name or '',
            'carrier_phone': '',
            'delivery_mode': 'express',
            'delivery_mode_text': _get_delivery_mode_text('express'),
            'amount': float(order.total_amount or 0),
            'progress_percent': _get_shipping_progress(shipment_status),
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
        }
    }


@admin_router.post('/shipments/{order_id}/update-tracking')
def update_shipment_tracking(
    order_id: int,
    tracking_no: str = Query(...),
    carrier_name: str = Query(default=''),
    carrier_phone: str = Query(default=''),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(GlobalRole.SUPER_ADMIN)),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {'code': 404, 'message': 'Order not found', 'data': None}

    order.legacy_logistics_no = tracking_no
    order.legacy_logistics_name = carrier_name
    if order.order_status == OrderStatus.PENDING_SHIP:
        order.order_status = OrderStatus.SHIPPED
    db.commit()

    return {'code': 0, 'message': 'success', 'data': {'success': True}}


def _get_shipment_status(order: Order):
    return SHIPMENT_STATUS_BY_ORDER_STATUS.get(order.order_status, ('pending', '待发货'))


def _get_order_title(db: Session, order: Order):
    item = db.query(OrderItem).filter(OrderItem.order_id == order.id).order_by(OrderItem.id.asc()).first()
    return item.product_name if item else f'订单 {order.order_no}'


def _get_shipping_hint(status):
    hints = {
        'pending': '等待发货',
        'shipping': '包裹运输中，请保持电话畅通',
        'delivered': '已签收，感谢您的购买',
        'cancelled': '已取消',
    }
    return hints.get(status, '')


def _get_delivery_mode_text(mode):
    modes = {
        'express': '快递配送',
        'self_pickup': '自提',
        '同城': '同城配送',
        'pickup': '上门自提',
    }
    return modes.get(mode, mode or '标准配送')


def _get_shipping_progress(status):
    progress = {
        'pending': 20,
        'shipping': 60,
        'delivered': 100,
        'cancelled': 0,
    }
    return progress.get(status, 0)
