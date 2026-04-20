from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.api.v1.mobile_serializers import page_slice, serialize_cart_item, serialize_favorite_product, serialize_footprint, serialize_shipment
from app.db.session import get_db
from app.models.user import User
from app.schemas.commerce import CartCheckoutRequest, CartItemCreateRequest, CartItemUpdateRequest
from app.services.commerce_service import CommerceService

app_router = APIRouter(prefix='/app/commerce')


@app_router.get('/products/{product_id}/status')
def product_status(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return {'code': 0, 'message': 'success', 'data': CommerceService.get_product_status(db, current_user, product_id)}


@app_router.post('/products/{product_id}/favorite')
def favorite_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    favorite = CommerceService.add_favorite(db, current_user, product_id)
    return {'code': 0, 'message': 'success', 'data': serialize_favorite_product(db, favorite)}


@app_router.delete('/products/{product_id}/favorite')
def unfavorite_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    CommerceService.remove_favorite(db, current_user.id, product_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.post('/products/{product_id}/footprint')
def record_product_footprint(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    footprint = CommerceService.record_footprint(db, current_user, product_id)
    return {'code': 0, 'message': 'success', 'data': serialize_footprint(db, footprint)}


@app_router.get('/favorites')
def list_favorites(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = page_slice(CommerceService.list_favorites(db, current_user), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_favorite_product(db, item) for item in rows]}


@app_router.delete('/favorites/{product_id}')
def remove_favorite(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    CommerceService.remove_favorite(db, current_user.id, product_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.get('/footprints')
def list_footprints(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = page_slice(CommerceService.list_footprints(db, current_user), page, page_size)
    return {'code': 0, 'message': 'success', 'data': [serialize_footprint(db, item) for item in rows]}


@app_router.delete('/footprints/{product_id}')
def remove_footprint(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    CommerceService.remove_footprint(db, current_user.id, product_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.get('/cart')
def list_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = CommerceService.list_cart_items(db, current_user)
    return {'code': 0, 'message': 'success', 'data': [serialize_cart_item(db, item) for item in rows]}


@app_router.post('/cart/items')
def add_cart_item(payload: CartItemCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = CommerceService.add_cart_item(db, current_user, payload.product_id, payload.quantity)
    return {'code': 0, 'message': 'success', 'data': serialize_cart_item(db, item)}


@app_router.patch('/cart/items/{item_id}')
def update_cart_item(
    item_id: int,
    payload: CartItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = CommerceService.update_cart_item(
        db,
        current_user,
        item_id,
        quantity=payload.quantity,
        selected=payload.selected,
    )
    return {'code': 0, 'message': 'success', 'data': serialize_cart_item(db, item)}


@app_router.delete('/cart/items/{item_id}')
def remove_cart_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    CommerceService.remove_cart_item(db, current_user.id, item_id)
    return {'code': 0, 'message': 'success', 'data': {'success': True}}


@app_router.post('/cart/checkout')
def checkout_cart(payload: CartCheckoutRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = CommerceService.checkout_cart(
        db,
        current_user,
        payload.item_ids,
        address_id=payload.address_id,
        points_amount=payload.points_amount,
        pay_channel=payload.pay_channel,
        auto_complete=payload.auto_complete,
    )
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'order_id': result['order'].id,
            'order_no': result['order'].order_no,
            'payment': result.get('payment'),
        },
    }


@app_router.get('/shipments')
def list_shipments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = CommerceService.list_shipments(db, current_user.id)
    return {'code': 0, 'message': 'success', 'data': [serialize_shipment(db, item) for item in rows]}


@app_router.get('/shipments/{order_id}')
def shipment_detail(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = CommerceService.get_shipment(db, current_user.id, order_id)
    return {'code': 0, 'message': 'success', 'data': serialize_shipment(db, order, include_detail=True)}
